import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from ucc_bench.results import SuiteResultsDatabase, to_df_timing

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Plot latest benchmark results.")
parser.add_argument("root_dir", type=str, help="Root directory of the benchmarks.")
parser.add_argument("runner_name", type=str, help="Name of the runner.")
args = parser.parse_args()

root_dir = args.root_dir
runner_name = args.runner_name

timing_results_db = SuiteResultsDatabase.from_root(
    root_dir, runner_name, "timing_benchmarks"
)
latest = timing_results_db.get_latest()

print(f"Latest benchmark results are : {latest.metadata.uid}")
print(f"Latest benchmark date is : {latest.metadata.uid_timestamp}")
latest_date = latest.metadata.uid_timestamp.strftime("%Y-%m-%d")

df_latest = to_df_timing(latest)
df_latest["compile_time"] = df_latest["compile_time_ms"] / 1000  # Convert to seconds


# Step 3: Define the bar width and create x-axis positions for the circuits
bar_width = 0.2
circuit_names = df_latest["benchmark_id"].unique()
circuit_names.sort()
x_positions = range(len(circuit_names))  # X positions for each circuit

# Create a dictionary to map circuit names to indices
circuit_name_to_index = {name: i for i, name in enumerate(circuit_names)}

# Step 4: Set up the figure and axes
fig, ax = plt.subplots(1, 2, figsize=(14, 7))

# Set color map for different compilers
# Get unique compilers and sort them alphabetically
unique_compilers = sorted(df_latest["compiler"].unique())

# Set color map for different compilers
colormap = plt.get_cmap("tab10", len(unique_compilers))
color_map = {compiler: colormap(i) for i, compiler in enumerate(unique_compilers)}


# Step 5: Plot compile time and gate count for each compiler
for i, (key, grp) in enumerate(df_latest.groupby("compiler")):
    # Get indices for each circuit in the current compiler group
    grp_indices = grp["benchmark_id"].map(circuit_name_to_index)

    # Plot compile time
    ax[0].bar(
        [
            grp_indices + i * bar_width for grp_indices in grp_indices
        ],  # Shift bars for each compiler
        grp["compile_time"],  # Compile time data
        width=bar_width,
        label=key,
        color=color_map[key],
    )

    # Plot gate count
    ax[1].bar(
        [
            grp_indices + i * bar_width for grp_indices in grp_indices
        ],  # Shift bars for each compiler
        grp["compiled_multiq_gates"],  # Gate count data
        width=bar_width,
        label=key,
        color=color_map[key],
    )

# Step 6: Customize plots
ax[0].set_title(f"Compiler Performance on Circuits (Date: {latest_date})")
ax[0].set_xlabel("Circuit Name")
ax[0].set_ylabel("Compile Time (s)")
ax[0].set_xticks(x_positions)
ax[0].set_xticklabels(circuit_names, rotation=75)
ax[0].set_yscale("log")

ax[1].set_title(f"Gate Counts on Circuits (Date: {latest_date})")
ax[1].set_xlabel("Circuit Name")
ax[1].set_ylabel("Compiled Gate Count")
ax[1].set_xticks(x_positions)
ax[1].set_xticklabels(circuit_names, rotation=75)
ax[1].set_yscale("log")

# Step 7: Add legend
ax[0].legend(title="Compiler")
ax[1].legend(title="Compiler")

# Adjust layout and save the figure
plt.tight_layout()
filename = Path(root_dir) / runner_name / "latest_compiler_benchmarks_by_circuit.png"
print(f"Saving plot to {filename}")
fig.savefig(filename)
