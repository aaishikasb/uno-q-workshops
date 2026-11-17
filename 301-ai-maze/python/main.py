from arduino.app_utils import App, Bridge

from collections import deque
import random
import time

import maze_model
from maze_model import COLS, ROWS, WALL, Episode, generate, greedy_path, new_q, run_episode, slide_path

try:
    from arduino.app_bricks.web_ui import WebUI
except ImportError:
    WebUI = None


TRAPS = 0
MIN_MOVES = 4
STEP_MODE_BELOW = 10
MAX_EPISODES_PER_TICK = 50
DEMO_STEP_SECONDS = 0.35
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

rng = random.Random()
initialized = False
mode = "human"
maze = None
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
knob_target = "speed"
speed = 5
epsilon = maze_model.EPSILON
episodes = 0
recent = deque(maxlen=20)
rewards = deque(maxlen=200)
agent_found_goal = False
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
        Bridge.call("show", color, count)
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
    print(f"HUMAN ROUND: tilt the board to roll the ball into the blinking exit. Best possible: {maze['optimal']} moves.")
    print("Button A = new maze, Button B = skip to AI training.")


def new_maze():
    global maze, q, episodes, agent_found_goal, episode, demo_path, human_moves, human_seconds, ai_moves
    maze = generate(rng.randrange(1_000_000), traps=TRAPS, min_moves=MIN_MOVES)
    q = new_q()
    episodes = 0
    recent.clear()
    rewards.clear()
    agent_found_goal = False
    episode = None
    demo_path = []
    human_moves = human_seconds = ai_moves = None
    draw_maze()
    start_human()


def start_training():
    global mode, episode
    mode = "training"
    episode = None
    place_ball(maze["start"])
    print("AI TRAINING: turn the knob for speed (low = watch every move). Press the knob to switch it to epsilon.")
    print("Button B = pause, Button C = watch the trained agent, Button A = new maze.")


def start_demo():
    global mode, demo_path, demo_success, next_step_at
    path, demo_success = greedy_path(q, maze)
    demo_path = list(path)
    mode = "demo"
    next_step_at = time.monotonic() + DEMO_STEP_SECONDS
    place_ball(maze["start"])
    print("DEMO: the agent plays its best-known route.")


def finish_episode(result):
    global episodes, agent_found_goal
    episodes += 1
    recent.append(result["success"])
    rewards.append(round(result["reward"], 1))
    if result["success"] and not agent_found_goal:
        agent_found_goal = True
        Bridge.call("pulse", 150)
        print(f"Episode {episodes}: the agent reached the exit for the first time.")


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
            print(f"PAUSED after {episodes} episodes. Button B resumes, Button C demos.")
        elif mode == "paused":
            mode = "training"
            print("Training resumed.")
    if pressed & 4 and mode in ("training", "paused"):
        start_demo()


def knob_value():
    return speed if knob_target == "speed" else round(epsilon * 100)


def update_knob():
    global last_knob_pressed, knob_target, speed, epsilon
    pressed = int(Bridge.call("read_knob_pressed"))
    toggled = pressed and not last_knob_pressed
    last_knob_pressed = pressed
    if toggled:
        knob_target = "epsilon" if knob_target == "speed" else "speed"
        Bridge.call("set_knob", knob_value())
        print(f"Knob now controls {knob_target} (currently {knob_value()}).")
        return
    raw = int(Bridge.call("read_knob"))
    value = max(0, min(100, raw))
    if value != raw:
        Bridge.call("set_knob", value)
    if knob_target == "speed":
        speed = value
    else:
        epsilon = value / 100


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
        print(f"YOU ESCAPED in {human_moves} moves and {human_seconds}s. Now watch the AI learn the same maze.")
        start_training()
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
    # No need to level the board between moves: a stopped ball already rests against a
    # wall in the direction it last rolled, so a held tilt only rolls when there is room.
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
    if speed < STEP_MODE_BELOW:
        if now < next_step_at:
            return
        next_step_at = now + 0.5 - speed * 0.04
        if episode is None:
            episode = Episode(maze)
        pos, done = episode.step(q, epsilon, rng)
        place_ball(pos)
        if done:
            finish_episode(episode.result())
            episode = None
        return
    episode = None
    result = None
    for _ in range(max(1, round((speed / 100) ** 2 * MAX_EPISODES_PER_TICK))):
        result = run_episode(q, maze, epsilon, rng=rng)
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
        print(f"AI escaped in {ai_moves} moves (human: {human}, best possible: {maze['optimal']}).")
    else:
        ai_moves = None
        print("The agent has not learned a route yet. Button B resumes training.")


def update_pixels():
    if mode == "human":
        show(BLUE, 8)
    elif mode == "demo":
        show(WHITE, 8)
    else:
        count = max(1, round(success_rate() * 8)) if recent else 0
        show(GREEN if mode == "training" else AMBER, count)


def state():
    return {
        "mode": mode,
        "rows": ROWS,
        "cols": COLS,
        "cells": list(maze["cells"]) if maze else [],
        "start": maze["start"] if maze else None,
        "ball": ball,
        "tilt": [round(value, 3) for value in tilt],
        "episodes": episodes,
        "success_rate": round(success_rate(), 3),
        "epsilon": epsilon,
        "speed": speed,
        "knob_target": knob_target,
        "values": [round(max(row), 2) for row in q] if q else [],
        "rewards": list(rewards),
        "human_moves": human_moves,
        "human_seconds": human_seconds,
        "ai_moves": ai_moves,
        "optimal_moves": maze["optimal"] if maze else None,
    }


def live():
    return {"mode": mode, "ball": ball, "tilt": [round(value, 3) for value in tilt]}


def loop():
    global initialized, next_control_at
    if not initialized:
        # Right after flashing, the MCU can time out or reply "method not available" until setup() finishes.
        try:
            Bridge.call("set_knob", speed)
        except Exception as error:
            print(f"Waiting for the MCU sketch to answer ({error}). If this repeats, check the sketch compiled and flashed.")
            time.sleep(1)
            return
        new_maze()
        initialized = True
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
    # Shorter than the usual 0.05 s so the tilt and the 3D board follow the hand closely.
    time.sleep(TILT_POLL_SECONDS)


ui = WebUI() if WebUI else None
if ui is not None:
    try:
        ui.expose_api("GET", "/api/state", state)
        ui.expose_api("GET", "/api/tilt", live)
    except Exception as error:
        print(f"Dashboard unavailable ({error}); the board game still works.")


if __name__ == "__main__":
    print("UNO Q AI Maze starting...")
    App.run(user_loop=loop)
