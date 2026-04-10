# Package marker for src
from importlib.metadata import version, PackageNotFoundError

__all__ = ["utils", "main", "__version__"]

try:
    __version__ = version("rabbit-crm")
except PackageNotFoundError:
    # Package is not installed, use a fallback version
    __version__ = "0.0.0+dev"
