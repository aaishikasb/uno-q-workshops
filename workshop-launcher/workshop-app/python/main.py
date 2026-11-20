"""UNO Q Workshop Launcher: pick 105, 201, or 301 with the Modulino Knob.

Menu: the LED matrix shows 1, 2, or 3. Turn the knob to choose, tap it to start.
In any app: hold the knob for 13 s to come back. After 5 s the Pixels count down the last 8 s,
one Pixel per second; let go during the countdown to stay in the app. The MCU times the hold.
"""

from arduino.app_utils import App, Bridge

import importlib
import time
import traceback

import app_duel
import app_gesture
import app_maze

try:
    from arduino.app_bricks.web_ui import WebUI
except ImportError:
    WebUI = None


APPS = {
    1: ("105 Reaction Duel", app_duel),
    2: ("201 Gesture Dial", app_gesture),
    3: ("301 AI Maze", app_maze),
}
# Knob steps per menu move. Raise it if the selection jumps too easily.
KNOB_STEPS_PER_CHOICE = 2
# A press shorter than this, then released, starts the selected app.
TAP_SECONDS = 1.0
MENU_POLL_SECONDS = 0.05
EXIT_CHECK_SECONDS = 0.1

initialized = False
active = 0  # 0 = menu, otherwise a key of APPS.
choice = 1
knob_anchor = 0
last_pressed = 0
pressed_at = None
next_exit_check = 0.0


def enter_menu():
    global active, knob_anchor, last_pressed, pressed_at
    Bridge.call("set_app", 0)
    active = 0
    knob_anchor = int(Bridge.call("read_knob"))
    # If the knob is still held from the exit hold, its release must not start an app.
    last_pressed = int(Bridge.call("read_knob_pressed"))
    pressed_at = None
    Bridge.call("show_menu", choice)
    print("\n=== UNO Q Workshop Launcher ===")
    print("Turn the knob to choose 1, 2, or 3 on the LED matrix, then tap it to start:")
    for number, (name, _) in APPS.items():
        print(f"  {number}: {name}")
    print("Inside an app, hold the knob for 13 seconds to come back here.")
    print(f"Selected: {choice} ({APPS[choice][0]})")


def launch(number):
    global active, next_exit_check
    name, module = APPS[number]
    # Reloading runs the module from the top, so every launch starts fresh, like a separate app.
    importlib.reload(module)
    Bridge.call("set_app", number)
    active = number
    next_exit_check = time.monotonic() + EXIT_CHECK_SECONDS
    module.start()


def leave_app(reason):
    name, module = APPS[active]
    try:
        module.stop()
    except Exception as error:
        print(f"{name} did not stop cleanly: {error}")
    print(f"\n{reason}")
    enter_menu()


def menu_tick():
    global choice, knob_anchor, last_pressed, pressed_at
    now = time.monotonic()
    position = int(Bridge.call("read_knob"))
    steps = int((position - knob_anchor) / KNOB_STEPS_PER_CHOICE)
    if steps:
        knob_anchor += steps * KNOB_STEPS_PER_CHOICE
        new_choice = max(1, min(len(APPS), choice + steps))
        if new_choice != choice:
            choice = new_choice
            Bridge.call("show_menu", choice)
            print(f"Selected: {choice} ({APPS[choice][0]})")
    pressed = int(Bridge.call("read_knob_pressed"))
    if pressed and not last_pressed:
        pressed_at = now
    if not pressed and last_pressed and pressed_at is not None:
        tapped = now - pressed_at < TAP_SECONDS
        pressed_at = None
        last_pressed = pressed
        if tapped:
            Bridge.call("pulse", 120)
            launch(choice)
            return
    last_pressed = pressed
    time.sleep(MENU_POLL_SECONDS)


def app_tick():
    global next_exit_check
    now = time.monotonic()
    if now >= next_exit_check:
        next_exit_check = now + EXIT_CHECK_SECONDS
        if int(Bridge.call("take_exit")):
            leave_app(f"Knob held for 13 seconds: leaving {APPS[active][0]}.")
            return
    try:
        APPS[active][1].loop()
    except Exception:
        traceback.print_exc()
        leave_app(f"{APPS[active][0]} stopped after an error; back to the menu.")


def loop():
    global initialized
    if not initialized:
        # The MCU may not answer until setup() finishes.
        try:
            Bridge.call("set_app", 0)
        except Exception as error:
            print(f"Waiting for the MCU sketch to answer ({error}). If this repeats, check the sketch compiled and flashed.")
            time.sleep(1)
            return
        enter_menu()
        initialized = True
    if active == 0:
        menu_tick()
    else:
        app_tick()


def page_state():
    return {"active": active, "choice": choice, "apps": {str(n): name for n, (name, _) in APPS.items()}}


def app_state(number, function):
    """Look the handler up at call time, because launching an app reloads its module."""
    def handler():
        try:
            return getattr(APPS[number][1], function)()
        except Exception as error:
            return {"error": str(error)}
    return handler


def start_web():
    if WebUI is None:
        print("WebUI brick not available; the apps still run without the dashboards.")
        return
    try:
        ui = WebUI()
        ui.expose_api("GET", "/api/launcher", page_state)
        ui.expose_api("GET", "/api/duel/state", app_state(1, "state"))
        ui.expose_api("GET", "/api/maze/state", app_state(3, "state"))
        ui.expose_api("GET", "/api/maze/tilt", app_state(3, "live"))
    except Exception as error:
        print(f"Dashboard unavailable ({error}); the apps still work.")


if __name__ == "__main__":
    print("UNO Q Workshop Launcher starting...")
    start_web()
    App.run(user_loop=loop)
