"""Safe-cracking game rules. Pure Python so it can be tested without hardware."""

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Stage:
    dial_size: int  # Knob steps in one full turn of the dial.
    tolerance: int  # Steps either side of a target that count as "on it".
    hold_seconds: float  # How long to stay on a target for the tumbler to fall.
    hint_range: int  # Distance at which the haptic "getting warmer" starts.
    time_limit: float | None  # Seconds from the first turn, or None.
    combo_length: int  # Targets to find, in order.


STAGES = (
    Stage(24, 3, 0.5, 12, None, 1),
    Stage(32, 2, 0.7, 12, None, 1),
    Stage(40, 2, 0.9, 12, 45.0, 1),
    Stage(48, 1, 0.9, 10, 45.0, 2),
    Stage(56, 1, 1.1, 8, 50.0, 2),
    Stage(64, 1, 1.2, 6, 55.0, 3),
    Stage(72, 1, 1.5, 5, 60.0, 3),
)

TUMBLER = "tumbler"  # One number of the combination was found.
STAGE_CLEAR = "stage_clear"
GAME_WON = "game_won"
TIMEOUT = "timeout"


@dataclass(frozen=True)
class Update:
    event: str | None
    warmth: int  # 0 = cold, 1-99 = warming, 100 = on a target.
    moved: bool


def circular_distance(a, b, size):
    diff = abs(a - b) % size
    return min(diff, size - diff)


class SafeGame:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.cleared = 0
        self.won = False
        self._start_stage_state()

    @property
    def stage(self):
        return STAGES[min(self.cleared, len(STAGES) - 1)]

    def new_game(self):
        self.cleared = 0
        self.won = False
        self._start_stage_state()

    def restart_stage(self):
        self._start_stage_state()

    def time_left(self, now):
        if self.stage.time_limit is None or self.started_at is None:
            return None
        return max(0.0, self.stage.time_limit - (now - self.started_at))

    def update(self, now, raw):
        """Feed one knob reading. Returns an Update."""
        if self.won:
            return Update(None, 0, False)
        stage = self.stage
        if self.origin is None:
            self.origin = raw
            self._pick_targets()

        position = (raw - self.origin) % stage.dial_size
        moved = position != self.position
        self.position = position
        if moved and self.started_at is None:
            self.started_at = now

        if self.time_left(now) == 0.0:
            self._start_stage_state()
            return Update(TIMEOUT, 0, moved)

        distance = circular_distance(position, self.targets[self.step], stage.dial_size)
        on_target = distance <= stage.tolerance
        warmth = self._warmth(distance, stage)

        event = None
        if on_target:
            if self.on_target_since is None:
                self.on_target_since = now
            if now - self.on_target_since >= stage.hold_seconds:
                event = self._advance()
                warmth = 0 if event != TUMBLER else warmth
        else:
            self.on_target_since = None
        return Update(event, warmth, moved)

    def _advance(self):
        self.on_target_since = None
        self.step += 1
        if self.step < self.stage.combo_length:
            return TUMBLER
        self.cleared += 1
        if self.cleared == len(STAGES):
            self.won = True
            return GAME_WON
        self._start_stage_state()
        return STAGE_CLEAR

    def _start_stage_state(self):
        # The next update() re-zeroes the dial, so every stage starts at 0.
        self.origin = None
        self.position = 0
        self.targets = []
        self.step = 0
        self.started_at = None
        self.on_target_since = None

    def _pick_targets(self):
        size = self.stage.dial_size
        min_gap = size // 4
        previous = 0  # The dial reads 0 right after the re-zero.
        self.targets = []
        for _ in range(self.stage.combo_length):
            while True:
                candidate = self.rng.randrange(size)
                if circular_distance(candidate, previous, size) >= min_gap:
                    break
            self.targets.append(candidate)
            previous = candidate

    @staticmethod
    def _warmth(distance, stage):
        if distance <= stage.tolerance:
            return 100
        if distance > stage.hint_range:
            return 0
        span = max(1, stage.hint_range - stage.tolerance)
        return max(1, round((1 - (distance - stage.tolerance) / span) * 99))
