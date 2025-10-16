"""Wrappers around the Kira Prime agents bundled as a submodule."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

KIRA_ROOT = Path(__file__).resolve().parents[1] / "kira-prime"
if not KIRA_ROOT.exists():  # pragma: no cover - defensive
    raise RuntimeError("kira-prime submodule is required but missing.")

if str(KIRA_ROOT) not in sys.path:
    sys.path.insert(0, str(KIRA_ROOT))

GardenAgent = import_module("agents.garden.garden_agent").GardenAgent
EchoAgent = import_module("agents.echo.echo_agent").EchoAgent
LimnusAgent = import_module("agents.limnus.limnus_agent").LimnusAgent
KiraAgent = import_module("agents.kira.kira_agent").KiraAgent

__all__ = ["GardenAgent", "EchoAgent", "LimnusAgent", "KiraAgent", "KIRA_ROOT"]
