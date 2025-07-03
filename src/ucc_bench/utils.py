from qbraid import transpile


def validate_circuit_gates(circuit, allowed_gates=None):
    """Validate that ``circuit`` only uses gates from ``allowed_gates``.

    Parameters
    ----------
    circuit: Any
        Circuit in any supported format. It will be converted to a Qiskit
        ``QuantumCircuit`` via :func:`qbraid.transpile` for inspection.
    allowed_gates: set[str] | None
        Names of gates that are permitted. If ``None`` the default set
        ``{"rx", "ry", "rz", "h", "cx"}`` is used.

    Raises
    ------
    ValueError
        If the circuit contains operations outside the allowed set.
    """
    if allowed_gates is None:
        allowed_gates = {"rx", "ry", "rz", "h", "cx"}

    qc = transpile(circuit, "qiskit")
    #
    invalid_gates = {
        instr.operation.name
        for instr in qc.data
        if instr.operation.name not in allowed_gates
        and instr.operation.name
        not in {"measure", "barrier", "reset", "delay", "if_else"}
    }

    if invalid_gates:
        raise ValueError(
            f"Compiled circuit contained unsupported gates: {sorted(invalid_gates)}"
        )

    return qc
