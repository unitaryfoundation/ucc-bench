from pydantic import BaseModel, computed_field
from functools import cached_property
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .suite import BenchmarkSuite
import pandas as pd
from collections import defaultdict


class RunnerSpecs(BaseModel):
    os: str
    cpu: str
    ram_gb: float
    physical_cores: int

    @classmethod
    def from_system(cls):
        """Create an instance of RunnerInfo based on the settings of the current system"""
        import platform
        import psutil

        return cls(
            os=platform.system(),
            cpu=platform.processor(),
            ram_gb=psutil.virtual_memory().total / 1024**3,
            physical_cores=psutil.cpu_count(logical=False),
        )


class CompilerInfo(BaseModel):
    id: str
    version: str


class Metadata(BaseModel):
    uid: str
    uid_timestamp: datetime
    run_start: datetime
    run_end: datetime
    runner_name: str
    runner_specs: RunnerSpecs
    runner_version: str
    runner_args: List[str]
    ucc_hash: Optional[str] = None
    ucc_timestamp: Optional[datetime] = None


class CompilationMetrics(BaseModel):
    compilation_time_ms: float
    raw_multiq_gates: int
    compiled_multiq_gates: int


class SimulationMetrics(BaseModel):
    measurement_id: Optional[str] = None
    uncompiled_ideal: float
    compiled_ideal: float
    uncompiled_noisy: float
    compiled_noisy: float


class BenchmarkResult(BaseModel):
    compiler: CompilerInfo
    benchmark_id: str
    run_start: datetime
    run_end: datetime
    compilation_metrics: CompilationMetrics
    simulation_metrics: Optional[SimulationMetrics] = None
    target_device_id: Optional[str] = None


class SuiteResults(BaseModel):
    suite_specification: BenchmarkSuite
    metadata: Metadata
    results: List[BenchmarkResult]

    @computed_field(repr=False)
    @cached_property
    def compiler_versions(self) -> dict[str, str]:
        """Return a map of compiler id to version used in this benchmark run"""

        # Ensure that for a given compiler id, the version is the same across all results
        checker = defaultdict(set)
        for result in self.results:
            checker[result.compiler.id].add(result.compiler.version)
        for compiler_id, versions in checker.items():
            if len(versions) != 1:
                raise ValueError(
                    f"Compiler {compiler_id} has multiple versions: {versions}"
                )

        # return flattened map of compiler id to version
        return {result.compiler.id: result.compiler.version for result in self.results}


def out_path_for_results(
    suite_results: SuiteResults, root_dir: Path, file_suffix: str
) -> Path:
    """
    Get the output directory for the benchmark results.

    The output directory is organized by slowly varying dimensions for easier loading
    and comparison, so will be in the path {out_dir}/{runner_name}/{suite_id}/{uid_date}/{uid}.{file_suffix}
    """
    uid_timestamp = suite_results.metadata.uid_timestamp
    out_dir = (
        root_dir
        / suite_results.metadata.runner_name
        / suite_results.suite_specification.id
        / uid_timestamp.strftime("%Y%m%d")
        / f"{uid_timestamp.strftime('%Y%m%d%H%M%S')}.{suite_results.metadata.uid}.{file_suffix}"
    )
    return out_dir


def save_results_json(suite_results: SuiteResults, root_dir: Path) -> None:
    """
    Save the benchmark results in JSON format beneath the given root directory.

    Benchmark results are organized by slowly varying dimenions for easier loading
    and comparison, so will be in the path {out_dir}/{runner_name}/{suite_id}/{uid_date}/{uid}.json
    """
    out_path = out_path_for_results(suite_results, root_dir, "json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving JSON results to {out_path}")

    with open(out_path, "w") as f:
        f.write(suite_results.model_dump_json(indent=2))


def to_df_timing(suite_results: SuiteResults) -> pd.DataFrame:
    """Return a DataFrame of the timing results from the benchmark suite."""
    timing_data = [
        {
            "compiler": result.compiler.id,
            "benchmark_id": result.benchmark_id,
            "target_device_id": result.target_device_id,
            "raw_multiq_gates": result.compilation_metrics.raw_multiq_gates,
            "compile_time_ms": result.compilation_metrics.compilation_time_ms,
            "compiled_multiq_gates": result.compilation_metrics.compiled_multiq_gates,
        }
        for result in suite_results.results
    ]
    # Create a Pandas DataFrame and write it to a CSV file
    df = pd.DataFrame(timing_data)
    return df


def to_df_timing_detailed(suite_results: SuiteResults) -> pd.DataFrame:
    """Return a DataFrame of the timing results from the benchmark suite with
    detailed data about compiler version and timestamps."""
    timing_data = [
        {
            "compiler": result.compiler.id,
            "benchmark_id": result.benchmark_id,
            "target_device_id": result.target_device_id,
            "raw_multiq_gates": result.compilation_metrics.raw_multiq_gates,
            "compile_time_ms": result.compilation_metrics.compilation_time_ms,
            "compiled_multiq_gates": result.compilation_metrics.compiled_multiq_gates,
            "compiler_version": result.compiler.version,
            "uid_timestamp": suite_results.metadata.uid_timestamp,
        }
        for result in suite_results.results
    ]
    df = pd.DataFrame(timing_data)
    df["uid_timestamp"] = pd.to_datetime(df["uid_timestamp"], utc=True)
    return df


def to_df_simulation(suite_results: SuiteResults) -> pd.DataFrame:
    """Return a DataFrame of the simulation results from the benchmark suite."""

    measurement_data = [
        {
            "compiler": result.compiler.id,
            "benchmark_id": result.benchmark_id,
            "target_device_id": result.target_device_id,
            "measurement_id": result.simulation_metrics.measurement_id,
            "uncompiled_ideal": result.simulation_metrics.uncompiled_ideal,
            "compiled_ideal": result.simulation_metrics.compiled_ideal,
            "uncompiled_noisy": result.simulation_metrics.uncompiled_noisy,
            "compiled_noisy": result.simulation_metrics.compiled_noisy,
        }
        for result in suite_results.results
        if result.simulation_metrics
    ]
    df = pd.DataFrame(measurement_data)
    return df


def to_df_simulation_detailed(suite_results: SuiteResults) -> pd.DataFrame:
    """Return a DataFrame of the simulation results from the benchmark suite."""

    measurement_data = [
        {
            "compiler": result.compiler.id,
            "benchmark_id": result.benchmark_id,
            "target_device_id": result.target_device_id,
            "measurement_id": result.simulation_metrics.measurement_id,
            "uncompiled_ideal": result.simulation_metrics.uncompiled_ideal,
            "compiled_ideal": result.simulation_metrics.compiled_ideal,
            "uncompiled_noisy": result.simulation_metrics.uncompiled_noisy,
            "compiled_noisy": result.simulation_metrics.compiled_noisy,
            "compiler_version": result.compiler.version,
            "uid_timestamp": suite_results.metadata.uid_timestamp,
        }
        for result in suite_results.results
        if result.simulation_metrics
    ]
    df = pd.DataFrame(measurement_data)
    df["uid_timestamp"] = pd.to_datetime(df["uid_timestamp"], utc=True)
    return df


def save_results_csv(suite_results: SuiteResults, root_dir: Path) -> None:
    """
    Save the benchmark results in CSV format beneath the given root directory.

    Benchmark results are organized by slowly varying dimensions for easier loading
    and comparison, so will be in the path {out_dir}/{runner_name}/{suite_id}/{uid_date}/{uid}.compilation.csv
    or {out_dir}/{runner_name}/{suite_id}/{uid_date}/{uid}.simulation.csv
    """

    out_path = out_path_for_results(suite_results, root_dir, "compilation.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving timing results to {out_path}")
    to_df_timing(suite_results).to_csv(out_path, index=False, float_format="%.4f")

    sim_df = to_df_simulation(suite_results)

    if len(sim_df) > 0:
        out_path = out_path_for_results(suite_results, root_dir, "simulation.csv")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Saving simulation results to {out_path}")
        sim_df.to_csv(out_path, index=False, float_format="%.4f")


class SuiteResultsDatabase:
    _suite_results_time_ordered: List[SuiteResults]
    _suite_results_by_uid: dict[str, SuiteResults]

    def __init__(self, suite_results: List[SuiteResults]):
        self._suite_results_time_ordered = sorted(
            suite_results, key=lambda x: x.metadata.uid_timestamp
        )
        self._suite_results_by_uid = {
            result.metadata.uid: result for result in self._suite_results_time_ordered
        }

    @classmethod
    def from_root(
        cls, root_dir: str, runner_name: str, suite_id: str
    ) -> "SuiteResultsDatabase":
        """
        Load all results from the given root/runner/suite_id directory
        """
        suite_results = []
        for path in (Path(root_dir) / runner_name / suite_id).glob("**/*.json"):
            suite_results.append(
                SuiteResults.model_validate_json(path.read_text(encoding="utf-8"))
            )
        return cls(suite_results)

    def from_uid(self, uid: str) -> Optional[SuiteResults]:
        """
        Get the results from the given UID.
        Return None of no results found
        """
        return self._suite_results_by_uid.get(uid, None)

    def get_latest(self) -> SuiteResults:
        """
        Return the results with the most recent uid timestamp.
        """
        if len(self._suite_results_time_ordered) == 0:
            raise ValueError("No benchmark results were found")
        latest_result = self._suite_results_time_ordered[-1]
        return latest_result

    def get_versions_changed(self) -> List[SuiteResults]:
        """
        From the time ordered set of results, return only those results
        when the compiler version changed for at least one compiler.
        """
        res = []

        last_versions = None

        for result in self._suite_results_time_ordered:
            if last_versions is None or result.compiler_versions != last_versions:
                res.append(result)
                last_versions = result.compiler_versions

        return res
