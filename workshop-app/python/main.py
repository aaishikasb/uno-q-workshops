from arduino.app_utils import *

import time


last_level = None
last_pressed = 0


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def loop():
    global last_level, last_pressed

    raw_value = Bridge.call("read_knob")
    pressed = Bridge.call("read_pressed")
    level = clamp(int(raw_value))

    if level != last_level:
        print(f"Level: {level}%")
        Bridge.call("show_level", level)
        last_level = level

    if pressed == 1 and last_pressed == 0:
        print(f"Pulse: {level}%")
        Bridge.call("pulse_vibro", level)

    last_pressed = pressed
    time.sleep(0.08)


print("Ready. Turn the Modulino Knob. Press it for haptic feedback.")
App.run(user_loop=loop)
