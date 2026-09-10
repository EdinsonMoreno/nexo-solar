"""Simple in-memory logger for Nexo Solar.

This module provides a basic logger that stores log messages in memory
for display in the UI. For persistent logging, use LoggingService instead.

Note: This is a legacy module. New code should use LoggingService from
data_access.logging_service for comprehensive logging with file rotation.
"""

import datetime
from typing import List


class Logger:
    """Simple in-memory logger for UI display.

    Stores log messages with timestamps in memory. Useful for displaying
    recent activity in the UI without file I/O overhead.

    Attributes:
        logs: List of log entries with timestamps
    """

    def __init__(self) -> None:
        """Initialize the logger with empty log list."""
        self.logs: List[str] = []

    def log(self, msg: str) -> str:
        """Log a message with timestamp.

        Args:
            msg: Message to log

        Returns:
            str: Formatted log entry with timestamp
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {msg}"
        self.logs.append(entry)
        return entry

    def get_logs(self, n: int = 100) -> List[str]:
        """Get the most recent log entries.

        Args:
            n: Number of recent entries to return (default: 100)

        Returns:
            List[str]: List of most recent log entries
        """
        return self.logs[-n:]
