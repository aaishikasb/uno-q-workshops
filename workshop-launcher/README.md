# QC UNO Q Workshop Launcher

One App Lab app that contains all three workshops. Pick one with the Modulino Knob:

| Matrix shows | App |
| --- | --- |
| **1** | [`105: Reaction Duel`](../105-reaction-duel/) |
| **2** | [`201: Gesture Dial`](../201-gesture-dial/) |
| **3** | [`301: AI Maze`](../301-ai-maze/) |

## Hardware

Use the 301 wiring, which includes every Modulino the three apps need:

```text
UNO Q Qwiic -> Modulino Movement -> Modulino Knob -> Modulino Buttons -> Modulino Pixels -> Modulino Vibro
```

## Using the launcher

1. Import `workshop-app.zip` in App Lab, open UNO Q Workshop Launcher, and click `Run`.
2. The LED matrix shows a large 1, 2, or 3, with three dots underneath showing where you are in the list. The Pixels show the app's color: green for 1, purple for 2, blue for 3.
3. Turn the knob to change the selection.
4. Tap the knob (press and release in under a second) to start the selected app.

While app 1 or 2 is running, its number stays dimly lit on the matrix. App 3 uses the matrix for the maze.

### Going back to the menu

Hold the knob for 13 seconds.

- For the first 5 seconds nothing changes.
- Then all 8 Pixels turn red and one goes out each second, with a small buzz, for 8 seconds.
- When the last Pixel goes out, the Vibro buzzes longer and the menu comes back.
- If you let go during the countdown, nothing happens and the app's own Pixels come back.

The MCU times the hold, so the countdown stays accurate even while the Linux side is busy, for example while the AI Maze picks a new exit.

## What changed in each app

All three apps work as described in their own READMEs, with these differences:

| App | Change | Why |
| --- | --- | --- |
| 201 Gesture Dial | To retrain, hold the knob for 3 s, wait for the buzz, then let go before 5 s. Before, retraining started on its own at 3 s. | Otherwise a 13-second exit hold would erase the model. |
| 301 AI Maze | Tap the knob to move the exit. Before, the exit moved as soon as the knob was pressed. | Otherwise every exit hold would also move the exit. |
| 301 AI Maze | The speed starts at 45 every time you launch the app, and it follows the knob from there. | The MCU no longer keeps a 0-100 knob value for the maze. |
| All | The Python state is reset each time you launch an app, the same as running it as its own app. | Each app module is reloaded on launch. |

The saved files from 105 (`data/leaderboard.json`) and 201 (`data/gesture_model.json`) persist across launches and restarts.

## Dashboard

Open `http://<board-ip>:7000`. The page follows the launcher: it shows the Reaction Duel leaderboard while app 1 runs, the 3D maze while app 3 runs, and a short note for the menu and for app 2, which has no dashboard.

## How it fits together

```text
 MCU (sketch.ino)                               Linux (python/)
 knob, buttons, tilt sampling, debounce          main.py        launcher: menu, launch, exit
 hold-to-exit timer + Pixel countdown  --exit--> app_duel.py    105 (start / loop / stop)
 matrix: menu digit or maze                      app_gesture.py 201
 Pixels cache (restored after countdown)         app_maze.py    301
 every app's Bridge calls                        button.py, duel_game.py, gesture_model.py, maze_model.py
```

- `set_app(n)` tells the MCU which app is running (0 = menu). Each switch resets the duel, maze, button events, and countdown.
- `take_exit()` returns 1 once after a 13-second hold. The launcher checks it every 100 ms, stops the app, and shows the menu.
- Calls whose names clashed between apps are renamed: 105's `show*` became `duel_show*` and 301's `show` became `maze_show`. All apps share `read_knob` and `read_knob_pressed`. `read_knob` is now an unbounded position, and each app uses only how much it changed.

## Tuning

| Setting | File | Default |
| --- | --- | --- |
| `COUNTDOWN_START_MS`, `EXIT_HOLD_MS` | `sketch/sketch.ino` | 5000, 13000 |
| `KNOB_STEPS_PER_CHOICE`: knob steps per menu move | `python/main.py` | 2 |
| `TAP_SECONDS`: longest press that still counts as a tap | `python/main.py` | 1.0 |
| `DIGIT_LEFT` / `DIGITS`: menu digit position and font | `sketch/sketch.ino` | centered 5x7 |

If the digit appears upside down or mirrored, your matrix is in a different orientation from the maze's row and column order. Change `drawDigit()` in `sketch.ino`.

## Files

- `workshop-app/app.yaml`: app name and the WebUI brick
- `workshop-app/sketch/sketch.ino`: the three sketches merged, plus the menu, hold-to-exit, and Pixel countdown
- `workshop-app/python/main.py`: launcher
- `workshop-app/python/app_duel.py`, `app_gesture.py`, `app_maze.py`: the three original `main.py` files as start/loop/stop modules
- `workshop-app/assets/index.html`: dashboard shell; `duel.html` and `maze.html` are the original dashboards with new API paths
- `workshop-app.zip`: importable App Lab project
