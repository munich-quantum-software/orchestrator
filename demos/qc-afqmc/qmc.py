# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Walker execution using Amazon Braket AFQMC."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from afqmc.qmc.classical import classical_afqmc, full_imag_time_evolution
from afqmc.qmc.quantum_shadow import cqa_afqmc, cqa_imag_time_evolution

if TYPE_CHECKING:
    from afqmc.trial_wavefunction.quantum_ovlp import QTrial
    from afqmc.trial_wavefunction.single_slater import SingleSlater
    from afqmc.utils.chemical_preparation import ChemicalProperties
    from mpi4py.MPI import Comm


def local_afqmc(
    num_walkers: int,
    num_steps: int,
    dtau: float,
    trial: QTrial | SingleSlater,
    psi0: np.ndarray,
    *,
    prop: ChemicalProperties | None = None,
    workers: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """Run upstream full trajectories with independent OS-entropy initialization.

    Supply ``prop`` for classical propagation. ``workers`` bounds the upstream
    process pool; each trajectory initializes its own random stream.

    Returns:
        Per-walker energies and pre-step weights.
    """
    if prop is None:
        return cqa_afqmc(num_walkers, num_steps, dtau, trial, psi0, max_pool=workers)
    return classical_afqmc(num_walkers, num_steps, dtau, trial, prop, max_pool=workers)


def mpi_afqmc(
    comm: Comm,
    inputs: tuple[int, int, int, float, QTrial, SingleSlater, ChemicalProperties, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
    """Run upstream full trajectories for this rank's share of the walkers.

    Rank zero supplies ``inputs`` as walker count, quantum steps, classical
    steps, time step, quantum trial, classical trial, chemical properties, and
    initial walker; the other ranks pass only ``comm``. As in local execution,
    each trajectory seeds its own random stream from OS entropy.

    Returns:
        Quantum energies/weights and classical energies/weights on rank zero,
        each with shape ``(num_walkers, steps)``; None on the other ranks.
    """
    num_walkers, quantum_steps, classical_steps, dtau, quantum_trial, classical_trial, prop, psi0 = comm.bcast(
        inputs, root=0
    )
    count = len(range(comm.rank, num_walkers, comm.size))
    classical_shift = classical_trial.compute_trial_energy(prop)
    trajectories = (
        [
            cqa_imag_time_evolution(quantum_steps, dtau, quantum_trial, quantum_trial.E_shift, psi0, 1.0)
            for _ in range(count)
        ],
        [
            full_imag_time_evolution(
                classical_steps, dtau, classical_trial, prop, classical_shift, classical_trial.psi0, 1.0
            )
            for _ in range(count)
        ],
    )
    gathered = comm.gather(trajectories, root=0)
    if comm.rank != 0:
        return None
    arrays = []
    for ensemble in range(2):
        energies, weights = zip(*(trajectory for rank in gathered for trajectory in rank[ensemble]), strict=True)
        arrays.extend((np.array(energies), np.array(weights)))
    return tuple(arrays)
