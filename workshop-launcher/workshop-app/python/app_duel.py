"""105 Reaction Duel, run by the launcher: start(), loop(), stop()."""

from arduino.app_utils import Bridge

import random
import time
from pathlib import Path

from button import Buttons
from duel_game import PLAYERS, Match, add_entry, counts_for_leaderboard, describe, load, save


BUTTON_B = 1
CUES = ("buzz", "light", "both")
OFF, WHITE, AMBER, GREEN, BLUE, RED, PURPLE = range(7)
PLAYER_COLORS = (GREEN, BLUE)
MIN_DELAY_MS = 3000
MAX_DELAY_MS = 5000
FEEDBACK_SECONDS = 1.5
LEADERBOARD_PATH = Path(__file__).resolve().parent.parent / "data" / "leaderboard.json"

buttons = Buttons()
match = Match()
match_number = 1
leaderboard = []
history = []
mode = "idle"
cue = None
feedback_until = 0.0


def state():
    return {
        "mode": mode,
        "players": list(PLAYERS),
        "match": match_number,
        "score": list(match.score),
        "cue": cue,
        "rounds": history[-10:],
        "fastest": match.fastest(),
        "leaderboard": leaderboard,
    }


def prompt():
    if mode == "match_over":
        winner = match.winner
        buttons.accept_after(Bridge.call("duel_show_side", winner, PLAYER_COLORS[winner]))
        print(f"MATCH {match_number} to {PLAYERS[winner]}, {match.score[0]}-{match.score[1]}. "
              "Press B for a new match.")
    else:
        buttons.accept_after(Bridge.call("duel_show_score", match.score[0], match.score[1]))
        print(f"Round {len(match.rounds) + 1}: hands on A (Player 1) and C (Player 2). "
              "Press B to start, then wait for the cue.")


def show_feedback(result):
    global mode, feedback_until
    if result["winner"] is None:
        Bridge.call("duel_show", AMBER, 8)
    elif result["false_start"] is not None:
        Bridge.call("duel_show_side", result["false_start"], RED)
    else:
        Bridge.call("duel_show_side", result["winner"], PLAYER_COLORS[result["winner"]])
    mode = "result"
    feedback_until = time.monotonic() + FEEDBACK_SECONDS


def finish_round(code):
    global leaderboard
    reaction_ms = int(Bridge.call("read_reaction_ms"))
    try:
        result = match.record(code, reaction_ms)
    except ValueError as error:
        print(f"RETRY: {error}. This round was not counted.")
        show_feedback({"winner": None, "false_start": None, "reaction_ms": 0})
        return
    print(describe(result, len(match.rounds), match.score))
    history.append({"match": match_number, "round": len(match.rounds), "cue": cue, **result})
    if counts_for_leaderboard(result):
        leaderboard = add_entry(leaderboard, result["winner"], result["reaction_ms"], match_number)
        try:
            save(leaderboard, LEADERBOARD_PATH)
        except OSError as error:
            print(f"Leaderboard could not be saved: {error}. It is kept until the app restarts.")
    show_feedback(result)
    if match.over:
        Bridge.call("pulse", 400)


def start_round():
    global mode, cue
    cue = random.choice(CUES)
    accepted = int(Bridge.call("arm_duel", CUES.index(cue), random.randint(MIN_DELAY_MS, MAX_DELAY_MS)))
    if accepted:
        mode = "armed"
        print(f"WAIT for the {cue} cue. Do not press yet.")
    else:
        print("Release every button, then press B again.")


def new_match():
    global match, match_number, mode
    match = Match()
    match_number += 1
    mode = "idle"


def start():
    global leaderboard, match_number
    print("\n=== 105 Reaction Duel ===")
    Bridge.call("cancel_duel")
    try:
        leaderboard = load(LEADERBOARD_PATH)
    except (OSError, ValueError) as error:
        print(f"Ignoring saved leaderboard: {error}")
        leaderboard = []
    match_number = max([row["match"] for row in leaderboard], default=0) + 1
    prompt()


def stop():
    Bridge.call("cancel_duel")


def loop():
    global mode
    try:
        events = buttons.poll()
    except ValueError as error:
        Bridge.call("cancel_duel")
        if mode == "armed":
            mode = "idle"
        print(f"RETRY: {error}")
        prompt()
        time.sleep(0.05)
        return
    for kind, button, at, duration in events:
        if kind != "release" or button != BUTTON_B or not 30 <= duration <= 1500:
            continue
        if mode == "idle":
            start_round()
            break
        if mode == "match_over":
            new_match()
            prompt()
            break
    if mode == "armed":
        code = int(Bridge.call("read_duel"))
        if code != -2:
            finish_round(code)
    if mode == "result" and time.monotonic() >= feedback_until and not buttons.held():
        mode = "match_over" if match.over else "idle"
        prompt()
    time.sleep(0.05)

