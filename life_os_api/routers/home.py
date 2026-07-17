"""Home dashboard: level/XP/streak/mode/boss-fights/companion + current
hour's tasks - the same data the CLI's home screen renders."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life_os.engine import LifeOSEngine

from ..deps import get_engine, serialize_state, serialize_tasks

router = APIRouter(prefix="/players/{player_id}/home", tags=["home"])


@router.get("")
def get_home(engine: LifeOSEngine = Depends(get_engine)):
    view = engine.home_view()
    return {
        "player_id": engine.player_id,
        "player_name": engine.player_name,
        "state": serialize_state(engine),
        "companion_message": engine.companion_message(),
        "current_hour": view["hour"],
        "current_hour_tasks": serialize_tasks(engine, view["tasks"]),
        "checkin": getattr(engine, "last_checkin", None),
    }
