"""Best-of-five Reaction Duel rules and a fastest-reaction leaderboard, with no hardware calls."""

import json
from pathlib import Path


PLAYERS = ("Player 1", "Player 2")
WINS_NEEDED = 3
LEADERBOARD_SIZE = 10
MINIMUM_MS = 80
MAXIMUM_MS = 2000
WIN_CODES = {1: 0, 2: 1}
FALSE_START_CODES = {11: 0, 12: 1}
TIMEOUT_CODE = 0


def decode(code, reaction_ms):
    """Turn the MCU result code into who won, who false-started, and the winning time."""
    if type(code) is not int or type(reaction_ms) is not int:
        raise ValueError("Duel results must be integers")
    if code == TIMEOUT_CODE:
        return {"winner": None, "false_start": None, "reaction_ms": 0}
    if code in FALSE_START_CODES:
        offender = FALSE_START_CODES[code]
        return {"winner": 1 - offender, "false_start": offender, "reaction_ms": 0}
    if code in WIN_CODES:
        if not 0 <= reaction_ms <= MAXIMUM_MS:
            raise ValueError("Reaction time is outside 0-2000 ms")
        return {"winner": WIN_CODES[code], "false_start": None, "reaction_ms": reaction_ms}
    raise ValueError(f"Unknown duel result {code}")


def counts_for_leaderboard(result):
    # Sub-80 ms wins are anticipation, not reaction, so they score but do not rank.
    return result["winner"] is not None and result["false_start"] is None and result["reaction_ms"] >= MINIMUM_MS


class Match:
    def __init__(self):
        self.score = [0, 0]
        self.rounds = []

    @property
    def over(self):
        return max(self.score) >= WINS_NEEDED

    @property
    def winner(self):
        return self.score.index(max(self.score)) if self.over else None

    def record(self, code, reaction_ms):
        if self.over:
            raise ValueError("The match is over; start a new one")
        result = decode(code, reaction_ms)
        if result["winner"] is not None:
            self.score[result["winner"]] += 1
        self.rounds.append(result)
        return result

    def fastest(self):
        times = [row["reaction_ms"] for row in self.rounds if counts_for_leaderboard(row)]
        return min(times) if times else None


def describe(result, round_number, score):
    tally = f"(score {score[0]}-{score[1]})"
    if result["winner"] is None:
        return f"Round {round_number}: nobody pressed within two seconds {tally}"
    if result["false_start"] is not None:
        return (f"Round {round_number}: FALSE START by {PLAYERS[result['false_start']]}, "
                f"point to {PLAYERS[result['winner']]} {tally}")
    return f"Round {round_number}: {PLAYERS[result['winner']]} wins in {result['reaction_ms']} ms {tally}"


def add_entry(board, player, reaction_ms, match_number):
    entry = {"player": PLAYERS[player], "reaction_ms": reaction_ms, "match": match_number}
    board = sorted(board + [entry], key=lambda row: row["reaction_ms"])
    return board[:LEADERBOARD_SIZE]


def save(board, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"version": 1, "entries": board}, indent=2), encoding="utf-8")
    temporary.replace(path)


def load(path):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("entries"), list):
        raise ValueError("Unsupported leaderboard file")
    for row in data["entries"]:
        if (not isinstance(row, dict) or row.get("player") not in PLAYERS
                or type(row.get("reaction_ms")) is not int or not MINIMUM_MS <= row["reaction_ms"] <= MAXIMUM_MS
                or type(row.get("match")) is not int or row["match"] < 1):
            raise ValueError("Invalid leaderboard entry")
    return sorted(data["entries"], key=lambda row: row["reaction_ms"])[:LEADERBOARD_SIZE]
