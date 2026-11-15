# QC-AFQMC showcase

How can quantum measurements help a classical calculation estimate a molecule's
energy? Quantum-classical auxiliary-field quantum Monte Carlo (QC-AFQMC) makes
that question tangible. Our small hydrogen-molecule example connects quantum
measurements to a population of classical walkers, whose propagation produces an
energy estimate.

The application uses the pinned Amazon Braket matchgate-shadow H₂ example.
Patrick Hopf's QDMI application supplies measurement and propagation stages,
classical walkers, and MPI workers. The workflow illustration follows those
executable stages.

Explore the stages with the buttons or left/right arrow keys. The illustration
shows the workflow, rather than execution timing.

```{raw} html
<div class="workflow" tabindex="0" aria-label="QC-AFQMC workflow">
<svg viewBox="0 0 900 180" role="img" aria-label="Prepare, allocate through Slurm HRES and compile for the selected device, execute through QDMI, then propagate classical walkers"><text x="25" y="90" font-size="22">Prepare → HRES allocation + compilation → QDMI → Propagation</text></svg>
<p class="workflow-description" aria-live="polite">Prepare the molecular trial and shadow circuits.</p>
<button type="button" data-step="-1">Previous stage</button>
<button type="button" data-step="1">Next stage</button>
</div>
```

## Run the dependent application

The measurement stage selects its device from the actual Slurm allocation. An
optional `--device` must match that grant. Outside Slurm, `--device` selects a
local target and defaults to DDSIM. The propagation stage reads the device
identity from its saved measurements and needs no quantum allocation.

In the login shell:

```bash
mkdir -p results
measurement=$(sbatch --parsable /workspace/demos/qc-afqmc/measure.sh --smoke)
sbatch --dependency=afterok:$measurement --kill-on-invalid-dep=yes \
  /workspace/demos/qc-afqmc/propagate.sh "results/$measurement"
```

Use a fresh output directory for each run. Remove `--smoke` for the bounded
local demonstration; `--full` selects the much larger upstream workload and is
never run by PR CI.

Core compiles for and executes on the allocated device. The quantum stage saves
the measured shadow counts and signed permutations in `measurements.json` and
writes accepted QDMI job IDs to its job log. The classical stage reconstructs
the trial and propagates walkers. `summary.json`, `results.npz`, and
`energies.png` retain reference energies, the workload, software versions, and
results. Slurm accounting records each stage's timing, state, and allocated
resources.

## Molecule and resource requests

The default follows the upstream example: H₂ at 0.75 Å in STO-3G, with its
four-orbital trial circuit and a double-excitation angle of 0.12 radians. Use
`--bond-length 1.0` on the measurement command to explore another H₂ geometry.
The saved molecule configuration controls the subsequent chemistry and reference
energies. Other molecules, bases, and trial circuits require a scientific
extension; changing the distance does not optimize the trial state. The pinned
upstream implementation supplies the matchgate signs directly.

| Workload  | Shadows | Shots | Walkers | Steps (quantum / classical) |
| --------- | ------: | ----: | ------: | --------------------------: |
| `--smoke` |       4 |    16 |       4 |                       3 / 3 |
| default   |     128 |   100 |       4 |                       8 / 8 |
| `--full`  |    4000 |   100 |    1440 |                   100 / 600 |

The measurement script requests one CPU and 2 GiB. The propagation script
requests four MPI ranks on two nodes, with 2 GiB per node. Sites can override
these Slurm requests. DDSIM's worker budget follows `SLURM_CPUS_PER_TASK`
(default one outside Slurm), unless `MQT_CORE_DD_WORKER_BUDGET` is explicitly
set. A container CPU quota alone does not restrict CPU affinity.

The quantum stage submits all shadow programs as one QDMI job through Core's
`DDSIMDevice` for DDSIM, or `QDMIDevice` for the allocated device otherwise.
Core splits that job only when a device declines its size; see
[Tasks and cost](providers.md#tasks-and-cost). All targets use Core's default
mapping parameters, seeded by `--seed`. DDSIM samples program `i` with seed plus
`i`.

## Propagate the measured trial

Propagation uses upstream `QTrial` to reconstruct matchgate overlaps for each
walker from the saved shadows. With MPI, rank zero constructs the trials and
distributes them; every rank runs upstream full trajectories for its share of
the walkers, and rank zero gathers them.

To propagate an existing measurement set, copy only `measurements.json` into a
fresh output directory. Matchgate reconstruction can take substantial time;
choose the Slurm time limit and worker count for the workload. The propagation
script's default four-hour limit accommodates longer classical continuation.

## Scientific limits

The smoke configuration establishes executable integration, not convergence or
quantum advantage. Its final energies must remain within a loose 0.25 hartree
sanity bound of the independent FCI calculation; this is not a statistical
confidence interval. The application compares against Hartree–Fock and full
configuration interaction for the same small molecule. Finite-shadow error and
AFQMC systematic biases are not eliminated by a successful workflow. Container
nodes share one host; MPI execution is not a scaling measurement.

Propagation draws fresh OS entropy, independently of the quantum measurement
seed. Local and MPI execution both use upstream full-trajectory routines, which
initialize one stream per trajectory. Quantum and Hartree–Fock trials do not
replay the same random numbers, and walkers are not branched or resampled.

Pointwise walker standard errors describe sampling at one imaginary-time point
conditional on the retained shadow trial. They exclude finite-shadow
uncertainty, time-discretization and phaseless biases, and do not provide an
error bar for a time-averaged energy without accounting for temporal
correlation. The deterministic Hartree–Fock reference line is distinct from the
stochastic Hartree–Fock-trial evolution, which also has walker uncertainty.
