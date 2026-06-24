"""Tests for Home Assistant voice routing decisions."""

import pytest

from gateway.voice_router import VoiceRoute, classify_voice_request


def test_classifies_smart_home_as_ha_native():
    decision = classify_voice_request("turn on the office light")

    assert decision.route == VoiceRoute.HA_NATIVE
    assert decision.risk == "low"
    assert decision.native_handoff is True
    assert decision.requires_hil is False


def test_classifies_time_question_as_ha_native():
    decision = classify_voice_request("what time is it")

    assert decision.route == VoiceRoute.HA_NATIVE
    assert decision.native_handoff is True


def test_classifies_short_question_as_fast_agent_by_default():
    decision = classify_voice_request("what does latency mean")

    assert decision.route == VoiceRoute.FAST_AGENT
    assert decision.risk == "low"
    assert decision.native_handoff is False


def test_classifies_short_question_as_fast_local_when_enabled():
    decision = classify_voice_request("what does latency mean", fast_local_enabled=True)

    assert decision.route == VoiceRoute.FAST_LOCAL
    assert decision.risk == "low"


def test_classifies_investigate_fix_as_kanban():
    decision = classify_voice_request("investigate why Voice PE latency is high and fix it")

    assert decision.route == VoiceRoute.KANBAN
    assert decision.risk == "medium"
    assert "background" in decision.speech.lower()
    assert decision.task_title
    assert "Original transcript" in (decision.task_body or "")


@pytest.mark.parametrize(
    "text",
    [
        "email this to Bob",
        "delete the production database",
        "change the authority policy",
        "buy more credits",
        "deploy this to production",
    ],
)
def test_classifies_boundary_crossing_as_hil(text):
    decision = classify_voice_request(text)

    assert decision.route == VoiceRoute.HIL
    assert decision.requires_hil is True
    assert decision.risk == "high"
    assert "approval" in decision.speech.lower() or "confirm" in decision.speech.lower()


def test_empty_transcript_asks_to_repeat_without_hil():
    decision = classify_voice_request("   ")

    assert decision.route == VoiceRoute.HIL
    assert decision.requires_hil is False
    assert "repeat" in decision.speech.lower()
