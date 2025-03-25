import tomllib
from pathlib import Path
from dataclasses import dataclass
from dataclasses import field
from typing import List
from .compilers import is_compiler_registered


@dataclass
class Compiler:
    """
    Represents a compiler to benchmark against

    Attributes:
        id: The id of the compiler, used to look up the compiler in the registry
    """

    id: str


@dataclass
class Benchmark:
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


@dataclass
class Suite:
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
    compilers: List[Compiler] = field(default_factory=list)
    benchmarks: List[Benchmark] = field(default_factory=list)

    def __post_init__(self):
        """Fully qualify path to qasm files"""
        for benchmark in self.benchmarks:
            benchmark.qasm_file = Path(self.spec_path.parent) / Path(
                benchmark.qasm_file
            )

    @classmethod
    def load(cls, path: str) -> "Suite":
        """Load a specification from a TOML file at the specified path."""
        with open(path, "rb") as f:
            raw = tomllib.load(f)

            # nested data needs to be manually converted to objects
            raw["compilers"] = [Compiler(**c) for c in raw.get("compilers", [])]
            raw["benchmarks"] = [Benchmark(**b) for b in raw.get("benchmarks", [])]

            return Suite(spec_path=Path(path), **raw)

    def validate(self):
        """Validate the specification, raising a ValueError if it is invalid."""
        # Check that all benchmarks have a unique id
        set_ids = set()
        for benchmark in self.benchmarks:
            if benchmark.id in set_ids:
                raise ValueError(f"Duplicate benchmark id: {benchmark.id}")
            set_ids.add(benchmark.id)

        # Check that all compilers are known and registered
        for compiler in self.compilers:
            if not is_compiler_registered(compiler.id):
                raise ValueError(f"Unknown compiler id: {compiler.id}")

        # Check that all qasm_files are valid paths
        for benchmark in self.benchmarks:
            if not benchmark.qasm_file.exists():
                raise ValueError(f"Invalid qasm file path: {benchmark.qasm_file}")
