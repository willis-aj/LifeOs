"""
Local JSON persistence for LifeOS.

Every player gets an isolated directory under `config.PLAYERS_DIR`:

    players/<player_id>/meta.json           -> {"name": ..., "created_at": ...}
    players/<player_id>/player_state.json    -> single PlayerState
    players/<player_id>/tasks.json            -> list[Task]  (today's schedule)
    players/<player_id>/goal_progress.json     -> list[Goal]
    players/<player_id>/routines.json           -> list[Routine]

Everything here is intentionally simple: read whole file, write whole file.
No external dependencies, no database. This keeps the door open for a future
sync layer (GitHub/Notion) to slot in without touching the rest of the app.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional

from . import config
from .models import Goal, PlayerState, Routine, Task


# ---------------------------------------------------------------------------
# Low-level JSON helpers
# ---------------------------------------------------------------------------

def _write_json(path: str, payload) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp_path, path)


def _read_json(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Player registry
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "player"


def player_dir(player_id: str) -> str:
    return os.path.join(config.PLAYERS_DIR, player_id)


def _player_path(player_id: str, filename: str) -> str:
    return os.path.join(player_dir(player_id), filename)


def player_exists(player_id: str) -> bool:
    return os.path.isdir(player_dir(player_id))


def list_players() -> List[Dict[str, str]]:
    """Return [{"id": ..., "name": ...}, ...] for every known player,
    sorted by creation time (oldest first)."""
    if not os.path.isdir(config.PLAYERS_DIR):
        return []
    players = []
    for entry in os.listdir(config.PLAYERS_DIR):
        full_path = os.path.join(config.PLAYERS_DIR, entry)
        if not os.path.isdir(full_path):
            continue
        meta = _read_json(os.path.join(full_path, config.PLAYER_META_FILE)) or {}
        players.append(
            {
                "id": entry,
                "name": meta.get("name", entry),
                "created_at": meta.get("created_at", ""),
            }
        )
    players.sort(key=lambda p: p["created_at"])
    return players


def create_player(name: str) -> str:
    """Create a new player directory (deduping slugs on collision) and
    return the new player_id."""
    name = name.strip() or "Player"
    base_slug = slugify(name)
    player_id = base_slug
    suffix = 2
    while player_exists(player_id):
        player_id = f"{base_slug}_{suffix}"
        suffix += 1

    os.makedirs(player_dir(player_id), exist_ok=True)
    meta = {"name": name, "created_at": datetime.datetime.now().isoformat(timespec="seconds")}
    _write_json(_player_path(player_id, config.PLAYER_META_FILE), meta)
    return player_id


def load_player_meta(player_id: str) -> Dict[str, Any]:
    return _read_json(_player_path(player_id, config.PLAYER_META_FILE)) or {"name": player_id}


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

def save_player_state(player_id: str, state: PlayerState) -> None:
    _write_json(_player_path(player_id, config.PLAYER_STATE_FILE), state.to_dict())


def load_player_state(player_id: str) -> PlayerState:
    data = _read_json(_player_path(player_id, config.PLAYER_STATE_FILE))
    if data is None:
        return PlayerState(companion_id=config.DEFAULT_COMPANION_ID)
    return PlayerState.from_dict(data)


# ---------------------------------------------------------------------------
# Tasks (today's schedule)
# ---------------------------------------------------------------------------

def save_tasks(player_id: str, tasks: List[Task]) -> None:
    _write_json(_player_path(player_id, config.TASKS_FILE), [t.to_dict() for t in tasks])


def load_tasks(player_id: str) -> Optional[List[Task]]:
    data = _read_json(_player_path(player_id, config.TASKS_FILE))
    if data is None:
        return None
    return [Task.from_dict(d) for d in data]


# ---------------------------------------------------------------------------
# Goal progress
# ---------------------------------------------------------------------------

def _default_goals() -> List[Goal]:
    return [
        Goal(
            id=g["id"],
            name=g["name"],
            description=g["description"],
            base_xp_per_task=g["base_xp_per_task"],
            milestones=list(g["milestones"]),
        )
        for g in config.GOALS
    ]


def save_goals(player_id: str, goals: List[Goal]) -> None:
    _write_json(_player_path(player_id, config.GOALS_FILE), [g.to_dict() for g in goals])


def load_goals(player_id: str) -> List[Goal]:
    data = _read_json(_player_path(player_id, config.GOALS_FILE))
    if data is None:
        return _default_goals()
    return [Goal.from_dict(d) for d in data]


# ---------------------------------------------------------------------------
# Routines (last-completed tracking persists alongside goals/tasks)
# ---------------------------------------------------------------------------

def _default_routines() -> List[Routine]:
    return [
        Routine(
            id=r["id"],
            label=r["label"],
            goal=r["goal"],
            frequency=r["frequency"],
            time_of_day=r.get("time_of_day"),
            duration_minutes=r["duration_minutes"],
            xp=r["xp"],
            boss=r.get("boss", False),
            interval_days=r.get("interval_days"),
            requires=list(r.get("requires", [])),
        )
        for r in config.ROUTINES
    ]


def save_routines(player_id: str, routines: List[Routine]) -> None:
    _write_json(_player_path(player_id, config.ROUTINES_FILE), [r.to_dict() for r in routines])


def load_routines(player_id: str) -> List[Routine]:
    data = _read_json(_player_path(player_id, config.ROUTINES_FILE))
    if data is None:
        return _default_routines()
    return [Routine.from_dict(d) for d in data]
