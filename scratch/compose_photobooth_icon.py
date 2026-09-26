import math
import cairo
import numpy as np
from PIL import Image, ImageFilter

def create_photobooth_icon():
    WIDTH = 512
    HEIGHT = 512
    
    # 1. Base squircle in Cairo
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.Antialias.SUBPIXEL)
    
    scale = 512.0 / 16.933
    
    def path_squircle(ctx):
        ctx.save()
        ctx.scale(scale, scale)
        ctx.move_to(5.36, 1.058)
        ctx.curve_to(5.36 - 1.53, 1.058, 5.36 - 2.577, 1.058 + 0.457, 5.36 - 3.26, 1.058 + 1.2)
        ctx.curve_to(5.36 - 3.26 - 0.678, 1.058 + 1.2 + 0.74, 5.36 - 3.26 - 1.042, 1.058 + 1.2 + 1.8, 5.36 - 3.26 - 1.042, 1.058 + 1.2 + 3.0)
        ctx.rel_line_to(0, 6.416)
        ctx.rel_curve_to(0, 1.2, 0.364, 2.261, 1.042, 3.001)
        ctx.rel_curve_to(0.683, 0.744, 1.73, 1.2, 3.26, 1.2)
        ctx.rel_line_to(6.23, 0)
        ctx.rel_curve_to(1.53, 0, 2.579, -0.456, 3.26, -1.2)
        ctx.rel_curve_to(0.68, -0.74, 1.025, -1.703, 1.025, -3.0)
        ctx.line_to(16.933 - 1.058, 5.5)
        ctx.curve_to(16.933 - 1.058, 5.5 - 1.57, 16.933 - 1.058 - 0.345, 5.5 - 2.502, 16.933 - 1.058 - 1.024, 5.5 - 3.242)
        ctx.rel_curve_to(-0.682, -0.743, -1.73, -1.2, -3.26, -1.2)
        ctx.line_to(6.745, 1.058)
        ctx.close_path()
        ctx.restore()

    # Background gradient: Ruby red
    grad = cairo.LinearGradient(256, 32, 256, 480)
    grad.add_color_stop_rgb(0.0, 1.0, 0.22, 0.31)   # #FF384F
    grad.add_color_stop_rgb(0.5, 0.88, 0.10, 0.20)  # #E01A33
    grad.add_color_stop_rgb(1.0, 0.68, 0.05, 0.12)  # #AD0D1F

    path_squircle(cr)
    cr.set_source(grad)
    cr.fill()

    # Subtle radial highlight on top-left of squircle
    rad_hl = cairo.RadialGradient(180, 120, 20, 200, 160, 280)
    rad_hl.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.20)
    rad_hl.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
    path_squircle(cr)
    cr.set_source(rad_hl)
    cr.fill()

    # Bottom inner shadow
    bot_shadow = cairo.LinearGradient(256, 400, 256, 480)
    bot_shadow.add_color_stop_rgba(0.0, 0.0, 0.0, 0.0, 0.0)
    bot_shadow.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.25)
    path_squircle(cr)
    cr.set_source(bot_shadow)
    cr.fill()

    # Specular rim
    rim_grad = cairo.LinearGradient(256, 30, 256, 480)
    rim_grad.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.48)
    rim_grad.add_color_stop_rgba(0.25, 1.0, 1.0, 1.0, 0.22)
    rim_grad.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.05)
    path_squircle(cr)
    cr.set_source(rim_grad)
    cr.set_line_width(1.5)
    cr.stroke()

    # Save squircle base
    surf.write_to_png('scratch/squircle_base.png')

    # 2. Build the Photo Strip Card at 2x resolution
    CARD_W = 168 * 2
    CARD_H = 412 * 2
    PAD_X = 12 * 2
    PAD_TOP = 14 * 2
    PAD_BOT = 16 * 2
    GAP_Y = 8 * 2
    CORNER_R = 10 * 2
    
    PHOTO_W = CARD_W - 2 * PAD_X
    PHOTO_H = int((CARD_H - PAD_TOP - PAD_BOT - 3 * GAP_Y) / 4)

    card_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, CARD_W, CARD_H)
    ccr = cairo.Context(card_surf)
    ccr.set_antialias(cairo.Antialias.SUBPIXEL)

    def draw_card_rect(ctx, x, y, w, h, r):
        ctx.new_sub_path()
        ctx.arc(x + w - r, y + r, r, -math.pi/2, 0)
        ctx.arc(x + w - r, y + h - r, r, 0, math.pi/2)
        ctx.arc(x + r, y + h - r, r, math.pi/2, math.pi)
        ctx.arc(x + r, y + r, r, math.pi, 3*math.pi/2)
        ctx.close_path()

    # Fill photopaper
    draw_card_rect(ccr, 0, 0, CARD_W, CARD_H, CORNER_R)
    paper_pat = cairo.LinearGradient(0, 0, CARD_W, CARD_H)
    paper_pat.add_color_stop_rgb(0.0, 1.0, 1.0, 1.0)
    paper_pat.add_color_stop_rgb(1.0, 0.96, 0.96, 0.97)
    ccr.set_source(paper_pat)
    ccr.fill()

    # Subtle card border
    draw_card_rect(ccr, 0.5, 0.5, CARD_W - 1, CARD_H - 1, CORNER_R)
    ccr.set_source_rgba(0.0, 0.0, 0.0, 0.10)
    ccr.set_line_width(1.5)
    ccr.stroke()

    # Load the 4 photos
    photos = [
        Image.open('scratch/photo1.png'),
        Image.open('scratch/photo2.png'),
        Image.open('scratch/photo3.png'),
        Image.open('scratch/photo4.png')
    ]

    card_surf.write_to_png('scratch/card_blank.png')
    card_img = Image.open('scratch/card_blank.png').convert('RGBA')

    # Draw each photo
    for i, p_img in enumerate(photos):
        px = PAD_X
        py = PAD_TOP + i * (PHOTO_H + GAP_Y)
        
        p_resized = p_img.resize((PHOTO_W, PHOTO_H), Image.Resampling.LANCZOS)
        
        m_surf = cairo.ImageSurface(cairo.FORMAT_A8, PHOTO_W, PHOTO_H)
        m_cr = cairo.Context(m_surf)
        draw_card_rect(m_cr, 0, 0, PHOTO_W, PHOTO_H, 6 * 2)
        m_cr.set_source_rgba(0, 0, 0, 1.0)
        m_cr.fill()
        m_surf.write_to_png('scratch/mask_tmp.png')
        mask = Image.open('scratch/mask_tmp.png').convert('L')
        
        card_img.paste(p_resized, (px, py), mask)

        # Inner groove around photo window
        overlay_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, PHOTO_W, PHOTO_H)
        ocr = cairo.Context(overlay_surf)
        draw_card_rect(ocr, 0.5, 0.5, PHOTO_W - 1, PHOTO_H - 1, 6 * 2)
        ocr.set_source_rgba(0.0, 0.0, 0.0, 0.20)
        ocr.set_line_width(1.5)
        ocr.stroke()
        overlay_surf.write_to_png('scratch/border_tmp.png')
        border_img = Image.open('scratch/border_tmp.png')
        card_img.paste(border_img, (px, py), border_img)

    # Diagonal gloss sheen across the entire photo strip
    gloss_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, CARD_W, CARD_H)
    gcr = cairo.Context(gloss_surf)
    draw_card_rect(gcr, 0, 0, CARD_W, CARD_H, CORNER_R)
    gcr.clip()
    
    g_pat = cairo.LinearGradient(0, 0, CARD_W, CARD_H * 0.75)
    g_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.28)
    g_pat.add_color_stop_rgba(0.35, 1.0, 1.0, 1.0, 0.10)
    g_pat.add_color_stop_rgba(0.65, 1.0, 1.0, 1.0, 0.0)
    gcr.set_source(g_pat)
    gcr.paint()
    gloss_surf.write_to_png('scratch/gloss_tmp.png')
    gloss_img = Image.open('scratch/gloss_tmp.png')
    card_img.paste(gloss_img, (0, 0), gloss_img)

    # Downscale card to 1x (168x412)
    card_1x = card_img.resize((168, 412), Image.Resampling.LANCZOS)
    card_1x.save('scratch/card_finished.png')

    # 3. Rotate card (-6.2 deg)
    ROT_ANGLE = -6.2
    card_rot = card_1x.rotate(ROT_ANGLE, resample=Image.Resampling.BICUBIC, expand=True)
    
    # Soft drop shadow for rotated card
    shadow_mask = card_rot.split()[3]
    shadow_img = Image.new('RGBA', card_rot.size, (0, 0, 0, 0))
    shadow_color = Image.new('RGBA', card_rot.size, (0, 0, 0, int(255 * 0.40)))
    shadow_img.paste(shadow_color, (0, 0), shadow_mask)
    shadow_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=8))

    # 4. Composite final icon
    squircle_img = Image.open('scratch/squircle_base.png').convert('RGBA')
    
    # Squircle ambient shadow
    sq_shadow = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    sq_black = Image.new('RGBA', (512, 512), (0, 0, 0, int(255 * 0.35)))
    sq_shadow.paste(sq_black, (0, 0), squircle_img.split()[3])
    sq_shadow_blurred = sq_shadow.filter(ImageFilter.GaussianBlur(radius=14))
    
    final_canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    # Squircle shadow
    final_canvas.paste(sq_shadow_blurred, (0, 10), sq_shadow_blurred)
    # Squircle
    final_canvas.paste(squircle_img, (0, 0), squircle_img)
    
    # Position card centered
    cw, ch = card_rot.size
    cx = (512 - cw) // 2
    cy = (512 - ch) // 2 - 4 # slightly shifted up so top overlaps squircle edge
    
    # Card shadow
    final_canvas.paste(shadow_blurred, (cx + 4, cy + 8), shadow_blurred)
    # Card
    final_canvas.paste(card_rot, (cx, cy), card_rot)

    # Save outputs
    final_canvas.save('assets/photobooth_icon.png')
    final_canvas.resize((256, 256), Image.Resampling.LANCZOS).save('scratch/photobooth_icon_256.png')
    final_canvas.resize((128, 128), Image.Resampling.LANCZOS).save('scratch/photobooth_icon_128.png')
    print('Photo Booth icon generated successfully!')

if __name__ == '__main__':
    create_photobooth_icon()
