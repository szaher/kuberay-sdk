"""Log level detection and source label formatting.

Used by display backends to colorize log output by level.
"""

from __future__ import annotations

import re

_LOG_LEVEL_RE = re.compile(r"\b(CRITICAL|ERROR|WARNING|WARN|INFO|DEBUG)\b", re.IGNORECASE)


def parse_log_level(line: str) -> str:
    """Detect the log level from a log line.

    Args:
        line: A single log line string.

    Returns:
        Uppercase log level string (e.g., ``"ERROR"``, ``"INFO"``).
        Defaults to ``"INFO"`` if no level is detected.
    """
    match = _LOG_LEVEL_RE.search(line)
    if match:
        level = match.group(1).upper()
        if level == "WARN":
            return "WARNING"
        return level
    return "INFO"


def format_source_label(source: str) -> str:
    """Format a source identifier as a display label.

    Args:
        source: Source identifier (e.g., ``"head"``, ``"worker-0"``).

    Returns:
        Formatted label string.
    """
    return f"[{source}]"
