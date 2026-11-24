[![CI](https://img.shields.io/github/actions/workflow/status/munich-quantum-software/orchestrator/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/munich-quantum-software/orchestrator/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/readthedocs/mqsc-orchestrator?logo=readthedocs&style=flat-square)](https://mqsc-orchestrator.readthedocs.io/en/latest/)
![Platform](https://img.shields.io/badge/deployment-Linux-blue?style=flat-square)
[![License](https://img.shields.io/badge/license-Apache--2.0%20WITH%20LLVM--exception-blue?style=flat-square)](LICENSE)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/_static/orchestrator-dark.svg">
    <img src="docs/_static/orchestrator-light.svg" width="760" alt="MQSC Orchestrator">
  </picture>
</p>

# MQSC Orchestrator

**Bring quantum computing into the flow of an HPC application.**

A useful quantum calculation rarely stands alone. Classical computers prepare
its input, a quantum processor contributes measurements, and classical workers
turn those measurements into a scientific result. The MQSC Orchestrator brings
these stages together in a deployable reference system.

Write applications in Qiskit or PennyLane, compile with the MQT Compiler
Collection, and reach devices through QDMI. Slurm 26.11.0 schedules access to
quantum devices through hierarchical resources (HRES). Our main showcase,
**QC-AFQMC**, follows this journey from a small molecular problem to quantum
measurements and distributed classical propagation.

Start with DDSIM and explore the whole workflow without a cloud account. Connect
hardware when you are ready, keeping the compilation target, execution device,
and results visible at every step. This is an integration of the MQSC stack,
with deployment, accounting, and reproducible checks in one place.

<p align="center">
  <a href="https://mqsc-orchestrator.readthedocs.io/en/latest/">
  <img width=30% src="https://img.shields.io/badge/documentation-blue?style=for-the-badge&logo=read%20the%20docs" alt="Documentation" />
  </a>
</p>

## Start locally

Use a Linux Docker engine with cgroup v2, rootful privileged containers, and
Docker Compose. On Apple Silicon, use Docker Desktop’s native Linux ARM64 VM
following the
[macOS setup](https://mqsc-orchestrator.readthedocs.io/en/latest/deployment.html#apple-silicon-development-and-demonstrations).
Allocate at least 8 CPUs and 24 GiB RAM for the compiler build and scientific
environment. The containers share host resources; they are not a multi-tenant
security boundary.

```bash
git clone --recurse-submodules https://github.com/munich-quantum-software/orchestrator.git
cd orchestrator
sh deploy/slurm/prepare.sh
docker compose -f deploy/slurm/compose.yml up --build -d --wait
docker compose -f deploy/slurm/compose.yml exec --user 10000:10000 login bash --login
```

Spack builds the pinned Slurm, Core, and QDMI provider sources; uv locks the
scientific Python environment. No Core checkout or cloud credentials are needed.
The shared application checkout is `/workspace`, the installed environment is
`/opt/venv`, and shared writable results are `/jobs`.

Run the complete isolated acceptance test from the host:

```bash
uvx nox -s integration
```

It exercises HRES capacity, availability, placement, accounting, serialized
provider formats on DDSIM, both frontends, and dependent QC-AFQMC jobs. It
removes only its own test cluster.

## Documentation

Explore the
[documentation](https://mqsc-orchestrator.readthedocs.io/en/latest/), starting
with
[deployment](https://mqsc-orchestrator.readthedocs.io/en/latest/deployment.html),
[architecture](https://mqsc-orchestrator.readthedocs.io/en/latest/architecture.html),
[QC-AFQMC](https://mqsc-orchestrator.readthedocs.io/en/latest/afqmc.html),
[providers](https://mqsc-orchestrator.readthedocs.io/en/latest/providers.html),
and
[validation](https://mqsc-orchestrator.readthedocs.io/en/latest/validation.html).

## Contributing

The
[development guide](https://mqsc-orchestrator.readthedocs.io/en/latest/development.html)
covers uv, pre-commit, tests, and documentation. [CHANGELOG.md](CHANGELOG.md)
records changes and human contributors.

## License

The MQSC Orchestrator is licensed under **Apache-2.0 WITH LLVM-exception**. See
[LICENSE](LICENSE) for the terms.
