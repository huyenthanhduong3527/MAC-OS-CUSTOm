"""
Device Battery Monitor for Apple Battery Rings Widget.
Queries UPower and Bluetooth for device battery levels (Laptop, AirPods/Headphones, Case, Mouse).
Provides smart fallback matching Apple ecosystem devices.
"""

import time
import subprocess
import threading
from gi.repository import GLib

class DeviceBattery:
    def __init__(self, dev_type="laptop", name="Laptop", percentage=83, charging=False):
        self.dev_type = dev_type # 'laptop', 'earbuds', 'case', 'mouse', 'keyboard'
        self.name = name
        self.percentage = max(0, min(100, int(percentage)))
        self.charging = charging

class BatteryManager:
    def __init__(self, on_update=None):
        self.on_update = on_update
        self.devices = [
            DeviceBattery("laptop", "Laptop", 83, False),
            DeviceBattery("earbuds", "AirPods", 91, True),
            DeviceBattery("case", "AirPods Case", 74, False),
            DeviceBattery("mouse", "Magic Mouse", 79, False),
        ]
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def _monitor_loop(self):
        while self._running:
            self._poll_upower()
            time.sleep(5.0)

    def _poll_upower(self):
        try:
            out = subprocess.check_output(["upower", "-e"], text=True, timeout=1.0)
            dev_paths = [l.strip() for l in out.strip().split("\n") if l.strip()]

            found_laptop = None
            found_bluetooth = []

            for p in dev_paths:
                info = subprocess.check_output(["upower", "-i", p], text=True, timeout=0.8)
                pct = None
                state = ""
                model = ""
                dev_type = ""

                for line in info.split("\n"):
                    line = line.strip()
                    if line.startswith("percentage:"):
                        pct = int(float(line.split(":")[1].replace("%", "").strip()))
                    elif line.startswith("state:"):
                        state = line.split(":")[1].strip().lower()
                    elif line.startswith("model:"):
                        model = line.split(":")[1].strip()
                    elif line.startswith("type:"):
                        dev_type = line.split(":")[1].strip().lower()

                if pct is not None and pct > 0:
                    is_charging = (state in ("charging", "fully-charged"))
                    if "battery" in p.lower() or dev_type == "battery":
                        found_laptop = DeviceBattery("laptop", model or "Laptop", pct, is_charging)
                    elif "headset" in dev_type or "headphone" in dev_type or "ear" in model.lower():
                        found_bluetooth.append(DeviceBattery("earbuds", model or "AirPods", pct, is_charging))
                    elif "mouse" in dev_type or "mouse" in model.lower():
                        found_bluetooth.append(DeviceBattery("mouse", model or "Magic Mouse", pct, is_charging))
                    elif "keyboard" in dev_type:
                        found_bluetooth.append(DeviceBattery("mouse", model or "Keyboard", pct, is_charging))

            # Update devices list while keeping 4 slots
            if found_laptop:
                self.devices[0] = found_laptop
            for idx, bt in enumerate(found_bluetooth[:3]):
                slot = idx + 1
                if slot < len(self.devices):
                    self.devices[slot] = bt

            if self.on_update:
                GLib.idle_add(self.on_update)
        except Exception:
            pass

    def stop(self):
        self._running = False
