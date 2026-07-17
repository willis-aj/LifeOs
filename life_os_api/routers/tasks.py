"""Schedule views (hour/day/month/backlog) and task actions (complete,
skip, add, pull-forward, edit, delete)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from life_os.engine import LifeOSEngine

from ..deps import get_engine, serialize_task, serialize_tasks
from ..schemas import AddManualTaskRequest, EditTaskRequest, PullForwardRequest

router = APIRouter(prefix="/players/{player_id}", tags=["tasks"])


def _result_or_error(result: dict) -> dict:
    """complete_task()/complete_specific_task() return {"locked": True, ...}
    instead of raising when the task can't be completed yet - surface that
    as a 409 so the client can distinguish "worked" from "not yet"."""
    if result.get("locked"):
        raise HTTPException(status_code=409, detail=result.get("message") or "Prerequisite tasks are not complete yet.")
    return result


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@router.get("/hour")
def get_hour_view(hour: Optional[int] = Query(default=None, ge=0, le=23), engine: LifeOSEngine = Depends(get_engine)):
    tasks = engine.hour_tasks(hour)
    return {"hour": hour if hour is not None else engine.home_view()["hour"], "tasks": serialize_tasks(engine, tasks)}


@router.get("/day")
def get_day_view(engine: LifeOSEngine = Depends(get_engine)):
    grouped = engine.day_view()
    return [{"hour": entry["hour"], "tasks": serialize_tasks(engine, entry["tasks"])} for entry in grouped]


@router.get("/month")
def get_month_view(
    year: Optional[int] = None,
    month: Optional[int] = None,
    engine: LifeOSEngine = Depends(get_engine),
):
    view = engine.month_calendar_view(year, month)
    return {
        "year": view["year"],
        "month": view["month"],
        "weeks": view["weeks"],
        "goals": view["goals"],
    }


@router.get("/backlog")
def get_backlog_view(engine: LifeOSEngine = Depends(get_engine)):
    view = engine.backlog_view()
    return {
        "pushed_today": serialize_tasks(engine, view["pushed_today"]),
        "tomorrow": serialize_tasks(engine, view["tomorrow"]),
        "later_this_week": [
            {"date": entry["date"], "tasks": serialize_tasks(engine, entry["tasks"])}
            for entry in view["later_this_week"]
        ],
    }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@router.post("/tasks")
def add_manual_task(body: AddManualTaskRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        task = engine.add_manual_task(
            body.label, body.duration_minutes, goal_id=body.goal_id, xp=body.xp, hour=body.hour
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return serialize_task(engine, task)


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, engine: LifeOSEngine = Depends(get_engine)):
    try:
        result = engine.complete_specific_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _result_or_error(result)


@router.post("/tasks/{task_id}/skip")
def skip_task(task_id: str, engine: LifeOSEngine = Depends(get_engine)):
    from life_os import scheduler

    task = scheduler.find_task_by_id(engine.schedule, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No such task '{task_id}'.")
    message = engine.skip_task(task)
    return {"rescheduled": message is not None, "message": message, "task": serialize_task(engine, task)}


@router.post("/tasks/{task_id}/pull-forward")
def pull_task_forward(task_id: str, body: PullForwardRequest, engine: LifeOSEngine = Depends(get_engine)):
    from life_os import scheduler

    task = scheduler.find_task_by_id(engine.schedule, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No such task '{task_id}'.")
    engine.pull_task_forward(task, hour=body.hour)
    return serialize_task(engine, task)


@router.put("/tasks/{task_id}")
def edit_task(task_id: str, body: EditTaskRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        task = engine.edit_task(
            task_id,
            label=body.label,
            duration_minutes=body.duration_minutes,
            goal_id=body.goal_id,
            xp=body.xp,
            hour=body.hour,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return serialize_task(engine, task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, engine: LifeOSEngine = Depends(get_engine)):
    try:
        engine.delete_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return None
