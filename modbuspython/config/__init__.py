"""Configuration management package for SolarSense SCADA.

This package handles externalized configuration, validation, and schema management.
"""

from .config_manager import ConfigurationManager
from . import validators

__all__ = ["ConfigurationManager", "validators"]
