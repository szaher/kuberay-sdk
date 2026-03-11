"""State color scheme for consistent resource state color coding.

Maps resource states to color names used across all display backends.
"""

from __future__ import annotations

from types import MappingProxyType

# Frozen mapping of resource states to color names.
# Color names are abstract — each backend translates to its rendering system.
STATE_COLORS: MappingProxyType[str, str] = MappingProxyType(
    {
        # Success states — green
        "RUNNING": "green",
        "READY": "green",
        "SUCCEEDED": "green",
        "COMPLETE": "green",
        # Transitional states — yellow
        "CREATING": "yellow",
        "PENDING": "yellow",
        "SCALING": "yellow",
        "INITIALIZING": "yellow",
        "SUBMITTING": "yellow",
        # Failure states — red
        "FAILED": "red",
        "ERROR": "red",
        "CRASHED": "red",
        "TIMEOUT": "red",
        "UNKNOWN": "red",
    }
)

# Default color for states not in the mapping.
_DEFAULT_COLOR = "yellow"


def get_state_color(state: str) -> str:
    """Get the display color for a resource state.

    Args:
        state: The resource state string (case-sensitive).

    Returns:
        A color name string (``"green"``, ``"yellow"``, or ``"red"``).
        Unknown states default to ``"yellow"``.
    """
    return STATE_COLORS.get(state.upper(), _DEFAULT_COLOR)
