# From application to result

The architecture follows the life of a scientific calculation: prepare a
problem, compile its quantum part, execute it, then continue with classical
work. Each layer has a clear role, so the same application can explore an ideal
simulator or a configured hardware target without losing track of what ran.

## The application journey

QC-AFQMC gives each layer a concrete job. The application prepares measurement
circuits and requests a quantum resource from Slurm. HRES admits the job when
that resource is available. Inside the allocation, MQT Core compiles the
circuits for the selected device, submits them through QDMI, and reconstructs
the measurements. A dependent Slurm job then uses those measurements to
propagate classical walkers across the compute nodes.

The layers have separate responsibilities:

- **Qiskit and PennyLane** express the quantum computation.
- **Slurm HRES** controls local resource admission and allocation on quantum
  access nodes (QANs).
- **The MQT Compiler Collection** compiles against the allocated device's model.
- **Core's QDMI driver and SDK adapters** submit programs and reconstruct
  framework results.
- **QDMI device implementations** handle discovery, validation, provider
  transport, and device-specific results.

An HRES allocation provides local access to a configured device; remote QPU
capacity and provider authorization remain with the provider. Compilation runs
within the allocation and above the provider interface.

## Deployment roles

| Role               | Responsibility                                  |
| ------------------ | ----------------------------------------------- |
| Login node         | Submission, application files, user credentials |
| Controller         | HRES resource availability and scheduling       |
| QANs               | Compilation and QDMI execution                  |
| Classical nodes    | Classical preprocessing and continuation        |
| SlurmDBD/MariaDB   | Persistent accounting                           |

All roles share `/jobs`. Classical nodes use an internal network; QANs have
outbound access. The local containers share one host and do not demonstrate
cluster scaling.

## Compilation and execution identity

An application compiles for and executes on the device selected by its HRES
allocation. Its results record the device. Do not silently choose another target
when discovery or execution fails.
