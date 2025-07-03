import pytest
from ucc_bench.compilers import (
    QiskitCompiler,
    CirqCompiler,
    PytketPeepCompiler,
    UCCCompiler,
    PyQPanda3Compiler,
    PYQPANDA3_AVAILABLE,
)
from ucc_bench.compilers.cirq_compiler import BenchmarkTargetGateset

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
import cirq
from pytket.circuit import Circuit as PytketCircuit
from qbraid import transpile


@pytest.fixture
def qasm_code():
    return """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    creg c[2];
    h q[0];
    rz(pi) q[1];
    rx(pi/2) q[1];
    rz(3*pi) q[1];
    cx q[0],q[1];
    cz q[0],q[1];
    """


compiler_fixtures = [
    (QiskitCompiler, QuantumCircuit, "qiskit-default"),
    (CirqCompiler, cirq.Circuit, "cirq"),
    (PytketPeepCompiler, PytketCircuit, "pytket-peep"),
    (UCCCompiler, QuantumCircuit, "ucc"),
]

if PYQPANDA3_AVAILABLE:
    from pyqpanda3.core import QProg

    compiler_fixtures.append((PyQPanda3Compiler, QProg, "pyqpanda3"))


@pytest.mark.parametrize(
    "compiler_class,expected_circuit_type,expected_id", compiler_fixtures
)
def test_compiler(compiler_class, expected_circuit_type, expected_id, qasm_code):
    """
    Basic tests that all compilers have the expected methods and return types.
    Does *not* test the correctness of compilation.
    """
    compiler = compiler_class()

    # Test id and version
    assert compiler.id() == expected_id
    assert isinstance(compiler.version(), str)

    # Test qasm_to_native
    circuit = compiler.qasm_to_native(qasm_code)
    assert isinstance(circuit, expected_circuit_type)

    # Test compile
    compiled_circuit = compiler.compile(circuit)
    assert isinstance(compiled_circuit, expected_circuit_type)

    # Test count_multi_qubit_gates of original circuit (to ignore compilation effects)
    multi_qubit_gates = compiler.count_multi_qubit_gates(circuit)
    assert isinstance(multi_qubit_gates, int)
    assert multi_qubit_gates == 2

    # Check circuits are equivalent using Qiskit
    compiled_qasm = compiler.native_to_qasm(compiled_circuit)
    circuit_qiskit = transpile(qasm_code, "qiskit")
    compiled_circuit_qiskit = transpile(compiled_qasm, "qiskit")
    assert Operator(circuit_qiskit).equiv(Operator(compiled_circuit_qiskit), atol=1e-6)


def test_cirq_benchmark_target_gateset_simple_circuit():
    """
    Tests the custom BenchmarkTargetGateset compiles a simple circuit
    to the desired target gateset and has equivalent functionality
    """

    import cirq

    q = cirq.LineQubit.range(2)
    c_orig = cirq.Circuit(
        cirq.T(q[0]),
        cirq.SWAP(*q),
        cirq.T(q[0]),
        cirq.SWAP(*q),
        cirq.SWAP(*q),
        cirq.T.on_each(*q),
    )

    c_new = cirq.optimize_for_target_gateset(c_orig, gateset=BenchmarkTargetGateset())

    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        c_orig, c_new, atol=1e-6
    )

    expected_gates = cirq.Gateset(cirq.CNOT, cirq.Rx, cirq.Ry, cirq.Rz, cirq.H)
    assert expected_gates.validate(c_new), "Cirq compilation had unsupported gatges"


def test_cirq_benchmark_target_gateset_random_circuit():
    """
    Tests the custom BenchmarkTargetGateset compiles a random circuit
    to the desired target gateset and has equivalent functionality
    """

    from cirq.testing import random_circuit

    c_orig = random_circuit(qubits=4, n_moments=6, op_density=0.8, random_state=1234)

    c_new = cirq.optimize_for_target_gateset(c_orig, gateset=BenchmarkTargetGateset())

    # Check that circuits are equivalent
    cirq.testing.assert_circuits_with_terminal_measurements_are_equivalent(
        c_orig, c_new, atol=1e-6
    )
    # Check if the compiled circuit uses only the expected gates
    expected_gates = cirq.Gateset(cirq.CNOT, cirq.Rx, cirq.Ry, cirq.Rz, cirq.H)
    assert expected_gates.validate(c_new), "Cirq compilation had unsupported gates"
