"""
XP, leveling, streaks, loot, boss fights, seasons, and companion flavor text.

Nothing here touches disk or the terminal - it's pure game logic operating
on the dataclasses in `models.py`, driven by the tables in `config.py`.
"""

from __future__ import annotations

import datetime
import random
from typing import Dict, List, Optional, Tuple

from . import config
from .models import Goal, PlayerState


# ---------------------------------------------------------------------------
# Leveling
# ---------------------------------------------------------------------------

def compute_level(total_xp: int) -> Tuple[int, int, int]:
    """Return (level, xp_into_current_level, xp_needed_for_next_level)."""
    level = 1
    remaining = total_xp
    threshold = config.XP_PER_LEVEL_BASE
    while remaining >= threshold:
        remaining -= threshold
        level += 1
        threshold = round(threshold * config.XP_PER_LEVEL_GROWTH)
    return level, remaining, threshold


def check_goal_milestones(goal: Goal) -> List[int]:
    """Update goal.milestones_reached in place; return newly reached ones."""
    newly_reached = []
    for milestone in goal.milestones:
        if goal.xp >= milestone and milestone not in goal.milestones_reached:
            goal.milestones_reached.append(milestone)
            newly_reached.append(milestone)
    goal.level = 1 + len(goal.milestones_reached)
    return newly_reached


def recompute_goal_progress(goal: Goal) -> None:
    """Re-derive milestones_reached/level after a goal's milestone list or
    XP has been edited directly (e.g. via the goal-editing CLI menu)."""
    goal.milestones_reached = sorted(m for m in goal.milestones_reached if m in goal.milestones)
    for milestone in sorted(goal.milestones):
        if goal.xp >= milestone and milestone not in goal.milestones_reached:
            goal.milestones_reached.append(milestone)
    goal.milestones_reached.sort()
    goal.level = 1 + len(goal.milestones_reached)


# ---------------------------------------------------------------------------
# XP awarding
# ---------------------------------------------------------------------------

def award_xp(state: PlayerState, goal: Goal, base_xp: int, is_boss: bool = False) -> Dict:
    """Apply streak bonus + boss multiplier, update state & goal, return a summary."""
    multiplier = config.BOSS_FIGHT_XP_MULTIPLIER if is_boss else 1.0
    streak_bonus = streak_bonus_xp(state)
    xp_gained = round(base_xp * multiplier) + streak_bonus

    state.xp += xp_gained
    goal.xp += xp_gained

    old_level = state.level
    state.level, _, _ = compute_level(state.xp)
    leveled_up = state.level > old_level

    newly_reached_milestones = check_goal_milestones(goal)

    return {
        "xp_gained": xp_gained,
        "streak_bonus": streak_bonus,
        "leveled_up": leveled_up,
        "new_level": state.level,
        "goal_milestones": newly_reached_milestones,
    }


# ---------------------------------------------------------------------------
# Streaks
# ---------------------------------------------------------------------------

def streak_bonus_xp(state: PlayerState) -> int:
    return min(state.streak_days * config.STREAK_BONUS_XP_PER_DAY, config.STREAK_BONUS_CAP)


def update_streak(state: PlayerState, today: Optional[datetime.date] = None) -> None:
    """Call on the first completed task of the day to advance the streak."""
    today = today or datetime.date.today()
    today_str = today.isoformat()

    if state.last_active_date == today_str:
        return  # already counted today

    if state.last_active_date is not None:
        last = datetime.date.fromisoformat(state.last_active_date)
        gap_days = (today - last).days
        if gap_days == 1:
            state.streak_days += 1
        else:
            state.streak_days = 1
    else:
        state.streak_days = 1

    state.longest_streak = max(state.longest_streak, state.streak_days)
    state.last_active_date = today_str


# ---------------------------------------------------------------------------
# Loot
# ---------------------------------------------------------------------------

def roll_loot() -> Dict:
    table = config.LOOT_TABLE
    weights = [item["weight"] for item in table]
    return random.choices(table, weights=weights, k=1)[0]


def grant_loot(state: PlayerState) -> Dict:
    item = roll_loot()
    state.inventory.append(item["id"])
    return item


# ---------------------------------------------------------------------------
# Boss fights
# ---------------------------------------------------------------------------

def resolve_boss_fight(state: PlayerState, goal: Goal, base_xp: int) -> Dict:
    xp_summary = award_xp(state, goal, base_xp, is_boss=True)
    state.boss_fights_won += 1
    loot = grant_loot(state)
    xp_summary["loot"] = loot
    xp_summary["boss_fights_won"] = state.boss_fights_won
    return xp_summary


# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------

_SEASON_EPOCH = datetime.date(2025, 1, 1)


def determine_season(today: Optional[datetime.date] = None) -> Dict:
    today = today or datetime.date.today()
    total_cycle = sum(s["duration_days"] for s in config.SEASONS)
    days_since = (today - _SEASON_EPOCH).days % total_cycle
    cursor = 0
    for season in config.SEASONS:
        cursor += season["duration_days"]
        if days_since < cursor:
            return season
    return config.SEASONS[-1]


def sync_season(state: PlayerState, today: Optional[datetime.date] = None) -> bool:
    """Update state.current_season_id if the season has rolled over. Returns True on change."""
    season = determine_season(today)
    if state.current_season_id != season["id"]:
        state.current_season_id = season["id"]
        return True
    return False


# ---------------------------------------------------------------------------
# Companions
# ---------------------------------------------------------------------------

def companion_by_id(companion_id: str) -> Dict:
    for companion in config.COMPANIONS:
        if companion["id"] == companion_id:
            return companion
    return config.COMPANIONS[0]


def encouragement(state: PlayerState) -> str:
    companion = companion_by_id(state.companion_id)
    return random.choice(companion["encouragements"])
