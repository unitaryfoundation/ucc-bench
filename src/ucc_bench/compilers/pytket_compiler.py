from .base_compiler import BaseCompiler
from pytket import __version__ as pytket_version
from pytket.passes import (
    SequencePass,
    AutoRebase,
    FullPeepholeOptimise,
)
from pytket.predicates import CompilationUnit
from pytket.circuit import OpType
from pytket import Circuit as PytketCircuit
from qbraid import transpile
from ..registry import register
from typing import Optional
from qiskit.providers import Backend


@register.compiler("pytket-peep")
class PytketPeepCompiler(BaseCompiler[PytketCircuit]):
    """
    Wrapper for benchmarking pytket compiler.

    Uses FullPeepholeOptimise and AutoRebase for compilation.
    """

    @classmethod
    def version(cls) -> str:
        return pytket_version

    def qasm_to_native(self, qasm: str) -> PytketCircuit:
        # Specify since pytket id != "pytket"
        return transpile(qasm, "pytket")

    def compile(
        self, circuit: PytketCircuit, target_device: Optional[Backend] = None
    ) -> PytketCircuit:
        if target_device is not None:
            raise ValueError("Pytket benchmark does not support target devices yet.")

        compilation_unit = CompilationUnit(circuit)
        passes = [
            FullPeepholeOptimise(),
            AutoRebase({OpType.Rx, OpType.Ry, OpType.Rz, OpType.CX, OpType.H}),
        ]
        SequencePass(passes).apply(compilation_unit)
        return compilation_unit.circuit

    def count_multi_qubit_gates(self, circuit: PytketCircuit) -> int:
        return circuit.n_gates - circuit.n_1qb_gates()
