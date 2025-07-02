from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional
from qbraid import transpile
from qiskit.transpiler import Target

# Define a generic type variable for a circuit, that concrete implementations
# will define for each library type
CircuitType = TypeVar("CircuitType")


class BaseCompiler(ABC, Generic[CircuitType]):
    """
    Abstract base class representing a compiler for use in benchmarking.
    """

    @classmethod
    def is_supported(cls) -> bool:
        """
        Check if the compiler is supported for the current environment.
        Defaults to True, but can be overridden by subclasses
        """
        return True

    @classmethod
    @abstractmethod
    def id(cls) -> str:
        """Return the id of the compiler; this will automatically be implemented
        if the class is registered using the @registry.compiler method"""
        pass

    @classmethod
    @abstractmethod
    def version(cls) -> str:
        """Return the version of the compiler"""
        pass

    def qasm_to_native(self, qasm: str) -> CircuitType:
        """
        Convert a QASM string to the native circuit type of this compiler

        The default implementation calls qbraid.transpile with a target that is the compiler id.
        Compiler instances that don't use the cannonical name for transpilation target should override this method.
        """
        return transpile(qasm, self.id())

    def native_to_qasm(self, circuit: CircuitType) -> str:
        """
        Convert a native circuit to a QASM string
        """
        return transpile(circuit, "qasm2")

    @abstractmethod
    def compile(
        self, circuit: CircuitType, target_device: Optional[Target] = None
    ) -> CircuitType:
        """Compile the given circuit"""
        pass

    @abstractmethod
    def count_multi_qubit_gates(self, circuit: CircuitType) -> int:
        """Count the number of multi-qubit gates in the circuit"""
        pass
