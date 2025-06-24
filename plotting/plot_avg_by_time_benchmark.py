import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from pathlib import Path
from ucc_bench.results import SuiteResultsDatabase, to_df_timing_detailed


def annotate_and_adjust(
    ax,
    text,
    xy,
    color,
    previous_bboxes,
    offset=(0, 15),
    increment=5,
    fontsize=8,
    max_attempts=20,
):
    """
    Annotates the plot while dynamically adjusting the position to avoid overlaps. In-place operation.

    Parameters:
        ax (matplotlib.axes.Axes): The axis object to annotate.
        text (str): The annotation text.
        xy (tuple): The (x, y) coordinates for the annotation anchor point.
        color (str): The color for the text and arrow.
        previous_bboxes (list): A list to track previous annotation bounding boxes (in data coordinates).
        offset (tuple): The initial offset in points (x_offset, y_offset).
        increment (int): The vertical adjustment increment in points to resolve overlaps.
        fontsize (int): Font size of the annotation text.
        max_attempts (int): The maximum number of position adjustments to resolve overlaps.
        #TODO: Add margin parameter to adjust the bounding box size. Can be an issue when comparing dates which are strings
    Returns:
        None
    """
    # Create the annotation
    annotation = ax.annotate(
        text,
        xy,
        textcoords="offset points",
        xytext=offset,  # Default offset
        ha="center",
        fontsize=fontsize,
        color=color,
        rotation=0,
        arrowprops=dict(
            arrowstyle="->",
            color=color,
            lw=0.5,
            shrinkA=0,  # Shrink arrow length to avoid overlap
            shrinkB=5,
        ),
        bbox=dict(
            boxstyle="round,pad=0.2",
            edgecolor=color,
            facecolor="white",
            alpha=0.25,
        ),
    )

    # Force a renderer update to ensure bounding box accuracy
    ax.figure.canvas.draw()
    renderer = ax.figure.canvas.get_renderer()

    # Get the bounding box of the annotation in data coordinates
    bbox = annotation.get_tightbbox(renderer).transformed(ax.transData.inverted())
    # print(f"Initial annotation: '{text}' at {xy}, bbox: {bbox}", '\n')

    attempts = 0
    current_offset = offset[1]
    # Adjust position to avoid overlap
    while any(bbox.overlaps(prev_bbox) for prev_bbox in previous_bboxes):
        for prev_bbox in previous_bboxes:
            if bbox.overlaps(prev_bbox):
                # print(f"\nOverlapping with previous annotation:\n"
                #       f"  Previous bbox: {prev_bbox}\n"
                #       f"  Annotation text: '{annotation.get_text()}'\n")
                break
        # Increase vertical offset to move annotation upward
        current_offset += increment
        annotation.set_position((offset[0], current_offset))

        # Force the renderer to update after position adjustment
        ax.figure.canvas.draw()
        bbox = annotation.get_tightbbox(renderer).transformed(ax.transData.inverted())

        # Update the plot to show the new position
        ax.figure.canvas.flush_events()
        # Increment the attempt counter and check for max attempts
        attempts += 1
        if attempts >= max_attempts:
            print(
                f"Warning: Maximum adjustment attempts reached for annotation '{text}'."
            )
            break

    # Add the final bounding box to the list of previous bounding boxes
    previous_bboxes.append(bbox)


def adjust_axes_to_fit_labels(
    ax, x_scale=[1.0, 1.0], y_scale=[1.0, 1.0], x_log=False, y_log=False
):
    """
    Adjust the axes limits to ensure all labels and annotations fit within the view. In-place operation.

    Parameters:
    - ax: The Matplotlib axes object to adjust.
    - x_scale: A list with two values [left_factor, right_factor] to scale the x-axis.
    - y_scale: A list with two values [bottom_factor, top_factor] to scale the y-axis.
    - x_log: Set to True if the x-axis uses a logarithmic scale.
    - y_log: Set to True if the y-axis uses a logarithmic scale.
    """
    renderer = ax.figure.canvas.get_renderer()

    # Get the current axes limits
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    # Check the position of all annotations
    all_bboxes = [
        child.get_window_extent(renderer=renderer).transformed(ax.transData.inverted())
        for child in ax.get_children()
        if isinstance(child, matplotlib.text.Annotation)
    ]

    # Expand x-axis limits if annotations are off the edge
    for bbox in all_bboxes:
        if bbox.x0 < x_min:  # Left edge
            x_min = bbox.x0
        if bbox.x1 > x_max:  # Right edge
            x_max = bbox.x1

    # Expand y-axis limits if annotations are off the edge
    for bbox in all_bboxes:
        if bbox.y0 < y_min:  # Bottom edge
            y_min = bbox.y0
        if bbox.y1 > y_max:  # Top edge
            y_max = bbox.y1

    # Apply scaling factors for x-axis
    if x_log:
        x_min = x_min / x_scale[0]  # Left scaling
        x_max = x_max * x_scale[1]  # Right scaling
    else:
        x_range = x_max - x_min
        x_min -= (x_scale[0] - 1) * x_range  # Left scaling
        x_max += (x_scale[1] - 1) * x_range  # Right scaling

    # Apply scaling factors for y-axis
    if y_log:
        y_min = y_min / y_scale[0]  # Bottom scaling
        y_max = y_max * y_scale[1]  # Top scaling
    else:
        y_range = y_max - y_min
        y_min -= (y_scale[0] - 1) * y_range  # Bottom scaling
        y_max += (y_scale[1] - 1) * y_range  # Top scaling

    # Set the new axis limits
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)


def plot_and_annotate_metric(
    ax,
    sorted_compilers,
    avg_df,
    color_map,
    version_changes_df,
    metric,
    y_label,
    title,
    y_log=False,
    y_scale=None,
):
    previous_bboxes = []
    for compiler in sorted_compilers:
        comp_df = avg_df[avg_df["compiler"] == compiler]
        color = color_map[compiler]

        ax.plot(comp_df["uid_timestamp"], comp_df[metric], label=compiler, color=color)

        changes = version_changes_df[version_changes_df["compiler"] == compiler]
        for _, row in changes.iterrows():
            ax.scatter(
                row["uid_timestamp"],
                row[metric],
                color=color,
                s=30,
                zorder=3,
                label="_nolegend_",
            )
            annotate_and_adjust(
                ax=ax,
                text=row["compiler_version"],
                xy=(row["uid_timestamp"], row[metric]),
                color=color,
                previous_bboxes=previous_bboxes,
                offset=(0, 17),
                increment=2,
                max_attempts=20,
            )
    ax.set_ylabel(y_label)
    ax.set_title(title)
    if y_log:
        ax.set_yscale("log")
    adjust_axes_to_fit_labels(ax, y_scale=y_scale or [1.0, 1.2], y_log=y_log)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def patch_legacy_data(df, root_dir, runner_name):
    """
    Pull in data from old `ucc` runs (see results/README.md)
    """
    df_legacy = pd.read_csv(
        Path(root_dir)
        / runner_name
        / "compilation_benchmarks"
        / "legacy_timing_results.csv"
    )
    df_legacy["compile_time_ms"] = df_legacy["compile_time"] * 1000
    df_legacy["benchmark_id"] = df_legacy["circuit_name"]
    df_legacy["uid_timestamp"] = pd.to_datetime(df_legacy["date"], utc=True)
    df_legacy["target_device_id"] = None
    df_legacy = df_legacy[df.columns]
    df_legacy.sort_values("uid_timestamp", inplace=True)

    # Only pull new data after the transition cut-off
    cutoff = "2025-04-06"
    df = pd.concat([df_legacy, df[df["uid_timestamp"] > cutoff]], ignore_index=True)
    df.sort_values("uid_timestamp", inplace=True)
    return df


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Plot latest benchmark results.",
    )
    parser.add_argument("root_dir", type=str, help="Root directory of the benchmarks.")
    parser.add_argument("runner_name", type=str, help="Name of the runner.")
    args = parser.parse_args()

    root_dir = args.root_dir
    runner_name = args.runner_name

    timing_results_db = SuiteResultsDatabase.from_root(
        root_dir, runner_name, "compilation_benchmarks"
    )

    # Gets time ordered list of results when at least one compiler version
    # changed from the prior run.
    timing_results = timing_results_db.get_versions_changed()
    df = pd.concat((to_df_timing_detailed(d) for d in timing_results))

    # Bring in old data from original `ucc` runs
    df = patch_legacy_data(df, root_dir, runner_name)

    # Filter data to be after Dec 2024 when dedicated runner was created
    df = df[df["uid_timestamp"] > "2024-12-16"]

    # Add calculated columns
    df["compile_time"] = df["compile_time_ms"] / 1000
    df["compiled_ratio"] = df["compiled_multiq_gates"] / df["raw_multiq_gates"]

    # Calculate average compile time and compiled ratio
    avg_df = (
        df.groupby(["uid_timestamp", "compiler"])
        .agg(
            {
                "compile_time": "mean",
                "compiled_ratio": "mean",
                "compiler_version": "first",
            }
        )
        .reset_index()
    )

    # Detect version changes that we will annotate
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
                    "compile_time": row["compile_time"],
                    "compiled_ratio": row["compiled_ratio"],
                }
            )
            last_versions[compiler] = version

    version_changes_df = pd.DataFrame(version_changes)

    # Use a consistent color map for both plots
    sorted_compilers = sorted(avg_df["compiler"].unique())
    colors = plt.get_cmap("tab10", len(sorted_compilers))
    color_map = {compiler: colors(i) for i, compiler in enumerate(sorted_compilers)}

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(8, 8),
        sharex=True,
    )

    plot_and_annotate_metric(
        ax1,
        sorted_compilers,
        avg_df,
        color_map,
        version_changes_df,
        metric="compiled_ratio",
        y_label="Compiled Ratio",
        title="Average Compiled Ratio by Compiler",
        y_log=False,
        y_scale=[1.1, 1.3],
    )

    plot_and_annotate_metric(
        ax2,
        sorted_compilers,
        avg_df,
        color_map,
        version_changes_df,
        metric="compile_time",
        y_label="Compile Time (s, log scale)",
        title="Average Compile Time by Compiler",
        y_log=True,
        y_scale=[1.0, 1.9],
    )

    # Create a single legend for both plots
    fig.legend(
        sorted_compilers,  # Use the sorted compiler names for the legend
        loc="lower center",  # Place legend at the bottom center of the figure
        bbox_to_anchor=(0.5, 0.5),  # Position between the two plots
        ncol=4,  # Arrange legend items in 4 columns
        borderaxespad=0.0,
    )

    filename = Path(root_dir) / runner_name / "avg_compiler_benchmarks_over_time.png"
    print(f"Saving plot to {filename}")
    fig.savefig(filename, bbox_inches="tight", dpi=150)


if __name__ == "__main__":
    main()
