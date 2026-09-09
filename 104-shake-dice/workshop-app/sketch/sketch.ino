#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoMovement movement;
ModulinoPixels pixels;
ModulinoBuzzer buzzer;
ModulinoVibro vibro;
ModulinoButtons buttons;

// Pip patterns for d6 faces — bitmask over 8 pixels.
// Pixel positions treated as a 2-row layout: [0,1,2,3] top, [4,5,6,7] bottom.
// d6 pip layouts (0-indexed pixels):
static const uint8_t PIP_MASK[6] = {
  0b00010000,  // 1: centre-left (pixel 4)
  0b10000001,  // 2: top-right + bottom-left
  0b10010001,  // 3: top-right + centre-left + bottom-left  (reuses centre pip)
  0b10100101,  // 4: four corners
  0b10110101,  // 5: four corners + centre-left
  0b11100111,  // 6: three left + three right
};

// Fanfare notes (ascending): low → high based on roll value.
static const int FANFARE_FREQS[3] = {330, 415, 523};

// d6 pip colour: warm gold. d8 pip colour: cool blue.
static const uint8_t D6_R = 220, D6_G = 160, D6_B = 0;
static const uint8_t D8_R = 0,   D8_G = 120, D8_B = 220;

int read_az() {
  // Read inside the Bridge handler — avoids I2C contention with the Bridge scheduler.
  movement.update();
  return (int)(movement.getZ() * 1000.0f);
}

int read_buttons() {
  // Returns a bitmask: bit 0 = button A, bit 1 = button B.
  // Single update() call covers both — avoids double I2C transaction.
  buttons.update();
  int state = 0;
  if (buttons.isPressed(0)) state |= 1;
  if (buttons.isPressed(1)) state |= 2;
  return state;
}

void show_face(int value, int sides) {
  value = constrain(value, 1, 8);
  sides = constrain(sides, 6, 8);

  uint8_t r = (sides == 6) ? D6_R : D8_R;
  uint8_t g = (sides == 6) ? D6_G : D8_G;
  uint8_t b = (sides == 6) ? D6_B : D8_B;

  pixels.clear();

  if (sides == 6) {
    uint8_t mask = PIP_MASK[value - 1];
    for (int i = 0; i < 8; i++) {
      if (mask & (1 << (7 - i))) {
        pixels.set(i, r, g, b, 25);
      }
    }
  } else {
    // d8: fill value pixels left-to-right as a simple bar.
    for (int i = 0; i < value; i++) {
      pixels.set(i, r, g, b, 25);
    }
  }

  pixels.show();
}

void show_rolling(int frame) {
  // Rapid random-looking flash during roll animation — frame 0–7 cycles colours.
  frame = constrain(frame, 0, 7);
  pixels.clear();
  // Light alternating pixels each frame to give a spinning effect.
  for (int i = 0; i < 8; i++) {
    if ((i + frame) % 2 == 0) {
      pixels.set(i, 220, 220, 220, 25);
    }
  }
  pixels.show();
}

void play_fanfare(int value) {
  // Three rising notes; pitch cluster scales loosely with roll value.
  value = constrain(value, 1, 8);
  int base = map(value, 1, 8, 0, 2);
  for (int i = 0; i <= base; i++) {
    buzzer.tone(FANFARE_FREQS[i], 120);
    // Blocking delay acceptable here — fanfare is a one-shot actuator call,
    // not inside the Python poll loop.
    delay(140);
  }
}

void pip_pulse() {
  vibro.on(100);
}

void setup() {
  Modulino.begin();
  movement.begin();
  pixels.begin();
  buzzer.begin();
  vibro.begin();
  buttons.begin();

  pixels.clear();
  pixels.show();

  // Startup pulse confirms hardware is connected before Bridge starts.
  vibro.on(200);

  Bridge.begin();
  Bridge.provide("read_az",      read_az);
  Bridge.provide("read_buttons", read_buttons);
  Bridge.provide_safe("show_face",    show_face);
  Bridge.provide_safe("show_rolling", show_rolling);
  Bridge.provide_safe("play_fanfare", play_fanfare);
  Bridge.provide_safe("pip_pulse",    pip_pulse);
}

void loop() {
}
