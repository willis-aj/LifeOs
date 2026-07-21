"""
Self-Care Agent - conversational brain.

Deterministic and rule-based (no external LLM/NLP dependency, consistent
with the rest of LifeOS, which has none): keyword/intent matching over the
user's free text, a small persisted conversation state machine (a single
`pending_action` the next message is checked against), and direct calls
into the existing LifeOSEngine (add_routine, toggle_comfort_mode,
routine_by_id) so anything the user asks for becomes a real routine/task,
never a parallel object the rest of the app can't see.

Conversation pipeline: user message -> intent -> (goal extraction ->
clarifying question -> confirmation) -> engine.add_routine() /
engine.toggle_comfort_mode() -> conversational reply. Every reply is run
through self_care_agent.lint_message() before being sent.

Two personas speak from this module, matching the chat UI's visual cues:
  - "system"        - structural confirmations ("Added X as a routine.")
  - "self_care_agent" - the warm, conversational wrapper around that fact
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from . import persistence, self_care_agent
from .engine import LifeOSEngine

SYSTEM = "system"
AGENT = "self_care_agent"
USER = "user"

# Keyword -> matching self-care routine id, so a free-text mention like
# "I never brush my teeth" resolves to the same routine the scheduler
# already tracks, rather than spawning a duplicate.
KEYWORD_ROUTINE_MAP: Dict[str, str] = {
    "brush": "brush_teeth_am",
    "teeth": "brush_teeth_am",
    "shower": "shower_weekly",
    "bath": "shower_weekly",
    "deodorant": "deodorant",
    "face": "face_wash",
    "nail": "nail_trim",
    "towel": "towel_swap",
    "sheet": "bedding_change",
    "bedding": "bedding_change",
}

OVERWHELM_PHRASES = (
    "too much",
    "overwhelmed",
    "overwhelming",
    "can't do this",
    "cant do this",
    "not today",
    "burnt out",
    "burned out",
)
AFFIRM_PHRASES = ("yes", "yeah", "yep", "sure", "ok", "okay", "do it", "please do")
DECLINE_PHRASES = ("no", "nah", "not now", "later", "skip it")
NEW_GOAL_MARKERS = ("want to", "help me", "i need", "remind me", "i'd like to", "id like to")
FREQUENCY_WORDS: Dict[str, str] = {
    "every day": "daily",
    "everyday": "daily",
    "daily": "daily",
    "every week": "weekly",
    "weekly": "weekly",
    "every month": "monthly",
    "monthly": "monthly",
}


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _agent_msg(text: str) -> Dict[str, str]:
    linted = self_care_agent.lint_message(text) or "Let's take this one step at a time."
    return {"speaker": AGENT, "text": linted, "timestamp": _now()}


def _system_msg(text: str) -> Dict[str, str]:
    return {"speaker": SYSTEM, "text": text, "timestamp": _now()}


def _detect_intent(text: str, pending_action: Optional[Dict[str, Any]]) -> str:
    lowered = text.lower().strip()

    if pending_action:
        if pending_action.get("type") == "awaiting_frequency" and any(
            phrase in lowered for phrase in FREQUENCY_WORDS
        ):
            return "frequency_given"
        if any(phrase in lowered for phrase in AFFIRM_PHRASES):
            return "confirm"
        if any(phrase in lowered for phrase in DECLINE_PHRASES):
            return "decline"

    if any(phrase in lowered for phrase in OVERWHELM_PHRASES):
        return "overwhelm"

    if any(keyword in lowered for keyword in KEYWORD_ROUTINE_MAP):
        return "known_goal_mention"

    if any(marker in lowered for marker in NEW_GOAL_MARKERS):
        return "new_goal_mention"

    return "unknown"


def _extract_goal_label(text: str) -> str:
    lowered = text.lower()
    for marker in NEW_GOAL_MARKERS:
        idx = lowered.find(marker)
        if idx != -1:
            remainder = text[idx + len(marker):].strip()
            if remainder:
                return remainder.rstrip(".!?").capitalize()
    return text.strip().rstrip(".!?").capitalize()


def _extract_frequency(text: str) -> str:
    lowered = text.lower()
    for phrase, frequency in FREQUENCY_WORDS.items():
        if phrase in lowered:
            return frequency
    return "weekly"


def _resolve_pending(engine: LifeOSEngine, pending: Dict[str, Any]) -> List[Dict[str, str]]:
    """User confirmed a pending action - actually do it via the real
    engine, then report both structurally (system) and conversationally
    (agent)."""
    if pending.get("type") == "confirm_comfort_mode":
        engine.toggle_comfort_mode()
        return [
            _system_msg("Comfort Mode enabled."),
            _agent_msg("Done. Everything non-essential just came off today's plate."),
        ]

    if pending.get("type") == "confirm_add_manual_task":
        routine_id = pending["routine_id"]
        routine = engine.routine_by_id(routine_id)
        if routine is None:
            return [_agent_msg("Hmm, I couldn't find that one anymore - no worries, we can pick it up another time.")]
        task = engine.add_manual_task(
            label=routine.label,
            duration_minutes=routine.duration_minutes,
            goal_id=routine.goal,
            xp=routine.xp,
        )
        return [
            _system_msg(f"Added \"{task.label}\" to today's schedule."),
            _agent_msg(f"It's on today's list now, whenever works for you."),
        ]

    return [_agent_msg("Okay.")]


def handle_message(engine: LifeOSEngine, user_text: str) -> List[Dict[str, str]]:
    """Process one user message against the player's persisted
    conversation state, mutate real engine state as needed (routines,
    tasks, Comfort Mode), persist the updated conversation, and return the
    new messages (the user's own message plus every system/agent reply) in
    the order they should be displayed."""
    convo = persistence.load_self_care_chat(engine.player_id)
    pending: Optional[Dict[str, Any]] = convo.get("pending_action")

    new_messages: List[Dict[str, str]] = [{"speaker": USER, "text": user_text, "timestamp": _now()}]
    intent = _detect_intent(user_text, pending)

    if intent == "confirm" and pending:
        new_messages.extend(_resolve_pending(engine, pending))
        pending = None

    elif intent == "decline" and pending:
        new_messages.append(_agent_msg("No worries, we can leave it for now."))
        pending = None

    elif intent == "frequency_given" and pending and pending.get("type") == "awaiting_frequency":
        frequency = _extract_frequency(user_text)
        routine = engine.add_routine(
            label=pending["label"],
            frequency=frequency,
            duration_minutes=10,
            note_template="Good enough: any attempt counts.",
        )
        new_messages.append(_system_msg(f"Added \"{routine.label}\" as a {frequency} routine."))
        new_messages.append(
            _agent_msg(f"Got it - I'll check in with you about {routine.label.lower()} {frequency}. You're all set.")
        )
        pending = None

    elif intent == "overwhelm":
        if engine.state.comfort_mode:
            new_messages.append(
                _agent_msg(
                    "You're already in Comfort Mode - the schedule's as light as it gets right now. "
                    "Be gentle with yourself today."
                )
            )
        else:
            new_messages.append(
                _agent_msg(
                    "That's okay. Want me to switch things to Comfort Mode? "
                    "It trims the schedule down to just the essentials."
                )
            )
            pending = {"type": "confirm_comfort_mode"}

    elif intent == "known_goal_mention":
        routine_id = next(
            routine_id for keyword, routine_id in KEYWORD_ROUTINE_MAP.items() if keyword in user_text.lower()
        )
        routine = engine.routine_by_id(routine_id)
        if routine is not None:
            today_task = next(
                (t for t in engine.tasks if t.source_routine_id == routine_id and not t.completed and not t.skipped),
                None,
            )
            reply = f"{routine.label} is already on your schedule."
            if today_task and today_task.note_template:
                reply += f" {today_task.note_template}"
            new_messages.append(_agent_msg(reply))
        else:
            new_messages.append(
                _agent_msg(
                    "I don't have that one tracked yet. Want me to add a reminder for it? "
                    "If so, how often - daily, weekly, or monthly?"
                )
            )
            pending = {"type": "awaiting_frequency", "label": _extract_goal_label(user_text)}

    elif intent == "new_goal_mention":
        new_messages.append(_agent_msg("Got it. How often would you like a reminder - daily, weekly, or monthly?"))
        pending = {"type": "awaiting_frequency", "label": _extract_goal_label(user_text)}

    else:
        new_messages.append(
            _agent_msg(
                "I'm listening - tell me about a self-care thing you want help keeping up with, "
                "or let me know if today's feeling like too much."
            )
        )

    convo["messages"] = convo.get("messages", []) + new_messages
    convo["pending_action"] = pending
    persistence.save_self_care_chat(engine.player_id, convo)

    return new_messages


def get_history(player_id: str) -> List[Dict[str, str]]:
    return persistence.load_self_care_chat(player_id).get("messages", [])
