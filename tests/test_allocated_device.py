# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Selection follows the allocated device rather than requested alternatives."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "allocated_device", Path(__file__).parents[1] / "demos/qc-afqmc/allocated_device.py"
)
assert spec is not None
assert spec.loader is not None
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)

DDSIM = "mqt.ddsim.default"
SC = "mqt.sc.default"


@pytest.fixture
def allocation(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Provide the pinned Slurm JSON fields without requiring a cluster."""
    monkeypatch.setenv("SLURM_JOB_ID", "42")
    monkeypatch.setenv("SLURM_JOB_LICENSES", f"{SC}:1|{DDSIM}:1")
    monkeypatch.setattr(selection.shutil, "which", lambda _: "/opt/slurm/bin/scontrol")
    job = {
        "job_id": 42,
        "user_id": os.getuid(),
        "job_state": ["RUNNING"],
        "licenses_allocated": f"{DDSIM}(quantum*1):1",
    }

    def query(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["/opt/slurm/bin/scontrol", "--json", "show", "job", "42"]
        assert kwargs["timeout"] == 10
        return subprocess.CompletedProcess(command, 0, json.dumps({"jobs": [job], "errors": []}))

    monkeypatch.setattr(selection.subprocess, "run", query)
    return job


def test_granted_device_overrides_local_default(allocation: dict) -> None:
    """Requested alternatives and local defaults cannot override the grant."""
    assert allocation["licenses_allocated"].startswith(DDSIM)
    assert selection.resolve_device(None, [DDSIM, SC], default=SC) == DDSIM
    with pytest.raises(ValueError, match="differs from allocated"):
        selection.resolve_device(SC, [DDSIM, SC])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_id", 43),
        ("user_id", -1),
        ("job_state", ["PENDING"]),
        ("licenses_allocated", None),
        ("licenses_allocated", f"{DDSIM}:1"),
        ("licenses_allocated", f"{DDSIM}(quantum*1):1;{SC}(quantum*1):1"),
        ("licenses_allocated", f"{DDSIM}(quantum*1):1|{SC}(quantum*1):1"),
        ("licenses_allocated", f"{DDSIM}(quantum*1):0"),
        ("licenses_allocated", "unknown(quantum*1):1"),
    ],
)
def test_invalid_grant_fails_closed(allocation: dict, field: str, value: object) -> None:
    """Missing, foreign, inactive, ambiguous, and unavailable grants cannot default."""
    allocation[field] = value
    with pytest.raises(ValueError, match=r"Slurm|No available"):
        selection.resolve_device(None, [DDSIM, SC], default=DDSIM)


def test_local_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local use keeps explicit device selection and the demo default."""
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    assert selection.resolve_device(None, [DDSIM], default=DDSIM) == DDSIM
    assert selection.resolve_device(SC, [DDSIM, SC]) == SC
    with pytest.raises(ValueError, match="No available"):
        selection.resolve_device("unknown", [DDSIM])


def test_controller_failure_never_uses_default(allocation: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed controller lookup cannot turn an allocation into local execution."""
    assert allocation["job_id"] == 42

    def unavailable(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        msg = "scontrol"
        raise subprocess.TimeoutExpired(msg, 10)

    monkeypatch.setattr(selection.subprocess, "run", unavailable)
    with pytest.raises(subprocess.TimeoutExpired):
        selection.resolve_device(None, [DDSIM], default=DDSIM)
