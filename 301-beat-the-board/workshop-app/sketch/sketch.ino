#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>
#include "controls.h"

ModulinoKnob knob;
ModulinoPixels pixels;
ModulinoVibro vibro;
Controls controls;

bool modulesReady = false, fault = false, connected = false;
uint32_t lastRpc = 0, lastSample = 0, lastFrame = 0, feedbackAt = 0;
int screen = 0, progress = 0, prediction = 0, chosen = 0, player = 0, board = 0;
// Screens: 0 waiting, 1 selection, 2 feedback, 3 match result, 4 error.

bool readKnob(int16_t &position, bool &pressed) {
  uint8_t data[3];
  if (!knob.read(data, 3)) return false;
  position = static_cast<int16_t>(data[0] | (data[1] << 8));
  pressed = data[2] != 0;
  return true;
}

void stopGame() {
  controls.close();
  fault = true;
  screen = 4;
}

int reset_game() {
  lastRpc = millis();
  connected = true;
  int16_t position;
  bool pressed;
  if (!modulesReady || !readKnob(position, pressed)) { stopGame(); return -1; }
  controls = Controls();
  controls.position = position;
  controls.raw = controls.pressed = pressed;
  controls.changedAt = millis();
  player = board = progress = 0;
  screen = 0;
  fault = false;
  return 0;
}

int open_round(int id, int historySize) {
  lastRpc = millis();
  if (fault || !connected || id <= 0 || id > 500000000 || historySize < 0 || historySize > 8) return -1;
  if (id == controls.round && screen == 1) return id;
  if (id <= controls.round || controls.event) return -1;
  controls.open(id);
  progress = historySize;
  screen = 1;
  return id;
}

int poll_event() {
  lastRpc = millis();
  return fault ? -1 : controls.event;
}

int show_feedback(int id, int guess, int choice, int playerScore, int boardScore, int historySize) {
  lastRpc = millis();
  if (fault || id != controls.round || choice != controls.selection ||
      controls.event != id * 4 + (choice < 0 ? 1 : 2) ||
      (guess != -1 && guess != 0 && guess != 1) ||
      playerScore < 0 || boardScore < 0 || playerScore + boardScore > 16 ||
      historySize < 1 || historySize > 8) return -1;
  controls.event = 0;  // Acknowledge only after validating the committed round.
  controls.close();
  prediction = guess; chosen = choice; player = playerScore; board = boardScore;
  progress = historySize;
  screen = 2;
  feedbackAt = millis();
  if (guess && guess == choice) vibro.on(100);
  return id;
}

int show_result(int id, int playerScore, int boardScore) {
  lastRpc = millis();
  if (fault || id != controls.round || controls.event || playerScore < 0 || boardScore < 0 || playerScore + boardScore != 16) return -1;
  player = playerScore; board = boardScore;
  controls.open(id, true);
  screen = 3;
  return id;
}

int show_error() { stopGame(); return 0; }

void side(int direction, int r, int g, int b) {
  for (int i = direction < 0 ? 0 : 4; i < (direction < 0 ? 4 : 8); ++i) pixels.set(i, r, g, b, 25);
}

void score() {
  for (int i = 0; i < 4; ++i) {
    int left = constrain(player - i * 4, 0, 4);
    int right = constrain(board - i * 4, 0, 4);
    if (left) pixels.set(i, 40, 220, 100, left * 6);
    if (right) pixels.set(7 - i, 220, 50, 140, right * 6);
  }
}

void render(uint32_t now) {
  pixels.clear();
  if (screen == 4) {
    if ((now / 400) % 2 == 0) { side(-1, 255, 0, 0); side(1, 255, 0, 0); }
  } else if (screen == 1) {
    if (controls.selection) side(controls.selection, 60, 140, 255);
    else if (progress < 8) {
      for (int i = 0; i < progress; ++i) pixels.set(i, 220, 150, 20, 20);
      pixels.set(progress, 255, 255, 255, 8);
    } else { pixels.set(3, 255, 255, 255, 12); pixels.set(4, 255, 255, 255, 12); }
  } else if (screen == 2) {
    uint32_t elapsed = now - feedbackAt;
    if (!prediction) {
      for (int i = 0; i < progress; ++i) pixels.set(i, 220, 150, 20, 20);
    } else if (elapsed < 350) side(prediction, 220, 50, 140);
    else if (elapsed < 800) {
      if (prediction == chosen) {
        if (((elapsed - 350) / 112) % 2 == 0) { side(-1, 220, 50, 140); side(1, 220, 50, 140); }
      } else {
        int step = constrain(static_cast<int>((elapsed - 350) / 112), 0, 3);
        pixels.set(3 - step, 40, 220, 100, 25);
        pixels.set(4 + step, 40, 220, 100, 25);
      }
    } else score();
  } else if (screen == 3) {
    if ((now / 1000) % 2 == 0) score();
    else if (player == board) { side(-1, 255, 255, 255); side(1, 255, 255, 255); }
    else if (player > board) side(-1, 40, 220, 100);
    else side(1, 220, 50, 140);
  } else { pixels.set(3, 255, 255, 255, 5); pixels.set(4, 255, 255, 255, 5); }
  pixels.show();
}

void setup() {
  Modulino.begin();
  bool k = knob.begin(), p = pixels.begin(), v = vibro.begin();
  modulesReady = k && p && v;
  if (!modulesReady) stopGame();
  Bridge.begin();
  Bridge.provide_safe("reset_game", reset_game);
  Bridge.provide_safe("open_round", open_round);
  Bridge.provide_safe("poll_event", poll_event);
  Bridge.provide_safe("show_feedback", show_feedback);
  Bridge.provide_safe("show_result", show_result);
  Bridge.provide_safe("show_error", show_error);
}

void loop() {
  uint32_t now = millis();
  if (modulesReady && now - lastSample >= 5) {
    lastSample = now;
    int16_t position;
    bool pressed;
    if (readKnob(position, pressed)) controls.sample(now, position, pressed);
    else stopGame();
  }
  if (connected && now - lastRpc > 1500) stopGame();
  if (now - lastFrame >= 25) { lastFrame = now; render(now); }
}
