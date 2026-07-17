"""
Shared FastAPI dependencies and serialization helpers.

Every request that operates on a player builds a *fresh* `LifeOSEngine` for
that player (via `get_engine`), which loads straight from the same JSON
files the CLI reads and writes. There is no in-memory session state here -
each request is self-contained, exactly like a single CLI check-in tick:
`get_engine` runs the same self-healing steps the CLI's main loop runs
every tick (new-day rollover, overdue-hour reflow, dependency
reconciliation) before handing the engine back, so the rolling task list,
tomorrow overflow, and dependency rescheduling all keep working
identically whether you're driving LifeOS from the terminal or the API.
"""

from __future__ import annotations

import sys
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from fastapi import HTTPException

# Make the sibling `life_os` package importable regardless of the exact
# working directory uvicorn was launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from life_os import config, persistence  # noqa: E402
from life_os.engine import LifeOSEngine  # noqa: E402
from life_os.models import Task  # noqa: E402

# Every request builds a fresh LifeOSEngine and self-heals (writes JSON
# files) before the route handler runs. FastAPI serves sync routes from a
# thread pool, so concurrent requests for the *same* player (e.g. the
# Settings page firing several GETs at once) can otherwise race on the same
# on-disk files - fatal on Windows, where os.replace() can fail if another
# thread has the destination file open. One lock per player_id serializes
# construction/self-heal for that player without blocking other players.
_player_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
_player_locks_guard = threading.Lock()


def _lock_for_player(player_id: str) -> threading.Lock:
    with _player_locks_guard:
        return _player_locks[player_id]


def checkin(engine: LifeOSEngine) -> Dict[str, Any]:
    """Run the same self-healing steps the CLI's main loop runs on every
    tick, and summarize what happened for the API caller."""
    rollover = engine.check_for_new_day()
    overdue_moved = engine.reflow_overdue_tasks()
    dependency_fixes = engine.reconcile_dependencies()
    return {
        "rolled_over": rollover["rolled_over"],
        "days_advanced": rollover["days_advanced"],
        "carried_count": rollover["carried_count"],
        "overdue_moved_count": len(overdue_moved),
        "dependency_fixes": [
            {"prerequisite": prereq, "dependent": dependent}
            for prereq, dependent in dependency_fixes
        ],
    }


def get_engine(player_id: str) -> LifeOSEngine:
    """FastAPI dependency: load (or 404) the player and self-heal their
    schedule before handing the engine to the route handler."""
    if not persistence.player_exists(player_id):
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' not found.")
    with _lock_for_player(player_id):
        engine = LifeOSEngine(player_id)
        engine.last_checkin = checkin(engine)  # stashed for routes that want to report it
    return engine


def serialize_player_summary(p: Dict[str, str]) -> Dict[str, Any]:
    return {"id": p["id"], "name": p["name"], "created_at": p.get("created_at", "")}


def serialize_task(engine: LifeOSEngine, task: Task) -> Dict[str, Any]:
    d = task.to_dict()
    goal = engine.goal_by_id(task.goal)
    d["goal_name"] = goal.name if goal else task.goal
    d["lock_reason"] = engine.lock_reason(task)
    return d


def serialize_tasks(engine: LifeOSEngine, tasks: List[Task]) -> List[Dict[str, Any]]:
    return [serialize_task(engine, t) for t in tasks]


def serialize_state(engine: LifeOSEngine) -> Dict[str, Any]:
    state = engine.state
    progress = engine.level_progress()
    mode_label = (
        "Chaos Mode" if state.chaos_mode
        else "Comfort Mode" if state.comfort_mode
        else config.ENERGY_MODES[state.energy_mode]["label"]
    )
    return {
        "xp": state.xp,
        "level": progress["level"],
        "xp_into_level": progress["xp_into_level"],
        "xp_to_next": progress["xp_to_next"],
        "streak_days": state.streak_days,
        "longest_streak": state.longest_streak,
        "energy_mode": state.energy_mode,
        "chaos_mode": state.chaos_mode,
        "comfort_mode": state.comfort_mode,
        "mode_label": mode_label,
        "companion_id": state.companion_id,
        "current_season_id": state.current_season_id,
        "inventory": list(state.inventory),
        "boss_fights_won": state.boss_fights_won,
        "tasks_completed_total": state.tasks_completed_total,
        "tasks_skipped_total": state.tasks_skipped_total,
    }
