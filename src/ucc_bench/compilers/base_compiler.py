from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from qbraid import transpile

# Define a generic type variable for a circuit, that concrete implementations
# will define for each library type
CircuitType = TypeVar("CircuitType")


class BaseCompiler(ABC, Generic[CircuitType]):
    """
    Abstract base class representing a compiler for use in benchmarking.
    """

    # Class-level registry for compiler subclasses
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        # When creating subclasses, register them in the registry by id
        super().__init_subclass__(**kwargs)
        cls._registry[cls.id()] = cls

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def lookup(cls, name: str) -> "BaseCompiler":
        return cls._registry[name]

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
        return transpile(qasm, self.id())

    @abstractmethod
    def compile(self, circuit: CircuitType) -> CircuitType:
        """Compile the given circuit"""
        pass

    @abstractmethod
    def count_multi_qubit_gates(self, circuit: CircuitType) -> int:
        """Count the number of multi-qubit gates in the circuit"""
        pass
