#!/usr/bin/env python3
import os
import json

config_dir = os.path.expanduser("~/.config/fastfetch")
os.makedirs(config_dir, exist_ok=True)

# Neon Matrix Colors
G = "\033[1;32m"   # Neon Green
W = "\033[1;37m"   # Bright White
C = "\033[1;36m"   # Cyan Visor
D = "\033[0;32m"   # Dim Green
R = "\033[0m"      # Reset

# Sleek Cyberpunk Visor Hacker Mask (NO goofy cartoon eyes!)
mask_lines = [
    f"{G}        .--------.        {R}",
    f"{G}       /  {C}.----.{G}  \\       {R}",
    f"{G}      |  {C}|======|{G}  |      {R}",
    f"{G}      |   {C}`----'{G}   |      {R}",
    f"{G}      |     {W}/\\{G}     |      {R}",
    f"{G}      |   {W}_______{G}  |      {R}",
    f"{G}       \\  {W}`====='{G} /       {R}",
    f"{G}        \\  {D}|||||{G}  /        {R}",
    f"{G}         `-------'        {R}",
]

mask_file = os.path.join(config_dir, "hacker_mask.txt")
with open(mask_file, "w", encoding="utf-8") as f:
    f.write("\n".join(mask_lines) + "\n")

print("Cyber Visor Mask applied!")
