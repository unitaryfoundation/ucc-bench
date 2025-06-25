import matplotlib.pyplot as plt
from ucc_bench.registry import register
import pandas as pd


def calculate_abs_relative_error(
    series1: pd.Series, series2: pd.Series, eps: float = 1e-8
) -> pd.Series:
    """Calculates the absolute relative error between two series."""
    return ((series1 - series2) / (series2 + eps)).abs()


def get_compiler_colormap() -> dict[str, tuple]:
    """Returns a dictionary mapping compiler names to unique colors."""
    compilers = register.get_compilers()
    colormap = plt.get_cmap("tab10", len(compilers))
    return {compiler: colormap(i) for i, compiler in enumerate(compilers)}
