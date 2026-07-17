"""Read-only view of a player's routines (definitions + completion
history) - brushing teeth, meds, raids, scheduling tasks, and so on."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life_os.engine import LifeOSEngine

from ..deps import get_engine

router = APIRouter(prefix="/players/{player_id}/routines", tags=["routines"])


@router.get("")
def list_routines(engine: LifeOSEngine = Depends(get_engine)):
    return [
        {
            "id": r.id,
            "label": r.label,
            "goal": r.goal,
            "frequency": r.frequency,
            "time_of_day": r.time_of_day,
            "duration_minutes": r.duration_minutes,
            "xp": r.xp,
            "boss": r.boss,
            "interval_days": r.interval_days,
            "requires": r.requires,
            "is_scheduling_task": r.is_scheduling_task,
            "last_completed_date": r.last_completed_date,
            "missed_dates": r.missed_dates,
        }
        for r in engine.routines
    ]
