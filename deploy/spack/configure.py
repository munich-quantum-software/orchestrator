# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Register image dependencies that Spack cannot discover automatically."""

from __future__ import annotations

import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
packages = {
    "python": {
        "buildable": False,
        "externals": [
            {
                "spec": f"python@{python_version}",
                "prefix": sys.base_prefix,
            }
        ],
    },
    "mqsc-mlir-sdk": {"buildable": False, "externals": [{"spec": "mqsc-mlir-sdk@23.1.4", "prefix": "/opt/llvm"}]},
}
for name in ("pip", "scikit-build-core", "nanobind", "vcs-versioning"):
    packages["py-" + name] = {
        "buildable": False,
        "externals": [{"spec": f"py-{name}@{version(name)} ^python@{python_version}", "prefix": sys.prefix}],
    }
# These Ubuntu development libraries are already present in the reference image.
for name, deb in {
    "dbus": "libdbus-1-dev",
    "glib": "libglib2.0-dev",
    "hwloc": "libhwloc-dev",
    "json-c": "libjson-c-dev",
    "lua": "liblua5.4-dev",
    "mariadb": "libmariadb-dev",
    "munge": "libmunge-dev",
    "pmix": "libpmix-dev",
    "readline": "libreadline-dev",
    "libyaml": "libyaml-dev",
    "lz4": "liblz4-dev",
    "zlib": "zlib1g-dev",
    "pkgconf": "pkgconf",
}.items():
    output = subprocess.check_output(  # ruff: ignore[subprocess-without-shell-equals-true] -- Fixed package inventory, no shell.
        ["/usr/bin/dpkg-query", "-W", "-f=${Version}", deb],
        text=True,
    )
    installed = output.strip().split(":")[-1].split("-")[0].split("+")[0]
    if name == "pmix":
        installed = subprocess.check_output(["/usr/bin/pkg-config", "--modversion", "pmix"], text=True).strip()
    prefix = (
        subprocess.check_output(["/usr/bin/pkg-config", "--variable=prefix", "pmix"], text=True).strip()
        if name == "pmix"
        else "/usr"
    )
    packages[name] = {"buildable": False, "externals": [{"spec": f"{name}@{installed}", "prefix": prefix}]}
Path(__file__).with_name("externals.yaml").write_text(json.dumps({"packages": packages}, indent=2) + "\n")
