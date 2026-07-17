"""Goal management: list, add, edit, delete - mirrors the CLI's "edit
goals" menu."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from life_os.engine import LifeOSEngine

from ..deps import get_engine
from ..schemas import AddGoalRequest, EditGoalRequest

router = APIRouter(prefix="/players/{player_id}/goals", tags=["goals"])


@router.get("")
def list_goals(engine: LifeOSEngine = Depends(get_engine)):
    return engine.goal_progress()


@router.post("", status_code=201)
def add_goal(body: AddGoalRequest, engine: LifeOSEngine = Depends(get_engine)):
    goal = engine.add_goal(body.name, body.description, body.base_xp_per_task, body.milestones)
    return next(g for g in engine.goal_progress() if g["id"] == goal.id)


@router.put("/{goal_id}")
def edit_goal(goal_id: str, body: EditGoalRequest, engine: LifeOSEngine = Depends(get_engine)):
    try:
        if body.name is not None:
            engine.rename_goal(goal_id, body.name)
        if body.base_xp_per_task is not None:
            engine.update_goal_base_xp(goal_id, body.base_xp_per_task)
        if body.milestones is not None:
            engine.update_goal_milestones(goal_id, body.milestones)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    match = next((g for g in engine.goal_progress() if g["id"] == goal_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"No such goal '{goal_id}'.")
    return match


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, engine: LifeOSEngine = Depends(get_engine)):
    try:
        engine.remove_goal(goal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None
