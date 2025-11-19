import pytest

from ucc_bench.simulation.observables import generate_qaoa_observable


def test_qaoa_observable_filters_edges_for_small_num_qubits():
    obs_5 = generate_qaoa_observable(5)
    # All pauli strings should be length 5
    assert all(len(pstr) == 5 for pstr, _ in obs_5.to_list()), (
        "Pauli strings must match num_qubits"
    )
    # Each term is ZZ on some pair; so each string must have exactly two Z's
    for pstr, coeff in obs_5.to_list():
        assert pstr.count("Z") == 2, f"Each term should be a ZZ; got {pstr}"  # noqa: S101


def test_qaoa_observable_minimum_qubits():
    with pytest.raises(ValueError):
        generate_qaoa_observable(1)


def test_qaoa_observable_full_10_qubits():
    obs_10 = generate_qaoa_observable(10)
    # Expect length equal to number of weighted edges in original list
    original_edge_count = 24
    assert len(obs_10.to_list()) == original_edge_count
    # Spot check one known coefficient value
    coeffs = [c for _, c in obs_10.to_list()]
    assert pytest.approx(6.720) in coeffs
