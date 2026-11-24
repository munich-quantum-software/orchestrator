# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Build the AWS SDK clients that the Amazon Braket QDMI device links statically."""

import sys

from spack.package import depends_on, version
from spack_repo.builtin.build_systems.cmake import CMakePackage, generator


class AwsSdkCpp(CMakePackage):
    """AWS SDK for C++ with only the Braket, S3, and STS clients.

    A separate package keeps this long build cached when MQT Core changes.
    """

    homepage = "https://github.com/aws/aws-sdk-cpp"
    git = homepage + ".git"
    # The version the Amazon Braket QDMI device would otherwise fetch.
    version("1.11.936", tag="1.11.936", commit="124e4c4b4f0bd05e0500b6ffb517353d831a42ab", submodules=True)
    generator("ninja")
    depends_on("cmake@3.24:", type="build")
    depends_on("ninja", type="build")
    depends_on("curl")
    depends_on("openssl")
    depends_on("zlib-api")
    depends_on("c", type="build")
    depends_on("cxx", type="build")

    def cmake_args(self) -> list[str]:
        """Return the settings of the device's in-tree SDK build.

        Returns:
            CMake definitions for a static, position-independent client build.
        """
        return [
            self.define("BUILD_ONLY", "braket;s3;sts"),
            self.define("BUILD_SHARED_LIBS", value=False),
            self.define("CMAKE_POSITION_INDEPENDENT_CODE", value=True),
            self.define("CPP_STANDARD", "20"),
            self.define("ENABLE_TESTING", value=False),
            self.define("AUTORUN_UNIT_TESTS", value=False),
            self.define("AWS_SDK_WARNINGS_ARE_ERRORS", value=False),
            # Ubuntu 26.04's static libcrypto needs dependencies that s2n does not propagate.
            self.define("S2N_USE_CRYPTO_SHARED_LIBS", value=sys.platform == "linux"),
        ]
