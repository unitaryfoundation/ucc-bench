# UCC Benchmark Results

This directory contains the "official" benchmark results of
[UCC](https://github.com/unitaryfoundation/ucc).

The top-level [`README`](../../README.md) explains the design an interface for
the benchmarks that generate these results generally. This file explains more
details specific to the "offical" results

## Directory Structure

## Relation to git history

## Github Action Workflows

## Legacy Results

Prior to `ucc-bench`, benchmark results were run and stored directly in the `ucc`
repository. For the plots showing benchmark results over time, we wanted to include
those earlier results. We did this by editing the corresponding [plot script](https://github.com/unitaryfoundation/ucc/blob/470f8e6a69e6c8bf209dc904c21d38940e7b8d3b/benchmarks/scripts/plot_avg_benchmarks_over_time.py#L68)
and saving a CSV with the aggregated results. Those "legacy" results are saved as [legacy_timing_results.csv][./timing_benchmarks/legacy_timing_results.csv], and then loaded into the new [plot script](../../.github/scripts/plot_avg_by_time_benchmark.py) to show the full history.
