from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from ucc_bench.suite import (
    BenchmarkSuite,
    BenchmarkSpec,
    CompilerSpec,
    TargetDeviceSpec,
)
from ucc_bench.unoptimization import unoptimize_circuit


def test_validate_valid_suite():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()  # Create an empty QASM file

        # Pydantic will validate during initialization
        suite = BenchmarkSuite(
            spec_path=temp_path / "suite.toml",
            spec_version="1.0",
            suite_version="1.0",
            id="suite1",
            description="A valid suite",
            compilers=[CompilerSpec(id="ucc")],
            benchmarks=[
                BenchmarkSpec(
                    id="bench1", description="Benchmark 1", qasm_file=qasm_file
                )
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
            BenchmarkSuite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with duplicate benchmark IDs",
                compilers=[CompilerSpec(id="ucc")],
                benchmarks=[
                    BenchmarkSpec(
                        id="bench1", description="Benchmark 1", qasm_file=qasm_file
                    ),
                    BenchmarkSpec(
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
            BenchmarkSuite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with unregistered compiler",
                compilers=[CompilerSpec(id="unknown_compiler")],
                benchmarks=[
                    BenchmarkSpec(
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
            BenchmarkSuite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with invalid QASM file path",
                compilers=[CompilerSpec(id="ucc")],
                benchmarks=[
                    BenchmarkSpec(
                        id="bench1",
                        description="Benchmark 1",
                        qasm_file=temp_path / "nonexistent.qasm",
                    )
                ],
            )


def test_validate_unregistered_target_device():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()

        with pytest.raises(ValueError, match="Unknown target device: unknown_target"):
            BenchmarkSuite(
                spec_path=temp_path / "suite.toml",
                spec_version="1.0",
                suite_version="1.0",
                id="suite1",
                description="A suite with unregistered target",
                compilers=[CompilerSpec(id="ucc")],
                target_devices=[TargetDeviceSpec(id="unknown_target")],
                benchmarks=[
                    BenchmarkSpec(
                        id="bench1", description="Benchmark 1", qasm_file=qasm_file
                    )
                ],
            )


def test_unoptimization_preserves_unitary_and_introduces_complexity():
    """Smoke test the unoptimization recipe on a seeded three-qubit circuit."""

    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.h(2)

    reference = Operator(qc).data

    unoptimized = unoptimize_circuit(
        qc,
        iterations=1,
        strategy="concatenated",
        decomposition_method="default",
        optimization_level=1,
        seed=7,
        synthesize=False,
    )

    assert unoptimized.size() > qc.size()
    assert np.allclose(Operator(unoptimized).data, reference)
