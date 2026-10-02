"""Run with: python3 -B 104-safe-cracker/test_safe_cracker.py"""

from pathlib import Path
import random
import sys

sys.path.insert(0, str(Path(__file__).parent / "workshop-app" / "python"))
from lock_game import (
    GAME_WON, STAGE_CLEAR, STAGES, TIMEOUT, TUMBLER, SafeGame, circular_distance,
)


def solve_stage(game, now, raw_start=1000):
    """Drive the dial straight to the current target(s). Returns (now, last event)."""
    game.update(now, raw_start)  # Zeroes the dial and picks targets.
    event = None
    for target in list(game.targets):
        raw = raw_start + target
        game.update(now, raw)
        now += game.stage.hold_seconds + 0.01
        event = game.update(now, raw).event
        now += 0.1
    return now, event


def check():
    assert circular_distance(1, 23, 24) == 2
    assert circular_distance(0, 12, 24) == 12

    # Difficulty only ever gets harder.
    assert len(STAGES) == 7
    for easy, hard in zip(STAGES, STAGES[1:]):
        assert hard.dial_size >= easy.dial_size
        assert hard.tolerance <= easy.tolerance
        assert hard.hint_range <= easy.hint_range
        assert hard.combo_length >= easy.combo_length
        assert hard.hold_seconds >= easy.hold_seconds

    for seed in range(50):
        game = SafeGame(random.Random(seed))
        now = 0.0

        # The dial re-zeroes per stage, and targets are spread out.
        game.update(now, 500)
        assert game.position == 0
        assert all(0 <= t < game.stage.dial_size for t in game.targets)

        # Warmth rises as the dial approaches the target and is 100 on it.
        target = game.targets[0]
        stage = game.stage
        assert game.update(now, 500 + target).warmth == 100
        near = (target + stage.tolerance + 2) % stage.dial_size
        far = (target + stage.dial_size // 2) % stage.dial_size
        warm_near = game.update(now, 500 + near).warmth
        warm_far = game.update(now, 500 + far).warmth
        assert warm_far <= warm_near < 100

        # Leaving the zone resets the hold timer.
        game = SafeGame(random.Random(seed))
        game.update(0.0, 0)
        target = game.targets[0]
        game.update(0.1, target)
        assert game.update(0.1 + stage.hold_seconds * 0.9, target).event is None
        game.update(0.1 + stage.hold_seconds * 0.95, (target + 8) % stage.dial_size)
        assert game.update(0.1 + stage.hold_seconds * 1.1, target).event is None

        # Full playthrough, including negative and wrapping raw knob values.
        game = SafeGame(random.Random(seed))
        now = 0.0
        for index, stage in enumerate(STAGES):
            assert game.cleared == index
            raw_start = -500 + index * 37
            now, event = solve_stage(game, now, raw_start)
            assert event == (GAME_WON if index == len(STAGES) - 1 else STAGE_CLEAR), event
        assert game.won and game.cleared == 7
        assert game.update(now, 0).event is None

    # Combos need every number, in order, with TUMBLER between them.
    game = SafeGame(random.Random(1))
    game.cleared = 5
    game.restart_stage()
    game.update(0.0, 0)
    first, second, third = game.targets
    events = []
    now = 0.1
    for target in (first, second, third):
        game.update(now, target)
        now += game.stage.hold_seconds + 0.01
        events.append(game.update(now, target).event)
        now += 0.1
    assert events == [TUMBLER, TUMBLER, STAGE_CLEAR]

    # The timer starts on the first turn, and a timeout reshuffles the stage.
    game = SafeGame(random.Random(2))
    game.cleared = 2  # Stage 3 has a 45 second limit.
    game.restart_stage()
    game.update(0.0, 0)
    assert game.time_left(100.0) is None  # Not started: the dial has not moved.
    target = game.targets[0]
    cold = (target + 20) % game.stage.dial_size
    game.update(100.0, cold)
    assert game.time_left(100.0) == 45.0
    assert game.update(146.0, cold).event == TIMEOUT
    assert game.cleared == 2 and game.targets == []

    # Press-to-restart gives a fresh stage; new_game clears progress.
    game.cleared = 4
    game.new_game()
    assert game.cleared == 0 and not game.won


if __name__ == "__main__":
    check()
    print("ok")
