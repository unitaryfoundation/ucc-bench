import tomllib
from pathlib import Path
from typing import List, Optional, Dict, Any
from qiskit import QuantumCircuit
from pydantic import BaseModel
from pydantic import Field, model_validator


from .registry import register


class CompilerSpec(BaseModel):
    """
    Represents a compiler to benchmark against

    Attributes:
        id: The id of the compiler, used to look up the compiler in the registry
    """

    id: str


class SimulationSpec(BaseModel):
    measurement: str


class TargetDeviceSpec(BaseModel):
    """
    Represents a target device to compile the circuit for.

    Attributes:
        The name of the target device, as defined in the registry.
    """

    id: str


class GeneratorSpec(BaseModel):
    """
    Specification for a circuit generator function.

    Attributes:
        name: The name of the generator function, as defined in the registry.
        params: A dictionary of parameters to pass to the generator function.
    """

    name: str
    params: Dict[str, Any] = {}

    @model_validator(mode="after")
    def validate_generator_and_params(self):
        """
        Validates that the generator exists in the registry and that
        the provided parameters match the generator's function signature.
        """
        if not register.has_generator(self.name):
            raise ValueError(f"Unknown generator name: '{self.name}'")

        # Now validate the parameters against the registered generator's signature
        registry_spec = register.get_generator(self.name)
        try:
            registry_spec.validate_params(self.params)
        except ValueError as e:
            # Re-raise the validation error from the registry so pydantic can catch it.
            raise e
        return self

    def uid(self) -> str:
        """Generate a unique identifier for this generator spec based on its name and parameters."""
        param_str = ",".join(f"{k}={v}" for k, v in sorted(self.params.items()))
        return f"{self.name}({param_str})" if param_str else self.name

    def generate_circuit(self) -> QuantumCircuit:
        """Generate a QuantumCircuit using the specified generator and parameters."""
        registry_spec = register.get_generator(self.name)
        return registry_spec.func(**self.params)


class BenchmarkSpec(BaseModel):
    """
    Represents a specific benchmark (circuit+metrics) to run.

    Attributes:
        id: The id of the benchmark, used to identify the benchmark
        description: A human-readable description of the benchmark
        qasm_file: The path to the QASM file containing the benchmark circuit. This path is relative to the spec file itself.
        generator: Specification for a circuit generator function and associated arguments
        resolved_qasm_file: The absolute path to the QASM file, resolved relative to the spec file.
        simulate: An optional specification of how to simulate the circuit and what measurements to take

    Note:
        Either qasm_file or generator must be specified, but not both.
        Resolved_qasm_file is populated automatically and should not be set by the user
    """

    id: str
    description: str
    qasm_file: Optional[Path] = None
    generator: Optional[GeneratorSpec] = None
    resolved_qasm_file: Optional[Path] = None
    simulate: Optional[SimulationSpec] = None

    def num_qubits(self) -> Optional[int]:
        """
        Return the number of qubits in the benchmark circuit.
        Only returns a value if the circuit is generated via a generator spec.
        """
        if self.generator is not None:
            return self.generator.params.get("N", 0)
        else:
            return None


class BenchmarkSuite(BaseModel):
    """
    Represents a specification of a benchmark suite.

    Attributes:
        spec_path: The path to the specification file
        spec_version: The version of the specification format
        suite_version: The version of the benchmark suite
        id: The id of the suite
        description: A human-readable description of the suite
        compilers: A list of compilers to benchmark against
        benchmarks: A list of benchmarks to run
    """

    spec_path: Optional[Path] = None
    spec_version: str
    suite_version: str
    id: str
    description: str
    compilers: List[CompilerSpec] = Field(default_factory=list)
    benchmarks: List[BenchmarkSpec] = Field(default_factory=list)
    target_devices: List[TargetDeviceSpec] = Field(default_factory=list)

    @classmethod
    def load_toml(cls, path: str) -> "BenchmarkSuite":
        """Load a specification from a TOML file at the specified path.

        Unlike deserializing stored results, loading a TOML spec for execution
        validates that all referenced compilers, target devices, measurements,
        and generators are currently registered.
        """
        with open(path, "rb") as f:
            raw = tomllib.load(f)
            raw["spec_path"] = Path(path)
            suite = BenchmarkSuite.model_validate(raw)

        # Validate that all referenced registry items exist. These checks
        # live here rather than on the Pydantic models so that historical
        # result JSON files (which embed the suite spec) can still be
        # deserialized after a compiler/device/measurement is retired.
        for compiler in suite.compilers:
            if not register.has_compiler(compiler.id):
                raise ValueError(f"Unknown compiler id: {compiler.id}")

        for target_device in suite.target_devices:
            if not register.has_target_device(target_device.id):
                raise ValueError(f"Unknown target device: {target_device.id}")

        for benchmark in suite.benchmarks:
            if benchmark.simulate:
                m = benchmark.simulate.measurement
                if not register.has_observable(m) and not register.has_output_metric(m):
                    raise ValueError(f"Unknown measurement id: {m}")

        return suite

    @model_validator(mode="after")
    def check_ids_unique(self):
        """Check that ids are unique for compilers, benchmarks and target_devices."""
        for field in ["compilers", "benchmarks", "target_devices"]:
            items = getattr(self, field, [])
            set_ids = set()
            for item in items:
                if item.id in set_ids:
                    raise ValueError(f"Duplicate {field[:-1]} id: {item.id}")
                set_ids.add(item.id)
        return self

    @model_validator(mode="after")
    def canonicalize_and_validate_qasm_paths(self):
        """Ensure all qasm_file paths are valid and relative to spec_path."""
        for benchmark in self.benchmarks:
            if (benchmark.qasm_file is None) == (benchmark.generator is None):
                raise ValueError("Provide exactly one of 'qasm_file' or 'generator'.")
            if benchmark.qasm_file is not None:
                if benchmark.resolved_qasm_file is None:
                    benchmark.resolved_qasm_file = (
                        self.spec_path.parent / benchmark.qasm_file
                    )
                if not benchmark.resolved_qasm_file.is_file():
                    raise ValueError(
                        "qasm_file for benchmark "
                        f"'{benchmark.id}' does not point to a valid file: {benchmark.resolved_qasm_file}"
                    )
        return self
