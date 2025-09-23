from shared import get_compiler_colormap

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def plot_compiled_metrics(
    csv_path, compiled_ideal_line=False, uncompiled_noisy_line=False
):
    """
    Plot compiled_ideal and compiled_noisy for each compiler and benchmark as subplots.
    If compiled_ideal_line is True, plot compiled_ideal as a horizontal line instead of a bar.
    If uncompiled_noisy_line is True, plot uncompiled_noisy as a horizontal line instead of a bar.
    """
    df = pd.read_csv(csv_path)
    benchmarks = df["benchmark_id"].unique()
    compilers = df["compiler"].unique()
    n_benchmarks = len(benchmarks)
    ncols = 3
    nrows = int(np.ceil(n_benchmarks / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), sharex=True)
    axes = axes.flatten()

    bar_width = 0.25
    group_gap = 0.15
    index = np.arange(len(compilers)) * (3 * bar_width + group_gap)
    # Use shared colormap for compilers
    compiler_colors = get_compiler_colormap()

    for i, ax in enumerate(axes):
        if i < n_benchmarks:
            benchmark = benchmarks[i]
            sub = df[df["benchmark_id"] == benchmark]
            bars_ideal = []
            bars_noisy = []
            bars_uncompiled_noisy = []
            for compiler in compilers:
                row = sub[sub["compiler"] == compiler]
                bars_ideal.append(
                    row["compiled_ideal"].values[0] if not row.empty else np.nan
                )
                bars_noisy.append(
                    row["compiled_noisy"].values[0] if not row.empty else np.nan
                )
                bars_uncompiled_noisy.append(
                    row["uncompiled_noisy"].values[0] if not row.empty else np.nan
                )
            for j, compiler in enumerate(compilers):
                base = index[j]
                # Plot compiled_ideal as bar or line
                if not compiled_ideal_line:
                    ax.bar(
                        base - bar_width,
                        bars_ideal[j],
                        bar_width,
                        label="ideal" if j == 0 else "",
                        color=compiler_colors.get(compiler, "#4C72B0"),
                        alpha=0.7,
                    )
                # Plot uncompiled_noisy as bar or line
                if not uncompiled_noisy_line:
                    ax.bar(
                        base,
                        bars_uncompiled_noisy[j],
                        bar_width,
                        label="uncompiled_noisy" if j == 0 else "",
                        color=compiler_colors.get(compiler, "#55A868"),
                        alpha=0.5,
                    )
                # compiled_noisy always as bar
                ax.bar(
                    base + bar_width,
                    bars_noisy[j],
                    bar_width,
                    label="compiled_noisy" if j == 0 else "",
                    color=compiler_colors.get(compiler, "#DD8452"),
                    alpha=1.0,
                    # hatch="//",ƒ
                )
            # Draw horizontal line for compiled_ideal if requested
            if compiled_ideal_line:
                ideal_val = bars_ideal[0] if bars_ideal else np.nan
                ax.axhline(
                    ideal_val,
                    color="black",
                    linestyle="--",
                    linewidth=2,
                    label="ideal",
                )
            # Draw horizontal line for uncompiled_noisy if requested
            if uncompiled_noisy_line:
                uncompiled_noisy_val = (
                    bars_uncompiled_noisy[0] if bars_uncompiled_noisy else np.nan
                )
                ax.axhline(
                    uncompiled_noisy_val,
                    color="red",
                    linestyle="--",
                    linewidth=2,
                    label="uncompiled_noisy",
                )
            ax.set_xticks(index)
            ax.set_xticklabels(compilers, rotation=30)
            ax.set_title(f"Benchmark: {benchmark}")
            ax.set_ylabel("Value")
            ax.legend()
        else:
            ax.set_title("")
    plt.tight_layout()
    plt.show()


def plot_relative_error(csv_path):
    """
    Plot the relative error between compiled_noisy and uncompiled_ideal for each compiler and benchmark as subplots.
    """
    df = pd.read_csv(csv_path)
    benchmarks = df["benchmark_id"].unique()
    compilers = df["compiler"].unique()
    n_benchmarks = len(benchmarks)
    ncols = 3
    nrows = int(np.ceil(n_benchmarks / ncols))
    # Compute relative error: (compiled_noisy - uncompiled_ideal) / uncompiled_ideal
    df["relative_error"] = abs(
        (df["uncompiled_ideal"] - df["compiled_noisy"]) / df["uncompiled_ideal"]
    )

    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), sharex=True)
    axes = axes.flatten()
    index = np.arange(len(compilers))
    compiler_colors = get_compiler_colormap()

    for i, ax in enumerate(axes):
        if i < n_benchmarks:
            benchmark = benchmarks[i]
            sub = df[df["benchmark_id"] == benchmark]
            rel_errs = []
            for j, compiler in enumerate(compilers):
                row = sub[sub["compiler"] == compiler]
                rel_errs.append(
                    row["relative_error"].values[0] if not row.empty else np.nan
                )
                ax.bar(
                    j,
                    rel_errs[-1],
                    color=compiler_colors.get(compiler, "#4C72B0"),
                    width=0.5,
                )
            ax.set_xticks(index)
            ax.set_xticklabels(compilers, rotation=30)
            ax.set_title(f"Benchmark: {benchmark}")
            ax.set_ylabel("Relative Error")
            ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        else:
            ax.set_title("")
    plt.suptitle("Relative Error", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.show()


filename = "/Users/jordansullivan/UnitaryFoundation/ucc-bench/.local_results/Jordans-MacBook-Pro.local/simulation_benchmarks/20250923/20250923144414.98be5c07-8a2a-40d4-9720-2ea4fdc23f7e.simulation.csv"

plot_relative_error(filename)
# plot_compiled_metrics(filename, compiled_ideal_line=True, uncompiled_noisy_line=True)
