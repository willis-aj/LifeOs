"""
Turns goals + due routines into a concrete hourly schedule for today.

Respects:
  - Energy modes (low / normal / high) which cap tasks-per-hour and the
    max duration of any single task.
  - Chaos Mode: shuffles the schedule and allows more tasks per hour, at a
    higher XP multiplier, for unpredictable days.
  - Comfort Mode: strips the schedule down to essential routines only, at
    a gentle pace, so streaks survive rough days.
"""

from __future__ import annotations

import datetime
import random
from typing import List, Optional

from . import config
from .models import Goal, PlayerState, Routine, Task
from .routines import due_routines


def _mode_settings(state: PlayerState) -> dict:
    if state.chaos_mode:
        return dict(config.CHAOS_MODE)
    if state.comfort_mode:
        return dict(config.COMFORT_MODE)
    return dict(config.ENERGY_MODES.get(state.energy_mode, config.ENERGY_MODES["normal"]))


def _routine_to_task(routine: Routine, today: datetime.date, xp_multiplier: float) -> Task:
    return Task(
        id=f"routine-{routine.id}-{today.isoformat()}",
        label=routine.label,
        goal=routine.goal,
        scheduled_hour=routine.time_of_day if routine.time_of_day is not None else -1,
        duration_minutes=routine.duration_minutes,
        xp=round(routine.xp * xp_multiplier),
        boss=routine.boss,
        source_routine_id=routine.id,
        dependencies=list(routine.requires),
    )


def is_locked(dependencies: List[str], routines_by_id: dict, today: datetime.date) -> bool:
    """A task is locked while any prerequisite routine hasn't been completed
    today. Unknown dependency ids are ignored rather than treated as blockers."""
    for dep_id in dependencies:
        dep_routine = routines_by_id.get(dep_id)
        if dep_routine is None:
            continue
        if dep_routine.last_completed_date != today.isoformat():
            return True
    return False


def apply_lock_state(tasks: List[Task], routines: List[Routine], today: datetime.date) -> None:
    """Recompute `task.locked` for every task with dependencies, in place."""
    routines_by_id = {r.id: r for r in routines}
    for task in tasks:
        if task.dependencies:
            task.locked = is_locked(task.dependencies, routines_by_id, today)
        else:
            task.locked = False


def _goal_tasks(goals: List[Goal], today: datetime.date, xp_multiplier: float) -> List[Task]:
    tasks: List[Task] = []
    for goal in goals:
        for i in range(config.GOAL_TASKS_PER_DAY):
            tasks.append(
                Task(
                    id=f"goal-{goal.id}-{today.isoformat()}-{i}",
                    label=f"Work on: {goal.name}",
                    goal=goal.id,
                    scheduled_hour=-1,  # unassigned, filled in by build_daily_schedule
                    duration_minutes=45,
                    xp=round(goal.base_xp_per_task * xp_multiplier),
                    boss=False,
                    source_routine_id=None,
                )
            )
    return tasks


def build_daily_schedule(
    goals: List[Goal],
    routines: List[Routine],
    state: PlayerState,
    today: Optional[datetime.date] = None,
) -> List[Task]:
    today = today or datetime.date.today()
    settings = _mode_settings(state)
    xp_multiplier = settings.get("xp_multiplier", 1.0)
    max_per_hour = settings.get("max_tasks_per_hour", 1)
    duration_cap = settings.get("task_duration_cap_minutes")

    due = due_routines(routines, today)
    if settings.get("only_essentials"):
        due = [r for r in due if r.id in config.ESSENTIAL_ROUTINE_IDS]

    tasks = [_routine_to_task(r, today, xp_multiplier) for r in due]

    if not settings.get("only_essentials"):
        tasks.extend(_goal_tasks(goals, today, xp_multiplier))

    if duration_cap is not None:
        for t in tasks:
            t.duration_minutes = min(t.duration_minutes, duration_cap)

    if settings.get("shuffle"):
        random.shuffle(tasks)

    hours = list(range(config.DAY_START_HOUR, config.DAY_END_HOUR + 1))
    slot_counts = {h: 0 for h in hours}

    preferred = [t for t in tasks if t.scheduled_hour != -1 and t.scheduled_hour in slot_counts]
    unassigned = [t for t in tasks if t.scheduled_hour == -1 or t.scheduled_hour not in slot_counts]

    for t in preferred:
        h = t.scheduled_hour
        if slot_counts[h] < max_per_hour:
            slot_counts[h] += 1
        else:
            # Preferred hour is full: bump to the next open hour.
            placed = False
            for candidate in hours:
                if slot_counts[candidate] < max_per_hour:
                    t.scheduled_hour = candidate
                    slot_counts[candidate] += 1
                    placed = True
                    break
            if not placed:
                t.scheduled_hour = hours[-1]

    for t in unassigned:
        placed = False
        for candidate in hours:
            if slot_counts[candidate] < max_per_hour:
                t.scheduled_hour = candidate
                slot_counts[candidate] += 1
                placed = True
                break
        if not placed:
            t.scheduled_hour = hours[-1]

    tasks.sort(key=lambda t: t.scheduled_hour)
    apply_lock_state(tasks, routines, today)
    return tasks


def current_hour_tasks(tasks: List[Task], hour: Optional[int] = None) -> List[Task]:
    hour = hour if hour is not None else datetime.datetime.now().hour
    return [t for t in tasks if t.scheduled_hour == hour and not t.completed and not t.skipped]


def next_upcoming_task(tasks: List[Task], hour: Optional[int] = None) -> Optional[Task]:
    hour = hour if hour is not None else datetime.datetime.now().hour
    pending = [t for t in tasks if not t.completed and not t.skipped]
    if not pending:
        return None
    same_hour_or_later = [t for t in pending if t.scheduled_hour >= hour]
    if same_hour_or_later:
        return sorted(same_hour_or_later, key=lambda t: t.scheduled_hour)[0]
    return sorted(pending, key=lambda t: t.scheduled_hour)[0]
