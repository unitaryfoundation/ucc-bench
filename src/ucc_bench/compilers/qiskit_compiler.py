from .base_compiler import BaseCompiler
from qiskit import (
    QuantumCircuit,
    transpile as qiskit_transpile,
    __version__ as qiskit_version,
)
from qiskit.providers import Backend
from typing import Optional
from qbraid import transpile

from ..registry import register


@register.compiler("qiskit-default")
class QiskitCompiler(BaseCompiler[QuantumCircuit]):
    """
    Wrapper for benchmarking qiskit compiler.

    Uses optimization_level 3 and compiles to the RX,RY,RZ,H,CX basis gates.
    """

    @classmethod
    def version(cls) -> str:
        return qiskit_version

    def qasm_to_native(self, qasm: str) -> QuantumCircuit:
        # Specify since we have -default suffix
        return transpile(qasm, "qiskit")

    def compile(
        self, circuit: QuantumCircuit, target_device: Optional[Backend] = None
    ) -> QuantumCircuit:
        if target_device is not None:
            return qiskit_transpile(
                circuit,
                optimization_level=3,
                backend=target_device,
            )
        else:
            return qiskit_transpile(
                circuit, optimization_level=3, basis_gates=["rz", "rx", "ry", "h", "cx"]
            )

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
