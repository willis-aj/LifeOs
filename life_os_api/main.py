"""
FastAPI entry point for the LifeOS REST API.

Run from the project root (so `life_os` and `life_os_api` are both
importable as top-level packages):

    uvicorn life_os_api.main:app --reload --port 8000

This is purely additive - `python -m life_os.cli` keeps working completely
unchanged whether or not this server is running. Both talk to the exact
same per-player JSON files under players/<id>/.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    companions,
    events,
    goals,
    home,
    inventory,
    modes,
    players,
    routines,
    seasons,
    self_care,
    self_care_chat,
    tasks,
)

app = FastAPI(
    title="LifeOS API",
    description="REST API layer over the LifeOS gamified life-management engine.",
    version="0.1.0",
)

# The Angular dev server runs on localhost:4200 by default; a built app
# served some other way can be added here too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(players.router)
app.include_router(home.router)
app.include_router(tasks.router)
app.include_router(goals.router)
app.include_router(modes.router)
app.include_router(events.router)
app.include_router(routines.router)
app.include_router(inventory.router)
app.include_router(companions.router)
app.include_router(seasons.router)
app.include_router(self_care.router)
app.include_router(self_care_chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
