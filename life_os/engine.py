"""
LifeOSEngine: the orchestrator that ties config, models, persistence,
scheduler, routines, and gamification together behind a small, CLI-friendly
API.

`cli.py` should not need to import anything except this module (plus maybe
`config` for display labels). All engine state is scoped to a single
`player_id` - callers select or create a player via `persistence.list_players()`
/ `persistence.create_player()` before constructing an engine.

The full schedule (`self.schedule`) spans multiple days - `self.tasks` is a
thin property proxy onto `self.schedule[today]` so the rest of the engine
(and all existing callers) can keep treating "today's tasks" as a plain
list, while pushed/rolled-over tasks land on whichever day actually has
room.
"""

from __future__ import annotations

import calendar
import datetime
import random
import uuid
import zlib
from typing import Dict, List, Optional, Tuple

from . import config, gamification, persistence, scheduler
from . import routines as routines_mod
from .models import Goal, PlayerState, Routine, Task

NON_BOSS_LOOT_CHANCE = 0.35


class LifeOSEngine:
    def __init__(self, player_id: str, today: Optional[datetime.date] = None):
        self.player_id = player_id
        self.player_name = persistence.load_player_meta(player_id).get("name", player_id)
        self.today = today or datetime.date.today()

        self.state: PlayerState = persistence.load_player_state(player_id)
        self.goals: List[Goal] = persistence.load_goals(player_id)
        self.routines: List[Routine] = persistence.load_routines(player_id)
        self.schedule: Dict[str, List[Task]] = persistence.load_schedule(player_id)
        self.last_dependency_fixes: List[Tuple[str, str]] = []

        gamification.sync_season(self.state, self.today)

        scheduler.build_daily_schedule(self.schedule, self.goals, self.routines, self.state, self.today)
        self.reconcile_dependencies()
        self.refresh_locks()
        self.save()

    @classmethod
    def create_new_player(cls, name: str, today: Optional[datetime.date] = None) -> "LifeOSEngine":
        """Convenience for the CLI's first-run flow: create the player
        directory and state files via persistence, then construct and
        return a fully initialized engine for them - ready to show the
        main home screen immediately."""
        player_id = persistence.create_player(name)
        return cls(player_id, today=today)

    @staticmethod
    def delete_player(player_id: str) -> None:
        """Permanently delete a player and all of their data. This is a
        thin, explicit wrapper around persistence.delete_player() - it
        doesn't operate on `self` since the player being deleted might not
        even be the one currently loaded (e.g. deleting someone else from
        the player-selection screen). All of the actual safety checks live
        in persistence.delete_player()."""
        persistence.delete_player(player_id)

    # ------------------------------------------------------------------
    # Today's tasks - a view onto self.schedule
    # ------------------------------------------------------------------

    @property
    def tasks(self) -> List[Task]:
        return self.schedule.setdefault(self.today.isoformat(), [])

    @tasks.setter
    def tasks(self, value: List[Task]) -> None:
        self.schedule[self.today.isoformat()] = value

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def rebuild_schedule(self) -> None:
        """Regenerate today's routine/goal tasks (e.g. after a mode switch),
        preserving completed/skipped tasks and anything manually-added,
        pulled-forward, or rolled over from a previous day."""
        scheduler.build_daily_schedule(
            self.schedule, self.goals, self.routines, self.state, self.today, force=True
        )
        self.reconcile_dependencies()
        persistence.save_schedule(self.player_id, self.schedule)

    def refresh_locks(self) -> None:
        scheduler.apply_lock_state(self.tasks, self.routines, self.today)

    def reconcile_dependencies(self) -> List[Tuple[str, str]]:
        """Ensure every dependency referenced by today's tasks actually has
        a prerequisite task present somewhere in the schedule. A routine
        can be due on a day its own prerequisite isn't (different
        cadences), which would otherwise leave a dependent locked with no
        way to ever unlock today. Inserts any missing prerequisite at the
        earliest available slot (rolling to tomorrow if today's full) and
        keeps the dependent ordered after it. Returns
        (prerequisite_label, dependent_label) pairs for anything that had
        to be fixed, so the caller can surface it to the user."""
        fixes = scheduler.ensure_prerequisites_present(self.schedule, self.routines, self.state, self.today)
        self.last_dependency_fixes = fixes
        if fixes:
            self.refresh_locks()
            self.save()
        return fixes

    def check_for_new_day(self) -> Dict:
        """Detect whether the real calendar date has advanced since this
        engine's `self.today`. If so, roll over each day's unfinished
        schedule in turn (see `scheduler.rollover_to_next_day`) and advance
        the engine to the new day. Returns a summary for the CLI to report."""
        real_today = datetime.date.today()
        summary = {"rolled_over": False, "days_advanced": 0, "carried_count": 0}
        if real_today <= self.today:
            return summary

        while self.today < real_today:
            result = scheduler.rollover_to_next_day(self.schedule, self.routines, self.state, self.today)
            for routine_id in result["missed_daily_routine_ids"]:
                routine = self.routine_by_id(routine_id)
                if routine is not None and self.today.isoformat() not in routine.missed_dates:
                    routine.missed_dates.append(self.today.isoformat())
            summary["rolled_over"] = True
            summary["days_advanced"] += 1
            summary["carried_count"] += len(result["carried"])
            self.today = self.today + datetime.timedelta(days=1)

        gamification.sync_season(self.state, self.today)
        scheduler.build_daily_schedule(self.schedule, self.goals, self.routines, self.state, self.today)
        summary["dependency_fixes"] = self.reconcile_dependencies()
        self.refresh_locks()
        self.save()
        return summary

    def reflow_overdue_tasks(self) -> List[Task]:
        """Detect any incomplete tasks left behind in past hours (the user
        didn't get to them before the hour moved on) and roll them forward -
        across the rest of today, into tomorrow if today's out of room -
        the same way regardless of whether the overdue task is a routine, a
        manually-added task, a boss fight, or part of a dependency chain.
        Returns the tasks that were moved (empty if nothing was overdue)."""
        current_hour = datetime.datetime.now().hour
        overdue = [
            t for t in self.tasks
            if not t.completed and not t.skipped and t.scheduled_hour < current_hour
        ]
        if not overdue:
            return []
        moved = scheduler.push_overdue_to_current_hour(self.schedule, overdue, current_hour, self.today, self.state)
        self.refresh_locks()
        self.save()
        return moved

    def home_view(self) -> Dict:
        """Snapshot for the main home screen: the current hour plus
        whatever's scheduled in it. Used by the CLI's universal [h]ome
        command to redraw the main screen from any submenu without
        disturbing the schedule or task pointers."""
        current_hour = datetime.datetime.now().hour
        return {
            "hour": current_hour,
            "tasks": self.hour_tasks(current_hour),
        }

    def later_today_tasks(self, hour: Optional[int] = None) -> List[Task]:
        """Pending tasks scheduled strictly after the given (or current)
        hour today, in schedule order - candidates for pulling forward."""
        hour = hour if hour is not None else datetime.datetime.now().hour
        return sorted(
            (t for t in self.tasks if not t.completed and not t.skipped and t.scheduled_hour > hour),
            key=lambda t: t.scheduled_hour,
        )

    def pull_task_forward(self, task: Task, hour: Optional[int] = None) -> Task:
        """Move a later task into the current (or given) hour, reflowing
        the schedule and pulling any of its own unmet prerequisites forward
        too so dependency order is preserved."""
        target_hour = hour if hour is not None else datetime.datetime.now().hour
        scheduler.pull_task_to_hour(self.schedule, task, self.today, target_hour, self.state)
        self.refresh_locks()
        self.save()
        return task

    def add_manual_task(
        self,
        label: str,
        duration_minutes: int,
        goal_id: Optional[str] = None,
        xp: Optional[int] = None,
        hour: Optional[int] = None,
    ) -> Task:
        """Manually insert an ad-hoc task into today's schedule, preferring
        the given (or current) hour. Falls back to the first goal if none
        is specified, since every task needs a goal to award XP against."""
        label = label.strip()
        if not label:
            raise ValueError("Task label cannot be empty.")
        if duration_minutes <= 0:
            raise ValueError("Duration must be a positive number of minutes.")
        duration_minutes = min(duration_minutes, scheduler.hour_capacity(self.state))

        goal = self.goal_by_id(goal_id) if goal_id else None
        if goal is None:
            goal = self.goals[0]

        xp_value = xp if xp is not None else max(5, round(duration_minutes / 3))
        target_hour = hour if hour is not None else datetime.datetime.now().hour

        task = Task(
            id=f"manual-{self.today.isoformat()}-{uuid.uuid4().hex[:8]}",
            label=label,
            goal=goal.id,
            scheduled_hour=target_hour,
            duration_minutes=duration_minutes,
            xp=xp_value,
            boss=False,
            source_routine_id=None,
        )
        scheduler.insert_task(self.schedule, task, self.today, target_hour, self.state)
        self.refresh_locks()
        self.save()
        return task

    def create_scheduled_event(
        self,
        event_date: datetime.date,
        label: Optional[str] = None,
        hour: Optional[int] = None,
        duration_minutes: int = 60,
        goal_id: Optional[str] = None,
        xp: Optional[int] = None,
        boss: bool = False,
    ) -> Task:
        """Create the "actual event" for a completed scheduling task (e.g.
        the real dinner, raid, or appointment) on a chosen future date. It's
        a genuinely one-off Task - not tied to any routine - so it behaves
        exactly like a manual task: bin-packed, dependency-aware (should it
        ever gain dependencies), editable via goal edits, and eligible for
        XP and boss-fight rewards, and it naturally surfaces in day/month/
        backlog views once inserted."""
        label = (label or "Scheduled event").strip() or "Scheduled event"
        if duration_minutes <= 0:
            raise ValueError("Duration must be a positive number of minutes.")
        duration_minutes = min(duration_minutes, scheduler.hour_capacity(self.state))

        goal = self.goal_by_id(goal_id) if goal_id else None
        if goal is None:
            goal = self.goals[0]

        xp_value = xp if xp is not None else max(10, round(duration_minutes / 2))
        target_hour = hour if hour is not None else config.DAY_START_HOUR

        task = Task(
            id=f"event-{event_date.isoformat()}-{uuid.uuid4().hex[:8]}",
            label=label,
            goal=goal.id,
            scheduled_hour=target_hour,
            duration_minutes=duration_minutes,
            xp=xp_value,
            boss=boss,
            source_routine_id=None,
        )
        scheduler.insert_task(self.schedule, task, event_date, target_hour, self.state)
        self.refresh_locks()
        self.save()
        return task

    def day_view(self) -> List[Dict]:
        """Group today's tasks by hour for a full-day overview."""
        by_hour: Dict[int, List[Task]] = {}
        for t in self.tasks:
            by_hour.setdefault(t.scheduled_hour, []).append(t)
        return [{"hour": h, "tasks": by_hour[h]} for h in sorted(by_hour)]

    def backlog_view(self) -> Dict:
        """Snapshot of everything that's been pushed forward today, plus
        what's already lined up for tomorrow and later this week - for the
        CLI's [b]acklog view."""
        today_key = self.today.isoformat()

        pushed_today = [
            t for t in self.schedule.get(today_key, [])
            if t.push_reason and not t.completed
        ]

        tomorrow_key = (self.today + datetime.timedelta(days=1)).isoformat()
        tomorrow_tasks = sorted(
            (t for t in self.schedule.get(tomorrow_key, []) if not t.completed),
            key=lambda t: t.scheduled_hour,
        )

        later_this_week: List[Dict] = []
        day = self.today + datetime.timedelta(days=2)
        week_end = self.today + datetime.timedelta(days=7)
        while day <= week_end:
            key = day.isoformat()
            day_tasks = sorted(
                (t for t in self.schedule.get(key, []) if not t.completed),
                key=lambda t: t.scheduled_hour,
            )
            if day_tasks:
                later_this_week.append({"date": key, "tasks": day_tasks})
            day += datetime.timedelta(days=1)

        return {
            "pushed_today": pushed_today,
            "tomorrow": tomorrow_tasks,
            "later_this_week": later_this_week,
        }

    def month_view(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict:
        """Project recurring routines onto a calendar month so the CLI can
        show a month-at-a-glance of boss fights, social/medical events,
        raids, journaling, and other non-daily routines. Each routine lands
        on a deterministic (id-derived) day each cycle, since routines don't
        track an explicit calendar anchor - it's a stable approximation, not
        an exact prediction."""
        year = year or self.today.year
        month = month or self.today.month
        days_in_month = calendar.monthrange(year, month)[1]

        events_by_day: Dict[int, List[str]] = {}

        def add_event(day: int, label: str) -> None:
            if 1 <= day <= days_in_month:
                events_by_day.setdefault(day, []).append(label)

        for routine in self.routines:
            if routine.frequency == "daily":
                continue
            routine_hash = zlib.crc32(routine.id.encode("utf-8"))
            if routine.frequency == "weekly":
                anchor = 1 + (routine_hash % 7)
                day = anchor
                while day <= days_in_month:
                    add_event(day, routine.label)
                    day += 7
            elif routine.frequency == "monthly":
                anchor = 1 + (routine_hash % 28)
                add_event(anchor, routine.label)
            elif routine.frequency == "every_n_days":
                interval = max(1, routine.interval_days or 1)
                anchor = 1 + (routine_hash % interval)
                day = anchor
                while day <= days_in_month:
                    add_event(day, routine.label)
                    day += interval

        # One-off scheduled events (created from completing a scheduling
        # task) land on whatever real date the user picked, so surface
        # those directly from the schedule rather than projecting them.
        for date_key, day_tasks in self.schedule.items():
            try:
                d = datetime.date.fromisoformat(date_key)
            except ValueError:
                continue
            if d.year != year or d.month != month:
                continue
            for t in day_tasks:
                if t.id.startswith("event-") and not t.completed:
                    add_event(d.day, t.label)

        return {
            "year": year,
            "month": month,
            "days_in_month": days_in_month,
            "events_by_day": events_by_day,
            "goals": self.goal_progress(),
        }

    def month_calendar_view(self, year: Optional[int] = None, month: Optional[int] = None) -> Dict:
        """Reshape month_view()'s data (routine projections + one-off
        scheduled events, already covering multi-day schedules, tomorrow
        overflow, and every routine type) into a Sunday-first calendar
        grid: a list of weeks, each exactly 7 cells (None for padding days
        outside the month), ready for the CLI's ASCII box renderer."""
        base = self.month_view(year, month)
        year, month = base["year"], base["month"]
        days_in_month = base["days_in_month"]
        events_by_day = base["events_by_day"]

        # calendar.weekday() is Monday=0..Sunday=6; remap to Sunday=0..Saturday=6.
        first_weekday = calendar.weekday(year, month, 1)
        first_col = (first_weekday + 1) % 7

        weeks: List[List[Optional[Dict]]] = []
        week: List[Optional[Dict]] = [None] * first_col
        for day in range(1, days_in_month + 1):
            week.append({"day": day, "labels": events_by_day.get(day, [])})
            if len(week) == 7:
                weeks.append(week)
                week = []
        if week:
            week.extend([None] * (7 - len(week)))
            weeks.append(week)

        return {
            "year": year,
            "month": month,
            "weeks": weeks,
            "goals": base["goals"],
        }

    def lock_reason(self, task: Task) -> Optional[str]:
        if not task.locked:
            return None
        labels = [r.label for r in (self.routine_by_id(dep_id) for dep_id in task.dependencies) if r is not None]
        if not labels:
            return "requires prerequisite tasks"
        return "requires " + ", ".join(labels)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def goal_by_id(self, goal_id: str) -> Optional[Goal]:
        return next((g for g in self.goals if g.id == goal_id), None)

    def routine_by_id(self, routine_id: str) -> Optional[Routine]:
        return next((r for r in self.routines if r.id == routine_id), None)

    def current_task(self, hour: Optional[int] = None) -> Optional[Task]:
        return scheduler.next_upcoming_task(self.tasks, hour)

    def hour_tasks(self, hour: Optional[int] = None) -> List[Task]:
        return scheduler.current_hour_tasks(self.tasks, hour)

    def pending_tasks(self) -> List[Task]:
        return [t for t in self.tasks if not t.completed and not t.skipped]

    # ------------------------------------------------------------------
    # Task actions
    # ------------------------------------------------------------------

    def complete_task(self, task: Task) -> Dict:
        if task.locked:
            return {"locked": True, "message": self.lock_reason(task)}

        goal = self.goal_by_id(task.goal)
        if goal is None:
            raise ValueError(f"Unknown goal '{task.goal}' for task '{task.id}'")

        gamification.update_streak(self.state, self.today)

        if task.boss:
            result = gamification.resolve_boss_fight(self.state, goal, task.xp)
        else:
            result = gamification.award_xp(self.state, goal, task.xp, is_boss=False)
            if random.random() < NON_BOSS_LOOT_CHANCE:
                result["loot"] = gamification.grant_loot(self.state)

        task.completed = True
        self.state.tasks_completed_total += 1

        if task.source_routine_id:
            routine = self.routine_by_id(task.source_routine_id)
            if routine is not None:
                routines_mod.mark_completed(routine, self.today)

        if task.is_scheduling_task:
            result["scheduling_task_completed"] = True

        self.refresh_locks()
        self.save()
        return result

    def complete_specific_task(self, task_id: str) -> Dict:
        """Complete exactly the task with this id - used when multiple
        tasks share an hour and the user picks one from a selection menu.
        Delegates to complete_task() so XP/streak/loot/boss/dependency
        handling stays identical no matter how the task was chosen, and
        every other task in the hour is left completely untouched."""
        task = scheduler.find_task_by_id(self.schedule, task_id)
        if task is None:
            raise ValueError(f"No such task '{task_id}'.")
        return self.complete_task(task)

    def _dependents_of(self, task: Task) -> List[Task]:
        if not task.source_routine_id:
            return []
        return [
            t for day_tasks in self.schedule.values() for t in day_tasks
            if not t.completed and task.source_routine_id in t.dependencies
        ]

    def skip_task(self, task: Task) -> Optional[str]:
        """Skip a task. If other tasks depend on it, don't abandon it -
        reschedule it (and cascade-push its dependents) later in the day
        (or tomorrow, if today's full) instead. Returns a message describing
        what happened when a reschedule occurred, or None for a plain skip."""
        dependents = self._dependents_of(task)
        if dependents:
            scheduler.reschedule_after_skip(self.schedule, task, self.state, self.today)
            self.refresh_locks()
            self.save()
            return "Prerequisite skipped — rescheduling it and pushing dependent tasks later."

        task.skipped = True
        self.state.tasks_skipped_total += 1
        self.save()
        return None

    # ------------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------------

    def set_energy_mode(self, mode: str) -> None:
        if mode not in config.ENERGY_MODES:
            raise ValueError(f"Unknown energy mode '{mode}'")
        self.state.energy_mode = mode
        self.state.chaos_mode = False
        self.state.comfort_mode = False
        self.rebuild_schedule()
        self.refresh_locks()
        self.save()

    def toggle_chaos_mode(self) -> bool:
        self.state.chaos_mode = not self.state.chaos_mode
        if self.state.chaos_mode:
            self.state.comfort_mode = False
        self.rebuild_schedule()
        self.refresh_locks()
        self.save()
        return self.state.chaos_mode

    def toggle_comfort_mode(self) -> bool:
        self.state.comfort_mode = not self.state.comfort_mode
        if self.state.comfort_mode:
            self.state.chaos_mode = False
        self.rebuild_schedule()
        self.refresh_locks()
        self.save()
        return self.state.comfort_mode

    def set_companion(self, companion_id: str) -> None:
        self.state.companion_id = companion_id
        self.save()

    # ------------------------------------------------------------------
    # Goal editing
    # ------------------------------------------------------------------

    def add_goal(
        self,
        name: str,
        description: str = "",
        base_xp_per_task: int = 10,
        milestones: Optional[List[int]] = None,
    ) -> Goal:
        base_slug = persistence.slugify(name)
        goal_id = base_slug
        suffix = 2
        existing_ids = {g.id for g in self.goals}
        while goal_id in existing_ids:
            goal_id = f"{base_slug}_{suffix}"
            suffix += 1

        goal = Goal(
            id=goal_id,
            name=name,
            description=description,
            base_xp_per_task=max(1, base_xp_per_task),
            milestones=sorted(milestones) if milestones else list(config.DEFAULT_MILESTONE_STEPS),
        )
        self.goals.append(goal)
        self.save()
        return goal

    def remove_goal(self, goal_id: str) -> None:
        goal = self.goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"No such goal '{goal_id}'.")
        if len(self.goals) <= 1:
            raise ValueError("Cannot remove the last remaining goal.")
        blocking_routines = [r.label for r in self.routines if r.goal == goal_id]
        if blocking_routines:
            raise ValueError(
                "Goal is still used by routines: " + ", ".join(blocking_routines) +
                ". Reassign or remove those routines first."
            )
        self.goals = [g for g in self.goals if g.id != goal_id]
        self.tasks = [t for t in self.tasks if t.goal != goal_id]
        self.save()

    def rename_goal(self, goal_id: str, new_name: str) -> None:
        goal = self.goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"No such goal '{goal_id}'.")
        goal.name = new_name
        self.save()

    def update_goal_base_xp(self, goal_id: str, new_base_xp: int) -> None:
        goal = self.goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"No such goal '{goal_id}'.")
        if new_base_xp <= 0:
            raise ValueError("Base XP per task must be a positive number.")
        goal.base_xp_per_task = new_base_xp
        self.save()

    def update_goal_milestones(self, goal_id: str, milestones: List[int]) -> None:
        goal = self.goal_by_id(goal_id)
        if goal is None:
            raise ValueError(f"No such goal '{goal_id}'.")
        if not milestones or any(m <= 0 for m in milestones):
            raise ValueError("Milestones must be a non-empty list of positive XP thresholds.")
        goal.milestones = sorted(set(milestones))
        gamification.recompute_goal_progress(goal)
        self.save()

    # ------------------------------------------------------------------
    # Player reset
    # ------------------------------------------------------------------

    def reset_player(self) -> None:
        """Wipe XP, streak, inventory, boss fights, companion, season, and
        task/routine history - but keep goal definitions, routine
        definitions, and config untouched."""
        self.state = PlayerState(companion_id=config.DEFAULT_COMPANION_ID)
        for goal in self.goals:
            goal.xp = 0
            goal.level = 1
            goal.milestones_reached = []
        for routine in self.routines:
            routine.last_completed_date = None
            routine.missed_dates = []
        gamification.sync_season(self.state, self.today)
        self.schedule = {}
        scheduler.build_daily_schedule(self.schedule, self.goals, self.routines, self.state, self.today)
        self.reconcile_dependencies()
        self.refresh_locks()
        self.save()

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def companion_message(self) -> str:
        return gamification.encouragement(self.state)

    def level_progress(self) -> Dict:
        level, xp_into_level, xp_to_next = gamification.compute_level(self.state.xp)
        return {"level": level, "xp_into_level": xp_into_level, "xp_to_next": xp_to_next}

    def goal_progress(self) -> List[Dict]:
        return [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "base_xp_per_task": g.base_xp_per_task,
                "xp": g.xp,
                "level": g.level,
                "milestones": list(g.milestones),
                "milestones_reached": list(g.milestones_reached),
                "next_milestone": next((m for m in g.milestones if m not in g.milestones_reached), None),
            }
            for g in self.goals
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        persistence.save_player_state(self.player_id, self.state)
        persistence.save_goals(self.player_id, self.goals)
        persistence.save_routines(self.player_id, self.routines)
        persistence.save_schedule(self.player_id, self.schedule)
