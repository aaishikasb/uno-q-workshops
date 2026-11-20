#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

// Workshop Launcher: one sketch that serves 105 Reaction Duel, 201 Gesture Dial, and 301 AI Maze.
// The LED matrix shows the menu (1, 2, 3). Holding the knob for 13 s inside any app returns to the
// menu; the last 8 s are a countdown on the Pixels, one Pixel per second.

// The Arduino_LED_Matrix class stops the sketch loading on the UNO Q (the MCU blinks red) when
// ArduinoGraphics is in the build, so the sketch calls the core's matrix functions directly.
extern "C" {
void matrixBegin(void);
void matrixGrayscaleWrite(const uint8_t* buf);
}

ModulinoMovement movement;
ModulinoKnob knob;
ModulinoButtons buttons;
ModulinoPixels pixels;
ModulinoVibro vibro;

bool hasMovement = false;
bool hasKnob = false;
bool hasButtons = false;

// ---------------------------------------------------------------- Launcher state

const int APP_MENU = 0;
const int APP_DUEL = 1;
const int APP_GESTURE = 2;
const int APP_MAZE = 3;
int activeApp = APP_MENU;
int menuChoice = 1;

// Hold-to-exit timing, measured on the MCU so it stays exact even if Linux is busy.
const uint32_t COUNTDOWN_START_MS = 5000;
const uint32_t EXIT_HOLD_MS = 13000;
const int COUNTDOWN_PIXELS = 8;  // One Pixel per second from 5 s to 13 s.
int countdown = 0;               // 0 = no countdown, otherwise Pixels still lit.
bool holdUsed = false;           // The current press already exited (or started before the app).
volatile int exitRequested = 0;

// ---------------------------------------------------------------- Pixels

// Apps draw into this cache. The countdown is drawn over it without losing it, so letting go of
// the knob early puts the app's Pixels straight back.
const uint8_t PIXEL_BRIGHTNESS = 25;
uint8_t pixelCache[8][3];

void cachePixel(int index, uint8_t red, uint8_t green, uint8_t blue) {
  if (index < 0 || index >= 8) return;
  pixelCache[index][0] = red;
  pixelCache[index][1] = green;
  pixelCache[index][2] = blue;
}

void clearPixelCache() {
  memset(pixelCache, 0, sizeof(pixelCache));
}

void flushPixels() {
  pixels.clear();
  for (int i = 0; i < 8; i++) {
    if (countdown > 0) {
      if (i < countdown) pixels.set(i, 220, 0, 0, PIXEL_BRIGHTNESS);
    } else if (pixelCache[i][0] || pixelCache[i][1] || pixelCache[i][2]) {
      pixels.set(i, pixelCache[i][0], pixelCache[i][1], pixelCache[i][2], PIXEL_BRIGHTNESS);
    }
  }
  pixels.show();
}

void pulse(int duration) {
  vibro.on(constrain(duration, 20, 600));
}

// ---------------------------------------------------------------- Knob (shared by every app)

// Track the knob by the change between reads, never by writing to it (knob.set() can invert the value
// on some firmware). One read gives both position and press. The position is unbounded; each app
// turns the change into what it needs (menu choice, gesture samples, maze speed).
const uint32_t KNOB_SAMPLE_MS = 20;
const int KNOB_MAX_STEP = 40;
volatile int knobPosition = 0;
volatile int knobPressed = 0;
int16_t knobRaw = 0;
bool knobSynced = false;
int knobDir = 0;
uint32_t knobPressedAt = 0;
uint32_t lastKnobAt = 0;

void sampleKnob(uint32_t now) {
  uint8_t buf[3];
  if (!knob.read(buf, 3) || buf[2] == 0xFF) return;  // Failed or short read.
  int pressedNow = buf[2] ? 1 : 0;
  if (pressedNow && !knobPressed) knobPressedAt = now;
  if (!pressedNow) holdUsed = false;
  knobPressed = pressedNow;
  int16_t raw = (int16_t)(buf[0] | (buf[1] << 8));
  if (!knobSynced) {
    knobRaw = raw;
    knobSynced = true;
    return;
  }
  int16_t delta = (int16_t)(raw - knobRaw);
  knobRaw = raw;
  if (delta == 0) {
    knobDir = 0;
    return;
  }
  int dir = delta > 0 ? 1 : -1;
  // A fast turn can make the encoder miscount backwards, so a change of direction
  // only counts after the knob has stopped for one read.
  if (abs(delta) > KNOB_MAX_STEP || dir == -knobDir) return;
  knobDir = dir;
  knobPosition = knobPosition + delta;
}

void updateExitHold(uint32_t now) {
  int left = 0;
  if (activeApp != APP_MENU && knobPressed && !holdUsed) {
    uint32_t held = uint32_t(now - knobPressedAt);
    if (held >= EXIT_HOLD_MS) {
      holdUsed = true;
      exitRequested = 1;
      pulse(400);
    } else if (held >= COUNTDOWN_START_MS) {
      left = COUNTDOWN_PIXELS - int((held - COUNTDOWN_START_MS) / 1000);
    }
  }
  if (left != countdown) {
    if (left > 0) pulse(40);  // A tick for every Pixel that goes out.
    countdown = left;
    flushPixels();
  }
}

int read_knob() {
  return knobPosition;
}

int read_knob_pressed() {
  return knobPressed;
}

// Returns 1 once after a 13 s hold, then clears.
int take_exit() {
  int value = exitRequested;
  exitRequested = 0;
  return value;
}

// ---------------------------------------------------------------- Buttons (105 debounced events)

const uint32_t BUTTON_SAMPLE_MS = 5;
const uint32_t DEBOUNCE_MS = 20;
const int BUTTON_COUNT = 3;
const int EVENT_CAPACITY = 32;
struct Edge { int button; int pressed; uint32_t at; };
Edge events[EVENT_CAPACITY];
int eventCount = 0;
bool overflowed = false;
bool pressed[BUTTON_COUNT] = {false, false, false};
bool rawPressed[BUTTON_COUNT] = {false, false, false};
uint32_t rawChangedAt[BUTTON_COUNT] = {0, 0, 0};
uint32_t lastButtonAt = 0;

int read_buttons() {
  int mask = 0;
  for (int i = 0; i < BUTTON_COUNT; i++) {
    if (pressed[i]) mask |= 1 << i;
  }
  return mask;
}

// ---------------------------------------------------------------- 105 Reaction Duel

// Flip if Player 1's half lights at the Button C end of your chain.
const bool PLAYER_ONE_ON_PIXEL_ZERO = true;
const uint32_t TIMEOUT_MS = 2000;
int duelState = 0;  // 0 idle, 1 waiting, 2 cue active, 3 finished.
int duelCue = 0;
int duelResult = -2;
int reactionMs = 0;
uint32_t armedAt = 0;
uint32_t cueAt = 0;
uint32_t waitMs = 0;

const uint8_t DUEL_COLORS[][3] = {
  {0, 0, 0}, {220, 220, 220}, {230, 150, 0}, {40, 200, 80},
  {0, 120, 220}, {220, 0, 0}, {120, 70, 220}
};

void duelPaint(int index, int color) {
  int pixel = PLAYER_ONE_ON_PIXEL_ZERO ? index : 7 - index;
  cachePixel(pixel, DUEL_COLORS[color][0], DUEL_COLORS[color][1], DUEL_COLORS[color][2]);
}

uint32_t duel_show(int color, int count) {
  color = constrain(color, 0, 6);
  count = constrain(count, 0, 8);
  clearPixelCache();
  for (int i = 0; i < count; i++) duelPaint(i, color);
  flushPixels();
  return millis();
}

uint32_t duel_show_side(int side, int color) {
  side = constrain(side, 0, 1);
  color = constrain(color, 0, 6);
  clearPixelCache();
  for (int i = 0; i < 4; i++) duelPaint(side * 4 + i, color);
  flushPixels();
  return millis();
}

uint32_t duel_show_score(int playerOne, int playerTwo) {
  playerOne = constrain(playerOne, 0, 4);
  playerTwo = constrain(playerTwo, 0, 4);
  clearPixelCache();
  for (int i = 0; i < playerOne; i++) duelPaint(i, 3);
  for (int i = 0; i < playerTwo; i++) duelPaint(7 - i, 4);
  flushPixels();
  return millis();
}

bool anyButtonHeld() {
  for (int i = 0; i < BUTTON_COUNT; i++) {
    if (pressed[i] || rawPressed[i]) return true;
  }
  return false;
}

int arm_duel(int cue, int delayMs) {
  if (anyButtonHeld() || cue < 0 || cue > 2 || delayMs < 3000 || delayMs > 5000) return 0;
  duelCue = cue;
  waitMs = delayMs;
  duel_show(2, 1);
  armedAt = millis();
  duelResult = -2;
  reactionMs = 0;
  duelState = 1;
  return 1;
}

int read_duel() {
  return duelResult;
}

int read_reaction_ms() {
  return reactionMs;
}

void cancel_duel() {
  duelState = 0;
  duelResult = -2;
  reactionMs = 0;
}

int playerCode(int button) {
  return button == 0 ? 1 : 2;
}

void finishDuel(int button, uint32_t at) {
  // A press that began before the cue but finished debouncing after it is still a false start.
  if (duelState == 1 || int32_t(at - cueAt) < 0) {
    duelResult = 10 + playerCode(button);
    reactionMs = 0;
  } else {
    uint32_t reaction = uint32_t(at - cueAt);
    duelResult = reaction <= TIMEOUT_MS ? playerCode(button) : 0;
    reactionMs = reaction <= TIMEOUT_MS ? int(reaction) : 0;
  }
  duelState = 3;
}

String poll_input() {
  String result = "[";
  // Consumer deadlines must wait for transitions still being debounced.
  result += uint32_t(lastButtonAt - DEBOUNCE_MS);
  result += ",";
  result += read_buttons();
  result += ",";
  result += overflowed ? 1 : 0;
  result += ",[";
  for (int i = 0; i < eventCount; i++) {
    if (i) result += ",";
    result += "[";
    result += events[i].button;
    result += ",";
    result += events[i].pressed;
    result += ",";
    result += events[i].at;
    result += "]";
  }
  result += "]]";
  eventCount = 0;
  overflowed = false;
  return result;
}

void sampleButtons(uint32_t now) {
  buttons.update();
  int first = -1;
  for (int i = 0; i < BUTTON_COUNT; i++) {
    bool reading = buttons.isPressed(i);
    if (reading != rawPressed[i]) {
      rawPressed[i] = reading;
      rawChangedAt[i] = now;
    }
    if (rawPressed[i] != pressed[i] && uint32_t(now - rawChangedAt[i]) >= DEBOUNCE_MS) {
      pressed[i] = rawPressed[i];
      if (eventCount < EVENT_CAPACITY) {
        events[eventCount++] = {i, pressed[i] ? 1 : 0, rawChangedAt[i]};
      } else {
        overflowed = true;
      }
      // Both players can settle in the same sample; the earlier transition wins, not the lower index.
      if (pressed[i] && i != 1 && (duelState == 1 || duelState == 2)
          && (first < 0 || int32_t(rawChangedAt[i] - rawChangedAt[first]) < 0)) {
        first = i;
      }
    }
  }
  if (first >= 0) {
    finishDuel(first, rawChangedAt[first]);
    return;
  }
  if (duelState == 1 && uint32_t(now - armedAt) >= waitMs) {
    for (int i = 0; i < BUTTON_COUNT; i += 2) {
      if (rawPressed[i] || pressed[i]) {
        duelResult = 10 + playerCode(i);
        reactionMs = 0;
        duelState = 3;
        return;
      }
    }
    if (duelCue != 0) duel_show(1, 8);
    if (duelCue != 1) pulse(150);
    cueAt = millis();
    duelState = 2;
    return;
  }
  // Allow a press that began at the deadline to finish debouncing.
  if (duelState == 2 && uint32_t(now - cueAt) > TIMEOUT_MS + DEBOUNCE_MS) {
    duelResult = 0;
    reactionMs = 0;
    duelState = 3;
  }
}

// ---------------------------------------------------------------- 201 Gesture Dial

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

void fill_pixels(uint8_t red, uint8_t green, uint8_t blue, int litPixels) {
  litPixels = constrain(litPixels, 0, 8);
  clearPixelCache();
  for (int i = 0; i < litPixels; i++) cachePixel(i, red, green, blue);
  flushPixels();
}

void show_mode(int mode, int progress) {
  progress = constrain(progress, 0, 8);
  switch (mode) {
    case MODE_LIVE:           fill_pixels(0, 120, 220, progress); break;
    case MODE_TRAIN_LEFT:     fill_pixels(220, 40, 120, progress); break;
    case MODE_TRAIN_RIGHT:    fill_pixels(40, 200, 80, progress); break;
    case MODE_TRAIN_WIGGLE:   fill_pixels(120, 70, 220, progress); break;
    case MODE_RECORDING:      fill_pixels(220, 220, 220, 8); break;
    case MODE_TRAINING_MODEL: fill_pixels(120, 70, 220, 8); break;
    case MODE_UNCERTAIN:      fill_pixels(230, 150, 0, progress); break;
    default:                  fill_pixels(220, 0, 0, 8); break;
  }
}

void show_prediction(int gesture, int confidence) {
  confidence = constrain(confidence, 0, 100);
  int litPixels = max(1, (confidence * 8 + 99) / 100);
  switch (gesture) {
    case GESTURE_LEFT:   fill_pixels(220, 40, 120, litPixels); break;
    case GESTURE_RIGHT:  fill_pixels(40, 200, 80, litPixels); break;
    case GESTURE_WIGGLE: fill_pixels(120, 70, 220, litPixels); break;
    default:             fill_pixels(230, 150, 0, litPixels); break;
  }
  vibro.on(map(confidence, 0, 100, 100, 320));
}

void pulse_feedback(int kind) {
  switch (kind) {
    case 0:  vibro.on(180); break;  // Ready.
    case 1:  vibro.on(120); break;  // Training example accepted.
    case 2:  vibro.on(400); break;  // Training finished.
    default: vibro.on(80); break;   // Retry or error.
  }
}

// ---------------------------------------------------------------- 301 AI Maze

const int ROWS = 8;
const int COLS = 13;
const int CELLS = ROWS * COLS;
const int MAX_TRAPS = 4;
const int TILT_LIMIT_MG = 2000;
const int TILT_OFFSET = 2048;
const uint32_t TILT_SAMPLE_MS = 5;

uint16_t walls[ROWS] = {0};
int goal = -1;
int traps[MAX_TRAPS] = {-1, -1, -1, -1};
int ball = -1;
uint32_t lastTiltAt = 0;
volatile int tiltPacked = TILT_OFFSET * 4096 + TILT_OFFSET;

void clearMaze() {
  for (int i = 0; i < ROWS; i++) walls[i] = 0;
  goal = -1;
  for (int i = 0; i < MAX_TRAPS; i++) traps[i] = -1;
  ball = -1;
}

// X and Y are packed into one int so both come from the same sample in a single Bridge call.
void sampleTilt() {
  if (!hasMovement || movement.update() != 1) return;
  int x = constrain(int(movement.getX() * 1000), -TILT_LIMIT_MG, TILT_LIMIT_MG);
  int y = constrain(int(movement.getY() * 1000), -TILT_LIMIT_MG, TILT_LIMIT_MG);
  tiltPacked = (x + TILT_OFFSET) * 4096 + (y + TILT_OFFSET);
}

int read_tilt() {
  return tiltPacked;
}

void set_row(int row, int mask) {
  if (row < 0 || row >= ROWS) return;
  walls[row] = constrain(mask, 0, (1 << COLS) - 1);
}

void set_goal(int index) {
  goal = constrain(index, -1, CELLS - 1);
}

void set_trap(int slot, int index) {
  if (slot < 0 || slot >= MAX_TRAPS) return;
  traps[slot] = constrain(index, -1, CELLS - 1);
}

void set_ball(int index) {
  ball = constrain(index, -1, CELLS - 1);
}

void maze_show(int color, int count) {
  const uint8_t colors[][3] = {
    {0, 120, 220}, {220, 40, 120}, {40, 200, 80}, {120, 70, 220},
    {220, 220, 220}, {230, 150, 0}, {220, 0, 0}, {0, 0, 0}
  };
  color = constrain(color, 0, 7);
  count = constrain(count, 0, 8);
  clearPixelCache();
  for (int i = 0; i < count; i++) cachePixel(i, colors[color][0], colors[color][1], colors[color][2]);
  flushPixels();
}

// ---------------------------------------------------------------- LED matrix

const uint32_t RENDER_MS = 50;
// The matrix draws 3-bit grayscale, so 7 is full brightness.
const uint8_t LIT = 7;
const uint8_t DIM = 1;
uint8_t frame[CELLS];
uint32_t lastRenderAt = 0;

// 5x7 digits, one byte per row, bit 4 is the leftmost column.
const uint8_t DIGITS[3][7] = {
  {0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110},  // 1
  {0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111},  // 2
  {0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110},  // 3
};
const int DIGIT_LEFT = 4;  // Centred on the 13 columns.

void drawDigit(int digit, uint8_t level) {
  for (int row = 0; row < 7; row++) {
    for (int col = 0; col < 5; col++) {
      if ((DIGITS[digit - 1][row] >> (4 - col)) & 1) frame[row * COLS + DIGIT_LEFT + col] = level;
    }
  }
}

void render(uint32_t now) {
  memset(frame, 0, sizeof(frame));
  if (activeApp == APP_MAZE) {
    bool goalOn = (now / 500) % 2 == 0;
    bool trapOn = (now / 150) % 2 == 0;
    for (int i = 0; i < CELLS; i++) {
      frame[i] = ((walls[i / COLS] >> (i % COLS)) & 1) ? LIT : 0;
    }
    if (goal >= 0) frame[goal] = goalOn ? LIT : 0;
    for (int i = 0; i < MAX_TRAPS; i++) {
      if (traps[i] >= 0) frame[traps[i]] = trapOn ? LIT : 0;
    }
    if (ball >= 0) frame[ball] = LIT;
  } else if (activeApp == APP_MENU) {
    // Big digit for the selected app, and three dots underneath showing where it sits in the list.
    drawDigit(menuChoice, LIT);
    for (int i = 0; i < 3; i++) frame[7 * COLS + DIGIT_LEFT + 2 * i] = (i == menuChoice - 1) ? LIT : DIM;
  } else {
    // Apps 1 and 2 do not use the matrix: keep their number on it, dimmed.
    drawDigit(activeApp, 2);
  }
  matrixGrayscaleWrite(frame);
}

// ---------------------------------------------------------------- Launcher Bridge calls

const uint8_t MENU_COLORS[3][3] = {{40, 200, 80}, {120, 70, 220}, {0, 120, 220}};

void show_menu(int choice) {
  menuChoice = constrain(choice, 1, 3);
  clearPixelCache();
  for (int i = 0; i < 8; i++) {
    cachePixel(i, MENU_COLORS[menuChoice - 1][0], MENU_COLORS[menuChoice - 1][1], MENU_COLORS[menuChoice - 1][2]);
  }
  flushPixels();
}

// 0 = menu, 1 = Reaction Duel, 2 = Gesture Dial, 3 = AI Maze. Every switch starts from a clean slate.
void set_app(int app) {
  activeApp = constrain(app, APP_MENU, APP_MAZE);
  cancel_duel();
  clearMaze();
  eventCount = 0;
  overflowed = false;
  exitRequested = 0;
  countdown = 0;
  holdUsed = knobPressed;  // A press that began before the switch never counts as an exit hold.
  clearPixelCache();
  flushPixels();
}

// ---------------------------------------------------------------- setup / loop

void report(const char* name, bool found) {
  Serial.print("Workshop Launcher: ");
  Serial.print(name);
  Serial.println(found ? " found" : " MISSING");
}

void setup() {
  Serial.begin(115200);
  // Register the Bridge methods before starting the Modulinos so Linux can connect early.
  // read_* handlers only return values cached by loop(), which owns the I2C bus.
  Bridge.begin();
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_knob_pressed", read_knob_pressed);
  Bridge.provide("read_buttons", read_buttons);
  Bridge.provide("read_tilt", read_tilt);
  Bridge.provide_safe("take_exit", take_exit);
  Bridge.provide_safe("set_app", set_app);
  Bridge.provide_safe("show_menu", show_menu);
  Bridge.provide_safe("pulse", pulse);
  // 105 Reaction Duel
  Bridge.provide_safe("poll_input", poll_input);
  Bridge.provide_safe("duel_show", duel_show);
  Bridge.provide_safe("duel_show_side", duel_show_side);
  Bridge.provide_safe("duel_show_score", duel_show_score);
  Bridge.provide_safe("arm_duel", arm_duel);
  Bridge.provide_safe("read_duel", read_duel);
  Bridge.provide_safe("read_reaction_ms", read_reaction_ms);
  Bridge.provide_safe("cancel_duel", cancel_duel);
  // 201 Gesture Dial
  Bridge.provide_safe("show_mode", show_mode);
  Bridge.provide_safe("show_prediction", show_prediction);
  Bridge.provide_safe("pulse_feedback", pulse_feedback);
  // 301 AI Maze
  Bridge.provide_safe("set_row", set_row);
  Bridge.provide_safe("set_goal", set_goal);
  Bridge.provide_safe("set_trap", set_trap);
  Bridge.provide_safe("set_ball", set_ball);
  Bridge.provide_safe("maze_show", maze_show);

  Modulino.begin();
  hasMovement = movement.begin();
  hasKnob = knob.begin();
  hasButtons = buttons.begin();
  report("Movement", hasMovement);
  report("Knob", hasKnob);
  report("Buttons", hasButtons);
  report("Pixels", pixels.begin());
  report("Vibro", vibro.begin());

  if (hasButtons) {
    buttons.update();
    for (int i = 0; i < BUTTON_COUNT; i++) pressed[i] = rawPressed[i] = buttons.isPressed(i);
  }
  uint32_t now = millis();
  lastButtonAt = lastKnobAt = lastTiltAt = now;
  for (int i = 0; i < BUTTON_COUNT; i++) rawChangedAt[i] = now;

  matrixBegin();
  show_menu(menuChoice);
  pulse(120);
}

// All Modulino reads happen here, never inside a Bridge handler.
void loop() {
  uint32_t now = millis();
  if (hasButtons && uint32_t(now - lastButtonAt) >= BUTTON_SAMPLE_MS) {
    lastButtonAt = now;
    sampleButtons(now);
  }
  if (hasKnob && uint32_t(now - lastKnobAt) >= KNOB_SAMPLE_MS) {
    lastKnobAt = now;
    sampleKnob(now);
    updateExitHold(now);
  }
  if (activeApp == APP_MAZE && uint32_t(now - lastTiltAt) >= TILT_SAMPLE_MS) {
    lastTiltAt = now;
    sampleTilt();
  }
  if (uint32_t(now - lastRenderAt) >= RENDER_MS) {
    lastRenderAt = now;
    render(now);
  }
}
