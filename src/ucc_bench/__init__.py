from importlib.metadata import version

# load to ensure we register all compilers and simulation items
import ucc_bench.compilers as _compilers
import ucc_bench.simulation as _simulation

__version__ = version("ucc_bench")
