from typing import List, Optional
from datetime import datetime
import logging
from logging import LoggerAdapter
from concurrent.futures import ProcessPoolExecutor
from .suite import BenchmarkSuite, BenchmarkSpec
from .compilers import BaseCompiler
from .results import BenchmarkResult, CompilerInfo, CompilationMetrics
from .registry import register
from .simulation.observables import calc_expectation_value
from .simulation.noise_models import create_depolarizing_noise_model
from qbraid import transpile
from time import perf_counter, process_time
import multiprocessing
from qiskit.transpiler import Target
from .utils import validate_circuit_gates

# module-level logger that can be used before dispatching to worker processes
logger = logging.getLogger(__name__)


def run_task(
    compiler: BaseCompiler,
    benchmark: BenchmarkSpec,
    target_device: Optional[Target] = None,
    target_device_id: Optional[str] = None,
) -> BenchmarkResult:
    """
    Run a single benchmark against the given compiler.
    """

    class ContextualLogger(LoggerAdapter):
        def process(self, msg, kwargs):
            return (
                f"[{self.extra['benchmark_id']}][{self.extra['compiler_id']}][{self.extra['target_device_id']}] {msg}",
                kwargs,
            )

    # Since this function is likely run in a separate process
    # get the logger locally versus at module scope
    logger = logging.getLogger(__name__)
    logger = ContextualLogger(
        logger,
        extra={
            "benchmark_id": benchmark.id,
            "compiler_id": compiler.id(),
            "target_device_id": target_device_id,
        },
    )
    print(
        f"Running benchmark '{benchmark.id}' with compiler '{compiler.id()}' for target device '{target_device_id}'"
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

    start_compile_dt = datetime.now()
    start_compile_wall = perf_counter()
    start_compile_cpu = process_time()

    compiled_circuit = compiler.compile(raw_circuit, target_device=target_device)

    end_compile_cpu = process_time()
    end_compile_wall = perf_counter()
    end_compile_dt = datetime.now()

    cpu_time = end_compile_cpu - start_compile_cpu
    wall_time = end_compile_wall - start_compile_wall
    cpu_utilization = cpu_time / wall_time if wall_time > 0 else 0.0

    logger.info(
        f"Finished compiling. Wall Time: {wall_time:.4f}s, CPU Time: {cpu_time:.4f}s, Utilization: {cpu_utilization:.2%}"
    )

    # Validate that the compiled circuit only contains the allowed basis gates.
    # This check occurs after timing so it does not affect measured compilation
    # performance.
    validate_circuit_gates(compiled_circuit, {"rx", "ry", "rz", "h", "cx"})

    simulation_metrics = None
    if benchmark.simulate:
        logger.info(f"Running simulation '{benchmark.simulate}'")

        # convert to qiskit form for simulation
        raw_circuit_qiskit = transpile(raw_circuit, "qiskit")
        compiled_circuit_qiskit = transpile(compiled_circuit, "qiskit")

        # Use the single/standard depolarizing noise model for now
        noise_model = create_depolarizing_noise_model(
            raw_circuit_qiskit, compiled_circuit_qiskit
        )

        if register.has_observable(benchmark.simulate.measurement):
            observable = register.get_observable(benchmark.simulate.measurement)
            simulation_metrics = calc_expectation_value(
                observable(raw_circuit_qiskit.num_qubits),
                raw_circuit_qiskit,
                compiled_circuit_qiskit,
                noise_model,
            )
            simulation_metrics.measurement_id = observable._id
        elif register.has_output_metric(benchmark.simulate.measurement):
            output_metric = register.get_output_metric(benchmark.simulate.measurement)
            simulation_metrics = output_metric(
                raw_circuit_qiskit,
                compiled_circuit_qiskit,
                noise_model,
            )
            simulation_metrics.measurement_id = output_metric._id
        else:
            raise ValueError(
                f"Unknown measurement '{benchmark.simulate.measurement}' for benchmark '{benchmark.id}'"
            )

    print(
        f"Completed benchmark '{benchmark.id}' with compiler '{compiler.id()}' for target device '{target_device_id}'"
    )

    return BenchmarkResult(
        compiler=CompilerInfo(id=compiler.id(), version=compiler.version()),
        benchmark_id=benchmark.id,
        run_start=start_compile_dt,
        run_end=end_compile_dt,
        compilation_metrics=CompilationMetrics(
            compilation_time_ms=wall_time * 1000,
            raw_multiq_gates=compiler.count_multi_qubit_gates(raw_circuit),
            compiled_multiq_gates=compiler.count_multi_qubit_gates(compiled_circuit),
        ),
        simulation_metrics=simulation_metrics,
        target_device_id=target_device_id,
    )


def configure_worker_logging(log_level):
    """
    Configure logging for worker processes.
    """
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(module)s [%(processName)s]: %(message)s",
    )


def run_suite(
    suite: BenchmarkSuite,
    num_parallel: int,
    only_compiler: Optional[str] = None,
    only_benchmark: Optional[str] = None,
    only_target_device: Optional[str] = None,
) -> List[BenchmarkResult]:
    """
    Run an entire benchmark suite against all compilers specified in the suite and return the results.
    """
    results = []
    tasks = []

    # Ensure that the multiprocessing module uses the 'spawn' method for creating new processes
    # This helps ensure consistency because each process will start with a fresh Python interpreter
    # versus a fork of the current one.
    multiprocessing.set_start_method("spawn", force=True)

    with ProcessPoolExecutor(
        max_workers=num_parallel,
        initializer=configure_worker_logging,
        initargs=(logging.getLogger().level,),
    ) as executor:
        for compiler in suite.compilers:
            if only_compiler and compiler.id != only_compiler:
                continue

            compiler_cls = register.get_compiler(compiler.id)
            if not compiler_cls.is_supported():
                logger.warning(
                    f"Compiler '{compiler.id}' is not supported on this platform. Skipping."
                )
                continue
            target_devices = suite.target_devices or [
                None
            ]  # Default to None if no target devices specified

            for target_device_spec in target_devices:
                if only_target_device and target_device_spec.id != only_target_device:
                    continue

                target_device = (
                    register.get_target_device(target_device_spec.id)
                    if target_device_spec
                    else None
                )
                for benchmark in suite.benchmarks:
                    if only_benchmark and benchmark.id != only_benchmark:
                        continue

                    # Submit tasks to the executor
                    tasks.append(
                        executor.submit(
                            run_task,
                            compiler_cls(),
                            benchmark,
                            target_device,
                            target_device_spec.id if target_device else None,
                        )
                    )

        # Collect results as tasks complete
        for future in tasks:
            results.append(future.result())

    return results
