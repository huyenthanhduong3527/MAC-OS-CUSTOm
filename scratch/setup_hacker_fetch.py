#!/usr/bin/env python3
import os
import json

config_dir = os.path.expanduser("~/.config/fastfetch")
os.makedirs(config_dir, exist_ok=True)

# Colors
G = "\033[1;32m"   # Neon Green
W = "\033[1;37m"   # Bright White
C = "\033[1;36m"   # Cyan
D = "\033[0;32m"   # Dim Green
R = "\033[0m"      # Reset

# Proportional, sharp Cyber Anonymous Hacker Mask
mask_lines = [
    f"{G}        .-------.        {R}",
    f"{G}       /  {W}.-. .-.{G}  \\       {R}",
    f"{G}      |  {C}( o ) ( o ){G}  |      {R}",
    f"{G}      |   {W}'-' '-'{G}   |      {R}",
    f"{G}      |     {W}/\\{G}     |      {R}",
    f"{G}      |   {G}\\_____/{G}   |      {R}",
    f"{G}       \\   {C}`==='{G}   /       {R}",
    f"{G}        \\   {D}|||{G}   /        {R}",
    f"{G}         `-------'        {R}",
]

mask_file = os.path.join(config_dir, "hacker_mask.txt")
with open(mask_file, "w", encoding="utf-8") as f:
    f.write("\n".join(mask_lines) + "\n")

# Compact, sleek Fastfetch JSON config
config = {
    "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
    "logo": {
        "source": mask_file,
        "type": "file-raw",
        "padding": {
            "top": 0,
            "left": 1,
            "right": 3
        }
    },
    "display": {
        "separator": " ➜  ",
        "color": {
            "keys": "green",
            "title": "cyan"
        }
    },
    "modules": [
        {
            "type": "title",
            "format": "AMTRVO@{host-name}"
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

print("Hacker Fastfetch configured successfully!")
