# Developing the MQSC Orchestrator

The MQSC Orchestrator connects applications, scheduling, compilation, and
quantum execution in one deployment. Contributions should make that workflow
easier to operate and verify. Compiler and adapter behavior belongs in MQT Core;
provider transport belongs in the device repositories.

## One workspace, clear responsibilities

Use uv 0.13.5 or newer. The application and repository tooling use Python 3.14,
without an upper Python-version bound. The root is a virtual uv workspace;
`demos/qc-afqmc` is its non-packaged application member. There is no root wheel
to build or publish.

```bash
uv sync --locked --only-group dev
uv tool install prek
prek install
uvx nox -s lint tests docs
```

Modern nox reads its inline script metadata itself. Standalone administration
scripts also use PEP 723. The default development groups contain only tooling;
they do not pull in MPI or the chemistry stack. For local application work, use
`uv sync --locked --package qc-afqmc`. Full integration uses the source-built
components inside the deployment image.

Spack owns the native component graph in `deploy/spack`: Slurm, Core, the QDMI
providers, and the AWS SDK clients they link. Spack discovers the image
compiler; `configure.py` registers the Python, portable MQSC MLIR SDK, and
preinstalled libraries that require explicit externals. Spack concretizes the
graph inside the image build. uv owns the scientific Python application and its
development tools in the root `uv.lock`. The image consumes that lock directly;
no requirements export is maintained. Cloud submission uses the native QDMI
providers. Site Spack interpreters must use Python 3.13 or newer. The portable
SDK is a separate distribution from the host compiler, so its version is tracked
independently.

After changing Python dependencies, run `uv lock`. Supply meaningful lower
bounds and check `uv lock --resolution lowest-direct` in a disposable checkout
before adopting them. Update native source pins in the Spack recipes, then run
the deployed acceptance suite. Never let a local `uv sync` replace the
source-built Core inside an allocation.

## Checks that follow the workflow

Pre-commit uses prek and the same families of checks as MQT Core: Ruff with all
rules enabled, Python project formatting and schema checks, typos, ShellCheck,
Prettier, rumdl, license headers, workflow schemas, and zizmor. The official ty
hook checks host tools and tests in the development environment; deployed
application behavior is covered by integration tests. Keep narrowly justified
Ruff exceptions beside the affected contract. Address every zizmor diagnostic;
never use `pull_request_target`.

```bash
uvx nox -s integration
```

This creates an isolated cluster and tests admission, scheduling, serialized
programs, reconstructed results, and dependent classical work. Keep asymmetric
examples and independent numerical expectations: they make mistakes in bit order
and job identity observable. Host tests alone cannot establish these
cross-component properties.

Build docs with `uvx nox -s docs`, then inspect the rendered pages, keyboard
interaction, console, and network with Chrome DevTools. Documentation examples
must run without provider credentials.

CI runs the host checks and the Slurm integration suite on every push and pull
request without credentials; its jobs run only in the public repository. It
builds the cluster image with a GitHub Actions layer cache and hands it to the
runner through `MQSC_ORCHESTRATOR_IMAGE`; a cold build compiles Slurm, Core, and
the providers from source.

## Contributions and releases

Follow the PR template and record user-visible changes in `CHANGELOG.md`, with
source links and human contributor credits. Preserve source copyrights and
required license notices. Keep `AGENTS.md` in step with repository decisions.
Shared template synchronization is currently disabled; the MQT-style files are
maintained locally until a deployment-oriented template profile fits them.

Release drafting prepares notes without publishing. See [AI usage](ai_usage.md)
for contribution guidelines. DDSIM runs do not qualify remote providers or a
multi-user site.
