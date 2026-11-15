# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Check failure and resource bounds without starting a Slurm cluster."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

pytestmark = pytest.mark.slurm

if sys.platform == "win32":
    pytest.skip("the Slurm fixture requires a POSIX Docker host", allow_module_level=True)


def load_script(script: Path) -> ModuleType:
    """Load an independent script invocation without creating its resources.

    Returns:
        The isolated script module.
    """
    spec = importlib.util.spec_from_file_location(script.stem, script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner() -> ModuleType:
    """Load the Slurm integration runner.

    Returns:
        The runner module from the source checkout.
    """
    return load_script(Path(__file__).parent / "slurm" / "run_integration.py")


def test_prepare_keeps_private_key_and_preserves_existing_cluster(runner: ModuleType, tmp_path: Path) -> None:
    """Create usable shared files without overwriting a cluster's authentication."""
    runtime = tmp_path / "cluster"
    command = ("sh", str(runner.CLUSTER / "prepare.sh"), str(runtime))
    runner.run(command)
    key = runtime / "munge.key"
    assert len(key.read_bytes()) == 1024
    assert key.stat().st_mode & 0o777 == 0o600
    assert (runtime / "slurm.conf").stat().st_mode & 0o777 == 0o644
    original = key.read_bytes()
    assert runner.run(command, check=False).returncode != 0
    assert key.read_bytes() == original


def test_timeout_kills_children_holding_output_pipes(runner: ModuleType, tmp_path: Path) -> None:
    """A Compose-like grandchild must not defeat the command deadline."""
    marker = tmp_path / "started"
    program = (
        "import subprocess, sys, time; from pathlib import Path; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
        f"Path({str(marker)!r}).touch(); time.sleep(30)"
    )
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run((sys.executable, "-c", program), timeout=1)
    assert marker.exists()
    assert time.monotonic() - started < 5


def test_diagnostic_timeout_is_best_effort(runner: ModuleType) -> None:
    """Bound failed diagnostics without replacing the original test failure."""
    result = runner.run((sys.executable, "-c", "import time; time.sleep(30)"), check=False, timeout=0.1)
    assert result.returncode == 124


def test_command_failure_keeps_output(runner: ModuleType) -> None:
    """Retain command diagnostics when a checked command fails."""
    with pytest.raises(subprocess.CalledProcessError) as error:
        runner.run((sys.executable, "-c", "import sys; print('reason'); sys.exit(7)"))
    assert error.value.returncode == 7
    assert "reason" in error.value.output


@pytest.mark.parametrize("record", ["FAILED|1:0", "COMPLETED|0:9", "CANCELLED|0:0", "TIMEOUT|0:0"])
def test_failed_accounting_record_is_not_success(
    runner: ModuleType, monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """A result file cannot hide a failed job or termination by signal."""
    monkeypatch.setattr(runner, "job", lambda *args: subprocess.CompletedProcess(args, 0, record, ""))
    with pytest.raises(AssertionError, match="Slurm job 42 ended"):
        runner.job_finished("42")


def test_diagnostic_failure_still_tears_down(
    runner: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable diagnostic service must not orphan a failed cluster."""
    monkeypatch.setattr(runner, "RUNTIME", tmp_path / "runtime")
    monkeypatch.setattr(runner, "run", lambda *args: subprocess.CompletedProcess(args, 0, "2", ""))
    commands = []

    def compose(*args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        if args[0] == "up":
            msg = "startup failure"
            raise RuntimeError(msg)
        return subprocess.CompletedProcess(args, 0, "", "")

    def diagnostics() -> None:
        msg = "diagnostics"
        raise subprocess.TimeoutExpired(msg, 30)

    monkeypatch.setattr(runner, "compose", compose)
    monkeypatch.setattr(runner, "print_diagnostics", diagnostics)
    with pytest.raises(RuntimeError, match="startup failure"):
        runner.main()
    assert commands[-1][0] == "down"


def test_result_written_during_accounting_query(
    runner: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read the shared output after accounting reports completion."""
    (tmp_path / "jobs").mkdir()
    monkeypatch.setattr(runner, "RUNTIME", tmp_path)

    def finished(_job_id: str) -> bool:
        (tmp_path / "jobs" / "sc-42.json").write_text("{}", encoding="utf-8")
        return True

    monkeypatch.setattr(runner, "job_finished", finished)
    runner.wait_for_result("sc", "42", "SC output")
