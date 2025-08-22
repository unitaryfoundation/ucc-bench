This directory contains scripts used to generate plots of benchmark performance.
These scripts are called from some automated workflows defined in `.github/scripts`, but are
placed here for users who want to run them on local results or customize the output.

## Plotting Scripts

### 1. `plot_latest_benchmark.py`

- **Purpose:**
  Generates a bar plot comparing compiler performance (compile time and gate count) for each circuit in the latest benchmark run.
- **Usage:**
  ```
  uv run python plot_latest_benchmark.py <root_dir> <runner_name> [--csv_path <csv_file>]
  ```
  - `<root_dir>`: Path to the root directory containing benchmark results.
  - `<runner_name>`: Name of the runner (subdirectory under `<root_dir>`).
  - `--csv_path`: (Optional) Path to a CSV file with benchmark data. If provided, the script will use this file instead of querying the results database.

- **Output:**
  Saves a PNG file named `latest_compiler_benchmarks_by_circuit.png` in the runner's directory.

- **Typical Use Cases:**
  - To visualize results from the latest official benchmark run.
  - To plot results from a custom or local run by specifying a CSV file. *Note that by default, results from local benchmark runs are saved in ucc/.local_results.

### 2. `plot_avg_by_time_benchmark.py`

- **Purpose:**
  Plots the average compiler performance (compile time and compiled ratio) over time, highlighting compiler version changes.
- **Usage:**
  ```
  uv run python plot_avg_by_time_benchmark.py <root_dir> <runner_name>
  ```
  - `<root_dir>`: Path to the root directory containing benchmark results.
  - `<runner_name>`: Name of the runner (subdirectory under `<root_dir>`).

- **Output:**
  Saves a PNG file named `avg_compiler_benchmarks_over_time.png` in the runner's directory.

- **Typical Use Cases:**
  - To track performance trends and the impact of compiler updates across official runs.
  - To analyze historical data, including legacy results if present.


