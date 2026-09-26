#!/usr/bin/env python3
import os
import json

config_dir = os.path.expanduser("~/.config/fastfetch")
os.makedirs(config_dir, exist_ok=True)

# Compact, perfectly-proportioned Fastfetch JSON config with Kali Linux Dragon
config = {
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "logo": {
        "source": "Kali_small",
        "type": "small",
        "padding": {
            "top": 0,
            "left": 1,
            "right": 3
        },
        "color": {
            "1": "cyan",
            "2": "blue"
        }
    },
    "display": {
        "separator": " ➜  ",
        "color": {
            "keys": "cyan",
            "title": "green"
        }
    },
    "modules": [
        {
            "type": "title",
            "format": "{user-name}@{host-name}"
        },
        {
            "type": "separator",
            "string": "─"
        },
        {
            "type": "os",
            "key": "OS",
            "format": "{name} {version}"
        },
        {
            "type": "host",
            "key": "Host"
        },
        {
            "type": "kernel",
            "key": "Kernel"
        },
        {
            "type": "uptime",
            "key": "Uptime"
        },
        {
            "type": "shell",
            "key": "Shell"
        },
        {
            "type": "cpu",
            "key": "CPU",
            "format": "{name}"
        },
        {
            "type": "gpu",
            "key": "GPU",
            "format": "{name}"
        },
        {
            "type": "memory",
            "key": "Memory"
        },
        "break",
        {
            "type": "colors",
            "symbol": "circle"
        }
    ]
}

config_file = os.path.join(config_dir, "config.jsonc")
with open(config_file, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)

print("Kali Linux Fastfetch configured successfully!")
