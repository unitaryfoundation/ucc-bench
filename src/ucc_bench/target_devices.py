from .registry import register

from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2

for device in FakeProviderForBackendV2().backends():
    register.add_target_device("ibm_" + device.name, device.target)
