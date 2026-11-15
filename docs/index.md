# MQSC Orchestrator

**One scientific workflow, across classical and quantum computers.**

Quantum computing becomes useful as part of a larger calculation. The MQSC
Orchestrator connects its stages: an application prepares a problem on classical
workers, compiles a quantum program for a chosen device, and carries the
measurements back into the next classical stage—all within a Slurm-managed
system.

Explore that journey through **QC-AFQMC**, our molecular-energy showcase. Begin
locally with DDSIM, inspect the generated results, then learn how the same
architecture connects to quantum providers through QDMI. Simulated execution and
hardware execution always have distinct identities.

The reference deployment brings together **Slurm HRES**, **MQT Core**, and
**QDMI devices**. Spack describes the native software environment, while uv
keeps the scientific Python application reproducible. These guides connect the
big picture to commands you can run and evidence you can inspect.

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Explore the architecture
:link: architecture
:link-type: doc

Follow an application from preparation to its reconstructed result.
:::

:::{grid-item-card} Run your first cluster
:link: deployment
:link-type: doc

Bring up the local reference system and execute through DDSIM.
:::

:::{grid-item-card} Meet QC-AFQMC
:link: afqmc
:link-type: doc

Connect quantum measurements to a molecular-energy calculation.
:::

:::{grid-item-card} Understand the evidence
:link: validation
:link-type: doc

See what the checks prove, and where live-provider validation begins.
:::

::::

```{toctree}
:hidden:
:maxdepth: 2

architecture
deployment
afqmc
providers
validation
operations
development
ai_usage
CHANGELOG
```
