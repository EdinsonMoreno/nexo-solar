"""Repository classes for data access."""

from .base_repository import BaseRepository
from .irradiance_repository import IrradianceRepository
from .schema_version_repository import SchemaVersionRepository

__all__ = ["BaseRepository", "IrradianceRepository", "SchemaVersionRepository"]
