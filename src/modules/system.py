"""
System hardware monitor for Dynamic Island.
Collects CPU %, RAM usage, Disk, and Battery (UPower/psutil).
"""

import psutil
import dbus
from gi.repository import GLib

class SystemMonitor:
    def __init__(self):
        self.cpu_pct = 0.0
        self.ram_pct = 0.0
        self.ram_used_gb = 0.0
        self.ram_total_gb = 0.0
        self.battery_pct = 100
        self.is_charging = False
        self.has_battery = False
        self.disk_pct = 0.0

        self._upower_device = None
        self._init_upower()
        self.refresh()

    def _init_upower(self):
        try:
            bus = dbus.SystemBus()
            upower = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower")
            # Try to get DisplayDevice
            self._upower_device = bus.get_object("org.freedesktop.UPower", "/org/freedesktop/UPower/devices/DisplayDevice")
        except Exception:
            self._upower_device = None

    def refresh(self):
        """Update system metrics."""
        # CPU
        self.cpu_pct = psutil.cpu_percent(interval=None)

        # RAM
        mem = psutil.virtual_memory()
        self.ram_pct = mem.percent
        self.ram_used_gb = mem.used / (1024 ** 3)
        self.ram_total_gb = mem.total / (1024 ** 3)

        # Disk
        try:
            disk = psutil.disk_usage('/')
            self.disk_pct = disk.percent
        except Exception:
            self.disk_pct = 0.0

        # Battery
        bat = psutil.sensors_battery()
        if bat is not None:
            self.has_battery = True
            self.battery_pct = int(bat.percent)
            self.is_charging = bat.power_plugged
        elif self._upower_device:
            try:
                props = dbus.Interface(self._upower_device, "org.freedesktop.DBus.Properties")
                dev_type = props.Get("org.freedesktop.UPower.Device", "Type")
                # Type 2 = Battery
                if dev_type == 2:
                    self.has_battery = True
                    self.battery_pct = int(props.Get("org.freedesktop.UPower.Device", "Percentage"))
                    state = props.Get("org.freedesktop.UPower.Device", "State")
                    self.is_charging = (state == 1) # 1 = Charging
                else:
                    self.has_battery = False
                    self.battery_pct = 100
                    self.is_charging = True
            except Exception:
                self.has_battery = False
                self.battery_pct = 100
                self.is_charging = True
        else:
            self.has_battery = False
            self.battery_pct = 100
            self.is_charging = True

        return {
            "cpu_pct": self.cpu_pct,
            "ram_pct": self.ram_pct,
            "ram_used_gb": self.ram_used_gb,
            "ram_total_gb": self.ram_total_gb,
            "battery_pct": self.battery_pct,
            "is_charging": self.is_charging,
            "has_battery": self.has_battery,
            "disk_pct": self.disk_pct,
        }
