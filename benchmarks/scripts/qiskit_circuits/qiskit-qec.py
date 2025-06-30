from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

def qec_bitflip_code():
    """
    Returns a QuantumCircuit implementing the 3-qubit bit-flip code with error correction.
    """
    # 3 data qubits, 2 ancilla for syndrome, 3 classical for data, 2 for syndrome
    qreg_data = QuantumRegister(3, "data")
    qreg_measure = QuantumRegister(2, "ancilla")
    creg_data = ClassicalRegister(3, "c_data")
    creg_syndrome = ClassicalRegister(2, "c_syndrome")
    qc = QuantumCircuit(qreg_data, qreg_measure, creg_data, creg_syndrome)

    # Initialize |1> state
    qc.x(qreg_data[0])
    qc.barrier(qreg_data)

    # Encode bit-flip (repetition code)
    qc.cx(qreg_data[0], qreg_data[1])
    qc.cx(qreg_data[0], qreg_data[2])
    qc.barrier(qreg_data)

    # Syndrome measurement (parity checks)
    qc.cx(qreg_data[0], qreg_measure[0])
    qc.cx(qreg_data[1], qreg_measure[0])
    qc.cx(qreg_data[0], qreg_measure[1])
    qc.cx(qreg_data[2], qreg_measure[1])
    qc.barrier(qreg_data, qreg_measure)
    qc.measure(qreg_measure, creg_syndrome)
    qc.barrier(qreg_data, qreg_measure)

    # Correction (classically controlled)
    qc.x(qreg_data[0]).c_if(creg_syndrome, 3)
    qc.x(qreg_data[1]).c_if(creg_syndrome, 1)
    qc.x(qreg_data[2]).c_if(creg_syndrome, 2)
    qc.barrier(qreg_data)

    # Final readout
    qc.measure(qreg_data, creg_data)
    return qc

# Example usage:
if __name__ == "__main__":
    qc = qec_bitflip_code()
    print(qc)