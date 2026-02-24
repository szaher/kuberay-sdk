"""ProgressStatus model for wait operation callbacks (US2)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProgressStatus(BaseModel):
    """Status update passed to progress callbacks during wait operations.

    Example:
        >>> status = ProgressStatus(state="CREATING", elapsed_seconds=5.0, message="Waiting for head pod")
        >>> print(status.state, status.elapsed_seconds)
    """

    state: str
    elapsed_seconds: float = Field(ge=0)
    message: str = ""
    metadata: dict[str, Any] = {}
