# This file has been modified from the original version in Qiskit.
# This code is part of Qiskit.
#
# (C) Copyright IBM 2024.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""Test circuit generation"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library.standard_gates import XGate
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import PauliEvolutionGate

import scipy


##############################################################################
# Main benchmark circuits
# Although these are written in Qiskit, we try to avoid using the qiskit.library
# implementations, so that we can more directly translate to other circuit
# frameworks at a structured level.


def prep_select_circuit(N: int, target_state: int) -> QuantumCircuit:
    """
    Prepare a "preparation and selection" circuit on N qubits to select the target_state.
    This is like an oracle step in a Grover's search algorithm.

    Parameters:
        N (int): Number of qubits
        target_state (int): The integer representation of the target state to select (0 to 2^N - 1)
    """
    assert 0 <= target_state < 2**N, "target_state must be in the range [0, 2^N - 1]"
    target_state = f"{target_state:0{N}b}"

    qc = QuantumCircuit(N)
    qc.h(range(N))

    # Flip the target state to be all |1>
    # Qiskit is little-endian, so we reverse the bit order
    for qubit, bit in enumerate(reversed(target_state)):
        if bit == "0":
            qc.x(qubit)

    # Flip the phase on just the target state
    controls = list(range(N - 1))
    target = N - 1
    qc.mcp(np.pi, controls, target)

    # Revert the flip
    for qubit, bit in enumerate(reversed(target_state)):
        if bit == "0":
            qc.x(qubit)

    return qc


def qcnn_circuit(N, seed=12345):
    """
    A circuit that implements the convolutional layers of a QCNN.

    Given a number of qubits N, the circuit applies a series of RXX and RY gates
    in a hierarchical manner, similar to a classical convolutional neural network.

    Each layer connects pairs of qubits that are 2^layer_index apart, followed by single
    qubit RY rotations (similar to activation functions in classical CNNs).

    Note this doesn't do any pooling or measurement, its just the convolutional layers.

    Parameters:
        N (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    rng = np.random.default_rng(seed=seed)

    qc = QuantumCircuit(N)
    num_layers = int(np.ceil(np.log2(N)))
    for i_layer in range(num_layers):
        for i_sub_layer in [0, 2**i_layer]:
            for i_q1 in range(i_sub_layer, N, 2 ** (i_layer + 1)):
                i_q2 = 2**i_layer + i_q1
                if i_q2 < N:
                    qc.rxx(rng.random(), i_q1, i_q2)
                    qc.ry(rng.random(), i_q1)
                    qc.ry(rng.random(), i_q2)

    return qc


def qft_circuit(N: int) -> QuantumCircuit:
    """
    Create a Quantum Fourier Transform (QFT) circuit on N qubits
    """
    qc = QuantumCircuit(N)

    for i in range(N):
        for j in range(i):
            phi = np.pi * (2 ** (j - i))
            qc.cp(phi, j, i)
        qc.h(i)

    # Final bit-reversal to match most significant to least significant ordering
    for k in range(N // 2):
        qc.swap(k, N - k - 1)

    return qc


def qv_circuit(N: int, depth: int, seed: int = 12345) -> QuantumCircuit:
    """
    Generate a quantum volume circuit for N qubits and given depth.

    From [1]_, a quantum volume circuit consists of layers of random elements
    of SU(4) applied between pairs of qubits in a random partition.

    Parameters:
        N (int): Number of qubits
        depth (int): Depth of the circuit (layers of SU(4) operations)
        seed (int): Random seed for reproducibility
    Returns:
        QuantumCircuit: The generated quantum volume circuit

    References:

    [1] A. Cross et al. Validating quantum computers using
    randomized model circuits, Phys. Rev. A 100, 032328 (2019).
    `arXiv:1811.12926 <https://arxiv.org/abs/1811.12926>`__
    """
    import numpy as np

    rng = np.random.default_rng(seed=seed)

    qc = QuantumCircuit(N)
    width = N // 2
    # Below code from https://github.com/Qiskit/qiskit/blob/c99f325baac1ea19ec4a316299579e9101e76271/qiskit/circuit/library/quantum_volume.py

    # For each layer, generate a permutation of qubits
    # Then generate and apply a Haar-random SU(4) to each pair

    # Generate all the unitaries at once for efficiency,
    unitaries = scipy.stats.unitary_group.rvs(4, depth * width, rng).reshape(
        depth, width, 4, 4
    )
    qubits = tuple(range(N))
    for row in unitaries:
        perm = rng.permutation(N)
        for w, unitary in enumerate(row):
            gate = UnitaryGate(unitary, check_input=False, num_qubits=2)
            qubit = 2 * w
            qc.append(gate, [qubits[perm[qubit]], qubits[perm[qubit + 1]]])
    return qc


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


def square_heisenberg_circuit(N: int, depth: int, seed: int = 12345) -> QuantumCircuit:
    """
    Generate a circuit that simulates a square lattice Heisenberg model on N^2 qubits.

    This is based on Hamlib (https://arxiv.org/pdf/2306.13126) and corres;onding to equation 9
    in the paper, using only an XXX model. We assume a square lattice with periodic boundary conditions.

    This one considers H = -0.5

    Parameters:
        N (int): The lattice will be N x N, so total qubits is N^2
        depth (int): Number of Trotter steps to use
        seed (int): Random seed for reproducibility
    """

    pstrings = []
    # Pairwise Paulis
    for op in "X", "Y", "Z":
        for p in lattice_to_qubit_mapping(N):
            pstring = ["I"] * (N * N)
            pstring[p[0]] = pstring[p[1]] = op
            pstrings.append("".join(pstring))
    # External field
    pstrings.extend(
        "".join(["I" * n, "Z", "I" * (N * N - n - 1)]) for n in range(N * N)
    )
    coeffs = [1.0] * (len(pstrings) - (N * N)) + [0.5] * (N * N)

    # convert to circuit via trotterization
    qc = QuantumCircuit(N * N)
    qc.add(PauliEvolutionGate(SparsePauliOp(pstrings, coeffs), reps=depth).decompose())
    return qc


##############################################################################


def dtc_unitary(num_qubits, g=0.95, seed=12345):
    """Generate a Floquet unitary for DTC evolution
    Parameters:
        num_qubits (int): Number of qubits
        g (float): Optional. Parameter controlling amount of x-rotation, default=0.95
        seed (int): Optional. Seed the random number generator, default=12345

    Returns:
        QuantumCircuit: Unitary operator
    """
    rng = np.random.default_rng(seed=seed)
    qc = QuantumCircuit(num_qubits)

    # X rotation by g*pi on all qubits (simulates imperfect periodic flips)
    for i in range(num_qubits):
        qc.rx(g * np.pi, i)

    # Ising interaction (only couples adjacent spins with random coupling strengths)
    for i in range(0, num_qubits - 1, 2):
        phi = rng.uniform(low=np.pi / 16, high=3 * np.pi / 16)
        qc.rzz(2 * phi, i, i + 1)
    for i in range(1, num_qubits - 1, 2):
        phi = rng.uniform(low=np.pi / 16, high=3 * np.pi / 16)
        qc.rzz(2 * phi, i, i + 1)

    # Longitudinal fields for disorder
    for i in range(num_qubits):
        h = rng.uniform(low=-np.pi, high=np.pi)
        qc.rz(h * np.pi, i)

    return qc


def multi_control_circuit(num_qubits):
    """A circuit with multi-control X-gates

    Parameters:
        num_qubits (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    gate = XGate()
    out = QuantumCircuit(num_qubits)
    out.compose(gate, range(gate.num_qubits), inplace=True)
    for _ in range(num_qubits - 1):
        gate = gate.control()
        out.compose(gate, range(gate.num_qubits), inplace=True)
    return out


def bv_all_ones(N):
    """A circuit to generate a BV circuit over N
    qubits for an all-ones bit-string

    Parameters:
        N (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    qc = QuantumCircuit(N, N - 1)
    qc.x(N - 1)
    qc.h(range(N))
    qc.cx(range(N - 1), N - 1)
    qc.h(range(N - 1))
    qc.measure(range(N - 1), range(N - 1))
    return qc


def trivial_bvlike_circuit(N):
    """A trivial circuit that should boil down
    to just a X and Z gate since they commute out

    Parameters:
        N (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    qc = QuantumCircuit(N)
    for kk in range(N - 1):
        qc.cx(kk, N - 1)
    qc.x(N - 1)
    qc.z(N - 2)
    for kk in range(N - 2, -1, -1):
        qc.cx(kk, N - 1)
    return qc


def random_clifford_circuit(num_qubits, seed=12345):
    """Generate a random clifford circuit
    Parameters:
        num_qubits (int): Number of qubits
        seed (int): Optional. Seed the random number generator, default=12345

    Returns:
        QuantumCircuit: Clifford circuit
    """
    # This code is used to generate the QASM file
    from qiskit.circuit.random import random_clifford_circuit

    gates = ["cx", "cz", "cy", "swap", "x", "y", "z", "s", "sdg", "h"]
    qc = random_clifford_circuit(
        num_qubits,
        gates=gates,
        num_gates=10 * num_qubits * num_qubits,
        seed=seed,
    )
    return qc


def random_clifford_optimized(num_qubits, seed=12345):
    """Generate a random clifford, using optimized decomposition
    Parameters:
        num_qubits (int): Number of qubits
        seed (int): Optional. Seed the random number generator, default=12345

    Returns:
        QuantumCircuit: Clifford circuit
    """
    # This code is used to generate the QASM file
    from qiskit.quantum_info import random_clifford

    cliff = random_clifford(num_qubits, seed=seed)
    qc = cliff.to_circuit()

    return qc


# Step 1: Create a Parameterized Quantum Circuit (Ansatz)
def VQE_ansatz(num_qubits, num_layers):
    params = ParameterVector("θ", length=num_qubits * num_layers)
    qc = QuantumCircuit(num_qubits)

    param_index = 0
    for layer in range(num_layers):
        # Add RX rotation for each qubit
        for qubit in range(num_qubits):
            qc.rx(params[param_index], qubit)
            param_index += 1
        # Add entangling gates (CX) in a linear chain
        for qubit in range(num_qubits - 1):
            qc.cx(qubit, qubit + 1)
    return qc


def qaoa_ising_ansatz(num_qubits, num_layers):
    """
    Generates a custom QAOA ansatz for a nearest-neighbor Ising Hamiltonian.

    Args:
        num_qubits (int): Number of qubits for the Ising Hamiltonian.
        num_layers (int): Number of QAOA layers.

    Returns:
        QuantumCircuit: Custom QAOA ansatz circuit.
    """
    # Initialize a quantum circuit with the required number of qubits
    qc = QuantumCircuit(num_qubits)

    # Define the parameters for each layer (gamma for cost and beta for mixer)
    gamma = [Parameter(f"γ_{i}") for i in range(num_layers)]
    beta = [Parameter(f"β_{i}") for i in range(num_layers)]

    # Create the QAOA circuit layer by layer
    for layer in range(num_layers):
        # Cost Hamiltonian Evolution: Apply ZZ interactions and single-qubit Z rotations
        for i in range(num_qubits):
            # Apply nearest-neighbor ZZ interaction if not at the last qubit
            if i < num_qubits - 1:
                qc.cx(i, i + 1)
                qc.rz(2 * gamma[layer], i + 1)
                qc.cx(i, i + 1)

            # Apply local Z rotation (Z_i) for each qubit
            qc.rz(2 * gamma[layer], i)

        # Mixer Hamiltonian Evolution: Apply RX rotations
        for i in range(num_qubits):
            qc.rx(2 * beta[layer], i)

    return qc


def initialize_qubits(
    circuit: QuantumCircuit, qreg_data: QuantumRegister
) -> QuantumCircuit:
    """Initialize qubit to |1>"""
    circuit.x(qreg_data[0])
    circuit.barrier(qreg_data)
    return circuit


def encode_bit_flip(circuit, state, ancillas) -> QuantumCircuit:
    """Encode bit-flip. This is done by simply adding a cx"""
    for ancilla in ancillas:
        circuit.cx(state, ancilla)
    circuit.barrier(state, *ancillas)
    return circuit


def measure_syndrome_bit(circuit, qreg_data, qreg_measure, creg_measure):
    """
    Measure the syndrome by measuring the parity.
    We reset our ancilla qubits after measuring the stabilizer
    so we can reuse them for repeated stabilizer measurements.
    Because we have already observed the state of the qubit,
    we can write the conditional reset protocol directly to
    avoid another round of qubit measurement if we used
    the `reset` instruction.
    """
    circuit.cx(qreg_data[0], qreg_measure[0])
    circuit.cx(qreg_data[1], qreg_measure[0])
    circuit.cx(qreg_data[0], qreg_measure[1])
    circuit.cx(qreg_data[2], qreg_measure[1])
    circuit.barrier(*qreg_data, *qreg_measure)
    circuit.measure(qreg_measure, creg_measure)
    with circuit.if_test((creg_measure[0], 1)):
        circuit.x(qreg_measure[0])
    with circuit.if_test((creg_measure[1], 1)):
        circuit.x(qreg_measure[1])
    circuit.barrier(*qreg_data, *qreg_measure)
    return circuit


def apply_correction_bit(circuit, qreg_data, creg_syndrome):
    """We can detect where an error occurred and correct our state"""
    with circuit.if_test((creg_syndrome, 3)):
        circuit.x(qreg_data[0])
    with circuit.if_test((creg_syndrome, 1)):
        circuit.x(qreg_data[1])
    with circuit.if_test((creg_syndrome, 2)):
        circuit.x(qreg_data[2])
    circuit.barrier(qreg_data)
    return circuit


def apply_final_readout(circuit, qreg_data, creg_data):
    """Read out the final measurements"""
    circuit.barrier(qreg_data)
    circuit.measure(qreg_data, creg_data)
    return circuit


def qec_bitflip_code(apply_correction=True, measure_all=False) -> QuantumCircuit:
    """
    Returns a QuantumCircuit implementing the 3-qubit bit-flip code with error correction. Modified from https://quantum.cloud.ibm.com/docs/en/tutorials/repetition-codes
    """
    qreg_data = QuantumRegister(3)
    qreg_measure = QuantumRegister(2)
    creg_data = ClassicalRegister(3, name="data")
    creg_syndrome = ClassicalRegister(2, name="syndrome")
    creg_measure = ClassicalRegister(2, name="measure")
    state_data = qreg_data[0]
    ancillas_data = qreg_data[1:]

    circuit = QuantumCircuit(
        qreg_data, qreg_measure, creg_data, creg_syndrome, creg_measure
    )

    # Reset the state and ancilla qubits to ensure a clean start
    circuit.reset(state_data)
    for ancilla in ancillas_data:
        circuit.reset(ancilla)

    circuit = initialize_qubits(circuit, qreg_data)

    circuit = encode_bit_flip(circuit, state_data, ancillas_data)
    circuit = measure_syndrome_bit(
        circuit, qreg_data, qreg_measure, creg_measure, creg_syndrome
    )

    if apply_correction:
        circuit = apply_correction_bit(circuit, qreg_data, creg_syndrome)

    if measure_all:
        circuit = apply_final_readout(circuit, qreg_data, creg_data)
    return circuit
