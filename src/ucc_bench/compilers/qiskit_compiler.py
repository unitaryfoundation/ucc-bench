from .base_compiler import BaseCompiler
from qiskit import (
    QuantumCircuit,
    transpile as qiskit_transpile,
    __version__ as qiskit_version,
)
from qiskit.transpiler import Target
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
        self, circuit: QuantumCircuit, target_device: Optional[Target] = None
    ) -> QuantumCircuit:
        return qiskit_transpile(
            circuit,
            optimization_level=3,
            basis_gates=["rz", "rx", "ry", "h", "cx"],
            coupling_map=target_device.build_coupling_map() if target_device else None,
        )

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
