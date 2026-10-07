# QC x Arduino UNO Q Workshops

This monorepo contains workshop materials for building projects with the Arduino UNO Q. Each workshop lives in its own directory with setup instructions, required hardware, source code, and supporting resources.

## Workshop Content

### `10x`: Hardware and App Lab foundations

Practice sensor input, physical feedback, and communication between the MCU and Linux MPU through Bridge.

| Workshop              | Description                                                                                             | Hardware                                           | Materials                             |
| --------------------- | ------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------- |
| `101: Haptic Dial`    | Build a physical dial that controls LEDs and haptic feedback across the UNO Q's MCU and Linux MPU.      | UNO Q, Modulino Knob, Pixels, and Vibro            | [View content](./101-haptic-dial/)    |
| `102: Proximity Lamp` | Build a proximity lamp with distance-based LED colors and haptic alerts at a knob-adjustable threshold. | UNO Q, Modulino Distance, Knob, Pixels, and Vibro  | [View content](./102-proximity-lamp/) |
| `103: Theremin Synth` | Play notes with hand distance, select musical scales with the knob, and visualize pitch on LEDs.        | UNO Q, Modulino Distance, Knob, Pixels, and Buzzer | [View content](./103-theremin-synth/) |
| `104: Safe Cracker`   | Crack a seven-stage safe with the dial, guided by haptic ticks and Pixel progress.                      | UNO Q, Modulino Knob, Pixels, and Vibro            | [View content](./104-safe-cracker/)   |

### `20x`: On-device machine learning

Collect examples, train local models, and use predictions to drive physical feedback. These workshops assume familiarity with App Lab and the MCU, MPU, and Bridge roles introduced in `10x`.

| Workshop            | Description                                                                                          | Hardware                                | Materials                           |
| ------------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------- | ----------------------------------- |
| `201: Gesture Dial` | Train a personal edge-AI dial that recognizes rotation gestures and expresses prediction confidence. | UNO Q, Modulino Knob, Pixels, and Vibro | [View content](./201-gesture-dial/) |
| `202: Anomaly Dial` | Learn normal dial movement locally and flag unusual speed, duration, or direction changes.           | UNO Q, Modulino Knob, Pixels, and Vibro | [View content](./202-anomaly-dial/) |

## Choose the right workshop files

Each numbered folder is a separate App Lab project. The filenames repeat across workshops, so always include the workshop folder when locating a file or asking for a change.

1. Open your workshop's **View content** link and follow its README for hardware, wiring, and setup.
2. Import the `workshop-app.zip` inside that same folder into App Lab. For workshop 103, use [`101-haptic-dial/workshop-app.zip`](./101-haptic-dial/workshop-app.zip).
3. To edit source, use that folder's `workshop-app/`: `python/main.py` runs on the Linux MPU, `sketch/sketch.ino` runs on the MCU, and `app.yaml` identifies the app. For example, workshop 103's Python entry point is [`101-haptic-dial/workshop-app/python/main.py`](./101-haptic-dial/workshop-app/python/main.py).

For coding assistants, [AGENTS.md](./AGENTS.md) defines how to select the workshop, scope edits, and verify changes.
