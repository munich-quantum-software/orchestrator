# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Query the SC device with one allocated device license."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "demos/qc-afqmc"))

from mqt.core.qdmi import builtin_driver as qdmi_driver

from allocated_device import resolve_device


def main() -> None:
    """Query the selected SC device and record the compute node."""
    job_id = os.environ["SLURM_JOB_ID"]
    device_id = resolve_device(None, qdmi_driver.registered_device_ids())
    device = qdmi_driver.open_device(device_id)
    result = {
        "device": device.name(),
        "job_id": job_id,
        "device_id": device_id,
        "node": os.environ["SLURM_JOB_NODELIST"],
        "qubits": device.qubits_num(),
    }
    result_path = Path(f"/jobs/sc-{job_id}.json")
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
    temporary.replace(result_path)


if __name__ == "__main__":
    main()
