from .base_compiler import BaseCompiler
from ucc import __version__ as ucc_version
from ucc import compile

# UCC uses qiskit internally
## TODO: ucc should expose a circuit type vs. assuming
from qiskit import QuantumCircuit
from qbraid import transpile


class UCCCompiler(BaseCompiler[QuantumCircuit]):
    """
    Wrapper for benchmarking ucc compiler.
    """

    @classmethod
    def id(cls) -> str:
        return "ucc"

    @classmethod
    def version(cls) -> str:
        return ucc_version

    def qasm_to_native(self, qasm: str) -> QuantumCircuit:
        return transpile(qasm, "qiskit")

    def compile(self, circuit: QuantumCircuit) -> QuantumCircuit:
        return compile(circuit)

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
