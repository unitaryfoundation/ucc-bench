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
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter, ParameterVector
from qiskit.circuit.library.standard_gates import XGate


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
        N (int): Number of qubits

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


def qcnn_circuit(N, seed=12345):
    """A circuit to generate a Quantum Convolutional Neural Network

    Parameters:
        N (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    rng = np.random.default_rng(seed=seed)

    qc = QuantumCircuit(N)
    num_layers = int(np.ceil(np.log2(N)))
    i_conv = 0
    for i_layer in range(num_layers):
        for i_sub_layer in [0, 2**i_layer]:
            for i_q1 in range(i_sub_layer, N, 2 ** (i_layer + 1)):
                i_q2 = 2**i_layer + i_q1
                if i_q2 < N:
                    qc.rxx(rng.random(), i_q1, i_q2)
                    qc.ry(rng.random(), i_q1)
                    qc.ry(rng.random(), i_q2)
                    i_conv += 1

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
