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

import datetime
import random
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

    def skip_task(self, task: Task) -> None:
        task.skipped = True
        self.state.tasks_skipped_total += 1
        self.save()

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
