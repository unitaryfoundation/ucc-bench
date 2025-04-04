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

# First get dataframe that has timing data, dates, compiler version
df = pd.concat((to_df_timing_detailed(d) for d in timing_results_db.get_all()))
df["compile_time"] = df["compile_time_ms"] / 1000
df["compiled_ratio"] = df["compiled_multiq_gates"] / df["raw_multiq_gates"]

df["effective_timestamp"] = df.apply(
    lambda row: row["upstream_timestamp"]
    if row["compiler"] == "ucc"
    else row["uid_timestamp"],
    axis=1,
)
df["effective_date"] = df["effective_timestamp"].dt.date

# --- STEP 2: Get first version appearance ---
first_version_dates = (
    df.groupby(["compiler", "compiler_version"])["effective_timestamp"]
    .min()
    .reset_index()
)
first_version_dates["first_date"] = first_version_dates["effective_timestamp"].dt.date
first_version_dates.drop("effective_timestamp", axis=1, inplace=True)

# --- STEP 3: Filter original data to those first-date rows ---
df_merged = df.merge(first_version_dates, on=["compiler", "compiler_version"])
filtered = df_merged[df_merged["effective_date"] == df_merged["first_date"]]

# --- STEP 4: Average compile times per compiler & date ---
result = (
    filtered.groupby(["compiler", "first_date"])["compile_time"].mean().reset_index()
)
result.rename(columns={"first_date": "date"}, inplace=True)

# --- STEP 5: Add version labels ---
annotations = pd.merge(
    first_version_dates,
    result,
    left_on=["compiler", "first_date"],
    right_on=["compiler", "date"],
)

# --- STEP 6: Create consistent color map for compilers ---

sorted_compilers = sorted(result["compiler"].unique())
colors = plt.cm.tab10.colors  # use a colormap with enough distinct colors
color_map = {
    compiler: colors[i % len(colors)] for i, compiler in enumerate(sorted_compilers)
}

# --- STEP 7: Plot with smart color-coded labels ---
plt.figure(figsize=(12, 6))
texts = []

for compiler in sorted_compilers:
    comp_df = result[result["compiler"] == compiler]
    color = color_map[compiler]

    # Line
    plt.plot(comp_df["date"], comp_df["compile_time"], label=compiler, color=color)

    # Labels
    annots = annotations[annotations["compiler"] == compiler]
    for _, row in annots.iterrows():
        text = plt.text(
            row["date"],
            row["compile_time"],
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
        texts.append(text)

# Adjust text to avoid overlaps
plt.yscale("log")
adjust_text(texts, arrowprops=dict(arrowstyle="->", color="gray", lw=0.5))


plt.xlabel("Date")
plt.ylabel("Average Compile Time (s)")
plt.title("Average Compile Time by Compiler (First Version Appearance Only)")
plt.legend()
plt.tight_layout()
plt.show()
