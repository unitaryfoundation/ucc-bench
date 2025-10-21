import inspect
from dataclasses import dataclass, field
from typing import Callable, Any, Dict
from qiskit.quantum_info import Operator
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.providers import Backend

# To avoid circular imports between this module and compilers,
# only import the BaseCompiler class when type checking.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .compilers.base_compiler import BaseCompiler


#### Information for circuit generator functions that can take arbitrary params##
@dataclass
class ParameterSpec:
    """Stores metadata about a single parameter of a generator function."""

    name: str
    annotation: Any
    default: Any
    required: bool


@dataclass
class GeneratorSpec:
    """
    Stores the generator function and metadata about its parameters,
    captured at registration time.
    """

    id: str
    func: Callable[..., QuantumCircuit]
    size_param: str  # The name of the first parameter, e.g., 'n' for number of qubits
    params: Dict[str, ParameterSpec] = field(default_factory=dict)

    def validate_params(self, provided_params: Dict[str, Any]):
        """
        Validates a dictionary of parameters against the function's signature.
        """
        provided_keys = set(provided_params.keys())
        expected_keys = set(self.params.keys())

        # Check for unknown parameters
        unknown_params = provided_keys - expected_keys
        if unknown_params:
            raise ValueError(
                f"Unknown parameter(s) for generator '{self.id}': {', '.join(unknown_params)}. "
                f"Available parameters are: {', '.join(expected_keys)}"
            )

        # Check for missing required parameters
        for name, spec in self.params.items():
            if spec.required and name not in provided_params:
                raise ValueError(
                    f"Missing required parameter for generator '{self.id}': {name}"
                )


class Registry:
    def __init__(self):
        self._compilers = {}
        self._output_metric = {}
        self._observables = {}
        self._target_devices = {}
        self._generators = {}

    def clear(self):
        """Clears all registered items. Primarily for testing purposes."""
        self._compilers.clear()
        self._output_metric.clear()
        self._observables.clear()
        self._target_devices.clear()
        self._generators.clear()

    def generator(self, id: str):
        """
        Decorator to register a circuit generator function.

        The decorated function's signature must have a single positional argument
        representing the problem size (e.g., number of qubits), followed by
        any number of keyword arguments.

        This decorator inspects the function's signature to capture metadata
        about its keyword arguments, which can be used later for validation.
        """

        def decorator(func: Callable[..., QuantumCircuit]):
            if id in self._generators:
                raise ValueError(f"Generator {id} is already registered.")

            sig = inspect.signature(func)
            params = list(sig.parameters.values())

            if not params:
                raise TypeError(
                    f"Generator function '{func.__name__}' must have at least one "
                    "parameter for problem size."
                )

            # The first parameter is considered the problem size argument.
            size_param_name = params[0].name
            assert size_param_name == "N"
            spec = GeneratorSpec(id=id, func=func, size_param=size_param_name)

            for p in params:
                if p.kind not in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                ):
                    raise TypeError(
                        f"Generator '{func.__name__}' optional parameters must be "
                        f"keyword-addressable, but '{p.name}' is not."
                    )

                is_required = p.default is inspect.Parameter.empty
                spec.params[p.name] = ParameterSpec(
                    name=p.name,
                    annotation=p.annotation
                    if p.annotation is not inspect.Parameter.empty
                    else Any,
                    default=p.default if not is_required else None,
                    required=is_required,
                )

            self._generators[id] = spec
            return func

        return decorator

    def has_generator(self, id: str) -> bool:
        return id in self._generators

    def get_generator(self, id: str) -> GeneratorSpec:
        """Returns the specification for the registered generator."""
        if not self.has_generator(id):
            raise ValueError(f"Generator '{id}' is not registered.")
        return self._generators[id]

    def get_generators(self) -> list[str]:
        """
        Returns a list of all registered generator ids.
        """
        return sorted(list(self._generators.keys()))

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

    def get_compilers(self) -> list[str]:
        """
        Returns a list of all registered compiler ids.
        """
        return sorted(list(self._compilers.keys()))

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
            func: Callable[[QuantumCircuit, QuantumCircuit, AerSimulator], float],
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
    ) -> Callable[[QuantumCircuit, QuantumCircuit, AerSimulator], float]:
        return self._output_metric[id]

    def add_target_device(self, id: str, t: Backend):
        """
        Add a given target device to the registry associated with the given id.
        """

        if id in self._target_devices:
            raise ValueError(f"Target device {id} is already registered.")

        self._target_devices[id] = t

    def has_target_device(self, id: str) -> bool:
        return id in self._target_devices

    def get_target_device(self, id: str) -> Backend:
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
