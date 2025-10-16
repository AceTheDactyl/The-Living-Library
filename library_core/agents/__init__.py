"""Wrappers around the bundled Kira Prime agents."""

from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from typing import Any, Dict
import json

from library_core.agents.base import BaseAgent
from workspace.manager import WorkspaceManager

KIRA_ROOT = Path(__file__).resolve().parents[1] / "kira-prime"
if KIRA_ROOT.exists():
    if str(KIRA_ROOT) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(KIRA_ROOT))
    GardenImpl = import_module("agents.garden.garden_agent").GardenAgent
    EchoImpl = import_module("agents.echo.echo_agent").EchoAgent
    LimnusImpl = import_module("agents.limnus.limnus_agent").LimnusAgent
    KiraImpl = import_module("agents.kira.kira_agent").KiraAgent
else:  # pragma: no cover - fallback for tests without submodule
    class _Stub:
        def __init__(self, *args, **kwargs):
            self._state = {}

        def log(self, text):
            return {"note": text}

        def resume(self):
            return "scatter"

        def learn(self, text):
            self._state["last"] = text

        def say(self, text):
            return text

        def status(self):
            return json.dumps(self._state)

        def cache(self, text, tags=None):
            return "cached"

        def validate(self):
            return {"passed": True, "issues": []}

    GardenImpl = EchoImpl = LimnusImpl = KiraImpl = _Stub


class GardenAgent(BaseAgent):
    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        agent = GardenImpl(self.record.path)
        note_ref = await self._run_blocking(agent.log, context.input_text)
        stage = await self._run_blocking(agent.resume)
        result = {"stage": stage, "ledger_ref": note_ref}
        await self.append_log("garden", result)
        return result


class EchoAgent(BaseAgent):
    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        agent = EchoImpl(self.record.path)
        await self._run_blocking(agent.learn, context.input_text)
        styled = await self._run_blocking(agent.say, context.input_text)
        state_json = await self._run_blocking(agent.status)
        try:
            state = json.loads(state_json)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            state = {"raw": state_json}
        return {"styled_text": styled, "state": state}


class LimnusAgent(BaseAgent):
    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        agent = LimnusImpl(self.record.path)
        await self._run_blocking(agent.cache, context.input_text, tags=[context.user_id])
        mem_path = self.record.path / "state" / "limnus_memory.json"
        if mem_path.exists():
            data = json.loads(mem_path.read_text(encoding="utf-8"))
            memory_id = data[-1].get("id") if data else None
            layer = data[-1].get("layer", "L2") if data else "L2"
        else:
            memory_id = None
            layer = "L2"
        return {"cached": True, "memory_id": memory_id, "layer": layer}


class KiraAgent(BaseAgent):
    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        agent = KiraImpl(self.record.path)
        validation = await self._run_blocking(agent.validate)
        return validation


__all__ = [
    "BaseAgent",
    "GardenAgent",
    "EchoAgent",
    "LimnusAgent",
    "KiraAgent",
]
