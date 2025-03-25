from .suite import BenchmarkSuite, BenchmarkSpec
from .compilers import lookup_compiler, BaseCompiler
from .results import BenchmarkResult, CompilerInfo, CompilationMetrics
from typing import List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def run_task(compiler: BaseCompiler, benchmark: BenchmarkSpec) -> BenchmarkResult:
    """
    Run a single benchmark against the given compiler.
    """
    logger.info(
        f"Starting task for benchmark '{benchmark.id}' with compiler '{compiler.id()}'."
    )

    raw_circuit = compiler.qasm_to_native(open(benchmark.qasm_file, "r").read())
    logger.info(f"Compiling '{benchmark.qasm_file}' with compiler '{compiler.id()}'.")

    start_compile = datetime.now()
    compiled_circuit = compiler.compile(raw_circuit)
    end_compile = datetime.now()

    logger.info(
        f"Finished compiling benchmark '{benchmark.id}' with compiler '{compiler.id()}'. Duration: {(end_compile - start_compile).total_seconds()} seconds."
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


def run_suite(suite: BenchmarkSuite) -> List[BenchmarkResult]:
    """
    Run an entire benchmark suite against all compilers specified in the suite and return the results.
    """
    results = []
    for compiler in suite.compilers:
        compiler_cls = lookup_compiler(compiler.id)
        for benchmark in suite.benchmarks:
            results.append(run_task(compiler_cls(), benchmark))
    return results
