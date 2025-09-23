import pytest
from pathlib import Path

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from ucc_bench.runner import run_task
from ucc_bench.utils import validate_circuit_gates
from ucc_bench.compilers import QiskitCompiler
from ucc_bench.suite import BenchmarkSpec
from ucc_bench import registry


def test_validate_circuit_gates_accepts_allowed_gates():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.reset(0)
    qc.cx(0, 1)
    qc.rx(0.1, 0)
    qc.ry(0.2, 1)
    qc.rz(0.3, 0)

    # Should not raise
    validate_circuit_gates(qc)


def test_validate_circuit_gates_accepts_classical_logic():
    qreg = QuantumRegister(2)
    creg = ClassicalRegister(1)
    qc = QuantumCircuit(qreg, creg)

    qc.barrier(0, 1)
    qc.delay(100, 0)
    qc.measure_all()
    with qc.if_test((creg, 1)):
        qc.x(qreg)

    # Should not raise
    validate_circuit_gates(qc)


def test_validate_circuit_gates_rejects_disallowed_gates():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.t(0)  # T gate is not in the allowed set

    with pytest.raises(ValueError):
        validate_circuit_gates(qc)


def test_run_task_gate_check_passes(tmp_path: Path):
    qasm = """
    OPENQASM 2.0;
    include \"qelib1.inc\";
    qreg q[2];
    h q[0];
    cx q[0],q[1];
    """
    qasm_file = tmp_path / "simple.qasm"
    qasm_file.write_text(qasm)

    bench = BenchmarkSpec(id="b1", description="bench", qasm_file=qasm_file)
    bench.resolved_qasm_file = qasm_file

    result = run_task(
        QiskitCompiler(), bench, target_device=None, target_device_id=None
    )
    assert result.benchmark_id == "b1"


def test_run_task_gate_check_fails(tmp_path: Path):
    qasm = """
    OPENQASM 2.0;
    include \"qelib1.inc\";
    qreg q[1];
    h q[0];
    """
    qasm_file = tmp_path / "simple.qasm"
    qasm_file.write_text(qasm)

    bench = BenchmarkSpec(id="b2", description="bench", qasm_file=qasm_file)
    bench.resolved_qasm_file = qasm_file

    class BadCompiler(QiskitCompiler):
        @classmethod
        def id(cls) -> str:  # type: ignore[override]
            return "bad"

        def compile(
            self, circuit: QuantumCircuit, target_device=None
        ) -> QuantumCircuit:  # type: ignore[override]
            qc = QuantumCircuit(1)
            qc.t(0)
            return qc

    with pytest.raises(ValueError):
        run_task(BadCompiler(), bench, target_device=None, target_device_id=None)


def test_run_task_backend_passes(tmp_path: Path):
    qasm = """
    OPENQASM 2.0;
    include \"qelib1.inc\";
    qreg q[2];
    h q[0];
    cx q[0],q[1];
    """
    qasm_file = tmp_path / "simple.qasm"
    qasm_file.write_text(qasm)

    bench = BenchmarkSpec(id="b1", description="bench", qasm_file=qasm_file)
    bench.resolved_qasm_file = qasm_file

    target_device_id = "ibm_fake_washington"

    result = run_task(
        QiskitCompiler(),
        bench,
        target_device=registry.register.get_target_device(target_device_id),
        target_device_id=target_device_id,
    )
    assert result.benchmark_id == "b1"
