import argparse
from pathlib import Path
import sys
from typing import Dict, List, Optional, Callable

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from ucc_bench.results import SuiteResultsDatabase, to_df_timing, to_df_simulation
from shared import calculate_abs_relative_error, get_compiler_colormap


def get_compiler_markers() -> Dict[str, str]:
    """Returns a dictionary mapping compiler names to unique marker styles."""
    from ucc_bench.registry import register

    compilers = sorted(register.get_compilers())
    # Different marker styles for visual distinction
    markers = ["o", "s", "^", "D", "v", "<", ">", "p", "*", "h", "H", "+", "x"]
    return {compiler: markers[i % len(markers)] for i, compiler in enumerate(compilers)}


def apply_jittering(
    x_values: np.ndarray,
    y_values: np.ndarray,
    scale: str = "log",
    jitter_factor: float = 0.005,
    tolerance: float = 0.01,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply jittering to overlapping data points in either log or linear scale.
    """
    if len(x_values) < 2:
        return x_values, y_values

    # Transform data based on the specified scale
    x_trans = np.log10(x_values) if scale == "log" else np.array(x_values)
    y_trans = np.log10(y_values) if scale == "log" else np.array(y_values)

    x_range = x_trans.max() - x_trans.min()
    y_range = y_trans.max() - y_trans.min()

    # Avoid division by zero if all points are identical
    x_range = x_range if x_range > 0 else 1
    y_range = y_range if y_range > 0 else 1

    jittered_x = x_trans.copy()
    jittered_y = y_trans.copy()

    # Find and jitter overlapping points
    for i in range(len(x_trans)):
        for j in range(i + 1, len(x_trans)):
            tol_x = tolerance * x_range if scale == "linear" else tolerance
            tol_y = tolerance * y_range if scale == "linear" else tolerance

            if (
                abs(x_trans[i] - x_trans[j]) < tol_x
                and abs(y_trans[i] - y_trans[j]) < tol_y
            ):
                jitter_x = np.random.uniform(
                    -jitter_factor * x_range, jitter_factor * x_range
                )
                jitter_y = np.random.uniform(
                    -jitter_factor * y_range, jitter_factor * y_range
                )
                jittered_x[j] += jitter_x
                jittered_y[j] += jitter_y

    # Transform back to original scale if necessary
    if scale == "log":
        return 10**jittered_x, 10**jittered_y
    return jittered_x, jittered_y


def create_scatter_plot(
    ax: plt.Axes,
    df: pd.DataFrame,
    baseline_compiler: str,
    metric: str,
    title: str,
    xlabel: str,
    ylabel: str,
    use_log_scale: bool = True,
    annotate_baseline: bool = False,
):
    """Creates a single comparative scatter plot on a given Axes object."""
    color_map = get_compiler_colormap()
    marker_map = get_compiler_markers()

    baseline_data = df[df["compiler"] == baseline_compiler].set_index("benchmark_id")[
        metric
    ]
    if baseline_data.empty:
        return  # Nothing to plot if baseline data is missing

    # Merge all data with the baseline data for comparison
    plot_df = pd.merge(
        df,
        baseline_data.rename(f"{metric}_baseline"),
        left_on="benchmark_id",
        right_index=True,
    )
    # Ensure baseline compiler's points lie on the diagonal (y=x)
    plot_df.loc[plot_df["compiler"] == baseline_compiler, metric] = plot_df[
        f"{metric}_baseline"
    ]

    # Apply jittering to avoid overplotting
    x_jittered, y_jittered = apply_jittering(
        plot_df[f"{metric}_baseline"].values,
        plot_df[metric].values,
        scale="log" if use_log_scale else "linear",
    )
    plot_df["x_jittered"] = x_jittered
    plot_df["y_jittered"] = y_jittered

    # Plot points for each compiler
    for compiler, group in plot_df.groupby("compiler"):
        is_baseline = compiler == baseline_compiler
        ax.scatter(
            group["x_jittered"],
            group["y_jittered"],
            label=compiler,
            color=color_map.get(compiler, "gray"),
            marker=marker_map.get(compiler, "o"),
            s=60 if is_baseline else 50,
            edgecolors="black" if is_baseline else "none",
            linewidth=1 if is_baseline else 0,
            alpha=0.9,
            zorder=3,
        )

    # --- Plot Aesthetics ---
    min_val = min(plot_df[f"{metric}_baseline"].min(), plot_df[metric].min())
    max_val = max(plot_df[f"{metric}_baseline"].max(), plot_df[metric].max())

    # Set plot limits and scale
    if use_log_scale:
        plot_min, plot_max = min_val / 1.2, max_val * 1.2
        ax.set_xscale("log")
        ax.set_yscale("log")
        x_range = np.logspace(np.log10(plot_min), np.log10(plot_max), 100)
    else:
        padding = (max_val - min_val) * 0.05
        plot_min, plot_max = max(0, min_val - padding), max_val + padding
        x_range = np.linspace(plot_min, plot_max, 100)

    ax.set_xlim(plot_min, plot_max)
    ax.set_ylim(plot_min, plot_max)

    # Diagonal reference line and shaded performance regions
    ax.plot(
        [plot_min, plot_max],
        [plot_min, plot_max],
        "k-",
        alpha=0.5,
        linewidth=1,
        zorder=1,
    )
    ax.fill_between(x_range, x_range, plot_max, color="lightcoral", alpha=0.1, zorder=0)
    ax.fill_between(x_range, plot_min, x_range, color="lightgreen", alpha=0.1, zorder=0)

    # Region labels
    ax.text(
        0.05,
        0.95,
        "Worse",
        transform=ax.transAxes,
        fontsize=12,
        ha="left",
        va="top",
        bbox=dict(boxstyle="round,pad=0.3", fc="lightcoral", alpha=0.7),
    )
    ax.text(
        0.95,
        0.05,
        "Better",
        transform=ax.transAxes,
        fontsize=12,
        ha="right",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", fc="lightgreen", alpha=0.7),
    )

    # Annotate baseline points with circuit names if requested
    if annotate_baseline:
        ANNOTATION_OFFSET = 20
        baseline_points = plot_df[plot_df["compiler"] == baseline_compiler].iterrows()
        for i, (_, row) in enumerate(baseline_points):
            display_name = (
                row["benchmark_id"].replace("_basis_rz_rx_ry_cx", "").replace("_", " ")
            )
            ax.annotate(
                display_name,
                (row["x_jittered"], row["y_jittered"]),
                xytext=(
                    0,
                    ANNOTATION_OFFSET if i % 2 == 0 else -ANNOTATION_OFFSET,
                ),  # Alternate position
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=9,
                alpha=0.8,
                zorder=2,
                arrowprops=dict(arrowstyle="-", color="gray", lw=0.5, alpha=0.8),
                bbox=dict(
                    boxstyle="round,pad=0.1", fc="white", alpha=0.7, ec="gray", lw=0.3
                ),
            )

    ax.set_xlabel(xlabel, fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=16)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.5)


def plot_comparative_data(
    df: pd.DataFrame,
    baseline_compiler: str,
    out_path: Path,
    plot_configs: List[Dict],
    preprocess_func: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
    use_pdf: bool = False,
):
    """Generates a figure with one or more comparative scatter plots."""
    if use_pdf:
        plt.rcParams.update({"text.usetex": True, "font.family": "serif"})

    if baseline_compiler not in df["compiler"].unique():
        available = ", ".join(df["compiler"].unique())
        raise ValueError(
            f"Baseline compiler '{baseline_compiler}' not found. Available: {available}"
        )

    if preprocess_func:
        df = preprocess_func(df.copy())

    # Filter to benchmarks where the baseline compiler has results
    baseline_benchmarks = df[df["compiler"] == baseline_compiler][
        "benchmark_id"
    ].unique()
    plot_df = df[df["benchmark_id"].isin(baseline_benchmarks)]

    fig, axes = plt.subplots(
        1, len(plot_configs), figsize=(7 * len(plot_configs), 7), squeeze=False
    )

    for ax, config in zip(axes.flatten(), plot_configs):
        create_scatter_plot(ax, plot_df, baseline_compiler, **config)

    # Create a shared legend below the plots
    handles, labels = axes.flatten()[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Compiler",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=min(len(labels), 5),
        fontsize=12,
        title_fontsize=14,
        frameon=True,
        fancybox=True,
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])  # Adjust for legend
    print(f"✅ Saving plot to {out_path}")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_plot_generation(args: argparse.Namespace, benchmark_name: str, suite_name: str):
    """Loads data and generates plots for a specific benchmark suite."""
    db = SuiteResultsDatabase.from_root(args.root_dir, args.runner_name, suite_name)
    suite_results = db.from_uid(args.uid) if args.uid else db.get_latest()

    if suite_results is None:
        print(
            f"⚠️ No {benchmark_name} data found for runner '{args.runner_name}' and UID '{args.uid or 'latest'}'."
        )
        return

    # --- Define Plot Configurations ---
    if benchmark_name == "compilation":
        df = to_df_timing(suite_results)
        df["compile_time"] = df["compile_time_ms"] / 1000.0

        def preprocess(d: pd.DataFrame) -> pd.DataFrame:
            d["compiled_ratio"] = d["compiled_multiq_gates"] / d["raw_multiq_gates"]
            return d

        plot_configs = [
            {
                "metric": "compile_time",
                "title": f"Compile Time vs {args.baseline_compiler}",
                "xlabel": f"{args.baseline_compiler} Compile Time (s)",
                "ylabel": "Compiler Compile Time (s)",
                "use_log_scale": True,
                "annotate_baseline": True,
            },
            {
                "metric": "compiled_ratio",
                "title": f"Gate Count Ratio vs {args.baseline_compiler}",
                "xlabel": f"{args.baseline_compiler} Compiled/Raw Gate Ratio",
                "ylabel": "Compiler Ratio",
                "use_log_scale": False,
            },
        ]
        preprocess_func = preprocess

    elif benchmark_name == "simulation":
        df = to_df_simulation(suite_results)

        def preprocess(d: pd.DataFrame) -> pd.DataFrame:
            d["rel_err_ideal"] = calculate_abs_relative_error(
                d["compiled_ideal"], d["uncompiled_ideal"]
            )
            d["rel_err_noisy"] = calculate_abs_relative_error(
                d["compiled_noisy"], d["uncompiled_noisy"]
            )
            return d

        plot_configs = [
            {
                "metric": "rel_err_ideal",
                "title": f"Ideal Simulation Error vs {args.baseline_compiler}",
                "xlabel": f"{args.baseline_compiler} Abs. Relative Error",
                "ylabel": "Compiler Abs. Relative Error",
                "use_log_scale": False,
            },
            {
                "metric": "rel_err_noisy",
                "title": f"Noisy Simulation Error vs {args.baseline_compiler}",
                "xlabel": f"{args.baseline_compiler} Abs. Relative Error",
                "ylabel": "Compiler Abs. Relative Error",
                "use_log_scale": False,
            },
        ]
        preprocess_func = preprocess
    else:
        raise ValueError(f"Unknown benchmark name: {benchmark_name}")

    file_ext = "pdf" if args.pdf else "png"
    out_path = (
        args.root_dir
        / args.runner_name
        / f"latest_{benchmark_name}_comparative_{args.baseline_compiler}.{file_ext}"
    )

    try:
        plot_comparative_data(
            df,
            args.baseline_compiler,
            out_path,
            plot_configs,
            preprocess_func,
            args.pdf,
        )
    except ValueError as e:
        print(f"❌ Error generating {benchmark_name} plot: {e}", file=sys.stderr)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Plot comparative benchmark results against a baseline compiler."
    )
    parser.add_argument("root_dir", type=Path, help="Root directory of the benchmarks.")
    parser.add_argument("runner_name", type=str, help="Name of the runner.")
    parser.add_argument(
        "baseline_compiler",
        type=str,
        help="Name of the baseline compiler for comparison.",
    )
    parser.add_argument(
        "--uid",
        type=str,
        default=None,
        help="UID of the benchmark result to plot. If not given, uses the latest.",
    )
    parser.add_argument(
        "--plot",
        type=str,
        choices=["all", "compilation", "simulation"],
        default="all",
        help="Which plot(s) to generate.",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Export plots as PDF with LaTeX-ready fonts instead of PNG.",
    )
    args = parser.parse_args()

    if args.plot in ["all", "compilation"]:
        run_plot_generation(
            args, benchmark_name="compilation", suite_name="compilation_benchmarks"
        )

    if args.plot in ["all", "simulation"]:
        run_plot_generation(
            args, benchmark_name="simulation", suite_name="simulation_benchmarks"
        )


if __name__ == "__main__":
    main()
