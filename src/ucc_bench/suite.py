import tomllib
from pathlib import Path
from pydantic import BaseModel
from pydantic import Field, model_validator, field_validator
from typing import List, Optional

from .compilers import is_compiler_registered


class CompilerSpec(BaseModel):
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


class BenchmarkSpec(BaseModel):
    """
    Represents a specific benchmark (circuit+metrics) to run.

    Attributes:
        id: The id of the benchmark, used to identify the benchmark
        description: A human-readable description of the benchmark
        qasm_file: The path to the QASM file containing the benchmark circuit. This path is relative to the spec file itself.
    """

    id: str
    description: str
    qasm_file: Path
    resolved_qasm_file: Optional[Path] = None


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

    spec_path: Path
    spec_version: str
    suite_version: str
    id: str
    description: str
    compilers: List[CompilerSpec] = Field(default_factory=list)
    benchmarks: List[BenchmarkSpec] = Field(default_factory=list)

    @classmethod
    def load_toml(cls, path: str) -> "BenchmarkSuite":
        """Load a specification from a TOML file at the specified path."""
        with open(path, "rb") as f:
            raw = tomllib.load(f)
            raw["spec_path"] = Path(path)
            return BenchmarkSuite.model_validate(raw)

    @model_validator(mode="after")
    def check_benchmarks_unique(self):
        set_ids = set()
        for benchmark in self.benchmarks:
            if benchmark.id in set_ids:
                raise ValueError(f"Duplicate benchmark id: {benchmark.id}")
            set_ids.add(benchmark.id)
        return self

    @model_validator(mode="after")
    def check_compilers_unique(self):
        set_ids = set()
        for compiler in self.compilers:
            if compiler.id in set_ids:
                raise ValueError(f"Duplicate compiler: {compiler.id}")
            set_ids.add(compiler.id)
        return self

    @model_validator(mode="after")
    def canonicalize_and_validate_qasm_paths(self):
        """Ensure all qasm_file paths are valid and relative to spec_path."""
        for benchmark in self.benchmarks:
            # Resolve qasm_file relative to spec_path
            if benchmark.resolved_qasm_file is None:
                benchmark.resolved_qasm_file = (
                    self.spec_path.parent / benchmark.qasm_file
                )

            # Check if the resolved path exists and is a file
            if not benchmark.resolved_qasm_file.is_file():
                raise ValueError(
                    f"qasm_file for benchmark '{benchmark.id}' does not point to a valid file: {benchmark.resolved_qasm_file}"
                )
        return self
