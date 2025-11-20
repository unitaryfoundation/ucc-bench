from typing import Optional

import cirq
from mitiq import __version__ as mitiq_version
from mitiq.ddd import construct_circuits as ddd_construct_circuits
from mitiq.ddd import rules as ddd_rules
from qbraid import transpile as qb_transpile
from qiskit import QuantumCircuit
from qiskit.providers import Backend
from ucc import __version__ as ucc_version
from ucc import compile as ucc_compile

from ..registry import register
from .base_compiler import BaseCompiler


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

        def hh_rule(slack_length):
            return ddd_rules.general_rule(
                    slack_length, [cirq.H, cirq.H]
                )
        ddd_circuits = ddd_construct_circuits(
            compiled,
            rule=hh_rule,
            num_trials=1,  # one circuit = no post-processing
        )
        return ddd_circuits[0]

    def count_multi_qubit_gates(self, circuit: QuantumCircuit) -> int:
        return circuit.num_nonlocal_gates()
