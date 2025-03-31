from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .suite import BenchmarkSuite

import logging

logger = logging.getLogger(__name__)


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


def save_results(results: SuiteResults, out_dir: Path) -> None:
    """
    Save the benchmark results in JSON format beneath the given root directory.

    Benchmark results are organized by slowly varying dimenions for easier loading
    and comparison, so will be in the path {out_dir}/{runner_name}/{suite_id}/{uid_date}/{uid.json}
    """
    out_path = (
        out_dir
        / results.metadata.runner_name
        / results.suite_specification.id
        / results.metadata.uid_timestamp.strftime("%Y%m%d")
        / f"{results.metadata.uid}.json"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving results to {out_path}")

    with open(out_path, "w") as f:
        f.write(results.model_dump_json(indent=2))
