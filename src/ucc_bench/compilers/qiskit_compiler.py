from .base_compiler import BaseCompiler
from qiskit import (
    QuantumCircuit,
    transpile as qiskit_transpile,
    __version__ as qiskit_version,
)
from ..registry import register


@register.compiler("qiskit")
class QiskitCompiler(BaseCompiler[QuantumCircuit]):
    """
    Wrapper for benchmarking qiskit compiler.

    Uses optimization_level 3 and compiles to the RX,RY,RZ,H,CX basis gates.
    """

    @classmethod
    def version(cls) -> str:
        return qiskit_version

    def compile(self, circuit: QuantumCircuit) -> QuantumCircuit:
        return qiskit_transpile(
            circuit,
            optimization_level=3,
            basis_gates=["rz", "rx", "ry", "h", "cx"],
        )

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
