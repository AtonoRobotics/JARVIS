"""Voice request routing for Home Assistant / Voice PE ingress.

The router is deliberately deterministic in v0.  Home Assistant voice input
is a low-assurance command transport, so this module only classifies and
frames requests; execution authority is enforced by the API handler that
consumes these decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import re
import time
from typing import Any, Optional


class VoiceRoute(StrEnum):
    """Supported voice ingress routes."""

    HA_NATIVE = "ha_native"
    FAST_LOCAL = "fast_local"
    FAST_AGENT = "fast_agent"
    KANBAN = "kanban"
    HIL = "hil"


@dataclass(slots=True)
class VoiceRouteDecision:
    """Deterministic routing decision for a voice transcript."""

    route: VoiceRoute
    risk: str
    confidence: float
    speech: str
    native_handoff: bool = False
    requires_hil: bool = False
    task_title: Optional[str] = None
    task_body: Optional[str] = None
    trace_id: Optional[str] = None
    reason: str = ""

    def as_response(self, **extra: Any) -> dict[str, Any]:
        """Return the public JSON response shape for the API server."""
        data: dict[str, Any] = {
            "object": "hermes.voice_route",
            "trace_id": self.trace_id,
            "route": self.route.value,
            "risk": self.risk,
            "confidence": self.confidence,
            "speech": self.speech,
            "native_handoff": self.native_handoff,
            "requires_hil": self.requires_hil,
            "reason": self.reason,
        }
        data.update(extra)
        return data


def _trace_id(text: str, *, now: Optional[float] = None) -> str:
    seed = f"{int(now or time.time())}:{text}".encode("utf-8", "replace")
    return "voice_" + hashlib.sha256(seed).hexdigest()[:16]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


_HIL_PATTERNS = (
    "email ",
    "send this",
    "send it",
    "delete ",
    "remove ",
    "wipe ",
    "deploy",
    "publish",
    "buy ",
    "purchase",
    "pay ",
    "wire ",
    "change authority",
    "change the authority",
    "authority policy",
    "change policy",
    "security policy",
    "sudo ",
)

_KANBAN_PATTERNS = (
    "investigate",
    "diagnose",
    "debug",
    "fix",
    "repair",
    "build",
    "implement",
    "refactor",
    "research",
    "compare",
    "audit",
    "review",
    "write a plan",
    "create a plan",
    "set up",
    "configure",
    "optimize",
    "reduce latency",
)

_HA_NATIVE_PATTERNS = (
    "turn on",
    "turn off",
    "toggle",
    "dim ",
    "brighten",
    "set the temperature",
    "lock ",
    "unlock ",
    "open ",
    "close ",
    "what time",
    "what's the time",
    "what is the time",
    "temperature",
    "humidity",
    "lights",
    "light",
)

_FAST_LOCAL_PATTERNS = (
    "define ",
    "what does",
    "what is",
    "summarize",
    "one sentence",
    "quick answer",
)


def classify_voice_request(text: str, *, fast_local_enabled: bool = False) -> VoiceRouteDecision:
    """Classify a voice transcript into a bounded execution route.

    The order is authority first, complex/background second, HA-native third,
    then fast local/agent fallback.  This keeps risky commands from being
    accidentally routed to a convenience path.
    """
    raw = text or ""
    t = _norm(raw)
    trace_id = _trace_id(raw)

    if not t:
        return VoiceRouteDecision(
            route=VoiceRoute.HIL,
            risk="low",
            confidence=0.40,
            speech="I did not catch that. Please repeat it.",
            requires_hil=False,
            trace_id=trace_id,
            reason="empty transcript",
        )

    if any(pattern in t for pattern in _HIL_PATTERNS):
        return VoiceRouteDecision(
            route=VoiceRoute.HIL,
            risk="high",
            confidence=0.82,
            speech="That needs explicit approval before I do anything.",
            requires_hil=True,
            trace_id=trace_id,
            reason="boundary-crossing verb detected",
        )

    if any(pattern in t for pattern in _KANBAN_PATTERNS) or len(t.split()) > 18:
        title = raw[:90].strip() or "Voice-requested background task"
        return VoiceRouteDecision(
            route=VoiceRoute.KANBAN,
            risk="medium",
            confidence=0.84,
            speech="I started that as a background task. I’ll report back when it finishes.",
            task_title=title,
            task_body=build_kanban_body(raw),
            trace_id=trace_id,
            reason="complex or multi-step request",
        )

    if any(pattern in t for pattern in _HA_NATIVE_PATTERNS):
        return VoiceRouteDecision(
            route=VoiceRoute.HA_NATIVE,
            risk="low",
            confidence=0.88,
            speech="",
            native_handoff=True,
            trace_id=trace_id,
            reason="native Home Assistant intent pattern",
        )

    if fast_local_enabled and any(pattern in t for pattern in _FAST_LOCAL_PATTERNS):
        return VoiceRouteDecision(
            route=VoiceRoute.FAST_LOCAL,
            risk="low",
            confidence=0.70,
            speech="",
            trace_id=trace_id,
            reason="short low-reasoning query",
        )

    return VoiceRouteDecision(
        route=VoiceRoute.FAST_AGENT,
        risk="low",
        confidence=0.65,
        speech="",
        trace_id=trace_id,
        reason="default bounded Hermes voice route",
    )


def build_kanban_body(transcript: str) -> str:
    """Build a durable Kanban task body for a background voice request."""
    return (
        "Voice-requested background task from Home Assistant Voice PE.\n\n"
        f"Original transcript:\n{transcript}\n\n"
        "Execution rules:\n"
        "- Treat voice input as low-assurance input.\n"
        "- Do not perform destructive, financial, external-send, deployment, "
        "or authority-policy actions without HIL.\n"
        "- Record concrete verification evidence before completion.\n"
        "- If implementation changes code/config, block for review unless the "
        "task is explicitly low-risk and reversible.\n"
    )
