"""
Turns goals + due routines into a concrete hourly schedule for today.

Respects:
  - Energy modes (low / normal / high) which cap how many minutes of task
    duration can be packed into a single hour, and the max duration of any
    single task.
  - Chaos Mode: shuffles the schedule and allows more minutes per hour, at a
    higher XP multiplier, for unpredictable days.
  - Comfort Mode: strips the schedule down to essential routines only, at
    a gentle pace, so streaks survive rough days.

Hours are bin-packed by duration rather than task count: an hour holds as
many tasks as fit within its minute budget, and anything that doesn't fit
overflows into the next available hour.
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


def _hour_capacity(state: PlayerState) -> int:
    return _mode_settings(state).get("hour_capacity_minutes", 60)


def _day_hours() -> List[int]:
    return list(range(config.DAY_START_HOUR, config.DAY_END_HOUR + 1))


def _used_minutes(tasks: List[Task], hour: int, exclude_id: Optional[str] = None) -> int:
    return sum(
        t.duration_minutes
        for t in tasks
        if t.scheduled_hour == hour and t.id != exclude_id and not t.skipped
    )


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


def _place_in_hour_or_later(
    tasks: List[Task],
    task: Task,
    hours: List[int],
    capacity: int,
    start_hour: int,
    strictly_after: bool = False,
) -> int:
    """Find the earliest hour at/after `start_hour` (or strictly after, if
    requested) with enough remaining duration budget for `task`. Falls back
    to the last hour of the day (overflow) if nothing fits."""
    if strictly_after:
        candidates = [h for h in hours if h > start_hour]
    else:
        candidates = [h for h in hours if h >= start_hour]
    if not candidates:
        candidates = [hours[-1]]

    for h in candidates:
        if _used_minutes(tasks, h, exclude_id=task.id) + task.duration_minutes <= capacity:
            return h
    return candidates[-1]


def build_daily_schedule(
    goals: List[Goal],
    routines: List[Routine],
    state: PlayerState,
    today: Optional[datetime.date] = None,
) -> List[Task]:
    today = today or datetime.date.today()
    settings = _mode_settings(state)
    xp_multiplier = settings.get("xp_multiplier", 1.0)
    hour_capacity = settings.get("hour_capacity_minutes", 60)
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

    hours = _day_hours()

    # Tasks with a preferred hour get first crack at it; anything unassigned
    # (goal deep-work tasks) fills in starting from the top of the day.
    preferred = [t for t in tasks if t.scheduled_hour != -1 and t.scheduled_hour in hours]
    unassigned = [t for t in tasks if t.scheduled_hour == -1 or t.scheduled_hour not in hours]

    placed: List[Task] = []
    for t in preferred:
        h = _place_in_hour_or_later(placed, t, hours, hour_capacity, t.scheduled_hour)
        t.scheduled_hour = h
        placed.append(t)
    for t in unassigned:
        h = _place_in_hour_or_later(placed, t, hours, hour_capacity, hours[0])
        t.scheduled_hour = h
        placed.append(t)

    placed.sort(key=lambda t: t.scheduled_hour)
    apply_lock_state(placed, routines, today)
    return placed


def insert_task(tasks: List[Task], new_task: Task, preferred_hour: int, state: PlayerState) -> Task:
    """Insert a manually-added task, preferring `preferred_hour` (typically
    the current hour). If that hour's duration budget is full, the new task
    (not the existing ones) is pushed forward to the next hour with room."""
    hours = _day_hours()
    capacity = _hour_capacity(state)
    h = _place_in_hour_or_later(tasks, new_task, hours, capacity, preferred_hour)
    new_task.scheduled_hour = h
    tasks.append(new_task)
    tasks.sort(key=lambda t: t.scheduled_hour)
    return new_task


def reschedule_after_skip(tasks: List[Task], skipped_task: Task, state: PlayerState, today: datetime.date) -> List[Task]:
    """Called when a task that other tasks depend on gets skipped instead of
    completed. Rather than leaving dependents locked indefinitely, the
    skipped prerequisite is deferred to the next open hour, and every task
    (direct or cascading) that depends on it is pushed to occur after that
    new hour, maintaining dependency order across the day.

    Returns the list of tasks that were moved (including `skipped_task`).
    """
    hours = _day_hours()
    capacity = _hour_capacity(state)
    moved: List[Task] = []

    old_hour = skipped_task.scheduled_hour
    new_hour = _place_in_hour_or_later(tasks, skipped_task, hours, capacity, old_hour, strictly_after=True)
    skipped_task.scheduled_hour = new_hour
    skipped_task.skipped = False
    moved.append(skipped_task)

    frontier = [skipped_task]
    visited_ids = {skipped_task.id}

    while frontier:
        current = frontier.pop(0)
        if not current.source_routine_id:
            continue
        for dependent in tasks:
            if dependent.id in visited_ids or dependent.completed:
                continue
            if current.source_routine_id not in dependent.dependencies:
                continue
            visited_ids.add(dependent.id)
            if dependent.scheduled_hour <= current.scheduled_hour:
                new_dep_hour = _place_in_hour_or_later(
                    tasks, dependent, hours, capacity, current.scheduled_hour, strictly_after=True
                )
                dependent.scheduled_hour = new_dep_hour
                moved.append(dependent)
            frontier.append(dependent)

    tasks.sort(key=lambda t: t.scheduled_hour)
    return moved


def pull_task_to_hour(tasks: List[Task], task: Task, target_hour: int, state: PlayerState) -> Task:
    """Pull a later task into `target_hour` (typically 'now'). If the task
    itself depends on a still-incomplete prerequisite that hasn't happened
    yet, that prerequisite is pulled forward first (recursively) so the
    dependent never lands at or before its own prerequisite."""
    hours = _day_hours()
    capacity = _hour_capacity(state)

    effective_hour = target_hour
    for dep_id in task.dependencies:
        prereq_task = next(
            (t for t in tasks if t.source_routine_id == dep_id and not t.completed), None
        )
        if prereq_task is None:
            continue
        if prereq_task.scheduled_hour > effective_hour:
            pull_task_to_hour(tasks, prereq_task, target_hour, state)
        effective_hour = max(effective_hour, prereq_task.scheduled_hour)

    new_hour = _place_in_hour_or_later(tasks, task, hours, capacity, effective_hour)
    task.scheduled_hour = new_hour
    tasks.sort(key=lambda t: t.scheduled_hour)
    return task


def push_overdue_to_current_hour(
    tasks: List[Task], overdue: List[Task], current_hour: int, state: PlayerState
) -> List[Task]:
    """Push tasks left incomplete in past hours into the current hour,
    reflowing (bin-packing) forward as needed. Prerequisite tasks are
    placed before their dependents so dependency order survives the push -
    this applies uniformly to routines, manual tasks, boss fights, and
    prerequisite/dependent tasks alike."""
    hours = _day_hours()
    capacity = _hour_capacity(state)

    # Tasks without their own dependencies (candidate prerequisites) get
    # placed first so any co-overdue dependents land at/after them.
    ordered = sorted(overdue, key=lambda t: bool(t.dependencies))

    moved: List[Task] = []
    for t in ordered:
        new_hour = _place_in_hour_or_later(tasks, t, hours, capacity, current_hour)
        if new_hour != t.scheduled_hour:
            t.scheduled_hour = new_hour
            moved.append(t)

    tasks.sort(key=lambda t: t.scheduled_hour)
    return moved


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
