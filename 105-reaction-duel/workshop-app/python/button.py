"""Read debounced MCU events for the three Modulino Buttons without timing Bridge round trips."""

import json

from arduino.app_utils import Bridge


BUTTON_COUNT = 3


def elapsed(now, start):
    return (now - start) & 0xFFFFFFFF


def _timestamp(value):
    return type(value) is int and 0 <= value <= 0xFFFFFFFF


class Buttons:
    def __init__(self):
        self.now = 0
        self.mask = 0
        self.pressed_at = [None] * BUTTON_COUNT
        self.accepted_after = None

    def held(self, button=None):
        if button is None:
            return self.mask != 0
        return bool(self.mask >> button & 1)

    def accept_after(self, at):
        """Ignore presses that began before an MCU prompt was displayed."""
        if not _timestamp(at):
            raise ValueError("Invalid prompt timestamp; import the matching Python and sketch files")
        self.accepted_after = at

    def poll(self):
        packet = json.loads(Bridge.call("poll_input"))
        if not isinstance(packet, list) or len(packet) != 4:
            raise ValueError("Invalid button packet; restart the app")
        now, mask, overflow, edges = packet
        if (not _timestamp(now)
                or type(mask) is not int or not 0 <= mask < 1 << BUTTON_COUNT
                or type(overflow) is not int or overflow not in (0, 1)
                or not isinstance(edges, list) or len(edges) > 32):
            raise ValueError("Invalid button state; restart the app")
        for edge in edges:
            if (not isinstance(edge, list) or len(edge) != 3
                    or type(edge[0]) is not int or not 0 <= edge[0] < BUTTON_COUNT
                    or type(edge[1]) is not int or edge[1] not in (0, 1)
                    or not _timestamp(edge[2])):
                raise ValueError("Invalid button event; restart the app")
        self.now, self.mask = now, mask
        if overflow:
            self.pressed_at = [None] * BUTTON_COUNT
            raise ValueError("Button buffer overflow; release all buttons and retry")
        events = []
        for button, down, at in edges:
            if down:
                self.pressed_at[button] = at
                events.append(("press", button, at, 0))
            elif self.pressed_at[button] is not None:
                events.append(("release", button, at, elapsed(at, self.pressed_at[button])))
                self.pressed_at[button] = None
        return [event for event in events if self.accepted_after is None
                or elapsed((event[2] - event[3]) & 0xFFFFFFFF, self.accepted_after) < 0x80000000]
