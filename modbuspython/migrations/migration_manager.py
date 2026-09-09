"""Database migration management system.

This module provides a robust migration system for managing database schema
changes with version tracking, apply/rollback capabilities, and comprehensive logging.

Requirements validated: 13.2, 13.3, 13.4
"""

import os
import importlib
import importlib.util
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

from modbuspython.data_access.database_manager import DatabaseManager, SchemaVersionRepository
from modbuspython.exceptions import MigrationError
from modbuspython.data_access.logging_service import LoggingService

logger = LoggingService()


class MigrationStatus(Enum):
    """Status of a migration."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationInfo:
    """Information about a migration.

    Attributes:
        version: Migration version number
        name: Human-readable migration name
        description: Detailed description of changes
        applied_at: When migration was applied (None if not applied)
        status: Current migration status
        file_path: Path to migration file
    """

    version: int
    name: str
    description: str
    applied_at: Optional[str] = None
    status: MigrationStatus = MigrationStatus.PENDING
    file_path: Optional[str] = None


@dataclass
class MigrationModule:
    """Wrapper for a migration module with upgrade/downgrade functions.

    Each migration module must implement:
    - upgrade(conn): Apply the migration
    - downgrade(conn): Reverse the migration

    Attributes:
        version: Migration version number
        name: Migration name
        description: Migration description
        upgrade: Function to apply migration
        downgrade: Function to reverse migration
    """

    version: int
    name: str
    description: str
    upgrade: Callable
    downgrade: Callable


class MigrationManager:
    """Manages database schema migrations with version tracking.

    Provides methods to discover, apply, and rollback database migrations.
    Migrations are stored in the migrations/versions/ directory as Python
    modules with upgrade() and downgrade() functions.

    Migration files should be named: v{version}_{description}.py
    Example: v1_initial_schema.py, v2_add_metrics_table.py

    Requirements validated: 13.2, 13.3, 13.4
    """

    def __init__(self, db_path: str, migrations_dir: Optional[str] = None):
        """Initialize migration manager.

        Args:
            db_path: Path to SQLite database file
            migrations_dir: Path to migrations directory (defaults to project migrations/)
        """
        self.db_path = db_path
        self.schema_repo = SchemaVersionRepository(db_path)

        if migrations_dir is None:
            # Default to modbuspython/migrations/versions/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            migrations_dir = os.path.join(base_dir, "migrations", "versions")

        self.migrations_dir = migrations_dir
        self._migration_cache: Dict[int, MigrationModule] = {}

        logger.info(
            "Initialized MigrationManager",
            db_path=db_path,
            migrations_dir=migrations_dir,
        )

    def discover_migrations(self) -> List[MigrationModule]:
        """Discover all available migration modules.

        Scans the migrations directory for Python files matching the naming
        convention v{version}_{description}.py and loads them as modules.

        Returns:
            List of MigrationModule objects sorted by version number

        Raises:
            MigrationError: If migration discovery fails
        """
        if not os.path.exists(self.migrations_dir):
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []

        migrations = []

        try:
            for filename in sorted(os.listdir(self.migrations_dir)):
                if not filename.endswith(".py") or filename.startswith("__"):
                    continue

                if not filename.startswith("v"):
                    logger.debug(f"Skipping non-migration file: {filename}")
                    continue

                module = self._load_migration_module(filename)
                if module:
                    migrations.append(module)

            # Sort by version number
            migrations.sort(key=lambda m: m.version)
            logger.info(f"Discovered {len(migrations)} migrations")
            return migrations

        except Exception as e:
            error_msg = f"Failed to discover migrations in {self.migrations_dir}"
            logger.error(error_msg, exc_info=True, error=str(e))
            raise MigrationError(error_msg, details={"migrations_dir": self.migrations_dir, "original_error": str(e)})

    def _load_migration_module(self, filename: str) -> Optional[MigrationModule]:
        """Load a single migration module from file.

        Args:
            filename: Migration filename (e.g., v1_initial_schema.py)

        Returns:
            MigrationModule if loaded successfully, None otherwise

        Raises:
            MigrationError: If module loading fails
        """
        try:
            # Parse version from filename (v1_initial_schema.py -> 1)
            version_str = filename.split("_")[0][1:]  # Remove 'v' prefix
            version = int(version_str)

            # Parse description from filename
            description = filename.replace(f"v{version}_", "").replace(".py", "").replace("_", " ")

            # Load module dynamically
            filepath = os.path.join(self.migrations_dir, filename)
            spec = importlib.util.spec_from_file_location(f"migration_{version}", filepath)
            if spec is None or spec.loader is None:
                raise MigrationError(f"Could not load spec for {filename}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Validate required functions
            if not hasattr(module, "upgrade"):
                raise MigrationError(f"Migration {filename} missing upgrade() function")
            if not hasattr(module, "downgrade"):
                raise MigrationError(f"Migration {filename} missing downgrade() function")

            migration_module = MigrationModule(
                version=version,
                name=description.title(),
                description=getattr(module, "DESCRIPTION", description),
                upgrade=module.upgrade,
                downgrade=module.downgrade,
            )

            self._migration_cache[version] = migration_module
            logger.debug(f"Loaded migration v{version}: {description}")
            return migration_module

        except MigrationError:
            raise
        except Exception as e:
            error_msg = f"Failed to load migration module {filename}"
            logger.error(error_msg, exc_info=True, filename=filename, error=str(e))
            raise MigrationError(error_msg, details={"filename": filename, "original_error": str(e)})

    def get_pending_migrations(self) -> List[MigrationModule]:
        """Get list of migrations that haven't been applied yet.

        Compares available migrations against current schema version.

        Returns:
            List of pending MigrationModule objects sorted by version

        Raises:
            MigrationError: If migration discovery or version check fails
        """
        try:
            current_version = self.schema_repo.get_schema_version()
            all_migrations = self.discover_migrations()

            pending = [m for m in all_migrations if m.version > current_version]
            logger.info(f"Found {len(pending)} pending migrations (current version: {current_version})")
            return pending

        except Exception as e:
            error_msg = "Failed to get pending migrations"
            logger.error(error_msg, exc_info=True, error=str(e))
            raise MigrationError(error_msg, details={"original_error": str(e)})

    def get_applied_migrations(self) -> List[MigrationInfo]:
        """Get list of all migrations with their application status.

        Returns:
            List of MigrationInfo objects for all discovered migrations
        """
        try:
            current_version = self.schema_repo.get_schema_version()
            all_migrations = self.discover_migrations()

            applied = []
            for migration in all_migrations:
                if migration.version <= current_version:
                    info = MigrationInfo(
                        version=migration.version,
                        name=migration.name,
                        description=migration.description,
                        status=MigrationStatus.APPLIED,
                        file_path=os.path.join(self.migrations_dir, f"v{migration.version}_*.py"),
                    )
                    applied.append(info)
                else:
                    info = MigrationInfo(
                        version=migration.version,
                        name=migration.name,
                        description=migration.description,
                        status=MigrationStatus.PENDING,
                        file_path=os.path.join(self.migrations_dir, f"v{migration.version}_*.py"),
                    )
                    applied.append(info)

            return applied

        except Exception as e:
            logger.error("Failed to get applied migrations", exc_info=True, error=str(e))
            return []

    def apply_migration(self, migration: MigrationModule) -> bool:
        """Apply a single migration to the database.

        Executes the migration's upgrade() function within a transaction.
        Updates schema version on success, rolls back on failure.

        Args:
            migration: MigrationModule to apply

        Returns:
            True if migration applied successfully, False otherwise

        Raises:
            MigrationError: If migration application fails
        """
        logger.info(f"Applying migration v{migration.version}: {migration.name}")

        try:
            with DatabaseManager.get_connection(self.db_path, auto_commit=False) as conn:
                # Execute migration
                try:
                    migration.upgrade(conn)
                    conn.commit()
                    logger.info(f"Migration v{migration.version} upgrade executed successfully")
                except Exception as e:
                    conn.rollback()
                    error_msg = f"Migration v{migration.version} upgrade failed"
                    logger.error(error_msg, exc_info=True, version=migration.version, error=str(e))
                    raise MigrationError(
                        error_msg,
                        details={
                            "version": migration.version,
                            "name": migration.name,
                            "original_error": str(e),
                        },
                    )

            # Update schema version
            self.schema_repo.set_schema_version(
                migration.version,
                description=migration.description,
            )

            logger.info(f"Migration v{migration.version} applied successfully")
            return True

        except MigrationError:
            raise
        except Exception as e:
            error_msg = f"Failed to apply migration v{migration.version}"
            logger.error(error_msg, exc_info=True, version=migration.version, error=str(e))
            raise MigrationError(error_msg, details={"version": migration.version, "original_error": str(e)})

    def apply_all_pending(self) -> List[int]:
        """Apply all pending migrations in order.

        Discovers and applies all migrations that haven't been applied yet,
        in ascending version order.

        Returns:
            List of applied migration version numbers

        Raises:
            MigrationError: If any migration fails (stops on first failure)
        """
        pending = self.get_pending_migrations()
        if not pending:
            logger.info("No pending migrations to apply")
            return []

        applied_versions = []

        for migration in pending:
            try:
                self.apply_migration(migration)
                applied_versions.append(migration.version)
            except MigrationError as e:
                logger.error(f"Migration sequence stopped at v{migration.version}: {e}")
                raise

        logger.info(f"Applied {len(applied_versions)} migrations: {applied_versions}")
        return applied_versions

    def rollback_migration(self, migration: MigrationModule) -> bool:
        """Rollback a single migration.

        Executes the migration's downgrade() function within a transaction.
        Updates schema version to previous version on success.

        Args:
            migration: MigrationModule to rollback

        Returns:
            True if migration rolled back successfully, False otherwise

        Raises:
            MigrationError: If rollback fails
        """
        logger.info(f"Rolling back migration v{migration.version}: {migration.name}")

        current_version = self.schema_repo.get_schema_version()
        if migration.version != current_version:
            error_msg = (
                f"Cannot rollback v{migration.version}: current version is v{current_version}. "
                f"Can only rollback the latest applied migration."
            )
            logger.error(error_msg, current_version=current_version, target_version=migration.version)
            raise MigrationError(
                error_msg,
                details={
                    "current_version": current_version,
                    "target_version": migration.version,
                },
            )

        try:
            with DatabaseManager.get_connection(self.db_path, auto_commit=False) as conn:
                # Execute rollback
                try:
                    migration.downgrade(conn)
                    conn.commit()
                    logger.info(f"Migration v{migration.version} downgrade executed successfully")
                except Exception as e:
                    conn.rollback()
                    error_msg = f"Migration v{migration.version} rollback failed"
                    logger.error(error_msg, exc_info=True, version=migration.version, error=str(e))
                    raise MigrationError(
                        error_msg,
                        details={
                            "version": migration.version,
                            "name": migration.name,
                            "original_error": str(e),
                        },
                    )

            # Set schema version to previous migration
            new_version = migration.version - 1
            self.schema_repo.set_schema_version(
                new_version,
                description=f"Rolled back from v{migration.version}",
            )

            logger.info(f"Migration v{migration.version} rolled back to v{new_version}")
            return True

        except MigrationError:
            raise
        except Exception as e:
            error_msg = f"Failed to rollback migration v{migration.version}"
            logger.error(error_msg, exc_info=True, version=migration.version, error=str(e))
            raise MigrationError(error_msg, details={"version": migration.version, "original_error": str(e)})

    def rollback_to_version(self, target_version: int) -> List[int]:
        """Rollback migrations to reach a target version.

        Rolls back migrations one by one from current version down to target version.

        Args:
            target_version: Target schema version to reach

        Returns:
            List of rolled back migration version numbers (in reverse order)

        Raises:
            MigrationError: If any rollback fails
        """
        current_version = self.schema_repo.get_schema_version()

        if target_version >= current_version:
            logger.warning(f"Target version {target_version} >= current version {current_version}, nothing to rollback")
            return []

        all_migrations = self.discover_migrations()
        rolled_back_versions = []

        # Rollback from current down to target + 1
        for version in range(current_version, target_version, -1):
            migration = next((m for m in all_migrations if m.version == version), None)
            if migration is None:
                error_msg = f"Cannot find migration v{version} for rollback"
                logger.error(error_msg)
                raise MigrationError(error_msg, details={"version": version})

            try:
                self.rollback_migration(migration)
                rolled_back_versions.append(version)
            except MigrationError as e:
                logger.error(f"Rollback sequence stopped at v{version}: {e}")
                raise

        logger.info(f"Rolled back {len(rolled_back_versions)} migrations: {rolled_back_versions}")
        return rolled_back_versions

    def migrate_to_latest(self) -> List[int]:
        """Apply all pending migrations to reach latest schema version.

        Convenience method that applies all pending migrations in order.

        Returns:
            List of applied migration version numbers
        """
        return self.apply_all_pending()

    def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration status information.

        Returns:
            Dictionary with current version, pending count, and migration list
        """
        try:
            current_version = self.schema_repo.get_schema_version()
            all_migrations = self.discover_migrations()
            pending = [m for m in all_migrations if m.version > current_version]

            return {
                "current_version": current_version,
                "latest_version": all_migrations[-1].version if all_migrations else 0,
                "total_migrations": len(all_migrations),
                "pending_count": len(pending),
                "applied_count": len(all_migrations) - len(pending),
                "migrations": [
                    {
                        "version": m.version,
                        "name": m.name,
                        "description": m.description,
                        "status": "applied" if m.version <= current_version else "pending",
                    }
                    for m in all_migrations
                ],
            }

        except Exception as e:
            logger.error("Failed to get migration status", exc_info=True, error=str(e))
            return {
                "current_version": 0,
                "latest_version": 0,
                "total_migrations": 0,
                "pending_count": 0,
                "applied_count": 0,
                "migrations": [],
                "error": str(e),
            }
