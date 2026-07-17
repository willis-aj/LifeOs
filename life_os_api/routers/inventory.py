"""Read-only view of a player's loot inventory."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life_os import config
from life_os.engine import LifeOSEngine

from ..deps import get_engine

router = APIRouter(prefix="/players/{player_id}/inventory", tags=["inventory"])

_LOOT_BY_ID = {item["id"]: item for item in config.LOOT_TABLE}


@router.get("")
def get_inventory(engine: LifeOSEngine = Depends(get_engine)):
    items = []
    for item_id in engine.state.inventory:
        loot = _LOOT_BY_ID.get(item_id)
        items.append(
            {
                "id": item_id,
                "label": loot["label"] if loot else item_id,
                "rarity": loot["rarity"] if loot else "unknown",
            }
        )
    return items
