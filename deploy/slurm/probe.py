#!/opt/venv/bin/python
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Return success only when the selected QDMI device is operational.

The last output line is a fixed reason for the controller log: the device status
in lower case, ``unregistered`` for a disabled or unknown device, or
``unavailable`` when opening it or reading its status fails.
"""

from __future__ import annotations

import sys


def reason(device_id: str) -> str:
    """Classify the device without exposing provider diagnostics.

    Returns:
        The lower-case device status, ``unregistered``, or ``unavailable``.
    """
    try:
        from mqt.core.qdmi import builtin_driver as qdmi_driver  # ruff: ignore[import-outside-top-level] - Fail closed on driver initialization and import errors.

        if device_id not in qdmi_driver.registered_device_ids():
            return "unregistered"
        return qdmi_driver.open_device(device_id).status().name.lower()
    except Exception:  # ruff: ignore[blind-except] - Any provider failure closes admission without leaking credentials.
        # Device diagnostics may contain credentials, so only a fixed reason is reported.
        return "unavailable"


def probe(device_id: str) -> int:
    """Print the reason as the last line.

    Returns:
        Zero for IDLE or BUSY, otherwise one.
    """
    result = reason(device_id)
    sys.stdout.write(f"\n{result}\n")
    return int(result not in {"idle", "busy"})


if __name__ == "__main__":
    sys.exit(probe(sys.argv[1]) if len(sys.argv) == 2 else 1)
