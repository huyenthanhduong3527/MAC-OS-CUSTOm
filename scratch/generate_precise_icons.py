from PIL import Image, ImageDraw

def create_mode_burst():
    # 4 vertical panels in a frame: [ | | | ]
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    
    # Outer rounded rectangle
    x0, y0, x1, y1 = 8, 12, 40, 36
    d.rounded_rectangle([x0, y0, x1, y1], radius=3, outline=(225, 225, 230, 240), width=2)
    
    # 3 vertical divider lines
    panel_w = (x1 - x0) / 4.0
    for i in range(1, 4):
        lx = int(x0 + i * panel_w)
        d.line([(lx, y0 + 3), (lx, y1 - 3)], fill=(225, 225, 230, 240), width=2)
        
    im.save("/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/mode_burst.png")

def create_mode_single():
    # Landscape photo with mountain and sun
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    
    x0, y0, x1, y1 = 8, 12, 40, 36
    d.rounded_rectangle([x0, y0, x1, y1], radius=3, outline=(255, 255, 255, 255), width=2)
    
    # Sun dot
    d.ellipse([28, 16, 33, 21], fill=(255, 255, 255, 255))
    
    # Mountains
    # Left mountain peak at (18, 24)
    # Right mountain peak at (27, 27)
    d.polygon([(10, 34), (18, 24), (25, 34)], fill=(255, 255, 255, 255))
    d.polygon([(22, 34), (28, 27), (38, 34)], fill=(255, 255, 255, 255))
    
    im.save("/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/mode_single.png")

def create_mode_video():
    # Video camera: rounded rect body + triangle lens
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    
    # Body
    x0, y0, x1, y1 = 8, 15, 31, 33
    d.rounded_rectangle([x0, y0, x1, y1], radius=3, outline=(225, 225, 230, 240), width=2)
    
    # Lens trapezoid / triangle on right
    # Points: (32, 21), (40, 16), (40, 32), (32, 27)
    d.polygon([(33, 21), (40, 16), (40, 32), (33, 27)], fill=(225, 225, 230, 240))
    
    im.save("/home/tramvo/DYNAMIC-ISLNAD-FOR-UNTUBU-LINUX/assets/photobooth/mode_video.png")

create_mode_burst()
create_mode_single()
create_mode_video()
print("Generated precise icons")
