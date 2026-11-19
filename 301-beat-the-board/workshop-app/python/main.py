import time

from arduino.app_utils import App, Bridge

from game import Controller
from opponent import Opponent


def main():
    try:
        opponent = Opponent()
    except Exception as error:
        print(f"MODEL ERROR: {error}. Restore the model files and pinned dependencies, then restart.", flush=True)
        try:
            Bridge.call("show_error", timeout=0.5)
        except Exception:
            pass
        raise
    print(f"ExecuTorch opponent loaded: XNNPACK, {opponent.load_ms:.1f} ms.", flush=True)
    controller = Controller(Bridge, opponent.predict, log=lambda line: print(line, flush=True))

    def loop():
        controller.step()
        time.sleep(0.02)

    App.run(user_loop=loop)


if __name__ == "__main__":
    main()
