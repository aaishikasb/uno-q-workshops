import time


class Game:
    def __init__(self, predict):
        self.predict = predict
        self.round_id = 0
        self.reset()

    def reset(self):
        self.history = []
        self.player = self.board = self.rounds = 0
        self.pending = False
        self.prediction = None

    @property
    def finished(self):
        return self.rounds == 16

    def prepare(self):
        if self.pending or self.finished:
            raise RuntimeError("Cannot prepare another round")
        self.prediction = None
        if len(self.history) == 8:
            prediction = self.predict(tuple(self.history))
            if type(prediction) is not int or prediction not in (-1, 1):
                raise ValueError("Invalid prediction")
            self.prediction = prediction
        self.round_id += 1
        self.pending = True
        return self.round_id

    def commit(self, round_id, choice):
        if type(choice) is not int or choice not in (-1, 1):
            raise ValueError("Invalid choice")
        if not self.pending or round_id != self.round_id:
            return False
        self.pending = False
        if self.prediction is not None:
            self.rounds += 1
            if choice == self.prediction:
                self.board += 1
            else:
                self.player += 1
        self.history = (self.history + [choice])[-8:]
        return True


class Controller:
    def __init__(self, bridge, predict, clock=time.monotonic, log=print):
        self.bridge, self.clock, self.log = bridge, clock, log
        self.game = Game(predict)
        self.phase = "starting"
        self.deadline = 0

    def call(self, name, *args):
        value = self.bridge.call(name, *args, timeout=0.5)
        if type(value) is not int or value < 0:
            raise RuntimeError(f"MCU rejected {name}: {value!r}")
        return value

    def start(self):
        self.call("reset_game")
        self.game.reset()
        self.log("Eight warm-up choices, then sixteen scored rounds. Turn to select; press to commit.")
        self.open_round()

    def open_round(self):
        # Inference has no access to the MCU; selection opens only after it returns.
        token = self.game.prepare()
        self.log(f"Round {token}: {'prediction locked' if self.game.prediction is not None else 'warm-up'}; choose now.")
        if self.call("open_round", token, len(self.game.history)) != token:
            raise RuntimeError("MCU round mismatch")
        self.phase = "select"

    def step(self):
        if self.phase == "error":
            return
        try:
            if self.phase == "starting":
                self.start()
                return
            event = self.call("poll_event")
            token, code = divmod(event, 4)
            if self.phase == "select" and event:
                if token != self.game.round_id or code not in (1, 2):
                    raise RuntimeError("Stale or invalid MCU event; restart the app")
                choice = -1 if code == 1 else 1
                if self.game.commit(token, choice):
                    g = self.game
                    self.call("show_feedback", token, g.prediction or 0, choice, g.player, g.board, len(g.history))
                    if g.prediction is None:
                        self.log(f"Warm-up {len(g.history)}/8")
                    else:
                        names = {-1: "LEFT", 1: "RIGHT"}
                        self.log(f"You: {names[choice]}; board: {names[g.prediction]}. Score: you {g.player}, board {g.board} ({g.rounds}/16).")
                    self.phase = "feedback"
                    self.deadline = self.clock() + (0.6 if g.prediction is None else 1.6)
            elif self.phase == "feedback" and self.clock() >= self.deadline:
                g = self.game
                if g.finished:
                    self.call("show_result", g.round_id, g.player, g.board)
                    result = "You win!" if g.player > g.board else "Board wins!" if g.board > g.player else "Draw!"
                    self.log(f"{result} You {g.player}, board {g.board}. Release, then press to play again.")
                    self.phase = "result"
                else:
                    self.open_round()
            elif self.phase == "result" and event:
                if token != self.game.round_id or code != 3:
                    raise RuntimeError("Invalid restart event")
                self.start()
        except Exception as error:
            self.phase = "error"
            self.log(f"GAME PAUSED: {error}. Check modules and connection, then restart the app.")
            try:
                self.bridge.call("show_error", timeout=0.5)
            except Exception:
                pass  # MCU watchdog disables input if Bridge is unavailable.
