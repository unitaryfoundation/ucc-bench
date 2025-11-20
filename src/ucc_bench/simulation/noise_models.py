from qiskit import QuantumCircuit
from qiskit.circuit.library import RZGate
from qiskit_aer.noise import (
    NoiseModel,
    amplitude_damping_error,
    coherent_unitary_error,
    depolarizing_error,
    phase_damping_error,
)

# error rates representative of current hardware as of Mar 24, 2025
# details: https://github.com/unitaryfund/ucc/issues/299#issuecomment-2748802174
SINGLE_QUBIT_ERROR_RATE = 0.00052
TWO_QUBIT_ERROR_RATE = 0.0071

SINGLE_QUBIT_AMPLITUDE_DAMPING = 0.00025
SINGLE_QUBIT_PHASE_DAMPING = 0.001
TWO_QUBIT_AMPLITUDE_DAMPING = 0.001
TWO_QUBIT_PHASE_DAMPING = 0.0025


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


def create_mixed_noise_model(*circuits: QuantumCircuit) -> NoiseModel:
    """Create a more complex noise model including a variety of error channels."""

    single_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=1)
    two_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=2)

    single_qubit_error = (
        depolarizing_error(SINGLE_QUBIT_ERROR_RATE, 1)
        .compose(amplitude_damping_error(SINGLE_QUBIT_AMPLITUDE_DAMPING), front=True)
        .compose(phase_damping_error(SINGLE_QUBIT_PHASE_DAMPING), front=True)
    )

    two_qubit_amp = amplitude_damping_error(TWO_QUBIT_AMPLITUDE_DAMPING).tensor(
        amplitude_damping_error(TWO_QUBIT_AMPLITUDE_DAMPING)
    )
    two_qubit_phase = phase_damping_error(TWO_QUBIT_PHASE_DAMPING).tensor(
        phase_damping_error(TWO_QUBIT_PHASE_DAMPING)
    )
    two_qubit_error = (
        depolarizing_error(TWO_QUBIT_ERROR_RATE, 2)
        .compose(two_qubit_amp, front=True)
        .compose(two_qubit_phase, front=True)
    )

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(
        single_qubit_error,
        list(single_qubit_gates),
    )
    noise_model.add_all_qubit_quantum_error(
        two_qubit_error,
        list(two_qubit_gates),
    )

    return noise_model


def create_rz_dephasing_plus_depolarizing_noise_model(
    *circuits: QuantumCircuit,
    rz_noise: float = 0.02,
) -> NoiseModel:
    """Noise model with coherent Rz plus depolarizing noise on all gates."""

    single_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=1)
    two_qubit_gates = get_n_qubit_gateset(*circuits, num_qubits=2)

    rz_unitary = RZGate(rz_noise).to_matrix()

    single_qubit_error = coherent_unitary_error(rz_unitary).compose(
        depolarizing_error(SINGLE_QUBIT_ERROR_RATE, 1)
    )

    two_qubit_coherent_error = coherent_unitary_error(rz_unitary).tensor(
        coherent_unitary_error(rz_unitary)
    )
    two_qubit_error = two_qubit_coherent_error.compose(
        depolarizing_error(TWO_QUBIT_ERROR_RATE, 2)
    )

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(
        single_qubit_error,
        list(single_qubit_gates),
    )
    noise_model.add_all_qubit_quantum_error(
        two_qubit_error,
        list(two_qubit_gates),
    )

    return noise_model
