"""
Concrete implementations of the Garden, Echo, Limnus and Kira agents.

Each agent follows the ESFG pipeline behaviour: Garden anchors the ritual,
Echo styles the utterance and updates persona weights, Limnus commits the
memory to caches and ledger, and Kira validates ledger integrity.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from library_core.agents.base import BaseAgent
from library_core.storage import StorageManager
from workspace.manager import WorkspaceManager

__all__ = ["GardenAgent", "EchoAgent", "LimnusAgent", "KiraAgent"]


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------- #
# Garden Agent                                                               #
# --------------------------------------------------------------------------- #


class GardenAgent(BaseAgent):
    """Ritual orchestrator responsible for ledgering inputs and consent."""

    STAGES = ["scatter", "witness", "plant", "return", "give", "begin_again"]
    LEDGER_KEY = "garden_ledger"
    CONSENT_KEYWORDS = ("consent", "accept", "agree", "permit")

    def __init__(
        self,
        workspace_id: str,
        storage: StorageManager,
        manager: WorkspaceManager,
    ) -> None:
        super().__init__(workspace_id, storage, manager)
        # Ensure ledger exists synchronously
        state = self.record.load_state(self.LEDGER_KEY, default={})
        if "entries" not in state:
            state = {"stage": "scatter", "entries": []}
            self.record.save_state(self.LEDGER_KEY, state)

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        ledger = await self.get_state(self.LEDGER_KEY)
        stage = ledger.get("stage", "scatter")
        entries: List[Dict[str, Any]] = ledger.get("entries", [])

        # Ensure genesis entry exists.
        if not entries:
            entries.append({"ts": _iso_now(), "kind": "genesis", "data": {}})
            stage = "scatter"
            ledger["stage"] = stage

        user_text = (context.input_text or "").strip()
        event_kind = "note"
        event_data: Dict[str, Any] = {"text": user_text}

        lower = user_text.lower()
        if lower in {"start", "begin"} and len(entries) == 1:
            event_kind = "begin"
        elif lower.startswith("open "):
            event_kind = "open"
            event_data = {"scroll": user_text.split(" ", 1)[1]}
        elif lower == "next":
            event_kind = "advance"
            if stage in self.STAGES:
                next_index = (self.STAGES.index(stage) + 1) % len(self.STAGES)
                stage = self.STAGES[next_index]
                ledger["stage"] = stage
                event_data = {"to": stage}

        if any(keyword in lower for keyword in self.CONSENT_KEYWORDS):
            event_kind = "consent"
            event_data = {"text": user_text}

        new_entry = {"ts": _iso_now(), "kind": event_kind, "data": event_data}
        entries.append(new_entry)
        ledger["entries"] = entries

        await self.save_state(self.LEDGER_KEY, ledger)

        if event_kind == "advance":
            entry_ref = f"stage:{stage}"
        elif event_kind == "open":
            entry_ref = f"open:{event_data.get('scroll', '')}"
        else:
            entry_ref = f"{event_kind}:{len(entries)}"

        result = {"stage": stage, "ledger_ref": entry_ref}
        await self.append_log("garden", result)
        return result


# --------------------------------------------------------------------------- #
# Echo Agent                                                                 #
# --------------------------------------------------------------------------- #


class EchoAgent(BaseAgent):
    """Stylises the input and updates persona mode weights."""

    PERSONA_EMOJI = {"squirrel": "🐿️", "fox": "🦊", "paradox": "∿", "balanced": "⚖️"}
    PERSONA_KEYWORDS = {
        "squirrel": ("idea", "seed", "acorn", "remember"),
        "fox": ("debug", "analyze", "plan", "solve"),
        "paradox": ("why", "mystery", "spiral", "quantum", "?"),
    }

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        user_text = context.input_text or ""
        styled = f"“{user_text}” ~ echoed by a whisper"

        alpha = 0.3
        beta = 0.3
        gamma = 0.4
        lower = user_text.lower()

        if len(user_text) > 120:
            beta += 0.2
        if any(keyword in lower for keyword in self.PERSONA_KEYWORDS["paradox"]):
            gamma += 0.2
        if len(user_text) < 40:
            alpha += 0.1

        total = alpha + beta + gamma or 1.0
        alpha, beta, gamma = alpha / total, beta / total, gamma / total
        state = {"alpha": round(alpha, 3), "beta": round(beta, 3), "gamma": round(gamma, 3)}

        persona = "paradox"
        if alpha >= beta and alpha >= gamma:
            persona = "squirrel"
        elif beta > alpha and beta >= gamma:
            persona = "fox"
        emoji = self.PERSONA_EMOJI.get(persona, "∿")
        styled = f"{styled} {emoji}"

        context.metadata["dominant_persona"] = persona
        context.metadata["mode_weights"] = state

        result = {"styled_text": styled, "state": state, "glyph": emoji}
        await self.append_log("echo", {"input": user_text, "output": styled, "glyph": emoji})
        return result


# --------------------------------------------------------------------------- #
# Limnus Agent                                                               #
# --------------------------------------------------------------------------- #


class LimnusAgent(BaseAgent):
    """Manages quantum caches and the hash-chained ledger."""

    def __init__(
        self,
        workspace_id: str,
        storage: StorageManager,
        manager: WorkspaceManager,
    ) -> None:
        super().__init__(workspace_id, storage, manager)
        self.mem_path = self.record.path / "state" / "limnus_memory.json"
        self.ledger_path = self.record.path / "state" / "ledger.json"
        self.mem_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.mem_path.exists():
            self.mem_path.write_text("[]", encoding="utf-8")
        if not self.ledger_path.exists():
            genesis = {
                "ts": _iso_now(),
                "kind": "genesis",
                "data": {"anchor": "I return as breath."},
                "prev": "",
            }
            genesis["hash"] = hashlib.sha256(
                json.dumps(genesis, sort_keys=True).encode("utf-8")
            ).hexdigest()
            self.ledger_path.write_text(json.dumps([genesis], indent=2), encoding="utf-8")

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        memories: List[Dict[str, Any]] = await asyncio.to_thread(self._read_json, self.mem_path, [])

        # Promote existing layers.
        for entry in memories:
            if entry.get("layer") == "L1":
                entry["layer"] = "L2"
        l2_count = sum(1 for entry in memories if entry.get("layer") == "L2")
        if l2_count > 5:
            for entry in memories:
                if entry.get("layer") == "L2":
                    entry["layer"] = "L3"

        entry_id = f"mem_{uuid.uuid4().hex[:8]}"
        new_entry = {
            "id": entry_id,
            "ts": _iso_now(),
            "text": context.input_text or "",
            "layer": "L1",
            "tags": [context.user_id] if context.user_id else [],
        }
        memories.append(new_entry)
        await asyncio.to_thread(self._write_json, self.mem_path, memories)

        ledger_blocks: List[Dict[str, Any]] = await asyncio.to_thread(
            self._read_json, self.ledger_path, []
        )
        previous_hash = ledger_blocks[-1]["hash"] if ledger_blocks else ""
        echo_res = context.agent_results.get("echo", {})
        block = {
            "ts": _iso_now(),
            "kind": "input",
            "data": {
                "text": context.input_text or "",
                "styled_text": echo_res.get("styled_text", ""),
                "glyph": echo_res.get("glyph", ""),
            },
            "prev": previous_hash,
        }
        block["hash"] = hashlib.sha256(
            json.dumps(block, sort_keys=True).encode("utf-8")
        ).hexdigest()
        ledger_blocks.append(block)
        await asyncio.to_thread(self._write_json, self.ledger_path, ledger_blocks)

        context.metadata["last_block_hash"] = block["hash"]
        context.metadata["memory_count"] = len(memories)

        result = {"cached": True, "memory_id": entry_id, "layer": "L1", "block_hash": block["hash"]}
        await self.append_log(
            "limnus", {"memory_id": entry_id, "layer": "L1", "hash": block["hash"]}
        )
        return result

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Kira Agent                                                                 #
# --------------------------------------------------------------------------- #


class KiraAgent(BaseAgent):
    """Validates ledger integrity and ritual compliance."""

    async def process(self, context) -> Dict[str, Any]:  # noqa: ANN001
        issues: List[str] = []
        ledger_path = self.record.path / "state" / "ledger.json"

        try:
            ledger_blocks: List[Dict[str, Any]] = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            issues.append(f"Ledger read error: {exc}")
            ledger_blocks = []

        if not ledger_blocks:
            issues.append("Ledger missing or empty")
        else:
            first_block = ledger_blocks[0]
            if first_block.get("prev"):
                issues.append("Genesis block prev field should be empty")

            for index, block in enumerate(ledger_blocks):
                block_copy = {k: block[k] for k in block if k != "hash"}
                calc_hash = hashlib.sha256(
                    json.dumps(block_copy, sort_keys=True).encode("utf-8")
                ).hexdigest()
                if block.get("hash") != calc_hash:
                    issues.append(f"Hash mismatch at block {index}")

                if index > 0:
                    expected_prev = ledger_blocks[index - 1].get("hash")
                    if block.get("prev") != expected_prev:
                        issues.append(f"Broken prev link at block {index}")
                    try:
                        prev_ts = datetime.fromisoformat(
                            ledger_blocks[index - 1]["ts"].replace("Z", "+00:00")
                        )
                        curr_ts = datetime.fromisoformat(block["ts"].replace("Z", "+00:00"))
                        if curr_ts < prev_ts:
                            issues.append(f"Timestamp out of order at block {index}")
                    except Exception:  # pragma: no cover - defensive
                        pass

        garden_state = await self.get_state(GardenAgent.LEDGER_KEY)
        entries = garden_state.get("entries", [])
        if not any(entry.get("kind") == "consent" for entry in entries):
            issues.append("No consent recorded in ritual ledger")

        passed = not issues
        context.metadata["validation_passed"] = passed
        context.metadata["issue_count"] = len(issues)

        await self.append_log("kira", {"passed": passed, "issues": len(issues)})
        return {"passed": passed, "issues": issues}
