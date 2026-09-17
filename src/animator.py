"""
High-performance physics-based spring and easing animation engine.
Provides smooth 60 FPS interpolation for Dynamic Island dimensions and transitions.
"""

import math
import time
from gi.repository import GLib

class SpringValue:
    """Simulates a physical damped spring for fluid Apple-like animations."""
    def __init__(self, value=0.0, stiffness=180.0, damping=18.0):
        self.current = float(value)
        self.target = float(value)
        self.velocity = 0.0
        self.stiffness = float(stiffness)
        self.damping = float(damping)

    def set_target(self, target):
        self.target = float(target)

    def set_immediate(self, value):
        self.current = float(value)
        self.target = float(value)
        self.velocity = 0.0

    def step(self, dt):
        """Simulate one physics step with Euler integration."""
        displacement = self.current - self.target
        spring_force = -self.stiffness * displacement
        damping_force = -self.damping * self.velocity
        total_force = spring_force + damping_force

        self.velocity += total_force * dt
        self.current += self.velocity * dt

        # Settle if close enough to target and nearly stopped
        if abs(displacement) < 0.2 and abs(self.velocity) < 0.3:
            self.current = self.target
            self.velocity = 0.0
            return True # settled
        return False


class IslandAnimator:
    """Manages 2D dimension and opacity animations for the Dynamic Island."""
    def __init__(self, initial_w=210.0, initial_h=36.0, on_update=None, on_finish=None):
        self.w = SpringValue(initial_w, stiffness=210.0, damping=20.0)
        self.h = SpringValue(initial_h, stiffness=230.0, damping=21.0)
        self.opacity = SpringValue(0.0, stiffness=190.0, damping=22.0) # 0.0 = compact, 1.0 = expanded

        self.on_update = on_update
        self.on_finish = on_finish
        self._running = False
        self._last_time = 0.0
        self._source_id = None

    def animate_to(self, target_w, target_h, target_opacity=None):
        self.w.set_target(target_w)
        self.h.set_target(target_h)
        if target_opacity is not None:
            self.opacity.set_target(target_opacity)

        if not self._running:
            self._running = True
            self._last_time = time.monotonic()
            self._source_id = GLib.timeout_add(16, self._tick)

    def set_immediate(self, w, h, opacity=None):
        self.stop()
        self.w.set_immediate(w)
        self.h.set_immediate(h)
        if opacity is not None:
            self.opacity.set_immediate(opacity)
        if self.on_update:
            self.on_update(self.w.current, self.h.current, self.opacity.current)

    def stop(self):
        if self._source_id is not None:
            GLib.source_remove(self._source_id)
            self._source_id = None
        self._running = False

    def is_running(self):
        return self._running

    @property
    def is_animating(self):
        return self._running

    def _tick(self):
        now = time.monotonic()
        dt = min(now - self._last_time, 0.05) # clamp dt to 50ms max to prevent tunneling
        self._last_time = now

        settled_w = self.w.step(dt)
        settled_h = self.h.step(dt)
        settled_o = self.opacity.step(dt)

        if self.on_update:
            self.on_update(self.w.current, self.h.current, self.opacity.current)

        if settled_w and settled_h and settled_o:
            self._running = False
            self._source_id = None
            if self.on_finish:
                self.on_finish()
            return False # Stop timer
        return True # Continue timer
