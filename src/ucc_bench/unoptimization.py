"""Quantum circuit unoptimization (elementary recipe) utilities.

Implements the four-step recipe described in arXiv:2311.03805, exposed as
`unoptimize_circuit` for use in ucc-bench prior to compilation.
"""

from __future__ import annotations

import random
import warnings
from typing import Any, Optional, Dict, List, Literal

import numpy as np
from qiskit import QuantumCircuit, transpile as qiskit_transpile
from qiskit.circuit.equivalence_library import SessionEquivalenceLibrary
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator, random_unitary
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import (
    BasisTranslator,
    Decompose,
    UnrollCustomDefinitions,
)


def unoptimize_circuit(
    qc: QuantumCircuit,
    iterations: int = 1,
    strategy: Literal["concatenated", "random"] = "concatenated",
    decomposition_method: Literal["default", "kak", "basis"] = "default",
    optimization_level: int = 3,
    seed: Optional[int] = None,
    synthesize: bool = True,
) -> QuantumCircuit:
    """Apply the elementary recipe to a quantum circuit multiple times.

    Parameters
    ----------
    qc: QuantumCircuit
        Input circuit to transform.
    iterations: int
        Number of times to apply the recipe.
    strategy: str
        Strategy used in gate insertion. One of {"concatenated", "random"}.
    decomposition_method: str
        Decomposition method for unitary synthesis. One of {"default", "kak", "basis"}.
    optimization_level: int
        Qiskit transpile optimization level for the final synthesis step.

    Returns
    -------
    QuantumCircuit
        The transformed (unoptimized) circuit.
    """
    # Optional determinism
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    new_qc = qc.copy()
    for i in range(iterations):
        derived_seed = (seed + i) if seed is not None else None
        new_qc, b1_info = _insert(new_qc, strategy, seed=derived_seed)
        if b1_info is None:
            # Could not apply this iteration; continue gracefully
            continue
        new_qc = _swap(new_qc, b1_info)
        new_qc = _decompose(new_qc, method=decomposition_method)
        if synthesize:
            new_qc = _synthesize(new_qc, optimization_level=optimization_level)
    return new_qc


def _insert(
    qc: QuantumCircuit,
    strategy: str = "concatenated",
    seed: Optional[int] = None,
) -> tuple[QuantumCircuit, Optional[Dict[str, Any]]]:
    """Insert a two-qubit gate A and its Hermitian conjugate A† between two gates B1 and B2.

    Returns the modified circuit and information about B1 for subsequent steps.
    """
    # Collect all two-qubit gates with their indices and qubits
    two_qubit_gates: List[Dict[str, Any]] = []

    for idx, instruction in enumerate(qc.data):
        instr = instruction.operation
        qargs = instruction.qubits
        if len(qargs) == 2:
            qubit_indices = [qc.find_bit(qarg).index for qarg in qargs]
            two_qubit_gates.append(
                {"index": idx, "qubits": qubit_indices, "gate": instr}
            )

    found_pair = False
    b1_idx = b1_qubits = b1_gate = shared_qubit = None

    if strategy == "concatenated":
        # Find a pair of gates that share a common qubit
        for i in range(len(two_qubit_gates)):
            for j in range(i + 1, len(two_qubit_gates)):
                qubits_i = set(two_qubit_gates[i]["qubits"])
                qubits_j = set(two_qubit_gates[j]["qubits"])
                common_qubits = qubits_i & qubits_j
                if len(common_qubits) == 1:
                    b1_idx = two_qubit_gates[i]["index"]
                    b1_qubits = two_qubit_gates[i]["qubits"]
                    b1_gate = two_qubit_gates[i]["gate"]
                    shared_qubit = list(common_qubits)[0]
                    found_pair = True
                    break
            if found_pair:
                break
    elif strategy == "random":
        if two_qubit_gates:
            gate_info = random.choice(two_qubit_gates)
            b1_idx = gate_info["index"]
            b1_qubits = gate_info["qubits"]
            b1_gate = gate_info["gate"]
            shared_qubit = b1_qubits[0]
            found_pair = True
    else:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Available strategies are 'concatenated' and 'random'."
        )

    if not found_pair or b1_idx is None or b1_qubits is None:
        warnings.warn(
            "No suitable pair of two-qubit gates found. Skipping gate insertion."
        )
        return qc, None

    # Generate a random two-qubit unitary A and its adjoint A†
    a = random_unitary(4, seed=seed)
    a_dag = a.adjoint()

    # Choose a third qubit distinct from the pair
    all_qubits = set(range(qc.num_qubits))
    other_qubits = list(all_qubits - set(b1_qubits))
    if not other_qubits:
        warnings.warn("Not enough qubits to perform gate insertion. Skipping.")
        return qc, None
    third_qubit = other_qubits[0]
    if shared_qubit is None:
        warnings.warn("Shared qubit is None. Skipping gate insertion.")
        return qc, None

    # Map indices back to qubits
    qubit_map = {qc.find_bit(q).index: q for q in qc.qubits}

    # Create a new circuit and insert A† A after B1
    new_qc = QuantumCircuit(*qc.qregs, *qc.cregs)

    # Copy the gates up to and including B1
    for instruction in qc.data[: b1_idx + 1]:
        new_qc.append(instruction.operation, instruction.qubits, instruction.clbits)

    # Insert A†, A on qubits [shared_qubit, third_qubit]
    qubits_for_a = [qubit_map[shared_qubit], qubit_map[third_qubit]]
    new_qc.unitary(a_dag, qubits_for_a, label="A_dag")
    new_qc.unitary(a, qubits_for_a, label="A")

    # Copy the remaining gates
    for instruction in qc.data[b1_idx + 1 :]:
        new_qc.append(instruction.operation, instruction.qubits, instruction.clbits)

    # Prepare B1_info for swap operation
    b1_info = {
        "index": b1_idx,
        "qubits": b1_qubits,
        "gate": b1_gate,
        "shared_qubit": shared_qubit,
        "third_qubit": third_qubit,
        "A": a,
    }

    return new_qc, b1_info


def _swap(qc: QuantumCircuit, b1_info: Dict[str, Any]) -> QuantumCircuit:
    r"""Swap the B1 gate with the A† gate in the circuit, replacing A† with \widetilde{A^\dagger}."""
    b1_idx = b1_info["index"]
    b1_qubits = b1_info["qubits"]
    b1_gate = b1_info["gate"]
    a = b1_info["A"]
    shared_qubit = b1_info["shared_qubit"]
    third_qubit = b1_info["third_qubit"]

    # Map qubit indices to qubit objects
    qubit_map = {qc.find_bit(q).index: q for q in qc.qubits}

    # Get the operators
    b1_operator = Operator(b1_gate)
    a_operator = Operator(a)
    a_dagger_operator = a_operator.adjoint()

    # Determine the qubits involved
    qubits_involved = sorted(set(b1_qubits + [shared_qubit, third_qubit]))
    qubits_involved_objs = [qubit_map[q] for q in qubits_involved]
    num_qubits_involved = len(qubits_involved)

    # Create mapping from qubit indices to positions
    qubit_positions = {q: idx for idx, q in enumerate(qubits_involved)}

    # Build B1_operator_full on the involved subspace
    b1_operator_full = Operator(np.eye(2**num_qubits_involved))
    b1_qubit_positions = [qubit_positions[q] for q in b1_qubits]
    b1_operator_full = b1_operator_full.compose(b1_operator, qargs=b1_qubit_positions)

    # Build A_dagger_operator_full on the involved subspace
    a_dagger_operator_full = Operator(np.eye(2**num_qubits_involved))
    a_dagger_qubits = [shared_qubit, third_qubit]
    a_dagger_qubit_positions = [qubit_positions[q] for q in a_dagger_qubits]
    a_dagger_operator_full = a_dagger_operator_full.compose(
        a_dagger_operator, qargs=a_dagger_qubit_positions
    )

    # Compute \widetilde{A^\dagger}
    b1_operator_full_dagger = b1_operator_full.adjoint()
    widetilde_a_dagger_operator = b1_operator_full_dagger.dot(
        a_dagger_operator_full
    ).dot(b1_operator_full)

    # Create UnitaryGate from \widetilde{A^\dagger}
    widetilde_a_dagger_gate = UnitaryGate(
        widetilde_a_dagger_operator.data, label=r"$\widetilde{A^{\dagger}}$"
    )

    # Create a new quantum circuit and perform the swap
    new_qc = QuantumCircuit(*qc.qregs, *qc.cregs)

    # Copy the gates up to B1_idx
    for i in range(b1_idx):
        instruction = qc.data[i]
        new_qc.append(instruction.operation, instruction.qubits, instruction.clbits)

    # Insert \widetilde{A^\dagger} at position B1_idx
    new_qc.append(widetilde_a_dagger_gate, qubits_involved_objs)

    # Insert B1 gate at position B1_idx + 1
    new_qc.append(b1_gate, [qubit_map[q] for q in b1_qubits])

    # Copy the remaining gates, skipping the original A_dagger gate
    for i in range(b1_idx + 2, len(qc.data)):
        instruction = qc.data[i]
        new_qc.append(instruction.operation, instruction.qubits, instruction.clbits)

    return new_qc


def _decompose(qc: QuantumCircuit, method: str = "default") -> QuantumCircuit:
    """Decompose multi-qubit unitary gates into elementary gates."""
    if method == "default":
        return qc.decompose()
    elif method == "kak":
        pm = PassManager()
        pm.append(Decompose())
        return pm.run(qc)
    elif method == "basis":
        basis_gates = ["cx", "u3"]
        pm = PassManager()
        pm.append(UnrollCustomDefinitions(SessionEquivalenceLibrary, basis_gates))
        pm.append(BasisTranslator(SessionEquivalenceLibrary, basis_gates))
        return pm.run(qc)
    else:
        raise ValueError(f"Unknown decomposition method: {method}")


def _synthesize(qc: QuantumCircuit, optimization_level: int = 3) -> QuantumCircuit:
    """Synthesize the circuit using Qiskit transpiler with a given optimization level."""
    return qiskit_transpile(
        qc, optimization_level=optimization_level, basis_gates=["cx", "u3"]
    )
