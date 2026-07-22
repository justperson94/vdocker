"""vdocker — Visualize Docker objects and their relationships."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("vdocker")
except PackageNotFoundError:
    __version__ = "0+unknown"
