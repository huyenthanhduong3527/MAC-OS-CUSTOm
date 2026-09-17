"""
Timer and Stopwatch module for Dynamic Island.
Provides countdown timer, Pomodoro presets, stopwatch, and alert callbacks.
"""

import time
from gi.repository import GLib

class IslandTimer:
    def __init__(self, on_finish=None, on_tick=None):
        self.on_finish = on_finish
        self.on_tick = on_tick

        self.mode = "timer" # "timer" or "stopwatch"
        self.is_running = False

        # Timer countdown
        self.target_seconds = 300 # Default 5 mins
        self.remaining_seconds = 300
        self._last_tick = 0.0

        # Stopwatch
        self.elapsed_seconds = 0.0

        self._source_id = None

    def start_timer(self, seconds=None):
        if seconds is not None:
            self.target_seconds = int(seconds)
            self.remaining_seconds = int(seconds)

        self.mode = "timer"
        self.is_running = True
        self._last_tick = time.time()
        self._schedule_tick()

    def start_stopwatch(self):
        self.mode = "stopwatch"
        self.is_running = True
        self._last_tick = time.time()
        self._schedule_tick()

    def pause(self):
        self.is_running = False
        if self._source_id:
            GLib.source_remove(self._source_id)
            self._source_id = None

    def resume(self):
        if not self.is_running:
            self.is_running = True
            self._last_tick = time.time()
            self._schedule_tick()

    def reset(self):
        self.pause()
        if self.mode == "timer":
            self.remaining_seconds = self.target_seconds
        else:
            self.elapsed_seconds = 0.0
        if self.on_tick:
            self.on_tick()

    def _schedule_tick(self):
        if self._source_id:
            GLib.source_remove(self._source_id)
        self._source_id = GLib.timeout_add(100, self._tick)

    def _tick(self):
        if not self.is_running:
            return False

        now = time.time()
        dt = now - self._last_tick
        self._last_tick = now

        if self.mode == "timer":
            self.remaining_seconds = max(0.0, self.remaining_seconds - dt)
            if self.on_tick:
                self.on_tick()

            if self.remaining_seconds <= 0.0:
                self.is_running = False
                self._source_id = None
                if self.on_finish:
                    self.on_finish()
                return False
        else:
            self.elapsed_seconds += dt
            if self.on_tick:
                self.on_tick()

        return True

    def get_display_text(self):
        """Returns formatted string MM:SS or MM:SS.d"""
        if self.mode == "timer":
            secs = int(math_ceil(self.remaining_seconds))
            mins = secs // 60
            secs = secs % 60
            return f"{mins:02d}:{secs:02d}"
        else:
            mins = int(self.elapsed_seconds) // 60
            secs = int(self.elapsed_seconds) % 60
            tenth = int((self.elapsed_seconds * 10) % 10)
            return f"{mins:02d}:{secs:02d}.{tenth}"

def math_ceil(v):
    return int(v) + (1 if v > int(v) else 0)
