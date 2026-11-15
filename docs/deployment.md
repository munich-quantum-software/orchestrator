# Bring up your first cluster

A local cluster puts the architecture into practice. The containers provide the
roles of an HPC installation in a Linux container environment, with DDSIM as the
available quantum execution device. Linux ARM64 runs directly; Apple Silicon
uses the Linux ARM64 virtual machine provided by Docker Desktop.

## Local reference cluster

Install Docker Engine with Compose on Linux, or Docker Desktop on Apple Silicon,
and initialize the pinned QC-AFQMC submodule:

```bash
git submodule update --init --depth 1
sh deploy/slurm/prepare.sh
docker compose -f deploy/slurm/compose.yml up --build -d --wait
```

Use rootful Docker with cgroup v2 and privileged containers. Allow 8 CPUs and 24
GiB RAM for the initial build. On Docker Desktop, allocate these resources to
the Linux VM in Settings → Resources; host capacity alone is insufficient.
`prepare.sh` refuses to overwrite an existing runtime or authentication key. The
runtime is `build/slurm`; stop the matching Compose project before removing it.

```bash
docker compose -f deploy/slurm/compose.yml exec --user 10000:10000 login bash --login
sinfo
scontrol show licenses
```

Slurm's `--licenses` CLI and `license/` accounting TRES name are also used by
HRES. They do not mean the old license-reservation admission mechanism is
active. `resources.yaml` defines HRES membership, counts, and the QDMI
maintenance callback.

```bash
srun --partition=quantum --licenses=mqt.ddsim.default:1 python /workspace/scripts/check_workflows.py --output /jobs/workflows
```

## Apple Silicon development and demonstrations

Use the native `linux/arm64` engine and build the image on the Mac. Do not set
`DOCKER_DEFAULT_PLATFORM=linux/amd64` or reuse a CPU-tuned image built on a
different ARM machine. Slurm, systemd, MPI, and the native compiler run inside
the Linux VM; host Python is used only for development tools and documentation.

Use the Apple Virtualization framework with VirtioFS file sharing. Keep the
checkout and runtime directory in a Docker-shared location, such as your home
directory. Database and controller state already use Linux named volumes.
Enhanced Container Isolation must be disabled for this privileged reference
cluster: Slurm needs the VM's host cgroup namespace. The containers use Docker's
cgroup mount directly, so no macOS `/sys/fs/cgroup` path needs sharing.

Check the selected engine before starting:

```bash
docker info --format '{{.OSType}} {{.Architecture}} cgroup={{.CgroupVersion}} CPUs={{.NCPU}} memory={{.MemTotal}}'
```

Expect Linux, ARM64 (`aarch64`), and cgroup version 2. Follow the same
preparation, Compose, and acceptance commands as on Linux. The deployment has
been exercised on Linux ARM64; Docker Desktop execution on Apple Silicon still
requires a full acceptance run before claiming that platform is qualified.
Docker's
[VM and resource settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/)
describe the host configuration.

## How the software is built

`deploy/spack/spack.yaml` selects the native components and pinned package
repository. Local recipes fix the Slurm, Core, QDMI provider, and AWS SDK source
revisions. The Ubuntu 26.04 container uses Spack compiler discovery and
registers its Python, LLVM SDK, and preinstalled libraries as externals. It then
builds the integration components from source, tuned for the build machine. Its
concrete lock and installed store remain in the image. The root `uv.lock`
supplies the scientific Python environment, without replacing the source-built
Core.

For an existing HPC site, reuse the recipes with your site's compiler, MPI,
external libraries, and Spack configuration. Concretize for that machine and
retain the resulting lock with deployment records. Build for the intended
execution hosts: native CPU tuning can make an image unsuitable for older CPUs.
The reference image's external-library paths are specific to the container.
Supply the portable `mqsc-mlir-sdk` through an external declaration; its package
is deliberately not buildable, so a missing SDK fails during concretization.

## From allocation to device

QC-AFQMC reads the running job's `licenses_allocated` record from the Slurm
controller once before opening a device. It requires one granted QDMI HRES
resource owned by the current user and rejects an explicit `--device` that
differs from that allocation. Resource names in this deployment are the
canonical QDMI device IDs. Requested alternatives and `SLURM_JOB_LICENSES` are
not used to choose the execution device.

The opened device supplies both the compiler target and execution backend.
Multiple-device allocations are not supported by this application path. The
lookup prevents accidental mismatches; provider credentials and site policy
still determine authorization.

## Existing clusters

Build the pinned HRES-capable Slurm revision with Lua support. Install the
shared Core/provider environment on QANs, the Lua callback and bounded QDMI
probe on the controller, and register devices in `resources.yaml`. Adapt node
names, partitions, accounts, and resource counts to site policy. Add matching
accounting TRES and validate with the supplied acceptance scenarios.

The callback starts admission closed, opens it for IDLE/BUSY devices, and closes
it on probe failure or timeout, logging each change with a fixed reason; see
[operations](operations.md). Running allocations retain their resources.
Controller probe credentials and user job credentials are independent.

HRES is a development interface pinned in the Slurm Spack recipe. Upgrade it
deliberately and rerun outage, recovery, capacity, placement, and accounting
checks.

## Configuration and credentials

`MQSC_ORCHESTRATOR_RUNTIME` and `MQSC_ORCHESTRATOR_ROOT` override the runtime
directory and the read-only repository mount.

The device catalogue is mounted at `/etc/mqt-core/qdmi.json`. Keep credentials
outside images and Git. Mount credential files read-only through a private
Compose overlay. `build/slurm/qdmi.env` configures controller probes; user jobs
need their own exported configuration. Follow each provider's authentication
documentation; [Run on Amazon Braket](providers.md#run-on-amazon-braket) walks
through one provider end to end.

## Stop

```bash
docker compose -f deploy/slurm/compose.yml down
```

This preserves accounting volumes. Use `down --volumes` only when you intend to
discard that cluster's accounting data.
