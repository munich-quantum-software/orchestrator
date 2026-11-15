# Know what a successful run proves

A useful demonstration leaves evidence. We check the journey from allocation to
classical result, and keep enough of the submitted program and returned data to
explain a failure. Local simulation and live execution answer different
questions; their results remain separate.

## Every pull request

The isolated Docker acceptance runner checks HRES capacity, QAN placement,
unavailable-device admission, recovery, independent resources, closed admission
for unconfigured provider devices, user job environments, and persistent
accounting. It then runs the serialized-payload checks and dependent QC-AFQMC
smoke application.

Asymmetric circuits retain unused output bits where the format supports them,
multiple classical registers, permuted measurements, and distinguishable batch
entries. Checks assert counts and ordered shot reconstruction through QDMI,
Qiskit, and PennyLane. Oracle tests deliberately reverse or corrupt results and
require rejection.

```bash
uvx nox -s tests
uvx nox -s integration
```

A failed run keeps its isolated runtime directory, including job logs and
results, under `build/slurm-tests/<run>/`. A simulator pass is never promoted to
a provider acceptance result.

## Provider validation

Pull-request CI uses no credentials. The scheduled
[provider target check](providers.md#target-checks) reads live device metadata
and compiles for it, but never submits to a provider. Local simulation does not
establish that a remote device accepts submissions or returns correct results;
provider transport is tested in each provider's repository. Any live validation
requires explicit authorization, a bounded scope, and provider-specific
credentials.

## Failure boundaries

A timeout after remote submission can leave the remote task running. Preserve
the remote job ID and report an unresolved state. Do not automatically retry an
ambiguous submission. Slurm cancellation alone does not guarantee remote
cancellation; investigate or cancel using the provider's owning API.

Native format or topology failures are integration failures. Fix the owning
Core/provider repository and update the pin; do not relabel or reorder results
here to make a test pass.
