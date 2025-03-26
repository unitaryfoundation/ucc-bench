from .suite import BenchmarkSuite, BenchmarkSpec
from .compilers import lookup_compiler, BaseCompiler
from .results import BenchmarkResult, CompilerInfo, CompilationMetrics
from typing import List
from datetime import datetime
import logging
from logging import LoggerAdapter
from concurrent.futures import ProcessPoolExecutor


def run_task(compiler: BaseCompiler, benchmark: BenchmarkSpec) -> BenchmarkResult:
    """
    Run a single benchmark against the given compiler.
    """

    class ContextualLogger(LoggerAdapter):
        def process(self, msg, kwargs):
            return (
                f"[{self.extra['benchmark_id']}][{self.extra['compiler_id']}] {msg}",
                kwargs,
            )

    # Since this function is likely run in a separate process
    # get the logger locally versus at module scope
    logger = logging.getLogger(__name__)
    logger = ContextualLogger(
        logger, extra={"benchmark_id": benchmark.id, "compiler_id": compiler.id()}
    )

    start_transpile = datetime.now()
    raw_circuit = compiler.qasm_to_native(
        open(benchmark.resolved_qasm_file, "r").read()
    )
    end_transpile = datetime.now()
    logger.info(
        f"Finished transpiling. Duration: {(end_transpile - start_transpile).total_seconds()} seconds."
    )

    logger.info(f"Begin compiling '{benchmark.qasm_file}'")

    start_compile = datetime.now()
    compiled_circuit = raw_circuit  # compiler.compile(raw_circuit)
    end_compile = datetime.now()

    logger.info(
        f"Finished compiling. Duration: {(end_compile - start_compile).total_seconds()} seconds."
    )
    return BenchmarkResult(
        compiler=CompilerInfo(id=compiler.id(), version=compiler.version()),
        benchmark_id=benchmark.id,
        run_start=start_compile,
        run_end=end_compile,
        compilation_metrics=CompilationMetrics(
            compilation_time_ms=(end_compile - start_compile).total_seconds() * 1000,
            raw_multiq_gates=compiler.count_multi_qubit_gates(raw_circuit),
            compiled_multiq_gates=compiler.count_multi_qubit_gates(compiled_circuit),
        ),
    )


def configure_worker_logging(log_level):
    """
    Configure logging for worker processes.
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(module)s [%(processName)s]: %(message)s",
    )


def run_suite(suite: BenchmarkSuite, num_parallel: int) -> List[BenchmarkResult]:
    """
    Run an entire benchmark suite against all compilers specified in the suite and return the results.
    """
    results = []
    tasks = []

    with ProcessPoolExecutor(
        max_workers=num_parallel,
        initializer=configure_worker_logging,
        initargs=(logging.getLogger().level,),
    ) as executor:
        for compiler in suite.compilers:
            compiler_cls = lookup_compiler(compiler.id)
            for benchmark in suite.benchmarks:
                # Submit tasks to the executor
                tasks.append(executor.submit(run_task, compiler_cls(), benchmark))

        # Collect results as tasks complete
        for future in tasks:
            results.append(future.result())

    return results
