import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from ucc_bench.suite import Suite, Compiler, Benchmark


def test_validate_valid_suite():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()  # Create an empty QASM file

        # Pydantic will validate during initialization
        suite = Suite(
            spec_path=temp_path / "suite.toml",
            spec_version="1.0",
            suite_version="1.0",
            id="suite1",
            description="A valid suite",
            compilers=[Compiler(id="ucc")],
            benchmarks=[
                Benchmark(id="bench1", description="Benchmark 1", qasm_file=qasm_file)
            ],
        )

        # No exceptions should be raised
        assert suite


def test_validate_duplicate_benchmark_ids():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()

        with pytest.raises(ValueError, match="Duplicate benchmark id: bench1"):
            Suite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with duplicate benchmark IDs",
                compilers=[Compiler(id="ucc")],
                benchmarks=[
                    Benchmark(
                        id="bench1", description="Benchmark 1", qasm_file=qasm_file
                    ),
                    Benchmark(
                        id="bench1", description="Benchmark 2", qasm_file=qasm_file
                    ),
                ],
            )


def test_validate_unregistered_compiler():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()

        with pytest.raises(ValueError, match="Unknown compiler id: unknown_compiler"):
            Suite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with unregistered compiler",
                compilers=[Compiler(id="unknown_compiler")],
                benchmarks=[
                    Benchmark(
                        id="bench1", description="Benchmark 1", qasm_file=qasm_file
                    )
                ],
            )


def test_validate_invalid_qasm_file_path():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        resolved_path = temp_path / "nonexistent.qasm"

        with pytest.raises(
            ValueError,
            match=f"qasm_file for benchmark 'bench1' does not point to a valid file: {resolved_path}",
        ):
            Suite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with invalid QASM file path",
                compilers=[Compiler(id="ucc")],
                benchmarks=[
                    Benchmark(
                        id="bench1",
                        description="Benchmark 1",
                        qasm_file=temp_path / "nonexistent.qasm",
                    )
                ],
            )
