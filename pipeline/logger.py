"""Minimal pipeline logger used during integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(slots=True)
class LogEntry:
    event: str
    payload: Dict[str, object]


class PipelineLogger:
    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self.entries: List[LogEntry] = []

    async def log_start(self, context) -> None:  # noqa: ANN001
        self.entries.append(LogEntry("pipeline_start", {"input": context.input_text}))

    async def log_agent_step(self, agent_name: str, context, result) -> None:  # noqa: ANN001
        self.entries.append(LogEntry("agent_step", {"agent": agent_name, "result": result}))

    async def log_complete(self, context, response) -> None:  # noqa: ANN001
        self.entries.append(LogEntry("pipeline_complete", {"success": response["success"]}))
