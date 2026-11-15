# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""The asymmetric oracle must reject plausible but incorrectly mapped results."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_workflows", Path(__file__).parents[1] / "scripts/check_workflows.py"
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("actual", [{"1000": 32}, {"0010": 32}, {"0100": 31}, {}, {"0100": 32, "0000": 1}])
def test_asymmetric_oracle_rejects_corruption(actual: dict) -> None:
    """Reject reversal, changed counts, and unexpected outcomes."""
    with pytest.raises(AssertionError):
        module.require_counts(actual, "0100", 32)
