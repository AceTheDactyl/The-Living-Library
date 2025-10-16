"""
Collaboration server placeholder.

The final implementation will host an async WebSocket API that fronts
Redis for presence tracking and PostgreSQL for durable session logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from fastapi import FastAPI

app = FastAPI(title="Living Library Collaboration Server")


@dataclass(slots=True)
class CollaborationEvent:
    """Lightweight record describing a collaboration event."""

    type: str
    user: Optional[str]
    payload: dict


class CollaborationServer:
    """
    Minimal stub for the WebSocket collaboration service.

    Methods currently log requested actions so that integration tests can
    be written ahead of the full async transport implementation.
    """

    def __init__(self) -> None:
        self._history: list[CollaborationEvent] = []

    @property
    def history(self) -> Iterable[CollaborationEvent]:
        """Return a snapshot of recorded events."""
        return tuple(self._history)

    def record(self, event_type: str, user: Optional[str], payload: dict) -> None:
        """Append an event to the in-memory history log."""
        self._history.append(CollaborationEvent(event_type, user, payload))

    def clear(self) -> None:
        """Reset the in-memory history."""
        self._history.clear()


@app.get("/health/live")
def live() -> dict[str, str]:
    """Basic liveness endpoint for the development container."""
    return {"status": "ok"}
