"""Sliding tilt maze and a tabular Q-learning agent, standard library only."""

from collections import deque
import random


ROWS = 8
COLS = 13
CELLS = ROWS * COLS
EMPTY, WALL, GOAL, TRAP = 0, 1, 2, 3
ACTIONS = ("up", "right", "down", "left")
STEPS = ((-1, 0), (0, 1), (1, 0), (0, -1))

GOAL_REWARD = 10
STEP_REWARD = -1
TRAP_REWARD = -50
ALPHA = 0.5
GAMMA = 0.9
EPSILON = 0.2
MAX_STEPS = 60
WALL_RATIO = 0.3
# Fixed seeds so every board trains Maze #1 identically.
DEMO_MAZE_SEED = 240
DEMO_AGENT_SEED = 1


def slide_path(cells, pos, action):
    """Return every cell the ball rolls through, and 'goal', 'trap', or None."""
    row, col = divmod(pos, COLS)
    d_row, d_col = STEPS[action]
    path = []
    while True:
        row, col = row + d_row, col + d_col
        if not (0 <= row < ROWS and 0 <= col < COLS) or cells[row * COLS + col] == WALL:
            return path, None
        index = row * COLS + col
        path.append(index)
        # The goal and traps are holes: the ball drops in as it rolls over them.
        if cells[index] == GOAL:
            return path, "goal"
        if cells[index] == TRAP:
            return path, "trap"


def slide(cells, pos, action):
    path, outcome = slide_path(cells, pos, action)
    return (path[-1] if path else pos), outcome


def shortest_actions(maze):
    """Breadth-first search over ball resting positions; None if the goal is unreachable."""
    start = maze["start"]
    previous = {start: None}
    queue = deque([start])
    while queue:
        pos = queue.popleft()
        for action in range(len(ACTIONS)):
            nxt, outcome = slide(maze["cells"], pos, action)
            if outcome == "trap" or nxt == pos:
                continue
            if outcome == "goal":
                actions = [action]
                while previous[pos] is not None:
                    pos, step = previous[pos]
                    actions.append(step)
                return actions[::-1]
            if nxt not in previous:
                previous[nxt] = (pos, action)
                queue.append(nxt)
    return None


def optimal_moves(maze):
    actions = shortest_actions(maze)
    return None if actions is None else len(actions)


def generate(seed, traps=0, min_moves=4, attempts=5000):
    rng = random.Random(seed)
    for _ in range(attempts):
        cells = [WALL if rng.random() < WALL_RATIO else EMPTY for _ in range(CELLS)]
        free = [i for i, cell in enumerate(cells) if cell == EMPTY]
        if len(free) < 2 + traps:
            continue
        start, goal, *trap_cells = rng.sample(free, 2 + traps)
        cells[goal] = GOAL
        for index in trap_cells:
            cells[index] = TRAP
        maze = {"cells": cells, "start": start, "goal": goal, "traps": trap_cells, "seed": seed}
        moves = optimal_moves(maze)
        if moves is not None and moves >= min_moves:
            maze["optimal"] = moves
            return maze
    raise ValueError("Could not generate a solvable maze; lower min_moves or traps")


# Target re-learning time after the exit moves, in agent moves (25-70 s at the default speed).
RELEARN_MOVES = (120, 360)


def relearn_moves(maze, q, rng_state, limit):
    """Replay training ahead on copies of q and the random numbers: moves until the route is optimal, or None."""
    rng = random.Random()
    rng.setstate(rng_state)
    q = [list(values) for values in q]
    moves = 0
    while moves <= limit:
        moves += run_episode(q, maze, EPSILON, rng=rng)["steps"]
        path, success = greedy_path(q, maze)
        if success and len(path) == maze["optimal"]:
            return moves
    return None


def move_goal(maze, q=None, rng=None, min_moves=4, max_moves=8, window=RELEARN_MOVES):
    """Move the exit to an open cell min_moves..max_moves from the start.

    With q and rng, replays training for each candidate and picks the one re-learned closest to the
    middle of `window`. Otherwise picks the cell farthest from the old exit.
    """
    old = maze["goal"]
    candidates = []
    for index, cell in enumerate(maze["cells"]):
        if cell != EMPTY or index == maze["start"]:
            continue
        cells = list(maze["cells"])
        cells[old] = EMPTY
        cells[index] = GOAL
        candidate = {**maze, "cells": cells, "goal": index}
        moves = optimal_moves(candidate)
        if moves is None or not min_moves <= moves <= max_moves:
            continue
        candidate["optimal"] = moves
        distance = abs(index // COLS - old // COLS) + abs(index % COLS - old % COLS)
        candidates.append((distance, candidate))
    if not candidates:
        return None
    candidates.sort(key=lambda item: -item[0])
    if q is not None and rng is not None:
        state, low, high = rng.getstate(), window[0], window[1]
        best = None
        for distance, candidate in candidates:
            moves = relearn_moves(candidate, q, state, 2 * high)
            if moves is None:
                continue
            score = abs(moves - (low + high) / 2) if low <= moves <= high else high + max(low - moves, moves - high)
            if best is None or score < best[0]:
                best = (score, candidate)
        if best is not None:
            return best[1]
    return candidates[0][1]


def arrows(q):
    """Per cell: best action (0-3) if its value is above 0, -1 if visited, -2 if never visited."""
    result = []
    for values in q:
        best = max(values)
        if best > 0:
            result.append(values.index(best))
        else:
            result.append(-1 if any(values) else -2)
    return result


def new_q():
    return [[0.0] * len(ACTIONS) for _ in range(CELLS)]


def choose(q, state, eps, rng):
    if rng.random() < eps:
        return rng.randrange(len(ACTIONS))
    best = max(q[state])
    return rng.choice([a for a, value in enumerate(q[state]) if value == best])


def reward_for(outcome):
    if outcome == "goal":
        return GOAL_REWARD
    if outcome == "trap":
        return TRAP_REWARD
    return STEP_REWARD


class Episode:
    """One attempt that can be advanced a move at a time, so the matrix can animate it."""

    def __init__(self, maze):
        self.maze = maze
        self.pos = maze["start"]
        self.reward = 0.0
        self.steps = 0
        self.success = False
        self.done = False
        self.path = []

    def step(self, q, eps, rng, alpha=None, gamma=None, max_steps=None):
        alpha = ALPHA if alpha is None else alpha
        gamma = GAMMA if gamma is None else gamma
        max_steps = MAX_STEPS if max_steps is None else max_steps
        state = self.pos
        action = choose(q, state, eps, rng)
        nxt, outcome = slide(self.maze["cells"], state, action)
        reward = reward_for(outcome)
        target = reward if outcome else reward + gamma * max(q[nxt])
        q[state][action] += alpha * (target - q[state][action])
        self.pos = nxt
        self.reward += reward
        self.steps += 1
        self.path.append(nxt)
        self.success = outcome == "goal"
        self.done = outcome is not None or self.steps >= max_steps
        return nxt, self.done

    def result(self):
        return {"reward": self.reward, "success": self.success, "steps": self.steps, "path": list(self.path)}


def run_episode(q, maze, eps, alpha=None, gamma=None, rng=None, max_steps=None):
    rng = rng or random.Random()
    episode = Episode(maze)
    while not episode.done:
        episode.step(q, eps, rng, alpha, gamma, max_steps)
    return episode.result()


def greedy_path(q, maze, max_steps=None):
    """Follow the best-known action from the start; stops on a repeated position."""
    max_steps = MAX_STEPS if max_steps is None else max_steps
    pos = maze["start"]
    seen = {pos}
    path = []
    for _ in range(max_steps):
        action = q[pos].index(max(q[pos]))
        pos, outcome = slide(maze["cells"], pos, action)
        path.append(pos)
        if outcome:
            return path, outcome == "goal"
        if pos in seen:
            return path, False
        seen.add(pos)
    return path, False
