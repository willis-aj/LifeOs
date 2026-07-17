# LifeOS API

An optional REST API layer over the LifeOS engine, for the Angular UI in
[`../lifeos-ui/`](../lifeos-ui/). Purely additive: `python -m life_os.cli`
keeps working completely unchanged whether or not this server is running,
and both read/write the exact same per-player JSON files under
`players/<id>/`.

## Running it

```bash
pip install -r life_os_api/requirements.txt

# from the project root (D:\AIProjects\LifeOs), so `life_os` and
# `life_os_api` are both importable as top-level packages:
uvicorn life_os_api.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

## Design

Every request builds a fresh `LifeOSEngine` for the given player from disk
(`deps.get_engine`), runs the same self-healing steps the CLI's main loop
runs every check-in tick (new-day rollover, overdue-hour reflow, dependency
reconciliation), and returns plain JSON. There's no server-side session
state - each request is self-contained, exactly like one CLI check-in.

| Router | Prefix | Covers |
|---|---|---|
| `players` | `/players` | list / create / delete / fetch a player |
| `home` | `/players/{id}/home` | dashboard: stats, companion, current hour |
| `tasks` | `/players/{id}/...` | hour/day/month/backlog views; complete/skip/add/pull-forward/edit/delete |
| `goals` | `/players/{id}/goals` | list/add/edit/delete goals |
| `modes` | `/players/{id}/mode`, `/reset` | energy/chaos/comfort modes, player reset |
| `events` | `/players/{id}/events` | create a scheduled event |
| `routines` | `/players/{id}/routines` | routine definitions + history |
| `inventory` | `/players/{id}/inventory` | loot inventory |
| `companions` | `/companions`, `/players/{id}/companion` | companion roster + selection |
| `seasons` | `/seasons`, `/players/{id}/season` | season roster + current season |

CORS is enabled for `http://localhost:4200` (the Angular dev server).
