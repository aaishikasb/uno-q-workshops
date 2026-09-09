# Workshop Progression Tracks

Each track starts at a 100-level embedded module and escalates through ML (200) and attendee-driven vision/complexity (300). The same hardware stays on the table across all three tiers — the progression is purely in what the software learns and how much the participant shapes it.

---

## Track A: Haptic Dial → Gesture Dial → Personal Gesture OS

### 101: Haptic Dial *(exists)*
**Hardware**: Knob + Pixels + Vibro  
**Concept**: Turn the knob to set a 0–100 level. Pixels fill as a color-coded bar. Press the knob for a haptic pulse whose duration scales with level. Entirely rule-based — the board does exactly what the code says.  
**What's fixed**: The mapping from knob position to color and haptic strength is hard-coded. Every board behaves identically.

---

### 201: Gesture Dial *(exists)*
**Hardware**: Knob + Pixels + Vibro  
**ML concept**: The same hardware as 101, but the board now learns to recognize the *way* you turn the knob rather than just its position. Participants record 5 examples each of three gestures — `flick_left`, `flick_right`, `wiggle` — and the board trains a nearest-centroid classifier on the resulting knob time-series features.

**Feature extraction**: knob readings over a 1.4 s window → resampled to fixed length → travel, reversal count, duration, peak step appended → standardized. Nearest-centroid with per-class radius for in-distribution gating.

**What changes**: The board stops reading state (where is the knob?) and starts reading intent (what did the person mean to do?). A fast flick left and a slow flick left both classify as `flick_left` even though their raw values differ.

**Wow moment**: Two people swap boards. Each board only recognizes its owner's gesture style. The same physical motion on someone else's trained board returns uncertain.

---

### 30X: Gesture OS
**Hardware**: Knob + Pixels + Vibro + Webcam  
**300-level additions**: Webcam adds face-presence detection (OpenCV res10 SSD). Each person who sits down at the board is detected as a new user; their personal gesture model loads automatically from a named JSON file. The knob gestures can now be mapped to arbitrary actions — not just label display — forming a personal, private control interface.

**What attendees build**: Each participant trains their own gesture vocabulary (same UX as 201 but with 4–5 classes instead of 3). They then map each gesture to an action of their choice: a console command, a sound trigger, a light pattern, a message printed to screen. The webcam watches for who is present and loads the right model. When a participant steps away and another sits down, the board silently switches vocabularies.

**ML concept**: 201's nearest-centroid classifier extended to 5 classes + face-presence gating for multi-user model management. The face detection is binary (someone is here / no one is here) — not identity recognition — so it triggers a "who are you?" prompt on change rather than inferring identity.

**Attendee contribution**: Participants choose their own gesture vocabulary names, record all training data, and define what each gesture does. The workshop ends with each person demonstrating a personal interface that nobody else can operate — because nobody else trained it.

**Wow moment**: One person demonstrates their board. Another sits down. The board asks "who are you?" and loads a completely different vocabulary. Same hardware, two completely different machines.

---

## Track B: Proximity Lamp → Approach Trainer → Object-Aware Sentinel

### 102: Proximity Lamp *(exists)*
**Hardware**: Distance + Pixels + Vibro + Knob  
**Concept**: ToF sensor measures object distance. Pixel count and color gradient show proximity (green = far, red = close). Haptic fires once on entry into a configurable alert zone. Knob sets the alert threshold. Rule-based — the mapping from distance to color and the threshold crossing logic are hard-coded.  
**What's fixed**: All objects and all approaches trigger the same response. The board cannot distinguish a fast lunge from a slow creep.

---

### 20X: Approach Trainer
**Hardware**: Distance + Pixels + Vibro + Knob  
**ML concept**: The same hardware as 102, but the board now learns to recognize *how* something approaches — not just that it entered the zone. Participants record 5 examples of three approach styles: `lunge` (fast approach from far), `creep` (slow approach from mid-range), `pulse` (quick in-and-out oscillation). Each is a 1-second time-series of distance readings.

**Feature extraction**: distance readings at 20 Hz over a 1 s window → resample to fixed length → append approach velocity (first derivative mean), reversal count, and total travel. Nearest-centroid classifier, same architecture as 201.

**What changes**: The board distinguishes intent from presence. A person lunging toward the sensor triggers a different response than someone slowly entering the zone — even if they both cross the same threshold.

**Wow moment**: Lunge at it — one haptic pattern. Creep toward it — a different one. Same sensor, two completely different behaviors based on learned style.

---

### 30X: Object-Aware Sentinel
**Hardware**: Distance + Pixels + Vibro + Knob + Webcam  
**300-level additions**: Webcam adds object identity (MobileNetV2-SSD TFLite) alongside the ToF approach classification. The distance sensor tells the board *how* something is approaching; the camera tells it *what*.

**What attendees build**: Participants train their own approach-style vocabulary (same UX as 20X). The webcam simultaneously classifies the approaching object into COCO categories. The board combines both signals — approach style × object class — to trigger compound responses. A person creeping toward the board triggers a different light and sound pattern than a bottle creeping toward it, even at the same speed and distance.

**ML concept**: Two independent classifiers fused by a simple rule table participants define themselves: rows are approach styles, columns are object classes, each cell maps to a response. The fusion logic is participant-authored, not hard-coded.

**Attendee contribution**: Participants define the compound response table — what happens for each (approach, object) pair — and record their own approach-style training data. The sentinel reflects their creative choices about what combinations mean.

**Wow moment**: Slowly move a phone toward the board. It plays one sound. Slowly move your hand. It plays a different one. The board knows what's coming and how.

---

## Track C: Theremin → Instrument Trainer → Collaborative Composer

### 103: Theremin Synth *(exists)*
**Hardware**: Distance + Pixels + Buzzer + Knob  
**Concept**: Hand position plays notes on a quantized scale. Rule-based pitch mapping.  
**What's fixed**: The scale shapes and the distance-to-pitch formula are hard-coded.

---

### 20X: Theremin Stylist
**Hardware**: Distance + Pixels + Buzzer + Vibro + Knob  
**ML concept**: Learn the participant's own playing vocabulary — not just "what note" but "what phrase shape."

**What changes**: The board watches how you move your hand and learns to recognize your recurring gestures as named musical phrases. You record 3 phrases: `sweep_up`, `sweep_down`, `hover`. Each is a 1-second time-series of distance readings. Nearest-centroid classifier (same architecture as 201) trained on those examples. In live mode, the board classifies your gesture in real time and triggers a pre-composed melodic fragment for each phrase rather than a single note — so a sweep becomes a run of notes, not just one pitch.

**New concept**: Time-series classification on a continuous analog sensor (not a knob). The ML layer transforms a simple instrument into one that speaks in phrases.

**Wow moment**: Your sweep up sounds like a rising arpeggio. Someone else's sweep up sounds different because they trained it differently.

---

### 30X: Duo Theremin
**Hardware**: Distance + Pixels + Buzzer + Vibro + Knob + Webcam  
**300-level additions**: Webcam adds a second spatial dimension (X position of hand in frame). Distance sensor is one axis, webcam hand-X is the other. Together they form a 2D control space.

**What attendees build**: Each participant trains their own 2D vocabulary — 4–5 named zones in the Distance×X space (e.g. "top-left", "center", "sweep-right"). Each zone drives a different melodic loop. Two participants can play simultaneously — one controlling distance, one waving left/right in frame — creating a two-voice instrument.

**ML concept**: 2D zone classification using k-NN on [distance, webcam_x] feature pairs. Attendees define zone boundaries by recording examples, not by coding them.

**Attendee contribution**: Participants choose their zone vocabulary, record their own training data, and define which musical fragment each zone triggers. The instrument is entirely participant-authored.

**Wow moment**: Two people improvise together on one board. Neither is playing "the same instrument" because they each trained theirs differently.

---

## Track D: Shake Dice → Shake Recognizer → Motion Controller

### 104: Shake Dice *(proposed)*
**Hardware**: Movement + Pixels + Buzzer + Vibro + Buttons  
**Concept**: Shake amplitude + duration → deterministic die roll. Rule-based.  
**What's fixed**: The shake-to-result formula is hard-coded. All shakes are treated the same.

---

### 20X: Shake Spellcaster
**Hardware**: Movement + Pixels + Buzzer + Vibro + Knob  
**ML concept**: Train 3 distinct shake styles as separate classes — `flick` (fast wrist snap), `roll` (slow figure-8), `slam` (abrupt vertical drop). Each style unlocks a different game action (attack, defend, magic).

**Feature extraction**: 40-sample IMU window at 50 Hz → resample to fixed length → extract peak magnitude, axis distribution (X vs. Y vs. Z dominance), and reversal count. Nearest-centroid classifier. Same structure as 201 but the sensor is the full 3-axis IMU rather than a knob.

**New concept**: 3-axis motion signature as a feature. The direction of the shake matters, not just its magnitude.

**Wow moment**: A flick does something completely different from a slam. You can feel the distinction even before looking at the LEDs.

---

### 30X: Full-Body Controller
**Hardware**: Movement + Pixels + Buzzer + Vibro + Webcam  
**300-level additions**: MediaPipe Pose (or Hands) adds body position as a second signal layer. IMU is on the board (held or worn), webcam watches from a fixed angle.

**What attendees build**: Participants define a personal gesture vocabulary of 5+ moves combining IMU signature (how the board moves) with body pose (what MediaPipe sees). Each gesture maps to a game event or instrument trigger. Attendees record all their own training examples — the workshop is largely a training session, not a coding session.

**ML concept**: Feature concatenation — IMU features + pose keypoint delta features (MediaPipe landmark displacement over 0.5 s window). k-NN on the combined vector.

**Attendee contribution**: Participants invent their own gesture vocabulary, record training data, and iterate on classification in real time. The board only does what it's taught.

**Wow moment**: The board recognizes a specific pose + shake combination that no one else's does. Fully personal.

---

## Track E: Step Counter → Activity Classifier → Personal Coach

### 105: Step Counter *(proposed)*
**Hardware**: Movement + Pixels + Vibro + Buttons + Knob  
**Concept**: Threshold peak detection counts steps. Refractory period prevents double-counting.  
**What's fixed**: One activity type (walking). No model of what "walking" looks like vs. anything else.

---

### 20X: Activity Classifier
**Hardware**: Movement + Pixels + Vibro + Knob  
**ML concept**: Train 3 activity states: `walking`, `jogging`, `idle`. Collect 5 examples of each by performing the activity for 2 seconds while pressing the knob. Feature vector: RMS of Z-axis over the window, peak count per second, mean inter-peak interval, axis variance ratio (Z vs. XY — walking is mostly vertical, jogging has more XY). Nearest-centroid classifier.

**New concept**: Activity as a statistical feature of a time window, not a single peak event. The classifier generalizes across walking speeds because it normalizes by window duration.

**Wow moment**: Start jogging in place. The LEDs shift color mid-step. It knows you sped up.

---

### 30X: Personal Rep Counter
**Hardware**: Movement + Pixels + Vibro + Buttons + Webcam  
**300-level additions**: MediaPipe Pose provides joint angles (elbow, knee, shoulder). IMU gives raw motion energy. Together they can classify exercise type AND count reps.

**What attendees build**: Participants train their own exercise vocabulary — whatever 3 exercises they choose (pushup, squat, jumping-jack, etc.). They record their own examples. The system learns to recognize each exercise from the combination of pose angles + IMU signature, and counts reps by detecting the cyclical pattern in the IMU stream (peak detection on the classified signal).

**ML concept**: Two-stage pipeline — exercise classifier (k-NN on pose + IMU features) → rep counter (peak detection on the classified activity stream). Attendees author both stages.

**Attendee contribution**: Full choice of exercise vocabulary, all training data self-recorded, rep threshold tunable via knob. Every participant leaves with a counter trained on their own body.

**Wow moment**: It counts your pushups. It doesn't count your squats as pushups. Because you taught it the difference.

---

## Track F: Hot/Cold Hunt → Anomaly Watchdog → Smart Room Sentinel

### 106: Hot/Cold Treasure Hunt *(proposed)*
**Hardware**: Thermo + Distance + Pixels + Vibro + Buzzer  
**Concept**: Weighted sensor fusion game. Score = f(distance, body heat). Rule-based thresholds.  
**What's fixed**: The thresholds and weights are hard-coded. "Normal" is assumed.

---

### 20X: Intruder Detector
**Hardware**: Thermo + Distance + Pixels + Vibro + Knob  
**ML concept**: Unsupervised anomaly detection — same architecture as the planned 204 Anomaly Watchdog but scoped to just these two sensors. Baseline 30 seconds of "normal" (empty space, ambient temp). Fit per-channel μ and σ. In watch mode, z-score each reading against baseline. Alert when max(z-scores) exceeds knob-set threshold.

**New concept**: The board learns what "nothing happening" looks like. Any deviation from that is anomalous — no labels needed. This is explicitly unsupervised, teaching the contrast with 201's supervised approach.

**Wow moment**: Wave your hand near the Distance sensor without touching. It triggers. Breathe on the Thermo. Different channel, same alert. The board learned "normal" and you broke it.

---

### 30X: Multi-Modal Room Monitor
**Hardware**: Thermo + Distance + Pixels + Vibro + Buzzer + Webcam  
**300-level additions**: Webcam adds frame-differencing motion score as a third channel. Three independent sensor streams feed a shared anomaly model.

**What attendees build**: Participants choose what "normal" is and record it themselves (the baseline recording is participant-controlled: they set the room state before starting). They then set per-channel sensitivity via button interface. Multiple participants can define different "normal" baselines and compete to see whose is most sensitive. Final challenge: try to sneak past the sentinel using only one sensor axis while others trigger.

**ML concept**: Weighted multivariate z-score fusion. Attendees adjust channel weights in real time and observe how the alert behavior changes — a live lesson in feature weighting.

**Attendee contribution**: Participants own the baseline, the sensitivity settings, and the "defeat the sensor" challenge design. The workshop becomes adversarial.

**Wow moment**: One participant covers the camera, another tries to sneak in from the side. The Thermo gets them anyway.

---

## Track G: Morse Tapper → Personal Tap Cipher → Collaborative Encoder

### 107: Morse Tapper *(proposed)*
**Hardware**: Buttons + Pixels + Buzzer + Vibro  
**Concept**: Standard Morse code via fixed lookup table. The encoding is universal.  
**What's fixed**: The dot/dash alphabet is pre-defined. Everyone uses the same code.

---

### 20X: Tap Rhythm Trainer
**Hardware**: Movement + Pixels + Vibro + Knob  
**ML concept**: Learn the participant's personal tap rhythms as distinct classes — not fixed Morse, but whatever 3 patterns they choose. Feature extraction: inter-tap intervals normalized by total duration (same as the planned 203 Tap Rhythm Classifier). Nearest-centroid classifier. Participants tap on the desk near the IMU; the IMU Z-axis picks up impact vibration.

**What changes**: The encoding is personal. Your "word for yes" is the rhythm you trained, not a universal standard. No two participants have the same vocabulary.

**New concept**: Rhythm as a personal biometric. The same concept (inter-onset interval features) as a professional rhythm-recognition system, built from stdlib math.

**Wow moment**: Tap your pattern. Only your board understands it. Someone else's board doesn't react.

---

### 30X: Collaborative Cipher Room
**Hardware**: Buttons + Movement + Pixels + Buzzer + Vibro + Webcam  
**300-level additions**: Webcam adds face detection (OpenCV res10 SSD) to identify which participant is at the board. Each participant's trained tap model is stored under their face's presence flag. When a new face appears, the system loads that person's tap vocabulary.

**What attendees build**: Each participant trains their own 3-class tap vocabulary, records it as a named model file. The webcam watches for face presence (not identity — just "someone is here" vs. "the same person is still here"). When the participant changes, the system prompts to select which model to load. Participants then exchange encoded tap messages across the room — only the sender knows what their rhythm means.

**ML concept**: Two independent classifiers running in sequence: face-presence detector → tap-rhythm classifier. Attendees author both training phases.

**Attendee contribution**: Participants design their own encoding schemes, exchange ciphered messages, and try to decode each other's taps. The workshop becomes a game.

**Wow moment**: Tap a rhythm. Your neighbor hears the buzzer and has to guess what you said. They can't — because they didn't train your model.

---

## Track H: Ambient Synesthesia → Color Mood Learner → Living Palette

### 108: Ambient Synesthesia *(proposed)*
**Hardware**: Light + Pixels + Buzzer + Knob + Vibro  
**Concept**: Dominant RGB channel → rule-based chord + color mapping.  
**What's fixed**: The color-to-mood-to-sound mapping is hard-coded by the developer.

---

### 20X: Personal Color Moods
**Hardware**: Light + Buttons + Pixels + Buzzer + Vibro + Knob  
**ML concept**: Participants label colors with their own emotional vocabulary. Hold a colored object under the Light sensor and press Button A ("calm"), Button B ("energetic"), or Button C ("tense"). Collect 5 samples per mood. k-NN classifier (k=3) on chromaticity features — same algorithm as 205 Adaptive Color Sorter but the categories are emotional, not physical.

**What changes**: The color-to-mood mapping is no longer a developer decision. It's yours. Your "calm" color might be green; someone else's might be blue.

**New concept**: Subjective labeling — the training data encodes the participant's personal associations, not objective color science.

**Wow moment**: Hold up a color that relaxes you. The board plays a calm chord. Show it to a friend — their board plays something different because they associated differently.

---

### 30X: Living Mood Lamp
**Hardware**: Light + Pixels + Buzzer + Vibro + Knob + Webcam  
**300-level additions**: Webcam reads colors from physical objects placed in its frame using HSV segmentation — extracts the dominant hue of whatever object is centered. Light sensor confirms ambient illumination. Two independent color sources feed the same trained model.

**What attendees build**: Participants first train their personal color-mood vocabulary (same as 20X). Then they build a "palette" — an arrangement of colored cards, objects, or fabrics in front of the webcam. As they rearrange objects in the frame, the board classifies each dominant color in real time and drives a continuous sonic and visual output. Multiple participants can bring their own colored objects and "play" the board like a physical instrument.

**ML concept**: Two-channel color classification — webcam dominant hue + light sensor chromaticity — both feeding the same k-NN model. Features are HSV from the webcam and normalized RGB from the sensor; k-NN operates on the concatenated vector.

**Attendee contribution**: Participants choose their physical objects, train their own mood vocabulary, and design the arrangement of their palette. The workshop output is a live performance of their own color language.

**Wow moment**: Swap a red card for a blue one mid-performance. The chord changes. The LEDs shift. The board is playing what you placed in front of it.

---

## Summary Table

| Track | 100 | 200 | 300 |
|---|---|---|---|
| **A: Dial** | 101 Haptic Dial ✓ | 201 Gesture Dial ✓ | 30X Gesture OS |
| **B: Proximity** | 102 Proximity Lamp ✓ | 20X Approach Trainer | 30X Object-Aware Sentinel |
| **C: Sound** | 103 Theremin Synth ✓ | 20X Theremin Stylist | 30X Duo Theremin |
| **D: Motion** | 104 Shake Dice | 20X Shake Spellcaster | 30X Full-Body Controller |
| **E: Fitness** | 105 Step Counter | 20X Activity Classifier | 30X Personal Rep Counter |
| **F: Sensing** | 106 Hot/Cold Hunt | 20X Intruder Detector | 30X Multi-Modal Sentinel |
| **G: Language** | 107 Morse Tapper | 20X Tap Rhythm Trainer | 30X Collaborative Cipher |
| **H: Color** | 108 Ambient Synesthesia | 20X Personal Color Moods | 30X Living Mood Lamp |

✓ = module exists in this repo.

**ML algorithm progression across 200-level**:
- 20X (A, B, C, D, E, G): Nearest-centroid on time-series — same algorithm as 201, new sensor domain each time.
- 20X (F): Unsupervised multivariate Gaussian — same as planned 204.
- 20X (H): k-NN on color features — same as planned 205.

**300-level pattern**: Every 30X adds a webcam and shifts the workshop from "follow the coding instructions" to "design your own training data." The participant's choices — what gestures to record, what moods to assign, what objects to bring — determine the system's behavior. Code contribution is minimal; creative contribution is maximal.
