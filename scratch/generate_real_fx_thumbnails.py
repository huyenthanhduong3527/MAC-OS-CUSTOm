import os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

feed_path = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/default_camera_feed.jpg"
out_dir = "/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth"

# Load and crop/resize base image to 120x90
base = Image.open(feed_path).convert("RGB")
# Crop center face
w, h = base.size
face = base.crop((w * 0.15, h * 0.1, w * 0.75, h * 0.9))
face = face.resize((120, 90), Image.LANCZOS)

# 1. Normal
face.save(os.path.join(out_dir, "fx_normal.png"))

# 2. Mirror
mirror = face.transpose(Image.FLIP_LEFT_RIGHT)
mirror.save(os.path.join(out_dir, "fx_mirror.png"))

# 3. B&W
bw = ImageOps.grayscale(face)
bw = ImageEnhance.Contrast(bw).enhance(1.4)
bw.save(os.path.join(out_dir, "fx_bw.png"))

# 4. Sepia
gray = ImageOps.grayscale(face)
sepia = ImageOps.colorize(gray, "#2e1c0c", "#e8c39e")
sepia.save(os.path.join(out_dir, "fx_sepia.png"))

# 5. Negative
neg = ImageOps.invert(face)
neg.save(os.path.join(out_dir, "fx_negative.png"))

# 6. Thermal
gray = ImageOps.grayscale(face)
thermal = ImageOps.colorize(gray, "#0000ff", "#ffff00", mid="#ff0000")
thermal.save(os.path.join(out_dir, "fx_thermal.png"))

# 7. Comic
comic = face.filter(ImageFilter.CONTOUR)
comic = ImageOps.invert(comic)
comic.save(os.path.join(out_dir, "fx_comic.png"))

# 8. Pop Art
# 4-quadrant Warhol style
p_w, p_h = 60, 45
q1 = ImageOps.colorize(ImageOps.grayscale(face.resize((p_w, p_h))), "#ff007f", "#00ffff")
q2 = ImageOps.colorize(ImageOps.grayscale(face.resize((p_w, p_h))), "#ffff00", "#ff0000")
q3 = ImageOps.colorize(ImageOps.grayscale(face.resize((p_w, p_h))), "#00ff00", "#7f00ff")
q4 = ImageOps.colorize(ImageOps.grayscale(face.resize((p_w, p_h))), "#ff7f00", "#0000ff")
popart = Image.new("RGB", (120, 90))
popart.paste(q1, (0, 0))
popart.paste(q2, (p_w, 0))
popart.paste(q3, (0, p_h))
popart.paste(q4, (p_w, p_h))
popart.save(os.path.join(out_dir, "fx_popart.png"))

# 9. Alien (toxic neon green)
alien = ImageOps.colorize(ImageOps.grayscale(face), "#002200", "#39ff14", mid="#00bb22")
alien.save(os.path.join(out_dir, "fx_alien.png"))

print("Successfully generated all 9 real photo effect thumbnails!")
