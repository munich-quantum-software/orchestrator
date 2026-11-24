# Changelog

All notable changes to this project will be documented in this file.

The format is based on a mixture of [Keep a Changelog] and [Common Changelog].
This project adheres to [Semantic Versioning].

## Unreleased

### Changed

- ⬆️ Deploy [Slurm 26.11.0] with upstream fixes for job completion and
  reservation accounting. ([#16]) ([**@burgholzer**])
- ⬆️ Run Slurm accounting on MariaDB 13.0 and upgrade system tables when reusing
  an accounting volume. ([#10]) ([**@burgholzer**])

### Fixed

- 🐛 Fix compilation for paused Amazon Braket devices and for IQM Garnet when
  its topology exposes fewer qubits than advertised. The deployment uses Amazon
  Braket QDMI 1.4.3 and AWS SDK for C++ 1.11.936. ([#15]) ([**@burgholzer**])
- 🐛 Build Slurm and MQT Core for baseline x86-64 so the amd64 image can run on
  workers with different CPU features. ([#14], [#15]) ([**@burgholzer**])

## [0.1.0] - 2026-11-16

✨This is the initial release of the `MQSC Orchestrator` project.
([**@burgholzer**], [**@flowerthrower**])

<!-- Version links -->

[0.1.0]: https://github.com/munich-quantum-software/orchestrator/releases/tag/v0.1.0
[Slurm 26.11.0]: https://github.com/SchedMD/slurm/releases/tag/slurm-26-11-0-1

<!-- PR links -->

[#16]: https://github.com/munich-quantum-software/orchestrator/pull/16
[#15]: https://github.com/munich-quantum-software/orchestrator/pull/15
[#14]: https://github.com/munich-quantum-software/orchestrator/pull/14
[#10]: https://github.com/munich-quantum-software/orchestrator/pull/10

<!-- Contributor -->

[**@burgholzer**]: https://github.com/burgholzer
[**@flowerthrower**]: https://github.com/flowerthrower

<!-- General links -->

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Common Changelog]: https://common-changelog.org/
[Semantic Versioning]: https://semver.org/
