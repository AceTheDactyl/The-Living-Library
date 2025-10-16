"""
Workspace manager scaffold for The Living Library.

The fully featured version will extend Kira Prime's multi-workspace
capabilities and tie in collaboration sessions plus shared resources.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable


@dataclass(slots=True)
class WorkspaceRecord:
    """Minimal description of a workspace."""

    workspace_id: str
    name: str
    path: Path


class WorkspaceManager:
    """Local registry for Living Library workspaces."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = Path(root or ".").resolve()
        self._workspaces: Dict[str, WorkspaceRecord] = {}

    def register(self, workspace_id: str, name: str | None = None) -> WorkspaceRecord:
        """Register a workspace with a minimal state footprint."""
        record = WorkspaceRecord(
            workspace_id=workspace_id,
            name=name or workspace_id,
            path=self._workspace_root(workspace_id),
        )
        self._ensure_structure(record)
        self._workspaces[workspace_id] = record
        return record

    def get(self, workspace_id: str) -> WorkspaceRecord:
        """Return an existing workspace, registering it on demand."""
        if workspace_id in self._workspaces:
            return self._workspaces[workspace_id]
        return self.register(workspace_id)

    def list_workspaces(self) -> Iterable[WorkspaceRecord]:
        """Return the currently registered workspaces."""
        return tuple(self._workspaces.values())

    # Internal helpers -------------------------------------------------

    def _workspace_root(self, workspace_id: str) -> Path:
        return self._root / "workspaces" / workspace_id

    def _ensure_structure(self, record: WorkspaceRecord) -> None:
        """Create the standard directory layout for a workspace."""
        record.path.mkdir(parents=True, exist_ok=True)
        for folder in ("logs", "state", "outputs", "collab"):
            (record.path / folder).mkdir(parents=True, exist_ok=True)
