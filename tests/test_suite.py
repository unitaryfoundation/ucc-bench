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
    GeneratorSpec,
)
from ucc_bench.registry import register
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


def test_validate_unregistered_compiler():
    """Unknown compiler ids are caught when loading a TOML for execution,
    but *not* when deserializing stored results (so old data still loads)."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()

        # Building the model directly should succeed (result deserialization path)
        suite = BenchmarkSuite(
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
        assert suite is not None

        # But loading via load_toml should reject the unknown compiler
        toml_path = temp_path / "suite.toml"
        toml_path.write_text(
            'spec_version = "1.0"\n'
            'suite_version = "1.0"\n'
            'id = "suite1"\n'
            'description = "bad"\n'
            "[[compilers]]\n"
            'id = "unknown_compiler"\n'
            "[[benchmarks]]\n"
            'id = "bench1"\n'
            'description = "Benchmark 1"\n'
            f'qasm_file = "{qasm_file.as_posix()}"\n'
        )
        with pytest.raises(ValueError, match="Unknown compiler id: unknown_compiler"):
            BenchmarkSuite.load_toml(str(toml_path))


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
    """Unknown target device ids are caught when loading a TOML for execution,
    but *not* when deserializing stored results."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        qasm_file = temp_path / "valid.qasm"
        qasm_file.touch()

        # Building the model directly should succeed (result deserialization path)
        suite = BenchmarkSuite(
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
        assert suite is not None

        # But loading via load_toml should reject the unknown target device
        toml_path = temp_path / "suite.toml"
        toml_path.write_text(
            'spec_version = "1.0"\n'
            'suite_version = "1.0"\n'
            'id = "suite1"\n'
            'description = "bad"\n'
            "[[compilers]]\n"
            'id = "ucc"\n'
            "[[target_devices]]\n"
            'id = "unknown_target"\n'
            "[[benchmarks]]\n"
            'id = "bench1"\n'
            'description = "Benchmark 1"\n'
            f'qasm_file = "{qasm_file.as_posix()}"\n'
        )
        with pytest.raises(ValueError, match="Unknown target device: unknown_target"):
            BenchmarkSuite.load_toml(str(toml_path))


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


@pytest.fixture(scope="module")
def registered_generators():
    @register.generator("dummy_gen")
    def dummy_gen(N, alpha=1, beta=2):
        return QuantumCircuit(N)

    @register.generator("required_param_gen")
    def required_param_gen(N, gamma):
        return QuantumCircuit(N)

    yield  # --- tests run here ---

    register.clear()


@pytest.mark.usefixtures("registered_generators")
class TestGeneratorSpecs:
    def test_generatorspec_valid(self):
        spec = GeneratorSpec(name="dummy_gen", params={"N": 3, "alpha": 5, "beta": 10})
        # Should not raise
        assert spec.name == "dummy_gen"
        assert spec.params["alpha"] == 5
        assert spec.params["beta"] == 10

    def test_generatorspec_unknown_generator(self):
        """Unknown generators are caught by validate_against_registry, not at construction."""
        spec = GeneratorSpec(name="not_a_gen", params={})
        with pytest.raises(ValueError, match="Unknown generator name: 'not_a_gen'"):
            spec.validate_against_registry()

    def test_generatorspec_unknown_param(self):
        spec = GeneratorSpec(name="dummy_gen", params={"N": 3, "foo": 1})
        with pytest.raises(
            ValueError, match="Unknown parameter\(s\) for generator 'dummy_gen': foo"
        ):
            spec.validate_against_registry()

    def test_generatorspec_missing_required_param(self):
        spec = GeneratorSpec(name="required_param_gen", params={})
        with pytest.raises(
            ValueError,
            match="Missing required parameter for generator 'required_param_gen': N",
        ):
            spec.validate_against_registry()
