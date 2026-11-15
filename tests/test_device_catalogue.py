# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Keep the device lists of the HRES, accounting, and QDMI configuration aligned."""

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parents[1]
CLUSTER = ROOT / "deploy" / "slurm"
BUILTIN_DEVICES = {"mqt.ddsim.default", "mqt.sc.default"}


def test_device_lists_agree() -> None:
    """Every HRES is accounted, and every catalogue entry is a disabled provider HRES."""
    resources = re.findall(r"^- resource: (\S+)$", (CLUSTER / "resources.yaml").read_text(), flags=re.MULTILINE)
    tres = re.search(r"^AccountingStorageTRES=(\S+)$", (CLUSTER / "slurm.conf").read_text(), flags=re.MULTILINE)
    assert tres is not None
    licenses = [entry.removeprefix("license/") for entry in tres[1].split(",") if entry.startswith("license/")]
    catalogue = json.loads((CLUSTER / "qdmi.json").read_text())["qdmi"]["devices"]
    providers = [device["id"] for device in catalogue]

    for names in (resources, licenses, providers):
        assert not [name for name, count in Counter(names).items() if count > 1], names
    assert set(licenses) == set(resources)
    assert set(resources) == BUILTIN_DEVICES | set(providers)
    assert not BUILTIN_DEVICES & set(providers)
    assert not [device["id"] for device in catalogue if device["enabled"]], "Provider devices stay disabled."


def test_target_checks_cover_catalogued_devices() -> None:
    """The scheduled target check compiles only for devices the cluster can admit."""
    workflow = (ROOT / ".github" / "workflows" / "provider-targets.yml").read_text()
    checked = set(
        re.findall(r"\b(?:iqm|ibm|amazon\.braket)\.[\w.-]+", workflow.split("check_provider_targets.py", 1)[1])
    )
    catalogue = {device["id"] for device in json.loads((CLUSTER / "qdmi.json").read_text())["qdmi"]["devices"]}
    assert checked
    assert checked <= catalogue, checked - catalogue
