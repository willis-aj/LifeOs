"""Mode management: energy modes (low/normal/high), Chaos Mode, Comfort
Mode, and player reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life_os import config
from life_os.engine import LifeOSEngine

from ..deps import get_engine, serialize_state
from ..schemas import SetEnergyModeRequest

router = APIRouter(prefix="/players/{player_id}", tags=["modes"])


@router.get("/mode")
def get_mode(engine: LifeOSEngine = Depends(get_engine)):
    return {
        "energy_mode": engine.state.energy_mode,
        "chaos_mode": engine.state.chaos_mode,
        "comfort_mode": engine.state.comfort_mode,
        "available_energy_modes": list(config.ENERGY_MODES.keys()),
        "state": serialize_state(engine),
    }


@router.post("/mode/energy")
def set_energy_mode(body: SetEnergyModeRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        engine.set_energy_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return serialize_state(engine)


@router.post("/mode/chaos/toggle")
def toggle_chaos_mode(engine: LifeOSEngine = Depends(get_engine)):
    now_on = engine.toggle_chaos_mode()
    return {"chaos_mode": now_on, "state": serialize_state(engine)}


@router.post("/mode/comfort/toggle")
def toggle_comfort_mode(engine: LifeOSEngine = Depends(get_engine)):
    now_on = engine.toggle_comfort_mode()
    return {"comfort_mode": now_on, "state": serialize_state(engine)}


@router.post("/reset")
def reset_player(engine: LifeOSEngine = Depends(get_engine)):
    engine.reset_player()
    return serialize_state(engine)
