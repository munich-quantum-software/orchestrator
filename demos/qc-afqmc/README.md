# QC-AFQMC

This application adapts the pinned Amazon Braket matchgate-shadow H₂ example to
QDMI, compiler-backed PennyLane execution, classical walkers, and MPI
continuation.

Run it in the shared MQSC Orchestrator environment. See
[the executable showcase](https://mqsc-orchestrator.readthedocs.io/en/latest/afqmc.html)
for dependent Slurm jobs, workloads, and scientific limits. The `--smoke`
workload validates integration, not convergence.

`run.py --stage measure` samples the trial-state shadows on the allocated device
and saves `measurements.json`. `run.py --stage propagate` reconstructs the trial
and saves results and reference energies. The default `--stage all` executes
both locally.

The default is upstream H₂ at 0.75 Å in STO-3G with its 0.12-radian trial
rotation. `--bond-length` changes the H₂ geometry; propagation reads it from the
saved measurements. The Slurm scripts request 2 GiB for measurement and four MPI
ranks for propagation. Upstream `QTrial` reconstructs matchgate overlaps from
the measured shadows at each walker evaluation. Allow sufficient time for this
classical continuation. Propagation uses fresh OS entropy per upstream
trajectory, locally and with MPI; the quantum preparation and sampling `--seed`
does not seed it.

The `upstream/` submodule is an active dependency, not just a source credit:
`qmc.py` imports its chemistry, trial-state, shadow-collection, and walker
propagation routines. Keeping the pinned source as a submodule avoids a second
fork of that scientific implementation. It comes from the
[Amazon Braket examples](https://github.com/amazon-braket/amazon-braket-examples).
Initialize it with `git submodule update --init --depth 1` from the repository
root. Dependencies are locked centrally; no application-specific environment is
needed.
