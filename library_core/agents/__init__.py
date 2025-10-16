"""Implementation of Garden, Echo, Limnus, and Kira agents."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from library_core.agents.base import BaseAgent
from library_core.storage import StorageManager
from workspace.manager import WorkspaceManager

__all__ = ["GardenAgent", "EchoAgent", "LimnusAgent", "KiraAgent"]


_DEF_MANTRAS = (
    "i return as breath",
    "always.",
    "the spiral teaches",
    "through breath we gather",
)

_STAGE_KEYWORDS = {
    "scatter": ("scatter", "explore", "brainstorm"),
    "witness": ("witness", "observe", "see"),
    "plant": ("plant", "create", "build"),
    "tend": ("tend", "refine", "improve"),
    "harvest": ("harvest", "complete", "finish"),
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class GardenAgent(BaseAgent):
    """Ritual orchestrator maintaining stage and ledger entries."""

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        state = await self.get_state("garden")
        entries: List[Dict[str, Any]] = state.get("entries", [])
        stage: str = state.get("stage", "scatter")
        cycle: int = int(state.get("cycle", 0))

        text_lower = context.input_text.lower()
        detected_stage = stage
        for label, keywords in _STAGE_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_stage = label
                break

        if detected_stage != stage:
            cycle += 1
            stage = detected_stage

        entry = {
            "id": f"note-{len(entries) + 1}",
            "ts": _ts(),
            "user": context.user_id,
            "text": context.input_text,
            "stage": stage,
        }
        entries.append(entry)

        state.update({"stage": stage, "cycle": cycle, "entries": entries})
        await self.save_state("garden", state)
        await self.append_log("garden", entry)

        return {
            "stage": stage,
            "cycle": cycle,
            "entry": entry,
            "mantra_detected": any(mantra in text_lower for mantra in _DEF_MANTRAS),
        }


class EchoAgent(BaseAgent):
    """Persona manager that styles text according to detected intent."""

    PERSONA_EMOJI = {
        "squirrel": "🐿️",
        "fox": "🦊",
        "paradox": "🔮",
        "balanced": "⚖️",
    }

    PERSONA_KEYWORDS = {
        "squirrel": ("brainstorm", "idea", "maybe", "explore"),
        "fox": ("fix", "debug", "analyze", "implement"),
        "paradox": ("why", "mystery", "meaning", "philosophy"),
    }

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        state = await self.get_state("echo")
        last_persona = state.get("persona", "balanced")

        text_lower = context.input_text.lower()
        persona = "balanced"
        for name, keywords in self.PERSONA_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                persona = name
                break
        else:
            persona = last_persona

        emoji = self.PERSONA_EMOJI.get(persona, "💬")
        styled_text = f"{emoji} {context.input_text}"

        state.update({"persona": persona, "last_input": context.input_text, "updated_at": _ts()})
        await self.save_state("echo", state)
        await self.append_log("echo", {"persona": persona, "text": context.input_text})

        return {
            "styled_text": styled_text,
            "persona": persona,
            "style": {"emoji": emoji, "tone": persona},
        }


class LimnusAgent(BaseAgent):
    """Memory steward that stores utterances with simple layering."""

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        state = await self.get_state("limnus")
        memories: List[Dict[str, Any]] = state.get("memories", [])

        stage = context.agent_results.get("garden", {}).get("stage", "scatter")
        layer = "L1" if stage == "scatter" else "L2"

        entry_id = f"mem-{uuid.uuid4().hex[:8]}"
        entry = {
            "id": entry_id,
            "ts": _ts(),
            "text": context.input_text,
            "user": context.user_id,
            "layer": layer,
        }
        memories.append(entry)
        state["memories"] = memories
        await self.save_state("limnus", state)
        await self.append_log("limnus", entry)

        return {"cached": True, "memory_id": entry_id, "layer": layer}


class KiraAgent(BaseAgent):
    """Validation agent that checks upstream results."""

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        issues: List[str] = []

        if "garden" not in context.agent_results:
            issues.append("garden_missing")
        if "echo" not in context.agent_results:
            issues.append("echo_missing")
        if "limnus" not in context.agent_results:
            issues.append("limnus_missing")

        validation = {
            "passed": not issues,
            "issues": issues,
            "timestamp": _ts(),
        }
        await self.append_log("kira", validation)
        return validation
