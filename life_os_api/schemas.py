"""Pydantic request bodies for life_os_api. Responses are plain dicts built
by deps.py's serialize_* helpers / engine methods - the engine's own
dataclasses are already the source of truth, so we don't duplicate every
field into a second set of response schemas."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CreatePlayerRequest(BaseModel):
    name: str = Field(min_length=1)


class AddManualTaskRequest(BaseModel):
    label: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0)
    goal_id: Optional[str] = None
    xp: Optional[int] = Field(default=None, gt=0)
    hour: Optional[int] = Field(default=None, ge=0, le=23)


class EditTaskRequest(BaseModel):
    label: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    goal_id: Optional[str] = None
    xp: Optional[int] = Field(default=None, gt=0)
    hour: Optional[int] = Field(default=None, ge=0, le=23)


class PullForwardRequest(BaseModel):
    hour: Optional[int] = Field(default=None, ge=0, le=23)


class AddGoalRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    base_xp_per_task: int = Field(default=10, gt=0)
    milestones: Optional[List[int]] = None


class EditGoalRequest(BaseModel):
    name: Optional[str] = None
    base_xp_per_task: Optional[int] = Field(default=None, gt=0)
    milestones: Optional[List[int]] = None


class SetEnergyModeRequest(BaseModel):
    mode: str  # "low" | "normal" | "high"


class SetCompanionRequest(BaseModel):
    companion_id: str


class CreateScheduledEventRequest(BaseModel):
    date: str  # ISO date, e.g. "2026-08-01"
    label: Optional[str] = None
    hour: Optional[int] = Field(default=None, ge=0, le=23)
    duration_minutes: int = Field(default=60, gt=0)
    goal_id: Optional[str] = None
    boss: bool = False
