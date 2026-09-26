"""
Privacy Monitor Module for Dynamic Island.
Monitors active Microphone and Camera usage in real-time.
- Microphone: Checks PipeWire / PulseAudio active input streams.
- Camera: Checks Video4Linux (/dev/video*) and PipeWire video streams.
Emits changes to Dynamic Island to display Apple-style glowing Orange (Mic) and Green (Camera) indicator dots.
"""

import os
import glob
import json
import time
import threading
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

class PrivacyMonitor:
    _instance = None

    @classmethod
    def get_instance(cls, on_change=None):
        if cls._instance is None:
            cls._instance = PrivacyMonitor(on_change=on_change)
        elif on_change:
            cls._instance.callbacks.append(on_change)
        return cls._instance

    def __init__(self, on_change=None):
        self.callbacks = [on_change] if on_change else []
        self.mic_active = False
        self.cam_active = False
        self._running = True
        self._lock = threading.Lock()

        # Start background polling thread (low frequency, 1.0s interval)
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def add_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def _monitor_loop(self):
        while self._running:
            try:
                mic, cam = self._detect_hardware_usage()
                with self._lock:
                    changed = (mic != self.mic_active) or (cam != self.cam_active)
                    self.mic_active = mic
                    self.cam_active = cam

                if changed:
                    GLib.idle_add(self._notify_callbacks, mic, cam)
            except Exception as e:
                # Shield worker loop from crashes
                pass

            time.sleep(1.2)

    def _detect_hardware_usage(self):
        """
        Detect active mic and camera via PipeWire and /dev/video*.
        Returns (mic_active: bool, cam_active: bool).
        """
        mic_active = False
        cam_active = False

        # 1. PipeWire Node Inspection via pw-dump Node (fast ~20ms)
        try:
            res = subprocess.run(
                ['pw-dump', 'Node'],
                capture_output=True,
                text=True,
                timeout=0.8
            )
            if res.returncode == 0 and res.stdout:
                nodes = json.loads(res.stdout)
                for node in nodes:
                    props = node.get('info', {}).get('props', {})
                    media_class = props.get('media.class', '')
                    state = node.get('info', {}).get('state', '')

                    # Audio recording stream from an application (Chrome, OBS, Discord, Meet...)
                    if media_class == 'Stream/Input/Audio':
                        if state in ('running', 'streaming'):
                            mic_active = True

                    # Video capture stream from an application (Meet, Zoom, Cheese...)
                    if media_class == 'Stream/Input/Video':
                        if state in ('running', 'streaming'):
                            cam_active = True
        except Exception:
            pass

        # 2. Direct V4L2 Device Inspection for Camera (/dev/video*)
        if not cam_active:
            cam_active = self._check_v4l2_camera()

        return mic_active, cam_active

    def _check_v4l2_camera(self):
        """Check if any /dev/video* device is currently opened by any user process."""
        try:
            video_devs = glob.glob('/dev/video*')
            if not video_devs:
                return False

            # Quick check via fuser: returns PIDs on stdout if devices are in use
            cmd = ['fuser'] + video_devs
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=0.5)
            if res.stdout.strip():
                return True
        except Exception:
            pass
        return False

    def _notify_callbacks(self, mic, cam):
        for cb in self.callbacks:
            try:
                cb(mic, cam)
            except Exception as e:
                print(f"[PrivacyMonitor] Callback error: {e}")
        return False

    def get_status(self):
        with self._lock:
            return self.mic_active, self.cam_active

    def stop(self):
        self._running = False
