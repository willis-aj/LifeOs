"""
Interactive hourly check-in CLI for LifeOS.

Run with:
    python -m life_os.cli
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from . import config, persistence
from .engine import LifeOSEngine
from .models import Task

DIVIDER = "-" * 60
ACTIONS_HELP = "[c]omplete  [s]kip  [m]ode  [g]oals  [e]dit goals  [i]nventory  [r]eset  [p]layer  [q]uit"
IDLE_ACTIONS_HELP = "[m]ode  [g]oals  [e]dit goals  [i]nventory  [r]eset  [p]layer  [q]uit"


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

def _print_header(engine: LifeOSEngine) -> None:
    progress = engine.level_progress()
    mode = "Chaos Mode" if engine.state.chaos_mode else (
        "Comfort Mode" if engine.state.comfort_mode else config.ENERGY_MODES[engine.state.energy_mode]["label"]
    )
    print(DIVIDER)
    print(f"LifeOS  |  {engine.player_name}  |  Level {progress['level']}  ({progress['xp_into_level']}/{progress['xp_to_next']} XP)")
    print(f"Streak: {engine.state.streak_days} day(s)  |  Longest: {engine.state.longest_streak}")
    print(f"Mode: {mode}  |  Boss fights won: {engine.state.boss_fights_won}")
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


def _mode_menu(engine: LifeOSEngine) -> None:
    print("\nModes: [1] low  [2] normal  [3] high  [4] toggle chaos  [5] toggle comfort  [b]ack")
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
    elif choice == "b":
        return
    else:
        print("Unrecognized option.")


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


def _reset_menu(engine: LifeOSEngine) -> bool:
    """Returns True if a reset actually happened."""
    print("\nThis wipes XP, streak, inventory, boss fights, companion choice,")
    print("season progress, and task/routine history for this player.")
    print("Goal and routine definitions are kept.")
    confirm = _prompt("Type 'yes' to confirm reset, anything else to cancel: ")
    if confirm == "yes":
        engine.reset_player()
        print("Player reset. Starting fresh.")
        return True
    print("Reset cancelled.")
    return False


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


def _edit_goals_menu(engine: LifeOSEngine) -> None:
    while True:
        _print_goal_list(engine)
        print("\n[a]dd  [r]emove  [n]ame (rename)  [x] base xp/task  [m]ilestones  [b]ack")
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

        elif choice in ("b", "q"):
            return
        else:
            print("Unrecognized option.")


# ---------------------------------------------------------------------------
# Task handling
# ---------------------------------------------------------------------------

def _handle_task(engine: LifeOSEngine, task: Task) -> Optional[str]:
    """Returns "restart" if the schedule was reset out from under us,
    "switch" if the user wants to change players, or None otherwise."""
    _print_task(engine, task)
    while True:
        action = _prompt(f"{ACTIONS_HELP}: ")
        if action == "c":
            result = engine.complete_task(task)
            _print_result(result)
            if result.get("locked"):
                continue
            return None
        if action == "s":
            engine.skip_task(task)
            print("   Skipped.")
            return None
        if action == "m":
            _mode_menu(engine)
            _print_header(engine)
            _print_task(engine, task)
            continue
        if action == "g":
            _goals_menu(engine)
            continue
        if action == "e":
            _edit_goals_menu(engine)
            continue
        if action == "i":
            _inventory_menu(engine)
            continue
        if action == "r":
            if _reset_menu(engine):
                return "restart"
            continue
        if action == "p":
            return "switch"
        if action == "q":
            raise SystemExit(0)
        print("Unrecognized option.")


def _play_session(engine: LifeOSEngine) -> str:
    """Run the hourly check-in loop for one player. Returns "switch" when
    the user wants to change players; raises SystemExit to quit outright."""
    print(f"\nWelcome back, {engine.player_name}.")
    print(f'"{engine.companion_message()}"')

    while True:
        _print_header(engine)
        current_hour = datetime.datetime.now().hour
        due_now = engine.hour_tasks(current_hour)

        if due_now:
            for task in due_now:
                signal = _handle_task(engine, task)
                if signal in ("restart", "switch"):
                    break
            if signal == "switch":
                return "switch"
            # "restart" or falling through: loop back and re-fetch fresh state
            continue

        upcoming = engine.current_task()
        if upcoming is None:
            print("\nAll tasks handled for today. Great work!")
            action = _prompt(f"{IDLE_ACTIONS_HELP}: ")
            if action == "m":
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
            elif action == "q":
                raise SystemExit(0)
            else:
                print("Unrecognized option.")
            continue

        print(f"\nNothing scheduled this hour. Next up at {_format_hour(upcoming.scheduled_hour)}:")
        _print_task(engine, upcoming)
        action = _prompt(f"[c]omplete now  [s]kip  [m]ode  [g]oals  [e]dit goals  [i]nventory  [r]eset  [p]layer  [q]uit: ")
        if action == "c":
            result = engine.complete_task(upcoming)
            _print_result(result)
        elif action == "s":
            engine.skip_task(upcoming)
            print("   Skipped.")
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
        elif action == "q":
            raise SystemExit(0)
        else:
            print("Unrecognized option.")


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
