from typing import Callable
from qiskit.quantum_info import Operator
from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel
from qiskit.transpiler import Target

# To avoid circular imports between this module and compilers,
# only import the BaseCompiler class when type checking.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .compilers.base_compiler import BaseCompiler


class Registry:
    _compilers = {}
    _output_metric = {}
    _observables = {}
    _target_devices = {}

    def compiler(self, id: str):
        """
        Decorator to register a Compiler class by id that conforms to the
        BaseCompiler interface. This also will add the id() -> str class method
        to return that name as the id.
        """

        def decorator(cls: "BaseCompiler"):
            if id in self._compilers:
                raise ValueError(f"Compiler {id} is already registered.")

            # Define a default id method on the clas instance if its still abstract
            if "id" in getattr(cls, "__abstractmethods__", set()):

                @classmethod
                def id_method(cls_):
                    return id

                cls.id = id_method

            # Optionally clear abstract methods if needed
            if hasattr(cls, "__abstractmethods__"):
                cls.__abstractmethods__ = frozenset()

            self._compilers[id] = cls
            return cls

        return decorator

    def has_compiler(self, id: str) -> bool:
        return id in self._compilers

    def get_compiler(self, id: str) -> "BaseCompiler":
        return self._compilers[id]

    def get_compilers(self) -> set[str]:
        """
        Returns a list of all registered compiler ids.
        """
        return set(self._compilers.keys())

    def observable(self, id: str):
        """
        Decorator to register a function that generates an observable Operator.

        Observables take a single argument, which is the number of qubits in the
        circuit, and return a Qiskit Operator representing the observable to measure.

        The code will automatically manage calculating the expectation value of this
        observable for the uncompiled and compiled circuits under the varying noise models.
        """

        def decorator(func: Callable[[int], Operator]):
            if id in self._observables:
                raise ValueError(f"Observable {id} is already registered.")
            func._id = id
            self._observables[id] = func
            return func

        return decorator

    def has_observable(self, id: str) -> bool:
        return id in self._observables

    def get_observable(self, id: str) -> Callable[[int], Operator]:
        return self._observables[id]

    def output_metric(self, id: str):
        """
        Decorator to register a function that calculates an output metric.

        Metric functions take the raw, compiled, and noisy circuits as arguments
        is responsible for determining the uncompiled/compiled and noisy measurement
        results.
        """

        def decorator(
            func: Callable[[QuantumCircuit, QuantumCircuit, NoiseModel], float],
        ):
            if id in self._output_metric:
                raise ValueError(f"Output metric {id} is already registered.")
            func._id = id
            self._output_metric[id] = func
            return func

        return decorator

    def has_output_metric(self, id: str) -> bool:
        return id in self._output_metric

    def get_output_metric(
        self, id: str
    ) -> Callable[[QuantumCircuit, QuantumCircuit, NoiseModel], float]:
        return self._output_metric[id]

    def add_target_device(self, id: str, t: Target):
        """
        Add a given target device to the registry associated with the given id.
        """

        if id in self._target_devices:
            raise ValueError(f"Target device {id} is already registered.")

        self._target_devices[id] = t

    def has_target_device(self, id: str) -> bool:
        return id in self._target_devices

    def get_target_device(self, id: str) -> Target:
        return self._target_devices[id]


# Instance to use to registry the above items
# E.g.
# from ..registry import register
#
# @register.compiler("my_compiler")
# class MyCompiler(BaseCompiler): pass
#
# @register.observable("my_observable")
# def my_observable(num_qubits: int) -> Operator: pass
register = Registry()
