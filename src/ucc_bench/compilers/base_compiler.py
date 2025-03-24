from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# A registry of all available compilers for benchmarking, maps from
# the compiler id to the class for that compiler
_compiler_registry = {}

# Define a generic type variable for a circuit, that concrete implementations
# will define for each library type
CircuitType = TypeVar("CircuitType")


class CompilerABC(ABC, Generic[CircuitType]):
    """
    Abstract base class representing a compiler for use in benchmaking.
    In order for a compiler to be used in the benchmarking framework, it must
    implement this interface.

    The CircuitType type variable is used to specify the type of the circuit
    object that the compiler will be working with.
    """

    def __init_subclass__(cls, **kwargs):
        # When implementing this class, register it in the compiler registry
        super().__init_subclass__(**kwargs)
        _compiler_registry[cls.id()] = cls

    @classmethod
    @abstractmethod
    def id(cls) -> str:
        """Return the identifier (name) of the compiler"""
        pass

    @classmethod
    @abstractmethod
    def version(cls) -> str:
        """Return the version of the compiler"""
        pass

    def qasm_to_native(self, qasm: str) -> CircuitType:
        """Convert a QASM string to the native circuit type of this compiler"""
        pass

    @abstractmethod
    def compile(self, circuit: CircuitType) -> CircuitType:
        """Compile the given circuit"""
        pass

    @abstractmethod
    def count_multi_qubit_gates(self, circuit: CircuitType) -> int:
        """Count the number of multi-qubit gates in the circuit"""
        pass


def lookup_compiler(name: str) -> CompilerABC:
    # Lookup compiler by name in the registry
    return _compiler_registry[name]
