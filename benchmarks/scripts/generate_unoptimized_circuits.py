#!/usr/bin/env python3
"""Generate pre-unoptimized QASM files for the compilation benchmarks.

This script applies the elementary unoptimization recipe from
``ucc_bench.unoptimization`` to the canonical benchmark circuits and writes the
resulting QASM to ``benchmarks/circuits/unoptimized``. It keeps the
configuration in one place so contributors can regenerate the assets if the
recipe changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from qiskit import QuantumCircuit, qasm2

from ucc_bench.unoptimization import unoptimize_circuit


@dataclass(frozen=True)
class CircuitTask:
    source: Path
    target: Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CIRCUIT_ROOT = REPO_ROOT / "benchmarks" / "circuits"
UNOPT_ROOT = CIRCUIT_ROOT / "unoptimized"

# Shared parameters for this batch of unoptimized circuits. Adjust these values
# if we want to regenerate the artefacts with a different configuration.
UNOPT_KWARGS = dict(
    iterations=1,
    strategy="concatenated",
    decomposition_method="default",
    optimization_level=3,
    seed=42,
)

TASKS: Iterable[CircuitTask] = (
    CircuitTask(
        source=CIRCUIT_ROOT
        / "benchpress"
        / "qaoa_barabasi_albert_N100_3reps_basis_rz_rx_ry_cx.qasm",
        target=UNOPT_ROOT / "qaoa_barabasi_albert_N100_3reps_unopt.qasm",
    ),
    CircuitTask(
        source=CIRCUIT_ROOT / "benchpress" / "qv_N100_12345_basis_rz_rx_ry_cx.qasm",
        target=UNOPT_ROOT / "qv_N100_12345_unopt.qasm",
    ),
    CircuitTask(
        source=CIRCUIT_ROOT / "benchpress" / "qft_N100_basis_rz_rx_ry_cx.qasm",
        target=UNOPT_ROOT / "qft_N100_unopt.qasm",
    ),
    CircuitTask(
        source=CIRCUIT_ROOT
        / "benchpress"
        / "square_heisenberg_N100_basis_rz_rx_ry_cx.qasm",
        target=UNOPT_ROOT / "square_heisenberg_N100_unopt.qasm",
    ),
    CircuitTask(
        source=CIRCUIT_ROOT / "ucc" / "prep_select_N25_ghz_basis_rz_rx_ry_h_cx.qasm",
        target=UNOPT_ROOT / "prep_select_N25_ghz_unopt.qasm",
    ),
    CircuitTask(
        source=CIRCUIT_ROOT / "ucc" / "qcnn_N100_7layers_basis_rz_rx_ry_h_cx.qasm",
        target=UNOPT_ROOT / "qcnn_N100_7layers_unopt.qasm",
    ),
)


def generate() -> None:
    UNOPT_ROOT.mkdir(parents=True, exist_ok=True)
    for task in TASKS:
        circuit = QuantumCircuit.from_qasm_file(task.source)
        unopt_circuit = unoptimize_circuit(circuit, **UNOPT_KWARGS)
        header = (
            "// Elementary unoptimization applied to "
            f"{task.source.relative_to(REPO_ROOT)}\n"
        )
        header += "// iterations={iterations}, strategy={strategy}, decomposition={decomposition_method}, opt_level={optimization_level}, seed={seed}\n".format(
            **UNOPT_KWARGS
        )
        header += (
            "// Generated via benchmarks/scripts/generate_unoptimized_circuits.py\n"
        )
        qasm_body = qasm2.dumps(unopt_circuit)
        task.target.write_text(header + qasm_body)
        print(
            f"Wrote {task.target.relative_to(REPO_ROOT)} (qubits={unopt_circuit.num_qubits}, ops={unopt_circuit.size()})"
        )


if __name__ == "__main__":
    generate()
