from importlib.metadata import version

# Load to ensure we register all compilers and simulation items
from ucc_bench import simulation as simulation
from ucc_bench import compilers as compilers

__version__ = version("ucc_bench")
