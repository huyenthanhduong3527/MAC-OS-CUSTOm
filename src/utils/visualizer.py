"""
Audio visualizer simulation engine.
Generates smooth, rhythmic multi-band equalizer heights for both compact and expanded views.
"""

import math
import random
import time

class AudioVisualizer:
    def __init__(self, num_bars=10):
        self.num_bars = num_bars
        self.bars = [0.15] * num_bars
        self.target_bars = [0.15] * num_bars
        self._is_playing = False
        self._phase = 0.0

    def set_playing(self, is_playing):
        self._is_playing = bool(is_playing)

    def is_playing(self):
        return self._is_playing

    def step(self, dt=0.03):
        self._phase += dt * 3.5

        if self._is_playing:
            for i in range(self.num_bars):
                # Harmonic oscillation with harmonic frequencies + random jitter
                harmonic1 = math.sin(self._phase * 1.8 + i * 0.75)
                harmonic2 = math.cos(self._phase * 2.7 - i * 0.45)
                harmonic3 = math.sin(self._phase * 4.2 + i * 1.1)

                raw = 0.5 + 0.28 * harmonic1 + 0.16 * harmonic2 + 0.1 * harmonic3
                # Bass bars (low indices) have higher energy swings
                energy_factor = 1.1 - 0.3 * (i / max(1, self.num_bars - 1))
                val = max(0.12, min(1.0, raw * energy_factor + random.uniform(-0.06, 0.06)))
                self.target_bars[i] = val
        else:
            # Idle gentle baseline
            for i in range(self.num_bars):
                self.target_bars[i] = 0.12

        # Smooth interpolation towards targets
        for i in range(self.num_bars):
            diff = self.target_bars[i] - self.bars[i]
            self.bars[i] += diff * min(1.0, dt * 12.0)

        return self.bars
