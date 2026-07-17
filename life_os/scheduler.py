"""
Turns goals + due routines into a concrete multi-day schedule.

A player's full schedule is a `Dict[str, List[Task]]` keyed by ISO date
string - `engine.py` exposes "today's" list as `self.tasks`, but everything
in here that moves a task around operates against the whole multi-day
`schedule` dict, because a task that can't fit today needs somewhere to
roll to.

Respects:
  - Energy modes (low / normal / high) which cap how many minutes of task
    duration can be packed into a single hour, and the max duration of any
    single task.
  - Chaos Mode: shuffles the schedule and allows more minutes per hour, at a
    higher XP multiplier, for unpredictable days.
  - Comfort Mode: strips the schedule down to essential routines only, at
    a gentle pace, so streaks survive rough days.

Hours are bin-packed by duration rather than task count: an hour holds as
many tasks as fit within its minute budget. The core primitive, `place_task`,
is a *rolling* placement: if a task doesn't fit anywhere left today, it rolls
into tomorrow (starting from the top of the day) rather than piling
everything that overflows into a single late hour.
"""

from __future__ import annotations

import datetime
import random
from typing import Dict, List, Optional, Tuple

from . import config
from .models import Goal, PlayerState, Routine, Task
from .routines import due_routines

MAX_ROLLOVER_DAYS_AHEAD = 21


def _mode_settings(state: PlayerState) -> dict:
    if state.chaos_mode:
        return dict(config.CHAOS_MODE)
    if state.comfort_mode:
        return dict(config.COMFORT_MODE)
    return dict(config.ENERGY_MODES.get(state.energy_mode, config.ENERGY_MODES["normal"]))


def _hour_capacity(state: PlayerState) -> int:
    return _mode_settings(state).get("hour_capacity_minutes", 60)


def hour_capacity(state: PlayerState) -> int:
    """Public accessor for the current mode's per-hour minute budget, so
    callers building ad-hoc tasks (manual tasks, scheduled events) can cap
    duration to something that can actually fit in an hour."""
    return _hour_capacity(state)


def _day_hours() -> List[int]:
    return list(range(config.DAY_START_HOUR, config.DAY_END_HOUR + 1))


def _date_key(d: datetime.date) -> str:
    return d.isoformat()


def _used_minutes_in_list(task_list: List[Task], hour: int, exclude_id: Optional[str] = None) -> int:
    return sum(
        t.duration_minutes
        for t in task_list
        if t.scheduled_hour == hour and t.id != exclude_id and not t.skipped
    )


def _routine_to_task(routine: Routine, today: datetime.date, xp_multiplier: float) -> Task:
    return Task(
        id=f"routine-{routine.id}-{today.isoformat()}",
        label=routine.label,
        goal=routine.goal,
        scheduled_hour=routine.time_of_day if routine.time_of_day is not None else -1,
        scheduled_date=today.isoformat(),
        duration_minutes=routine.duration_minutes,
        xp=round(routine.xp * xp_multiplier),
        boss=routine.boss,
        source_routine_id=routine.id,
        dependencies=list(routine.requires),
        is_scheduling_task=routine.is_scheduling_task,
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
                    scheduled_date=today.isoformat(),
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


def ensure_prerequisites_present(
    schedule: Dict[str, List[Task]], routines: List[Routine], state: PlayerState, today: datetime.date
) -> List[Tuple[str, str]]:
    """Guarantee every dependency referenced by a task in today's schedule
    actually has a prerequisite task present somewhere in the schedule.

    A routine can be due today while its own prerequisite isn't (different
    cadences) - `due_routines` has no idea the two are linked, so a
    dependent like "Cook dinner" could otherwise appear with "Grocery
    shopping" nowhere on the schedule, leaving it locked with no way to
    ever unlock. For anything missing, this synthesizes the prerequisite
    task, inserts it at the earliest available slot today (rolling to
    tomorrow if today's full, via the same bin-packing `place_task` uses
    everywhere else), and pushes the dependent to occur no earlier than
    it. Works the same regardless of whether the dependent is a daily
    routine, a manual task, a pulled-forward task, a scheduled event, or a
    boss fight - dependencies are just a list of routine ids on the Task.

    Returns (prerequisite_label, dependent_label) pairs for anything that
    had to be fixed, so the caller can tell the user about it.
    """
    today_key = _date_key(today)
    today_tasks = schedule.get(today_key, [])
    routines_by_id = {r.id: r for r in routines}
    capacity = _hour_capacity(state)
    settings = _mode_settings(state)
    xp_multiplier = settings.get("xp_multiplier", 1.0)

    known_source_ids = {
        t.source_routine_id for day_tasks in schedule.values() for t in day_tasks if t.source_routine_id
    }

    fixes: List[Tuple[str, str]] = []

    for dependent in list(today_tasks):
        if dependent.completed or not dependent.dependencies:
            continue
        for dep_id in dependent.dependencies:
            if dep_id in known_source_ids:
                continue
            dep_routine = routines_by_id.get(dep_id)
            if dep_routine is None:
                continue

            prereq_task = _routine_to_task(dep_routine, today, xp_multiplier)
            place_task(schedule, prereq_task, today, config.DAY_START_HOUR, capacity)
            known_source_ids.add(dep_id)
            fixes.append((dep_routine.label, dependent.label))

            prereq_date = datetime.date.fromisoformat(prereq_task.scheduled_date)
            dependent_date_key = dependent.scheduled_date or today_key
            if (dependent_date_key, dependent.scheduled_hour) <= (prereq_task.scheduled_date, prereq_task.scheduled_hour):
                place_task(schedule, dependent, prereq_date, prereq_task.scheduled_hour, capacity, strictly_after=True)

    return fixes


# ---------------------------------------------------------------------------
# Core rolling placement
# ---------------------------------------------------------------------------

def _remove_from_schedule(schedule: Dict[str, List[Task]], task: Task) -> None:
    old_date = task.scheduled_date
    if old_date and old_date in schedule:
        schedule[old_date] = [t for t in schedule[old_date] if t.id != task.id]


def place_task(
    schedule: Dict[str, List[Task]],
    task: Task,
    start_date: datetime.date,
    start_hour: int,
    capacity: int,
    strictly_after: bool = False,
) -> None:
    """Find room for `task`, starting from `start_hour` on `start_date` and
    spreading across the remaining hours of that day (duration-based
    bin-packing). If the day has no more room, rolls into the next day
    (from its own top-of-day) instead of piling everything into whatever
    hour is left open - this is what prevents pushed tasks from all
    stacking up at 11pm (or wherever the last slot happens to be).

    Mutates `task.scheduled_date` / `task.scheduled_hour` and inserts it
    into the right day's list in `schedule`, removing it from wherever it
    used to live first.
    """
    _remove_from_schedule(schedule, task)

    hours = _day_hours()
    day = start_date

    for day_offset in range(MAX_ROLLOVER_DAYS_AHEAD):
        date_key = _date_key(day)
        day_tasks = schedule.get(date_key, [])

        if day_offset == 0:
            candidates = [h for h in hours if (h > start_hour if strictly_after else h >= start_hour)]
        else:
            candidates = hours

        for h in candidates:
            used = _used_minutes_in_list(day_tasks, h, exclude_id=task.id)
            if used + task.duration_minutes <= capacity:
                task.scheduled_date = date_key
                task.scheduled_hour = h
                schedule.setdefault(date_key, []).append(task)
                schedule[date_key].sort(key=lambda t: t.scheduled_hour)
                return

        day = day + datetime.timedelta(days=1)

    # Exhausted the lookahead window (shouldn't normally happen) - force
    # placement on the last day/hour checked so nothing is silently lost.
    date_key = _date_key(day)
    task.scheduled_date = date_key
    task.scheduled_hour = hours[-1]
    schedule.setdefault(date_key, []).append(task)
    schedule[date_key].sort(key=lambda t: t.scheduled_hour)


# ---------------------------------------------------------------------------
# Building a fresh day
# ---------------------------------------------------------------------------

def _is_generated_task(task: Task, date_key: str) -> bool:
    """True if `task` is a routine/goal task originally generated for
    `date_key` (as opposed to a manually-added, pulled-forward, or
    rolled-over task). Checks the task id - which embeds its *generation*
    date and never changes - rather than `scheduled_date`, which drifts
    whenever the task gets rescheduled or rolled onto a different day."""
    return (task.id.startswith("routine-") or task.id.startswith("goal-")) and date_key in task.id


def build_daily_schedule(
    schedule: Dict[str, List[Task]],
    goals: List[Goal],
    routines: List[Routine],
    state: PlayerState,
    today: Optional[datetime.date] = None,
    force: bool = False,
) -> List[Task]:
    """Populate `schedule[today]` with routine/goal tasks, unless that day
    was already built (idempotent, so re-running an engine session doesn't
    duplicate anything) - pass `force=True` (e.g. after a mode switch) to
    regenerate pending routine/goal tasks while keeping anything completed,
    skipped, manually-added, pulled-forward, or rolled over from a
    previous day."""
    today = today or datetime.date.today()
    date_key = _date_key(today)
    existing = schedule.get(date_key, [])
    already_built = any(_is_generated_task(t, date_key) for t in existing)

    if already_built and not force:
        apply_lock_state(existing, routines, today)
        return existing

    if force:
        existing = [
            t for t in existing
            if t.completed or t.skipped or not _is_generated_task(t, date_key)
        ]
        schedule[date_key] = existing

    settings = _mode_settings(state)
    xp_multiplier = settings.get("xp_multiplier", 1.0)
    hour_capacity = settings.get("hour_capacity_minutes", 60)
    duration_cap = settings.get("task_duration_cap_minutes")

    due = due_routines(routines, today)
    if settings.get("only_essentials"):
        due = [r for r in due if r.id in config.ESSENTIAL_ROUTINE_IDS]

    # A routine with no completion history is always "due" (see is_due()),
    # so without this guard a pending instance sitting anywhere in the
    # schedule (e.g. carried forward from a previous day, and now possibly
    # living on today's own list) would get a second, freshly-generated
    # copy the moment a new day is built. (When force-rebuilding today's
    # pending routine tasks after a mode switch, they've already been
    # stripped from `schedule[date_key]` above, so this still lets them
    # regenerate normally.)
    pending_routine_ids = {
        t.source_routine_id
        for day_tasks in schedule.values()
        for t in day_tasks
        if t.source_routine_id and not t.completed and not t.skipped
    }
    due = [r for r in due if r.id not in pending_routine_ids]

    new_tasks = [_routine_to_task(r, today, xp_multiplier) for r in due]

    if not settings.get("only_essentials"):
        new_tasks.extend(_goal_tasks(goals, today, xp_multiplier))

    if duration_cap is not None:
        for t in new_tasks:
            t.duration_minutes = min(t.duration_minutes, duration_cap)

    if settings.get("shuffle"):
        random.shuffle(new_tasks)

    preferred = [t for t in new_tasks if t.scheduled_hour != -1]
    unassigned = [t for t in new_tasks if t.scheduled_hour == -1]

    schedule.setdefault(date_key, [])
    for t in preferred:
        place_task(schedule, t, today, t.scheduled_hour, hour_capacity)
    for t in unassigned:
        place_task(schedule, t, today, config.DAY_START_HOUR, hour_capacity)

    apply_lock_state(schedule[date_key], routines, today)
    return schedule[date_key]


# ---------------------------------------------------------------------------
# Manual insertion / pulling a later task forward
# ---------------------------------------------------------------------------

def insert_task(
    schedule: Dict[str, List[Task]], new_task: Task, today: datetime.date, preferred_hour: int, state: PlayerState
) -> Task:
    """Insert a manually-added task, preferring `preferred_hour` (typically
    the current hour) and rolling forward (today, then tomorrow, ...) if
    that hour's duration budget is already full."""
    capacity = _hour_capacity(state)
    place_task(schedule, new_task, today, preferred_hour, capacity)
    return new_task


def pull_task_to_hour(
    schedule: Dict[str, List[Task]], task: Task, today: datetime.date, target_hour: int, state: PlayerState
) -> Task:
    """Pull a later task into `target_hour` (typically 'now'). If the task
    itself depends on a still-incomplete prerequisite that hasn't happened
    yet, that prerequisite is pulled forward first (recursively) so the
    dependent never lands at or before its own prerequisite."""
    capacity = _hour_capacity(state)
    today_tasks = schedule.get(_date_key(today), [])

    effective_hour = target_hour
    for dep_id in task.dependencies:
        prereq_task = next(
            (t for t in today_tasks if t.source_routine_id == dep_id and not t.completed), None
        )
        if prereq_task is None:
            continue
        if prereq_task.scheduled_hour > effective_hour:
            place_task(schedule, prereq_task, today, target_hour, capacity)
        effective_hour = max(effective_hour, prereq_task.scheduled_hour)

    place_task(schedule, task, today, effective_hour, capacity)
    return task


# ---------------------------------------------------------------------------
# Skip -> reschedule cascade
# ---------------------------------------------------------------------------

def reschedule_after_skip(
    schedule: Dict[str, List[Task]], skipped_task: Task, state: PlayerState, today: datetime.date
) -> List[Task]:
    """Called when a task that other tasks depend on gets skipped instead of
    completed. Rather than leaving dependents locked indefinitely, the
    skipped prerequisite is deferred to the next open slot (rolling into
    tomorrow if today's full), and every task (direct or cascading) that
    depends on it is pushed to occur after that new slot, maintaining
    dependency order across the day (and across days, if it rolled over).

    Returns the list of tasks that were moved (including `skipped_task`).
    """
    capacity = _hour_capacity(state)
    moved: List[Task] = [skipped_task]

    old_hour = skipped_task.scheduled_hour
    old_date = datetime.date.fromisoformat(skipped_task.scheduled_date) if skipped_task.scheduled_date else today
    place_task(schedule, skipped_task, old_date, old_hour, capacity, strictly_after=True)
    skipped_task.skipped = False
    skipped_task.push_reason = "skip"

    frontier = [skipped_task]
    visited_ids = {skipped_task.id}

    while frontier:
        current = frontier.pop(0)
        if not current.source_routine_id:
            continue
        # Dependents may have rolled onto a different day than their
        # prerequisite, so cascade across the whole schedule, not just today.
        search_pool = [t for day_tasks in schedule.values() for t in day_tasks]
        for dependent in search_pool:
            if dependent.id in visited_ids or dependent.completed:
                continue
            if current.source_routine_id not in dependent.dependencies:
                continue
            visited_ids.add(dependent.id)
            current_date = datetime.date.fromisoformat(current.scheduled_date)
            dependent_date_key = dependent.scheduled_date or _date_key(today)
            if (dependent_date_key, dependent.scheduled_hour) <= (current.scheduled_date, current.scheduled_hour):
                place_task(schedule, dependent, current_date, current.scheduled_hour, capacity, strictly_after=True)
                dependent.push_reason = "dependency_push"
                moved.append(dependent)
            frontier.append(dependent)

    return moved


# ---------------------------------------------------------------------------
# Hour-drift: pushing overdue tasks into the current hour
# ---------------------------------------------------------------------------

def push_overdue_to_current_hour(
    schedule: Dict[str, List[Task]], overdue: List[Task], current_hour: int, today: datetime.date, state: PlayerState
) -> List[Task]:
    """Push tasks left incomplete in past hours into the current hour,
    rolling across the rest of today (and into tomorrow if today's out of
    room) rather than cramming them all into one slot. Prerequisite tasks
    are placed before their dependents so dependency order survives - this
    applies uniformly to routines, manual tasks, boss fights, and
    prerequisite/dependent tasks alike."""
    capacity = _hour_capacity(state)

    # Tasks without their own dependencies (candidate prerequisites) get
    # placed first so any co-overdue dependents land at/after them.
    ordered = sorted(overdue, key=lambda t: bool(t.dependencies))

    moved: List[Task] = []
    for t in ordered:
        old_hour, old_date = t.scheduled_hour, t.scheduled_date
        place_task(schedule, t, today, current_hour, capacity)
        if t.scheduled_hour != old_hour or t.scheduled_date != old_date:
            t.push_reason = "hour_drift"
            moved.append(t)

    return moved


# ---------------------------------------------------------------------------
# End-of-day rollover
# ---------------------------------------------------------------------------

def rollover_to_next_day(
    schedule: Dict[str, List[Task]],
    routines: List[Routine],
    state: PlayerState,
    today: datetime.date,
) -> Dict[str, List[str]]:
    """Called when the real calendar date has advanced past `today`. Any
    task still incomplete (not completed, not skipped) in today's list is
    handled as follows:
      - If it came from a DAILY routine, it's left behind marked as missed
        (the caller records this in the routine's history) rather than
        duplicated - tomorrow's schedule gets its own fresh instance of
        that routine normally, once.
      - Everything else (weekly/monthly/every-N-days/one-time scheduling
        routines, manual tasks, boss fights, and dependency chains) rolls
        into tomorrow's schedule, bin-packed and dependency-ordered like
        any other push. `build_daily_schedule`'s pending-routine guard
        keeps this from ever duplicating even for never-yet-completed
        routines.

    Returns {"carried": [task ids moved], "missed_daily_routine_ids": [...]}.
    """
    today_key = _date_key(today)
    tomorrow = today + datetime.timedelta(days=1)
    today_tasks = schedule.get(today_key, [])

    routines_by_id = {r.id: r for r in routines}
    capacity = _hour_capacity(state)

    carried: List[Task] = []
    missed_daily_routine_ids: List[str] = []
    remaining_today: List[Task] = []

    for t in today_tasks:
        if t.completed or t.skipped:
            remaining_today.append(t)
            continue

        routine = routines_by_id.get(t.source_routine_id) if t.source_routine_id else None
        if routine is not None and routine.frequency == "daily":
            # Leave the missed instance in today's history; don't carry it.
            remaining_today.append(t)
            missed_daily_routine_ids.append(routine.id)
        else:
            carried.append(t)

    schedule[today_key] = remaining_today

    # Prerequisites before dependents, so cross-day ordering still holds.
    ordered = sorted(carried, key=lambda t: bool(t.dependencies))
    for t in ordered:
        t.push_reason = "eod_rollover"
        place_task(schedule, t, tomorrow, config.DAY_START_HOUR, capacity)

    return {
        "carried": [t.id for t in carried],
        "missed_daily_routine_ids": missed_daily_routine_ids,
    }


def find_task_by_id(schedule: Dict[str, List[Task]], task_id: str) -> Optional[Task]:
    """Locate a task by id anywhere in the multi-day schedule. Used when a
    task is chosen from a selection menu (e.g. multiple tasks sharing an
    hour) rather than passed around as an object."""
    for day_tasks in schedule.values():
        for t in day_tasks:
            if t.id == task_id:
                return t
    return None


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
