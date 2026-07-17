"""Companions: the global roster (config-driven) plus a player's current
companion selection."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life_os import config
from life_os.engine import LifeOSEngine

from ..deps import get_engine
from ..schemas import SetCompanionRequest

router = APIRouter(tags=["companions"])


@router.get("/companions")
def list_companions():
    return [
        {"id": c["id"], "name": c["name"], "personality": c["personality"]}
        for c in config.COMPANIONS
    ]


@router.get("/players/{player_id}/companion")
def get_companion(engine: LifeOSEngine = Depends(get_engine)):
    return {
        "companion_id": engine.state.companion_id,
        "message": engine.companion_message(),
    }


@router.post("/players/{player_id}/companion")
def set_companion(body: SetCompanionRequest, engine: LifeOSEngine = Depends(get_engine)):
    valid_ids = {c["id"] for c in config.COMPANIONS}
    if body.companion_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unknown companion '{body.companion_id}'.")
    engine.set_companion(body.companion_id)
    return {"companion_id": engine.state.companion_id, "message": engine.companion_message()}
