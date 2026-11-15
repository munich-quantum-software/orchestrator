# MQSC Orchestrator Agent Guide

Read the relevant parts of [development](docs/development.md),
[AI usage](docs/ai_usage.md), and [operations](docs/operations.md) before
changing their contracts.

## Layout and ownership

- `deploy/spack/` owns native source builds and component pins.
- `deploy/slurm/` owns the Compose reference cluster, HRES callback, device
  catalogue, and accounting configuration.
- `scripts/` owns cross-component validation and administration tools. `tests/`
  checks their contracts.
- `demos/qc-afqmc/` is a uv workspace member. Its upstream submodule retains its
  license and must not be edited locally.
- `docs/` uses Furo and MyST. `brand/` contains canonical artwork and font
  sources. Native source revisions live only in the Spack recipes.
- Generated files, runtimes, credentials, and evidence belong in ignored
  `build/` directories. Never commit or print secrets.

## Working principles

Inspect status first and preserve other work. Complete authorized changes
without routine permission checkpoints. Trace deployment, callers,
configuration, tests, and documentation together. Prefer existing platform
facilities over a new service or scheduler.

Compilation, adapters, and result contracts belong in Core; provider transport
belongs in provider repositories. Fix defects there, then update compatible
pins. Do not compensate for output-order defects in Orchestrator. Keep the
compilation target distinct from the execution device and preserve exact
serialized payloads and readout mappings.

Resolve quantum device selection from the controller's `licenses_allocated`
record once per application process; never infer the grant from requested
licenses. Compile and execute through the same Device with Core's public
PennyLane APIs; do not override private Core members or decode results here.

HRES gates local admission. It does not reserve remote QPUs, authorize cloud
access, or prove remote cancellation. Keep admission fail-closed, bound probes,
retain remote job IDs, and never retry an ambiguous submission automatically. No
paid or emulator submissions without explicit authorization and bounded scope.
Workflow jobs run only in the public repository. PR CI is credential-free. The
scheduled provider-target workflow may read device metadata with credentials; it
never submits to a provider.

Treat HRES and provider pins as reviewed integration inputs, not stable APIs.
Keep simulated execution labeled. CI executes only on DDSIM; provider transport
is tested in the provider repositories, not here. Provider devices stay disabled
in the reference catalogue.

## Style and documentation

Use MQSC, MQT, IQM, IBM, and Amazon Braket in prose; retain exact API and Spack
identifiers. Use “The MQSC Orchestrator” in running prose. Project sources use
Apache-2.0 WITH LLVM-exception with MQSC copyright and the year 2026; maintain
headers with the license-tools hook. Keep artwork assets and their generator
only; do not add branding policies or asset-specific test machinery.

Use accessible, inviting prose and established scientific terminology. Explain
the application journey before configuration details. Document current
contracts, ownership, failure boundaries, and numerical limits. Keep release
history in `CHANGELOG.md`, with source PR/commit links and every contributing
human author. Update it for user-visible changes; do not invent PR numbers or
attribute human authorship to an agent.

Use Ruff formatting and Google-style docstrings; fix lint diagnostics rather
than hiding them. PEP 723 metadata suits standalone administration scripts. Use
Python 3.14 in controlled environments and at least 3.13 for site tools,
meaningful dependency lower bounds, and no upper `requires-python` bound. Run
nox with `uvx nox`. Never use `pull_request_target` or suppress zizmor
diagnostics. Template synchronization is disabled; maintain the MQT-style files
locally. Runtime applications use the shared uv workspace lock and installed
deployment environment; never let uv replace the source-built Core installation
inside a running allocation.

## Validation

- `uv sync --locked --only-group dev` installs repository tools without
  scientific runtime packages.
- `uvx nox -s lint` runs pre-commit checks through prek.
- `uvx nox -s tests` runs host contracts; use pytest filters when appropriate.
- `uvx nox -s docs` builds the documentation.
- `uv run --script tests/slurm/run_integration.py` validates changed deployment
  behavior.
- `uv run --script scripts/branding.py` regenerates vector assets. Do not
  recolor, redraw, or optimize the canonical `brand/mqsc.svg`.

QC-AFQMC reuses upstream science and defaults to its H₂ trial. Keep one seeded
shadow-generation call. Record molecule configuration with measurements and use
it for propagation. Request memory explicitly in Slurm jobs. Propagation uses
upstream `QTrial` and upstream full trajectories, locally and per MPI rank.
Propagation uses fresh OS entropy; quantum preparation and sampling retain their
separate seed. Keep this distinction explicit; do not substitute exact molecular
amplitudes or a custom trial evaluator. Slurm accounting, not an
application-specific trace, records stage timing.

Run affected checks after edits and inspect the final diff. Inspect rendered
documentation and branding with Chrome DevTools, including console and network;
a successful build is not visual validation. Keep performance claims tied to a
measured workload; distinguish local allocations from remote usage. Do not
monitor hosted CI unless asked; report credit or infrastructure failures
separately from code failures.

## Git and collaboration

Develop on branches and merge through pull requests to `main`. Every commit and
annotated tag must be signed with the configured key; verify commits before
pushing. Stop if signing fails. Preserve human authors and trailers; record
assistance with `Assisted-by`, never an AI `Co-authored-by`.

Use gitmoji-prefixed imperative subjects, at most 72 characters. Keep public
GitHub text consistent with the AI usage policy. Submit PRs using the existing
template, assign `burgholzer`, and apply existing appropriate labels. Never
merge, publish, change visibility, enable paid execution, or modify external
repositories without authorization for that action.

Record substantial plans in `.agent/plans/`. Document publication blockers and
upstream constraints; do not claim site qualification from a single-host Compose
test.
