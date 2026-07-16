# LifeOS

A personal life-management engine that behaves like a gamified, adaptive,
hourly check-in productivity system. LifeOS tracks a handful of active
goals, breaks them into an hourly schedule alongside your recurring
routines, and runs a lightweight RPG layer (XP, levels, streaks, loot,
boss fights) on top so check-ins feel like progress instead of chores.

## Features

- **Goals** - 3-5+ active goals, each with its own XP curve and milestones.
  Fully editable at runtime from the CLI's "edit goals" menu (add, remove,
  rename, adjust XP-per-task, adjust milestone thresholds) - no need to touch
  code, and edits persist across restarts. Defaults live in `life_os/config.py`.
- **Routines** - daily/weekly/monthly/every-N-days recurring tasks (brushing
  teeth, meds, Dexcom sensor changes, grocery runs, game nights, raids, and
  more), config-driven.
- **Task dependencies** - some routines require a prerequisite first (e.g.
  "Dinner with friends" requires "Schedule dinner with friends", "Cook
  dinner" requires "Grocery shopping"). Gated tasks show up locked until
  their prerequisite is completed the same day. Skipping a prerequisite no
  longer locks its dependent forever - it automatically reschedules the
  skipped task to the next open hour and pushes its dependents later so
  order is preserved across the day.
- **Scheduling tasks -> real events** - completing a "scheduling"-type task
  (Schedule raid, Schedule dinner with friends, RSVP to junk journaling,
  Schedule friend game night, Schedule medical appointment, Schedule
  creative session) offers to create the actual one-off event on whatever
  date/time/duration you choose. The created event is a completely normal
  task from then on - bin-packed, shows up in day/month/backlog views,
  awards XP, and can be a boss fight. Scheduling tasks themselves are
  one-time: once completed they never regenerate, and if left unfinished
  they carry forward like any other task rather than duplicating.
- **Rolling multi-day scheduler** - builds an hourly schedule from due
  routines and goal deep-work tasks, bin-packing each hour by task duration
  (multiple short tasks share an hour). When a hour's full, tasks roll
  forward across the *rest of the day* instead of piling into one slot -
  and if the whole day is full, they roll into tomorrow, which is created
  and bin-packed the same way. Respects your current energy mode.
- **End-of-day rollover** - when you check in on a new calendar day,
  anything left unfinished from before rolls forward automatically
  (dependency order and bin-packing preserved). The one exception: a missed
  *daily* routine (brush teeth, meds) is marked missed in its history
  instead of duplicating - tomorrow's instance shows up normally, once.
- **Backlog view** - `[b]acklog` lists everything pushed forward today
  (with why - skip, dependency push, hour drift, or end-of-day rollover),
  what's already lined up for tomorrow, and what's coming later this week.
- **Add task** - `[a]dd task` offers two ways to fill the current hour: add a
  brand-new manual task (name/duration/goal), or pull an already-scheduled
  later task forward into now. Both reflow the schedule and preserve
  dependency order and multi-task-per-hour bin-packing.
- **Auto-push overdue tasks** - if an hour passes without a task being
  completed or skipped, LifeOS automatically pushes it into the current
  hour the next time you check in (reflowing forward as needed) rather than
  leaving it stranded in the past - this applies uniformly to routines,
  manual tasks, boss fights, and prerequisite/dependent tasks.
- **Universal home command** - `[h]ome` is available from every menu and
  submenu (mode, goals, edit goals, inventory, reset, add task) and jumps
  straight back to the main screen - header, current mode, and the current
  hour's tasks - without disturbing the schedule or your place in it.
- **Day view / month view** - `[d]ay view` shows every scheduled hour today
  with duration, goal, XP, and dependency status; `[month]` projects boss
  fights, routines, and other non-daily events across the current calendar
  month alongside a summary of your active goals.
- **Energy modes** - `low`, `normal`, `high`, plus two special modes:
  - **Chaos Mode**: shuffles the schedule, allows more tasks per hour, pays
    out bonus XP - for unpredictable days.
  - **Comfort Mode**: strips the schedule down to essentials only, at a
    gentle pace - for rough days where just staying afloat is the win.
- **Gamification** - XP, leveling, streak bonuses, weighted loot drops, boss
  fights (for the big/important routines), seasonal expansions, and a
  companion with its own personality and encouragement lines.
- **Multi-player** - each player gets an isolated save under `players/<id>/`.
  The CLI prompts for a player at startup and lets you switch players
  mid-session without restarting the process.
- **Player reset** - wipe XP, streak, inventory, boss fights, companion
  choice, season progress, and routine/task history back to a clean slate
  for a player, without touching goal or routine definitions.
- **Hourly check-in CLI** - see what's due this hour, mark it complete or
  skip it, watch XP/loot/level-ups happen live, switch modes on the fly.
- **Local JSON persistence** - each player's state, today's tasks, goal
  progress, and routine due-dates are saved under `players/<id>/` between runs.

## Project layout

```
LifeOs/
  README.md
  pyproject.toml
  life_os/
    __init__.py
    config.py        # all editable data: goals, routines, modes, loot, companions
    models.py         # Goal / Task / Routine / PlayerState dataclasses
    scheduler.py       # builds the day's hourly schedule
    gamification.py    # XP, leveling, streaks, loot, boss fights, seasons
    routines.py         # recurrence / due-date logic
    engine.py            # orchestrates everything for the CLI
    persistence.py        # JSON save/load
    cli.py                 # interactive hourly check-in
```

## Running it

No external dependencies are required - pure standard library.

```bash
python -m life_os.cli
```

Each run:

1. Prompts you to pick an existing player or create a new one.
2. Loads (or initializes) that player's state, goals, and routines from
   `players/<id>/`.
3. Builds today's hourly schedule if one doesn't already exist for today.
4. Shows what's due this hour and lets you complete or skip it (locked
   tasks show why they're gated and can't be completed until unlocked).
5. Lets you check/edit goals, view inventory, switch modes, reset your
   progress, or switch players at any point.

State is saved after every action, so you can stop and resume the check-in
loop throughout the day.

## Customizing

Defaults for goals, routines, energy mode tuning, XP curve, loot table,
seasons, and companion personalities live in
[`life_os/config.py`](life_os/config.py). Add a new routine there and it
will show up in the schedule automatically. Goals can also be added,
renamed, or retuned per-player at runtime via the CLI's "edit goals" menu -
no code changes needed for day-to-day goal tweaks.

## Roadmap

The persistence layer is intentionally a thin JSON wrapper so a future sync
backend (GitHub Issues/Projects, Notion databases, etc.) can be added
without touching the scheduler, gamification, or CLI layers.
