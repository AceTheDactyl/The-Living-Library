"""
Remote collaboration runtime scaffolding.

This module exposes the entry points for the forthcoming WebSocket
server, OT/CRDT engine, and CLI metrics integration described in the
Phase 3 specification.
"""

from .server import CollaborationServer
from .client import CollaborationClient

__all__ = ["CollaborationServer", "CollaborationClient"]
