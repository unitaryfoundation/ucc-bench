from .base_compiler import BaseCompiler
from qiskit import QuantumCircuit
from qiskit.providers import Backend
from typing import Optional
from qbraid import transpile as qb_transpile

from ucc import __version__ as ucc_version
from ucc import compile as ucc_compile

from ..registry import register

from mitiq import __version__ as mitiq_version
from mitiq.ddd import construct_circuits as ddd_construct_circuits
from mitiq.ddd import rules as ddd_rules


@register.compiler("ucc-ddd")
class UCCDDDCompiler(BaseCompiler[QuantumCircuit]):
    """
    UCC compiler followed by Digital Dynamical Decoupling using Mitiq.
    """

    @classmethod
    def version(cls) -> str:
        return f"UCC:{ucc_version}+mitiq:{mitiq_version}"

    def qasm_to_native(self, qasm: str) -> QuantumCircuit:
        return qb_transpile(qasm, "qiskit")

    def compile(
        self, circuit: QuantumCircuit, target_device: Optional[Backend] = None
    ) -> QuantumCircuit:
        if target_device is not None:
            compiled = ucc_compile(circuit, target_backend=target_device)
        else:
            compiled = ucc_compile(
                circuit,
                target_gateset={"rx", "ry", "rz", "h", "cx"},
            )

        ddd_circuits = ddd_construct_circuits(
            compiled,
            rule=ddd_rules.xx,
            num_trials=1, # one circuit = no post-processing
        )
        return ddd_circuits[0]

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()

