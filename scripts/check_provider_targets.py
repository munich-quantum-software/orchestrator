# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Compile for provider devices without submitting to them, then run the result on DDSIM.

Opening a provider device reads its metadata; this script never submits a job to it.
"""

from __future__ import annotations

import argparse
import logging
import sys

from check_workflows import require_counts

SHOTS = 32


def check(device_id: str) -> None:
    """Compile an asymmetric circuit for one device and check its meaning on DDSIM."""
    from mqt.core.mlir import (
        CompilationOptions,
        OutputFormat,
        QIRProfile,
        TargetEnvironment,
        compile_program,
        decode_counts,
    )
    from mqt.core.qdmi import ProgramFormat, builtin_driver
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    environment = TargetEnvironment.from_device(builtin_driver.open_device(device_id))
    circuit = QuantumCircuit(QuantumRegister(4, "q"), ClassicalRegister(2, "a"), ClassicalRegister(2, "b"))
    circuit.x(0)
    circuit.measure(0, 2)
    circuit.measure(1, 0)
    circuit.measure(2, 1)
    circuit.measure(3, 3)  # Base Profile QIR requires every output bit to be measured.
    options = CompilationOptions(seed=17)
    # The exact payload and format that submission to this device would send.
    compiled = compile_program(circuit, target=environment, options=options)
    if not compiled.payload:
        msg = f"{device_id}: empty {compiled.program_format.name} payload"
        raise AssertionError(msg)

    if compiled.program_format in {ProgramFormat.QASM2, ProgramFormat.QASM3, ProgramFormat.QIR_BASE_STRING}:
        payload, program_format, layout = compiled.payload, compiled.program_format, compiled.result_layout
    else:
        # DDSIM cannot read this format; run the same target-native program as Base Profile QIR.
        native = compile_program(circuit, target=environment.target, options=options, output=OutputFormat.QC)
        payload = native.to_qir(QIRProfile.BASE).to_llvm_ir()
        program_format, layout = ProgramFormat.QIR_BASE_STRING, None

    # Physical qubit IDs can be sparse, so DDSIM needs the largest ID, not the site count.
    width = max(site.id for site in environment.target.sites) + 1
    simulator = builtin_driver.open_device("mqt.ddsim.default", custom1=str(width))
    job = simulator.submit_job(payload, program_format, SHOTS)
    if not job.wait(300):
        msg = f"{device_id}: DDSIM did not finish the compiled program"
        raise TimeoutError(msg)
    # QDMI labels use descending classical-bit indices: c[3] ... c[0].
    require_counts(decode_counts(job.get_counts(), compiled.result_width, SHOTS, layout), "0100", SHOTS)
    print(
        f"PASS {device_id}: {environment.target.num_sites} sites, {compiled.program_format.name} payload, "
        f"{program_format.name} on DDSIM"
    )


def main() -> None:
    """Check each requested device and fail if any check failed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("devices", nargs="+", help="QDMI device IDs to compile for")
    failed = []
    for device_id in parser.parse_args().devices:
        try:
            check(device_id)
        except Exception:
            # One unavailable device must not hide the results for the others.
            logging.getLogger(__name__).exception("FAIL %s", device_id)
            failed.append(device_id)
    if failed:
        sys.exit(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
