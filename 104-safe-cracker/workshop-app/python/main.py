from arduino.app_utils import App, Bridge

import time

from lock_game import GAME_WON, STAGE_CLEAR, STAGES, TIMEOUT, TUMBLER, SafeGame


HOLD_TO_RESET_SECONDS = 3.0
BLINK_SECONDS = 0.4
ZONE_BUZZ_SECONDS = 0.2
LOOP_SECONDS = 0.05
READ_FAILURE_LIMIT = 20

game = SafeGame()
initialized = False
last_pressed = 0
pressed_at = None
ignore_next_release = False
last_blink_at = 0.0
blink_on = True
last_zone_buzz_at = 0.0
read_failures = 0
last_error = None


def call(name, *args):
    """Bridge.call that reports a failure instead of crashing the loop."""
    global last_error
    try:
        return Bridge.call(name, *args)
    except Exception as error:
        message = f"Bridge call {name} failed: {error}"
        if message != last_error:
            print(message)
            last_error = message
        return None


def show_progress():
    call("show_stage", game.cleared, int(blink_on))


def check_mcu():
    """Prove the MCU sketch is running and sampling before the game starts."""
    first = call("read_heartbeat")
    time.sleep(0.3)
    second = call("read_heartbeat")
    if first is None or second is None:
        print("CHECK FAILED: no answer from the MCU sketch over Bridge.")
        print("  Did the sketch compile and flash? Look for errors in the App Lab console.")
    elif int(first) == int(second):
        print("CHECK FAILED: the MCU answers, but its loop() is not sampling the knob.")
        print("  Check the Qwiic cables and power-cycle the UNO Q.")
    else:
        print(f"MCU OK. Knob reads {call('read_knob')}.")


def new_game():
    game.new_game()
    print("\nNew game. Turn the knob until it buzzes harder, then hold still on the spot.")
    describe_stage()
    show_progress()


def describe_stage():
    stage = STAGES[game.cleared]
    limit = f"{stage.time_limit:.0f}s limit" if stage.time_limit else "no time limit"
    numbers = f"{stage.combo_length} number{'s' if stage.combo_length > 1 else ''}"
    print(f"STAGE {game.cleared + 1}/{len(STAGES)}: {numbers}, {limit}.")


def play_victory():
    print("\nSAFE OPEN! Press the knob to play again.")
    call("pulse", 3)
    for phase in range(20):
        call("show_win", phase)
        time.sleep(0.15)


def handle_event(event):
    if event == TUMBLER:
        print("  click - one number down")
        call("pulse", 1)
    elif event == STAGE_CLEAR:
        print("  UNLOCKED")
        call("pulse", 2)
        describe_stage()
        show_progress()
    elif event == GAME_WON:
        call("show_stage", len(STAGES), 0)
        play_victory()
    elif event == TIMEOUT:
        print("  Time's up. Stage reset with a new combination.")
        call("show_alert")
        call("pulse", 4)
        time.sleep(0.6)
        show_progress()


def handle_haptics(update, now):
    global last_zone_buzz_at
    if update.warmth >= 100:
        # Locked onto a target: steady buzz while the tumbler falls.
        if now - last_zone_buzz_at >= ZONE_BUZZ_SECONDS:
            call("tick", 120)
            last_zone_buzz_at = now
    elif update.warmth > 0 and update.moved:
        call("tick", 15 + round(update.warmth * 0.6))


def handle_button(pressed, now):
    global last_pressed, pressed_at, ignore_next_release
    if pressed == 1 and last_pressed == 0:
        pressed_at = now
    if pressed == 1 and pressed_at is not None and now - pressed_at >= HOLD_TO_RESET_SECONDS:
        ignore_next_release = True
        pressed_at = None
        new_game()
    if pressed == 0 and last_pressed == 1:
        if ignore_next_release:
            ignore_next_release = False
        elif game.won:
            new_game()
        else:
            print("Stage restarted with a new combination.")
            game.restart_stage()
        pressed_at = None
    last_pressed = pressed


def loop():
    global initialized, last_blink_at, blink_on, read_failures
    if not initialized:
        check_mcu()
        new_game()
        initialized = True

    raw = call("read_knob")
    pressed = call("read_pressed")
    if raw is None or pressed is None:
        read_failures += 1
        if read_failures == READ_FAILURE_LIMIT:
            print("Still cannot read the knob. See the CHECK notes above.")
        time.sleep(LOOP_SECONDS)
        return
    read_failures = 0

    now = time.monotonic()
    handle_button(int(pressed), now)

    if not game.won:
        update = game.update(now, int(raw))
        if update.event:
            handle_event(update.event)
        else:
            handle_haptics(update, now)

        if now - last_blink_at >= BLINK_SECONDS:
            last_blink_at = now
            blink_on = not blink_on
            show_progress()

    time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    print("UNO Q Safe Cracker starting...")
    App.run(user_loop=loop)
