#!/usr/bin/env python3
"""
Generate a True 4K (3840x2160) 60FPS Seamless Live Wallpaper.
Theme: Japanese Torii Gate with Falling Sakura Petals, Breathing Sunburst, & Cosmic Twinkling Stars.
"""

import os
import sys
import math
import random
import time
import subprocess
import cv2
import numpy as np

_script_dir = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(os.path.dirname(_script_dir), "assets", "wallpapers")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sakura_torii_4k_live.mp4")

WIDTH = 3840
HEIGHT = 2160
FPS = 60
DURATION_SEC = 6.0
TOTAL_FRAMES = int(FPS * DURATION_SEC) # 360 frames

def create_petal_mask(size=40):
    """Generate a realistic sakura petal with alpha channel."""
    s = size
    mask = np.zeros((s, s, 4), dtype=np.uint8)
    center = (s // 2, s // 2)
    
    # Draw petal polygon
    pts = []
    num_pts = 30
    for i in range(num_pts):
        angle = 2.0 * math.pi * i / num_pts
        # Cardioid-like / teardrop petal equation
        r = (s * 0.42) * (1.0 - 0.25 * math.sin(angle)) * (1.0 + 0.15 * math.cos(2 * angle))
        # Notch at the tip
        if abs(angle - math.pi / 2) < 0.35:
            r *= 0.82
        x = int(center[0] + r * math.cos(angle))
        y = int(center[1] - r * math.sin(angle))
        pts.append([x, y])
        
    pts = np.array(pts, dtype=np.int32)
    # Fill with soft pink-white gradient
    cv2.fillPoly(mask, [pts], (225, 180, 245, 230))
    # Soft inner highlight
    inner_pts = (pts - center) * 0.65 + center
    cv2.fillPoly(mask, [inner_pts.astype(np.int32)], (250, 220, 255, 255))
    # Slight blur for smooth edges
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    return mask

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"🌸 Generating 4K Live Wallpaper ({WIDTH}x{HEIGHT} @ {FPS}fps, {TOTAL_FRAMES} frames)...")

    # 1. Load and upscale/crop base image to 4K
    if not os.path.exists(SRC_IMAGE):
        print(f"Error: Source image {SRC_IMAGE} not found!")
        return

    base_raw = cv2.imread(SRC_IMAGE)
    ih, iw = base_raw.shape[:2]
    # Crop to 16:9 ratio
    target_aspect = WIDTH / HEIGHT
    current_aspect = iw / ih
    if current_aspect > target_aspect:
        new_w = int(ih * target_aspect)
        start_x = (iw - new_w) // 2
        cropped = base_raw[:, start_x:start_x + new_w]
    else:
        new_h = int(iw / target_aspect)
        start_y = (ih - new_h) // 2
        cropped = base_raw[start_y:start_y + new_h, :]

    base_4k = cv2.resize(cropped, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)
    print("Base image processed to 4K.")

    # 2. Setup Petals (Seamless Loop)
    random.seed(42)
    NUM_PETALS = 140
    petals = []
    
    for i in range(NUM_PETALS):
        z = random.uniform(0.35, 1.8) # Depth
        size = int(24 * z)
        p_mask = create_petal_mask(max(size, 12))
        
        # Periodic movement parameters
        vx = random.uniform(180, 340) * z # Drift leftwards
        vy = random.uniform(80, 220) * z   # Fall downwards
        
        # Periodic integer turns so rotation loops perfectly
        rot_turns = random.choice([-2, -1, 1, 2, 3])
        flip_turns = random.choice([2, 3, 4])
        
        petals.append({
            'x0': random.uniform(-200, WIDTH + 400),
            'y0': random.uniform(-200, HEIGHT + 400),
            'vx': vx,
            'vy': vy,
            'z': z,
            'mask': p_mask,
            'size': size,
            'rot_turns': rot_turns,
            'flip_turns': flip_turns,
            'wobble_freq': random.choice([1, 2, 3]),
            'wobble_amp': random.uniform(25, 60),
            'phase': random.uniform(0, 2 * math.pi)
        })

    # 3. Setup Twinkling Stars in upper nebula
    NUM_STARS = 70
    stars = []
    for _ in range(NUM_STARS):
        sx = random.uniform(0, WIDTH)
        sy = random.uniform(0, HEIGHT * 0.40) # upper sky
        radius = random.uniform(1.5, 4.0)
        blink_k = random.choice([1, 2, 3]) # integer harmonic for seamless loop
        stars.append({
            'x': int(sx),
            'y': int(sy),
            'r': radius,
            'k': blink_k,
            'phase': random.uniform(0, 2 * math.pi),
            'color': random.choice([(255, 230, 240), (255, 255, 220), (220, 240, 255)])
        })

    # 4. Sunburst radial glow map
    sun_x, sun_y = int(WIDTH * 0.53), int(HEIGHT * 0.65)
    Y, X = np.ogrid[:HEIGHT, :WIDTH]
    dist_from_sun = np.sqrt((X - sun_x)**2 + (Y - sun_y)**2)
    glow_radius = 900.0
    sun_mask = np.clip(1.0 - (dist_from_sun / glow_radius), 0, 1) ** 2.2
    sun_glow_layer = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    sun_glow_layer[:, :, 0] = sun_mask * 40.0  # Blue
    sun_glow_layer[:, :, 1] = sun_mask * 110.0 # Green
    sun_glow_layer[:, :, 2] = sun_mask * 180.0 # Red (Warm Golden Peach)

    # 5. FFmpeg Video Encoding Pipe (True 4K, 60 FPS, High Quality)
    cmd = [
        'ffmpeg', '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{WIDTH}x{HEIGHT}',
        '-pix_fmt', 'bgr24',
        '-r', str(FPS),
        '-i', '-',
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '16', # Visually lossless 4K
        '-pix_fmt', 'yuv420p',
        OUTPUT_FILE
    ]

    print("Encoding video through FFmpeg...")
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    t_start = time.time()

    for f_idx in range(TOTAL_FRAMES):
        t = f_idx / FPS # Time in seconds (0.0 to 6.0)
        norm_t = f_idx / TOTAL_FRAMES # 0.0 to 1.0 (loop fraction)

        # Base frame copy
        frame = base_4k.astype(np.float32)

        # A. Sunburst breathing pulse
        sun_pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * norm_t)
        frame += sun_glow_layer * (0.35 + 0.25 * sun_pulse)

        # Clip back to uint8
        frame = np.clip(frame, 0, 255).astype(np.uint8)

        # B. Twinkling Stars
        for star in stars:
            brightness = 0.4 + 0.6 * math.sin(2.0 * math.pi * star['k'] * norm_t + star['phase'])
            if brightness > 0.15:
                rad = max(1, int(star['r'] * (0.8 + 0.4 * brightness)))
                alpha = brightness * 0.85
                cv2.circle(frame, (star['x'], star['y']), rad, star['color'], -1, lineType=cv2.LINE_AA)
                if star['r'] > 2.5: # Star glow halo
                    cv2.circle(frame, (star['x'], star['y']), rad * 2, star['color'], 1, lineType=cv2.LINE_AA)

        # C. Sakura Petals (Seamless Motion)
        for p in petals:
            # Periodic displacement
            dx = (p['vx'] * t + p['wobble_amp'] * math.sin(2.0 * math.pi * p['wobble_freq'] * norm_t + p['phase']))
            dy = p['vy'] * t
            
            # Wrap within screen boundaries
            cur_x = (p['x0'] - dx) % (WIDTH + 600) - 300
            cur_y = (p['y0'] + dy) % (HEIGHT + 400) - 200

            # Rotation & 3D Flip
            angle = (p['rot_turns'] * 360.0 * norm_t) % 360.0
            flip = abs(math.cos(p['flip_turns'] * 2.0 * math.pi * norm_t)) # 3D tumble flip
            
            # Transform petal mask
            s = p['mask'].shape[0]
            if s <= 0 or flip < 0.05:
                continue

            # Scale Y by flip factor
            scaled_h = max(2, int(s * flip))
            scaled_mask = cv2.resize(p['mask'], (s, scaled_h), interpolation=cv2.INTER_LINEAR)
            
            # Rotate
            M = cv2.getRotationMatrix2D((s // 2, scaled_h // 2), angle, 1.0)
            rotated = cv2.warpAffine(scaled_mask, M, (s, scaled_h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

            # Paste into frame with alpha blending
            px, py = int(cur_x), int(cur_y)
            rw, rh = rotated.shape[1], rotated.shape[0]

            x1, y1 = max(0, px), max(0, py)
            x2, y2 = min(WIDTH, px + rw), min(HEIGHT, py + rh)

            if x2 > x1 and y2 > y1:
                mx1, my1 = x1 - px, y1 - py
                mx2, my2 = mx1 + (x2 - x1), my1 + (y2 - y1)
                
                petal_bgr = rotated[my1:my2, mx1:mx2, :3]
                alpha = rotated[my1:my2, mx1:mx2, 3:] / 255.0

                frame[y1:y2, x1:x2] = (frame[y1:y2, x1:x2] * (1.0 - alpha) + petal_bgr * alpha).astype(np.uint8)

        # Stream frame to FFmpeg
        pipe.stdin.write(frame.tobytes())

        if (f_idx + 1) % 60 == 0:
            print(f"Rendered {f_idx + 1}/{TOTAL_FRAMES} frames ({(f_idx + 1)/TOTAL_FRAMES * 100:.0f}%)...")

    pipe.stdin.close()
    pipe.wait()

    elapsed = time.time() - t_start
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"🎉 4K Live Wallpaper generated successfully in {elapsed:.1f}s!")
    print(f"File: {OUTPUT_FILE} ({size_mb:.2f} MB, {WIDTH}x{HEIGHT} @ {FPS}fps)")

if __name__ == "__main__":
    main()
