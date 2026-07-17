"""Player management: list, create, delete, and fetch a single player's
top-level summary."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life_os import persistence
from life_os.engine import LifeOSEngine

from ..deps import get_engine, serialize_player_summary, serialize_state
from ..schemas import CreatePlayerRequest

router = APIRouter(prefix="/players", tags=["players"])


@router.get("")
def list_players():
    return [serialize_player_summary(p) for p in persistence.list_players()]


@router.post("", status_code=201)
def create_player(body: CreatePlayerRequest):
    engine = LifeOSEngine.create_new_player(body.name)
    return {
        "id": engine.player_id,
        "name": engine.player_name,
        "state": serialize_state(engine),
    }


@router.get("/{player_id}")
def get_player(engine: LifeOSEngine = Depends(get_engine)):
    return {
        "id": engine.player_id,
        "name": engine.player_name,
        "state": serialize_state(engine),
        "companion_message": engine.companion_message(),
        "checkin": getattr(engine, "last_checkin", None),
    }


@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: str):
    if not persistence.player_exists(player_id):
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' not found.")
    try:
        LifeOSEngine.delete_player(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None
