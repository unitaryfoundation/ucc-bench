from .base_compiler import BaseCompiler
from ucc import __version__ as ucc_version
from ucc import compile

# UCC uses qiskit internally
## TODO: ucc should expose a circuit type vs. assuming always qiskit?
from qiskit import QuantumCircuit
from qiskit.providers import Backend
from typing import Optional
from qbraid import transpile
from ..registry import register


@register.compiler("ucc")
class UCCCompiler(BaseCompiler[QuantumCircuit]):
    """
    Wrapper for benchmarking ucc compiler.
    """

    @classmethod
    def version(cls) -> str:
        return ucc_version

    def qasm_to_native(self, qasm: str) -> QuantumCircuit:
        # Need to manually specifiy since id != "qiskit"
        return transpile(qasm, "qiskit")

    def compile(
        self, circuit: QuantumCircuit, target_device: Optional[Backend] = None
    ) -> QuantumCircuit:
        if target_device is not None:
            return compile(circuit, target_backend=target_device)
        else:
            return compile(
                circuit,
                target_gateset={"rx", "ry", "rz", "h", "cx"},
            )

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
