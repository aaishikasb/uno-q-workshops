# 104: Shake Dice

Build a physical die that rolls itself. Shake the Arduino UNO Q and the IMU Z-axis detects the impact — acceleration peak and shake duration combine to produce a result. Pixels display the die face, the Buzzer plays a fanfare, and the Vibro pulses once per pip. You will learn how IMU acceleration sampling works, how to detect gesture onset and release using a threshold state machine, and how to derive a varied-but-deterministic result from physical input.

## Prerequisites

- Completed [101: Haptic Dial](../101-haptic-dial/README.md)
- Arduino App Lab installed and connected to your UNO Q board

## Hardware Setup

Connect the following Modulinos to your Arduino UNO Q using Qwiic cables, daisy-chained in any order:

```
UNO Q
  └── Modulino Movement  (LSM6DSOX IMU — accelerometer + gyroscope)
  └── Modulino Pixels    (8 RGB LEDs)
  └── Modulino Buzzer    (piezo buzzer)
  └── Modulino Vibro     (haptic motor)
  └── Modulino Buttons   (A / B / C buttons)
```

Hold the board flat in your palm during a roll so the Z-axis (perpendicular to the board surface) takes the full impact of the shake.

## App Lab Setup

1. Open **Arduino App Lab** in your browser and connect to your UNO Q board.
2. Click **Import** and select `workshop-app.zip` from this folder.
3. Click **Run**. App Lab will compile the sketch, flash the MCU, and start the Python app.
4. A short haptic pulse on startup confirms the hardware is ready.

## How It Works

```
Shake the board
      │
      ▼
[MCU: read_az() — IMU Z-axis via Bridge handler]
      │
      ▼
[Python: threshold state machine]
  az_g >= 2.0 g? ──yes──> record shake_start, track peak_az
  az_g  < 2.0 g? ──yes──> if duration >= 80 ms: valid shake
                                │
                                ▼
                     derive_result(peak_az, duration_ms, sides)
                     = (peak_int + duration_ms) % sides + 1
                                │
                    ┌───────────┴───────────┐
                    │                       │
             animate_roll()           reveal(value, sides)
          (12 frames, 60 ms each)           │
                                    ┌───────┴───────┐
                                    │               │
                             show_face()      play_fanfare()
                             show_rolling()   pip_pulse() × value
                                    │
                               MCU updates
                             Pixels + Buzzer + Vibro
```

**Shake detection**: Python reads the IMU Z-axis via Bridge at 50 Hz. When acceleration exceeds 2.0 g, the shake timer starts. When it drops back below threshold and at least 80 ms have elapsed, the roll is confirmed. Peak and duration are recorded throughout.

**Result derivation**: `(peak_az_int + shake_duration_ms) % sides + 1`. Neither value alone is uniform — their sum spreads results across the face range more evenly across different shake styles.

**Die faces (d6)**: Pixels 0–7 are arranged as two rows of four. Each d6 face uses a bitmask matching standard pip positions. d8 uses a left-to-right bar fill (1–8 pixels).

**Controls**:
- **Button A**: re-roll without shaking — uses stored peak scaled by current time.
- **Button B**: toggle between d6 and d8 mode (gold pixels vs. blue pixels).

## Files

```
104-shake-dice/
├── README.md
├── workshop-app.zip
└── workshop-app/
    ├── app.yaml
    ├── python/
    │   └── main.py          Shake detection, result derivation, animation sequencing
    └── sketch/
        ├── sketch.ino       IMU read, Pixel face patterns, Buzzer fanfare, Vibro pip pulse
        └── sketch.yaml      Arduino build configuration
```

## Sources

- [Modulino Movement (LSM6DSOX) documentation](https://docs.arduino.cc/hardware/modulino-movement/)
- [Modulino Pixels documentation](https://docs.arduino.cc/hardware/modulino-pixels/)
- [Modulino Buzzer documentation](https://docs.arduino.cc/hardware/modulino-buzzer/)
- [Modulino Vibro documentation](https://docs.arduino.cc/hardware/modulino-vibro/)
- [Modulino Buttons documentation](https://docs.arduino.cc/hardware/modulino-buttons/)
- [Arduino UNO Q documentation](https://docs.arduino.cc/hardware/uno-q/)
