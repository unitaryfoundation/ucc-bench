from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector, SparsePauliOp
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_aer import AerSimulator
import numpy as np
import math
from typing import Set, Tuple
from abc import ABC, abstractmethod

SINGLE_QUBIT_ERROR_RATE = 0.01
TWO_QUBIT_ERROR_RATE = 0.03


class NoiseModelFactory(ABC):
    """Abstract base class for noise model factories."""

    _registry = {}

    def __init_subclass__(cls, **kwargs):
        # When creating subclasses, register them in the registry by id
        super().__init_subclass__(**kwargs)
        cls._registry[cls.id()] = cls

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def lookup(cls, name: str) -> "NoiseModelFactory":
        return cls._registry[name]

    @classmethod
    @abstractmethod
    def id(cls) -> str:
        """Return the identifier (name) of the noise model"""
        pass

    @abstractmethod
    def create(circuit: QuantumCircuit) -> NoiseModel:
        """Creates a noise model."""
        pass


def get_n_qubit_gateset(circuit: QuantumCircuit, num_qubits: int) -> set[str]:
    """Extracts the set of gates of size num_qubits from a quantum circuit."""
    return {
        instr.operation.name
        for instr in circuit.data
        if instr.operation.num_qubits == num_qubits
        and instr.operation.name != "measure"
    }


class DepolarizingNoiseModelFactory(NoiseModelFactory):
    """Creates a depolarizing noise model for a quantum circuit with specified error rates
    for single and two qubit gates.
    """

    def __init__(
        self,
        single_qubit_error_rate: float = SINGLE_QUBIT_ERROR_RATE,
        two_qubit_error_rate: float = TWO_QUBIT_ERROR_RATE,
    ):
        self.single_qubit_error_rate = single_qubit_error_rate
        self.two_qubit_error_rate = two_qubit_error_rate

    @classmethod
    def id(cls) -> str:
        return "depolarizing"

    def create(self, circuit: QuantumCircuit) -> NoiseModel:
        """Creates a depolarizing noise model."""

        single_qubit_gates = get_n_qubit_gateset(circuit, num_qubits=1)
        two_qubit_gates = get_n_qubit_gateset(circuit, num_qubits=2)

        noise_model = NoiseModel()
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(self.single_qubit_error_rate, 1),
            list(single_qubit_gates),
        )
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(self.two_qubit_error_rate, 2), list(two_qubit_gates)
        )
        return noise_model


def simulate_density_matrix_with_noise(
    circuit: QuantumCircuit, noise_model: NoiseModel
) -> np.ndarray:
    """Simulates the given quantum circuit using a density matrix simulator with a specified noise model."""
    simulator = AerSimulator(
        method="density_matrix",
        noise_model=noise_model,
        max_parallel_threads=1,
    )
    return simulator.run(circuit).result().data()["density_matrix"]


class Observable(ABC):
    """Abstract base class for observables."""

    _registry = {}

    def __init_subclass__(cls, **kwargs):
        # When creating subclasses, register them in the registry by id
        super().__init_subclass__(**kwargs)
        cls._registry[cls.id()] = cls

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def lookup(cls, name: str) -> "Observable":
        return cls._registry[name]

    @classmethod
    @abstractmethod
    def id(cls) -> str:
        """Return the identifier (name) of the observable"""
        pass

    @abstractmethod
    def get_observable(self, num_qubits: int) -> Operator:
        pass

    def calc_observable(
        self,
        uncompiled_circuit: QuantumCircuit,
        compiled_circuit: QuantumCircuit,
        noise_model: NoiseModel,
    ) -> Tuple[float, float, float, float]:
        """Calculates the ideal and noisy observables for uncompiled and compiled circuits."""
        # Ensure circuits save density matrices
        uncompiled_circuit.save_density_matrix()
        compiled_circuit.save_density_matrix()

        observable = self.get_observable(uncompiled_circuit.num_qubits)

        # Ideal observables
        uncompiled_state = Statevector.from_instruction(uncompiled_circuit)
        compiled_state = Statevector.from_instruction(compiled_circuit)
        uncompiled_ideal = np.real(uncompiled_state.expectation_value(observable))
        compiled_ideal = np.real(compiled_state.expectation_value(observable))

        uncompiled_density_matrix = simulate_density_matrix_with_noise(
            uncompiled_circuit, noise_model
        )
        compiled_density_matrix = simulate_density_matrix_with_noise(
            compiled_circuit, noise_model
        )
        uncompiled_noisy = np.real(
            uncompiled_density_matrix.expectation_value(observable)
        )
        compiled_noisy = np.real(compiled_density_matrix.expectation_value(observable))

        return uncompiled_ideal, compiled_ideal, uncompiled_noisy, compiled_noisy


class ComputationalBasisObservable(Observable):
    """Observable for the computational basis."""

    @classmethod
    def id(cls) -> str:
        return "computational_basis"

    def get_observable(self, num_qubits: int) -> Operator:
        return Operator.from_label("Z" * num_qubits)


class QaoaObservable(Observable):
    """Observable for QAOA benchmarking circuits."""

    @classmethod
    def id(cls) -> str:
        return "qaoa"

    def get_observable(self, num_qubits: int) -> SparsePauliOp:
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
        pauli_strings = []
        coeffs = []
        for i, j, weight in weighted_edges:
            pauli_string = ["I"] * num_qubits
            pauli_string[i] = "Z"
            pauli_string[j] = "Z"
            pauli_strings.append("".join(pauli_string))
            coeffs.append(weight)
        return SparsePauliOp(pauli_strings, coeffs)


class HOPFObservable(Observable):
    """Observable for the Heavy Output Probability Fidelity (HOPF)."""

    @classmethod
    def id(cls) -> str:
        return "hopf"

    # Because this is not an expectation value calculation, we cannot leverage the
    # common base class implementation
    def calc_observable(
        self,
        uncompiled_circuit: QuantumCircuit,
        compiled_circuit: QuantumCircuit,
        noise_model: NoiseModel = None,
    ) -> Tuple[float, float, float, float]:
        def estimate_heavy_output_prob(
            circuit: QuantumCircuit, noise_model: NoiseModel
        ) -> float:
            heavy_bitstrings = self.get_heavy_bitstrings(circuit)
            simulator = AerSimulator(
                method="statevector",
                noise_model=noise_model,
                max_parallel_threads=1,
            )
            result = simulator.run(circuit).result()
            heavy_counts = sum(
                result.get_counts().get(bitstring, 0) for bitstring in heavy_bitstrings
            )
            nshots = 1024
            return (
                heavy_counts - 2 * math.sqrt(heavy_counts * (nshots - heavy_counts))
            ) / nshots

        uncompiled_circuit.measure_all()
        compiled_circuit.measure_all()

        uncompiled_ideal = estimate_heavy_output_prob(uncompiled_circuit, None)
        compiled_ideal = estimate_heavy_output_prob(compiled_circuit, None)
        uncompiled_noisy = estimate_heavy_output_prob(uncompiled_circuit, noise_model)
        compiled_noisy = estimate_heavy_output_prob(compiled_circuit, noise_model)

        return uncompiled_ideal, compiled_ideal, uncompiled_noisy, compiled_noisy

    def get_heavy_bitstrings(self, circuit: QuantumCircuit) -> Set[str]:
        simulator = AerSimulator(method="statevector", max_parallel_threads=1)
        result = simulator.run(circuit, shots=1024).result()
        counts = list(result.get_counts().items())
        median = np.median([c for (_, c) in counts])
        return set(bitstring for (bitstring, p) in counts if p > median)
