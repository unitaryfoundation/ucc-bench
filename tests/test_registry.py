import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from ucc_bench.registry import Registry, GeneratorSpec
from qiskit_ibm_runtime.fake_provider import FakeQuebec


# Helper generator function for testing
def dummy_generator(N, param1, param2=2):
    qc = QuantumCircuit(N)
    return qc


def test_generator_registration_and_retrieval():
    reg = Registry()
    reg.generator("dummy_gen")(dummy_generator)
    assert reg.has_generator("dummy_gen")
    spec = reg.get_generator("dummy_gen")
    assert isinstance(spec, GeneratorSpec)
    assert spec.id == "dummy_gen"
    assert spec.size_param == "N"
    assert set(spec.params.keys()) == {"N", "param1", "param2"}
    # Validate params
    spec.validate_params({"N": 3, "param1": 5, "param2": 10})

    # extra/unknown parameter
    with pytest.raises(ValueError):
        spec.validate_params({"N": 3, "param1": 5, "unknown": 1})

    # N and param1 are required
    with pytest.raises(ValueError):
        spec.validate_params({})

    with pytest.raises(ValueError):
        spec.validate_params({"n": 3})


def test_duplicate_generator_registration():
    reg = Registry()
    reg.generator("dup_gen")(dummy_generator)
    with pytest.raises(ValueError):
        reg.generator("dup_gen")(dummy_generator)


def test_compiler_registration_and_retrieval():
    reg = Registry()

    class DummyCompiler:
        pass

    reg.compiler("dummy_compiler")(DummyCompiler)
    assert reg.has_compiler("dummy_compiler")
    assert reg.get_compiler("dummy_compiler") is DummyCompiler
    assert "dummy_compiler" in reg.get_compilers()
    with pytest.raises(ValueError):
        reg.compiler("dummy_compiler")(DummyCompiler)


def test_observable_registration_and_retrieval():
    reg = Registry()

    def obs(n):
        return Operator(QuantumCircuit(n))

    reg.observable("obs1")(obs)
    assert reg.has_observable("obs1")
    assert reg.get_observable("obs1") is obs
    with pytest.raises(ValueError):
        reg.observable("obs1")(obs)


def test_output_metric_registration_and_retrieval():
    reg = Registry()

    def metric(qc1, qc2, noise):
        return 1.0

    reg.output_metric("metric1")(metric)
    assert reg.has_output_metric("metric1")
    assert reg.get_output_metric("metric1") is metric
    with pytest.raises(ValueError):
        reg.output_metric("metric1")(metric)


def test_target_device_registration_and_retrieval():
    reg = Registry()
    backend = FakeQuebec()
    reg.add_target_device("sim1", backend)
    assert reg.has_target_device("sim1")
    assert reg.get_target_device("sim1") is backend
    with pytest.raises(ValueError):
        reg.add_target_device("sim1", backend)
