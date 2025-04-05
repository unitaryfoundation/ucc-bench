import argparse
import pandas as pd
import matplotlib.pyplot as plt
from adjustText import adjust_text

from ucc_bench.results import SuiteResultsDatabase, to_df_timing_detailed

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

# Gets time ordered list of results when at least one compiler version
# changed from the prior run.
timing_results = timing_results_db.get_versions_changed()
df = pd.concat((to_df_timing_detailed(d) for d in timing_results))
df["compile_time"] = df["compile_time_ms"] / 1000
df["compiled_ratio"] = df["compiled_multiq_gates"] / df["raw_multiq_gates"]
avg_df = (
    df.groupby(["uid_timestamp", "compiler"])
    .agg(
        {
            "compile_time_ms": "mean",
            "compiler_version": "first",  # assume same version per compiler per run
        }
    )
    .reset_index()
)

# --- STEP 3: Identify version change points per compiler ---
version_changes = []
last_versions = {}

for _, row in avg_df.iterrows():
    compiler = row["compiler"]
    version = row["compiler_version"]
    timestamp = row["uid_timestamp"]
    compile_time = row["compile_time_ms"]

    if compiler not in last_versions or version != last_versions[compiler]:
        version_changes.append(
            {
                "compiler": compiler,
                "uid_timestamp": timestamp,
                "compiler_version": version,
                "compile_time_ms": compile_time,
            }
        )
        last_versions[compiler] = version

version_changes_df = pd.DataFrame(version_changes)

# --- STEP 4: Create consistent color map ---
sorted_compilers = sorted(avg_df["compiler"].unique())
colors = plt.cm.tab10.colors
color_map = {
    compiler: colors[i % len(colors)] for i, compiler in enumerate(sorted_compilers)
}

# --- STEP 5: Plot ---
plt.figure(figsize=(12, 6))
texts = []

for compiler in sorted_compilers:
    comp_df = avg_df[avg_df["compiler"] == compiler]
    color = color_map[compiler]

    # Plot line
    plt.plot(
        comp_df["uid_timestamp"],
        comp_df["compile_time_ms"],
        label=compiler,
        color=color,
    )

    # Add version change annotations
    changes = version_changes_df[version_changes_df["compiler"] == compiler]
    for _, row in changes.iterrows():
        label_text = row["compiler_version"]
        label_date = row["uid_timestamp"].date()

        text = plt.text(
            row["uid_timestamp"],
            row["compile_time_ms"],
            label_text,
            fontsize=8,
            ha="center",
            va="bottom",
            color=color,
            bbox=dict(
                boxstyle="round,pad=0.2",
                edgecolor=color,
                facecolor="white",
                linewidth=0.8,
            ),
        )
        texts.append(text)

# Adjust text to avoid overlaps
adjust_text(texts, arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))

plt.xlabel("Timestamp")
plt.ylabel("Average Compile Time (ms)")
plt.title("Average Compile Time by Compiler (Version Change Points Annotated)")
plt.legend()
plt.tight_layout()
plt.show()
