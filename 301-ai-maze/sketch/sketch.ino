#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

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

const int ROWS = 8;
const int COLS = 13;
const int CELLS = ROWS * COLS;
const int MAX_TRAPS = 4;
const int TILT_LIMIT_MG = 2000;
const int TILT_OFFSET = 2048;
const uint32_t RENDER_MS = 50;
const uint32_t TILT_SAMPLE_MS = 5;
const uint32_t INPUT_SAMPLE_MS = 20;
// The matrix draws 3-bit grayscale, so 7 is full brightness.
const uint8_t LIT = 7;

uint16_t walls[ROWS] = {0};
int goal = -1;
int traps[MAX_TRAPS] = {-1, -1, -1, -1};
int ball = -1;
uint8_t frame[CELLS];
bool dirty = true;
uint32_t lastRenderAt = 0;
uint32_t lastTiltAt = 0;
uint32_t lastInputAt = 0;
bool hasMovement = false;
bool hasKnob = false;
bool hasButtons = false;
// loop() owns the I2C bus and caches readings; the read_* handlers only return the cache.
volatile int tiltPacked = TILT_OFFSET * 4096 + TILT_OFFSET;
volatile int knobValue = 0;
volatile int knobPressed = 0;
volatile int buttonMask = 0;

// X and Y are packed into one int so both come from the same sample in a single Bridge call.
void sampleTilt() {
  if (!hasMovement || movement.update() != 1) return;
  int x = constrain(int(movement.getX() * 1000), -TILT_LIMIT_MG, TILT_LIMIT_MG);
  int y = constrain(int(movement.getY() * 1000), -TILT_LIMIT_MG, TILT_LIMIT_MG);
  tiltPacked = (x + TILT_OFFSET) * 4096 + (y + TILT_OFFSET);
}

void sampleInputs() {
  if (hasKnob) {
    knobValue = knob.get();
    knobPressed = knob.isPressed() ? 1 : 0;
  }
  if (hasButtons) {
    buttons.update();
    int mask = 0;
    for (int i = 0; i < 3; i++) {
      if (buttons.isPressed(i)) mask |= 1 << i;
    }
    buttonMask = mask;
  }
}

int read_tilt() {
  return tiltPacked;
}

int read_knob() {
  return knobValue;
}

int read_knob_pressed() {
  return knobPressed;
}

int read_buttons() {
  return buttonMask;
}

void set_knob(int value) {
  value = constrain(value, 0, 100);
  if (hasKnob) knob.set(value);
  knobValue = value;
}

void set_row(int row, int mask) {
  if (row < 0 || row >= ROWS) return;
  walls[row] = constrain(mask, 0, (1 << COLS) - 1);
  dirty = true;
}

void set_goal(int index) {
  goal = constrain(index, -1, CELLS - 1);
  dirty = true;
}

void set_trap(int slot, int index) {
  if (slot < 0 || slot >= MAX_TRAPS) return;
  traps[slot] = constrain(index, -1, CELLS - 1);
  dirty = true;
}

void set_ball(int index) {
  ball = constrain(index, -1, CELLS - 1);
  dirty = true;
}

void show(int color, int count) {
  const uint8_t colors[][3] = {
    {0, 120, 220}, {220, 40, 120}, {40, 200, 80}, {120, 70, 220},
    {220, 220, 220}, {230, 150, 0}, {220, 0, 0}, {0, 0, 0}
  };
  color = constrain(color, 0, 7);
  count = constrain(count, 0, 8);
  pixels.clear();
  for (int i = 0; i < count; i++) {
    pixels.set(i, colors[color][0], colors[color][1], colors[color][2], 25);
  }
  pixels.show();
}

void pulse(int duration) {
  vibro.on(constrain(duration, 20, 600));
}

// Only this function touches the LED matrix API, so it is the one place to adapt.
void render(uint32_t now) {
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
  matrixGrayscaleWrite(frame);
}

void report(const char* name, bool found) {
  Serial.print("AI Maze: ");
  Serial.print(name);
  Serial.println(found ? " found" : " MISSING");
}

void setup() {
  Serial.begin(115200);
  // Register the Bridge methods first, so Linux can reach them while the Modulinos are still starting.
  // Handlers check the has* flags, so they are safe to call before the modules are found.
  Bridge.begin();
  Bridge.provide("read_tilt", read_tilt);
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_knob_pressed", read_knob_pressed);
  Bridge.provide("read_buttons", read_buttons);
  Bridge.provide_safe("set_knob", set_knob);
  Bridge.provide_safe("set_row", set_row);
  Bridge.provide_safe("set_goal", set_goal);
  Bridge.provide_safe("set_trap", set_trap);
  Bridge.provide_safe("set_ball", set_ball);
  Bridge.provide_safe("show", show);
  Bridge.provide_safe("pulse", pulse);
  Modulino.begin();
  hasMovement = movement.begin();
  hasKnob = knob.begin();
  hasButtons = buttons.begin();
  report("Movement", hasMovement);
  report("Knob", hasKnob);
  report("Buttons", hasButtons);
  report("Pixels", pixels.begin());
  report("Vibro", vibro.begin());
  matrixBegin();
  show(0, 8);
  pulse(120);
}

// Matches the on-board modulino-check app: all Modulino reads happen here, never inside a Bridge handler.
void loop() {
  uint32_t now = millis();
  if (uint32_t(now - lastTiltAt) >= TILT_SAMPLE_MS) {
    lastTiltAt = now;
    sampleTilt();
  }
  if (uint32_t(now - lastInputAt) >= INPUT_SAMPLE_MS) {
    lastInputAt = now;
    sampleInputs();
  }
  if (dirty || uint32_t(now - lastRenderAt) >= RENDER_MS) {
    lastRenderAt = now;
    dirty = false;
    render(now);
  }
}
