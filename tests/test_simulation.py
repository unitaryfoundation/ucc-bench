from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Operator
from ucc_bench.simulation.noise_models import get_n_qubit_gateset
from ucc_bench.simulation.observables import (
    generate_qcnn_observable,
    generate_computational_basis_observable,
    generate_ghz_state_projector,
    generate_uniform_superposition_projector,
    generate_prep_select_all_ones_observable,
)


def test_get_n_qubit_gateset_single_qubit_gates():
    circuit = QuantumCircuit(1)
    circuit.h(0)  # Add a single-qubit gate (Hadamard)
    circuit.x(0)  # Add another single-qubit gate (Pauli-X)

    result = get_n_qubit_gateset(circuit, num_qubits=1)
    assert result == {"h", "x"}, "Should return single-qubit gate names"


def test_get_n_qubit_gateset_two_qubit_gates():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)  # Add a two-qubit gate (CNOT)
    circuit.cz(0, 1)  # Add another two-qubit gate (CZ)

    result = get_n_qubit_gateset(circuit, num_qubits=2)
    assert result == {"cx", "cz"}, "Should return two-qubit gate names"


def test_get_n_qubit_gateset_mixed_gates():
    circuit = QuantumCircuit(2)
    circuit.h(0)  # Single-qubit gate
    circuit.cx(0, 1)  # Two-qubit gate

    single_qubit_result = get_n_qubit_gateset(circuit, num_qubits=1)
    two_qubit_result = get_n_qubit_gateset(circuit, num_qubits=2)

    assert single_qubit_result == {"h"}, "Should return only single-qubit gate names"
    assert two_qubit_result == {"cx"}, "Should return only two-qubit gate names"


def test_get_n_qubit_gateset_no_gates():
    circuit = QuantumCircuit(1)  # Empty circuit

    result = get_n_qubit_gateset(circuit, num_qubits=1)
    assert result == set(), "Should return an empty set for no gates"


def test_get_n_qubit_gateset_ignores_measurements():
    circuit = QuantumCircuit(1)
    circuit.h(0)  # Single-qubit gate
    circuit.measure_all()  # Add measurement

    result = get_n_qubit_gateset(circuit, num_qubits=1)
    assert result == {"h"}, "Should ignore measurement operations"


def test_generate_computational_basis_observable():
    assert generate_computational_basis_observable(4) == Operator.from_label("ZZZZ")
    assert generate_computational_basis_observable(6) == Operator.from_label("ZZZZZZ")


def test_generate_qcnn_observable():
    assert generate_qcnn_observable(4) == SparsePauliOp(["ZXZI", "IZXZ"])
    assert generate_qcnn_observable(6) == SparsePauliOp(
        ["ZXZIII", "IZXZII", "IIZXZI", "IIIZXZ"]
    )


def test_generate_ghz_state_projector():
    expected = (
        1 / 2 * Operator([[1, 0, 0, 1], [0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 0, 1]])
    )
    assert generate_ghz_state_projector(2) == expected


def test_generate_uniform_superposition_projector():
    expected = (
        1 / 4 * Operator([[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]])
    )
    assert generate_uniform_superposition_projector(2) == expected


def test_generate_prep_select_all_ones():
    expected = (
        1 / 4 * Operator([[1, 1, 1, -1], [1, 1, 1, -1], [1, 1, 1, -1], [-1, -1, -1, 1]])
    )
    assert generate_prep_select_all_ones_observable(2) == expected
