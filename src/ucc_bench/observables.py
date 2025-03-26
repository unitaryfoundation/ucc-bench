from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector, SparsePauliOp
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_aer import AerSimulator
import numpy as np
import math
from typing import Set

SINGLE_QUBIT_ERROR_RATE = 0.01
TWO_QUBIT_ERROR_RATE = 0.03


class Observable:
    def calc_observable(
        raw_circuit: QuantumCircuit, compiled_circuit: QuantumCircuit, noise_model
    ) -> float:
        pass


def get_n_qubit_gateset(circuit: QuantumCircuit, num_qubits: int) -> set[str]:
    """Extracts the set of gates of size num_qubits from a quantum circuit.

    Args:
        circuit: Quantum circuit.
        num_qubits: The size of the gates to get.

    Returns:
        Set of string names of <num_qubits>-qubit gates.
    """
    return {
        instr.operation.name
        for instr in circuit.data
        if instr.operation.num_qubits == num_qubits
        and instr.operation.name != "measure"
    }


def create_depolarizing_noise_model(
    circuit: QuantumCircuit,
    single_qubit_error_rate: float = 0.01,
    two_qubit_error_rate: float = 0.03,
) -> NoiseModel:
    """Depolarizing noise model with error rates applied to the single and
    two-qubit gates of the circuit.

    Args:
        circuit: Quantum circuit to apply the model to.
        single_qubit_error_rate: Error rate for a single qubit gate.
        two_qubit_error_rate: Error rate for a two qubit gate.

    Returns:
        Depolarizing noise model.
    """
    single_qubit_gates = get_n_qubit_gateset(circuit, num_qubits=1)
    two_qubit_gates = get_n_qubit_gateset(circuit, num_qubits=2)

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(single_qubit_error_rate, 1),
        list(single_qubit_gates),
    )
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(two_qubit_error_rate, 2), list(two_qubit_gates)
    )

    return noise_model


def simulate_density_matrix(circuit: QuantumCircuit) -> np.ndarray:
    """Simulates the given quantum circuit using a density matrix simulator
    with depolarizing noise.

    Args:
        circuit: The quantum circuit to simulate.

    Returns:
        The resulting density matrix from the simulation.
    """
    depolarizing_noise = create_depolarizing_noise_model(
        circuit, SINGLE_QUBIT_ERROR_RATE, TWO_QUBIT_ERROR_RATE
    )
    simulator = AerSimulator(
        method="density_matrix",
        noise_model=depolarizing_noise,
        max_parallel_threads=1,
    )
    return simulator.run(circuit).result().data()["density_matrix"]


class ComputationalBasisObservable:
    def get_observable(self, num_qubits: int) -> Operator:
        """
        Returns the computational basis operator for the given number of qubits.
        """
        return Operator.from_label("Z" * num_qubits)

    def calc_observable(
        self, uncompiled_circuit: QuantumCircuit, compiled_circuit: QuantumCircuit
    ) -> float:
        # Ensure circuits save density matrices
        uncompiled_circuit.save_density_matrix()
        compiled_circuit.save_density_matrix()

        observable = self.get_observable(uncompiled_circuit.num_qubits)

        uncompiled_circuit_state = Statevector.from_instruction(uncompiled_circuit)
        uncompiled_ideal_observable = np.real(
            uncompiled_circuit_state.expectation_value(observable)
        )

        compiled_circuit_state = Statevector.from_instruction(compiled_circuit)
        compiled_ideal_observable = np.real(
            compiled_circuit_state.expectation_value(observable)
        )

        # do noise simulations
        uncompiled_circuit_density_matrix = simulate_density_matrix(uncompiled_circuit)
        uncompiled_noisy_observable = np.real(
            uncompiled_circuit_density_matrix.expectation_value(observable)
        )

        compiled_circuit_density_matrix = simulate_density_matrix(compiled_circuit)
        compiled_noisy_observable = np.real(
            compiled_circuit_density_matrix.expectation_value(observable)
        )

        return (
            uncompiled_ideal_observable,
            compiled_ideal_observable,
            uncompiled_noisy_observable,
            compiled_noisy_observable,
        )


class QaoaObservable:
    def get_observable(self, num_qubits: int) -> Operator:
        """Generates the problem Hamiltonian as the observable for the QAOA
        benchmarking circuits, based on the binary encoding described in
        Franz G. Fuchs, Herman Øie Kolden, Niels Henrik Aase, and Giorgio
        Sartor "Efficient encoding of the weighted MAX k-CUT on a quantum computer
        using QAOA". (2020) arXiv 2009.01095 (https://arxiv.org/abs/2009.01095).
        The weights of the edges between vertices and of the resulting unitary
        evolution come from the 10-vertex Barabasi-Albert graph in Fig 4(c)
        of the paper.
        """

        pauli_strings = []
        # Weights of edges between vertices and of the resulting unitary evolution
        weighted_edges = [
            (0, 1, 6.720),
            (0, 2, 3.246),
            (1, 2, 6.462),
            (1, 3, 3.386),
            (1, 5, 5.014),
            (1, 6, 6.596),
            (2, 3, 8.579),
            (2, 4, 0.62),
            (2, 5, 0.708),
            (2, 6, 2.275),
            (2, 7, 5.0),
            (2, 8, 4.034),
            (3, 4, 4.987),
            (3, 6, 1.089),
            (3, 9, 2.961),
            (4, 5, 1.134),
            (4, 6, 6.865),
            (5, 6, 8.184),
            (5, 7, 9.459),
            (6, 7, 2.268),
            (6, 8, 8.197),
            (6, 9, 1.212),
            (7, 9, 4.265),
            (8, 9, 1.690),
        ]
        for i, j, _ in weighted_edges:
            # Start with identity string
            pauli_string = ["I"] * num_qubits
            # Place Z operators on the chosen qubits
            pauli_string[i] = "Z"
            pauli_string[j] = "Z"
            # Convert to PauliSumOp
            pauli_strings.append("".join(pauli_string))
        coeffs = [weight for _, _, weight in weighted_edges]
        observable = SparsePauliOp(pauli_strings, coeffs)
        return observable

        def calc_observable(
            self, uncompiled_circuit: QuantumCircuit, compiled_circuit: QuantumCircuit
        ) -> float:
            # Ensure circuits save density matrices
            uncompiled_circuit.save_density_matrix()
            compiled_circuit.save_density_matrix()

            observable = self.get_observable(uncompiled_circuit.num_qubits)

            uncompiled_circuit_state = Statevector.from_instruction(uncompiled_circuit)
            uncompiled_ideal_observable = np.real(
                uncompiled_circuit_state.expectation_value(observable)
            )

            compiled_circuit_state = Statevector.from_instruction(compiled_circuit)
            compiled_ideal_observable = np.real(
                compiled_circuit_state.expectation_value(observable)
            )

            # do noise simulations
            uncompiled_circuit_density_matrix = simulate_density_matrix(
                uncompiled_circuit
            )
            uncompiled_noisy_observable = np.real(
                uncompiled_circuit_density_matrix.expectation_value(observable)
            )

            compiled_circuit_density_matrix = simulate_density_matrix(compiled_circuit)
            compiled_noisy_observable = np.real(
                compiled_circuit_density_matrix.expectation_value(observable)
            )

            return (
                uncompiled_ideal_observable,
                compiled_ideal_observable,
                uncompiled_noisy_observable,
                compiled_noisy_observable,
            )


def get_heavy_bitstrings(circuit: QuantumCircuit) -> Set[str]:
    """ "Determine the heavy bitstrings of the circuit."""
    simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    result = simulator.run(circuit, shots=1024).result()
    counts = list(result.get_counts().items())
    median = np.median([c for (_, c) in counts])
    return set(bitstring for (bitstring, p) in counts if p > median)


def estimate_heavy_output_prob(circuit: QuantumCircuit, noisy: bool = True) -> float:
    """Sample the heavy bitstrings on the backend and estimate the heavy output
    probability from the counts of the heavy bitstrings.

    Args:
        circuit: The circuit for which to compute the heavy output metric.
        qv_1q_err: The single qubit error rate for the backend noise model.
        qv_2q_err: The two-qubit error rate for the backend noise model.

    Returns:
        The heavy output probability as a float.
    """
    heavy_bitstrings = get_heavy_bitstrings(circuit)

    if noisy:
        simulator = AerSimulator(
            method="statevector",
            noise_model=create_depolarizing_noise_model(
                circuit, SINGLE_QUBIT_ERROR_RATE, TWO_QUBIT_ERROR_RATE
            ),
            max_parallel_threads=1,
        )
    else:
        simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    result = simulator.run(circuit).result()

    heavy_counts = sum(
        result.get_counts().get(bitstring, 0) for bitstring in heavy_bitstrings
    )
    nshots = 1024
    hop = (
        heavy_counts - 2 * math.sqrt(heavy_counts * (nshots - heavy_counts))
    ) / nshots
    return hop


class HOPFObservable:
    def calc_observable(
        self, uncompiled_circuit: QuantumCircuit, compiled_circuit: QuantumCircuit
    ) -> float:
        # Ensure circuits save density matrices
        uncompiled_circuit.save_density_matrix()
        compiled_circuit.save_density_matrix()

        uncompiled_circuit.measure_all()
        compiled_circuit.measure_all()

        uncompiled_ideal_observable = estimate_heavy_output_prob(
            uncompiled_circuit, False
        )
        compiled_ideal_observable = estimate_heavy_output_prob(compiled_circuit, False)
        uncompiled_noisy_observable = estimate_heavy_output_prob(
            uncompiled_circuit, True
        )
        compiled_noisy_observable = estimate_heavy_output_prob(compiled_circuit, True)

        return (
            uncompiled_ideal_observable,
            compiled_ideal_observable,
            uncompiled_noisy_observable,
            compiled_noisy_observable,
        )
