"""Seasons: the global roster (config-driven) plus a player's current
season."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life_os import config
from life_os.engine import LifeOSEngine

from ..deps import get_engine

router = APIRouter(tags=["seasons"])


@router.get("/seasons")
def list_seasons():
    return [{"id": s["id"], "label": s["label"], "duration_days": s["duration_days"]} for s in config.SEASONS]


@router.get("/players/{player_id}/season")
def get_current_season(engine: LifeOSEngine = Depends(get_engine)):
    season_id = engine.state.current_season_id
    match = next((s for s in config.SEASONS if s["id"] == season_id), None)
    return {
        "id": season_id,
        "label": match["label"] if match else None,
    }
