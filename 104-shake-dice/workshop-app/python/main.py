from arduino.app_utils import *

import time

SAMPLE_INTERVAL_SECONDS = 0.05

# Shake detection thresholds.
SHAKE_THRESHOLD_G = 2.0   # az must exceed this (in g) to count as a shake onset
SHAKE_MIN_MS = 80         # shake must sustain above threshold for at least this long

# Roll animation: number of frames shown before revealing the result.
ROLL_FRAMES = 12
ROLL_FRAME_MS = 60

SIDES_D6 = 6
SIDES_D8 = 8

mode = SIDES_D6           # current die type

shake_start = None        # time.monotonic() when az first crossed threshold
last_peak_az = 0          # peak az seen during the current shake
last_buttons = 0
result = None             # last rolled result


def az_to_g(raw):
    return raw / 1000.0


def derive_result(peak_az_raw, shake_duration_ms, sides):
    # Combine peak and duration into a deterministic but varied result.
    # Neither peak nor duration alone produces uniform-feeling rolls —
    # the sum spreads results across the range more evenly.
    return (int(peak_az_raw) + int(shake_duration_ms)) % sides + 1


def animate_roll():
    for frame in range(ROLL_FRAMES):
        Bridge.call("show_rolling", frame % 8)
        time.sleep(ROLL_FRAME_MS / 1000.0)


def reveal(value, sides):
    Bridge.call("show_face", value, sides)
    Bridge.call("play_fanfare", value)
    # Pulse vibro once per pip.
    for _ in range(value):
        Bridge.call("pip_pulse")
        time.sleep(0.12)
    print(f"Rolled: {value} (d{sides})")


def loop():
    global shake_start, last_peak_az, last_buttons, result, mode

    az_raw = Bridge.call("read_az")
    buttons = Bridge.call("read_buttons")
    button_a = buttons & 1
    button_b = (buttons >> 1) & 1

    az_g = abs(az_to_g(az_raw))
    now = time.monotonic()

    last_button_a = last_buttons & 1
    last_button_b = (last_buttons >> 1) & 1

    # Button B: toggle die mode.
    if button_b == 1 and last_button_b == 0:
        mode = SIDES_D8 if mode == SIDES_D6 else SIDES_D6
        print(f"Mode: d{mode}")
        Bridge.call("show_face", 1, mode)

    # Button A: re-roll with same die (uses last peak/duration if available).
    if button_a == 1 and last_button_a == 0 and result is not None:
        animate_roll()
        reroll = (int(last_peak_az) + int(now * 1000)) % mode + 1
        reveal(reroll, mode)
        result = reroll

    # Shake detection state machine.
    if az_g >= SHAKE_THRESHOLD_G:
        if shake_start is None:
            shake_start = now
            last_peak_az = abs(az_raw)
        else:
            if abs(az_raw) > last_peak_az:
                last_peak_az = abs(az_raw)
    else:
        if shake_start is not None:
            duration_ms = (now - shake_start) * 1000
            if duration_ms >= SHAKE_MIN_MS:
                animate_roll()
                result = derive_result(last_peak_az, duration_ms, mode)
                reveal(result, mode)
            shake_start = None

    last_buttons = buttons
    time.sleep(SAMPLE_INTERVAL_SECONDS)


print("Ready. Shake the board to roll. Button A re-rolls. Button B toggles d6/d8.")
App.run(user_loop=loop)
