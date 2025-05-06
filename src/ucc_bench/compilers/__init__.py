# Explicitly import the modules to be sure the register.compiler decorator runs
from .base_compiler import BaseCompiler as BaseCompiler
from .qiskit_compiler import QiskitCompiler as QiskitCompiler
from .cirq_compiler import CirqCompiler as CirqCompiler
from .pytket_compiler import PytketPeepCompiler as PytketPeepCompiler
from .ucc_compiler import UCCCompiler as UCCCompiler
from .pyqpanda3_compiler import (
    PyQPanda3Compiler as PyQPanda3Compiler,
    PYQPANDA3_AVAILABLE as PYQPANDA3_AVAILABLE,
)
