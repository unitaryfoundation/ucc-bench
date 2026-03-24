from ucc_bench.registry import register
import pandas as pd
import seaborn as sns


def calculate_abs_relative_error(
    series1: pd.Series, series2: pd.Series, eps: float = 1e-8
) -> pd.Series:
    """Calculates the absolute relative error between two series."""
    return ((series1 - series2) / (series2 + eps)).abs()


def get_compiler_colormap(extra_compilers: list[str] | None = None) -> dict[str, tuple]:
    """Returns a dictionary mapping compiler names to unique colors.

    Includes all currently registered compilers plus any additional names
    passed via *extra_compilers* (e.g. retired compilers found in historical
    result data).
    """
    compilers = sorted(set(register.get_compilers()) | set(extra_compilers or []))
    colormap = sns.color_palette("colorblind", n_colors=max(len(compilers), 1))
    return {compiler: colormap[i] for i, compiler in enumerate(compilers)}
