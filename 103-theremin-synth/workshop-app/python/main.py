from arduino.app_utils import *

import time

SAMPLE_INTERVAL_SECONDS = 0.05

# Scales: list of (note_name, freq_hz) in ascending pitch order.
PENTATONIC = [
    ("C4", 262), ("D4", 294), ("E4", 330), ("G4", 392), ("A4", 440),
    ("C5", 523), ("D5", 587), ("E5", 659),
]
MAJOR = [
    ("C4", 262), ("D4", 294), ("E4", 330), ("F4", 349), ("G4", 392),
    ("A4", 440), ("B4", 494), ("C5", 523),
]
CHROMATIC = [
    ("C4",  262), ("C#4", 277), ("D4",  294), ("D#4", 311),
    ("E4",  330), ("F4",  349), ("F#4", 370), ("G4",  392),
    ("G#4", 415), ("A4",  440), ("A#4", 466), ("B4",  494),
    ("C5",  523), ("C#5", 554), ("D5",  587), ("D#5", 622),
]

SCALES = [PENTATONIC, MAJOR, CHROMATIC]
SCALE_NAMES = ["pentatonic", "major", "chromatic"]

# Distance range (mm) mapped to pitch position across the scale.
DIST_MIN_MM = 50
DIST_MAX_MM = 600

# Color zone lookup: index 0 (lowest/closest) → index 5 (highest/farthest).
# Zone index is derived from position across the scale.
# close = red(5), far = blue(0)
def _zone_color(note_index, scale_len):
    zone = int((note_index / max(scale_len - 1, 1)) * 5)
    return 5 - zone  # invert: close=red, far=blue


def _pick_scale(knob_val):
    if knob_val <= 33:
        return 0
    if knob_val <= 66:
        return 1
    return 2


def _distance_to_note_index(dist_mm, scale):
    clamped = max(DIST_MIN_MM, min(DIST_MAX_MM, dist_mm))
    t = (clamped - DIST_MIN_MM) / (DIST_MAX_MM - DIST_MIN_MM)
    # Invert: close hand = high note, far away = low note.
    t = 1.0 - t
    raw_index = t * (len(scale) - 1)
    return int(round(raw_index))


last_note_index = -1
last_scale_idx = -1
last_knob = -1

NOTE_DURATION_MS = 120


def loop():
    global last_note_index, last_scale_idx, last_knob

    dist_mm = Bridge.call("read_distance")
    knob_val = Bridge.call("read_knob")

    scale_idx = _pick_scale(knob_val)
    scale = SCALES[scale_idx]
    note_index = _distance_to_note_index(dist_mm, scale)

    # Hysteresis: only update when note index changes by more than 0.
    # (The rounding in _distance_to_note_index already provides 1-note hysteresis.)
    if note_index != last_note_index or scale_idx != last_scale_idx:
        note_name, freq = scale[note_index]
        color_code = _zone_color(note_index, len(scale))
        lit_count = note_index + 1

        Bridge.call("play_note", freq, NOTE_DURATION_MS)
        Bridge.call("show_zone", color_code, lit_count)

        if scale_idx != last_scale_idx:
            print(f"Scale: {SCALE_NAMES[scale_idx]}")

        print(f"Note: {note_name} ({freq} Hz) | dist: {dist_mm} mm")

        last_note_index = note_index
        last_scale_idx = scale_idx

    last_knob = knob_val
    time.sleep(SAMPLE_INTERVAL_SECONDS)


print("Ready. Wave your hand over the Distance sensor. Turn the Knob to change scale.")
App.run(user_loop=loop)
