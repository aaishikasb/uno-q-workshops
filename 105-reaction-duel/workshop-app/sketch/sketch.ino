#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoButtons buttons;
ModulinoPixels pixels;
ModulinoVibro vibro;

// Flip if Player 1's half lights at the Button C end of your chain.
const bool PLAYER_ONE_ON_PIXEL_ZERO = true;
const uint32_t SAMPLE_MS = 5;
const uint32_t DEBOUNCE_MS = 20;
const uint32_t TIMEOUT_MS = 2000;
const int BUTTON_COUNT = 3;
const int EVENT_CAPACITY = 32;
struct Edge { int button; int pressed; uint32_t at; };
Edge events[EVENT_CAPACITY];
int eventCount = 0;
bool overflowed = false;
bool pressed[BUTTON_COUNT] = {false, false, false};
bool rawPressed[BUTTON_COUNT] = {false, false, false};
uint32_t rawChangedAt[BUTTON_COUNT] = {0, 0, 0};
uint32_t lastSampleAt = 0;
int duelState = 0;  // 0 idle, 1 waiting, 2 cue active, 3 finished.
int duelCue = 0;
int duelResult = -2;
int reactionMs = 0;
uint32_t armedAt = 0;
uint32_t cueAt = 0;
uint32_t waitMs = 0;

const uint8_t COLORS[][3] = {
  {0, 0, 0}, {220, 220, 220}, {230, 150, 0}, {40, 200, 80},
  {0, 120, 220}, {220, 0, 0}, {120, 70, 220}
};

void paint(int index, int color) {
  int pixel = PLAYER_ONE_ON_PIXEL_ZERO ? index : 7 - index;
  pixels.set(pixel, COLORS[color][0], COLORS[color][1], COLORS[color][2], 25);
}

uint32_t show(int color, int count) {
  color = constrain(color, 0, 6);
  count = constrain(count, 0, 8);
  pixels.clear();
  for (int i = 0; i < count; i++) paint(i, color);
  pixels.show();
  return millis();
}

uint32_t show_side(int side, int color) {
  side = constrain(side, 0, 1);
  color = constrain(color, 0, 6);
  pixels.clear();
  for (int i = 0; i < 4; i++) paint(side * 4 + i, color);
  pixels.show();
  return millis();
}

uint32_t show_score(int playerOne, int playerTwo) {
  playerOne = constrain(playerOne, 0, 4);
  playerTwo = constrain(playerTwo, 0, 4);
  pixels.clear();
  for (int i = 0; i < playerOne; i++) paint(i, 3);
  for (int i = 0; i < playerTwo; i++) paint(7 - i, 4);
  pixels.show();
  return millis();
}

void pulse(int duration) {
  vibro.on(constrain(duration, 20, 600));
}

bool anyHeld() {
  for (int i = 0; i < BUTTON_COUNT; i++) {
    if (pressed[i] || rawPressed[i]) return true;
  }
  return false;
}

int arm_duel(int cue, int delayMs) {
  if (anyHeld() || cue < 0 || cue > 2 || delayMs < 3000 || delayMs > 5000) return 0;
  duelCue = cue;
  waitMs = delayMs;
  show(2, 1);
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
  result += uint32_t(lastSampleAt - DEBOUNCE_MS);
  result += ",";
  int mask = 0;
  for (int i = 0; i < BUTTON_COUNT; i++) {
    if (pressed[i]) mask |= 1 << i;
  }
  result += mask;
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

void setup() {
  Modulino.begin();
  buttons.begin();
  pixels.begin();
  vibro.begin();
  buttons.update();
  for (int i = 0; i < BUTTON_COUNT; i++) {
    pressed[i] = rawPressed[i] = buttons.isPressed(i);
  }
  lastSampleAt = millis();
  for (int i = 0; i < BUTTON_COUNT; i++) rawChangedAt[i] = lastSampleAt;
  show(4, 8);
  pulse(120);
  Bridge.begin();
  Bridge.provide_safe("poll_input", poll_input);
  Bridge.provide_safe("show", show);
  Bridge.provide_safe("show_side", show_side);
  Bridge.provide_safe("show_score", show_score);
  Bridge.provide_safe("pulse", pulse);
  Bridge.provide_safe("arm_duel", arm_duel);
  Bridge.provide_safe("read_duel", read_duel);
  Bridge.provide_safe("read_reaction_ms", read_reaction_ms);
  Bridge.provide_safe("cancel_duel", cancel_duel);
}

void loop() {
  uint32_t now = millis();
  if (uint32_t(now - lastSampleAt) < SAMPLE_MS) return;
  lastSampleAt = now;
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
    if (duelCue != 0) show(1, 8);
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
