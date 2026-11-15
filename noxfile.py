# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

# /// script
# requires-python = ">=3.14"
# dependencies = ["nox>=2026.10.20"]
# ///

"""Development sessions for the deployment and its documentation."""

from __future__ import annotations

import nox

nox.needs_version = ">=2026.10.20"
nox.options.default_venv_backend = "uv"


@nox.session(python="3.14", reuse_venv=True, default=True)
def lint(session: nox.Session) -> None:
    """Check all maintained sources."""
    session.install("prek>=0.5.7")
    session.run("prek", "run", "--all-files", *session.posargs)


@nox.session(python="3.14", reuse_venv=True)
def tests(session: nox.Session) -> None:
    """Exercise host contracts without provider credentials."""
    session.install("--group", "test")
    session.run("pytest", *session.posargs)


@nox.session(python="3.14", reuse_venv=True)
def docs(session: nox.Session) -> None:
    """Build the documentation."""
    session.install("--group", "docs")
    session.run("sphinx-build", "-W", "--keep-going", "-b", "html", "docs", "build/docs", *session.posargs)


@nox.session(venv_backend="none")
def integration(session: nox.Session) -> None:
    """Run the deployed Slurm/HRES and QC-AFQMC workflows."""
    session.run("uv", "run", "--script", "tests/slurm/run_integration.py")
