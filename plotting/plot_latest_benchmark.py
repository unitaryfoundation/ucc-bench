import argparse
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
from ucc_bench.results import SuiteResultsDatabase, to_df_timing, to_df_simulation

from shared import calculate_abs_relative_error, get_compiler_colormap

BAR_WIDTH = 0.2


def generate_plot(
    df: pd.DataFrame, plot_configs: list[dict], latest_date: str, out_path: Path
):
    """Generic plotting function to create bar charts for benchmark data."""
    circuit_names = sorted(df["benchmark_id"].unique())
    x_positions = range(len(circuit_names))
    circuit_name_to_index = {name: i for i, name in enumerate(circuit_names)}
    color_map = get_compiler_colormap()

    num_plots = len(plot_configs)
    fig, axes = plt.subplots(1, num_plots, figsize=(7 * num_plots, 7), squeeze=False)
    axes = axes.flatten()

    compilers = df["compiler"].unique()
    for i, compiler_name in enumerate(compilers):
        grp = df[df["compiler"] == compiler_name]
        grp_indices = grp["benchmark_id"].map(circuit_name_to_index)
        bar_positions = [idx + i * BAR_WIDTH for idx in grp_indices]

        for ax, config in zip(axes, plot_configs):
            ax.bar(
                bar_positions,
                grp[config["y_col"]],
                width=BAR_WIDTH,
                label=compiler_name,
                color=color_map.get(compiler_name),
            )

    for ax, config in zip(axes, plot_configs):
        ax.set_title(f"{config['title']} (Date: {latest_date})")
        ax.set_xlabel("Circuit Name")
        ax.set_ylabel(config["ylabel"])
        ax.set_xticks(x_positions)
        ax.set_xticklabels(circuit_names, rotation=75, ha="right")
        ax.set_yscale("log")
        ax.legend(title="Compiler")

    plt.tight_layout()
    print(f"Saving plot to {out_path}")
    fig.savefig(out_path)
    plt.close(fig)


def plot_compilation(df: pd.DataFrame, latest_date: str, out_path: Path):
    """Generates and saves plots for compilation benchmark data."""
    plot_configs = [
        {
            "y_col": "compile_time",
            "title": "Compiler Performance",
            "ylabel": "Compile Time (s)",
        },
        {
            "y_col": "compiled_multiq_gates",
            "title": "Gate Counts",
            "ylabel": "Compiled Gate Count",
        },
    ]
    generate_plot(df, plot_configs, latest_date, out_path)


def plot_simulation(df: pd.DataFrame, latest_date: str, out_path: Path):
    """Generates and saves plots for simulation benchmark data."""
    df_sim = df.copy()
    df_sim["rel_err_ideal"] = calculate_abs_relative_error(
        df_sim["compiled_ideal"], df_sim["uncompiled_ideal"]
    )
    df_sim["rel_err_noisy"] = calculate_abs_relative_error(
        df_sim["compiled_noisy"], df_sim["uncompiled_noisy"]
    )

    plot_configs = [
        {
            "y_col": "rel_err_ideal",
            "title": "Observable Error (Noiseless Sim)",
            "ylabel": "Absolute Relative Error",
        },
        {
            "y_col": "rel_err_noisy",
            "title": "Observable Error (Noisy Sim)",
            "ylabel": "Absolute Relative Error",
        },
    ]
    generate_plot(df_sim, plot_configs, latest_date, out_path)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Plot latest benchmark results.")
    parser.add_argument("root_dir", type=Path, help="Root directory of the benchmarks.")
    parser.add_argument("runner_name", type=str, help="Name of the runner.")
    parser.add_argument(
        "--uid",
        type=str,
        default=None,
        help="UID of the benchmark result to plot. If provided, uses this UID instead of the latest.",
    )
    parser.add_argument(
        "--plot",
        type=str,
        choices=["all", "compilation", "simulation"],
        default="all",
        help="Which plot(s) to generate.",
    )
    args = parser.parse_args()

    # --- Plot Compilation Benchmarks ---
    if args.plot in ["all", "compilation"]:
        db = SuiteResultsDatabase.from_root(
            args.root_dir, args.runner_name, "compilation_benchmarks"
        )

        suite_results = db.from_uid(args.uid) if args.uid else db.get_latest()
        if suite_results is None:
            print(f"No compilation data found for UID {args.uid}")
            sys.exit(1)

        latest_date = suite_results.metadata.uid_timestamp.strftime("%Y-%m-%d")

        df = to_df_timing(suite_results)
        if "compile_time_ms" in df.columns:
            df["compile_time"] = df["compile_time_ms"] / 1000.0

        out_path = (
            args.root_dir
            / args.runner_name
            / "latest_compiler_benchmarks_by_circuit.png"
        )
        plot_compilation(df, latest_date, out_path)

    # --- Plot Simulation Benchmarks ---
    if args.plot in ["all", "simulation"]:
        db = SuiteResultsDatabase.from_root(
            args.root_dir, args.runner_name, "simulation_benchmarks"
        )

        suite_results = db.from_uid(args.uid) if args.uid else db.get_latest()
        if suite_results is None:
            print(f"No simulation data found for UID {args.uid}")
            sys.exit(1)

        latest_date = suite_results.metadata.uid_timestamp.strftime("%Y-%m-%d")

        df = to_df_simulation(suite_results)

        out_path = (
            args.root_dir
            / args.runner_name
            / "latest_simulation_benchmarks_by_circuit.png"
        )
        plot_simulation(df, latest_date, out_path)


if __name__ == "__main__":
    main()
