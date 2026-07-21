"""
Self-Care Agent: a reasoning layer over the existing LifeOSEngine that
surfaces gentle, neurodivergent-friendly nudges for self-care routines
(hygiene, grooming, rest, environment upkeep) and detects when a player
looks overwhelmed enough that Comfort Mode is worth suggesting.

Deliberately NOT a parallel task/schedule system. Self-care "tasks" are
ordinary Task objects generated from the routines listed in
config.SELF_CARE_ROUTINE_IDS, and "low-demand mode" is the engine's
existing Comfort Mode (which already restricts the schedule to config.
ESSENTIAL_ROUTINE_IDS - see scheduler.build_daily_schedule's only_essentials
filter). This module only adds: signal detection from real task/routine
history, an overwhelm flag, and softly-worded nudge messages built from
each routine's note_template (its "good enough" / sensory-friendly
alternative). The conversational front-end for this same reasoning lives
in life_os/self_care_agent_chat.py.
"""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from . import config
from .engine import LifeOSEngine
from .models import Task

# Phrasing the agent must never use, however a note_template ends up being
# authored later - a last-line-of-defense tone check before a message goes out.
BANNED_WORDS = ("should", "forgot", "again", "still haven't", "lazy")

# A self-care task is considered "overdue enough to count" once its routine
# has gone this many days past its own cadence.
_FREQUENCY_INTERVAL_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 28,
}


@dataclass
class SelfCareSignals:
    """Real, computed-from-history signals - no separate tracking state is
    persisted anywhere; this is recomputed fresh every time."""

    consecutive_skips: int
    overdue_ratio: float
    overwhelm: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _self_care_routines(engine: LifeOSEngine):
    return [r for r in engine.routines if r.id in config.SELF_CARE_ROUTINE_IDS]


def _routine_interval_days(routine) -> int:
    if routine.frequency == "every_n_days":
        return routine.interval_days or 1
    return _FREQUENCY_INTERVAL_DAYS.get(routine.frequency, 1)


def compute_signals(engine: LifeOSEngine, today: Optional[datetime.date] = None) -> SelfCareSignals:
    """Derive overwhelm signals from real task/routine history already
    persisted by the engine - nothing self-care-specific is stored."""
    today = today or engine.today
    routines = _self_care_routines(engine)

    # Signal 1: self-care tasks sitting skipped, unaddressed, anywhere in the
    # rolling multi-day schedule (skip_task() leaves them in place unless
    # something depends on them).
    consecutive_skips = sum(
        1
        for day_tasks in engine.schedule.values()
        for t in day_tasks
        if t.source_routine_id in config.SELF_CARE_ROUTINE_IDS and t.skipped
    )

    # Signal 2: fraction of self-care routines currently overdue relative to
    # their own cadence - a proxy for "falling behind" over time.
    overdue_count = 0
    for r in routines:
        if r.last_completed_date is None:
            overdue_count += 1
            continue
        last = datetime.date.fromisoformat(r.last_completed_date)
        if (today - last).days > _routine_interval_days(r):
            overdue_count += 1
    overdue_ratio = (overdue_count / len(routines)) if routines else 0.0

    overwhelm = (consecutive_skips >= 2) and (overdue_ratio > 0.4)

    return SelfCareSignals(
        consecutive_skips=consecutive_skips,
        overdue_ratio=round(overdue_ratio, 2),
        overwhelm=overwhelm,
    )


def lint_message(text: str) -> Optional[str]:
    """Tone self-check: returns the text unchanged if it's clean, or None if
    it trips a banned-word guard (caller should fall back to a generic,
    pre-approved phrasing rather than send a shaming message)."""
    lowered = text.lower()
    if any(word in lowered for word in BANNED_WORDS):
        return None
    return text


def _format_window(hour: Optional[int]) -> str:
    """Flexible time-blindness-friendly phrasing: a window, never a bare
    clock time."""
    if hour is None:
        return "whenever works today"

    def fmt(h: int) -> str:
        period = "AM" if h < 12 else "PM"
        display = h % 12 or 12
        return f"{display}:00 {period}"

    end = min(config.DAY_END_HOUR, hour + 3)
    return f"sometime between {fmt(hour)} and {fmt(end)}"


def _nudge_text(task: Task, simplify: bool) -> str:
    good_enough = task.note_template
    window = _format_window(task.scheduled_hour)

    if simplify and good_enough:
        text = f"No pressure - {window}, {good_enough[0].lower()}{good_enough[1:]}"
    elif good_enough:
        text = f"{task.label}, {window}. {good_enough}"
    else:
        text = f"{task.label}, {window}."

    return lint_message(text) or f"{task.label} is up whenever you're ready."


def nudge_messages(engine: LifeOSEngine, simplify: bool = False) -> List[Dict[str, Any]]:
    """Gentle reminders for today's pending self-care tasks. When `simplify`
    is True (overwhelm detected), phrasing leads with the "good enough"
    alternative instead of the full ask."""
    messages: List[Dict[str, Any]] = []
    for task in engine.tasks:
        if task.source_routine_id not in config.SELF_CARE_ROUTINE_IDS:
            continue
        if task.completed or task.skipped or task.locked:
            continue

        messages.append(
            {
                "task_id": task.id,
                "label": task.label,
                "text": _nudge_text(task, simplify),
                "tone": "gentle_nudge",
            }
        )
    return messages


def self_care_status(engine: LifeOSEngine) -> Dict[str, Any]:
    """Top-level entry point: real signals + today's nudges + whether
    Comfort Mode is worth suggesting. Read-only - completing a task,
    adding a routine, or toggling Comfort Mode all go through the engine's
    existing methods; this just reports on current state."""
    signals = compute_signals(engine)
    messages = nudge_messages(engine, simplify=signals.overwhelm)
    comfort_mode_recommended = signals.overwhelm and not engine.state.comfort_mode

    return {
        "signals": signals.to_dict(),
        "comfort_mode_active": engine.state.comfort_mode,
        "comfort_mode_recommended": comfort_mode_recommended,
        "messages": messages,
    }
