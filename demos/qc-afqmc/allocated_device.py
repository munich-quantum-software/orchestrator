# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Select a device from the running Slurm allocation, or an explicit local choice."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection


def resolve_device(requested: str | None, available: Collection[str], *, default: str | None = None) -> str:
    """Resolve one device, rejecting choices inconsistent with the allocation.

    The controller's allocation is selection evidence, not provider authorization.
    Local callers may supply a default; allocations never fall back to it.

    Returns:
        The available device ID selected for execution.

    Raises:
        ValueError: If the allocation or selection is invalid.
        FileNotFoundError: If ``scontrol`` is unavailable inside an allocation.
    """
    job_id = os.environ.get("SLURM_JOB_ID")
    if job_id is None:
        selected = requested or default
    else:
        if not job_id.isascii() or not job_id.isdecimal() or int(job_id) < 1:
            msg = "SLURM_JOB_ID must identify a running numeric Slurm job"
            raise ValueError(msg)
        scontrol = shutil.which("scontrol")
        if scontrol is None:
            msg = "scontrol is required to resolve the Slurm allocation"
            raise FileNotFoundError(msg)
        result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] -- Fixed command and validated numeric argument.
            [scontrol, "--json", "show", "job", job_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        response = json.loads(result.stdout)
        jobs = response.get("jobs", [])
        if response.get("errors") or len(jobs) != 1:
            msg = "Slurm did not return exactly one allocated job"
            raise ValueError(msg)
        job = jobs[0]
        if job.get("job_id") != int(job_id) or job.get("user_id") != os.getuid() or job.get("job_state") != ["RUNNING"]:
            msg = "The Slurm job must be running and owned by the current user"
            raise ValueError(msg)
        # Pinned Slurm serializes allocated HRES as name(layer*count,...):count.
        match = re.fullmatch(r"([^();:|,\[\]\s]+)\([^()]+\):[1-9][0-9]*", job.get("licenses_allocated") or "")
        if match is None:
            msg = "The Slurm allocation must grant exactly one QDMI HRES device"
            raise ValueError(msg)
        selected = match[1]
        if requested is not None and requested != selected:
            msg = f"Requested device {requested!r} differs from allocated device {selected!r}"
            raise ValueError(msg)
    if selected is None or selected not in available:
        msg = f"No available QDMI device matches {selected!r}"
        raise ValueError(msg)
    return selected
