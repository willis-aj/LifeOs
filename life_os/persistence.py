"""
Local JSON persistence for LifeOS.

Every player gets an isolated directory under `config.PLAYERS_DIR`:

    players/<player_id>/meta.json           -> {"name": ..., "created_at": ...}
    players/<player_id>/player_state.json    -> single PlayerState
    players/<player_id>/tasks.json            -> {ISO date: list[Task]}  (multi-day schedule)
    players/<player_id>/goal_progress.json     -> list[Goal]
    players/<player_id>/routines.json           -> list[Routine]

Everything here is intentionally simple: read whole file, write whole file.
No external dependencies, no database. This keeps the door open for a future
sync layer (GitHub/Notion) to slot in without touching the rest of the app.

SAFETY RULE: there is exactly one function in this module that can delete a
real player - `delete_player(player_id)` - and it exists only as a
deliberate, user-confirmed CLI feature (see `cli.py`'s delete-player flow,
which requires an explicit [y]es before calling it). It is not a cleanup
helper: it never wipes `PLAYERS_DIR` itself, never touches any player other
than the one named, and refuses to operate on anything that doesn't resolve
to a direct child of `PLAYERS_DIR`. There must never be a "wipe all
players" / bulk-cleanup function that targets `PLAYERS_DIR`. Ad-hoc or
automated testing should use `cleanup_test_players()` instead, which is
hard-coded to the separate `config.TEST_PLAYERS_DIR` sandbox and can never
reach real player data.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
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


def has_players() -> bool:
    """True if PLAYERS_DIR exists and contains at least one player
    directory. Used at CLI startup to decide whether to show the
    player-selection menu at all, or jump straight to creating the first
    one."""
    return bool(list_players())


def cleanup_test_players() -> None:
    """Delete the sandboxed TEST_PLAYERS_DIR tree, if present. This is the
    ONLY cleanup function in this module, and it is hard-coded to the test
    sandbox directory - it never touches PLAYERS_DIR under any
    circumstance, so it is always safe to call regardless of what real
    player data exists."""
    if os.path.isdir(config.TEST_PLAYERS_DIR):
        shutil.rmtree(config.TEST_PLAYERS_DIR)


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


def delete_player(player_id: str) -> None:
    """Permanently delete one player's entire directory - all of their
    JSON state, schedules, and inventory. Intended to be called only after
    the CLI has already gotten an explicit [y]es confirmation from the
    user.

    Safety guards (all must pass, in order, or this raises instead of
    deleting anything):
      - `player_id` must be non-empty and not a path-traversal token
        ("." / ".." / containing a path separator).
      - The resolved target must sit directly inside the resolved
        `PLAYERS_DIR` - never PLAYERS_DIR itself, never anything outside it.
    """
    if not player_id or player_id in (".", "..") or "/" in player_id or "\\" in player_id:
        raise ValueError(f"Refusing to delete invalid player id {player_id!r}.")

    target = os.path.abspath(player_dir(player_id))
    root = os.path.abspath(config.PLAYERS_DIR)

    if target == root:
        raise ValueError("Refusing to delete the entire players directory.")
    if os.path.dirname(target) != root:
        raise ValueError(f"Refusing to delete a path outside {config.PLAYERS_DIR}: {target}")

    if os.path.isdir(target):
        shutil.rmtree(target)


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
# Schedule (multi-day: ISO date string -> list of Task)
# ---------------------------------------------------------------------------

def save_schedule(player_id: str, schedule: Dict[str, List[Task]]) -> None:
    payload = {date_key: [t.to_dict() for t in tasks] for date_key, tasks in schedule.items() if tasks}
    _write_json(_player_path(player_id, config.TASKS_FILE), payload)


def load_schedule(player_id: str) -> Dict[str, List[Task]]:
    data = _read_json(_player_path(player_id, config.TASKS_FILE))
    if not isinstance(data, dict):
        return {}
    return {date_key: [Task.from_dict(d) for d in items] for date_key, items in data.items()}


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
            is_scheduling_task=r.get("is_scheduling_task", False),
            note_template=r.get("note_template"),
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


# ---------------------------------------------------------------------------
# Self-Care Agent conversation history
# ---------------------------------------------------------------------------
# Stored as a single object rather than a bare list so the small pending-
# action state machine (life_os.self_care_agent_chat) can persist alongside
# the transcript without a second file.

def save_self_care_chat(player_id: str, data: Dict[str, Any]) -> None:
    _write_json(_player_path(player_id, config.SELF_CARE_CHAT_FILE), data)


def load_self_care_chat(player_id: str) -> Dict[str, Any]:
    data = _read_json(_player_path(player_id, config.SELF_CARE_CHAT_FILE))
    if data is None:
        return {"messages": [], "pending_action": None}
    return data
