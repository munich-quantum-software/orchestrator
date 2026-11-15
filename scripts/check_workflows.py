# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

"""Check exact serialized payloads and asymmetric results on ideal DDSIM."""

from __future__ import annotations


def require_counts(actual: dict[str, int], expected: str, shots: int) -> None:
    """Reject a changed count or classical-bit destination."""
    if actual != {expected: shots}:
        msg = f"Expected {expected!r} x {shots}, got {actual}"
        raise AssertionError(msg)


def run() -> None:
    """Exercise the DDSIM payload formats and both application frontends."""
    import pennylane as qml
    from mqt.core.mlir import OutputFormat, compile_program
    from mqt.core.plugins.pennylane import QDMIDevice
    from mqt.core.plugins.qiskit import QDMIBackend
    from mqt.core.qdmi import ProgramFormat, builtin_driver
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    shots = 32
    device = builtin_driver.open_device("mqt.ddsim.default")
    backend = QDMIBackend(device)
    circuit = QuantumCircuit(QuantumRegister(4, "q"), ClassicalRegister(2, "a"), ClassicalRegister(2, "b"))
    circuit.x(0)
    circuit.measure(0, 2)
    circuit.measure(1, 0)
    circuit.measure(2, 1)
    # b[1] remains zero; reversing either wires or register order changes this result.
    expected = "01 00"
    for fmt, name in ((OutputFormat.OPENQASM3, "digital.qasm"), (OutputFormat.QIR_BASE, "digital.ll")):
        source = circuit.copy()
        if fmt == OutputFormat.QIR_BASE:
            source.measure(3, 3)  # Base Profile requires every output bit to be measured.
        compiled = compile_program(source, output=fmt)
        payload = compiled.source if fmt == OutputFormat.OPENQASM3 else compiled.to_llvm_ir()
        native_format = ProgramFormat.QASM3 if fmt == OutputFormat.OPENQASM3 else ProgramFormat.QIR_BASE_STRING
        job = device.submit_job(payload, native_format, shots)
        if not job.wait(60):
            raise TimeoutError(name)
        # QDMI labels use descending classical-bit indices: c[3] ... c[0].
        require_counts(job.get_counts(), "0100", shots)
        assert job.get_shots() == ["0100"] * shots

    second = circuit.copy()
    second.data = [item for item in second.data if item.operation.name != "x"]
    result = backend.run([circuit, second], shots=shots, memory=True).result()
    for i, bits in enumerate((expected, "00 00")):
        require_counts(result.get_counts(i), bits, shots)
        assert result.get_memory(i) == [bits] * shots

    pl_device = QDMIDevice(device=device, wires=["left", "idle", "right"])

    @qml.qnode(pl_device)
    def asymmetric() -> dict:
        qml.PauliX("left")
        return qml.counts(wires=["right", "left", "idle"])

    require_counts(qml.set_shots(asymmetric, shots=shots)(), "010", shots)


if __name__ == "__main__":
    run()
