from arduino.app_utils import *

import time
from pathlib import Path

from gesture_model import extract_features, load, predict, save, train


SAMPLE_INTERVAL_SECONDS = 0.05
CAPTURE_SECONDS = 1.4
GESTURE_END_SECONDS = 0.30
MAX_GESTURE_SECONDS = 1.6
MINIMUM_TRAVEL = 6
EXAMPLES_PER_GESTURE = 5
HOLD_TO_RETRAIN_SECONDS = 3.0

GESTURES = ["flick_left", "flick_right", "wiggle"]
GESTURE_CODES = {"flick_left": 0, "flick_right": 1, "wiggle": 2}
TRAINING_MODES = {"flick_left": 1, "flick_right": 2, "wiggle": 3}

APP_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = APP_ROOT / "data" / "gesture_model.json"

model = None
mode = "starting"
initialized = False
training_examples = {label: [] for label in GESTURES}
training_label_index = 0
capture_samples = []
capture_started_at = 0.0

last_knob = None
last_pressed = 0
pressed_at = None
ignore_next_release = False

live_samples = []
live_started_at = None
last_motion_at = None


def movement(samples):
    return sum(abs(samples[index] - samples[index - 1]) for index in range(1, len(samples)))


def show_training_prompt():
    label = GESTURES[training_label_index]
    completed = len(training_examples[label])
    progress = round(completed * 8 / EXAMPLES_PER_GESTURE)
    Bridge.call("show_mode", TRAINING_MODES[label], progress)
    print(
        f"TRAIN {label}: example {completed + 1}/{EXAMPLES_PER_GESTURE}. "
        "Press and release the knob, then immediately perform the gesture."
    )


def begin_training(clear_saved_model=False):
    global mode, training_examples, training_label_index
    global live_samples, live_started_at, last_motion_at

    if clear_saved_model and MODEL_PATH.exists():
        MODEL_PATH.unlink()

    training_examples = {label: [] for label in GESTURES}
    training_label_index = 0
    live_samples = []
    live_started_at = None
    last_motion_at = None
    mode = "training_ready"

    print("\nTraining mode started.")
    print("You will record five flick-left, five flick-right, and five wiggle gestures.")
    show_training_prompt()


def begin_capture(now, knob_value):
    global mode, capture_samples, capture_started_at
    mode = "capturing"
    capture_samples = [knob_value]
    capture_started_at = now
    Bridge.call("show_mode", 4, 8)
    print("Recording now...")


def finish_capture():
    global mode, training_label_index

    label = GESTURES[training_label_index]
    if movement(capture_samples) < MINIMUM_TRAVEL:
        print(f"Not enough movement for {label}; please try that example again.")
        Bridge.call("show_mode", 6, 3)
        Bridge.call("pulse_feedback", 3)
        time.sleep(0.5)
        mode = "training_ready"
        show_training_prompt()
        return

    try:
        features = extract_features(capture_samples)
    except ValueError as error:
        print(f"Could not use that example: {error}. Please try again.")
        Bridge.call("show_mode", 7, 8)
        Bridge.call("pulse_feedback", 3)
        time.sleep(0.5)
        mode = "training_ready"
        show_training_prompt()
        return

    training_examples[label].append(features)
    completed = len(training_examples[label])
    print(f"Accepted {label} example {completed}/{EXAMPLES_PER_GESTURE}.")
    Bridge.call("pulse_feedback", 1)

    if completed >= EXAMPLES_PER_GESTURE:
        training_label_index += 1

    if training_label_index >= len(GESTURES):
        finish_training()
    else:
        mode = "training_ready"
        show_training_prompt()


def finish_training():
    global model, mode

    mode = "fitting"
    Bridge.call("show_mode", 5, 8)
    print("Training the local gesture model...")

    model = train(training_examples)
    save(model, MODEL_PATH)

    mode = "live"
    Bridge.call("show_mode", 0, 8)
    Bridge.call("pulse_feedback", 2)
    print(f"Model saved to {MODEL_PATH}")
    print_live_help()


def print_live_help():
    print("\nLIVE: perform a flick-left, flick-right, or wiggle gesture.")
    print("The number of lit Pixels represents prediction confidence.")
    print("Hold the knob for three seconds to erase the model and retrain.")


def load_or_train():
    global model, mode
    try:
        model = load(MODEL_PATH)
    except (OSError, ValueError) as error:
        print(f"Ignoring saved model: {error}")
        model = None

    if model is None:
        begin_training()
    else:
        mode = "live"
        Bridge.call("show_mode", 0, 8)
        print(f"Loaded gesture model from {MODEL_PATH}")
        print_live_help()


def classify_live_gesture(samples):
    if movement(samples) < MINIMUM_TRAVEL:
        return

    try:
        features = extract_features(samples)
        result = predict(model, features)
    except ValueError as error:
        print(f"Ignored gesture: {error}")
        return

    confidence_percent = round(result["confidence"] * 100)
    distances = ", ".join(
        f"{label}={distance:.2f}" for label, distance in result["distances"].items()
    )

    if result["accepted"]:
        label = result["label"]
        print(f"PREDICT {label} ({confidence_percent}%): {distances}")
        Bridge.call("show_prediction", GESTURE_CODES[label], confidence_percent)
    else:
        print(
            f"UNCERTAIN best={result['label']} confidence={confidence_percent}%: {distances}"
        )
        Bridge.call("show_mode", 6, max(1, round(confidence_percent * 8 / 100)))
        Bridge.call("pulse_feedback", 3)


def update_live_gesture(now, knob_value, delta):
    global live_samples, live_started_at, last_motion_at

    if live_started_at is None:
        if abs(delta) >= 1:
            live_started_at = now
            last_motion_at = now
            live_samples = [knob_value - delta, knob_value]
        return

    live_samples.append(knob_value)
    if abs(delta) >= 1:
        last_motion_at = now

    gesture_finished = now - last_motion_at >= GESTURE_END_SECONDS
    gesture_timed_out = now - live_started_at >= MAX_GESTURE_SECONDS
    if gesture_finished or gesture_timed_out:
        classify_live_gesture(live_samples)
        live_samples = []
        live_started_at = None
        last_motion_at = None


def loop():
    global initialized, last_knob, last_pressed, pressed_at, ignore_next_release

    if not initialized:
        load_or_train()
        initialized = True

    now = time.monotonic()
    knob_value = int(Bridge.call("read_knob"))
    pressed = int(Bridge.call("read_pressed"))

    if last_knob is None:
        last_knob = knob_value

    delta = knob_value - last_knob

    if pressed == 1 and last_pressed == 0:
        pressed_at = now

    if mode == "live" and pressed == 1 and pressed_at is not None:
        if now - pressed_at >= HOLD_TO_RETRAIN_SECONDS:
            ignore_next_release = True
            begin_training(clear_saved_model=True)
            pressed_at = None

    if pressed == 0 and last_pressed == 1:
        if ignore_next_release:
            ignore_next_release = False
        elif mode == "training_ready":
            begin_capture(now, knob_value)
        pressed_at = None

    if mode == "capturing":
        capture_samples.append(knob_value)
        if now - capture_started_at >= CAPTURE_SECONDS:
            finish_capture()
    elif mode == "live" and pressed == 0:
        update_live_gesture(now, knob_value, delta)

    last_knob = knob_value
    last_pressed = pressed
    time.sleep(SAMPLE_INTERVAL_SECONDS)


print("UNO Q Gesture Dial starting...")
App.run(user_loop=loop)
