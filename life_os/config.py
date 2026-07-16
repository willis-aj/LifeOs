"""
Central configuration for LifeOS.

Everything a user is likely to want to tweak - goals, routines, energy modes,
XP curves, loot tables, companion personalities - lives here so the rest of
the codebase can stay logic-only.
"""

from __future__ import annotations

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
# Keep this list to 3-5 active goals. Each goal is broken into hourly tasks
# by the scheduler. `milestones` are XP thresholds that unlock a message.

GOALS: List[Dict[str, Any]] = [
    {
        "id": "health",
        "name": "Health & Body",
        "description": "Move daily, eat well, manage blood sugar.",
        "base_xp_per_task": 15,
        "milestones": [100, 300, 750, 1500, 3000],
    },
    {
        "id": "career",
        "name": "Career & Craft",
        "description": "Deep work on skills and projects that matter.",
        "base_xp_per_task": 20,
        "milestones": [150, 400, 900, 1800, 3500],
    },
    {
        "id": "home",
        "name": "Home & Order",
        "description": "Keep the household running smoothly.",
        "base_xp_per_task": 10,
        "milestones": [80, 250, 600, 1200, 2400],
    },
    {
        "id": "social",
        "name": "Social & Fun",
        "description": "Nurture friendships and make time for play.",
        "base_xp_per_task": 12,
        "milestones": [80, 250, 600, 1200, 2400],
    },
    {
        "id": "creativity",
        "name": "Creativity & Play",
        "description": "Make things, cook things, write things.",
        "base_xp_per_task": 12,
        "milestones": [80, 250, 600, 1200, 2400],
    },
]

# ---------------------------------------------------------------------------
# Routines
# ---------------------------------------------------------------------------
# frequency: "daily" | "weekly" | "monthly" | "every_n_days"
# time_of_day: preferred hour (0-23) or None if flexible
# interval_days: only used when frequency == "every_n_days"

ROUTINES: List[Dict[str, Any]] = [
    {
        "id": "brush_teeth_am",
        "label": "Brush teeth (AM)",
        "goal": "health",
        "frequency": "daily",
        "time_of_day": 8,
        "duration_minutes": 5,
        "xp": 5,
    },
    {
        "id": "brush_teeth_pm",
        "label": "Brush teeth (PM)",
        "goal": "health",
        "frequency": "daily",
        "time_of_day": 22,
        "duration_minutes": 5,
        "xp": 5,
    },
    {
        "id": "daily_meds",
        "label": "Take daily medication",
        "goal": "health",
        "frequency": "daily",
        "time_of_day": 9,
        "duration_minutes": 5,
        "xp": 10,
    },
    {
        "id": "shower_weekly",
        "label": "Shower",
        "goal": "health",
        "frequency": "weekly",
        "time_of_day": 19,
        "duration_minutes": 20,
        "xp": 15,
    },
    {
        "id": "weekly_shot",
        "label": "Weekly injection",
        "goal": "health",
        "frequency": "weekly",
        "time_of_day": 20,
        "duration_minutes": 10,
        "xp": 20,
        "boss": True,
    },
    {
        "id": "dexcom_sensor",
        "label": "Change Dexcom sensor",
        "goal": "health",
        "frequency": "every_n_days",
        "interval_days": 10,
        "time_of_day": 9,
        "duration_minutes": 15,
        "xp": 25,
        "boss": True,
    },
    {
        "id": "med_refill",
        "label": "Order medication refill",
        "goal": "health",
        "frequency": "monthly",
        "time_of_day": 12,
        "duration_minutes": 15,
        "xp": 20,
    },
    {
        "id": "grocery_shopping",
        "label": "Grocery shopping",
        "goal": "home",
        "frequency": "weekly",
        "time_of_day": 11,
        "duration_minutes": 60,
        "xp": 30,
    },
    {
        "id": "cook_dinner",
        "label": "Cook dinner",
        "goal": "home",
        "frequency": "weekly",
        "time_of_day": 18,
        "duration_minutes": 45,
        "xp": 20,
        "requires": ["grocery_shopping"],
    },
    {
        "id": "try_new_recipe",
        "label": "Try a new recipe",
        "goal": "creativity",
        "frequency": "weekly",
        "time_of_day": 18,
        "duration_minutes": 60,
        "xp": 30,
    },
    {
        "id": "add_recipes_to_notion",
        "label": "Add recipes to Notion",
        "goal": "home",
        "frequency": "weekly",
        "time_of_day": 20,
        "duration_minutes": 15,
        "xp": 10,
    },
    {
        "id": "monthly_game_night",
        "label": "Host / attend game night",
        "goal": "social",
        "frequency": "monthly",
        "time_of_day": 19,
        "duration_minutes": 180,
        "xp": 50,
        "boss": True,
    },
    {
        "id": "schedule_raid",
        "label": "Schedule raid night with the team",
        "goal": "social",
        "frequency": "weekly",
        "time_of_day": 12,
        "duration_minutes": 10,
        "xp": 5,
    },
    {
        "id": "destiny_2_raid",
        "label": "Destiny 2 raid night",
        "goal": "social",
        "frequency": "weekly",
        "time_of_day": 20,
        "duration_minutes": 120,
        "xp": 40,
        "boss": True,
        "requires": ["schedule_raid"],
    },
    {
        "id": "schedule_dinner_with_friends",
        "label": "Schedule dinner with friends",
        "goal": "social",
        "frequency": "weekly",
        "time_of_day": 10,
        "duration_minutes": 10,
        "xp": 5,
    },
    {
        "id": "dinner_with_friends",
        "label": "Dinner with friends",
        "goal": "social",
        "frequency": "weekly",
        "time_of_day": 19,
        "duration_minutes": 90,
        "xp": 35,
        "requires": ["schedule_dinner_with_friends"],
    },
    {
        "id": "rsvp_junk_journaling",
        "label": "RSVP to junk journaling event",
        "goal": "creativity",
        "frequency": "weekly",
        "time_of_day": 13,
        "duration_minutes": 5,
        "xp": 5,
    },
    {
        "id": "junk_journaling",
        "label": "Junk journaling session",
        "goal": "creativity",
        "frequency": "weekly",
        "time_of_day": 21,
        "duration_minutes": 30,
        "xp": 20,
        "requires": ["rsvp_junk_journaling"],
    },
]

# ---------------------------------------------------------------------------
# Scheduler / energy modes
# ---------------------------------------------------------------------------

DAY_START_HOUR = 7
DAY_END_HOUR = 23

# Routines that must survive Comfort Mode's "only essentials" filter.
ESSENTIAL_ROUTINE_IDS = [
    "brush_teeth_am",
    "brush_teeth_pm",
    "daily_meds",
    "weekly_shot",
    "dexcom_sensor",
]

# How many generic deep-work tasks per active goal get scheduled each day
# (skipped entirely in Comfort Mode).
GOAL_TASKS_PER_DAY = 2

# `hour_capacity_minutes` is the scheduler's bin-packing budget: as many
# tasks as fit within that many minutes get placed in a given hour before
# the scheduler overflows the rest into the next available hour.
ENERGY_MODES: Dict[str, Dict[str, Any]] = {
    "low": {
        "label": "Low Energy",
        "hour_capacity_minutes": 30,
        "xp_multiplier": 1.2,  # reward showing up even when running on empty
        "task_duration_cap_minutes": 30,
    },
    "normal": {
        "label": "Normal",
        "hour_capacity_minutes": 60,
        "xp_multiplier": 1.0,
        "task_duration_cap_minutes": 60,
    },
    "high": {
        "label": "High Energy",
        "hour_capacity_minutes": 120,
        "xp_multiplier": 1.0,
        "task_duration_cap_minutes": 120,
    },
}

# Chaos Mode: schedule is deliberately shuffled / compressed for unpredictable days.
CHAOS_MODE = {
    "label": "Chaos Mode",
    "xp_multiplier": 1.5,
    "shuffle": True,
    "hour_capacity_minutes": 150,
}

# Comfort Mode: low pressure, only essentials, generous XP so streaks survive.
COMFORT_MODE = {
    "label": "Comfort Mode",
    "xp_multiplier": 1.0,
    "only_essentials": True,
    "hour_capacity_minutes": 30,
}

# ---------------------------------------------------------------------------
# Gamification
# ---------------------------------------------------------------------------

XP_PER_LEVEL_BASE = 100
XP_PER_LEVEL_GROWTH = 1.15  # each level requires 15% more XP than the last

STREAK_BONUS_XP_PER_DAY = 2  # extra XP per consecutive day, capped below
STREAK_BONUS_CAP = 30

LOOT_TABLE: List[Dict[str, Any]] = [
    {"id": "common_trinket", "label": "A shiny paperclip", "rarity": "common", "weight": 50},
    {"id": "uncommon_badge", "label": "Productivity Badge", "rarity": "uncommon", "weight": 30},
    {"id": "rare_gem", "label": "Focus Gem", "rarity": "rare", "weight": 15},
    {"id": "epic_relic", "label": "Relic of Consistency", "rarity": "epic", "weight": 4},
    {"id": "legendary_crown", "label": "Crown of Follow-Through", "rarity": "legendary", "weight": 1},
]

BOSS_FIGHT_XP_MULTIPLIER = 2.0

SEASONS: List[Dict[str, Any]] = [
    {"id": "s1_spring_sprint", "label": "Spring Sprint", "duration_days": 90},
    {"id": "s2_summer_surge", "label": "Summer Surge", "duration_days": 90},
    {"id": "s3_autumn_ascent", "label": "Autumn Ascent", "duration_days": 90},
    {"id": "s4_winter_watch", "label": "Winter Watch", "duration_days": 90},
]

COMPANIONS: List[Dict[str, Any]] = [
    {
        "id": "sage",
        "name": "Sage",
        "personality": "calm",
        "encouragements": [
            "One step at a time. You've got this.",
            "Progress, not perfection.",
            "Breathe. Then begin.",
        ],
    },
    {
        "id": "spark",
        "name": "Spark",
        "personality": "hype",
        "encouragements": [
            "LET'S GOOO! XP incoming!",
            "You're on fire, keep the streak alive!",
            "Boss fight time, show it who's boss!",
        ],
    },
    {
        "id": "gruff",
        "name": "Gruff",
        "personality": "no_nonsense",
        "encouragements": [
            "Task's on the board. Go do it.",
            "No excuses, just execution.",
            "Done is better than perfect. Move.",
        ],
    },
]

DEFAULT_COMPANION_ID = "sage"

# ---------------------------------------------------------------------------
# Persistence / multi-player
# ---------------------------------------------------------------------------

# Each player gets their own subdirectory under PLAYERS_DIR containing all of
# their state: players/<player_id>/player_state.json, tasks.json, etc.
PLAYERS_DIR = "players"
PLAYER_META_FILE = "meta.json"
PLAYER_STATE_FILE = "player_state.json"
TASKS_FILE = "tasks.json"
GOALS_FILE = "goal_progress.json"
ROUTINES_FILE = "routines.json"

# Default milestone spacing used when a new goal is created via the CLI and
# no explicit milestones are supplied.
DEFAULT_MILESTONE_STEPS = [80, 250, 600, 1200, 2400]
