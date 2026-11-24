# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""HRES-capable Slurm with Lua and YAML discovery enabled."""

from spack.package import depends_on, version
from spack_repo.builtin.packages.slurm.package import Slurm as BaseSlurm


class Slurm(BaseSlurm):
    """Slurm with the HRES Lua plugin and per-node layer reporting."""

    git = "https://github.com/SchedMD/slurm.git"
    version("26-11-0-1", commit="7a94f2a5580b4e0f5e99b8228db53cd6763302e1")
    depends_on("lua@5.4:")
    depends_on("libyaml")

    def configure_args(self) -> list[str]:
        """Return flags that install service units in the reference image."""
        args = [arg for arg in super().configure_args() if not arg.startswith(("--with-ssl=", "--with-zlib="))]
        return [*args, f"--with-systemdsystemunitdir={self.prefix.lib}/systemd/system"]
