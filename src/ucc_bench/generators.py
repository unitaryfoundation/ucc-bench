import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import PauliEvolutionGate
import scipy
from mqt.bench.benchmarks import get_benchmark_catalog
from mqt.bench import get_benchmark, BenchmarkLevel
from .registry import register, Registry


# Register all MQT benchmarks as generators at import time
def register_mqt_benchmarks(reg: Registry = register):
    """Register MQT benchmarks as circuit generators.

    Each MQT benchmark will be available under the id "mqt:<benchmark_name>", and can be
    configured for a number of qubits N and a benchmark level via the `level` parameter.

    At this time, no other configuration options for MQT benchmarks are supported.
    """
    for _name, _desc in get_benchmark_catalog().items():

        def _make_mqt_wrapper(bench_name: str, bench_desc: str):
            def _wrapper(N: int, level: str = "alg"):
                """
                MQT benchmark adapter.

                Benchmark: {bench_name}

                {bench_desc}

                Parameters:
                    N (int): Number of qubits
                    Use the `level` kwarg to choose the MQT BenchmarkLevel as a string where
                        - 'alg' maps to BenchmarkLevel.ALG (default)
                        - 'indep' maps to BenchmarkLevel.INDEP
                """.format(bench_name=bench_name, bench_desc=bench_desc)
                if level == "alg":
                    mqt_level = BenchmarkLevel.ALG
                elif level == "indep":
                    mqt_level = BenchmarkLevel.INDEP
                else:
                    raise ValueError(f"Benchmark level: {level} not supported")
                return get_benchmark(bench_name, mqt_level, circuit_size=N)

            # Give the function a stable python identifier (handy for debugging)
            _wrapper.__name__ = f"mqt_{bench_name.replace('-', '_')}"
            return _wrapper

        wrapper = _make_mqt_wrapper(_name, _desc)
        reg.generator(f"mqt:{_name}")(wrapper)


# Call the registration function at import time
register_mqt_benchmarks()


@register.generator("prep_select")
def prep_select_circuit(N: int, target_state: int = 1) -> QuantumCircuit:
    """
    Prepare a "preparation and selection" circuit on N qubits to select the target_state.
    This is like an oracle step in a Grover's search algorithm.

    Parameters:
        N (int): Number of qubits
        target_state (int): The integer representation of the target state to select (0 to 2^N - 1)
    """
    # replaced assert with explicit check
    if not (0 <= target_state < 2**N):
        raise ValueError(
            f"target_state must be in the range [0, 2^N - 1]; got {target_state} for N={N}"
        )
    target_state = f"{target_state:0{N}b}"

    qc = QuantumCircuit(N)
    qc.h(range(N))

    # Flip the target state to be all |1>
    # Qiskit is little-endian, so we reverse the bit order
    for qubit, bit in enumerate(reversed(target_state)):
        if bit == "0":
            qc.x(qubit)

    # Flip the phase on just the target state
    controls = list(range(N - 1))
    target = N - 1
    qc.mcp(np.pi, controls, target)

    # Revert the flip
    for qubit, bit in enumerate(reversed(target_state)):
        if bit == "0":
            qc.x(qubit)

    return qc


@register.generator("qcnn")
def qcnn_circuit(N: int, seed=12345):
    """
    A circuit that implements the convolutional layers of a QCNN.

    Given a number of qubits N, the circuit applies a series of RXX and RY gates
    in a hierarchical manner, similar to a classical convolutional neural network.

    Each layer connects pairs of qubits that are 2^layer_index apart, followed by single
    qubit RY rotations (similar to activation functions in classical CNNs).

    Note this doesn't do any pooling or measurement, its just the convolutional layers.

    Parameters:
        N (int): Number of qubits

    Returns:
        QuantumCircuit: Output circuit
    """
    rng = np.random.default_rng(seed=seed)

    qc = QuantumCircuit(N)
    num_layers = int(np.ceil(np.log2(N)))
    for i_layer in range(num_layers):
        for i_sub_layer in [0, 2**i_layer]:
            for i_q1 in range(i_sub_layer, N, 2 ** (i_layer + 1)):
                i_q2 = 2**i_layer + i_q1
                if i_q2 < N:
                    qc.rxx(rng.random(), i_q1, i_q2)
                    qc.ry(rng.random(), i_q1)
                    qc.ry(rng.random(), i_q2)

    return qc


@register.generator("qft")
def qft_circuit(N: int) -> QuantumCircuit:
    """
    Create a Quantum Fourier Transform (QFT) circuit on N qubits
    """
    qc = QuantumCircuit(N)

    for i in range(N):
        for j in range(i):
            phi = np.pi * (2 ** (j - i))
            qc.cp(phi, j, i)
        qc.h(i)

    # Final bit-reversal to match most significant to least significant ordering
    for k in range(N // 2):
        qc.swap(k, N - k - 1)

    return qc


@register.generator("qv")
def qv_circuit(N: int, depth: int = 3, seed: int = 12345) -> QuantumCircuit:
    """
    Generate a quantum volume circuit for N qubits and given depth.

    From [1]_, a quantum volume circuit consists of layers of random elements
    of SU(4) applied between pairs of qubits in a random partition.

    Parameters:
        N (int): Number of qubits
        depth (int): Depth of the circuit (layers of SU(4) operations)
        seed (int): Random seed for reproducibility
    Returns:
        QuantumCircuit: The generated quantum volume circuit

    References:

    [1] A. Cross et al. Validating quantum computers using
    randomized model circuits, Phys. Rev. A 100, 032328 (2019).
    `arXiv:1811.12926 <https://arxiv.org/abs/1811.12926>`__
    """
    import numpy as np

    rng = np.random.default_rng(seed=seed)

    qc = QuantumCircuit(N)
    width = N // 2
    # Below code from https://github.com/Qiskit/qiskit/blob/c99f325baac1ea19ec4a316299579e9101e76271/qiskit/circuit/library/quantum_volume.py

    # For each layer, generate a permutation of qubits
    # Then generate and apply a Haar-random SU(4) to each pair

    # Generate all the unitaries at once for efficiency,
    unitaries = scipy.stats.unitary_group.rvs(4, depth * width, rng).reshape(
        depth, width, 4, 4
    )
    qubits = tuple(range(N))
    for row in unitaries:
        perm = rng.permutation(N)
        for w, unitary in enumerate(row):
            gate = UnitaryGate(unitary, check_input=False, num_qubits=2)
            qubit = 2 * w
            qc.append(gate, [qubits[perm[qubit]], qubits[perm[qubit + 1]]])
    return qc


def lattice_to_qubit_mapping(N: int) -> list[tuple[int, int]]:
    """Generate qubit mapping for the square Heisenberg problem Hamiltonian."""
    nnodes = int(np.sqrt(N))
    # replaced assert with explicit check
    if nnodes * nnodes != N:
        raise ValueError(f"N must be a perfect square; got N={N}")
    # Create a 2D grid of qubit indices
    lattice = np.arange(nnodes * nnodes).reshape(
        nnodes, nnodes
    )  # generate rows in order
    lattice[1::2, :] = lattice[1::2, ::-1]  # reverse every other row
    current = lattice.flatten()  # Flatten the arrays
    # Get right and down neighbors using roll
    right = np.roll(lattice, shift=-1, axis=1).flatten()
    down = np.roll(lattice, shift=-1, axis=0).flatten()
    return list(
        {tuple(sorted(pair)) for pair in zip(current, right)}
        | {tuple(sorted(pair)) for pair in zip(current, down)}
    )


@register.generator("square_heisenberg")
def square_heisenberg_circuit(
    N: int, depth: int = 3, seed: int = 12345
) -> QuantumCircuit:
    """
    Generate a circuit that simulates a square lattice Heisenberg model on N qubits.

    This is based on Hamlib (https://arxiv.org/pdf/2306.13126) and corresponds to equation 9
    in the paper, using only an XXX model. We assume a square lattice with periodic boundary conditions.

    This one considers H = -0.5

    Parameters:
        N (int): The lattice will be sqrt(N) x sqrt(N), so N should be a perfect square
        depth (int): Number of Trotter steps to use
        seed (int): Random seed for reproducibility
    """

    pstrings = []
    # Pairwise Paulis
    for op in "X", "Y", "Z":
        for p in lattice_to_qubit_mapping(N):
            pstring = ["I"] * N
            pstring[p[0]] = pstring[p[1]] = op
            pstrings.append("".join(pstring))
    # External field
    pstrings.extend("".join(["I" * n, "Z", "I" * (N - n - 1)]) for n in range(N))
    coeffs = [1.0] * (len(pstrings) - N) + [0.5] * N

    # convert to circuit via trotterization
    qc = QuantumCircuit(N)
    step = PauliEvolutionGate(SparsePauliOp(pstrings, coeffs), time=0.1)
    qc.append(step, range(N))
    qc = qc.decompose(reps=depth)
    return qc
