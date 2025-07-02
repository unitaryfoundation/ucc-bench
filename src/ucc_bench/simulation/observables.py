"""
This module provides functionality calculating expectation values of compiled circuits
with and without noise. It has some common functions for calculating these values given an
observable, represented as a qiskit Operator.

Users can also register their own observables using the `@register.observable` decorator for
use in the benchmarking framework. The observables should be defined as functions that take the number of qubits
in the circuit as an argument and return a Qiskit Operator representing the observable to measure.
"""

from math import sqrt
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector, SparsePauliOp
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
import numpy as np
from ..registry import register
from ..results import SimulationMetrics


# ----------------------------------------------------
# Simulation functions to calculate expectation values
# ----------------------------------------------------


def simulate_density_matrix_with_noise(
    circuit: QuantumCircuit, noise_model: NoiseModel
):
    """Simulates the given quantum circuit using a density matrix simulator with a specified noise model."""
    simulator = AerSimulator(
        method="density_matrix",
        noise_model=noise_model,
        max_parallel_threads=1,
    )
    return simulator.run(circuit).result().data()["density_matrix"]


def calc_expectation_value(
    observable: Operator,
    uncompiled_circuit: QuantumCircuit,
    compiled_circuit: QuantumCircuit,
    noise_model: NoiseModel,
) -> SimulationMetrics:
    """Calculates the ideal and noisy expectation value of the observable for uncompiled and compiled circuits."""

    # Ideal observables
    uncompiled_state = Statevector.from_instruction(uncompiled_circuit)
    compiled_state = Statevector.from_instruction(compiled_circuit)
    uncompiled_ideal = np.real(uncompiled_state.expectation_value(observable))
    compiled_ideal = np.real(compiled_state.expectation_value(observable))

    # Noisy observables
    uncompiled_circuit.save_density_matrix()
    compiled_circuit.save_density_matrix()

    uncompiled_density_matrix = simulate_density_matrix_with_noise(
        uncompiled_circuit, noise_model
    )
    compiled_density_matrix = simulate_density_matrix_with_noise(
        compiled_circuit, noise_model
    )
    uncompiled_noisy = np.real(uncompiled_density_matrix.expectation_value(observable))
    compiled_noisy = np.real(compiled_density_matrix.expectation_value(observable))

    return SimulationMetrics(
        uncompiled_ideal=uncompiled_ideal,
        compiled_ideal=compiled_ideal,
        uncompiled_noisy=uncompiled_noisy,
        compiled_noisy=compiled_noisy,
    )


# --------------------------------------------------
# Specific observables
#
# To define a new observable to use in benchmarking, create a function
# that returns the Operator representing the observable, and decorate
# it with the `@register.observable` decorator with the associated id/name.
# --------------------------------------------------


@register.observable("computational_basis")
def generate_computational_basis_observable(
    num_qubits: int,
) -> Operator:
    return Operator.from_label("Z" * num_qubits)


@register.observable("ghz_state_projector")
def generate_ghz_state_projector(num_qubits: int) -> Operator:
    """Generates the projector for the GHZ state |0...0> + |1...1>."""
    ghz_state = Statevector.from_label("0" * num_qubits) + Statevector.from_label(
        "1" * num_qubits
    )
    ghz_state /= np.sqrt(2)
    return ghz_state.to_operator()


@register.observable("uniform_superposition_projector")
def generate_uniform_superposition_projector(num_qubits: int) -> Operator:
    """Generates the projector for the uniform superposition state."""
    raw_vec = np.ones(2**num_qubits) / np.sqrt(2**num_qubits)
    return Statevector(raw_vec).to_operator()


@register.observable("prep_select_all_ones")
def generate_prep_select_all_ones_observable(num_qubits: int) -> Operator:
    """Generate a projector that is uniform superposition over computational basis but with (-1) phase on the all ones"""
    raw_vec = np.ones(2**num_qubits) / np.sqrt(2**num_qubits)
    raw_vec[-1] *= -1
    return Statevector(raw_vec).to_operator()


def lattice_to_qubit_mapping(nnodes):
    """Generate qubit mapping for the square Heisenberg problem Hamiltonian."""
    lattice = np.arange(nnodes * nnodes).reshape(
        nnodes, nnodes
    )  # generate rows in order
    lattice[1::2, :] = lattice[1::2, ::-1]  # reverse every other row
    current = lattice.flatten()  # Flatten the arrays
    # Get right and down neighbors using roll
    right = np.roll(lattice, shift=-1, axis=1).flatten()
    down = np.roll(lattice, shift=-1, axis=0).flatten()
    return list(
        {tuple(sorted(pair)) for pair in zip(current, right)}
        | {tuple(sorted(pair)) for pair in zip(current, down)}
    )


@register.observable("hamlib_heisenberg_pbc-qubitnodes_Lx_Ly_h-0.5")
def generate_square_heisenberg_observable(num_qubits):
    """Uses the problem Hamiltonian as the observable for the square
    Heisenberg benchmarking circuit. The Hamiltonian was obtained from the
    Heisenberg dataset in the HamLib Hamiltonian library.
    Nicolas PD Sawaya et al. HamLib: A library of Hamiltonians for benchmarking
    quantum algorithms and hardware. arXiv: 2306.13126 (2024).
    link: https://arxiv.org/abs/2306.13126.
    """

    nnodes = int(sqrt(num_qubits))

    if num_qubits > nnodes**2:
        raise ValueError("Invalid qubit number for square Heisenberg circuit")

    pstrings = []
    # Pairwise Paulis
    for op in "X", "Y", "Z":
        for p in lattice_to_qubit_mapping(nnodes):
            pstring = ["I"] * num_qubits
            pstring[p[0]] = pstring[p[1]] = op
            pstrings.append("".join(pstring))
    # External field
    pstrings.extend(
        "".join(["I" * n, "Z", "I" * (num_qubits - n - 1)]) for n in range(num_qubits)
    )
    coeffs = [1.0] * (len(pstrings) - num_qubits) + [0.5] * (num_qubits)
    return SparsePauliOp(pstrings, coeffs)


@register.observable("qaoa")
def generate_qaoa_observable(num_qubits):
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


@register.observable("qcnn")
def generate_qcnn_observable(num_qubits):
    """Generates the observable for the QCNN benchmarking circuits, based on
    the observable defined in Iris Cong, Soonwon Choi, and Mikhail D. Lukin
    "Quantum Convolutional Neural Networks". (2019) arXiv 1810.03787
    (https://arxiv.org/abs/1810.03787).
    """
    pauli_strings = []
    for i in range(num_qubits - 2):
        pauli_string = ["I"] * num_qubits
        pauli_string[i : i + 3] = ["Z", "X", "Z"]
        pauli_strings.append("".join(pauli_string))
    qcnn_observable = SparsePauliOp(pauli_strings)
    return qcnn_observable
