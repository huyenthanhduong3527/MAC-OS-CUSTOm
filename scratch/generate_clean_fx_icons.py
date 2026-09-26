import os
import math
from PIL import Image, ImageDraw, ImageOps, ImageFilter

out_dir = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth"
w, h = 120, 90

def draw_base_silhouette(color_fg=(220, 220, 230), color_bg=(32, 34, 40)):
    im = Image.new("RGB", (w, h), color_bg)
    d = ImageDraw.Draw(im)
    # Draw simple clean portrait head and shoulders
    cx, cy = w // 2, h // 2 - 4
    # Head
    head_r = 16
    d.ellipse([cx - head_r, cy - head_r, cx + head_r, cy + head_r], fill=color_fg)
    # Shoulders
    d.pieslice([cx - 36, cy + 8, cx + 36, cy + 60], 180, 360, fill=color_fg)
    return im

# 1. Normal
im_norm = draw_base_silhouette()
im_norm.save(os.path.join(out_dir, "fx_normal.png"))

# 2. Mirror
im_mirror = draw_base_silhouette()
d = ImageDraw.Draw(im_mirror)
# Draw split line and mirrored arrow
d.line([(w//2, 10), (w//2, h-10)], fill=(0, 122, 255), width=2)
im_mirror.save(os.path.join(out_dir, "fx_mirror.png"))

# 3. B&W
im_bw = draw_base_silhouette(color_fg=(255, 255, 255), color_bg=(15, 15, 15))
im_bw.save(os.path.join(out_dir, "fx_bw.png"))

# 4. Sepia
im_sepia = draw_base_silhouette(color_fg=(230, 195, 150), color_bg=(45, 30, 18))
im_sepia.save(os.path.join(out_dir, "fx_sepia.png"))

# 5. Negative
im_neg = draw_base_silhouette(color_fg=(20, 20, 30), color_bg=(235, 235, 245))
im_neg.save(os.path.join(out_dir, "fx_negative.png"))

# 6. Thermal
im_thermal = draw_base_silhouette(color_fg=(255, 60, 0), color_bg=(0, 20, 180))
d = ImageDraw.Draw(im_thermal)
d.ellipse([w//2 - 10, h//2 - 14, w//2 + 10, h//2 + 6], fill=(255, 255, 0))
im_thermal.save(os.path.join(out_dir, "fx_thermal.png"))

# 7. Comic
im_comic = draw_base_silhouette(color_fg=(255, 255, 255), color_bg=(20, 20, 20))
d = ImageDraw.Draw(im_comic)
for y in range(0, h, 6):
    for x in range(0, w, 6):
        d.point((x, y), fill=(100, 100, 100))
im_comic.save(os.path.join(out_dir, "fx_comic.png"))

# 8. Pop Art
im_pop = Image.new("RGB", (w, h), (0, 0, 0))
q_w, q_h = w // 2, h // 2
colors = [
    ((255, 0, 128), (0, 255, 255)),
    ((255, 255, 0), (255, 0, 0)),
    ((0, 255, 0), (128, 0, 255)),
    ((255, 128, 0), (0, 0, 255))
]
for idx, (bg, fg) in enumerate(colors):
    qx = (idx % 2) * q_w
    qy = (idx // 2) * q_h
    tile = Image.new("RGB", (q_w, q_h), bg)
    td = ImageDraw.Draw(tile)
    cx, cy = q_w // 2, q_h // 2 - 2
    td.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=fg)
    td.pieslice([cx - 18, cy + 4, cx + 18, cy + 30], 180, 360, fill=fg)
    im_pop.paste(tile, (qx, qy))
im_pop.save(os.path.join(out_dir, "fx_popart.png"))

# 9. Alien
im_alien = draw_base_silhouette(color_fg=(57, 255, 20), color_bg=(10, 35, 15))
im_alien.save(os.path.join(out_dir, "fx_alien.png"))

print("Generated clean effect icons without any user photos")
