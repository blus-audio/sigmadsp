"""A module that helps with determining the correct package version."""
from . import _version

__version__ = _version.get_versions()["version"]
