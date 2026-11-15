# Connect a quantum provider

Every QDMI device joins the cluster the same way. The image builds MQT Core and
the Amazon Braket, IBM, IQM and Pasqal QDMI providers from their pinned Spack
recipes. Each provider registers its devices with Core, and Slurm admits jobs to
a device through one HRES resource with the same name.

## The four steps

1. **Install.** Add a Spack recipe in `deploy/spack/spack_repo/mqsc/packages/`
   and its spec in `deploy/spack/spack.yaml`. The provider's
   `mqt.core.qdmi.manifests` entry point registers its device IDs.
2. **Catalogue.** `/etc/mqt-core/qdmi.json` (from `deploy/slurm/qdmi.json`)
   enables, disables, or configures devices by ID; see
   [Core's configuration guide](https://mqt.readthedocs.io/projects/core/en/latest/qdmi/configuration.html).
3. **Admit.** Add an HRES entry to `deploy/slurm/resources.yaml` and its
   `license/<id>` TRES to `AccountingStorageTRES` in `slurm.conf`. The Lua
   callback opens the device every 30 seconds for local devices and every three
   minutes for remote ones, and keeps admission closed unless it reports IDLE or
   BUSY. A host test checks that the HRES, accounting, and catalogue device
   lists agree.
4. **Authenticate.** Put probe credentials in `build/slurm/qdmi.env` for the
   controller. Users export their own credentials in their job environment.

The reference cluster registers every device that the scheduled target checks
cover, plus Pasqal's free emulator, and disables each in the catalogue, so
admission stays closed and no network request leaves the cluster. A host test
keeps the target checks within the catalogue. Remove a device's
`"enabled": false` entry after configuring credentials.

| Provider      | HRES / device IDs                                                             | Credentials                                                                                                                                                                    | Payload                        |
| ------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------ |
| DDSIM         | `mqt.ddsim.default`, `mqt.sc.default`                                         | None; local                                                                                                                                                                    | OpenQASM / QIR                 |
| IQM           | `iqm.emerald`, `iqm.garnet`, `iqm.sirius`                                     | `IQM_TOKEN` or `IQM_TOKENS_FILE`; [QDMI-on-IQM](https://github.com/iqm-finland/QDMI-on-IQM)                                                                                    | IQM JSON lowered from Base QIR |
| IBM           | `ibm.aachen`, `ibm.berlin`                                                    | `IBM_QUANTUM_API_KEY`, `IBM_QUANTUM_INSTANCE_CRN`; [ibm-qdmi-device](https://github.com/munich-quantum-software/ibm-qdmi-device)                                               | QPY                            |
| Amazon Braket | `amazon.braket.sv1` and the QPUs listed under [Target checks](#target-checks) | AWS SDK credential chain; see [Run on Amazon Braket](#run-on-amazon-braket); [amazon-braket-qdmi-device](https://github.com/munich-quantum-software/amazon-braket-qdmi-device) | OpenQASM 3                     |
| Pasqal        | `pasqal.emu-free`                                                             | `PASQAL_EMAIL`, `PASQAL_PASSWORD`, `PASQAL_PROJECT_ID`; [pasqal-qdmi-device](https://github.com/munich-quantum-software/pasqal-qdmi-device)                                    | Pulser analog sequence         |

Providers register further device IDs in their manifests. Pasqal devices run
analog Pulser sequences, not circuits, so QC-AFQMC cannot target them. Selecting
a device never grants remote access, and no paid or emulator submission runs
without explicit authorization and scope.

## Run on Amazon Braket

The reference Amazon Braket entry is the SV1 state-vector simulator: it has no
queue, bills only simulation time, and exercises the same submission path as a
QPU. This walkthrough was validated with the QC-AFQMC smoke workload on SV1. Any
submission costs money, so start with `--smoke` and set an
[AWS budget](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
first.

### Results buckets

Every quantum task writes its results to S3 in the device's region, and the
bucket name must begin with `amazon-braket-`. Create one bucket per region ahead
of time, so users need no permission to create buckets or resolve their account:

| Region     | Devices        | Bucket                                          |
| ---------- | -------------- | ----------------------------------------------- |
| us-east-1  | SV1, DM1, IonQ | `amazon-braket-orchestrator-us-east-1-ACCOUNT`  |
| us-west-1  | Rigetti        | `amazon-braket-orchestrator-us-west-1-ACCOUNT`  |
| eu-north-1 | IQM, AQT       | `amazon-braket-orchestrator-eu-north-1-ACCOUNT` |

```bash
aws s3api create-bucket --bucket amazon-braket-orchestrator-eu-north-1-ACCOUNT --region eu-north-1 --create-bucket-configuration LocationConstraint=eu-north-1
```

Omit `--create-bucket-configuration` in us-east-1. New buckets block public
access and encrypt objects by default. Users select the bucket for their
device's region with `AMZN_BRAKET_TASK_RESULTS_S3_URI`, for example
`s3://amazon-braket-orchestrator-us-east-1-ACCOUNT/USER`.

### Two permission sets

The controller's availability check only reads device metadata. Give it an
identity with this policy and nothing else:

```json
{
  "Version": "2012-10-17",
  "Statement": [{ "Effect": "Allow", "Action": "braket:GetDevice", "Resource": "*" }]
}
```

Users who run work need to create, poll, and cancel quantum tasks, and to read
results from the prepared buckets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["braket:GetDevice", "braket:CreateQuantumTask", "braket:GetQuantumTask", "braket:CancelQuantumTask"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::amazon-braket-orchestrator-*-ACCOUNT/*"
    }
  ]
}
```

With a results URI set, the pinned provider calls only these Braket actions and
reads result objects. Amazon Braket writes the results with its own service
permissions, so users need neither `s3:PutObject` nor `s3:ListBucket`; an SV1
task with exactly this policy confirmed it. Attach the execution policy to the
roles or IAM Identity Center permission sets of the people who may spend the
account's budget. To restrict users to particular devices, scope
`braket:CreateQuantumTask` to their device ARNs.

### Credentials

Prefer short-lived credentials from a role or IAM Identity Center over access
keys. The provider reads the standard AWS credential chain, including
`AWS_PROFILE` and temporary `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and
`AWS_SESSION_TOKEN`.

- **Controller.** systemd reads `build/slurm/qdmi.env` when `slurmctld` starts,
  so restart the controller after changing it. Temporary credentials there
  expire, after which admission closes; a site should use an instance role or a
  profile with `credential_process` instead.
- **Users.** Export credentials and the results URI in the login shell. Slurm
  copies the submission environment into the job, and the quantum access nodes
  reach AWS directly. A profile also needs its configuration readable on those
  nodes.

### Smoke run on SV1

Remove the `amazon.braket.sv1` entry from `build/slurm/qdmi.json`, put the
controller's credentials in `build/slurm/qdmi.env`, and start or restart the
cluster. Admission opens within three minutes, once
`scontrol show licenses amazon.braket.sv1` reports `DisableHRES=false`. Then
open a login shell with your credentials:

```bash
docker compose -f deploy/slurm/compose.yml exec --user 10000:10000 -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN -e AMZN_BRAKET_TASK_RESULTS_S3_URI login bash --login
```

```bash
mkdir -p results
measurement=$(sbatch --parsable --licenses=amazon.braket.sv1:1 /workspace/demos/qc-afqmc/measure.sh --smoke)
sbatch --dependency=afterok:$measurement --kill-on-invalid-dep=yes \
  /workspace/demos/qc-afqmc/propagate.sh "results/$measurement"
```

The measurement log lists the quantum task ARNs, and `summary.json` records the
device. The smoke workload sends four SV1 tasks of 16 shots.

### Tasks and cost

Core submits all shadow circuits of a measurement as one QDMI job. Devices that
support Amazon Braket program sets run such a job as one quantum task, which
avoids a per-task fee for every circuit. SV1 and DM1 do not, so each circuit is
its own task. The QPUs in the pinned catalogue accept at most 100 programs per
set; AQT also caps a set at 10,000 shots, and IonQ requires at least 100 shots
per program, more than `--smoke` uses. When a device declines a job, Core asks
it, without submitting, for the largest accepted program count and splits the
job into the fewest near-equal program sets. The default workload's 128 shadows
become two QPU tasks of 64 circuits each.

## Target checks

Pull-request CI needs no credentials and executes only on DDSIM. The scheduled
`Provider targets` workflow checks that Core still compiles for each live
digital device without submitting anything to it:

1. Open the device, which reads its metadata: sites, couplings, native
   operations, and program formats.
2. Compile an asymmetric circuit to the exact payload that submission would
   send.
3. Run that payload on DDSIM, or the same target-native program as Base Profile
   QIR when DDSIM cannot read the format, and check the decoded counts.

Each week, or on demand, the workflow checks IQM Emerald, Garnet, and Sirius;
IBM Aachen and Berlin; and on Amazon Braket, AQT Ibex Q1, IonQ Forte 1, IQM
Emerald and Garnet, Rigetti Cepheus-1-108Q, and the SV1 simulator. A failing
device does not stop the others. The workflow reads these settings from the
`provider-targets` environment:

| Provider      | Secrets                                           | Variables             |
| ------------- | ------------------------------------------------- | --------------------- |
| IQM           | `IQM_TOKEN`                                       |                       |
| IBM           | `IBM_QUANTUM_API_KEY`, `IBM_QUANTUM_INSTANCE_CRN` |                       |
| Amazon Braket |                                                   | `AWS_BRAKET_ROLE_ARN` |

Amazon Braket uses short-lived credentials from GitHub OIDC instead of a stored
access key. Trust GitHub's OIDC provider for the role only from this
repository's `provider-targets` environment, using the subject format that
`gh api repos/OWNER/REPO/actions/oidc/customization/sub` reports; allow only
`braket:GetDevice`, and deny `braket:CreateQuantumTask`, `braket:CreateJob`, and
S3 writes. Each device entry carries its own region. IQM and IBM credentials
cannot be limited to metadata, so the guarantee there is that the check never
submits. These providers bill submitted work, not metadata reads. A failed run
can mean a provider outage or changed calibration rather than a Core regression;
provider transport is tested in each provider's repository.

## Device selection and access

For QC-AFQMC, the allocated HRES name selects the registered QDMI device before
compilation. The application compiles for and executes on that same opened
device.
