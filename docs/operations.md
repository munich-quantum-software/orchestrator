# Follow the work as it runs

Slurm's own tools show which jobs are waiting, which devices admit work, and
what completed allocations consumed. Use them together with the application's
saved artifacts to follow a calculation from submission to its result. These are
local scheduler observations, not remote QPU utilization or billable time.

Inspect `scontrol show licenses` for `DisableHRES` and `DisableLayer`, and
`scontrol -d show node qan1` for the HRES layers that contain a QAN. The
controller logs each change in a device's admission with a fixed reason, for
example `hres_qdmi: amazon.braket.sv1 admission closed: unavailable`:

| Reason                                           | Meaning                                                                       |
| ------------------------------------------------ | ----------------------------------------------------------------------------- |
| `idle`, `busy`                                   | Admission open                                                                |
| `offline`, `maintenance`, `calibration`, `error` | The device reports this status                                                |
| `unregistered`                                   | Disabled in the catalogue or not installed                                    |
| `unavailable`                                    | Opening the device or reading its status failed, often credentials or network |
| `timeout`                                        | The check exceeded 10 seconds                                                 |
| `failed`                                         | The check produced no recognizable reason                                     |

Provider messages never reach the log, because they may contain credentials;
reproduce a failure with the device's own tooling. Check the controller's
credential mounts independently of the application environment. Use
`sacct -X -P` to distinguish completed, failed, cancelled, and pending
allocations.

For remote timeouts, retain the provider's task identifier before retrying
anything; QC-AFQMC writes accepted QDMI job IDs to its measurement job log. A
successful scheduler allocation is not proof that quantum execution or classical
postprocessing succeeded.

## HRES integration and upgrades

[HRES is an upstream beta interface](https://slurm.schedmd.com/hres.html).
The source revision is pinned because callback and state formats can change. The
reference callback probes each configured QDMI device within a time bound, every
30 seconds for local devices and every three minutes for remote ones, and
updates local admission; Slurm owns allocation and accounting. No second
scheduler maintains a competing allocation ledger. Preserve provider identity
from admission through compilation and submission.

Treat every Slurm/Core/provider update as an integration change. Re-run
discovery, capacity exhaustion, independent-device admission, unavailable-device
recovery, cancellation, failure reporting, and accounting checks before adopting
it. A successful callback cannot prove remote reservation or cancellation.
Record remote IDs durably in application artifacts and reconcile unresolved
submissions with the provider before allowing a retry. Terminating an allocation
is not a remote cancellation acknowledgement.

## Site deployment and recovery

The Compose controller, database, login node, and workers correspond to the
site's `slurmctld`, MariaDB/`slurmdbd`, submission host, and `slurmd` nodes.
Keep the pinned compiler, driver, adapters, provider libraries, and
configuration consistent across submission and execution hosts. Replace Compose
service names, UID/GID mappings, resource memberships, and credential mounts
with site-owned values. Keep cloud credentials outside images and job artifacts.
Reference local bindings and single-user authentication are not a production
perimeter.

Before upgrades, drain quantum resources and wait for or reconcile outstanding
remote jobs. Back up the accounting database with its supported consistent
backup procedure, controller state, configuration, component pins, and
application artifacts. Restore to an isolated cluster and verify accounting
continuity and resource discovery before reopening admission. Keep the matching
old images and configuration for rollback; never roll back a changed database
schema without a compatible database restore. A backup that has not passed
restoration testing is not release evidence.
