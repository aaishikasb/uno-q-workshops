"""301 AI Maze, run by the launcher: start(), loop(), stop()."""

from arduino.app_utils import Bridge

from collections import deque
import random
import time

import maze_model
from maze_model import (COLS, ROWS, WALL, Episode, arrows, generate, greedy_path, move_goal, new_q,
                        run_episode, slide_path)


TRAPS = 0
MIN_MOVES = 4
# Knob 0 to STEP_MODE_UP_TO animates every move, from SLOWEST to FASTEST seconds per move.
# Above that it fast-forwards, up to MAX_EPISODES_PER_TICK attempts per tick.
DEFAULT_SPEED = 45
STEP_MODE_UP_TO = 60
SLOWEST_MOVE_SECONDS = 0.5
FASTEST_MOVE_SECONDS = 0.05
MAX_EPISODES_PER_TICK = 50
DEMO_STEP_SECONDS = 0.35
# A knob press shorter than this moves the exit; long holds belong to the launcher (hold 13 s to exit).
KNOB_TAP_SECONDS = 1.0
TRAIL_LENGTH = 8
# Tilt is read every loop; buttons, knob, training, and Pixels only every CONTROL_SECONDS.
TILT_POLL_SECONDS = 0.01
CONTROL_SECONDS = 0.05
# A tilt counts beyond TILT_G and keeps counting down to LEVEL_G, so a shaky hand does not flicker.
TILT_G = 0.35
LEVEL_G = 0.15
# Gravity: the first cell takes ROLL_FIRST_CELL_SECONDS, and each later cell is faster.
ROLL_FIRST_CELL_SECONDS = 0.3
ROLL_ACCELERATION = 0.85
ROLL_MIN_CELL_SECONDS = 0.12
# Flip these if the ball rolls the wrong way for how your board is mounted.
SWAP_AXES = False
FLIP_RIGHT = False
FLIP_DOWN = False

BLUE, PINK, GREEN, PURPLE, WHITE, AMBER, RED, OFF = range(8)

# `rng` drives the agent and is reseeded per maze; `maze_rng` picks new mazes.
rng = random.Random()
maze_rng = random.Random()
mode = "human"
maze = None
maze_number = 0
q = None
ball = 0
moves = 0
started_at = 0.0
rolling = []
roll_outcome = None
next_roll_at = 0.0
roll_cell_seconds = ROLL_FIRST_CELL_SECONDS
tilt = (0.0, 0.0)
tilt_action = None
next_control_at = 0.0
last_buttons = 0
last_knob_pressed = 0
knob_pressed_at = None
last_knob = None
speed = DEFAULT_SPEED
episodes = 0
recent = deque(maxlen=20)
# One entry per attempt: [moves, escaped, its best route's length or None, best possible].
attempts = deque(maxlen=200)
trail = deque(maxlen=TRAIL_LENGTH)
agent_found_goal = False
learned_at = None
moved_at = None
episode = None
next_step_at = 0.0
demo_path = []
demo_success = False
human_moves = None
human_seconds = None
ai_moves = None
pixels_shown = None


def success_rate():
    return sum(recent) / len(recent) if recent else 0.0


def show(color, count):
    global pixels_shown
    if pixels_shown != (color, count):
        Bridge.call("maze_show", color, count)
        pixels_shown = (color, count)


def place_ball(pos):
    global ball
    ball = pos
    Bridge.call("set_ball", pos)


def draw_maze():
    for row in range(ROWS):
        mask = 0
        for col in range(COLS):
            if maze["cells"][row * COLS + col] == WALL:
                mask |= 1 << col
        Bridge.call("set_row", row, mask)
    Bridge.call("set_goal", maze["goal"])
    for slot in range(4):
        Bridge.call("set_trap", slot, maze["traps"][slot] if slot < len(maze["traps"]) else -1)


def start_human():
    global mode, moves, started_at, rolling, roll_outcome
    mode = "human"
    moves = 0
    rolling = []
    roll_outcome = None
    started_at = time.monotonic()
    place_ball(maze["start"])
    print(f"MAZE #{maze_number}, YOUR TURN: tilt the board to roll the ball into the blinking exit. "
          f"Best possible: {maze['optimal']} moves.")
    print("Button B = skip to the AI.")


def new_maze():
    global maze, maze_number, q, episodes, agent_found_goal, learned_at, moved_at, episode, demo_path
    global human_moves, human_seconds, ai_moves
    maze_number += 1
    seed = maze_model.DEMO_MAZE_SEED if maze_number == 1 else maze_rng.randrange(1_000_000)
    maze = generate(seed, traps=TRAPS, min_moves=MIN_MOVES)
    rng.seed(maze_model.DEMO_AGENT_SEED)
    q = new_q()
    episodes = 0
    recent.clear()
    attempts.clear()
    trail.clear()
    agent_found_goal = False
    learned_at = moved_at = None
    episode = None
    demo_path = []
    human_moves = human_seconds = ai_moves = None
    draw_maze()
    start_human()


def wait_for_ai():
    """Hold the AI round until Button B."""
    global mode
    mode = "paused"
    place_ball(maze["start"])


def start_training():
    global mode, episode
    mode = "training"
    episode = None
    trail.clear()
    place_ball(maze["start"])
    print("AI'S TURN: it has no map. Every move costs 1 point and the exit is worth 10.")
    print("Knob = speed, Button B = pause, Button C = race, knob tap = move the exit, hold the knob 13 s = menu.")


def start_demo():
    global mode, demo_path, demo_success, next_step_at
    path, demo_success = greedy_path(q, maze)
    demo_path = list(path)
    mode = "demo"
    trail.clear()
    next_step_at = time.monotonic() + DEMO_STEP_SECONDS
    place_ball(maze["start"])
    print("RACE: the AI plays its best route.")


def move_exit():
    """Move the exit and keep the Q-table."""
    global maze, mode, episode, learned_at, moved_at, ai_moves
    moved = move_goal(maze, q, rng)
    if moved is None:
        print("There is no good spot to move the exit to in this maze. Press Button A for a new maze.")
        return
    maze = moved
    learned_at = None
    moved_at = episodes
    ai_moves = None
    episode = None
    trail.clear()
    draw_maze()
    mode = "training"
    place_ball(maze["start"])
    Bridge.call("pulse", 300)
    print(f"THE EXIT MOVED. Best possible is now {maze['optimal']} moves.")


def finish_episode(result):
    global episodes, agent_found_goal, learned_at
    episodes += 1
    recent.append(result["success"])
    path, success = greedy_path(q, maze)
    best = len(path) if success else None
    attempts.append([result["steps"], int(result["success"]), best, maze["optimal"]])
    if result["success"] and not agent_found_goal:
        agent_found_goal = True
        Bridge.call("pulse", 150)
        print(f"Attempt {episodes}: first escape.")
    if learned_at is None and best == maze["optimal"]:
        learned_at = episodes
        Bridge.call("pulse", 250)
        since = f" {episodes - moved_at} attempts after the exit moved" if moved_at is not None else ""
        print(f"Attempt {episodes}: it found the best route ({best} moves){since}.")


def handle_buttons():
    global last_buttons, mode
    mask = int(Bridge.call("read_buttons"))
    pressed = mask & ~last_buttons
    last_buttons = mask
    if pressed & 1:
        new_maze()
        return
    if pressed & 2:
        if mode == "human":
            start_training()
        elif mode == "training":
            mode = "paused"
            print(f"PAUSED after {episodes} attempts. Button B resumes, Button C races.")
        elif mode == "paused" and episodes == 0 and moved_at is None:
            start_training()
        elif mode == "paused":
            mode = "training"
            print("Training resumed.")
    if pressed & 4 and mode in ("training", "paused"):
        start_demo()


def update_knob():
    """Knob turn = speed 0-100. A short tap (press and release) moves the exit."""
    global last_knob_pressed, knob_pressed_at, last_knob, speed
    now = time.monotonic()
    pressed = int(Bridge.call("read_knob_pressed"))
    if pressed and not last_knob_pressed:
        knob_pressed_at = now
    if not pressed and last_knob_pressed and knob_pressed_at is not None:
        if now - knob_pressed_at < KNOB_TAP_SECONDS and mode != "human" and episodes > 0:
            move_exit()
        knob_pressed_at = None
    last_knob_pressed = pressed
    # The MCU reports an unbounded position; the speed follows its change and stays in 0-100.
    position = int(Bridge.call("read_knob"))
    if last_knob is not None:
        speed = max(0, min(100, speed + position - last_knob))
    last_knob = position


def seconds_per_move():
    fraction = min(speed, STEP_MODE_UP_TO) / STEP_MODE_UP_TO
    return SLOWEST_MOVE_SECONDS - (SLOWEST_MOVE_SECONDS - FASTEST_MOVE_SECONDS) * fraction


def board_tilt(packed):
    """Unpack the MCU reading into g toward the maze's right and bottom edges."""
    x = (packed // 4096 - 2048) / 1000
    y = (packed % 4096 - 2048) / 1000
    if SWAP_AXES:
        x, y = y, x
    return (-x if FLIP_RIGHT else x), (y if FLIP_DOWN else -y)


def poll_tilt():
    global tilt, tilt_action
    right, down = board_tilt(int(Bridge.call("read_tilt")))
    tilt = (right, down)
    strongest = max(abs(right), abs(down))
    if abs(right) >= abs(down):
        direction = 1 if right > 0 else 3
    else:
        direction = 2 if down > 0 else 0
    if strongest >= TILT_G:
        tilt_action = direction
    elif strongest < LEVEL_G or direction != tilt_action:
        tilt_action = None


def finish_roll(now):
    global human_moves, human_seconds
    if roll_outcome == "goal":
        human_moves = moves
        human_seconds = round(now - started_at, 1)
        Bridge.call("pulse", 400)
        print(f"YOU ESCAPED in {human_moves} moves and {human_seconds}s. Button B starts the AI.")
        wait_for_ai()
    elif roll_outcome == "trap":
        Bridge.call("pulse", 150)
        print("TRAP! Back to the start.")
        place_ball(maze["start"])


def human_tick(now):
    global moves, rolling, roll_outcome, next_roll_at, roll_cell_seconds
    if rolling:
        if now < next_roll_at:
            return
        place_ball(rolling.pop(0))
        next_roll_at = now + roll_cell_seconds
        roll_cell_seconds = max(ROLL_MIN_CELL_SECONDS, roll_cell_seconds * ROLL_ACCELERATION)
        if not rolling:
            finish_roll(now)
        return
    if tilt_action is None:
        return
    path, roll_outcome = slide_path(maze["cells"], ball, tilt_action)
    if path:
        moves += 1
        rolling = path
        next_roll_at = now
        roll_cell_seconds = ROLL_FIRST_CELL_SECONDS


def train_tick(now):
    global episode, next_step_at
    # Both branches use rng identically, so speed does not change what is learned.
    if speed <= STEP_MODE_UP_TO:
        if now < next_step_at:
            return
        next_step_at = now + seconds_per_move()
        if episode is None:
            episode = Episode(maze)
            trail.clear()
            trail.append(maze["start"])
        pos, done = episode.step(q, maze_model.EPSILON, rng)
        place_ball(pos)
        trail.append(pos)
        if done:
            finish_episode(episode.result())
            episode = None
        return
    if episode is not None:
        while not episode.done:
            episode.step(q, maze_model.EPSILON, rng)
        finish_episode(episode.result())
        episode = None
    trail.clear()
    result = None
    count = max(1, round(((speed - STEP_MODE_UP_TO) / (100 - STEP_MODE_UP_TO)) ** 2 * MAX_EPISODES_PER_TICK))
    for _ in range(count):
        result = run_episode(q, maze, maze_model.EPSILON, rng=rng)
        finish_episode(result)
    place_ball(result["path"][-1] if result["path"] else maze["start"])


def demo_tick(now):
    global mode, ai_moves, next_step_at
    if now < next_step_at:
        return
    next_step_at = now + DEMO_STEP_SECONDS
    if demo_path:
        place_ball(demo_path.pop(0))
        return
    mode = "paused"
    if demo_success:
        ai_moves = len(greedy_path(q, maze)[0])
        Bridge.call("pulse", 250)
        human = f"{human_moves} moves" if human_moves is not None else "skipped"
        print(f"AI escaped in {ai_moves} moves (you: {human}, best possible: {maze['optimal']}).")
        print("Tap the knob to move the exit.")
    else:
        ai_moves = None
        print("It has not learned a route yet. Button B resumes training.")


def update_pixels():
    if mode == "human":
        show(BLUE, 8)
    elif mode == "demo":
        show(WHITE, 8)
    else:
        count = max(1, round(success_rate() * 8)) if recent else 0
        show(GREEN if mode == "training" else AMBER, count)


def caption():
    if maze is None:
        return "Starting..."
    if mode == "human":
        return f"Your turn: tilt the board to roll the ball into the blinking exit. Best possible: {maze['optimal']} moves."
    if mode == "demo":
        return "Race: the AI plays the best route it knows."
    if mode == "paused" and ai_moves is not None:
        you = f"You: {human_moves} moves" if human_moves is not None else "You: skipped"
        return f"{you}. AI: {ai_moves} moves. Best possible: {maze['optimal']}. Tap the knob to move the exit."
    if mode == "paused" and episodes == 0:
        you = f"You escaped in {human_moves} moves. " if human_moves is not None else ""
        return f"{you}Press Button B to let the AI try the same maze, starting with no map."
    if mode == "paused":
        return "Paused. Button B resumes, Button C races."
    attempt = f"Attempt {episodes + 1}"
    if moved_at is not None and learned_at is None:
        return (f"{attempt}: the exit moved. Its arrows still point to the old exit, "
                "so it has to unlearn them and find the new one.")
    if learned_at is not None:
        again = "again " if moved_at is not None else ""
        return (f"Learned {again}in {learned_at - (moved_at or 0)} attempts: its route is the best possible. "
                "It still tries a random move now and then, to keep exploring. Press C to race it.")
    if agent_found_goal:
        return (f"{attempt}: arrows show moves it has learned lead to the exit. "
                "Each escape spreads them one step further back.")
    return f"{attempt}: exploring at random. It has no map, only points: -1 per move, +10 for the exit."


def state():
    return {
        "mode": mode,
        "caption": caption(),
        "maze_number": maze_number,
        "rows": ROWS,
        "cols": COLS,
        "cells": list(maze["cells"]) if maze else [],
        "start": maze["start"] if maze else None,
        "episodes": episodes,
        "success_rate": round(success_rate(), 3),
        "speed": speed,
        "arrows": arrows(q) if q else [],
        "strength": [round(max(0.0, min(1.0, max(row) / maze_model.GOAL_REWARD)), 2) for row in q] if q else [],
        "attempts": list(attempts),
        "first_attempt": episodes - len(attempts) + 1,
        "moved_at": moved_at,
        "max_moves": maze_model.MAX_STEPS,
        "human_moves": human_moves,
        "human_seconds": human_seconds,
        "ai_moves": ai_moves,
        "optimal_moves": maze["optimal"] if maze else None,
    }


def live():
    return {"mode": mode, "ball": ball, "tilt": [round(value, 3) for value in tilt], "trail": list(trail)}


def start():
    print("\n=== 301 AI Maze ===")
    new_maze()


def stop():
    pass


def loop():
    global next_control_at
    now = time.monotonic()
    poll_tilt()
    if now >= next_control_at:
        next_control_at = now + CONTROL_SECONDS
        handle_buttons()
        update_knob()
        if mode == "training":
            train_tick(now)
        elif mode == "demo":
            demo_tick(now)
        update_pixels()
    if mode == "human":
        human_tick(now)
    time.sleep(TILT_POLL_SECONDS)
