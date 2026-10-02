#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoKnob knob;
ModulinoPixels pixels;
ModulinoVibro vibro;

const unsigned long SAMPLE_PERIOD_US = 20000;  // 50 Hz hardware sampling.
const int STAGE_PIXELS = 7;                    // One Pixel per lock stage.

// The knob is only ever read from loop(). Bridge handlers return these cached
// values instead of touching I2C from the Bridge thread.
volatile int latestKnob = 0;
volatile int latestPressed = 0;
volatile int heartbeat = 0;
unsigned long lastSampleAt = 0;

int read_knob() {
  return latestKnob;
}

int read_pressed() {
  return latestPressed;
}

// Increments every sample. If this does not change, loop() is not running.
int read_heartbeat() {
  return heartbeat;
}

// Stages 0..cleared-1 are green. The next stage glows amber while `blink` is 1.
void show_stage(int cleared, int blink) {
  cleared = constrain(cleared, 0, STAGE_PIXELS);
  pixels.clear();
  for (int i = 0; i < cleared; i++) {
    pixels.set(i, 40, 200, 80, 25);
  }
  if (blink && cleared < STAGE_PIXELS) {
    pixels.set(cleared, 230, 150, 0, 25);
  }
  pixels.show();
}

// Victory animation: Python advances `phase` to rotate the colors.
void show_win(int phase) {
  const uint8_t palette[7][3] = {
    {220, 0, 0}, {230, 120, 0}, {220, 220, 0}, {40, 200, 80},
    {0, 120, 220}, {120, 70, 220}, {220, 40, 120}
  };
  pixels.clear();
  for (int i = 0; i < STAGE_PIXELS; i++) {
    const uint8_t *c = palette[(i + phase) % 7];
    pixels.set(i, c[0], c[1], c[2], 25);
  }
  pixels.show();
}

void show_alert() {
  pixels.clear();
  for (int i = 0; i < STAGE_PIXELS; i++) {
    pixels.set(i, 220, 0, 0, 25);
  }
  pixels.show();
}

// Short pulse while turning; Python picks the length from how close you are.
void tick(int milliseconds) {
  vibro.on(constrain(milliseconds, 10, 200));
}

void pulse(int kind) {
  switch (kind) {
    case 0:  // Ready.
      vibro.on(180);
      break;
    case 1:  // Tumbler fell.
      vibro.on(90);
      break;
    case 2:  // Stage unlocked.
      vibro.on(140);
      delay(90);
      vibro.on(140);
      break;
    case 3:  // Safe open.
      for (int i = 0; i < 3; i++) {
        vibro.on(250);
        delay(120);
      }
      break;
    default:  // Time ran out.
      vibro.on(400);
      break;
  }
}

void setup() {
  Modulino.begin();
  knob.begin();
  pixels.begin();
  vibro.begin();

  knob.set(0);
  latestKnob = knob.get();
  latestPressed = knob.isPressed() ? 1 : 0;
  lastSampleAt = micros();
  show_stage(0, 1);
  pulse(0);

  Bridge.begin();
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_pressed", read_pressed);
  Bridge.provide("read_heartbeat", read_heartbeat);
  Bridge.provide_safe("show_stage", show_stage);
  Bridge.provide_safe("show_win", show_win);
  Bridge.provide_safe("show_alert", show_alert);
  Bridge.provide_safe("tick", tick);
  Bridge.provide_safe("pulse", pulse);
}

void loop() {
  unsigned long now = micros();
  if (now - lastSampleAt >= SAMPLE_PERIOD_US) {
    lastSampleAt = now;
    latestKnob = knob.get();
    latestPressed = knob.isPressed() ? 1 : 0;
    heartbeat = heartbeat + 1;
  }
}
