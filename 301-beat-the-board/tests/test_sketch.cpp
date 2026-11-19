#include <cassert>
#include "../workshop-app/sketch/sketch.ino"

void tick(uint32_t elapsed, int16_t position, bool pressed) {
  fakeMillis += elapsed;
  knob.position = position;
  knob.down = pressed;
  loop();
}

int main() {
  setup();
  assert(reset_game() == 0);
  assert(open_round(1, 0) == 1);
  tick(35, 0, false);
  tick(5, 0, true); tick(35, 0, true);
  assert(poll_event() == 0); // A press without a selection cannot submit.
  tick(5, 0, false); tick(35, 0, false);
  tick(5, -1, false); // Select left.
  tick(5, -1, true); tick(10, -1, false); tick(5, -1, true);
  assert(poll_event() == 0); // Bounce must settle first.
  tick(35, -1, true);
  assert(poll_event() == 5);
  tick(100, 12, true);
  assert(poll_event() == 5); // Event remains latched; ignored movement cannot change it.
  assert(open_round(2, 1) == -1); // Cannot discard an unacknowledged event.
  assert(show_feedback(2, 0, -1, 0, 0, 1) == -1);
  assert(poll_event() == 5);
  assert(show_feedback(1, 0, -1, 0, 0, 1) == 1);
  assert(poll_event() == 0);
  assert(show_feedback(1, 0, -1, 0, 0, 1) == -1);
  assert(open_round(2, 1) == 2);
  tick(100, 14, true);
  assert(controls.selection == 0); // Holding the previous press cannot enter the next round.
  tick(5, 14, false); tick(35, 14, false);
  tick(5, 15, false);
  assert(controls.selection == 1);
  assert(open_round(2, 1) == 2); // Repeating an open command preserves the selected side.
  assert(controls.selection == 1);
  tick(5, 15, true); tick(35, 15, true);
  assert(poll_event() == 10);
  assert(show_feedback(2, 1, 1, 0, 1, 2) == 2);
  assert(vibro.pulses == 1);
  // Result input also requires a new press after release.
  assert(show_result(2, 8, 8) == 2);
  tick(100, 15, true);
  assert(poll_event() == 0);
  tick(5, 15, false); tick(35, 15, false);
  tick(5, 15, true); tick(35, 15, true);
  assert(poll_event() == 11);
  assert(reset_game() == 0);
  assert(poll_event() == 0);
  assert(open_round(3, 0) == 3);
  tick(1600, 15, true);
  assert(poll_event() == -1); // Lost Bridge connection disables input.
  assert(!controls.active);
  assert(reset_game() == 0);
  knob.healthy = false;
  tick(5, 20, false);
  assert(poll_event() == -1); // A failed I2C read cannot invent a turn.
  knob.healthy = true;
  assert(reset_game() == 0);
  assert(open_round(4, 0) == 4);
  controls.position = 32767;
  tick(35, -32768, false);
  assert(controls.selection == 1); // Signed counter wrap still means one step right.
  tick(5, 32767, false);
  assert(controls.selection == -1);
  return 0;
}
