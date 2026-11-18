#!/usr/bin/env -S uv run --script
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

"""Run the real Slurm admission and QDMI execution integration test."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "slurm"
CLUSTER = ROOT / "deploy" / "slurm"
RUNTIME = ROOT / "build" / "slurm-tests" / uuid.uuid4().hex
NODES: list[str] = []
QANS = ["qan1", "qan2"]
COMPUTE_NODES = 2  # The node scale in deploy/slurm/compose.yml.
# Provider devices are registered as HRES but disabled until a site adds credentials.
PROVIDER_DEVICES = [device["id"] for device in json.loads((CLUSTER / "qdmi.json").read_text())["qdmi"]["devices"]]
COMPOSE = (
    "docker",
    "compose",
    "--project-name",
    f"mqsc-orchestrator-{RUNTIME.name}",
    "--file",
    str(CLUSTER / "compose.yml"),
    "--file",
    str(FIXTURE / "compose.yml"),
)
TIMEOUT = 120.0
COMMAND_TIMEOUT = 30.0
LOGGER = logging.getLogger(__name__)


def _communicate(process: subprocess.Popen[str], timeout: float) -> tuple[str, str]:
    """Collect output, killing the whole command group on interruption.

    Returns:
        The command's stdout and stderr.
    """
    try:
        return process.communicate(timeout=timeout)
    except BaseException:
        # Docker can spawn a Compose child holding our output pipes.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise


def run(
    command: Sequence[str],
    *,
    check: bool = True,
    timeout: float = COMMAND_TIMEOUT,
    capture_output: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and retain output for assertions and diagnostics."""
    LOGGER.info("+ %s", shlex.join(command))
    try:
        with subprocess.Popen(  # ruff: ignore[subprocess-without-shell-equals-true] - Argument vectors are constructed by this local runner.
            command,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            text=True,
            env=env,
            start_new_session=True,
        ) as process:
            stdout, stderr = _communicate(process, timeout)
            result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        if check:
            raise
        LOGGER.warning("Command failed: %s", error)
        return subprocess.CompletedProcess(
            command, 124 if isinstance(error, subprocess.TimeoutExpired) else 127, "", str(error)
        )
    if result.stdout:
        LOGGER.info("%s", result.stdout.rstrip())
    if result.stderr:
        LOGGER.info("%s", result.stderr.rstrip())
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)
    return result


def compose(
    *arguments: str,
    check: bool = True,
    timeout: float = COMMAND_TIMEOUT,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run Docker Compose for this invocation's isolated project and artifacts."""
    return run(
        (*COMPOSE, *arguments),
        check=check,
        timeout=timeout,
        capture_output=capture_output,
        env={
            **os.environ,
            "MQSC_ORCHESTRATOR_ROOT": str(ROOT),
            "MQSC_ORCHESTRATOR_RUNTIME": str(RUNTIME),
        },
    )


def controller(*command: str, check: bool = True, timeout: float = COMMAND_TIMEOUT) -> subprocess.CompletedProcess[str]:
    """Run an administrative command on the controller."""
    return compose("exec", "-T", "controller", *command, check=check, timeout=timeout)


def job(*command: str, check: bool = True, timeout: float = COMMAND_TIMEOUT) -> subprocess.CompletedProcess[str]:
    """Submit workloads from the login node as an ordinary cluster user."""
    return compose(
        "exec",
        "-T",
        "--user",
        "10000:10000",
        "login",
        "env",
        *command,
        check=check,
        timeout=timeout,
    )


def wait_for(description: str, predicate: Callable[[], bool], timeout: float = TIMEOUT) -> None:
    """Poll a condition and report a precise timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.5)
    msg = f"Timed out while waiting for {description}"
    raise TimeoutError(msg)


def node_record(node: str) -> str:
    """Return one machine-readable Slurm node record."""
    return controller("scontrol", "show", "node", node, "--oneliner").stdout.strip()


def node_layers(node: str) -> set[tuple[str, str]]:
    """Return the HRES layers that contain a node."""
    (record,) = json.loads(controller("scontrol", "--json", "show", "node", node).stdout)["nodes"]
    return {(layer["hres_name"], layer["layer_name"]) for layer in record.get("hres", [])}


def node_is_idle(node: str, cpus: int, memory: int) -> bool:
    """Return whether a compute node has registered and is idle."""
    record = node_record(node)
    return "State=IDLE" in record and f"CPUTot={cpus} " in record and f"RealMemory={memory} " in record


def job_record(job_id: str) -> tuple[str, str, str] | None:
    """Return state, reason, and node for an active job."""
    output = controller("squeue", "--noheader", "--jobs", job_id, "--format=%T|%R|%N").stdout.strip()
    if not output:
        return None
    state, reason, node = output.split("|", maxsplit=2)
    # squeue renders a pending reason in parentheses even with a custom format.
    if reason.startswith("(") and reason.endswith(")"):
        reason = reason[1:-1]
    return state, reason, node


def job_matches(job_id: str, state: str, *, node: str | None = None, reason: str | None = None) -> bool:
    """Return whether an active job has the requested observable state."""
    record = job_record(job_id)
    if record is None:
        return False
    actual_state, actual_reason, actual_node = record
    return (
        actual_state == state and (node is None or actual_node == node) and (reason is None or actual_reason == reason)
    )


def job_finished(job_id: str) -> bool:
    """Require successful completion recorded by Slurm accounting."""
    output = job("sacct", "-X", "--noheader", "--parsable2", "--jobs", job_id, "--format=State,ExitCode").stdout.strip()
    if not output:
        return False
    state, exit_code = output.split("|")
    if state in {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING", "SUSPENDED"}:
        return False
    if (state, exit_code) != ("COMPLETED", "0:0"):
        msg = f"Slurm job {job_id} ended with {state}, ExitCode={exit_code}"
        raise AssertionError(msg)
    return True


def submit(script: str, license_expression: str, *, node: str | None = None, hold: bool = False) -> str:
    """Submit one single-processor batch job and return its numeric ID."""
    command = [
        "sbatch",
        "--parsable",
        "--nodes=1",
        "--ntasks=1",
        "--cpus-per-task=1",
        "--partition=quantum",
        "--time=5",
        f"--licenses={license_expression}",
        "--chdir=/workspace",
        "--output=/jobs/slurm-%j.out",
    ]
    if node is not None:
        command.append(f"--nodelist={node}")
    payload = ["python3", f"/workspace/tests/slurm/{script}"]
    if hold:
        payload.append("--hold")
    command.extend(("--wrap", shlex.join(payload)))
    job_id = job(*command).stdout.strip().split(";", maxsplit=1)[0]
    if not job_id.isdecimal():
        msg = f"sbatch returned an invalid job ID: {job_id!r}"
        raise RuntimeError(msg)
    return job_id


def license_record(name: str) -> dict[str, str]:
    """Parse one `scontrol show lic` record."""
    output = controller("scontrol", "show", "lic", name, "--oneliner").stdout
    return dict(field.split("=", maxsplit=1) for field in output.split() if "=" in field)


def assert_license(name: str, *, total: int, used: int, free: int) -> None:
    """Require the exact static Slurm license counters."""
    record = license_record(name)
    expected = {"LicenseName": name, "Total": str(total), "Used": str(used), "Free": str(free)}
    if not expected.items() <= record.items():
        msg = f"Unexpected license record for {name}: {record}; expected {expected}"
        raise AssertionError(msg)


def load_result(kind: str, job_id: str) -> dict[str, Any]:
    """Load one batch-job result from the shared runtime directory."""
    return json.loads((RUNTIME / "jobs" / f"{kind}-{job_id}.json").read_text(encoding="utf-8"))


def wait_for_result(kind: str, job_id: str, description: str) -> None:
    """Wait for a workload result, reporting a completed job's missing output."""
    result_path = RUNTIME / "jobs" / f"{kind}-{job_id}.json"

    def result_exists_or_raise() -> bool:
        finished = job_finished(job_id)
        if result_path.exists():
            return True
        if not finished:
            return False
        output_path = RUNTIME / "jobs" / f"slurm-{job_id}.out"
        output = output_path.read_text(encoding="utf-8") if output_path.exists() else "<no batch output>"
        msg = f"Slurm job {job_id} completed without {result_path.name}:\n{output.rstrip()}"
        raise RuntimeError(msg)

    wait_for(description, result_exists_or_raise)


def assert_allocation(job_id: str, expected_node: str | None = None) -> None:
    """Check placement and the license received by a successful DDSIM workload."""
    result = load_result("ddsim", job_id)
    if expected_node is not None and result["node"] != expected_node:
        msg = f"Slurm job {job_id} ran on {result['node']}, expected {expected_node}"
        raise AssertionError(msg)
    if result["device_id"] != "mqt.ddsim.default":
        msg = f"The job resolved an unexpected allocated device: {result['device_id']}"
        raise AssertionError(msg)


def clean_runtime() -> None:
    """Create private artifacts and a Munge key for this invocation only."""
    run(("sh", str(CLUSTER / "prepare.sh"), str(RUNTIME)))


def print_diagnostics() -> None:
    """Print cluster state without hiding the original test failure."""
    controller("squeue", "--all", check=False, timeout=5)
    controller(
        "sacct",
        "--allusers",
        "--starttime=now-1hour",
        "--format=JobID,State,ExitCode,Reason,NodeList",
        check=False,
        timeout=5,
    )
    controller("scontrol", "show", "node", check=False, timeout=5)
    controller("scontrol", "show", "lic", check=False, timeout=5)
    for output in sorted((RUNTIME / "jobs").glob("slurm-*.out")):
        LOGGER.info("=== %s ===", output.name)
        try:
            LOGGER.info("%s", output.read_text(encoding="utf-8").rstrip())
        except OSError as error:
            LOGGER.info("Could not read %s: %s", output, error)
    for service, index, units in [
        ("controller", 1, ("munge.service", "slurmctld.service")),
        ("accounting", 1, ("slurmdbd.service", "slurm-accounting.service")),
        *((qan, 1, ("slurmd.service",)) for qan in QANS),
        *(("node", index, ("munge.service", "slurmd.service")) for index in range(1, len(NODES) + 1)),
    ]:
        prefix = ("exec", "-T", "--index", str(index), service)
        compose(*prefix, "systemctl", "status", "--no-pager", *units, check=False, timeout=5)
        compose(
            *prefix,
            "journalctl",
            "--no-pager",
            "--lines=100",
            *(argument for unit in units for argument in ("--unit", unit)),
            check=False,
            timeout=5,
        )
    compose("logs", "--no-color", check=False, timeout=5)


def test_core() -> None:
    """Verify admission and execution with the bundled DDSIM and SC devices."""
    assert_license("mqt.ddsim.default", total=2, used=0, free=2)
    assert_license("mqt.sc.default", total=1, used=0, free=1)

    first = submit("bell_job.py", "mqt.ddsim.default:1", node=QANS[0], hold=True)
    second = submit("bell_job.py", "mqt.ddsim.default:1", node=QANS[1], hold=True)
    wait_for_result("ddsim", first, "the first DDSIM Bell result")
    wait_for_result("ddsim", second, "the second DDSIM Bell result")
    wait_for("the first DDSIM job to hold on its node", lambda: job_matches(first, "RUNNING", node=QANS[0]))
    wait_for("the second DDSIM job to hold on its node", lambda: job_matches(second, "RUNNING", node=QANS[1]))
    if "CPUAlloc=1" not in node_record(QANS[0]) or "CPUAlloc=1" not in node_record(QANS[1]):
        msg = "Each held DDSIM job must leave processors free on its quantum access node"
        raise AssertionError(msg)

    third = submit("bell_job.py", "mqt.ddsim.default:1")
    wait_for(
        "the third DDSIM job to wait for its license",
        lambda: job_matches(third, "PENDING", node="", reason="ReqNodeNotAvail, May be reserved for other job"),
    )
    assert_license("mqt.ddsim.default", total=2, used=2, free=0)

    sc_job = submit("sc_job.py", "mqt.sc.default:1")
    wait_for_result("sc", sc_job, "the SC job to execute on a free CPU")
    wait_for("the SC job to complete", lambda: job_finished(sc_job))
    sc_result = load_result("sc", sc_job)
    if sc_result["node"] not in QANS or sc_result["device_id"] != "mqt.sc.default" or sc_result["qubits"] <= 0:
        msg = f"Unexpected SC job result: {sc_result}"
        raise AssertionError(msg)
    if not job_matches(first, "RUNNING", node=QANS[0]) or not job_matches(second, "RUNNING", node=QANS[1]):
        msg = "The SC job did not complete while both DDSIM licenses remained held"
        raise AssertionError(msg)

    configuration = RUNTIME / "qdmi.json"
    catalogue = configuration.read_text(encoding="utf-8")
    outage = json.loads(catalogue)
    outage["qdmi"]["devices"].append({"id": "mqt.ddsim.default", "enabled": False})
    configuration.write_text(json.dumps(outage), encoding="utf-8")
    controller("scontrol", "reconfigure")
    wait_for(
        "the failed QDMI probe to disable its HRES layer",
        lambda: license_record("mqt.ddsim.default")["DisableLayer"] == "true",
    )
    wait_for(
        "the controller to log why admission closed",
        lambda: (
            "hres_qdmi: mqt.ddsim.default admission closed: unregistered"
            in controller("journalctl", "--no-pager", "--unit", "slurmctld.service").stdout
        ),
    )
    # Every configured HRES keeps its single quantum layer on both QANs.
    expected_layers = {(name, "quantum") for name in ("mqt.ddsim.default", "mqt.sc.default", *PROVIDER_DEVICES)}
    for qan in QANS:
        wait_for(
            f"{qan} to retain every HRES layer after reconfiguration",
            lambda qan=qan: node_layers(qan) == expected_layers,
        )
    wait_for("the unaffected SC layer to recover", lambda: license_record("mqt.sc.default")["DisableLayer"] == "false")
    assert_license("mqt.ddsim.default", total=2, used=2, free=0)
    assert job_matches(first, "RUNNING")
    assert job_matches(second, "RUNNING")
    for job_id in (first, second):
        (RUNTIME / "jobs" / f"release-{job_id}").touch()
        wait_for(f"the released DDSIM job {job_id} to finish", lambda job_id=job_id: job_finished(job_id))
    assert_license("mqt.ddsim.default", total=2, used=0, free=2)
    job(
        "srun", "--immediate=5", "--time=1", "--partition=quantum", "--licenses=mqt.sc.default", "/bin/true", timeout=60
    )
    wait_for(
        "the disabled HRES to hold its pending job without nodes",
        lambda: job_matches(third, "PENDING", node="", reason="HRESDisabled"),
    )
    assert job("scontrol", "update", "HRESName=mqt.ddsim.default", "DisableHRES=false", check=False).returncode != 0

    configuration.write_text(catalogue, encoding="utf-8")
    wait_for_result("ddsim", third, "the pending DDSIM job to execute after recovery")
    wait_for("the third DDSIM job to finish", lambda: job_finished(third))
    assert_allocation(first, QANS[0])
    assert_allocation(second, QANS[1])
    assert_allocation(third)
    compose("up", "--detach", "--no-deps", "--force-recreate", "--wait", "accounting", timeout=120)
    accounting = job(
        "sacct",
        "-X",
        "--noheader",
        "--parsable2",
        "--jobs",
        third,
        "--format=User,Account,Partition,AllocTRES%200",
    ).stdout.strip()
    assert accounting.startswith("mqt-dev|research|quantum|"), accounting
    assert "license/mqt.ddsim.default=1" in accounting, accounting
    assert_license("mqt.ddsim.default", total=2, used=0, free=2)
    assert license_record("mqt.ddsim.default")["Reserved"] == "0"

    LOGGER.info(
        "Slurm enforced license capacity, kept unavailable-device jobs pending without allocating nodes, "
        "and resumed the pending Bell job after a successful health check."
    )


def test_applications() -> None:
    """Run serialized frontend checks and a dependent two-node AFQMC workflow."""
    mismatch = job(
        "srun",
        "--partition=quantum",
        "--licenses=mqt.ddsim.default:1",
        "--time=2",
        "python",
        "/workspace/demos/qc-afqmc/run.py",
        "--stage",
        "measure",
        "--smoke",
        "--device",
        "mqt.sc.default",
        "--output",
        "/jobs/afqmc-mismatch",
        check=False,
        timeout=150,
    )
    assert mismatch.returncode != 0
    assert "differs from allocated device" in mismatch.stderr
    assert not (RUNTIME / "jobs/afqmc-mismatch/measurements.json").exists()
    job(
        "sbatch",
        "--wait",
        "--partition=quantum",
        "--licenses=mqt.ddsim.default:1",
        "--time=10",
        "--mem=8G",
        "--output=/jobs/formats.log",
        "--wrap",
        "srun python /workspace/scripts/check_workflows.py && "
        "srun python /workspace/scripts/check_provider_targets.py mqt.ddsim.default && "
        "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 srun python /workspace/tests/slurm/check_afqmc.py",
        timeout=660,
    )
    measurement = job(
        "sbatch",
        "--parsable",
        "--partition=quantum",
        "--licenses=mqt.ddsim.default:1",
        "--time=10",
        "--mem=8G",
        "--output=/jobs/afqmc-measure.log",
        "--wrap",
        "OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 srun python /workspace/demos/qc-afqmc/run.py "
        "--stage measure --smoke --output /jobs/afqmc",
        timeout=30,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9]+", measurement):
        msg = f"Invalid measurement job ID: {measurement!r}"
        raise RuntimeError(msg)
    propagation = job(
        "sbatch",
        "--parsable",
        "--partition=compute",
        "--nodes=2",
        "--ntasks=4",
        "--ntasks-per-node=2",
        "--cpus-per-task=1",
        "--mem=2G",
        f"--dependency=afterok:{measurement}",
        "--kill-on-invalid-dep=yes",
        "--time=10",
        "--output=/jobs/afqmc-propagate.log",
        "--wrap",
        "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1; "
        "mpirun --bind-to core python -m mpi4py "
        "/workspace/demos/qc-afqmc/run.py --stage propagate --mpi --output /jobs/afqmc",
    ).stdout.strip()
    wait_for("AFQMC measurement", lambda: job_finished(measurement), timeout=660)
    wait_for("AFQMC propagation", lambda: job_finished(propagation), timeout=660)
    summary = json.loads((RUNTIME / "jobs/afqmc/summary.json").read_text())
    assert summary["qdmi_jobs"] > 0
    assert summary["device"] == "mqt.ddsim.default"
    assert summary["workload"]["name"] == "smoke"
    assert summary["workers"] == 4
    accounting = job(
        "sacct",
        "-X",
        "-P",
        "--noheader",
        "-j",
        f"{measurement},{propagation}",
        "--format=JobID,State,ExitCode,NNodes,AllocTRES%200",
    ).stdout
    (RUNTIME / "jobs/afqmc-accounting.txt").write_text(accounting)
    assert f"{propagation}|COMPLETED|0:0|2|" in accounting, accounting
    assert any(
        row.startswith(f"{measurement}|COMPLETED|0:0|1|") and "mem=8G" in row for row in accounting.splitlines()
    ), accounting


def test_partitions() -> None:
    """Allocate both QANs together and keep classical work on compute nodes."""
    executable = job("bash", "--login", "-c", "command -v python").stdout.strip()
    assert executable == "/opt/venv/bin/python", executable
    hostnames = job(
        "srun",
        "--immediate=5",
        "--time=1",
        "--partition=quantum",
        "--nodes=2",
        "--ntasks=2",
        "--ntasks-per-node=1",
        "--cpus-per-task=4",
        "--mem=8192M",
        "hostname",
    ).stdout.split()
    assert set(hostnames) == set(QANS), hostnames
    hostname = job("srun", "--immediate=5", "--time=1", "hostname").stdout.strip()
    assert hostname in NODES, hostname
    assert (
        job(
            "srun",
            "--immediate=2",
            "--time=1",
            "--partition=compute",
            "--licenses=mqt.ddsim.default",
            "hostname",
            check=False,
        ).returncode
        != 0
    )


def test_job_environment() -> None:
    """Export job settings through srun and sbatch independently of daemon settings."""
    program = (
        "import os; assert os.geteuid() == 10000; "
        "assert os.environ['MQT_CORE_QDMI_CONFIG_FILE'] == '/jobs/devices.json'; "
        "assert os.environ['MQT_SLURM_TEST_REFERENCE'] == 'job-value'"
    )
    environment = ("env", "MQT_CORE_QDMI_CONFIG_FILE=/jobs/devices.json", "MQT_SLURM_TEST_REFERENCE=job-value")
    job(*environment, "srun", "--immediate=5", "--time=1", "python3", "-c", program, timeout=60)
    job(
        *environment,
        "sbatch",
        "--wait",
        "--time=1",
        "--output=/jobs/environment.out",
        "--wrap",
        shlex.join(("python3", "-c", program)),
        timeout=120,
    )
    job(
        "srun",
        "--immediate=5",
        "--time=1",
        "python3",
        "-c",
        "import os; assert 'MQT_SLURM_TEST_REFERENCE' not in os.environ; "
        "assert 'MQT_CORE_QDMI_CONFIG_FILE' not in os.environ",
        timeout=60,
    )


def main() -> None:
    """Build the shared cluster and run the offline acceptance suite."""
    started_at = time.monotonic()

    success = False
    started = False
    try:
        cgroup_version = run(("docker", "info", "--format", "{{.CgroupVersion}}")).stdout.strip()
        if cgroup_version != "2":
            msg = f"The Slurm integration requires Docker on cgroup v2, got {cgroup_version!r}"
            raise RuntimeError(msg)

        clean_runtime()
        LOGGER.info("Slurm runtime directory: %s", RUNTIME)
        started = True
        compose(
            "up",
            *(() if os.environ.get("MQSC_ORCHESTRATOR_IMAGE") else ("--build",)),
            "--detach",
            "--wait",
            "--wait-timeout",
            "120",
            timeout=7200,
            capture_output=False,
        )
        NODES[:] = [
            compose("exec", "-T", "--index", str(index), "node", "hostname").stdout.strip()
            for index in range(1, COMPUTE_NODES + 1)
        ]
        LOGGER.info("Slurm image build and startup: %.2fs", time.monotonic() - started_at)
        testing_at = time.monotonic()

        version_output = controller("scontrol", "--version").stdout.strip()
        version_match = re.search(r"^slurm(?:-wlm)?\s+(\d+)\.(\d+)\b", version_output, flags=re.IGNORECASE)
        if version_match is None or tuple(map(int, version_match.groups())) < (26, 11):
            msg = f"The fixture requires Slurm 26.11 or newer, got {version_output!r}"
            raise RuntimeError(msg)

        for partition, nodes, cpus, memory in (("compute", NODES, 2, 2048), ("quantum", QANS, 4, 8192)):
            for node in nodes:
                wait_for(
                    f"{node} to become IDLE with {cpus} processors and {memory} MiB",
                    lambda node=node, cpus=cpus, memory=memory: node_is_idle(node, cpus, memory),
                )
            registered = set(
                controller("sinfo", f"--partition={partition}", "--Node", "--noheader", "--format=%N").stdout.split()
            )
            assert registered == set(nodes), registered
        for license_name in ("mqt.ddsim.default", "mqt.sc.default"):
            wait_for(
                f"{license_name} to become available",
                lambda license_name=license_name: license_record(license_name)["DisableLayer"] == "false",
            )
        for license_name in PROVIDER_DEVICES:
            assert license_record(license_name)["DisableLayer"] == "true", license_name
        test_partitions()
        test_core()
        test_job_environment()
        test_applications()

        success = True
        LOGGER.info("Slurm admission and execution checks: %.2fs", time.monotonic() - testing_at)
    finally:
        try:
            if started and not success:
                try:
                    print_diagnostics()
                except Exception:
                    LOGGER.exception("Could not collect Slurm diagnostics")
        finally:
            if started:
                if success:
                    compose(
                        "exec", "-T", "controller", "chown", "-R", f"{os.getuid()}:{os.getgid()}", "/jobs", check=False
                    )
                stopped = compose("down", "--volumes", "--remove-orphans", check=False, timeout=60)
                if success and stopped.returncode == 0:
                    shutil.rmtree(RUNTIME)
                elif success:
                    msg = f"Slurm cleanup failed; retained artifacts in {RUNTIME}"
                    raise RuntimeError(msg)
            LOGGER.info("Slurm integration total: %.2fs", time.monotonic() - started_at)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
