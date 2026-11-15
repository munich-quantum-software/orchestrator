# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Check upstream chemistry, matchgate signs, and H2 references."""

from __future__ import annotations

import os
import sys
from functools import reduce
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pennylane.devices import ExecutionConfig
    from pennylane.tape import QuantumScriptOrBatch
    from pennylane.typing import Result, ResultBatch

import numpy as np
import pennylane as qml
from openfermion import InteractionOperator, get_sparse_operator
from openfermion.chem.molecular_data import spinorb_from_spatial

DEMO = Path(__file__).resolve().parents[2] / "demos/qc-afqmc"
sys.path.insert(0, str(DEMO))
demo = import_module("run")
matchgate = import_module("afqmc.utils.matchgate")
shadow = import_module("afqmc.shadow_collection")


class RecordedReference(qml.devices.DefaultQubit):
    """Retain the upstream circuit for an independent trial-state check."""

    def execute(
        self, circuits: QuantumScriptOrBatch, execution_config: ExecutionConfig | None = None
    ) -> Result | ResultBatch:
        """Save the executed tapes and run PennyLane's reference simulator."""
        self.tapes = circuits
        return super().execute(circuits, execution_config)


def check_science() -> None:
    """Check the trial amplitudes, Majorana conjugation, and two H2 geometries."""
    reference = RecordedReference(wires=4, seed=7)
    shadow.run(1, 16, reference)
    trial = qml.tape.QuantumScript(reference.tapes[0].operations[:3])
    state = qml.matrix(trial, wire_order=range(4))[:, 0]
    expected = np.zeros(16)
    expected[[0, 3, 12]] = [1, -np.sin(0.06), np.cos(0.06)]
    np.testing.assert_allclose(state, expected / np.sqrt(2), atol=1e-14)
    paulis = (np.array([[0, 1], [1, 0]]), np.array([[0, -1j], [1j, 0]]))
    majoranas = np.array([
        reduce(np.kron, [np.diag([1, -1])] * mode + [pauli] + [np.eye(2)] * (3 - mode))
        for mode in range(4)
        for pauli in paulis
    ])
    rng = np.random.default_rng(7)
    for _ in range(4):
        orthogonal, _ = shadow.random_signed_permutation(8, rng)
        schedule, angles, signs = matchgate.compile_gaussian_givens(orthogonal)

        with qml.queuing.AnnotatedQueue() as queue:
            matchgate.apply_gaussian_givens(angles, schedule)
            matchgate.apply_pauli_layer(signs)
        unitary = qml.matrix(qml.tape.QuantumScript.from_queue(queue), wire_order=range(4))
        np.testing.assert_allclose(
            unitary.conj().T @ majoranas @ unitary,
            np.einsum("jk,kab->jab", orthogonal, majoranas),
            atol=1e-13,
        )
    demo.lib.num_threads(1)
    sector = [i for i in range(16) if i.bit_count() == 2]
    for length in (0.75, 1.0):
        mol = demo.gto.M(atom=f"H 0 0 0; H 0 0 {length}", basis="sto-3g", unit="Angstrom", verbose=0)
        hf = mol.RHF().run()
        assert hf.converged
        prop = demo.chemistry_preparation(mol, hf)
        one, two = spinorb_from_spatial(prop.h1e, prop.eri)
        hamiltonian = get_sparse_operator(InteractionOperator(prop.nuclear_repulsion, one, two / 2)).toarray()
        np.testing.assert_allclose(hamiltonian[12, 12], hf.e_tot, atol=1e-10)
        exact = np.linalg.eigvalsh(hamiltonian[np.ix_(sector, sector)])[0]
        np.testing.assert_allclose(exact, demo.fci.FCI(hf).kernel()[0], atol=1e-10)


if __name__ == "__main__":
    os.environ["SEED"] = "7"
    check_science()
    print("PASS QC-AFQMC: trial amplitudes, matchgate signs, H2 references")
