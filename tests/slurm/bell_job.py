# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Execute a Bell circuit with one allocated DDSIM license."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "demos/qc-afqmc"))

from mqt.core.qdmi import ProgramFormat
from mqt.core.qdmi import builtin_driver as qdmi_driver

from allocated_device import resolve_device

BELL_PROGRAM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q -> c;
"""
SHOTS = 256


def main() -> None:
    """Run the circuit, write its result, and optionally retain the allocation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--hold", action="store_true")
    args = parser.parse_args()

    job_id = os.environ["SLURM_JOB_ID"]
    device_id = resolve_device(None, qdmi_driver.registered_device_ids())
    device = qdmi_driver.open_device(device_id)
    job = device.submit_job(BELL_PROGRAM, ProgramFormat.QASM2, SHOTS)
    if not job.wait(60):
        msg = "DDSIM did not complete the Bell circuit within 60 seconds"
        raise RuntimeError(msg)

    counts = job.get_counts()
    if sum(counts.values()) != SHOTS:
        msg = f"Expected {SHOTS} Bell samples, got {sum(counts.values())}"
        raise RuntimeError(msg)
    if set(counts) != {"00", "11"}:
        msg = f"Expected only Bell outcomes 00 and 11, got {sorted(counts)}"
        raise RuntimeError(msg)

    result = {
        "counts": counts,
        "device": device.name(),
        "job_id": job_id,
        "device_id": device_id,
        "node": os.environ["SLURM_JOB_NODELIST"],
        "shots": SHOTS,
    }
    runtime = Path("/jobs")
    result_path = runtime / f"ddsim-{job_id}.json"
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
    temporary.replace(result_path)

    if args.hold:
        release = runtime / f"release-{job_id}"
        deadline = time.monotonic() + 180
        while not release.exists():
            if time.monotonic() >= deadline:
                msg = f"Release marker for Slurm job {job_id} did not appear"
                raise TimeoutError(msg)
            time.sleep(0.2)


if __name__ == "__main__":
    main()
