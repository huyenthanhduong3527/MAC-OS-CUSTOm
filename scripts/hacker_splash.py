#!/usr/bin/env python3
import sys
import time
import random
import shutil
import getpass
import os
import pwd

def get_display_name():
    try:
        gecos = pwd.getpwuid(os.getuid()).pw_gecos
        name = gecos.split(",")[0].strip()
        if name:
            return name
    except Exception:
        pass
    for env in ("USER_DISPLAY_NAME", "FULLNAME", "NAME"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    return getpass.getuser()

def run_matrix_splash(duration=0.9):
    # Only run in real interactive terminal
    if not sys.stdout.isatty():
        return

    cols, lines = shutil.get_terminal_size((80, 24))
    
    # Hide cursor
    sys.stdout.write("\033[?25l\033[2J")
    sys.stdout.flush()

    # Matrix characters (numbers, letters, katakana-like symbols)
    chars = "0123456789ABCDEFabcdef$#@%&*+=<>~:;!?/\\|"
    
    # Columns state: each column has a position and length
    drops = [random.randint(-lines, 0) for _ in range(cols)]
    
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            output = []
            for col in range(0, cols, 2):  # skip every 2 cols for clean spacing
                row = drops[col]
                if 0 <= row < lines:
                    # White bright head
                    char = random.choice(chars)
                    output.append(f"\033[{row+1};{col+1}H\033[1;37m{char}")
                if 0 <= row - 1 < lines:
                    # Bright neon green
                    char = random.choice(chars)
                    output.append(f"\033[{row};{col+1}H\033[1;32m{char}")
                if 0 <= row - 3 < lines:
                    # Dim green tail
                    char = random.choice(chars)
                    output.append(f"\033[{row-2};{col+1}H\033[0;32m{char}")
                if 0 <= row - 6 < lines:
                    # Erase trail
                    output.append(f"\033[{row-5};{col+1}H ")
                
                # Advance drop
                drops[col] += 1
                if drops[col] - 6 > lines:
                    drops[col] = random.randint(-4, 0)

            sys.stdout.write("".join(output))
            sys.stdout.flush()
            time.sleep(0.035)

    except KeyboardInterrupt:
        pass
    finally:
        # Reset and clear
        user = get_display_name()
        sys.stdout.write("\033[2J\033[1;1H\033[?25h\033[0m")
        # Sleek hacker greeting badge
        sys.stdout.write("\033[1;32m⚡ [SYSTEM READY]\033[0m ")
        sys.stdout.flush()
        time.sleep(0.06)

        # Typewriter effect for "Xin chào, {user}!"
        greeting = f"Xin chào, {user}!"
        sys.stdout.write("\033[1;36m")
        try:
            for char in greeting:
                sys.stdout.write(char)
                sys.stdout.flush()
                time.sleep(0.03)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write("\033[0m\n\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_matrix_splash(0.85)
