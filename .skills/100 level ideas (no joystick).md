# 100-Level Workshop Ideas (No Joystick)

These are proposed 100-series modules using any combination of: knob, pixel, vibro, buzzer, light, thermo, distance, movement, and buttons.

---

## 104: Shake Dice

**Modulinos**: Movement + Pixels + Buzzer + Vibro + Buttons

**Concept**: Shake the board to roll a virtual die (1–6). The IMU Z-axis measures total acceleration magnitude. A shake above a threshold locks in a result derived from the shake's peak amplitude and duration — deterministic enough to feel fair, varied enough to feel random. Pixels display the die face pattern (1–6 using standard pip positions). Buzzer plays a short fanfare. Button A re-rolls. Button B toggles between d6 and d8 mode. Vibro pulses once per pip when displaying the result.

**MCU responsibilities**:
- Poll IMU at 100 Hz in `loop()`, cache `latestAz` (×1000 int).
- Expose `read_az()` → int.
- Accept `show_face(value, sides)` — lights Pixels in die-face pattern.
- Accept `roll_fanfare(value)` — plays a 3-note ascending run on Buzzer.
- Accept `pip_pulse()` — short Vibro tick.

**Python responsibilities**:
- Detect shake onset: abs(az/1000) > 2.0 g sustained for >80 ms.
- Track shake peak and duration → derive result as `(peak_int + duration_ms) % sides + 1`.
- Animate Pixels before revealing result: fast random flash for 600 ms, then settle.
- Pulse Vibro once per pip count on reveal.
- Print roll result and mode to console.

**New concept**: IMU magnitude as a gesture trigger, deterministic-but-varied result generation, multi-phase animation (roll → reveal).

**Wow moment**: You physically shake the board and it rolls a die.

---

## 105: Step Counter

**Modulinos**: Movement + Pixels + Vibro + Buttons + Knob

**Concept**: Strap the board to your wrist or clip it to a pocket and walk around the room. The IMU Z-axis detects footstep impacts via peak detection with a 300 ms refractory period. Pixels fill up as a progress bar toward a step goal. Vibro fires a celebration pulse at 25%, 50%, 75%, and 100% of goal. Button A resets count. Button B toggles display between count (pixel fill) and pace (blink rate). Knob sets the goal from 10–200 steps.

**MCU responsibilities**:
- Poll IMU at 100 Hz in `loop()`, cache `latestAz` (×1000 int).
- Expose `read_az()` → int.
- Accept `show_progress(percent)` — fills 0–8 pixels.
- Accept `show_pace(bpm)` — blinks a single pixel at the given bpm rate.
- Accept `celebrate(level)` — drives Vibro with duration mapped to level (1–4).

**Python responsibilities**:
- Peak detection: `az/1000 > 1.8 g` with 300 ms lockout after each step.
- Track total steps, compute pace (steps/min) over a rolling 10 s window.
- Edge detection on 25/50/75/100% milestones → `celebrate()`.
- Knob read once per second — adjust goal in real time.
- Print `Steps: 47 | Goal: 100 | Pace: 62 spm` each second.

**New concept**: Threshold + refractory peak detection, rolling window rate calculation, milestone edge detection.

**Wow moment**: Walk across the room and watch the bar fill. It counted your steps with no setup.

---

## 106: Hot/Cold Treasure Hunt

**Modulinos**: Thermo + Distance + Pixels + Vibro + Buzzer

**Concept**: A two-sensor game. Designate one corner of the room as the "treasure." The Distance sensor (aimed down the room) gives coarse proximity (far = few pixels, close = many pixels). The Thermo sensor detects body heat when a participant's hand hovers nearby and adds a "warmth bonus" to the display. Combined: participants navigate toward the treasure guided only by Pixels + haptic + Buzzer feedback — like a hot/cold game that uses real physics. Python weights both channels and drives a single 0–8 intensity score.

**MCU responsibilities**:
- Read Distance fresh in Bridge handler (same pattern as 102).
- Expose `read_distance()` → int (mm), `read_temp()` → int (°C × 10).
- Accept `show_signal(intensity, mode)` — intensity 0–8 pixels; mode 0=cold (blue), 1=warm (orange), 2=hot (red).
- Accept `buzz_hint(freq, ms)` — single Buzzer pulse.
- Accept `haptic_hint(strength)` — Vibro with mapped duration.

**Python responsibilities**:
- Distance score: map 3000–200 mm → 0–6 (clamp).
- Warmth bonus: temp > ambient+2 °C adds +1; temp > ambient+4 °C adds +2 (max 8 total).
- Determine mode from combined score: 0–2 = cold, 3–5 = warm, 6–8 = hot.
- Buzz and haptic at rate inversely proportional to distance (1× per 2 s at far end, 3× per 1 s when close).
- Print score breakdown each poll: `Dist: 840mm (+3) | Temp: 26.4°C (+1) | Score: 4/8`.

**New concept**: Multi-sensor fusion without ML, scoring as a weighted sum, adaptive feedback rate (pulse frequency scales with closeness).

**Wow moment**: Someone navigates to the "treasure" using only LED + buzz feedback. The room gets it instantly.

---

## 107: Morse Tapper

**Modulinos**: Buttons + Pixels + Buzzer + Vibro

**Concept**: Tap Morse code using Button A (dot) and Button B (dash). Pixels display the current symbol accumulating: each dot/dash appended lights one more pixel. Button C sends the current letter — Python decodes the dot/dash sequence, maps it to the corresponding character, and prints it. Buzzer plays the classic Morse tones (dot = 80 ms @ 700 Hz, dash = 240 ms @ 700 Hz). Vibro confirms each successful letter decode. A 2-second idle auto-sends (like a real Morse key).

**MCU responsibilities**:
- Expose `read_button_a/b/c()` → int (0/1).
- Accept `play_symbol(is_dash)` — plays dot or dash tone on Buzzer.
- Accept `show_symbols(count, bitmask)` — displays accumulated symbols as Pixels.
- Accept `confirm_letter()` — short Vibro pulse.
- Accept `error_flash()` — red flash on Pixels for unknown sequence.

**Python responsibilities**:
- State: accumulate list of `'.'` and `'-'` strings on button press events.
- Lookup against a standard Morse table (A–Z, 0–9).
- Auto-send on 2 s idle using `time.monotonic()` delta.
- Print decoded character and running message to console.
- Clear symbol list after each send.

**New concept**: Timing-window input, edge detection on button press, lookup-table decoding, idle timeout as a delimiter.

**Wow moment**: Tap out your initials and see them print. Then tap SOS.

---

## 108: Ambient Synesthesia

**Modulinos**: Light + Pixels + Buzzer + Knob + Vibro

**Concept**: The LTR381RGB sensor reads ambient light color (R, G, B channels). Python maps the dominant color channel to a Pixel color scheme and to a harmonic chord on the Buzzer. Blue light → cool pixels + minor chord. Red light → warm pixels + major chord. Green light → green pixels + suspended chord. Knob controls update rate (slow drift vs. fast response). Vibro pulses when the dominant channel shifts — a "color change event." Shine different colored lights or hold colored objects near the sensor.

**MCU responsibilities**:
- Expose `read_r()`, `read_g()`, `read_b()` → int (lux × 10).
- Accept `show_color(r, g, b, lit_count)` — sets all lit pixels to the given color.
- Accept `play_chord(root_freq, quality)` — plays 3-note chord on Buzzer briefly.
- Accept `color_shift_pulse()` — 150 ms Vibro on dominant channel change.

**Python responsibilities**:
- Normalize R/G/B to chromaticity (divide each by R+G+B sum).
- Detect dominant channel. Hysteresis: only trigger chord/vibro when dominant channel changes and holds for 3 consecutive samples.
- Pixel count 2–8 scales with total lux (bright room = more pixels lit).
- Knob 0–100 maps update interval from 2 s to 100 ms.
- Print `Dominant: BLUE | lux: 312 | chord: minor` to console.

**New concept**: Chromaticity normalization, color-to-sound synesthesia, hysteresis for stable dominant-channel detection.

**Wow moment**: Shine your phone flashlight through a colored filter (or your hand) and the board plays a chord and changes color.
