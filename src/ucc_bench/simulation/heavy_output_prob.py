"""
This module implements the heavy output probability metric for simulation benchmarks.

The implementation differs from other metrics that calculate an expected value because
it is a metric on the distribution of measurement results.
"""

from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel
from qiskit_aer import AerSimulator
import numpy as np
import math
from typing import Set
from ..registry import register
from ..results import SimulationMetrics

# Use a fix number of shots to measure heavy output probability. This matches
# the default number of shots qiskit uses in the AerSimulator at the time the
# code was authored.
NUM_SHOTS = 1024


def get_heavy_bitstrings(circuit: QuantumCircuit) -> Set[str]:
    """Calculate the set of heavy bitstrings for a given circuit."""
    # Don't use parallel threads to avoid issues in higher level parallelism
    # in the benchmarks
    simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    result = simulator.run(circuit, shots=NUM_SHOTS).result()
    counts = list(result.get_counts().items())
    median = np.median([c for (_, c) in counts])
    return set(bitstring for (bitstring, p) in counts if p > median)


def estimate_heavy_output_prob(
    circuit: QuantumCircuit, noise_model: NoiseModel
) -> float:
    heavy_bitstrings = get_heavy_bitstrings(circuit)
    simulator = AerSimulator(
        method="statevector",
        noise_model=noise_model,
        max_parallel_threads=1,
    )
    result = simulator.run(circuit, shots=NUM_SHOTS).result()
    heavy_counts = sum(
        result.get_counts().get(bitstring, 0) for bitstring in heavy_bitstrings
    )
    nshots = 1024
    return (
        heavy_counts - 2 * math.sqrt(heavy_counts * (nshots - heavy_counts))
    ) / nshots


@register.output_metric("heavy_output")
def calc_heavy_output_observables(
    uncompiled_circuit: QuantumCircuit,
    compiled_circuit: QuantumCircuit,
    noise_model: NoiseModel,
) -> SimulationMetrics:
    # Ensure circuits are measured at the end to generate bitstrings
    uncompiled_circuit.measure_all()
    compiled_circuit.measure_all()

    uncompiled_ideal = estimate_heavy_output_prob(uncompiled_circuit, None)
    compiled_ideal = estimate_heavy_output_prob(compiled_circuit, None)
    uncompiled_noisy = estimate_heavy_output_prob(uncompiled_circuit, noise_model)
    compiled_noisy = estimate_heavy_output_prob(compiled_circuit, noise_model)

    return SimulationMetrics(
        uncompiled_ideal=uncompiled_ideal,
        compiled_ideal=compiled_ideal,
        uncompiled_noisy=uncompiled_noisy,
        compiled_noisy=compiled_noisy,
    )
