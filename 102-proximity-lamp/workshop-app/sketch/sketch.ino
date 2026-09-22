#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoDistance distance;
ModulinoPixels pixels;
ModulinoVibro vibro;
ModulinoKnob knob;

int latestDistance = 2000;

int read_distance() {
  // Read fresh on each Bridge call — avoids I2C contention with the Bridge
  // scheduler that occurs when polling from loop().
  if (distance.available()) {
    latestDistance = distance.get();
  }
  return latestDistance;
}

int read_knob() {
  return knob.get();
}

void show_distance(int colorCode, int litCount, int alertActive) {
  colorCode = constrain(colorCode, 0, 3);
  litCount = constrain(litCount, 0, 7);
  alertActive = constrain(alertActive, 0, 1);

  uint8_t red = 0;
  uint8_t green = 0;
  uint8_t blue = 0;

  switch (colorCode) {
    case 0: green = 200;                      break;  // green — far
    case 1: red = 200; green = 160;           break;  // yellow — mid
    case 2: red = 220; green = 80;            break;  // orange — close
    case 3: red = 220;                        break;  // red — very close
  }

  pixels.clear();
  for (int i = 0; i < litCount; i++) {
    pixels.set(i, red, green, blue, 25);
  }

  // Pixel 7 blinks white when inside the alert zone.
  if (alertActive) {
    pixels.set(7, 220, 220, 220, 25);
  }

  pixels.show();
}

void pulse_alert(int strength) {
  strength = constrain(strength, 0, 1);
  // strength 0 = short entry pulse, 1 = long re-entry pulse
  vibro.on(strength == 0 ? 120 : 280);
}

void setup() {
  Modulino.begin();
  distance.begin();
  pixels.begin();
  vibro.begin();
  knob.begin();

  knob.set(50);

  // Startup pulse confirms Vibro is connected before Bridge starts.
  vibro.on(200);
  show_distance(0, 0, 0);

  Bridge.begin();
  Bridge.provide("read_distance", read_distance);
  Bridge.provide("read_knob", read_knob);
  Bridge.provide_safe("show_distance", show_distance);
  Bridge.provide_safe("pulse_alert", pulse_alert);
}

void loop() {
}
