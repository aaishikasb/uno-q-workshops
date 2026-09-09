# 105: Proximity Lamp

Build a configurable proximity alert lamp using a Time-of-Flight distance sensor. As an object moves
closer, the Pixel LEDs light up in a color gradient from green to red and a Vibro haptic pulse fires
the moment the object crosses your chosen alert threshold. You will learn how ToF sensors work, how
to map a continuous sensor range to a visual display, and how to detect threshold crossings using
edge detection rather than polling.

## Prerequisites

- Completed [101: Haptic Dial](../101-haptic-dial/README.md)
- Arduino App Lab installed and connected to your UNO Q board

## Hardware Setup

Connect the following Modulinos to your Arduino UNO Q using Qwiic cables, daisy-chained in any order:

```
UNO Q
  └── Modulino Distance   (VL53L4CD ToF sensor — point the sensor window outward)
  └── Modulino Pixels     (8 RGB LEDs)
  └── Modulino Vibro      (haptic motor)
  └── Modulino Knob       (rotary encoder)
```

Point the Distance sensor window toward open space — it needs a clear line of sight to measure
correctly. Avoid pointing it at a mirror or highly reflective surface during setup.

## App Lab Setup

1. Open **Arduino App Lab** in your browser and connect to your UNO Q board.
2. Click **Import** and select `workshop-app.zip` from this folder.
3. Click **Run**. App Lab will compile the sketch, flash the MCU, and start the Python app.
4. Watch the console — you should see `Ready.` and a startup haptic pulse within a few seconds.

## How It Works

```
Modulino Distance          Modulino Knob
  (ToF, 20 Hz poll)        (threshold setting)
       |                          |
       v                          v
  MCU loop()             read_knob() via Bridge
  latestDistance  ──────────────────────────────> Python loop()
                                                        |
                                          ┌─────────────┴──────────────┐
                                          |                            |
                                   map distance                  knob → threshold
                                   → color code                  50–500 mm
                                   → lit count (0–7)
                                          |
                                          v
                              detect alert zone crossing
                              (edge: was outside, now inside)
                                          |
                              ┌───────────┴──────────┐
                              |                      |
                       show_distance()          pulse_alert()
                       (color, count,           (haptic, once
                        alert pixel 7)           on entry only)
                              |
                         MCU updates
                         Pixels + Vibro
```

**Distance bands:**

| Distance | Color | Meaning |
|---|---|---|
| > 1000 mm | Green | Far |
| 300–1000 mm | Yellow | Mid |
| 150–300 mm | Orange | Close |
| < 150 mm | Red | Very close |

**Pixel layout:**
- Pixels 0–6 fill left to right as the object gets closer (7 = closest, 0 = farthest detected).
- Pixel 7 lights white independently when the object is inside the alert zone.

**Alert edge detection:**
Python tracks `in_alert_zone` state. The haptic only fires on the `False → True` transition —
not continuously while the object is inside the zone. This is why you get one pulse when your
hand enters the zone, not a continuous buzz.

**Knob:**
Turning the Knob adjusts the alert threshold from 50 mm (full left) to 500 mm (full right).
The current threshold prints to console on every change.

## Files

```
105-proximity-lamp/
├── README.md
├── workshop-app.zip
└── workshop-app/
    ├── app.yaml
    ├── python/
    │   └── main.py          Distance reading, threshold logic, edge detection
    └── sketch/
        ├── sketch.ino       ToF polling loop, Pixel gradient, Vibro pulse
        └── sketch.yaml      Arduino build configuration
```

## Sources

- [Modulino Distance (VL53L4CD) documentation](https://docs.arduino.cc/hardware/modulino-distance/)
- [Modulino Pixels documentation](https://docs.arduino.cc/hardware/modulino-pixels/)
- [Modulino Vibro documentation](https://docs.arduino.cc/hardware/modulino-vibro/)
- [Modulino Knob documentation](https://docs.arduino.cc/hardware/modulino-knob/)
- [Arduino UNO Q documentation](https://docs.arduino.cc/hardware/uno-q/)
