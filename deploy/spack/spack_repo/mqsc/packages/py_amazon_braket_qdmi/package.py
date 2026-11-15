# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Build the Amazon Braket QDMI implementation from its reviewed source."""

from typing import override

from spack.package import depends_on, version
from spack_repo.builtin.build_systems.python import PythonPackage


class PyAmazonBraketQdmi(PythonPackage):
    """Native Amazon Braket QDMI device and framework entry points."""

    homepage = "https://github.com/munich-quantum-software/amazon-braket-qdmi-device"
    git = homepage + ".git"
    version("1.4.1", commit="f450e29fa69ee81e7a16e227b73ae73651bb3543")
    depends_on("py-mqt-core@4.2.1:", type="run")
    depends_on("py-scikit-build-core@1.1:", type="build")
    depends_on("py-vcs-versioning@2.3:", type="build")
    depends_on("cmake@3.28:", type="build")
    depends_on("ninja", type="build")
    depends_on("aws-sdk-cpp@1.11.908", type=("build", "link"))
    depends_on("curl", type=("build", "link"))
    depends_on("openssl", type=("build", "link"))
    depends_on("zlib-api", type=("build", "link"))
    depends_on("c", type="build")
    depends_on("cxx", type="build")

    @override
    def config_settings(self, spec: object, _prefix: object) -> dict[str, str]:
        """Link the prebuilt SDK and fail instead of downloading another copy.

        Returns:
            Build settings for the deployment wheel.
        """
        return {
            "cmake.define.AWSSDK_ROOT": str(spec["aws-sdk-cpp"].prefix),
            "cmake.define.CMAKE_REQUIRE_FIND_PACKAGE_AWSSDK": "ON",
        }
