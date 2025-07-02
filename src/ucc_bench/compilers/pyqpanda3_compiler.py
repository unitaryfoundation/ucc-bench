from .base_compiler import BaseCompiler
from ..registry import register
from typing import Optional
from qiskit.transpiler import Target

try:
    from pyqpanda3 import __version__ as pyqpanda_version
    from pyqpanda3.intermediate_compiler import (
        convert_qasm_string_to_qprog,
        convert_qprog_to_qasm,
    )
    from pyqpanda3.core import QProg
    from pyqpanda3.transpilation import Transpiler

    PYQPANDA3_AVAILABLE = True
except ImportError:
    PYQPANDA3_AVAILABLE = False

if PYQPANDA3_AVAILABLE:

    @register.compiler("pyqpanda3")
    class PyQPanda3Compiler(BaseCompiler[QProg]):
        """
        Wrapper for benchmarking pyqpanda3 compiler.
        Uses highest optimization (level 2) and targest
        RX,RY,RZ,H,CX gate set.
        """

        @classmethod
        def is_supported(cls) -> bool:
            return True

        @classmethod
        def version(cls) -> str:
            return pyqpanda_version

        def qasm_to_native(self, qasm: str) -> QProg:
            # Not supported by qbraid yet
            return convert_qasm_string_to_qprog(qasm)

        def native_to_qasm(self, circuit: QProg) -> str:
            return convert_qprog_to_qasm(circuit)

        def compile(
            self, circuit: QProg, target_device: Optional[Target] = None
        ) -> QProg:
            if target_device is not None:
                raise ValueError(
                    "Pyqpanda3 benchmark does not support target devices yet."
                )
            transpiler = Transpiler()
            return transpiler.transpile(
                circuit,
                init_mapping={},
                optimization_level=2,
                basic_gates=["RX", "RY", "RZ", "H", "CNOT"],
            )

        def count_multi_qubit_gates(self, circuit: QProg) -> int:
            return sum(
                count for (gate, count) in circuit.count_ops(only_q2=True).items()
            )
else:

    @register.compiler("pyqpanda3")
    class PyQPanda3Compiler(BaseCompiler):
        """
        Placeholder for pyqpanda3 compiler on unsupported platforms.
        """

        @classmethod
        def is_supported(cls) -> bool:
            return False

        @classmethod
        def version(cls) -> str:
            return "Unavailable"

        def qasm_to_native(self, qasm: str):
            raise NotImplementedError("pyqpanda3 is not supported on this platform.")

        def native_to_qasm(self, circuit):
            raise NotImplementedError("pyqpanda3 is not supported on this platform.")

        def compile(self, circuit, target_device=None):
            raise NotImplementedError("pyqpanda3 is not supported on this platform.")

        def count_multi_qubit_gates(self, circuit):
            raise NotImplementedError("pyqpanda3 is not supported on this platform.")
