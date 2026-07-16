"""
Interactive hourly check-in CLI for LifeOS.

Run with:
    python -m life_os.cli
"""

from __future__ import annotations

import calendar
import datetime
from typing import List, Optional

from . import config, persistence
from .engine import LifeOSEngine
from .models import Task

DIVIDER = "-" * 60
ACTIONS_HELP = (
    "[c]omplete  [s]kip  [a]dd task  [d]ay view  [month]  [b]acklog  [m]ode  "
    "[g]oals  [e]dit goals  [i]nventory  [r]eset  [p]layer  [h]ome  [q]uit"
)
IDLE_ACTIONS_HELP = (
    "[a]dd task  [d]ay view  [month]  [b]acklog  [m]ode  [g]oals  [e]dit goals  "
    "[i]nventory  [r]eset  [p]layer  [h]ome  [q]uit"
)

PUSH_REASON_LABELS = {
    "skip": "skipped",
    "dependency_push": "dependency push",
    "hour_drift": "hour drift",
    "eod_rollover": "end-of-day rollover",
}


def _format_hour(hour: int) -> str:
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:00 {period}"


def _prompt(prompt_text: str) -> str:
    """For menu choices - case-insensitive."""
    try:
        return input(prompt_text).strip().lower()
    except EOFError:
        return "q"


def _prompt_raw(prompt_text: str) -> str:
    """For free-text entry (names, descriptions) - preserves case."""
    try:
        return input(prompt_text).strip()
    except EOFError:
        return ""


def _parse_int_list(raw: str) -> Optional[List[int]]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Player selection
# ---------------------------------------------------------------------------

def _select_player() -> str:
    while True:
        players = persistence.list_players()
        print("\nSelect player:")
        for i, p in enumerate(players, start=1):
            print(f"  {i}. {p['name']}")
        print(f"  {len(players) + 1}. New player")

        choice = _prompt("Choose: ")
        if choice in ("q", "quit", "exit"):
            raise SystemExit(0)
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(players):
                return players[idx - 1]["id"]
            if idx == len(players) + 1:
                name = _prompt_raw("Enter new player name: ")
                if not name:
                    print("Name cannot be empty.")
                    continue
                return persistence.create_player(name)
        print("Unrecognized option.")


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _mode_label(engine: LifeOSEngine) -> str:
    if engine.state.chaos_mode:
        return "Chaos Mode"
    if engine.state.comfort_mode:
        return "Comfort Mode"
    return config.ENERGY_MODES[engine.state.energy_mode]["label"]


def _print_header(engine: LifeOSEngine) -> None:
    progress = engine.level_progress()
    print(DIVIDER)
    print(f"LifeOS  |  {engine.player_name}  |  Level {progress['level']}  ({progress['xp_into_level']}/{progress['xp_to_next']} XP)")
    print(f"Streak: {engine.state.streak_days} day(s)  |  Longest: {engine.state.longest_streak}")
    print(f"Mode: {_mode_label(engine)}  |  Boss fights won: {engine.state.boss_fights_won}")
    print(DIVIDER)


def _print_task(engine: LifeOSEngine, task: Task) -> None:
    tag = " [BOSS FIGHT]" if task.boss else ""
    hour_label = _format_hour(task.scheduled_hour)
    line = f"\n>> {hour_label}{tag}  {task.label}"
    if task.locked:
        reason = engine.lock_reason(task) or "requirements not met"
        line += f"  (locked: {reason})"
    print(line)
    print(f"   Goal: {task.goal}  |  Duration: {task.duration_minutes} min  |  XP: {task.xp}")


def _print_hour_cluster(engine: LifeOSEngine, hour: int, tasks: List[Task]) -> None:
    """Show every task sharing this hour before drilling into each one."""
    print(f"\n{_format_hour(hour)}")
    if not tasks:
        print(" (nothing scheduled)")
        return
    for t in tasks:
        tag = " [BOSS]" if t.boss else ""
        note = ""
        if t.completed:
            note = "  (done)"
        elif t.skipped:
            note = "  (skipped)"
        elif t.locked:
            note = f"  (locked: {engine.lock_reason(t)})"
        print(f" - {t.label}{tag} ({t.duration_minutes} min){note}")


def _print_result(result: dict) -> None:
    if result.get("locked"):
        print(f"   Locked: {result.get('message', 'prerequisite tasks are not complete yet.')}")
        return
    print(f"   +{result['xp_gained']} XP", end="")
    if result.get("streak_bonus"):
        print(f" (includes +{result['streak_bonus']} streak bonus)", end="")
    print()
    if result.get("leveled_up"):
        print(f"   LEVEL UP! You are now level {result['new_level']}.")
    for milestone in result.get("goal_milestones", []):
        print(f"   Goal milestone reached: {milestone} XP!")
    loot = result.get("loot")
    if loot:
        print(f"   Loot drop: {loot['label']} ({loot['rarity']})")
    if "boss_fights_won" in result:
        print(f"   Boss defeated! Total boss fights won: {result['boss_fights_won']}")


def _mode_menu(engine: LifeOSEngine) -> Optional[str]:
    print("\nModes: [1] low  [2] normal  [3] high  [4] toggle chaos  [5] toggle comfort  [b]ack  [h]ome")
    choice = _prompt("Choose: ")
    if choice == "1":
        engine.set_energy_mode("low")
    elif choice == "2":
        engine.set_energy_mode("normal")
    elif choice == "3":
        engine.set_energy_mode("high")
    elif choice == "4":
        now_on = engine.toggle_chaos_mode()
        print("Chaos Mode " + ("enabled." if now_on else "disabled."))
    elif choice == "5":
        now_on = engine.toggle_comfort_mode()
        print("Comfort Mode " + ("enabled." if now_on else "disabled."))
    elif choice == "h":
        return "home"
    elif choice == "b":
        return None
    else:
        print("Unrecognized option.")
    return None


def _goals_menu(engine: LifeOSEngine) -> None:
    print("\nGoal progress:")
    for g in engine.goal_progress():
        milestone_note = f", next milestone at {g['next_milestone']} XP" if g["next_milestone"] else " (all milestones reached!)"
        print(f"  - {g['name']}: level {g['level']}, {g['xp']} XP{milestone_note}")


def _inventory_menu(engine: LifeOSEngine) -> None:
    if not engine.state.inventory:
        print("\nInventory is empty. Complete tasks for a chance at loot!")
        return
    print("\nInventory:")
    for item_id in engine.state.inventory:
        print(f"  - {item_id}")


def _reset_menu(engine: LifeOSEngine) -> Optional[str]:
    """Returns "restart" if a reset actually happened, "home" if the user
    bailed out via the universal home command, or None if cancelled."""
    print("\nThis wipes XP, streak, inventory, boss fights, companion choice,")
    print("season progress, and task/routine history for this player.")
    print("Goal and routine definitions are kept.")
    confirm = _prompt("Type 'yes' to confirm reset, 'h' for home, anything else to cancel: ")
    if confirm == "yes":
        engine.reset_player()
        print("Player reset. Starting fresh.")
        return "restart"
    if confirm == "h":
        return "home"
    print("Reset cancelled.")
    return None


# ---------------------------------------------------------------------------
# Goal editing
# ---------------------------------------------------------------------------

def _print_goal_list(engine: LifeOSEngine) -> None:
    print("\nGoals:")
    for i, g in enumerate(engine.goal_progress(), start=1):
        print(f"  {i}. [{g['id']}] {g['name']}  |  base XP/task: {g['base_xp_per_task']}  |  milestones: {g['milestones']}")


def _resolve_goal_id(engine: LifeOSEngine, raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(engine.goals):
            return engine.goals[idx - 1].id
        return None
    if engine.goal_by_id(raw) is not None:
        return raw
    return None


def _edit_goals_menu(engine: LifeOSEngine) -> Optional[str]:
    while True:
        _print_goal_list(engine)
        print("\n[a]dd  [r]emove  [n]ame (rename)  [x] base xp/task  [m]ilestones  [b]ack  [h]ome")
        choice = _prompt("Choose: ")

        if choice == "a":
            name = _prompt_raw("New goal name: ")
            if not name:
                print("Name cannot be empty.")
                continue
            description = _prompt_raw("Description (optional): ")
            xp_raw = _prompt("Base XP per task (default 10): ").strip()
            base_xp = int(xp_raw) if xp_raw.isdigit() else 10
            milestones_raw = _prompt("Milestones, comma separated (blank for default): ").strip()
            milestones = _parse_int_list(milestones_raw) if milestones_raw else None
            goal = engine.add_goal(name, description, base_xp, milestones)
            print(f"Added goal '{goal.name}' ({goal.id}).")

        elif choice == "r":
            goal_id = _resolve_goal_id(engine, _prompt("Goal number or id to remove: "))
            if goal_id is None:
                print("Unknown goal.")
                continue
            try:
                engine.remove_goal(goal_id)
                print("Goal removed.")
            except ValueError as exc:
                print(f"Cannot remove: {exc}")

        elif choice == "n":
            goal_id = _resolve_goal_id(engine, _prompt("Goal number or id to rename: "))
            if goal_id is None:
                print("Unknown goal.")
                continue
            new_name = _prompt_raw("New name: ")
            if not new_name:
                print("Name cannot be empty.")
                continue
            engine.rename_goal(goal_id, new_name)
            print("Goal renamed.")

        elif choice == "x":
            goal_id = _resolve_goal_id(engine, _prompt("Goal number or id: "))
            if goal_id is None:
                print("Unknown goal.")
                continue
            xp_raw = _prompt("New base XP per task: ").strip()
            if not xp_raw.isdigit():
                print("Must be a positive whole number.")
                continue
            try:
                engine.update_goal_base_xp(goal_id, int(xp_raw))
                print("Base XP per task updated.")
            except ValueError as exc:
                print(f"Error: {exc}")

        elif choice == "m":
            goal_id = _resolve_goal_id(engine, _prompt("Goal number or id: "))
            if goal_id is None:
                print("Unknown goal.")
                continue
            milestones = _parse_int_list(_prompt("New milestones, comma separated XP thresholds: "))
            if milestones is None:
                print("Could not parse milestones - use comma separated numbers.")
                continue
            try:
                engine.update_goal_milestones(goal_id, milestones)
                print("Milestones updated.")
            except ValueError as exc:
                print(f"Error: {exc}")

        elif choice == "h":
            return "home"
        elif choice in ("b", "q"):
            return None
        else:
            print("Unrecognized option.")


# ---------------------------------------------------------------------------
# Add task (manual entry or pulling a later task forward)
# ---------------------------------------------------------------------------

def _add_manual_task_flow(engine: LifeOSEngine) -> None:
    label = _prompt_raw("Task name: ")
    if not label:
        print("Task name cannot be empty.")
        return
    duration_raw = _prompt("Duration in minutes: ").strip()
    if not duration_raw.isdigit() or int(duration_raw) <= 0:
        print("Duration must be a positive whole number of minutes.")
        return
    duration = int(duration_raw)

    _print_goal_list(engine)
    goal_raw = _prompt("Goal number or id (blank for default): ").strip()
    goal_id = _resolve_goal_id(engine, goal_raw) if goal_raw else None

    task = engine.add_manual_task(label, duration, goal_id)
    print(f"Added '{task.label}' at {_format_hour(task.scheduled_hour)} ({task.duration_minutes} min).")


def _pull_task_forward_flow(engine: LifeOSEngine) -> None:
    candidates = engine.later_today_tasks()
    if not candidates:
        print("Nothing scheduled later today to pull forward.")
        return

    print("\nTasks later today:")
    for i, t in enumerate(candidates, start=1):
        tag = " [BOSS]" if t.boss else ""
        lock_note = f"  (locked: {engine.lock_reason(t)})" if t.locked else ""
        print(f"  {i}. [{_format_hour(t.scheduled_hour)}] {t.label}{tag} ({t.duration_minutes} min){lock_note}")

    raw = _prompt("Number to pull forward (blank to cancel): ").strip()
    if not raw:
        return
    if not raw.isdigit() or not (1 <= int(raw) <= len(candidates)):
        print("Unrecognized option.")
        return

    chosen = candidates[int(raw) - 1]
    engine.pull_task_forward(chosen)
    print("Task pulled forward into the current hour.")


def _add_task_menu(engine: LifeOSEngine) -> Optional[str]:
    print("\n[a]dd task")
    print("  1. Add a manual task")
    print("  2. Pull a task forward from later today")
    print("  [b]ack  [h]ome")
    choice = _prompt("Choose: ")
    if choice == "1":
        _add_manual_task_flow(engine)
    elif choice == "2":
        _pull_task_forward_flow(engine)
    elif choice == "h":
        return "home"
    elif choice == "b":
        return None
    else:
        print("Unrecognized option.")
    return None


# ---------------------------------------------------------------------------
# Day / month views
# ---------------------------------------------------------------------------

def _print_day_view(engine: LifeOSEngine) -> None:
    print("\n=== Today ===")
    grouped = engine.day_view()
    if not grouped:
        print("Nothing scheduled today.")
    for entry in grouped:
        print(f"\n{_format_hour(entry['hour'])}")
        for t in entry["tasks"]:
            goal = engine.goal_by_id(t.goal)
            goal_name = goal.name if goal else t.goal
            tag = " [BOSS]" if t.boss else ""
            bits = []
            if t.completed:
                bits.append("done")
            elif t.skipped:
                bits.append("skipped")
            elif t.locked:
                bits.append(f"locked: {engine.lock_reason(t)}")
            status = f"  ({', '.join(bits)})" if bits else ""
            print(f"  - {t.label}{tag} ({t.duration_minutes} min, {goal_name}, {t.xp} XP){status}")
    print(f"\nMode: {_mode_label(engine)}")


def _describe_task_line(engine: LifeOSEngine, t: Task, include_origin: bool = True) -> str:
    goal = engine.goal_by_id(t.goal)
    goal_name = goal.name if goal else t.goal
    tag = " [BOSS]" if t.boss else ""
    bits = []
    if include_origin and t.push_reason:
        bits.append(PUSH_REASON_LABELS.get(t.push_reason, t.push_reason))
    if t.locked:
        bits.append(f"locked: {engine.lock_reason(t)}")
    note = f"  ({', '.join(bits)})" if bits else ""
    return f"  - [{_format_hour(t.scheduled_hour)}] {t.label}{tag} ({t.duration_minutes} min, {goal_name}, {t.xp} XP){note}"


def _print_backlog(engine: LifeOSEngine) -> None:
    view = engine.backlog_view()
    print("\n=== Backlog ===")

    print("\nPushed forward today:")
    if not view["pushed_today"]:
        print("  (none)")
    for t in view["pushed_today"]:
        print(_describe_task_line(engine, t))

    print("\nTomorrow:")
    if not view["tomorrow"]:
        print("  (nothing yet)")
    for t in view["tomorrow"]:
        print(_describe_task_line(engine, t))

    print("\nLater this week:")
    if not view["later_this_week"]:
        print("  (nothing yet)")
    for entry in view["later_this_week"]:
        print(f"  {entry['date']}:")
        for t in entry["tasks"]:
            print("  " + _describe_task_line(engine, t))


def _print_month_view(engine: LifeOSEngine) -> None:
    view = engine.month_view()
    month_name = calendar.month_name[view["month"]]
    print(f"\n=== {month_name} {view['year']} ===")
    events = view["events_by_day"]
    if not events:
        print("No recurring events projected this month.")
    else:
        for day in sorted(events):
            for label in events[day]:
                print(f"{day} — {label}")
    print("\nActive goals:")
    for g in view["goals"]:
        print(f"  - {g['name']}: level {g['level']}, {g['xp']} XP")


# ---------------------------------------------------------------------------
# Scheduled event creation (after completing a scheduling-type task)
# ---------------------------------------------------------------------------

def _offer_create_scheduled_event(engine: LifeOSEngine) -> None:
    print("\nYou just completed a scheduling task.")
    choice = _prompt("Would you like to create the actual event on another day? [y]es  [n]o: ")
    if choice != "y":
        return

    date_raw = _prompt_raw("Date for the event (YYYY-MM-DD): ")
    try:
        event_date = datetime.date.fromisoformat(date_raw)
    except ValueError:
        print("Could not parse that date - skipping event creation.")
        return

    label = _prompt_raw("Event name (blank for 'Scheduled event'): ").strip() or None

    time_raw = _prompt("Time - hour 0-23, optional (blank to use day start): ").strip()
    hour = int(time_raw) if time_raw.isdigit() and 0 <= int(time_raw) <= 23 else None

    duration_raw = _prompt("Duration in minutes, optional (blank for 60): ").strip()
    duration = int(duration_raw) if duration_raw.isdigit() and int(duration_raw) > 0 else 60

    _print_goal_list(engine)
    goal_raw = _prompt("Goal number or id (blank for default): ").strip()
    goal_id = _resolve_goal_id(engine, goal_raw) if goal_raw else None

    boss_raw = _prompt("Is this a boss fight? [y]es  [n]o (blank = no): ").strip()
    boss = boss_raw == "y"

    engine.create_scheduled_event(
        event_date, label=label, hour=hour, duration_minutes=duration, goal_id=goal_id, boss=boss
    )
    print("Event created and scheduled.")


# ---------------------------------------------------------------------------
# Task handling
# ---------------------------------------------------------------------------

def _handle_task(engine: LifeOSEngine, task: Task) -> Optional[str]:
    """Returns "restart" after a player reset, "rescheduled" after a
    dependency-triggered reschedule, "home" for the universal home command,
    "switch" to change players, or None once the task itself has been
    resolved (or the user backs out having only touched a side menu)."""
    _print_task(engine, task)
    while True:
        action = _prompt(f"{ACTIONS_HELP}: ")
        if action == "c":
            result = engine.complete_task(task)
            _print_result(result)
            if result.get("locked"):
                continue
            if result.get("scheduling_task_completed"):
                _offer_create_scheduled_event(engine)
            return None
        if action == "s":
            message = engine.skip_task(task)
            if message:
                print(f"   {message}")
                return "rescheduled"
            print("   Skipped.")
            return None
        if action == "a":
            signal = _add_task_menu(engine)
            if signal:
                return signal
            continue
        if action == "d":
            _print_day_view(engine)
            continue
        if action == "month":
            _print_month_view(engine)
            continue
        if action == "b":
            _print_backlog(engine)
            continue
        if action == "m":
            signal = _mode_menu(engine)
            if signal:
                return signal
            _print_header(engine)
            _print_task(engine, task)
            continue
        if action == "g":
            _goals_menu(engine)
            continue
        if action == "e":
            signal = _edit_goals_menu(engine)
            if signal:
                return signal
            continue
        if action == "i":
            _inventory_menu(engine)
            continue
        if action == "r":
            signal = _reset_menu(engine)
            if signal:
                return signal
            continue
        if action == "p":
            return "switch"
        if action == "h":
            return "home"
        if action == "q":
            raise SystemExit(0)
        print("Unrecognized option.")


def _play_session(engine: LifeOSEngine) -> str:
    """Run the hourly check-in loop for one player. Returns "switch" when
    the user wants to change players; raises SystemExit to quit outright."""
    print(f"\nWelcome back, {engine.player_name}.")
    print(f'"{engine.companion_message()}"')

    while True:
        rollover = engine.check_for_new_day()
        if rollover["rolled_over"]:
            day_word = "day" if rollover["days_advanced"] == 1 else "days"
            print(
                f"\nNew day detected ({rollover['days_advanced']} {day_word} passed) - "
                f"rolled {rollover['carried_count']} unfinished task(s) forward."
            )

        _print_header(engine)

        moved_overdue = engine.reflow_overdue_tasks()
        if moved_overdue:
            print("\nUnfinished tasks detected — moving them to the current hour.")

        view = engine.home_view()
        current_hour = view["hour"]
        due_now = view["tasks"]

        if due_now:
            target_hour = current_hour
            cluster = due_now
        else:
            upcoming = engine.current_task()
            if upcoming is None:
                print("\nAll tasks handled for today. Great work!")
                action = _prompt(f"{IDLE_ACTIONS_HELP}: ")
                if action == "a":
                    _add_task_menu(engine)
                elif action == "d":
                    _print_day_view(engine)
                elif action == "month":
                    _print_month_view(engine)
                elif action == "b":
                    _print_backlog(engine)
                elif action == "m":
                    _mode_menu(engine)
                elif action == "g":
                    _goals_menu(engine)
                elif action == "e":
                    _edit_goals_menu(engine)
                elif action == "i":
                    _inventory_menu(engine)
                elif action == "r":
                    _reset_menu(engine)
                elif action == "p":
                    return "switch"
                elif action == "h":
                    pass
                elif action == "q":
                    raise SystemExit(0)
                else:
                    print("Unrecognized option.")
                continue

            target_hour = upcoming.scheduled_hour
            cluster = engine.hour_tasks(target_hour)
            print(f"\nNothing scheduled this hour. Next up at {_format_hour(target_hour)}:")

        _print_hour_cluster(engine, target_hour, cluster)

        signal = None
        for task in cluster:
            if task.completed or task.skipped or task.scheduled_hour != target_hour:
                continue
            signal = _handle_task(engine, task)
            if signal in ("restart", "switch", "rescheduled", "home"):
                break

        if signal == "switch":
            return "switch"
        continue


def run() -> None:
    while True:
        player_id = _select_player()
        engine = LifeOSEngine(player_id)
        signal = _play_session(engine)
        if signal != "switch":
            break
        print("\nSwitching player...")


def main() -> None:
    try:
        run()
    except SystemExit:
        print("\nSee you next check-in.")
    except KeyboardInterrupt:
        print("\nInterrupted. See you next check-in.")


if __name__ == "__main__":
    main()
