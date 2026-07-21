"""Self-Care Agent status - gentle nudges and overwhelm detection layered
on top of a player's existing self-care routines (see life_os.config.
SELF_CARE_ROUTINE_IDS). Read-only: completing a self-care task, adding one,
or toggling Comfort Mode all go through the existing tasks/routines/modes
routers - this endpoint only reports on current state. The conversational
counterpart (chat) lives in self_care_chat.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from life_os import self_care_agent
from life_os.engine import LifeOSEngine

from ..deps import get_engine

router = APIRouter(prefix="/players/{player_id}/self-care", tags=["self-care"])


@router.get("/status")
def get_self_care_status(engine: LifeOSEngine = Depends(get_engine)):
    return self_care_agent.self_care_status(engine)
