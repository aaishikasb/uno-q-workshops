#include <Arduino_Modulino.h>
#include <Arduino_RouterBridge.h>

ModulinoDistance distance;
ModulinoPixels pixels;
ModulinoBuzzer buzzer;
ModulinoKnob knob;

int latestDistance = 9999;

// Color codes for show_zone: 0=blue, 1=cyan, 2=green, 3=yellow, 4=orange, 5=red
static const uint8_t ZONE_R[] = {  0,   0,   0, 220, 220, 220};
static const uint8_t ZONE_G[] = {  0, 160, 200, 200,  80,   0};
static const uint8_t ZONE_B[] = {220, 220,   0,   0,   0,   0};

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

void play_note(int freq, int duration_ms) {
  freq = constrain(freq, 60, 2000);
  duration_ms = constrain(duration_ms, 10, 500);
  buzzer.tone(freq, duration_ms);
}

void show_zone(int color_code, int lit_count) {
  color_code = constrain(color_code, 0, 5);
  lit_count = constrain(lit_count, 0, 8);
  pixels.clear();
  for (int i = 0; i < lit_count; i++) {
    pixels.set(i, ZONE_R[color_code], ZONE_G[color_code], ZONE_B[color_code], 25);
  }
  pixels.show();
}

void setup() {
  Modulino.begin();
  distance.begin();
  pixels.begin();
  buzzer.begin();
  knob.begin();

  knob.set(0);
  show_zone(0, 0);

  Bridge.begin();
  Bridge.provide("read_distance", read_distance);
  Bridge.provide("read_knob", read_knob);
  Bridge.provide_safe("play_note", play_note);
  Bridge.provide_safe("show_zone", show_zone);
}

void loop() {
}
