# UNO Q Workshop Plan
## LLM Generation Guide — All Three Levels

This document contains everything an LLM needs to generate new workshop modules.
Read the full document before generating any module. The canonical examples in
Section 3 are the ground truth for code style, file structure, and API usage.

---

## Table of Contents

1. [Platform Reference](#1-platform-reference)
2. [File Structure & Conventions](#2-file-structure--conventions)
3. [Canonical Examples (101 and 201)](#3-canonical-examples-101-and-201)
4. [100-Series: Embedded Engineering](#4-100-series-embedded-engineering)
5. [200-Series: Machine Learning](#5-200-series-machine-learning)
6. [300-Series: Edge Vision](#6-300-series-edge-vision)
7. [Module Generation Checklist](#7-module-generation-checklist)

---

## 1. Platform Reference

### Hardware

**Arduino UNO Q** — dual-core board:

| Core | Chip | Role |
|---|---|---|
| MCU | ARM Cortex-M4 (Zephyr RTOS) | Hardware I/O, sensor polling, actuator control |
| MPU | Qualcomm QRB2210, quad-core Cortex-A53 @ 2.0 GHz | Application logic, ML inference, state machines |

MPU specs: 2 GB LPDDR4, 16 GB eMMC, Adreno GPU, full Debian Linux.

MCU and MPU communicate over **Bridge RPC** — the only allowed IPC mechanism.
The MCU exposes named functions; Python calls them by name.

### Modulino Ecosystem

All Modulinos connect via **I2C using JST/Qwiic connectors** and daisy-chain.
The `Arduino_Modulino` library (0.8.0+) provides all C++ APIs.

| Modulino | C++ Class | Key API | Library |
|---|---|---|---|
| Knob | `ModulinoKnob` | `.get()` → int, `.isPressed()` → bool, `.set(int)` | Arduino_Modulino |
| Pixels | `ModulinoPixels` | `.set(i, r, g, b, brightness)`, `.clear()`, `.show()` | Arduino_Modulino |
| Vibro | `ModulinoVibro` | `.on(duration_ms)` | Arduino_Modulino |
| Buttons | `ModulinoButtons` | `.update()`, `.isPressed(A/B/C)` → bool | Arduino_Modulino |
| Buzzer | `ModulinoBuzzer` | `.tone(freq_hz, duration_ms)`, `.noTone()` | Arduino_Modulino |
| Movement | `ModulinoMovement` | `.update()`, `.getX/Y/Z()` → float (accel g), `.getAngularVelocityX/Y/Z()` → float (gyro dps) — backed by LSM6DSOX | Arduino_Modulino / Arduino_LSM6DSOX |
| Distance | `ModulinoDistance` | `.available()` → bool, `.get()` → int (mm) — backed by VL53L4CD | Arduino_Modulino / STM32duino VL53L4CD |
| Thermo | `ModulinoThermo` | `.update()`, `.getTemperature()` → float (°C), `.getHumidity()` → float (%) — backed by HS300x | Arduino_Modulino / Arduino_HS300x |
| Light | `ModulinoLight` | `.update()`, `.getLux()` → float, `.getRed/Green/Blue()` → float | Arduino_Modulino / Arduino_LTR381RGB |
| LED Matrix | `ModulinoLEDMatrix` | `.set(x, y, on)`, `.clear()`, `.show()` — 8×8 grid | Arduino_Modulino / ArduinoGraphics |
| Joystick | `ModulinoJoystick` | `.update()`, `.getX()` → int (-100..100), `.getY()` → int (-100..100), `.isPressed()` → bool | Arduino_Modulino |
| Latch Relay | `ModulinoRelay` | `.set(true/false)` latches ON/OFF | Arduino_Modulino |

### Bridge RPC API

**MCU side (C++)**

```cpp
// Register a handler — called by Python
Bridge.provide("function_name", function_ptr);        // non-blocking read
Bridge.provide_safe("function_name", function_ptr);   // safe for display/actuator calls

// Handler signatures (fixed — must match exactly):
int  handler_name();                    // no-arg, returns int
int  handler_name(int a);              // one int arg
void handler_name(int a);              // one int arg, no return
void handler_name(int a, int b);       // two int args
```

**Python side**

```python
from arduino.app_utils import *   # provides Bridge, App

result = Bridge.call("function_name")          # no args
result = Bridge.call("function_name", value)   # one int arg
Bridge.call("function_name", arg1, arg2)       # two int args

App.run(user_loop=loop)   # starts the poll loop
```

Bridge values are always integers. Pass floats as scaled integers when needed
(e.g. multiply by 100 on MCU side, divide by 100 in Python).

### Arduino App Lab

Browser-based IDE. Participants import the module as a `.zip` archive.
The zip structure must be exactly:

```
workshop-app.zip
└── workshop-app/
    ├── app.yaml
    ├── python/
    │   └── main.py          (plus any helper .py files)
    └── sketch/
        ├── sketch.ino
        └── sketch.yaml
```

### 300-Series: Webcam

For 300-level modules, a USB webcam connects to the MPU via V4L2.
Install on the board's Debian side:

```bash
sudo apt install python3-opencv
# or
pip install opencv-python-headless
```

Python webcam access:

```python
import cv2
cap = cv2.VideoCapture(0)          # /dev/video0
ret, frame = cap.read()            # BGR frame, 640×480 default
```

Available packages on Debian (installable via pip/apt):
- `opencv-python-headless` — frame capture, DNN inference, Haar cascades
- `tflite-runtime` — TensorFlow Lite inference (no full TF required)
- `mediapipe` — hand/face landmarks (arm64 wheel available)

---

## 2. File Structure & Conventions

### Directory layout for every module

```
NNN-module-name/
├── README.md
├── workshop-app.zip          (zip of workshop-app/ — include in output)
└── workshop-app/
    ├── app.yaml
    ├── python/
    │   └── main.py           (plus helper .py files if needed)
    └── sketch/
        ├── sketch.ino
        └── sketch.yaml
```

### app.yaml

```yaml
name: UNO Q <Module Name>
description: <One sentence describing the module and what Modulinos it uses.>
```

### sketch.yaml

Always use this exact template — do not change the library list even if the
module only uses a subset. The full list ensures App Lab resolves dependencies
for all hardware without requiring per-module customization.

```yaml
profiles:
  default:
    fqbn:
    platforms:
      - platform: arduino:zephyr
    libraries:
      - Arduino_Modulino (0.8.0)
      - STM32duino VL53L4CD (1.0.5)
      - STM32duino VL53L4ED (1.0.1)
      - Arduino_LSM6DSOX (1.1.2)
      - Arduino_LPS22HB (1.0.2)
      - Arduino_HS300x (1.0.0)
      - ArduinoGraphics (1.1.5)
      - Arduino_LTR381RGB (1.0.1)

default_profile: default
```

### sketch.ino conventions

```cpp
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

// Declare hardware objects at file scope
ModulinoKnob knob;
ModulinoPixels pixels;
// ...

// setup() order: Modulino.begin() → each .begin() → any startup feedback →
//                Bridge.begin() → Bridge.provide() calls
void setup() {
  Modulino.begin();
  knob.begin();
  pixels.begin();
  // ...

  Bridge.begin();
  Bridge.provide("function_name", function_ptr);
}

// loop() is empty for event-driven modules.
// Use loop() only for hardware that must be polled at high frequency
// (e.g. 50 Hz IMU sampling), and use micros()-based timing, not delay().
void loop() {
}
```

Rules:
- All Bridge handler arguments and return values are `int`.
- Use `constrain()` defensively on all incoming values before using them.
- Use `map()` for linear range remapping.
- `pixels.set(i, r, g, b, 25)` — always use brightness 25 (dim, long-session safe).
- `vibro.on(ms)` — typical range 80–400 ms. Short = subtle, long = strong.
- `buzzer.tone(freq, ms)` — pentatonic scale: 262, 294, 330, 370, 415, 466, 523, 587 Hz.
- Never use `delay()` in `loop()` — use micros() delta timing.
- Never use `Serial.print` — the Bridge owns the serial bus.
- Never call I2C sensor reads (e.g. `distance.available()`, `distance.get()`,
  `movement.update()`) from `loop()` when Bridge is active. The I2C transaction
  blocks the Bridge scheduler and causes `TimeoutError` on the Python side.
  Instead, perform the sensor read inside the Bridge handler function itself,
  which runs in the correct Bridge-managed context. Use `loop()` only for
  pure MCU state (timers, counters) with no I2C calls.

### main.py conventions

```python
from arduino.app_utils import *
import time

SAMPLE_INTERVAL_SECONDS = 0.05   # 50 Hz poll rate — standard for all modules

def loop():
    # 1. Read sensors via Bridge.call()
    # 2. Run Python logic
    # 3. Update display/actuators via Bridge.call()
    time.sleep(SAMPLE_INTERVAL_SECONDS)

print("Ready. <One line telling participant what to do.>")
App.run(user_loop=loop)
```

Rules:
- `from arduino.app_utils import *` must be the first import.
- `time.sleep(0.05)` at the end of every loop iteration — no busy-waiting.
- Use `time.monotonic()` for elapsed time — never `time.time()`.
- Use `pathlib.Path` for all file I/O.
- Standard library only unless the module spec explicitly lists packages
  (200-series: stdlib only; 300-series: cv2, tflite-runtime, mediapipe allowed).
- State machines use a string `mode` variable.
- Print participant-facing status lines to console with `print()`.
- No comments explaining what the code does — only add a comment if the WHY
  is non-obvious (a timing constraint, a workaround, a subtle invariant).

### README.md structure

Every module README follows this section order:

```
# NNN: <Module Name>

One-paragraph description of what the workshop builds and what the participant
learns.

## Prerequisites
## Hardware Setup
## App Lab Setup
## How It Works
## Files
## Sources
```

The **How It Works** section must include a plain-text flowchart or ASCII
diagram showing the MCU ↔ Python data flow.

---

## 3. Canonical Examples (101 and 201)

These are the ground truth. Match their code style exactly.

### 101: Haptic Dial

**`workshop-app/sketch/sketch.ino`**

```cpp
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoKnob knob;
ModulinoPixels pixels;
ModulinoVibro vibro;

int read_knob() {
  return knob.get();
}

int read_pressed() {
  return knob.isPressed() ? 1 : 0;
}

void show_level(int level) {
  level = constrain(level, 0, 100);
  int litPixels = (level * 8 + 99) / 100;

  uint8_t red = 0;
  uint8_t green = 120;
  uint8_t blue = 220;

  if (level >= 67) {
    red = 220;
    green = 40;
    blue = 120;
  } else if (level >= 34) {
    red = 40;
    green = 200;
    blue = 80;
  }

  pixels.clear();
  for (int i = 0; i < litPixels; i++) {
    pixels.set(i, red, green, blue, 25);
  }
  pixels.show();
}

void pulse_vibro(int level) {
  level = constrain(level, 0, 100);
  int duration = map(level, 0, 100, 180, 400);
  vibro.on(duration);
}

void setup() {
  Modulino.begin();
  knob.begin();
  pixels.begin();
  vibro.begin();

  // A startup pulse confirms the Vibro is connected before Bridge starts.
  vibro.on(250);

  knob.set(0);
  show_level(0);

  Bridge.begin();
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_pressed", read_pressed);
  Bridge.provide("show_level", show_level);
  Bridge.provide("pulse_vibro", pulse_vibro);
}

void loop() {
}
```

**`workshop-app/python/main.py`**

```python
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
```

---

### 201: Gesture Dial

**`workshop-app/sketch/sketch.ino`**

```cpp
#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoKnob knob;
ModulinoPixels pixels;
ModulinoVibro vibro;

const unsigned long SAMPLE_PERIOD_US = 20000;  // 50 Hz hardware sampling.
volatile int latestKnob = 0;
volatile int latestPressed = 0;
unsigned long lastSampleAt = 0;

enum DisplayMode {
  MODE_LIVE = 0,
  MODE_TRAIN_LEFT = 1,
  MODE_TRAIN_RIGHT = 2,
  MODE_TRAIN_WIGGLE = 3,
  MODE_RECORDING = 4,
  MODE_TRAINING_MODEL = 5,
  MODE_UNCERTAIN = 6,
  MODE_ERROR = 7
};

enum GestureClass {
  GESTURE_LEFT = 0,
  GESTURE_RIGHT = 1,
  GESTURE_WIGGLE = 2
};

int read_knob() { return latestKnob; }
int read_pressed() { return latestPressed; }

void fill_pixels(uint8_t red, uint8_t green, uint8_t blue, int litPixels) {
  litPixels = constrain(litPixels, 0, 8);
  pixels.clear();
  for (int i = 0; i < litPixels; i++) {
    pixels.set(i, red, green, blue, 25);
  }
  pixels.show();
}

void show_mode(int mode, int progress) {
  progress = constrain(progress, 0, 8);
  switch (mode) {
    case MODE_LIVE:           fill_pixels(0, 120, 220, progress);   break;
    case MODE_TRAIN_LEFT:     fill_pixels(220, 40, 120, progress);  break;
    case MODE_TRAIN_RIGHT:    fill_pixels(40, 200, 80, progress);   break;
    case MODE_TRAIN_WIGGLE:   fill_pixels(120, 70, 220, progress);  break;
    case MODE_RECORDING:      fill_pixels(220, 220, 220, 8);        break;
    case MODE_TRAINING_MODEL: fill_pixels(120, 70, 220, 8);         break;
    case MODE_UNCERTAIN:      fill_pixels(230, 150, 0, progress);   break;
    default:                  fill_pixels(220, 0, 0, 8);            break;
  }
}

void show_prediction(int gesture, int confidence) {
  confidence = constrain(confidence, 0, 100);
  int litPixels = max(1, (confidence * 8 + 99) / 100);
  switch (gesture) {
    case GESTURE_LEFT:   fill_pixels(220, 40, 120, litPixels);  break;
    case GESTURE_RIGHT:  fill_pixels(40, 200, 80, litPixels);   break;
    case GESTURE_WIGGLE: fill_pixels(120, 70, 220, litPixels);  break;
    default:             fill_pixels(230, 150, 0, litPixels);   break;
  }
  int duration = map(confidence, 0, 100, 100, 320);
  vibro.on(duration);
}

void pulse_feedback(int kind) {
  switch (kind) {
    case 0: vibro.on(180); break;  // Ready.
    case 1: vibro.on(120); break;  // Training example accepted.
    case 2: vibro.on(400); break;  // Training finished.
    default: vibro.on(80); break;  // Retry or error.
  }
}

void setup() {
  Modulino.begin();
  knob.begin();
  pixels.begin();
  vibro.begin();

  knob.set(0);
  latestKnob = knob.get();
  latestPressed = knob.isPressed() ? 1 : 0;
  lastSampleAt = micros();
  show_mode(MODE_LIVE, 8);
  pulse_feedback(0);

  Bridge.begin();
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_pressed", read_pressed);
  Bridge.provide_safe("show_mode", show_mode);
  Bridge.provide_safe("show_prediction", show_prediction);
  Bridge.provide_safe("pulse_feedback", pulse_feedback);
}

void loop() {
  unsigned long now = micros();
  if (now - lastSampleAt >= SAMPLE_PERIOD_US) {
    lastSampleAt = now;
    latestKnob = knob.get();
    latestPressed = knob.isPressed() ? 1 : 0;
  }
}
```

**`workshop-app/python/main.py`** — see the actual file at
`201-gesture-dial/workshop-app/python/main.py` (260 lines).

**`workshop-app/python/gesture_model.py`** — see the actual file at
`201-gesture-dial/workshop-app/python/gesture_model.py` (181 lines).

Key architectural points for 201 that carry forward to all 200-series modules:
- `gesture_model.py` is a separate file imported by `main.py`.
- The model is a **nearest-centroid classifier** trained entirely from stdlib
  math — no numpy, no sklearn.
- Feature extraction: resample raw sensor stream to N fixed points → normalize
  → append scalar motion features (travel, reversals, duration, peak step).
- Training: compute per-class centroids + radii over standardized features.
- Prediction: standardize, compute distances to all centroids, softmax-like
  confidence, accept if confidence ≥ 0.58 and in-distribution.
- Model is persisted as JSON to `<app_root>/data/<model_name>.json`.
- State machine modes: `starting`, `training_ready`, `capturing`, `fitting`,
  `live`. All 200-series modules should follow this same state machine pattern,
  adapting mode names and transitions as needed.

---

## 4. 100-Series: Embedded Engineering

**Theme**: Hardware literacy. Build things that respond.
**ML**: None — pure embedded systems, sensor I/O, and actuation.
**Prerequisites**: None. Participants start here.
**Duration**: 2 hours each.

---

### 101: Haptic Dial *(existing — do not regenerate)*

See `101-haptic-dial/`. Reference implementation for all coding conventions.

---

### 102: Melody Maker

**Modulinos**: Knob + Pixels + Buzzer

**Concept**: Knob scrolls through 8 notes of a pentatonic scale.
Each position lights the corresponding Pixel. Press the knob to play the note
as a buzzer tone. Python records each press as a step in a sequence. After 8
steps, the sequence plays back automatically in a loop. Press and hold to clear
and start a new sequence.

**MCU responsibilities**:
- Read knob position (0–100) and button state.
- Accept `play_tone(freq, duration)` calls and drive the Buzzer.
- Accept `show_note(index)` calls and light the correct Pixel with a
  note-specific color.

**Python responsibilities**:
- Map knob 0–100 to note index 0–7 (pentatonic: 262, 294, 330, 370, 415,
  466, 523, 587 Hz).
- Detect button press → append (note_index, freq) to sequence list.
- After 8 steps OR on a 2-second idle: play back the sequence, one note per
  0.25 s.
- 3-second hold → clear sequence.
- Print current note name and sequence length to console.

**Pixel color scheme** (one color per note, cycle through):
`red, orange, yellow, green, cyan, blue, indigo, violet`

**New concept**: Frequency-to-pitch mapping, sequence recording, timed playback.

**Wow moment**: Play back your own melody 30 seconds after you started.

---

### 103: Environmental Dashboard

**Modulinos**: Thermo + Light + Pixels + Knob

**Concept**: Live 2-panel LED dashboard. Left 4 pixels show temperature band
(blue = cool, green = comfortable, orange = warm, red = hot). Right 4 pixels
show humidity band (dry → humid). Knob selects display mode: CURRENT, MIN,
MAX recorded since session start. Python logs all readings with timestamps.

**MCU responsibilities**:
- Accept `show_temp_panel(band, count)` and `show_humidity_panel(band, count)`
  calls — `band` is a color code int, `count` is 0–4 pixels lit.
- Read knob and button state.

**Python responsibilities**:
- Poll Thermo every 2 seconds — push temp and humidity to MCU display.
- Poll Light for lux — used as a third panel overlay when lux drops below
  threshold (night mode: all pixels dimmer).
- Track session min/max for both channels.
- Knob position selects CURRENT (0–33) / MIN (34–66) / MAX (67–100) mode.
- Print `Temp: 24.3°C | Humidity: 61% | Lux: 312` to console each poll.

**New concept**: Multi-sensor polling, rolling min/max tracking, mode selection
via knob range.

**Wow moment**: Watch the panels shift as you breathe on the Thermo sensor.

---

### 104: Joystick Light Painter

**Modulinos**: Joystick + LED Matrix + Buttons (A/B/C) + Buzzer + Pixels

**Concept**: Joystick moves a cursor around the 8×8 LED Matrix — like an
Etch-a-Sketch. Button A toggles the pen down (drawing) vs. up (moving without
marking). Button B clears the canvas. Button C replays the drawing stroke-by-
stroke from the beginning, showing each pixel appear in sequence with a short
Buzzer tick per step. Pixels show current pen state by color (green = drawing,
blue = moving, white = replaying).

**MCU responsibilities**:
- Read joystick X/Y (-100..100) and all three button states via `read_joystick_x`,
  `read_joystick_y`, `read_button_a`, `read_button_b`, `read_button_c`.
- Accept `set_pixel(x, y, on)` — sets one cell on the LED Matrix.
- Accept `clear_matrix()` — clears the entire LED Matrix.
- Accept `show_status(color_code)` — updates Pixels to show pen state.
- Accept `play_tick()` — short Buzzer click during replay.

**Python responsibilities**:
- Map joystick to cursor delta: X/Y values above a deadzone (±20) move the
  cursor one step every 150 ms. Cursor wraps at matrix edges.
- PEN_DOWN mode: each cursor position is recorded as `(x, y)` in a stroke list
  and immediately lit on the matrix.
- PEN_UP mode: cursor moves without recording or lighting cells.
- Button B: clear matrix, clear stroke list.
- Button C: REPLAY mode — turn off all cells, then re-draw stroke list one
  pixel at a time at 100 ms intervals with a Buzzer tick per step.
- Print cursor position and stroke count to console.

**New concept**: 2D coordinate mapping from analog input, canvas state as a
list of positions, sequential replay with timed playback.

**Wow moment**: Draw something, press replay, watch it redraw itself.

---

### 105: Proximity Lamp

**Modulinos**: Distance (VL53L4CD) + Pixels + Vibro + Knob

**Concept**: ToF sensor measures object distance 5–200 cm. Pixel count and
color gradient show how close the object is (green = far, yellow = mid,
red = close). Haptic fires a single pulse when the object enters a configurable
alert zone. Knob sets the alert threshold. Pixel 7 blinks independently when
the object is inside the alert zone.

**MCU responsibilities**:
- Poll Distance sensor at 20 Hz in `loop()` using micros() delta. Cache latest
  reading as `latestDistance` (int, mm).
- Expose `read_distance()` → int (mm).
- Accept `show_distance(color_code, lit_count, alert_active)`.
- Accept `pulse_alert(strength)` → short or long haptic.

**Python responsibilities**:
- Read distance every 50 ms.
- Map 50–2000 mm → 0–8 pixels (clamp beyond range).
- Color: green (>1000 mm), yellow (300–1000 mm), orange (150–300 mm),
  red (<150 mm).
- Track whether object just entered the alert zone (edge detection) → trigger
  `pulse_alert` only on the transition, not continuously.
- Knob 0–100 maps to alert threshold 50–500 mm.
- Print distance and alert state to console.

**New concept**: ToF sensor, range-to-visual mapping, edge detection for
threshold crossing (trigger on enter, not while inside).

**Wow moment**: It feels like a parking sensor you own.

---

## 5. 200-Series: Machine Learning

**Theme**: Machine learning. Build things that learn from you.
**ML**: Every module trains a model from the participant's own data.
**Prerequisites**: Complete 101 first.
**Duration**: 2 hours each.

**ML progression across the series**:
- 201: Nearest-centroid on knob time-series (knob sensor)
- 202: Nearest-centroid on IMU orientation (new sensor, same algorithm)
- 203: Nearest-centroid on vibration onset intervals (new feature domain)
- 204: Multivariate Gaussian anomaly detection (first unsupervised module)
- 205: k-NN on RGB color sensor readings (second algorithm)

**Shared implementation pattern** (replicate for every 200-series module):
- A separate `<name>_model.py` file handles all feature extraction,
  training, prediction, save, and load — stdlib only, no numpy/sklearn.
- `main.py` imports from `<name>_model.py` and owns the state machine.
- State machine modes: `starting` → `training_ready` → `capturing` →
  `fitting` → `live`. Adapt names per module but keep the same flow.
- Model persisted as JSON to `<app_root>/data/<name>.json`.
- 5 examples per class, same training UX as 201.
- Haptic feedback codes: 0=ready, 1=example accepted, 2=training done,
  3=retry/error.

---

### 201: Gesture Dial *(existing — do not regenerate)*

See `201-gesture-dial/`. Reference implementation for all 200-series modules.

---

### 202: Posture Trainer

**Modulinos**: Movement (LSM6DSOX IMU) + Pixels + Vibro + Knob

**Concept**: Participant trains 3 posture classes on their own body:
`upright`, `slouch_forward`, `lean_back`. The board is placed on a flat
surface near the participant (e.g. desk edge or laptop). After training,
live IMU readings are classified continuously. Pixels show the current
posture class by color. Haptic fires a reminder pulse after N consecutive
seconds of a non-upright class. Knob adjusts the grace period (N seconds).

**Sensor**: IMU accelerometer axes (X, Y, Z in g). Gyroscope not needed —
posture is a static orientation, not a motion.

**Feature extraction** (`posture_model.py`):
- Collect 20 accelerometer samples at 50 Hz over 0.4 s capture window.
- Average each axis over the window → [mean_x, mean_y, mean_z].
- L2-normalize the 3-vector so magnitude = 1 (removes scale variation).
- Feature vector is [norm_x, norm_y, norm_z] — 3 dimensions.
- Use the same nearest-centroid classifier and standardization as
  `gesture_model.py`, adapted for 3 features instead of 16.

**Training UX**: Same as 201. Press knob to start capture, hold still
for 0.4 s, haptic confirms. 5 examples per class × 3 classes = 15 total.

**Live mode**: Classify continuously every 0.4 s (not gesture-triggered).
Track consecutive non-upright seconds. When elapsed ≥ knob-set grace period
(5–60 s mapped from knob 0–100), pulse haptic and reset timer.

**MCU responsibilities**:
- Poll IMU in `loop()` at 50 Hz, cache latest [ax, ay, az] as three
  separate `volatile int` values (multiply float by 1000 for int transport).
- Expose `read_imu()` → returns ax*1000 as int (Python reads three
  consecutive calls: ax, ay, az). **Alternative**: expose three separate
  Bridge functions `read_ax`, `read_ay`, `read_az` — prefer this for clarity.
- Accept `show_mode(mode_code, progress)` and `pulse_feedback(kind)`.

**Python responsibilities**: State machine identical to 201, sensor is IMU
instead of knob.

**New concept**: IMU as a posture sensor, static orientation vs. dynamic
gesture, gravity vector for tilt estimation, timer-based alerts in live mode.

**Wow moment**: It buzzes when you slouch. Participants keep using it after
the workshop.

---

### 203: Tap Rhythm Classifier

**Modulinos**: Movement (LSM6DSOX IMU) + Pixels + Vibro + Knob

**Concept**: Tap on the desk surface. The IMU Z-axis (vertical) picks up
the impact vibration. Python detects tap onsets and extracts the inter-tap
interval (ITI) pattern. Train 3 rhythms: `waltz` (3-beat), `march` (4-beat),
`swing` (syncopated 3-beat). After training, tap any rhythm and it classifies
which one you're performing.

**Sensor**: IMU accelerometer Z-axis only. Tap onset = Z-axis spike
above threshold (e.g. |az| > 1.5 g peak).

**Feature extraction** (`rhythm_model.py`):
- Detect tap onsets from Z-axis samples using a peak-detector with
  refractory period (min 80 ms between taps to avoid double-counting).
- Collect the first N taps in a capture window (N=4 for 3-beat, N=5 for
  4-beat — use N=5 for all classes for consistency).
- Compute inter-tap intervals (ITI) in ms: [t1-t0, t2-t1, t3-t2, t4-t3].
- Normalize ITIs by total duration so the feature is tempo-invariant.
- Append: total duration (capped at 3 s), mean ITI, std of ITIs.
- Feature vector: [norm_iti_0, norm_iti_1, norm_iti_2, norm_iti_3,
  total_duration, mean_iti, std_iti] — 7 dimensions.
- Same nearest-centroid classifier as 201/202.

**Training UX**: Same as 201. Press knob = start capture. Tap N times
within 3 s. Haptic confirms capture. 5 examples per class × 3 classes.

**New concept**: Vibration onset detection, inter-onset interval (IOI)
as a feature, tempo-invariant normalization (the same rhythm at different
speeds should classify the same way).

**Wow moment**: It learns YOUR rhythm — not a pre-programmed template.

---

### 204: Anomaly Watchdog

**Modulinos**: Movement (LSM6DSOX IMU) + Thermo (HS300x) + Pixels + Vibro + Knob

**Concept**: First phase records a 30-second baseline of normal conditions
(board sitting still, ambient temp). Python fits a multivariate Gaussian
(per-channel μ and σ) to the baseline data. Second phase is watch mode:
LEDs stay calm green. If any sensor channel exceeds N standard deviations
from its baseline mean, LEDs flash red and haptic fires an alert. Knob
adjusts sensitivity (N = 1.0–4.0 standard deviations). Participants test by
shaking the board, blowing on the Thermo, or knocking the desk.

**Sensors**: IMU [ax, ay, az, gx, gy, gz] (6 channels) + Thermo [temp, humidity]
(2 channels) = 8 channels total.

**Model** (`anomaly_model.py`):
- Baseline: collect all 8-channel readings at 10 Hz for 30 s = 300 samples.
- Compute per-channel mean and std.
- Detection: for each new sample, compute per-channel z-score =
  abs(value - mean) / std. Flag anomaly if max(z-scores) > threshold.
- No training phase in the traditional sense — this is unsupervised.
- Save baseline stats as JSON.

**State machine**:
- `baseline`: record 300 samples with a countdown on Pixels (pixel count
  decreases as time passes). Haptic when done.
- `watch`: continuous classification. Alert on anomaly, return to green
  when normal. Print which channel triggered and its z-score.

**No training UX** — the baseline is recorded automatically. This is
intentional: teach participants the difference between supervised (201–203)
and unsupervised (204) learning.

**New concept**: Unsupervised vs. supervised ML, z-score, multivariate
Gaussian, the concept of "normal" as a learned distribution rather than
a hard-coded rule.

**Wow moment**: Blow on the board. Watch it trigger. Shake it. Watch a
different channel trigger. Industrial IoT in 90 minutes.

---

### 205: Adaptive Color Sorter

**Modulinos**: Light (LTR381RGB) + Buttons (A/B/C) + Pixels + Vibro + Knob

**Concept**: Participant labels colored objects by holding them under the
Light sensor and pressing a button. Button A = class RED, Button B = class
GREEN, Button C = class BLUE (but any 3 distinct colored objects work —
the names are just labels). After collecting 5 samples per class, a k-NN
classifier (k=3) is trained on the RGB readings. In live mode, hold any
object under the sensor and the board classifies which class it belongs to.
Knob adjusts how many examples are shown during training (progress display).

**Sensor**: Light sensor RGB channels → [r, g, b] float values normalized
to sum = 1 (chromaticity coordinates, removing brightness variation).

**Feature extraction** (`color_model.py`):
- Average 10 readings at 20 Hz over 0.5 s.
- Normalize: total = r + g + b; features = [r/total, g/total, b/total].
  This makes the model lighting-invariant (a red object looks red under
  bright or dim light).
- Feature vector: [norm_r, norm_g, norm_b] — 3 dimensions.

**Algorithm** (`color_model.py`):
- k-NN (k=3): store all labeled examples. Predict by finding 3 nearest
  neighbors by Euclidean distance, return majority vote + confidence
  (votes/3 as fraction). Stdlib only.

**Training UX**: Button A/B/C each trigger a capture for that class.
5 examples per button. Pixels show which class is next and progress.
No explicit "finish training" step — model is automatically trained after
all 15 examples are collected.

**New concept**: k-NN as a second algorithm (contrast with nearest-centroid),
chromaticity normalization (lighting-invariant color features), multi-button
input for labeled data collection.

**Wow moment**: Sort different colored candies or post-its. The board
identifies them.

---

## 6. 300-Series: Edge Vision

**Theme**: Edge vision. Build things that see.
**Prerequisites**: Complete 101. Familiarity with Python recommended.
**Duration**: 2 hours each.
**Extra hardware**: USB webcam connected to UNO Q MPU via USB.

**Setup required before workshop**:
```bash
# On the UNO Q Linux side:
sudo apt update
sudo apt install -y python3-opencv libopencv-dev
pip install tflite-runtime mediapipe
```

**Webcam init pattern** (include at top of every 300-series `main.py`):
```python
import cv2

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
if not cap.isOpened():
    raise RuntimeError("Webcam not found — check USB connection.")
```

**Frame capture pattern**:
```python
ret, frame = cap.read()
if not ret:
    time.sleep(0.033)
    continue
```

**Key performance notes for Cortex-A53**:
- Target 10–15 FPS for inference — 640×480 is fine.
- Resize to 224×224 or 160×160 before passing to TFLite models.
- Use `cv2.resize(frame, (224, 224))` before inference.
- MobileNet-class models run at ~100–200 ms/frame on 4× A53 cores.
- Always `cap.release()` on exit — App Lab may not clean up otherwise.

**300-series Python structure**:
```
workshop-app/
├── python/
│   ├── main.py          (state machine, Bridge calls, camera loop)
│   └── vision.py        (all cv2/tflite/mediapipe logic isolated here)
```
Isolate all vision code in `vision.py` so `main.py` stays readable.

---

### 301: Face Presence Dashboard

**Modulinos**: Pixels + Vibro + Knob
**Vision stack**: OpenCV DNN face detector (res10_300x300_ssd)

**Concept**: Webcam detects whether a face is present in frame.
No face → Pixels red, dim. Face detected → Pixels pulse green, brief haptic
welcome. Python tracks occupancy: how many seconds a face has been present
this session. Knob adjusts detection confidence threshold (0.3–0.9).

**`vision.py`**:
- Load `res10_300x300_ssd_iter_140000.caffemodel` and `.prototxt` (ship
  with the module or download on first run).
- `detect_faces(frame, threshold)` → list of bounding boxes + confidences.
- Return `has_face: bool` and `max_confidence: float`.

**`main.py`**:
- Camera loop at ~15 FPS.
- State: `absent`, `present`.
- On `absent → present` transition: haptic welcome pulse, pixels green.
- On `present → absent` transition: pixels red.
- Track total presence seconds; print `Presence: Xm Ys` to console every
  5 seconds.
- Knob maps 0–100 to confidence threshold 0.3–0.9.

**New concept**: OpenCV VideoCapture, DNN face detector, confidence
thresholds as a tuneable parameter.

**Wow moment**: Board reacts to you sitting down. Feels like a smart device.

---

### 302: Expression Mood Lamp

**Modulinos**: Pixels + Vibro + Buzzer + Knob
**Vision stack**: TFLite micro expression model (~2 MB, MobileNetV2 backbone)

**Concept**: Webcam classifies facial expression into 3 classes: `neutral`,
`happy`, `surprised`. Each maps to a Pixel color scheme + haptic pattern +
buzzer chord. Python logs the expression timeline. Knob adjusts inference
frequency (how often to re-classify, 0.5–3 s).

**Model**: Use a pre-trained FER (Facial Expression Recognition) TFLite model.
Recommended: `MobileNetV2` fine-tuned on FER2013, 3-class subset
(neutral/happy/surprised), quantized INT8 (~2 MB). Include the `.tflite` file
in `workshop-app/python/`.

**`vision.py`**:
- `detect_face_crop(frame)` → cropped, resized (48×48 grayscale) face region.
  Returns `None` if no face found (use OpenCV Haar cascade for face crop).
- `classify_expression(tflite_interpreter, face_crop)` → `{label, confidence}`.
- Preprocessing: resize to 48×48, grayscale, normalize 0–1.

**`main.py`**:
- Classify at interval set by knob (0.5–3 s).
- Expression → Pixel color: neutral=white, happy=yellow, surprised=cyan.
- Expression → Vibro: neutral=none, happy=short double-pulse, surprised=long pulse.
- Expression → Buzzer: neutral=none, happy=major chord (262+330+392 Hz briefly),
  surprised=rising tone sweep.
- Print `Expression: happy (87%)` to console.

**New concept**: TFLite inference on embedded Linux, preprocessing pipeline
(crop → resize → normalize), classification interval as UX parameter.

**Wow moment**: Smile and the LEDs turn yellow and play a chord.

---

### 303: Hand Light Painter

**Modulinos**: LED Matrix + Pixels + Vibro + Buzzer
**Vision stack**: MediaPipe Hands

**Concept**: MediaPipe Hands tracks your index fingertip position in the
webcam frame. The fingertip position maps directly to an (x, y) cell on the
8×8 LED Matrix — move your finger and the cursor follows in real time.
Make a fist to put the pen down (draw mode) — the trail is painted onto the
matrix. Open your hand to lift the pen (move mode). Hold both hands in frame
to trigger a clear + replay sequence: matrix wipes, then redraws the stroke
history pixel-by-pixel with Buzzer ticks and a Vibro pulse at the end.
Pixels show current mode by color (green = drawing, blue = moving, white = replay).

**`vision.py`**:
- Init MediaPipe Hands with `max_num_hands=2`, `min_detection_confidence=0.7`.
- `detect_hands(frame)` → list of hand dicts, each with:
  - `index_tip: (x_norm, y_norm)` — index fingertip, normalized 0–1.
  - `is_fist: bool` — true if all finger tips are below their MCP joints
    (simple fist detection from landmark y-coordinates).
- Return up to 2 hands.

**`main.py`**:
- Single-hand mode: map index tip (x, y) normalized → matrix cell (0–7, 0–7).
- Fist = pen down: record cell in stroke list + light it.
- Open hand = pen up: move cursor without recording.
- Two hands detected simultaneously for >0.5 s → trigger replay:
  clear matrix, redraw stroke list at 80 ms/pixel, Buzzer tick per step,
  Vibro pulse when complete.
- Pixels show mode: green (drawing), blue (moving), white (replaying), red (no hand).
- Print fingertip coordinates and stroke length to console.

**New concept**: Hand landmark detection for cursor control (no buttons),
gesture-as-input (fist vs. open hand), two-hand trigger interaction.

**Wow moment**: Paint on the LED Matrix with your finger in the air.
Both hands = replay. No physical contact at all.

---

### 304: Object Counter + Relay

**Modulinos**: Latch Relay + LED Matrix + Buttons (A/B/C) + Pixels + Buzzer
**Vision stack**: MobileNetV2-SSD TFLite (COCO, 80 classes)

**Concept**: On-device object detection. Counts occurrences of a chosen
COCO category in the webcam frame. Relay triggers (latches ON) when count
exceeds a configurable threshold — simulates an access gate or alarm.
LED Matrix shows rolling count as a 2-digit display. Button A cycles the
tracked category (person, bottle, phone, cup, book). Button B sets the relay
threshold. Button C resets count and unlatches relay. Pixels show
current relay state (green=off, red=latched).

**Model**: `mobilenet_v2_ssd_coco_quant.tflite` (quantized INT8, ~6 MB).
Include with the module. Input: 300×300 RGB, normalized.

**`vision.py`**:
- Load SSD model with TFLite interpreter.
- `detect_objects(frame, category_id, confidence_threshold)` → count of
  detected objects matching category_id above threshold.
- Apply NMS (non-maximum suppression) to avoid double-counting overlapping
  detections.

**`main.py`**:
- Inference every ~200 ms (5 FPS is enough for counting).
- Track rolling count with a 3-second exponential moving average to avoid
  jitter.
- Relay latches ON when smoothed count > threshold. Stays latched until
  Button C.
- LED Matrix displays count (0–99) as two digits.
- Print `Detecting: person | Count: 2 | Threshold: 3 | Relay: OFF` to console.

**New concept**: Object detection vs. classification, confidence filtering,
non-maximum suppression, relay actuation from a vision signal, no cloud API.

**Wow moment**: Count people walking past. The relay triggers at 3.
All local. No internet.

---

### 305: Multi-Modal Sentinel

**Modulinos**: Movement (IMU) + Thermo + Pixels + Vibro + Buzzer
**Vision stack**: OpenCV frame differencing (no ML model needed)

**Concept**: Three independent sensor streams — camera motion (frame diff),
IMU shake, and temperature spike — each contribute "evidence" to a shared
event score. When the combined score exceeds a threshold, the Sentinel alerts:
Pixels flash, haptic fires, Buzzer sounds. Knob adjusts global sensitivity.
Python logs each trigger with which sensor(s) contributed.

**Design goal**: Teach multi-modal sensor fusion — the board triggers on a
wider range of events than any single sensor could catch, but also rejects
false positives better because all sensors must agree (weighted sum, not
majority vote).

**`vision.py`**:
- `motion_score(prev_frame, curr_frame)` → float 0–1 using frame differencing.
  Resize to 160×120 before diffing for speed. Threshold pixel diff count
  normalized to frame area.

**`main.py`**:
- Sample all 3 sources every 100 ms.
- Compute weighted score: `score = 0.5*motion + 0.3*imu_shake + 0.2*temp_spike`.
  Each sub-score is a float 0–1 derived from its channel's z-score against
  a rolling 10-second baseline.
- Alert if score > knob-set threshold (0.3–0.9).
- After alert: 2-second cooldown before re-arming.
- Print which sensor fired and its contribution each alert.

**New concept**: Multi-modal sensor fusion, weighted evidence combination,
rolling baselines per channel, cooldown logic, building a system where no
single modality is authoritative.

**Wow moment**: The camera sees you wave. Shake the board. Blow on it.
All three trigger the same alert, but from completely different sensors.

---

## 7. Module Generation Checklist

When generating a new module, produce all of the following:

```
NNN-module-name/
├── README.md
├── workshop-app.zip
└── workshop-app/
    ├── app.yaml
    ├── python/
    │   ├── main.py
    │   └── (helper .py files if needed)
    └── sketch/
        ├── sketch.ino
        └── sketch.yaml
```

**Before writing any code**:
- [ ] Re-read Section 2 (conventions) and Section 3 (canonical examples).
- [ ] Confirm every Bridge handler uses only `int` arguments and return values.
- [ ] Confirm `sketch.yaml` is copied verbatim from the template.
- [ ] Confirm `main.py` starts with `from arduino.app_utils import *`.
- [ ] Confirm `time.sleep(0.05)` is at the end of every loop iteration.
- [ ] Confirm `time.monotonic()` is used for elapsed time (never `time.time()`).
- [ ] Confirm no comments that explain what the code does — only non-obvious WHY.

**After writing code**:
- [ ] Every Modulino used has a matching `ModulinoXxx` object in `sketch.ino`.
- [ ] Every Bridge function called in Python has a matching `Bridge.provide()`
      in `setup()`.
- [ ] `Bridge.provide_safe()` is used for all display/actuator handlers
      (anything that drives Pixels, Vibro, Buzzer, Motors, Relay).
- [ ] `Bridge.provide()` (non-safe) is used only for sensor read functions.
- [ ] All incoming Bridge values are `constrain()`-ed before use in MCU code.
- [ ] `pixels.set()` always uses brightness `25`.
- [ ] `App.run(user_loop=loop)` is the last line of `main.py`.
- [ ] README follows the section order: description, prerequisites, hardware
      setup, App Lab setup, how it works (with diagram), files, sources.
- [ ] `app.yaml` `name:` field is `UNO Q <Module Name>`.

**200-series additional checks**:
- [ ] A separate `<name>_model.py` file exists for all ML logic.
- [ ] Model uses stdlib only (no numpy, no sklearn).
- [ ] Model is saved/loaded as JSON to `<app_root>/data/<name>.json`.
- [ ] State machine has at minimum: `training_ready`, `capturing`, `fitting`,
      `live` modes.
- [ ] Haptic feedback codes 0–3 are used as defined in Section 5.

**300-series additional checks**:
- [ ] `vision.py` exists and contains all cv2/tflite/mediapipe code.
- [ ] `cap.release()` is called on exit.
- [ ] Frames are resized before inference.
- [ ] Camera init block matches the pattern in Section 6.
