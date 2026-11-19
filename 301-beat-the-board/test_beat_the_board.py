"""Run from the repo root: python3 -B 301-beat-the-board/test_beat_the_board.py."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "workshop-app" / "python"))
from game import Controller, Game
from opponent import choose, validate_history


class FakeBridge:
    def __init__(self):
        self.calls = []
        self.event = 0
        self.fail = None

    def call(self, name, *args, timeout=0.5):
        self.calls.append((name, args))
        if name == self.fail:
            raise TimeoutError("simulated disconnection")
        if name == "poll_event":
            return self.event
        if name in ("show_feedback", "reset_game", "show_result"):
            self.event = 0
        return args[0] if args else 0


class WorkshopTests(unittest.TestCase):
    def test_complete_match_duplicate_events_and_reset(self):
        observed = []
        def predict(history):
            observed.append(history)
            return -1
        game = Game(predict)
        for turn in range(24):
            token = game.prepare()
            choice = -1 if turn % 2 == 0 else 1
            before = tuple(game.history)
            self.assertFalse(game.commit(token - 1, choice))
            self.assertEqual(tuple(game.history), before)
            self.assertTrue(game.commit(token, choice))
            self.assertFalse(game.commit(token, choice))
            if turn < 8:
                self.assertEqual(game.player + game.board, 0)
            else:
                self.assertEqual(observed[-1], before)
        self.assertEqual((game.rounds, game.player, game.board), (16, 8, 8))
        self.assertEqual(len(observed), 16)
        with self.assertRaises(RuntimeError):
            game.prepare()
        game.reset()
        self.assertEqual(game.history, [])
        self.assertGreater(game.prepare(), token)

    def test_prediction_cannot_be_mutated_or_recomputed(self):
        game = Game(lambda history: 1)
        game.history = [-1] * 8
        game.prepare()
        with self.assertRaises(RuntimeError):
            game.prepare()
        with self.assertRaises(ValueError):
            game.commit(game.round_id, True)
        self.assertTrue(game.pending)
        self.assertEqual(game.prediction, 1)

    def test_controller_orders_inference_before_input_and_restarts(self):
        bridge, now, predictions = FakeBridge(), [0.0], []
        def predict(history):
            self.assertNotEqual(bridge.calls[-1][0], "open_round")
            predictions.append(tuple(history))
            return -1
        app = Controller(bridge, predict, clock=lambda: now[0], log=lambda _: None)
        app.step()
        for turn in range(24):
            self.assertEqual(app.phase, "select")
            bridge.event = app.game.round_id * 4 + (1 if turn % 2 == 0 else 2)
            app.step()
            self.assertEqual(app.phase, "feedback")
            app.step()
            self.assertEqual(app.phase, "feedback")
            now[0] += 2
            app.step()
        self.assertEqual(app.phase, "result")
        self.assertEqual(len(predictions), 16)
        bridge.event = app.game.round_id * 4 + 3
        app.step()
        self.assertEqual(app.phase, "select")
        self.assertEqual(app.game.history, [])

    def test_failure_closes_game_without_retrying_or_scoring(self):
        for failure in ("poll_event", "open_round"):
            bridge = FakeBridge()
            app = Controller(bridge, lambda _: -1, log=lambda _: None)
            app.step()
            bridge.fail = failure
            if failure == "open_round":
                app.phase, app.deadline = "feedback", 0
                app.game.pending = False
            app.step()
            self.assertEqual(app.phase, "error")
            self.assertEqual(app.game.player + app.game.board, 0)
            self.assertEqual(bridge.calls[-1][0], "show_error")
            count = len(bridge.calls)
            app.step()
            self.assertEqual(len(bridge.calls), count)

    def test_stale_events_and_bad_predictions_fail_closed(self):
        bridge = FakeBridge()
        app = Controller(bridge, lambda _: -1, log=lambda _: None)
        app.step()
        bridge.event = (app.game.round_id + 1) * 4 + 1
        app.step()
        self.assertEqual(app.phase, "error")
        game = Game(lambda _: 0)
        game.history = [-1] * 8
        with self.assertRaises(ValueError):
            game.prepare()
        self.assertFalse(game.pending)

    def test_model_input_and_output_boundaries(self):
        for row in ([], [-1] * 7, [0] * 8, [True] * 8, [1.0] * 8):
            with self.assertRaises(ValueError):
                validate_history(row)
        for logits in ([0], [float("nan"), 0], [0, float("inf")]):
            with self.assertRaises(ValueError):
                choose(logits)
        self.assertEqual(choose([1, 1]), -1)
        fixtures = json.loads((ROOT / "workshop-app/python/models/fixtures.json").read_text())
        self.assertEqual(len({tuple(f["history"]) for f in fixtures}), 256)

    @unittest.skipUnless(shutil.which("c++"), "C++ compiler required for MCU simulation")
    def test_actual_sketch_with_simulated_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "test_sketch")
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "tests" / "stubs"),
                            str(ROOT / "tests" / "test_sketch.cpp"), "-o", binary], check=True)
            subprocess.run([binary], check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
