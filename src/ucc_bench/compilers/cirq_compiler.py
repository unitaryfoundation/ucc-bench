from .base_compiler import BaseCompiler
import cirq
from typing import List, Optional
import warnings
from ..registry import register
from qiskit.providers import Backend


class BenchmarkTargetGateset(cirq.TwoQubitCompilationTargetGateset):
    """Target gateset for compiling circuits for benchmarking.

     This is modeled off cirq's `CZCompilationTargetGateset`_, but instead:
         * Decomposes non target gateset single-qubit gates into Rz, Ry gates versus XZPowGate.
         * Decomposes two-qubit gates into CNOT gates versus CZPowGate.
         * Overrides the base classes postprocess_transformers to eliminate the
           merge_single_qubit_moments_to_phxz pass to avoid re-introducing XZPowGates.

    The gate families accepted by this gateset are:
     *  Single-Qubit Gates: `cirq.H`, `cirq.Rx`, `cirq.Ry`, `cirq.Rz`.
     *  Two-Qubit Gates: `cirq.CNOT`
     *  `cirq.MeasurementGate`

     .. _CZCompilationTargetGateset: https://github.com/quantumlib/Cirq/blob/dd3df78c045a03b2de70b2d54d8582abbfc1f6c2/cirq-core/cirq/transformers/target_gatesets/cz_gateset.py#L27
    """

    def __init__(self):
        """Initializes BenchmarkTargetGateset"""
        super().__init__(
            cirq.H,
            cirq.CNOT,
            cirq.Rx,
            cirq.Ry,
            cirq.Rz,
            cirq.MeasurementGate,
            name="BenchmarkTargetGateset",
        )

    def _decompose_single_qubit_operation(
        self, op: cirq.Operation, moment_idx: int
    ) -> cirq.OP_TREE:
        if not cirq.protocols.has_unitary(op):
            return NotImplemented

        mat = cirq.unitary(op)

        pre_phase, rotation, post_phase = (
            cirq.linalg.deconstruct_single_qubit_matrix_into_angles(mat)
        )
        return [
            cirq.rz(pre_phase).on(op.qubits[0]),
            cirq.ry(rotation).on(op.qubits[0]),
            cirq.rz(post_phase).on(op.qubits[0]),
        ]

    def _decompose_two_qubit_operation(self, op: cirq.Operation, _) -> cirq.OP_TREE:
        if not cirq.has_unitary(op):
            return NotImplemented
        mat = cirq.unitary(op)
        q0, q1 = op.qubits
        naive = cirq.two_qubit_matrix_to_cz_operations(
            q0, q1, mat, allow_partial_czs=False
        )
        temp = cirq.map_operations_and_unroll(
            cirq.Circuit(naive),
            lambda op, _: (
                [
                    cirq.H(op.qubits[1]),
                    cirq.CNOT(*op.qubits),
                    cirq.H(op.qubits[1]),
                ]
                if op.gate == cirq.CZ
                else op
            ),
        )
        return cirq.merge_k_qubit_unitaries(
            temp,
            k=1,
            rewriter=lambda op: self._decompose_single_qubit_operation(op, -1),
        ).all_operations()

    @property
    def postprocess_transformers(self) -> List["cirq.TRANSFORMER"]:
        """List of transformers which should be run after decomposing individual operations."""
        processors: List["cirq.TRANSFORMER"] = [
            cirq.transformers.drop_negligible_operations,
            cirq.transformers.drop_empty_moments,
        ]
        if not self._preserve_moment_structure:
            processors.append(cirq.transformers.stratified_circuit)
        return processors

    def __repr__(self) -> str:
        return "BenchmarkTargetGateset()"


@register.compiler("cirq")
class CirqCompiler(BaseCompiler[cirq.Circuit]):
    """
    Wrapper for benchmarking cirq compiler.

    Uses the above BenchmarkTargetGateset for compilation.
    """

    @classmethod
    def version(cls) -> str:
        return cirq.__version__

    def compile(
        self, circuit: cirq.Circuit, target_device: Optional[Backend] = None
    ) -> cirq.Circuit:
        if target_device is not None:
            raise ValueError("Cirq benchmark does not support target devices yet.")

        with warnings.catch_warnings(action="ignore", category=FutureWarning):
            # Cirq 1.5 release added the warning:
            # "FutureWarning: In cirq 1.6 the default value of `use_repetition_ids` will change to
            # `use_repetition_ids=False`. To make this warning go away, please pass
            # explicit `use_repetition_ids`, e.g., to preserve current behavior, use
            #
            # CircuitOperations(..., use_repetition_ids=True)"
            #
            # This prints ***many many times*** during the benchmark, and seems due
            # to the cirq qasm parser not adding this flag when construction circuit operations
            # This looks to be fixed in cirq 1.6 line (https://github.com/quantumlib/Cirq/pull/6910)
            # so we can remove the warning suppression in the future.
            return cirq.optimize_for_target_gateset(
                circuit, gateset=BenchmarkTargetGateset()
            )

    def count_multi_qubit_gates(self, circuit: cirq.Circuit) -> int:
        return sum(
            1 for operation in circuit.all_operations() if len(operation.qubits) > 1
        )
