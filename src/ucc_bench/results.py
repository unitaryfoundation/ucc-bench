from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .suite import BenchmarkSuite
import pandas as pd


class RunnerInfo(BaseModel):
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


class Metadata(BaseModel):
    uid: str
    uid_timestamp: datetime
    run_start: datetime
    run_end: datetime
    runner_name: str
    runner_specs: RunnerInfo
    runner_version: str
    runner_args: List[str]
    upstream_hash: Optional[str] = None
    upstream_timestamp: Optional[datetime] = None


class CompilerInfo(BaseModel):
    id: str
    version: str


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


class SuiteResults(BaseModel):
    suite_specification: BenchmarkSuite
    metadata: Metadata
    results: List[BenchmarkResult]


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
            "raw_multiq_gates": result.compilation_metrics.raw_multiq_gates,
            "compile_time_ms": result.compilation_metrics.compilation_time_ms,
            "compiled_multiq_gates": result.compilation_metrics.compiled_multiq_gates,
        }
        for result in suite_results.results
    ]
    # Create a Pandas DataFrame and write it to a CSV file
    df = pd.DataFrame(timing_data)
    return df


def to_df_simulation(suite_results: SuiteResults) -> pd.DataFrame:
    """Return a DataFrame of the simulation results from the benchmark suite."""

    measurement_data = [
        {
            "compiler": result.compiler.id,
            "benchmark_id": result.benchmark_id,
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
    to_df_timing(suite_results).to_csv(out_path, index=False)

    sim_df = to_df_simulation(suite_results)

    if len(sim_df) > 0:
        out_path = out_path_for_results(suite_results, root_dir, "simulation.csv")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Saving simulation results to {out_path}")
        sim_df.to_csv(out_path, index=False)


class SuiteResultsDatabase(BaseModel):
    _suite_results: List[SuiteResults]
    _suite_results_by_uid: dict[str, SuiteResults]

    def __init__(self, suite_results: List[SuiteResults]):
        super().__init__(suite_results=suite_results)
        self._suite_results_by_uid = {
            result.metadata.uid: result for result in suite_results
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
