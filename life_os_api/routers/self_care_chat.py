"""Self-Care Agent chat - the conversational front-end over
life_os.self_care_agent_chat. Every reply may mutate real engine state
(adding a routine/task, toggling Comfort Mode) via the same methods the
rest of the API uses - nothing here bypasses the engine."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from life_os import self_care_agent_chat
from life_os.engine import LifeOSEngine

from ..deps import get_engine
from ..schemas import SelfCareChatRequest

router = APIRouter(prefix="/players/{player_id}/self-care", tags=["self-care"])


@router.post("/chat")
def post_chat_message(body: SelfCareChatRequest, engine: LifeOSEngine = Depends(get_engine)) -> Dict[str, Any]:
    messages = self_care_agent_chat.handle_message(engine, body.message)
    return {"messages": messages}


@router.get("/history")
def get_chat_history(engine: LifeOSEngine = Depends(get_engine)) -> Dict[str, List[Dict[str, str]]]:
    return {"messages": self_care_agent_chat.get_history(engine.player_id)}
