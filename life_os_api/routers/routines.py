"""Routine definitions + completion history - brushing teeth, meds, raids,
scheduling tasks, and so on - plus creating new ones (e.g. from the
"create new event or routine" completion-popup form)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from life_os.engine import LifeOSEngine
from life_os.models import Routine

from ..deps import get_engine
from ..schemas import AddRoutineRequest

router = APIRouter(prefix="/players/{player_id}/routines", tags=["routines"])


def _serialize_routine(r: Routine) -> Dict[str, Any]:
    return {
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
        "note_template": r.note_template,
    }


@router.get("")
def list_routines(engine: LifeOSEngine = Depends(get_engine)):
    return [_serialize_routine(r) for r in engine.routines]


@router.post("", status_code=201)
def add_routine(body: AddRoutineRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        routine = engine.add_routine(
            body.label,
            goal_id=body.goal_id,
            duration_minutes=body.duration_minutes,
            xp=body.xp,
            frequency=body.frequency,
            time_of_day=body.time_of_day,
            interval_days=body.interval_days,
            boss=body.boss,
            note_template=body.note_template,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_routine(routine)
