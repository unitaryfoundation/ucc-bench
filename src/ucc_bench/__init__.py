from importlib.metadata import version

# Load to ensure we register all compilers and simulation functions in register
from . import simulation as simulation
from . import compilers as compilers
from . import target_devices as target_devices

__version__ = version("ucc_bench")
