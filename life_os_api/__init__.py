"""
life_os_api: an optional REST API layer over the LifeOS engine.

This package is purely additive - it imports `life_os` (the CLI package)
and exposes its functionality over HTTP for the Angular UI (`lifeos-ui/`).
It never modifies CLI behavior, and the CLI (`python -m life_os.cli`)
keeps working exactly as before whether or not this API is running.

Run with (from the project root, so both `life_os` and `life_os_api` are
importable as top-level packages):

    uvicorn life_os_api.main:app --reload
"""
