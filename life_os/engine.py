"""
LifeOSEngine: the orchestrator that ties config, models, persistence,
scheduler, routines, and gamification together behind a small, CLI-friendly
API.

`cli.py` should not need to import anything except this module (plus maybe
`config` for display labels). All engine state is scoped to a single
`player_id` - callers select or create a player via `persistence.list_players()`
/ `persistence.create_player()` before constructing an engine.
"""

from __future__ import annotations

import calendar
import datetime
import random
import uuid
import zlib
from typing import Dict, List, Optional

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

        gamification.sync_season(self.state, self.today)

        self.tasks: List[Task] = self._load_or_build_schedule()
        self.refresh_locks()

    # ------------------------------------------------------------------
    # Schedule management
    # ------------------------------------------------------------------

    def _schedule_is_current(self, tasks: Optional[List[Task]]) -> bool:
        if not tasks:
            return False
        marker = self.today.isoformat()
        return all(marker in t.id for t in tasks)

    def _load_or_build_schedule(self) -> List[Task]:
        tasks = persistence.load_tasks(self.player_id)
        if not self._schedule_is_current(tasks):
            tasks = scheduler.build_daily_schedule(self.goals, self.routines, self.state, self.today)
            persistence.save_tasks(self.player_id, tasks)
        return tasks

    def rebuild_schedule(self) -> None:
        """Regenerate the schedule (e.g. after a mode switch), preserving
        any tasks already completed or skipped today."""
        handled = [t for t in self.tasks if t.completed or t.skipped]
        handled_ids = {t.id for t in handled}

        fresh = scheduler.build_daily_schedule(self.goals, self.routines, self.state, self.today)
        fresh = [t for t in fresh if t.id not in handled_ids]

        self.tasks = handled + fresh
        self.tasks.sort(key=lambda t: t.scheduled_hour)
        persistence.save_tasks(self.player_id, self.tasks)

    def refresh_locks(self) -> None:
        scheduler.apply_lock_state(self.tasks, self.routines, self.today)

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

    def reflow_overdue_tasks(self) -> List[Task]:
        """Detect any incomplete tasks left behind in past hours (the user
        didn't get to them before the hour moved on) and push them into the
        current hour, reflowing the rest of the day forward as needed.
        Works the same regardless of whether the overdue task is a routine,
        a manually-added task, a boss fight, or part of a dependency chain.
        Returns the tasks that were moved (empty if nothing was overdue)."""
        current_hour = datetime.datetime.now().hour
        overdue = [
            t for t in self.tasks
            if not t.completed and not t.skipped and t.scheduled_hour < current_hour
        ]
        if not overdue:
            return []
        moved = scheduler.push_overdue_to_current_hour(self.tasks, overdue, current_hour, self.state)
        self.refresh_locks()
        self.save()
        return moved

    def later_today_tasks(self, hour: Optional[int] = None) -> List[Task]:
        """Pending tasks scheduled strictly after the given (or current)
        hour, in schedule order - candidates for pulling forward."""
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
        scheduler.pull_task_to_hour(self.tasks, task, target_hour, self.state)
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
        scheduler.insert_task(self.tasks, task, target_hour, self.state)
        self.refresh_locks()
        self.save()
        return task

    def day_view(self) -> List[Dict]:
        """Group today's tasks by hour for a full-day overview."""
        by_hour: Dict[int, List[Task]] = {}
        for t in self.tasks:
            by_hour.setdefault(t.scheduled_hour, []).append(t)
        return [{"hour": h, "tasks": by_hour[h]} for h in sorted(by_hour)]

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

        return {
            "year": year,
            "month": month,
            "days_in_month": days_in_month,
            "events_by_day": events_by_day,
            "goals": self.goal_progress(),
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

        self.refresh_locks()
        self.save()
        return result

    def _dependents_of(self, task: Task) -> List[Task]:
        if not task.source_routine_id:
            return []
        return [
            t for t in self.tasks
            if not t.completed and task.source_routine_id in t.dependencies
        ]

    def skip_task(self, task: Task) -> Optional[str]:
        """Skip a task. If other tasks depend on it, don't abandon it -
        reschedule it (and cascade-push its dependents) later in the day
        instead. Returns a message describing what happened when a
        reschedule occurred, or None for a plain skip."""
        dependents = self._dependents_of(task)
        if dependents:
            scheduler.reschedule_after_skip(self.tasks, task, self.state, self.today)
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
        gamification.sync_season(self.state, self.today)
        self.tasks = scheduler.build_daily_schedule(self.goals, self.routines, self.state, self.today)
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
        persistence.save_tasks(self.player_id, self.tasks)
