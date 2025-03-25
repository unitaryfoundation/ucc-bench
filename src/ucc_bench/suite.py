import tomllib
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field, model_validator, field_validator
from typing import List
from .compilers import is_compiler_registered


class Compiler(BaseModel):
    """
    Represents a compiler to benchmark against

    Attributes:
        id: The id of the compiler, used to look up the compiler in the registry
    """

    id: str

    @field_validator("id", mode="after")
    @classmethod
    def is_valid_compiler(cls, value: str) -> str:
        if not is_compiler_registered(value):
            raise ValueError(f"Unknown compiler id: {value}")
        return value


class Benchmark(BaseModel):
    """
    Represents a specific benchmark circuit to run.

    Attributes:
        id: The id of the benchmark, used to identify the benchmark
        description: A human-readable description of the benchmark
        qasm_file: The path to the QASM file containing the benchmark circuit
    """

    id: str
    description: str
    qasm_file: Path


class Suite(BaseModel):
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

    spec_path: Path
    spec_version: str
    suite_version: str
    id: str
    description: str
    compilers: List[Compiler] = Field(default_factory=list)
    benchmarks: List[Benchmark] = Field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "Suite":
        """Load a specification from a TOML file at the specified path."""
        with open(path, "rb") as f:
            raw = tomllib.load(f)
            raw["spec_path"] = Path(path)
            return Suite.model_validate(raw)

    @model_validator(mode="after")
    def check_benchmarks_unique(self):
        set_ids = set()
        for benchmark in self.benchmarks:
            if benchmark.id in set_ids:
                raise ValueError(f"Duplicate benchmark id: {benchmark.id}")
            set_ids.add(benchmark.id)
        return self

    @model_validator(mode="after")
    def canonicalize_and_validate_qasm_paths(self):
        """Ensure all qasm_file paths are valid and relative to spec_path."""
        for benchmark in self.benchmarks:
            # Resolve qasm_file relative to spec_path
            resolved_path = self.spec_path.parent / benchmark.qasm_file

            # Check if the resolved path exists and is a file
            if not resolved_path.is_file():
                raise ValueError(
                    f"qasm_file for benchmark '{benchmark.id}' does not point to a valid file: {resolved_path}"
                )

            # Update the qasm_file to the resolved path
            benchmark.qasm_file = resolved_path

        return self
