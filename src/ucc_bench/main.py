import argparse
import logging
import sys
from datetime import datetime
import uuid
import platform
from pathlib import Path
import psutil

from .suite import BenchmarkSuite
from .runner import run_suite
from .results import SuiteResults, RunnerInfo, Metadata, save_results
from . import __version__

# qBraid is setting up logging in a way that is incompatible with the logging setup in this file.
# To avoid conflicts, we will clear the existing handlers and configure logging here.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Command line utility to run UCC compiler benchmark comparison"
    )
    parser.add_argument(
        "spec_path", help="The TOML file that specifies the benchmark suite to run"
    )
    parser.add_argument(
        "--uid",
        help="Unique identifier for the run. When not provided, a random UUID is generated. When running official results, this should be the git hash of the git commit to run against.",
    )
    parser.add_argument(
        "--uid_timestamp",
        help="Timestamp to use for the unique identifier. When not provided, the current time is used. When running official results, this should be the timestamp of the git commit we are running against.",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=".local_results",
        help="Root directory to save results. Defaults to .local_results.",
    )
    parser.add_argument(
        "--runner_name",
        default=platform.node(),
        help="Name of runner machine; should be stable across runs you want to compare. Defaults to the hostname of current machine.",
    )
    parser.add_argument(
        "-j",
        "--parallel",
        help="Number of benchmarks to run in parallel. If unspecified, set to the number of physical cores on the machine",
    )
    parser.add_argument(
        "--log_level",
        default="WARNING",
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    )

    suite = BenchmarkSuite.load_toml(args.spec_path)

    run_start = datetime.now()
    num_parallel = (
        int(args.parallel) if args.parallel else psutil.cpu_count(logical=False)
    )
    logger.info(
        f"Running benchmark suite '{suite.id}' with {num_parallel} parallel tasks"
    )
    benchmark_results = run_suite(suite, num_parallel)
    run_end = datetime.now()

    results = SuiteResults(
        suite_specification=suite,
        metadata=Metadata(
            uid=args.uid or str(uuid.uuid4()),
            uid_timestamp=args.uid_timestamp or datetime.now(),
            run_start=run_start,
            run_end=run_end,
            runner_name=args.runner_name,
            runner_specs=RunnerInfo.from_system(),
            runner_version=__version__,
            runner_args=sys.argv,
        ),
        results=benchmark_results,
    )
    logger.info(f"Finished running benchmark suite '{suite.id}'")

    save_results(results, Path(args.out))
