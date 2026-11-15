# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Run the matchgate-shadow H2 experiment with MQT Core and a QDMI device."""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import sys
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent / "upstream/examples/hybrid_quantum_algorithms/Quantum_Monte_Carlo_Chemistry"),
)

import numpy as np
from afqmc.shadow_collection import run as collect_shadows
from afqmc.trial_wavefunction.quantum_ovlp import QTrial
from afqmc.trial_wavefunction.single_slater import SingleSlater
from afqmc.utils.chemical_preparation import chemistry_preparation
from afqmc.utils.shadow import shadow_from_json
from matplotlib.figure import Figure
from mqt.core.mlir import CompilationOptions
from mqt.core.plugins.pennylane import DDSIMDevice, QDMIDevice
from mqt.core.qdmi import builtin_driver
from pyscf import fci, gto, lib

from allocated_device import resolve_device
from qmc import local_afqmc, mpi_afqmc

if TYPE_CHECKING:
    from mpi4py.MPI import Comm

DEFAULT_DEVICE_ID = "mqt.ddsim.default"
WORKLOADS = {
    "smoke": {"shadows": 4, "shots": 16, "walkers": 4, "quantum_steps": 3, "classical_steps": 3},
    "default": {"shadows": 128, "shots": 100, "walkers": 4, "quantum_steps": 8, "classical_steps": 8},
    "full": {"shadows": 4000, "shots": 100, "walkers": 1440, "quantum_steps": 100, "classical_steps": 600},
}
DTAU = 0.005


def shadow_device(device_id: str, seed: int) -> QDMIDevice:
    """Open the selected device for four-wire shadows with seeded compilation.

    Returns:
        Core's PennyLane device, compiling for and executing on the same QDMI device.
    """
    options = CompilationOptions(seed=seed)
    if device_id == DEFAULT_DEVICE_ID:
        os.environ.setdefault("MQT_CORE_DD_WORKER_BUDGET", os.environ.get("SLURM_CPUS_PER_TASK", "1"))
        return DDSIMDevice(wires=4, seed=seed, compile_options=options)
    return QDMIDevice(device_id, wires=4, compile_options=options)


def measure(args: argparse.Namespace) -> None:
    """Sample the trial-state shadows on the allocated device and save them."""
    workload = WORKLOADS[args.workload]
    device_id = resolve_device(args.device, builtin_driver.registered_device_ids(), default=DEFAULT_DEVICE_ID)
    device = shadow_device(device_id, args.seed)
    os.environ["SEED"] = str(args.seed)  # Upstream seeds its single shadow-generation call from SEED.
    try:
        counts, permutations = collect_shadows(workload["shadows"], workload["shots"], device)
    finally:
        # Keep remote job IDs in the job log, also when collection fails.
        job = device.last_job
        # Batched shadows share one job, so list each ID once.
        job_ids = list(
            dict.fromkeys(a.handle.id for e in (job.entries if job else ()) for a in e.attempts if a.handle is not None)
        )
        sys.stderr.write(f"QDMI job IDs: {job_ids}\n")
    assert len(counts) == workload["shadows"]
    assert all(sum(snapshot.values()) == workload["shots"] for snapshot in counts)
    args.output.mkdir(parents=True, exist_ok=True)
    measurements = {
        "molecule": {"bond_length_angstrom": args.bond_length, "basis": "sto-3g", "trial_angle_radians": 0.12},
        "workload": {"name": args.workload, **workload},
        "device": device_id,
        "seed": args.seed,
        "qdmi_jobs": device.submitted_jobs,
        "output": counts,
        "Q_save": permutations,
    }
    (args.output / "measurements.json").write_text(json.dumps(measurements) + "\n", encoding="utf-8")


def propagate(args: argparse.Namespace, comm: Comm | None = None) -> None:
    """Reconstruct the trial from saved shadows, propagate walkers, and save results."""
    measurements = json.loads((args.output / "measurements.json").read_text(encoding="utf-8"))
    molecule, workload = measurements["molecule"], measurements["workload"]
    num_walkers, quantum_steps, classical_steps = (
        workload[key] for key in ("walkers", "quantum_steps", "classical_steps")
    )
    lib.num_threads(1)
    shadow = shadow_from_json(measurements["output"], measurements["Q_save"])
    mol = gto.M(
        atom=f"H 0 0 0; H 0 0 {molecule['bond_length_angstrom']}", basis=molecule["basis"], unit="Angstrom", verbose=0
    )
    hf = mol.RHF().run()
    assert hf.converged, "Hartree-Fock did not converge."
    fci_energy, _ = fci.FCI(hf).kernel()
    assert np.isfinite(fci_energy)
    assert fci_energy <= hf.e_tot + 1e-8, "FCI reference exceeds the variational Hartree-Fock energy."
    prop = chemistry_preparation(mol, hf)
    psi0 = np.eye(2 * prop.nbasis, prop.nup + prop.ndown)
    quantum_trial = QTrial(prop, shadow)
    classical_trial = SingleSlater(prop, psi0)

    if comm is not None:
        workers = comm.size
        results = mpi_afqmc(
            comm, (num_walkers, quantum_steps, classical_steps, DTAU, quantum_trial, classical_trial, prop, psi0)
        )
        assert results is not None
        quantum_local, quantum_weights, classical_local, classical_weights = results
    else:
        workers = min(args.workers, num_walkers)
        quantum_local, quantum_weights = local_afqmc(
            num_walkers, quantum_steps, DTAU, quantum_trial, psi0, workers=workers
        )
        classical_local, classical_weights = local_afqmc(
            num_walkers, classical_steps, DTAU, classical_trial, classical_trial.psi0, prop=prop, workers=workers
        )

    for energies, weights, steps in (
        (quantum_local, quantum_weights, quantum_steps),
        (classical_local, classical_weights, classical_steps),
    ):
        assert energies.shape == weights.shape == (num_walkers, steps)
        assert np.isfinite(energies).all(), "AFQMC produced non-finite local energies."
        assert np.isfinite(weights).all()
        assert (weights >= 0).all()
        assert (weights.sum(axis=0) > 0).all(), "All walkers lost their weight."
    quantum_energy = np.real(np.average(quantum_local, weights=quantum_weights, axis=0))
    classical_energy = np.real(np.average(classical_local, weights=classical_weights, axis=0))
    quantum_time = DTAU * np.arange(quantum_steps)
    classical_time = DTAU * np.arange(classical_steps)
    if workload["name"] == "smoke":
        # A loose small-system sanity bound, not a confidence interval or convergence claim.
        assert abs(quantum_energy[-1] - fci_energy) < 0.25
        assert abs(classical_energy[-1] - fci_energy) < 0.25

    np.savez_compressed(
        args.output / "results.npz",
        quantum_local_energies=quantum_local,
        quantum_weights=quantum_weights,
        quantum_energy=quantum_energy,
        quantum_time=quantum_time,
        classical_local_energies=classical_local,
        classical_weights=classical_weights,
        classical_energy=classical_energy,
        classical_time=classical_time,
        **{f"shadow_{key}": value for key, value in shadow.items()},
    )
    summary = {
        "molecule": molecule,
        "workload": workload,
        "device": measurements["device"],
        "seed": measurements["seed"],
        "qdmi_jobs": measurements["qdmi_jobs"],
        "dtau": DTAU,
        "workers": workers,
        "hartree_fock_energy": float(hf.e_tot),
        "fci_energy": float(fci_energy),
        "final_quantum_energy": float(quantum_energy[-1]),
        "final_classical_energy": float(classical_energy[-1]),
        "versions": {name: version(name) for name in ("mqt-core", "pennylane", "pyscf")},
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    figure = Figure(figsize=(7, 4))
    axis = figure.subplots()
    axis.plot(quantum_time, quantum_energy, ".-", label="Quantum-assisted AFQMC")
    axis.plot(classical_time, classical_energy, ".-", label="Classical AFQMC")
    axis.axhline(fci_energy, color="black", linestyle="--", label="FCI")
    axis.axhline(hf.e_tot, color="gray", linestyle=":", label="Hartree-Fock")
    axis.set(xlabel="Imaginary time (1/hartree)", ylabel="Energy (hartree)", title="H2 matchgate-shadow AFQMC")
    axis.legend()
    figure.tight_layout()
    figure.savefig(args.output / "energies.png", dpi=160)


def main() -> None:
    """Prepare H2, measure its trial state, propagate walkers, and save results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=("all", "measure", "propagate"), default="all", help="Run the full workflow or one stage."
    )
    parser.add_argument("--device", help=f"QDMI device ID (allocated device in Slurm; locally {DEFAULT_DEVICE_ID}).")
    workload = parser.add_mutually_exclusive_group()
    workload.add_argument(
        "--full", dest="workload", action="store_const", const="full", help="Use the upstream notebook workload."
    )
    workload.add_argument(
        "--smoke", dest="workload", action="store_const", const="smoke", help="Use a minimal integration workload."
    )
    parser.set_defaults(workload="default")
    parser.add_argument("--bond-length", type=float, default=0.75, help="H2 bond length in angstrom (STO-3G).")
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Quantum preparation and sampling seed (default: 7); propagation uses OS entropy.",
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Local AFQMC worker processes (default: 1; ignored with MPI)."
    )
    parser.add_argument("--mpi", action="store_true", help="Distribute propagation over the launched MPI ranks.")
    parser.add_argument("--output", type=Path, default=Path("results"), help="Output directory (default: results).")
    args = parser.parse_args()
    if not math.isfinite(args.bond_length) or args.bond_length <= 0:
        parser.error("--bond-length must be positive and finite")
    if args.workers < 1 or not 0 < args.seed < 2**31:
        parser.error("--workers must be positive and --seed must be between 1 and 2147483647")
    if args.mpi and args.stage != "propagate":
        parser.error("--mpi requires --stage propagate")

    if args.mpi:
        from mpi4py import MPI  # ruff: ignore[import-outside-top-level] - Only the distributed stage initializes MPI.

        if MPI.COMM_WORLD.rank == 0:
            propagate(args, MPI.COMM_WORLD)
        else:
            mpi_afqmc(MPI.COMM_WORLD)
        return
    if args.stage in {"all", "measure"}:
        measure(args)
    if args.stage in {"all", "propagate"}:
        propagate(args)


if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()
