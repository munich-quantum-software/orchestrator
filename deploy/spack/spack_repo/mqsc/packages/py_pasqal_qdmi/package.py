# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Build the Pasqal QDMI implementation from its reviewed source."""

from spack.package import depends_on, version
from spack_repo.builtin.build_systems.python import PythonPackage


class PyPasqalQdmi(PythonPackage):
    """Native Pasqal QDMI device and framework entry points."""

    homepage = "https://github.com/munich-quantum-software/pasqal-qdmi-device"
    git = homepage + ".git"
    version("1.2.1", commit="9d9f253bd3f6950c423eacea4b6487405bc6956d")
    depends_on("py-mqt-core@4.2.1:", type="run")
    depends_on("py-scikit-build-core@1.1:", type="build")
    depends_on("cmake@3.28:", type="build")
    depends_on("ninja", type="build")
    depends_on("curl", type=("build", "link"))
    depends_on("openssl", type=("build", "link"))
    depends_on("c", type="build")
    depends_on("cxx", type="build")
