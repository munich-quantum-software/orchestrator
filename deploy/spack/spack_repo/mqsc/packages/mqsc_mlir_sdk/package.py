# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Portable MLIR SDK supplied by MQSC's setup-mlir distribution."""

from spack.package import version
from spack_repo.builtin.build_systems.bundle import BundlePackage


class MqscMlirSdk(BundlePackage):
    """External SDK, distinct from the host's LLVM compiler installation."""

    homepage = "https://github.com/munich-quantum-software/setup-mlir"
    version("23.1.4")
