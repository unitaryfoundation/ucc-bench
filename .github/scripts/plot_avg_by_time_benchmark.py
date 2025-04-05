import argparse
import pandas as pd
import matplotlib.pyplot as plt
from adjustText import adjust_text
from pathlib import Path
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

# --- STEP 2: Group by (uid_timestamp, compiler) ---
avg_df = (
    df.groupby(["uid_timestamp", "compiler"])
    .agg(
        {
            "compile_time_ms": "mean",
            "compiled_ratio": "mean",
            "compiler_version": "first",
        }
    )
    .reset_index()
)

# Convert compile_time to seconds
avg_df["compile_time_s"] = avg_df["compile_time_ms"] / 1000.0

# --- STEP 3: Detect version changes ---
version_changes = []
last_versions = {}

for _, row in avg_df.iterrows():
    compiler = row["compiler"]
    version = row["compiler_version"]
    timestamp = row["uid_timestamp"]

    if compiler not in last_versions or version != last_versions[compiler]:
        version_changes.append(
            {
                "compiler": compiler,
                "uid_timestamp": timestamp,
                "compiler_version": version,
                "compile_time_s": row["compile_time_s"],
                "compiled_ratio": row["compiled_ratio"],
            }
        )
        last_versions[compiler] = version

version_changes_df = pd.DataFrame(version_changes)

# --- STEP 4: Color map ---
sorted_compilers = sorted(avg_df["compiler"].unique())
colors = plt.get_cmap("tab10", len(sorted_compilers))
color_map = {compiler: colors(i) for i, compiler in enumerate(sorted_compilers)}

# --- STEP 5: Plot both metrics ---
fig, (ax1, ax2) = plt.subplots(
    2,
    1,
    figsize=(8, 8),
    sharex=True,
)
texts_ax1 = []
texts_ax2 = []

# --- Plot 1: compiled_ratio ---
for compiler in sorted_compilers:
    comp_df = avg_df[avg_df["compiler"] == compiler]
    color = color_map[compiler]

    ax1.plot(
        comp_df["uid_timestamp"], comp_df["compiled_ratio"], label=compiler, color=color
    )

    # Add version change annotations
    changes = version_changes_df[version_changes_df["compiler"] == compiler]
    for _, row in changes.iterrows():
        text = ax1.text(
            row["uid_timestamp"],
            row["compiled_ratio"],
            row["compiler_version"],
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
        texts_ax1.append(text)

ax1.set_ylabel("Compiled Ratio")
ax1.set_title("Average Compiled Ratio by Compiler")
ax1.grid(True)
ax1.legend(loc="best")

# --- Plot 2: compile_time_s (log scale) ---
for compiler in sorted_compilers:
    comp_df = avg_df[avg_df["compiler"] == compiler]
    color = color_map[compiler]

    ax2.plot(
        comp_df["uid_timestamp"], comp_df["compile_time_s"], label=compiler, color=color
    )

    changes = version_changes_df[version_changes_df["compiler"] == compiler]
    for _, row in changes.iterrows():
        text = ax2.text(
            row["uid_timestamp"],
            row["compile_time_s"],
            row["compiler_version"],
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
        texts_ax2.append(text)

ax2.set_ylabel("Compile Time (s, log scale)")
ax2.set_title("Average Compile Time by Compiler")
ax2.set_yscale("log")
ax2.set_xlabel("Timestamp")
ax2.grid(True)
ax2.legend(loc="best")

# --- Adjust labels separately for each axis ---
adjust_text(texts_ax1, ax=ax1, arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))

adjust_text(texts_ax2, ax=ax2, arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))

fig.tight_layout()

filename = Path(root_dir) / runner_name / "avg_compiler_benchmarks_over_time.png"
print(f"Saving plot to {filename}")
fig.savefig(filename)
