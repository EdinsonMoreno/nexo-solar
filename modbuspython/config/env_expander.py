"""Environment variable expansion for configuration values.

Supports ${VAR_NAME} syntax in configuration files and loads
environment variables from .env files via python-dotenv.
"""

import os
import re
from typing import Any, List
from pathlib import Path
import logging
from dotenv import load_dotenv


class EnvExpander:
    """Handles environment variable loading and expansion.

    Supports ${VAR_NAME} syntax in configuration values and loads
    variables from .env files using python-dotenv.
    """

    _ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

    def __init__(self) -> None:
        """Initialize env expander."""
        self._logger = logging.getLogger(__name__)
        self._env_vars_loaded = False
        self._load_env_variables()

    def _load_env_variables(self) -> None:
        """Load environment variables from .env file if it exists.

        Uses python-dotenv to load variables from .env file in project root.
        Does not override existing environment variables.
        """
        try:
            env_paths = [Path(".env"), Path(__file__).parent.parent.parent / ".env"]
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(dotenv_path=str(env_path), override=False)
                    self._env_vars_loaded = True
                    self._logger.info(f"Loaded environment variables from {env_path}")
                    break
        except Exception as e:
            self._logger.warning(f"Failed to load .env file: {e}")
            self._env_vars_loaded = False

    def expand(self, value: Any) -> Any:
        """Recursively expand environment variables in configuration values.

        Supports ${VAR_NAME} syntax. If the variable is not set, the original
        string is kept unchanged.

        Args:
            value: Configuration value (dict, list, or primitive)

        Returns:
            Value with environment variables expanded
        """
        if isinstance(value, dict):
            return {k: self.expand(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.expand(item) for item in value]
        elif isinstance(value, str):
            return self._ENV_VAR_PATTERN.sub(self._replace_env_var, value)
        return value

    def _replace_env_var(self, match: re.Match[str]) -> str:
        """Replace a single environment variable reference with its value.

        Args:
            match: Regex match object for ${VAR_NAME}

        Returns:
            Environment variable value or original reference if not set
        """
        var_name = match.group(1)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            self._logger.debug(f"Expanded environment variable: {var_name}")
            return env_value
        self._logger.warning(f"Environment variable not set: {var_name}")
        return str(match.group(0))

    def find_missing_vars(self, config: Any) -> List[str]:
        """Find unexpanded environment variable references in config.

        Args:
            config: Configuration structure to check

        Returns:
            List of missing required environment variable names
        """
        missing: List[str] = []
        self._check_unexpanded(config, missing, "")
        return missing

    def _check_unexpanded(self, value: Any, missing: List[str], path: str) -> None:
        """Recursively check for unexpanded environment variable references.

        Args:
            value: Configuration value to check
            missing: List to append missing variable names to
            path: Current path in config (for logging)
        """
        if isinstance(value, dict):
            for k, v in value.items():
                self._check_unexpanded(v, missing, f"{path}.{k}" if path else k)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                self._check_unexpanded(item, missing, f"{path}[{i}]")
        elif isinstance(value, str):
            matches = self._ENV_VAR_PATTERN.findall(value)
            for var_name in matches:
                if var_name not in missing:
                    missing.append(var_name)

    @property
    def env_vars_loaded(self) -> bool:
        """Whether environment variables were successfully loaded."""
        return self._env_vars_loaded
