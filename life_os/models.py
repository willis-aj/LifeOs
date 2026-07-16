"""
Core dataclasses used across LifeOS.

These are deliberately plain and serialization-friendly (only primitives,
lists, and dicts) so `persistence.py` can dump/load them as JSON without
needing custom encoders.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Goal:
    id: str
    name: str
    description: str
    base_xp_per_task: int
    milestones: List[int] = field(default_factory=list)
    xp: int = 0
    level: int = 1
    milestones_reached: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        return cls(**data)


@dataclass
class Task:
    id: str
    label: str
    goal: str
    scheduled_hour: int
    duration_minutes: int
    xp: int
    boss: bool = False
    completed: bool = False
    skipped: bool = False
    source_routine_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # prerequisite routine ids
    locked: bool = False  # True while any dependency is unmet today
    scheduled_date: str = ""  # ISO date - which day's schedule this task lives on
    push_reason: Optional[str] = None  # "skip" | "dependency_push" | "hour_drift" | "eod_rollover" | None
    is_scheduling_task: bool = False  # True for "schedule X" / "RSVP to X" style tasks

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(**data)


@dataclass
class Routine:
    id: str
    label: str
    goal: str
    frequency: str  # "daily" | "weekly" | "monthly" | "every_n_days" | "once"
    time_of_day: Optional[int]
    duration_minutes: int
    xp: int
    boss: bool = False
    interval_days: Optional[int] = None
    last_completed_date: Optional[str] = None  # ISO date string
    requires: List[str] = field(default_factory=list)  # prerequisite routine ids
    missed_dates: List[str] = field(default_factory=list)  # ISO dates this routine went incomplete
    is_scheduling_task: bool = False  # True for "schedule X" / "RSVP to X" style routines

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Routine":
        return cls(**data)


@dataclass
class PlayerState:
    xp: int = 0
    level: int = 1
    streak_days: int = 0
    longest_streak: int = 0
    last_active_date: Optional[str] = None
    energy_mode: str = "normal"
    chaos_mode: bool = False
    comfort_mode: bool = False
    companion_id: str = "sage"
    current_season_id: Optional[str] = None
    inventory: List[str] = field(default_factory=list)
    boss_fights_won: int = 0
    tasks_completed_total: int = 0
    tasks_skipped_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerState":
        return cls(**data)
