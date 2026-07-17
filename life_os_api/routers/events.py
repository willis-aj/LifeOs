"""Scheduled event creation - the "actual event" a user creates after
completing a scheduling-type task (or any time they want to add one)."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException

from life_os.engine import LifeOSEngine

from ..deps import get_engine, serialize_task
from ..schemas import CreateScheduledEventRequest

router = APIRouter(prefix="/players/{player_id}/events", tags=["events"])


@router.post("", status_code=201)
def create_scheduled_event(body: CreateScheduledEventRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        event_date = datetime.date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{body.date}' - expected YYYY-MM-DD.")

    try:
        task = engine.create_scheduled_event(
            event_date,
            label=body.label,
            hour=body.hour,
            duration_minutes=body.duration_minutes,
            goal_id=body.goal_id,
            boss=body.boss,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return serialize_task(engine, task)
