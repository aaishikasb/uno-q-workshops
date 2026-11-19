#pragma once
#include <algorithm>
#include <cstdint>
inline uint32_t fakeMillis = 0;
inline uint32_t millis() { return fakeMillis; }
template <typename T> T constrain(T value, T low, T high) { return std::max(low, std::min(high, value)); }
struct ModulinoClass { void begin() {} };
inline ModulinoClass Modulino;
struct ModulinoKnob {
  int16_t position = 0;
  bool down = false, healthy = true;
  bool begin() { return healthy; }
  bool read(uint8_t *data, int) {
    data[0] = position & 255; data[1] = (static_cast<uint16_t>(position) >> 8); data[2] = down;
    return healthy;
  }
};
struct ModulinoPixels {
  bool begin() { return true; }
  void clear() {}
  void set(int, int, int, int, int) {}
  void show() {}
};
struct ModulinoVibro {
  int pulses = 0;
  bool begin() { return true; }
  void on(unsigned long) { ++pulses; }
};
