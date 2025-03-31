from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel, depolarizing_error

# error rates representative of current hardware as of Mar 24, 2025
# details: https://github.com/unitaryfund/ucc/issues/299#issuecomment-2748802174
SINGLE_QUBIT_ERROR_RATE = 0.00052
TWO_QUBIT_ERROR_RATE = 0.0071


def get_n_qubit_gateset(*circuits: QuantumCircuit, num_qubits: int) -> set[str]:
    """Extracts the set of gates of size num_qubits from the circuits."""
    return {
        instr.operation.name
        for circuit in circuits
        for instr in circuit.data
        if instr.operation.num_qubits == num_qubits
        and instr.operation.name not in ("measure", "barrier", "reset")
    }


def create_depolarizing_noise_model(*circuits: QuantumCircuit) -> NoiseModel:
    """Create a depolarizing noise model that applies a fix single (two) qubit
    error rate across all single (two) qubit gate types in either circuit.
    """

    single_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=1)
    two_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=2)

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(SINGLE_QUBIT_ERROR_RATE, 1),
        list(single_qubit_gates),
    )
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(TWO_QUBIT_ERROR_RATE, 2), list(two_qubit_gates)
    )
    return noise_model
