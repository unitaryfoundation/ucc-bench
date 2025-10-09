This document gives a high-level overview of the modules in `ucc-bench`

## Architecture
* `main.py`: Handles command-line argument parsing, logging setup, loading the suite specification, initiating the run, and saving results.
* `runner.py`: Orchestrates the execution of benchmark tasks using concurrent.futures.ProcessPoolExecutor for parallelism. It calls run_task for each compiler/benchmark combination. run_task performs transpilation, compilation, optional simulation, and gathers results.
* `suite.py`: Defines Pydantic models (BenchmarkSuite, BenchmarkSpec, CompilerSpec, SimulationSpec) for parsing and validating the TOML configuration file. Handles path resolution for QASM files.
* `results.py`: Defines Pydantic models for structuring the output results (SuiteResults, BenchmarkResult, Metadata, CompilationMetrics, SimulationMetrics, etc.) and includes the save_results function.
* `registry.py`: Implements the Registry class and register instance. Provides decorators (@register.compiler, @register.observable, @register.output_metric) to dynamically register new components.
* `compilers/`: Contains modules for specific compiler implementations.
* * `base_compiler.py`: Defines the abstract BaseCompiler class interface.
* * `_compiler.py`: Concrete implementations for Qiskit, Cirq, PyTket, and UCC, inheriting from BaseCompiler and registered using the decorator.
* `simulation/`: Contains modules related to circuit simulation.
* * `noise_models.py`: Defines functions to create noise models (currently a standard depolarizing model).
* * `observables.py`: Provides functions to calculate expectation values and includes implementations of registered observables (computational_basis, qaoa).
* * `heavy_output_prob.py`: Implements the Heavy Output Probability metric as a registered output metric.

## Circuit Unoptimization

We provide a dedicated suite at `benchmarks/compilation_benchmarks_unoptimized.toml`
containing circuits that have already been processed by the "elementary" quantum
unoptimization recipe (arXiv:2311.03805). The resulting QASM lives in
`benchmarks/circuits/unoptimized`. If the recipe parameters change, regenerate the
artefacts by running `uv run python benchmarks/scripts/generate_unoptimized_circuits.py`.
