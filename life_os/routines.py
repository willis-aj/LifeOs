"""
Routine due-date logic.

Routines are recurring obligations (brush teeth, grocery shopping, Dexcom
sensor changes, ...) defined in `config.ROUTINES` and tracked as `Routine`
objects with a `last_completed_date`. This module answers one question:
"is this routine due, given today's date?"
"""

from __future__ import annotations

import datetime
from typing import List

from .models import Routine


def _parse_date(date_str: str) -> datetime.date:
    return datetime.date.fromisoformat(date_str)


def is_due(routine: Routine, today: datetime.date) -> bool:
    """Return True if `routine` should appear on today's schedule."""
    if routine.last_completed_date is None:
        return True

    last = _parse_date(routine.last_completed_date)
    if last >= today:
        # Already handled today (or in the future, e.g. clock weirdness).
        return False

    delta_days = (today - last).days

    if routine.frequency == "daily":
        return delta_days >= 1
    if routine.frequency == "weekly":
        return delta_days >= 7
    if routine.frequency == "monthly":
        return delta_days >= 28
    if routine.frequency == "every_n_days":
        interval = routine.interval_days or 1
        return delta_days >= interval

    # Unknown frequency: default to "always due" so nothing silently vanishes.
    return True


def due_routines(routines: List[Routine], today: datetime.date | None = None) -> List[Routine]:
    today = today or datetime.date.today()
    return [r for r in routines if is_due(r, today)]


def mark_completed(routine: Routine, today: datetime.date | None = None) -> None:
    today = today or datetime.date.today()
    routine.last_completed_date = today.isoformat()
