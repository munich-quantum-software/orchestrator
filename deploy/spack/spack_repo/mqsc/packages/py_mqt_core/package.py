# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Source-built compiler, driver, simulators, and Python bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from spack.package import depends_on, version
from spack_repo.builtin.build_systems.python import PythonPackage

if TYPE_CHECKING:
    from llnl.util.environment import EnvironmentModifications


class PyMqtCore(PythonPackage):
    """MQT Core with its compiler and bundled QDMI devices."""

    homepage = "https://mqt.readthedocs.io/projects/core"
    git = "https://github.com/munich-quantum-toolkit/core.git"
    version("4.2.1", commit="020cb98c2acb4d62a15193f09e1ec6774460c867")
    depends_on("python@3.14:", type=("build", "run"))
    depends_on("py-scikit-build-core@1.1:", type="build")
    depends_on("py-vcs-versioning@2.3:", type="build")
    depends_on("py-nanobind@3.1:", type="build")
    depends_on("cmake@4.4.1:", type="build")
    depends_on("ninja", type="build")
    depends_on("mqsc-mlir-sdk@23.1.4", type=("build", "link"))
    depends_on("c", type="build")
    depends_on("cxx", type="build")

    @override
    def config_settings(self, _spec: object, _prefix: object) -> dict[str, str]:
        """Return upstream build settings for the deployment wheel."""
        return {"cmake.define.DEPLOY": "ON", "cmake.define.ENABLE_IPO": "ON", "cmake.define.CMAKE_LINKER_TYPE": "LLD"}

    def setup_build_environment(self, env: EnvironmentModifications) -> None:
        """Select the compiler SDK from this concrete environment."""
        env.set("MLIR_DIR", self.spec["mqsc-mlir-sdk"].prefix.lib.cmake.mlir)
        env.set("VCS_VERSIONING_PRETEND_VERSION_FOR_MQT_CORE", str(self.spec.version))
