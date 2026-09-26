#!/usr/bin/env python3
import os
import json

config_dir = os.path.expanduser("~/.config/fastfetch")
os.makedirs(config_dir, exist_ok=True)

# Neon Cyber Colors
G = "\033[1;32m"   # Neon Green
W = "\033[1;37m"   # Bright White
C = "\033[1;36m"   # Cyan
D = "\033[0;32m"   # Dim Green
R = "\033[0m"      # Reset

# Watch Dogs / DedSec Cyber Skull (Badass, zero goofy face!)
mask_lines = [
    f"{G}          ______          {R}",
    f"{G}       .-\"      \"-.       {R}",
    f"{G}      /            \\      {R}",
    f"{G}     |   {C}[X]  [X]{G}   |     {R}",
    f"{G}     |      {W}/\\{G}      |     {R}",
    f"{G}     |    {W}|====|{G}    |     {R}",
    f"{G}      \\   {W}|    |{G}   /      {R}",
    f"{G}       `'-.____.-'`       {R}",
]

mask_file = os.path.join(config_dir, "hacker_mask.txt")
with open(mask_file, "w", encoding="utf-8") as f:
    f.write("\n".join(mask_lines) + "\n")

print("DedSec Cyber Skull generated!")
