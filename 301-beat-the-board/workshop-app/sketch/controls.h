#pragma once
#include <stdint.h>

// Input state stays on the MCU; Bridge handlers run safely on the loop thread.
struct Controls {
  int round = 0, selection = 0, event = 0;
  bool active = false, restart = false, armed = false;
  bool raw = true, pressed = true;
  uint32_t changedAt = 0;
  int16_t position = 0;

  void close() { active = false; armed = false; }

  void open(int id, bool forRestart = false) {
    round = id;
    selection = event = 0;
    active = true;
    restart = forRestart;
    armed = false;
  }

  void sample(uint32_t now, int16_t value, bool down) {
    int16_t delta = static_cast<int16_t>(static_cast<uint16_t>(value) - static_cast<uint16_t>(position));
    position = value;
    if (down != raw) { raw = down; changedAt = now; }
    bool rising = false;
    if (now - changedAt >= 30 && pressed != raw) {
      pressed = raw;
      rising = pressed;
    }
    if (!active) return;
    if (!raw && !pressed && now - changedAt >= 30) armed = true;
    if (!armed) return;
    if (!raw && !pressed && !restart && delta) selection = delta < 0 ? -1 : 1;
    if (rising && (restart || selection)) {
      event = round * 4 + (restart ? 3 : selection < 0 ? 1 : 2);
      close();
    }
  }
};
