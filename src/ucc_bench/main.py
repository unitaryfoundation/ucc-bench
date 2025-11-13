import argparse
import logging
import sys
from datetime import datetime
import uuid
import platform
from pathlib import Path
import psutil
from typing import Callable, List, Dict

from ucc_bench.suite import BenchmarkSuite
from ucc_bench.runner import run_suite
from ucc_bench.results import (
    SuiteResults,
    RunnerSpecs,
    Metadata,
    out_path,
    save_results_json,
    save_results_csv,
)
from ucc_bench.registry import register
from ucc_bench import __version__

# qBraid is setting up logging in a way that is incompatible with the logging setup in this file.
# To avoid conflicts, we will clear the existing handlers and configure logging here.
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logger = logging.getLogger(__name__)


###################
# Run command
###################


def _configure_run_logging(args, suite: BenchmarkSuite, uid_timestamp, uid) -> dict:
    """Configure logging for a run subcommand and return the logging config."""
    log_level = args.log_level.upper()
    log_format = "%(asctime)s [%(levelname)s] %(module)s: %(message)s"

    log_config = {
        "level": log_level,
        "format": log_format,
    }

    if args.log_stderr:
        log_config["stream"] = sys.stderr
    elif args.log_file:
        log_config["filename"] = args.log_file
        log_config["filemode"] = "w"
    else:
        log_filename = out_path(
            Path(args.out), args.runner_name, suite.id, uid_timestamp, uid, "log"
        )
        log_filename.parent.mkdir(parents=True, exist_ok=True)
        log_config["filename"] = str(log_filename)
        log_config["filemode"] = "w"

    logging.basicConfig(**log_config)

    if "stream" in log_config:
        # For downstream compatibility
        log_config.pop("stream")
        log_config["stderr"] = True
    return log_config


def _execute_command(args) -> int:
    """Execute the benchmark run command."""
    suite = BenchmarkSuite.load_toml(args.spec_path)
    uid_timestamp = args.uid_timestamp or datetime.now()
    uid = args.uid or str(uuid.uuid4())

    log_config = _configure_run_logging(args, suite, uid_timestamp, uid)

    ### Run the benchmark suite
    run_start = datetime.now()
    num_parallel = (
        int(args.parallel) if args.parallel else psutil.cpu_count(logical=False)
    )
    print(f"Running benchmark suite '{suite.id}' with {num_parallel} parallel tasks")
    print(f"Saving log to {log_config.get('filename', 'stdout')}")

    benchmark_results = run_suite(
        suite,
        num_parallel,
        log_config=log_config,
        only_compiler=args.only_compiler,
        only_benchmark=args.only_benchmark,
        only_target_device=args.only_target_device,
        strict=args.strict,
    )
    run_end = datetime.now()

    results = SuiteResults(
        suite_specification=suite,
        metadata=Metadata(
            uid=uid,
            uid_timestamp=uid_timestamp,
            run_start=run_start,
            run_end=run_end,
            runner_name=args.runner_name,
            runner_specs=RunnerSpecs.from_system(),
            runner_version=__version__,
            runner_args=sys.argv,
            ucc_hash=args.ucc_hash,
            ucc_timestamp=args.ucc_timestamp,
        ),
        results=benchmark_results,
    )
    logger.info(
        f"Finished running benchmark suite '{suite.id}', log in '{log_config.get('filename', 'stdout')}'"
    )

    save_results_json(results, Path(args.out))
    save_results_csv(results, Path(args.out))

    return 0


###################
# List command
###################


def _list_command(args) -> int:
    """Execute the list subcommand printing registered item ids."""

    # Map normalized category names to their retrieval functions
    category_getters: Dict[str, Callable[[], List[str]]] = {
        "generators": register.get_generators,
        "compilers": register.get_compilers,
        "observables": register.get_observables,
        "metrics": register.get_output_metrics,
        "target-devices": register.get_target_devices,
    }

    # Normalize user input
    category_aliases = {
        "generator": "generators",
        "compiler": "compilers",
        "observable": "observables",
        "metric": "metrics",
        "output-metrics": "metrics",
        "output_metric": "metrics",
        "target_device": "target-devices",
    }

    category = args.category.lower()
    normalized_category = category_aliases.get(category, category)

    if normalized_category == "all":
        for cat_name, getter_func in category_getters.items():
            print(f"{cat_name.capitalize()}:")
            items = getter_func()
            if not items:
                print("  (None registered)")
            for item in items:
                print(f"  - {item}")
            print()  # Add a blank line for readability
        return 0

    getter = category_getters.get(normalized_category)
    if getter:
        items = getter()
        if not items:
            print(f"No items found for category '{category}'.")
        for item in items:
            print(item)
        return 0
    else:
        print(
            f"Unknown category '{category}'. Valid categories: "
            f"{', '.join(list(category_getters.keys()) + ['all'])}",
            file=sys.stderr,
        )
        return 1


def _add_common_run_arguments(parser: argparse.ArgumentParser):
    """Add the common set of arguments for the 'run' command."""
    parser.add_argument(
        "--uid",
        help="Unique identifier for the run. If not provided, a random UUID is generated. For official results, use the git hash of the commit being tested.",
    )
    parser.add_argument(
        "--uid_timestamp",
        help="Timestamp for the unique identifier. If not provided, the current time is used. For official results, use the timestamp of the git commit being tested.",
    )
    parser.add_argument(
        "-o",
        "--out",
        default=".local_results",
        help="Root directory to save results. Defaults to '.local_results'. Individual run results are stored in a hierarchy within this directory.",
    )
    parser.add_argument(
        "--runner_name",
        default=platform.node(),
        help="Name of the runner machine. Should remain consistent across runs for comparison. Defaults to the current machine's hostname.",
    )
    parser.add_argument(
        "-j",
        "--parallel",
        help="Number of benchmarks to run in parallel. Defaults to the number of physical CPU cores if not specified.",
    )
    parser.add_argument(
        "--log_level",
        default="WARNING",
        help="Logging level for the application. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL. Defaults to 'WARNING'.",
    )
    parser.add_argument(
        "--log-file",
        help="Path to save the log file. If not provided, defaults to 'ucc_bench_run.log' next to the result files.",
        default=None,
    )
    parser.add_argument(
        "--log-stderr",
        action="store_true",
        help="Force logging to stderr instead of a file.",
    )
    parser.add_argument(
        "--only_compiler",
        help="Run benchmarks only for the specified compiler.",
    )
    parser.add_argument(
        "--only_benchmark",
        help="Run only the specified benchmark.",
    )
    parser.add_argument(
        "--only_target_device",
        help="Run benchmarks which match only the specified target device.",
    )
    parser.add_argument(
        "--ucc_hash",
        help="Hash of commit of UCC being tested. This is used to track the version of UCC being benchmarked.",
    )
    parser.add_argument(
        "--ucc_timestamp",
        help="Timestamp of commit of UCC being tested. This is used to track the version of UCC being benchmarked.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="If set, the run of the benchmark suite will fail if any individual benchmark fails.",
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="UCC Bench: run compiler/simulation benchmarks and list registered components."
    )
    parser.add_argument(
        "--version", action="version", version=f"ucc-bench {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="command", metavar="<command>", help="Available commands"
    )

    # Run subcommand
    run_parser = subparsers.add_parser(
        "execute",
        help="Execute a benchmark suite defined in a TOML specification file.",
    )
    run_parser.add_argument(
        "spec_path", help="Path to the TOML file specifying the benchmark suite to run."
    )
    _add_common_run_arguments(run_parser)  # Add all the shared --flag arguments

    # List subcommand
    list_parser = subparsers.add_parser(
        "list",
        help="List registered items (generators, compilers, observables, metrics, target-devices, all).",
    )
    list_parser.add_argument(
        "category",
        help="Category to list: generators | compilers | observables | metrics | target-devices | all",
    )

    return parser


def main() -> None:
    parser = _build_parser()

    command_funcs = {
        "execute": _execute_command,
        "list": _list_command,
    }

    # Define known commands and global flags that aren't legacy
    known_commands = command_funcs.keys() | {"-h", "--help", "--version"}

    # Handle legacy implicit 'run' command
    # If argv is not empty, and the first arg is not a known command and not a flag
    argv = sys.argv[1:]
    if (
        sys.argv
        and len(argv) > 0
        and argv[0] not in known_commands
        and not argv[0].startswith("-")
    ):
        print(
            "WARNING: Implicit run mode is deprecated and will be removed in a future release. "
            "Please use 'ucc-bench execute <spec_path>'.",
            file=sys.stderr,
        )
        # Prepend 'execute' to trigger the execute subcommand
        argv.insert(0, "execute")

    args = parser.parse_args(argv)
    func = command_funcs.get(args.command)
    if func:
        exit_code = func(args)
        sys.exit(exit_code)
    else:
        # No subcommand was provided (and not legacy), so show help.
        parser.print_help(sys.stderr)
        sys.exit(2)


if "__main__" == __name__:
    main()
