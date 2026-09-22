from arduino.app_utils import *

import time


SAMPLE_INTERVAL_SECONDS = 0.05

# Distance bands in mm.
BAND_FAR_MM = 1000
BAND_MID_MM = 300
BAND_CLOSE_MM = 150

# Knob 0–100 maps to alert threshold 50–500 mm.
THRESHOLD_MIN_MM = 50
THRESHOLD_MAX_MM = 500

last_distance_mm = None
last_knob = None
in_alert_zone = False


def clamp(value, low, high):
    return max(low, min(high, value))


def distance_to_color_code(distance_mm):
    if distance_mm > BAND_FAR_MM:
        return 0  # green
    if distance_mm > BAND_MID_MM:
        return 1  # yellow
    if distance_mm > BAND_CLOSE_MM:
        return 2  # orange
    return 3  # red


def distance_to_lit_count(distance_mm):
    # Map 50–2000 mm → 7–0 pixels (closer = more pixels lit, up to 7).
    # Pixel 7 is reserved for the alert blink.
    clamped = clamp(distance_mm, 50, 2000)
    lit = round((2000 - clamped) * 7 / (2000 - 50))
    return clamp(lit, 0, 7)


def knob_to_threshold(knob_value):
    return round(THRESHOLD_MIN_MM + knob_value * (THRESHOLD_MAX_MM - THRESHOLD_MIN_MM) / 100)


def loop():
    global last_distance_mm, last_knob, in_alert_zone

    distance_mm = int(Bridge.call("read_distance"))
    knob_value = int(Bridge.call("read_knob"))

    threshold_mm = knob_to_threshold(knob_value)
    now_in_alert = distance_mm <= threshold_mm

    color_code = distance_to_color_code(distance_mm)
    lit_count = distance_to_lit_count(distance_mm)
    alert_active = 1 if now_in_alert else 0

    distance_changed = distance_mm != last_distance_mm
    knob_changed = knob_value != last_knob

    if distance_changed or knob_changed:
        Bridge.call("show_distance", color_code, lit_count, alert_active)

    # Pulse haptic only on the transition into the alert zone.
    if now_in_alert and not in_alert_zone:
        Bridge.call("pulse_alert", 0)
        print(f"Alert! Object at {distance_mm} mm (threshold: {threshold_mm} mm)")

    if distance_changed or knob_changed:
        zone_label = "ALERT" if now_in_alert else "clear"
        print(f"Distance: {distance_mm} mm | Threshold: {threshold_mm} mm | {zone_label}")

    last_distance_mm = distance_mm
    last_knob = knob_value
    in_alert_zone = now_in_alert
    time.sleep(SAMPLE_INTERVAL_SECONDS)


print("Ready. Move an object toward the sensor. Turn the Knob to set the alert threshold.")
App.run(user_loop=loop)
