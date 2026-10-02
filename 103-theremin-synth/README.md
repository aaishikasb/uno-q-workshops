# 106: Theremin Synth

Play notes by waving your hand over the Distance sensor — no buttons, no touching. The VL53L4CD ToF sensor measures how far your hand is from the board (5–60 cm) and Python maps that distance to a note on the selected scale. The Pixels show pitch as a color gradient (blue = low/far, red = high/close). Turn the Knob to cycle between pentatonic, major, and chromatic scales.

## Prerequisites

- Completed 101: Haptic Dial, or equivalent familiarity with the App Lab import flow.

## Hardware Setup

Connect the following Modulinos to the Arduino UNO Q via I2C (JST/Qwiic daisy-chain):

1. **Modulino Distance** (VL53L4CD) — aim the sensor upward or forward so a hand can pass over it 5–60 cm away.
2. **Modulino Pixels** — any position on the chain.
3. **Modulino Buzzer** — any position on the chain.
4. **Modulino Knob** — any position on the chain.

Power the board via USB. No other wiring required.

## App Lab Setup

1. Open [Arduino App Lab](https://app-lab.arduino.cc) in your browser.
2. Click **Import** and upload `workshop-app.zip`.
3. Flash the sketch to the MCU (the board's Cortex-M4 side).
4. Run `python/main.py` on the MPU (the Linux side).

## How It Works

```
Hand position (distance mm)
        │
        ▼
[MCU: read_distance()]  ──────────────────────────────┐
        │                                              │
        ▼                                             latestDistance
[Python: _distance_to_note_index()]                    │ (cached in
        │                                              │  Bridge handler)
        ├── note_index → freq (Hz)
        ├── note_index → color_code + lit_count
        │
        ▼
[MCU: play_note(freq, 120)]   → Buzzer tone
[MCU: show_zone(color, count)] → Pixels update

[Python: Knob 0–33 = pentatonic, 34–66 = major, 67–100 = chromatic]
```

**Distance → pitch**: 50 mm (very close) = highest note, 600 mm (far) = lowest note. Inverted so bringing your hand closer raises the pitch — matching theremin convention.

**Scale quantization**: raw distance is mapped to a float position across the scale array, then rounded to the nearest integer index. This ensures only in-scale notes play — no dissonant "between" frequencies.

**Hysteresis**: the note only updates when the rounded index changes. Because rounding provides a dead-band around each note's midpoint, small hand tremor does not cause rapid note switching.

## Files

| File | Description |
|---|---|
| `workshop-app/sketch/sketch.ino` | MCU firmware: Distance read, Buzzer and Pixels handlers |
| `workshop-app/sketch/sketch.yaml` | Arduino library manifest |
| `workshop-app/python/main.py` | MPU logic: scale tables, distance-to-note mapping, hysteresis |
| `workshop-app/app.yaml` | App Lab metadata |

## Sources

- [VL53L4CD datasheet](https://www.st.com/en/imaging-and-photonics-solutions/vl53l4cd.html)
- [Arduino Modulino library](https://github.com/arduino-libraries/Arduino_Modulino)
- [Theremin (Wikipedia)](https://en.wikipedia.org/wiki/Theremin)
- Pentatonic scale frequencies: C4–E5 subset of equal temperament
