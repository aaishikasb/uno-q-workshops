#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoKnob knob;
ModulinoPixels pixels;
ModulinoVibro vibro;

int read_knob() {
  return knob.get();
}

int read_pressed() {
  return knob.isPressed() ? 1 : 0;
}

void show_level(int level) {
  level = constrain(level, 0, 100);
  int litPixels = (level * 8 + 99) / 100;

  uint8_t red = 0;
  uint8_t green = 120;
  uint8_t blue = 220;

  if (level >= 67) {
    red = 220;
    green = 40;
    blue = 120;
  } else if (level >= 34) {
    red = 40;
    green = 200;
    blue = 80;
  }

  pixels.clear();
  for (int i = 0; i < litPixels; i++) {
    pixels.set(i, red, green, blue, 25);
  }
  pixels.show();
}

void pulse_vibro(int level) {
  level = constrain(level, 0, 100);
  int duration = map(level, 0, 100, 180, 400);
  vibro.on(duration);
}

void setup() {
  Modulino.begin();
  knob.begin();
  pixels.begin();
  vibro.begin();

  // A startup pulse confirms the Vibro is connected before Bridge starts.
  vibro.on(250);

  knob.set(0);
  show_level(0);

  Bridge.begin();
  Bridge.provide("read_knob", read_knob);
  Bridge.provide("read_pressed", read_pressed);
  Bridge.provide("show_level", show_level);
  Bridge.provide("pulse_vibro", pulse_vibro);
}

void loop() {
}
