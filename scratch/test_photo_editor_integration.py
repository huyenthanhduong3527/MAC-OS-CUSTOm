import os
import sys
import tempfile
import shutil
from PIL import Image, ImageDraw

# Create dummy image
temp_dir = tempfile.mkdtemp()
img_path = os.path.join(temp_dir, "sample_test.jpg")

im = Image.new("RGB", (1200, 800), color=(100, 150, 200))
draw = ImageDraw.Draw(im)
draw.rectangle([100, 100, 500, 400], fill=(220, 80, 50))
draw.text((150, 150), "Apple macOS Photos Test", fill=(255, 255, 255))
im.save(img_path, "JPEG")
print(f"Created sample image: {img_path}, size={im.size}")

# Test PhotoEditorEngine
from src.ui.photo_editor import PhotoEditorEngine

engine = PhotoEditorEngine(img_path)
assert engine.original_im is not None
assert engine.original_im.size == (1200, 800)
print("1. Engine loaded image successfully.")

# Test Adjustments
engine.set_adjustment("exposure", 25)
engine.set_adjustment("brilliance", 15)
engine.set_adjustment("saturation", 30)
engine.set_adjustment("warmth", 10)
pb = engine.render_preview_pixbuf()
assert pb is not None
assert pb.get_width() > 0
print("2. Adjustments rendered preview pixbuf successfully.")

# Test Filters
engine.set_filter("vivid", 0.8)
pb_vivid = engine.render_preview_pixbuf()
assert pb_vivid is not None
engine.set_filter("noir", 1.0)
pb_noir = engine.render_preview_pixbuf()
assert pb_noir is not None
print("3. Filters applied successfully.")

# Test Crop and Rotation
engine.rotate_right()
assert engine.rotation_deg == 90
engine.set_crop_box((0.1, 0.1, 0.9, 0.9))
pb_crop = engine.render_preview_pixbuf()
assert pb_crop is not None
print("4. Rotation & crop rendered preview successfully.")

# Test Markup
engine.add_markup({
    "type": "arrow",
    "p1": (0.2, 0.2),
    "p2": (0.6, 0.6),
    "color": (255, 59, 48, 255),
    "width": 6
})
engine.add_markup({
    "type": "text",
    "pos": (0.3, 0.3),
    "text": "Tested Markup",
    "color": (255, 204, 0, 255)
})
pb_markup = engine.render_preview_pixbuf()
assert pb_markup is not None
print("5. Markup added and rendered successfully.")

# Test Auto-Enhance
engine.auto_enhance()
assert engine.adjustments["exposure"] != 0.0 or engine.adjustments["contrast"] != 0.0
print("6. Auto-enhance executed successfully.")

# Test Save Full
assert engine.save_full() is True
assert engine.has_backup() is True
print("7. Full-res save and backup created successfully.")

# Test Revert to original
assert engine.revert_to_original() is True
print("8. Revert to original restored successfully.")

# Cleanup
shutil.rmtree(temp_dir)
print("\nALL PHOTO EDITOR INTEGRATION TESTS PASSED SUCCESSFULLY!")
