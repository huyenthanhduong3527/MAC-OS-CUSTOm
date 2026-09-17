"""
Cosmic Orbit Celestial Solar App Launcher for Dynamic Island.
Redesigned with Apple Glassmorphic aesthetics:
- Synchronized harmonic orbital resonance (locked 60° phase separation, zero clumping/collision)
- Asymmetric 3D depth perspective (tucked behind island, sweeping gracefully below into open desktop space)
- Ultra-refined liquid glass orbs with atmospheric nebula halos & specular glass sheen
- Sparkling comet tail / stardust trails behind each moving planet
- Photorealistic Saturn ring with golden specular gradient
- Apple frosted glass floating badge on hover
- Instant non-blocking app execution with cosmic shockwave ripples
"""

import os
import math
import time
import subprocess
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from src.utils.icons import get_pixbuf

class Shockwave:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.radius = 8.0
        self.max_radius = 60.0
        self.alpha = 0.95

    def step(self, dt):
        self.radius += 120.0 * dt
        self.alpha = max(0.0, 1.0 - (self.radius / self.max_radius))
        return self.radius < self.max_radius


class CosmicPlanet:
    def __init__(self, planet_id, name, commands, phase_index, base_radius, color, glow, icon_name, has_rings=False):
        self.id = planet_id
        self.name = name
        self.commands = commands
        self.phase_index = phase_index  # 0 to 5 for exact 60° harmonic spacing
        self.base_radius = base_radius
        self.color = color  # (r, g, b)
        self.glow = glow    # (r, g, b)
        self.icon_name = icon_name
        self.has_rings = has_rings

        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.scale = 1.0
        self.angle = 0.0
        self.hovered = False
        self.hover_progress = 0.0  # 0.0 to 1.0

    def update_position(self, master_angle, cx, cy, orbit_a=310.0, dt=0.033):
        # Guaranteed locked harmonic angular separation (60° apart)
        self.angle = (master_angle + self.phase_index * (2.0 * math.pi / 6.0)) % (2.0 * math.pi)

        # Asymmetric 3D Perspective Projection:
        # Behind the pill (sin < 0): tightly tucked behind island pill, never touches top bar
        # In front of the pill (sin >= 0): swoops gracefully downward into the open wallpaper area
        self.x = cx + orbit_a * math.cos(self.angle)
        sin_a = math.sin(self.angle)
        center_y = cy + 18.0

        if sin_a < 0:
            self.y = center_y + 18.0 * sin_a
        else:
            self.y = center_y + 70.0 * sin_a

        self.z = sin_a  # depth: < 0 is behind, >= 0 is in front

        # Smooth hover scale transition
        target_hover = 1.0 if self.hovered else 0.0
        self.hover_progress += (target_hover - self.hover_progress) * min(1.0, dt * 14.0)

        # Depth perspective scale (larger when in front) + hover expansion
        depth_scale = 1.0 + 0.20 * self.z
        self.scale = depth_scale * (1.0 + 0.26 * self.hover_progress)

    def contains_point(self, px, py):
        eff_radius = (self.base_radius * self.scale) + 12.0
        dx = px - self.x
        dy = py - self.y
        return (dx * dx + dy * dy) <= (eff_radius * eff_radius)

    def launch(self):
        """Execute the planet's application command non-blockingly."""
        for cmd in self.commands:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[Cosmic Orbit] Launched {self.name} via {cmd}")
                return True
            except FileNotFoundError:
                continue
            except Exception as e:
                print(f"[Cosmic Orbit] Error launching {self.name}: {e}")
                continue

        try:
            subprocess.Popen(["xdg-open", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return False


class CosmicOrbitEngine:
    def __init__(self):
        self.planets = [
            # 1. Google Chrome / Web Browser (Vibrant Ocean Cyan)
            CosmicPlanet(
                planet_id="browser",
                name="Google Chrome",
                commands=[["google-chrome"], ["google-chrome-stable"], ["chromium-browser"], ["firefox"]],
                phase_index=0,
                base_radius=17.0,
                color=(0.12, 0.70, 0.98),
                glow=(0.15, 0.75, 1.0),
                icon_name="globe"
            ),
            # 2. Terminal / Ptyxis (Fiery Coral / Crimson)
            CosmicPlanet(
                planet_id="terminal",
                name="Terminal",
                commands=[["ptyxis"], ["x-terminal-emulator"], ["gnome-terminal"]],
                phase_index=1,
                base_radius=15.0,
                color=(0.98, 0.35, 0.22),
                glow=(1.0, 0.40, 0.25),
                icon_name="terminal"
            ),
            # 3. Saturn / VS Code Editor (Golden Amber with Rings)
            CosmicPlanet(
                planet_id="code",
                name="VS Code / Editor",
                commands=[["code"], ["gnome-text-editor"], ["gedit"]],
                phase_index=2,
                base_radius=18.0,
                color=(0.95, 0.75, 0.20),
                glow=(0.98, 0.80, 0.30),
                icon_name="code",
                has_rings=True
            ),
            # 4. Music / Spotify (Luminous Emerald Green)
            CosmicPlanet(
                planet_id="music",
                name="Music / Spotify",
                commands=[["spotify"], ["google-chrome", "https://music.youtube.com"], ["xdg-open", "https://open.spotify.com"]],
                phase_index=3,
                base_radius=16.0,
                color=(0.15, 0.85, 0.45),
                glow=(0.25, 0.95, 0.55),
                icon_name="music"
            ),
            # 5. Files / Nautilus (Cupertino Royal Blue)
            CosmicPlanet(
                planet_id="files",
                name="Files (Nautilus)",
                commands=[["nautilus", os.path.expanduser("~")]],
                phase_index=4,
                base_radius=17.0,
                color=(0.22, 0.60, 0.98),
                glow=(0.30, 0.70, 1.0),
                icon_name="folder"
            ),
            # 6. System Settings (Space Gray / Titanium Silver)
            CosmicPlanet(
                planet_id="settings",
                name="System Settings",
                commands=[["gnome-control-center"]],
                phase_index=5,
                base_radius=14.0,
                color=(0.85, 0.90, 0.95),
                glow=(0.90, 0.95, 1.0),
                icon_name="settings"
            ),
        ]

        self.master_angle = 0.0
        self.base_speed = 0.22  # ~28.5 seconds per revolution
        self.orbit_a = 310.0

        # Twinkling stardust particles along the orbital ellipse
        self.stars = []
        for i in range(32):
            self.stars.append({
                "ang": (i / 32.0) * 2 * math.pi,
                "offset_r": (math.sin(i * 7) * 12.0),
                "size": 1.0 + (i % 3) * 0.5,
                "speed": 1.5 + (i % 4) * 0.8,
                "phase": (i * 1.3)
            })

        self.shockwaves = []
        self.hovered_planet = None

    def update(self, dt, cx, cy):
        """Advance harmonic celestial rotation and update physics."""
        # Slow down rotation smoothly when user hovers over a planet for easy clicking
        target_speed = 0.05 if self.hovered_planet else self.base_speed
        self.master_angle = (self.master_angle + target_speed * dt) % (2.0 * math.pi)

        for p in self.planets:
            p.update_position(self.master_angle, cx, cy, self.orbit_a, dt)

        # Update shockwaves
        self.shockwaves = [sw for sw in self.shockwaves if sw.step(dt)]

    def handle_mouse_move(self, mx, my):
        """Hit test planets for hover highlight and badge."""
        found = None
        # Test front planets first
        sorted_planets = sorted(self.planets, key=lambda p: p.z, reverse=True)
        for p in sorted_planets:
            if p.contains_point(mx, my):
                found = p
                break

        changed = False
        for p in self.planets:
            is_hov = (p == found)
            if p.hovered != is_hov:
                p.hovered = is_hov
                changed = True

        self.hovered_planet = found
        return changed

    def handle_click(self, mx, my):
        """Launch app and trigger cosmic shockwave ripple upon click."""
        if self.hovered_planet and self.hovered_planet.contains_point(mx, my):
            p = self.hovered_planet
            self.shockwaves.append(Shockwave(p.x, p.y, p.glow))
            p.launch()
            return True

        for p in sorted(self.planets, key=lambda p: p.z, reverse=True):
            if p.contains_point(mx, my):
                self.shockwaves.append(Shockwave(p.x, p.y, p.glow))
                p.launch()
                return True
        return False

    def draw_orbits(self, cr, cx, cy):
        """Draw ultra-refined celestial orbit line and twinkling stardust."""
        cr.save()
        center_y = cy + 18.0

        # Draw orbital elliptical trajectory path
        cr.new_sub_path()
        steps = 120
        for i in range(steps + 1):
            ang = (i / float(steps)) * 2.0 * math.pi
            ox = cx + self.orbit_a * math.cos(ang)
            sin_a = math.sin(ang)
            oy = center_y + (18.0 * sin_a if sin_a < 0 else 70.0 * sin_a)
            if i == 0:
                cr.move_to(ox, oy)
            else:
                cr.line_to(ox, oy)
        cr.close_path()
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.16)
        cr.set_line_width(0.9)
        cr.set_dash([4.0, 4.0])
        cr.stroke()

        # Draw twinkling stardust
        now = time.time()
        for s in self.stars:
            twinkle = 0.25 + 0.35 * math.sin(now * s["speed"] + s["phase"])
            ang = s["ang"]
            ox = cx + self.orbit_a * math.cos(ang) + s["offset_r"]
            sin_a = math.sin(ang)
            oy = center_y + (18.0 * sin_a if sin_a < 0 else 70.0 * sin_a)
            cr.new_sub_path()
            cr.arc(ox, oy, s["size"], 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 1.0, 1.0, twinkle)
            cr.fill()

        cr.restore()

    def draw_planets_back(self, cr):
        """Draw planets currently moving BEHIND the Dynamic Island (z < 0)."""
        back_planets = [p for p in self.planets if p.z < 0]
        back_planets.sort(key=lambda p: p.z)
        for p in back_planets:
            self._draw_single_planet(cr, p, is_front=False)

    def draw_planets_front(self, cr):
        """Draw planets currently moving IN FRONT OF the Dynamic Island (z >= 0)."""
        front_planets = [p for p in self.planets if p.z >= 0]
        front_planets.sort(key=lambda p: p.z)
        for p in front_planets:
            self._draw_single_planet(cr, p, is_front=True)

        # Draw shockwaves
        for sw in self.shockwaves:
            cr.save()
            cr.new_sub_path()
            cr.arc(sw.x, sw.y, sw.radius, 0, 2 * math.pi)
            cr.set_line_width(2.2 * sw.alpha)
            r, g, b = sw.color
            cr.set_source_rgba(r, g, b, sw.alpha)
            cr.stroke()
            cr.restore()

        # Draw hover badge on top
        if self.hovered_planet:
            self._draw_hover_badge(cr, self.hovered_planet)

    def _draw_single_planet(self, cr, p, is_front):
        cr.save()
        rad = p.base_radius * p.scale
        alpha_mult = 1.0 if is_front else 0.80

        # 1. Comet Tail (Fading stardust sparks trailing behind planet)
        center_y = p.y - (18.0 * p.z if p.z < 0 else 70.0 * p.z)
        orbit_cx = p.x - self.orbit_a * math.cos(p.angle)
        for t_step in range(1, 5):
            t_ang = p.angle - t_step * 0.08
            tx = orbit_cx + self.orbit_a * math.cos(t_ang)
            t_sin = math.sin(t_ang)
            ty = center_y + (18.0 * t_sin if t_sin < 0 else 70.0 * t_sin)
            t_size = max(0.8, (rad * 0.22) * (1.0 - t_step * 0.20))
            t_alpha = 0.45 * (1.0 - t_step * 0.22) * alpha_mult
            cr.new_sub_path()
            cr.arc(tx, ty, t_size, 0, 2 * math.pi)
            gr, gg, gb = p.glow
            cr.set_source_rgba(gr, gg, gb, t_alpha)
            cr.fill()

        # 2. Atmospheric Nebula Halo Glow
        glow_pat = cairo.RadialGradient(p.x, p.y, rad * 0.4, p.x, p.y, rad * 2.3)
        gr, gg, gb = p.glow
        glow_alpha = (0.55 if p.hovered else 0.28) * alpha_mult
        glow_pat.add_color_stop_rgba(0.0, gr, gg, gb, glow_alpha)
        glow_pat.add_color_stop_rgba(1.0, gr, gg, gb, 0.0)
        cr.set_source(glow_pat)
        cr.arc(p.x, p.y, rad * 2.3, 0, 2 * math.pi)
        cr.fill()

        # 3. Saturn Planetary Rings
        if p.has_rings:
            cr.save()
            cr.translate(p.x, p.y)
            cr.rotate(math.radians(-22.0))
            cr.scale(1.0, 0.34)
            cr.new_sub_path()
            cr.arc(0, 0, rad * 2.2, 0, 2 * math.pi)
            cr.set_line_width(2.8 * p.scale)
            cr.set_source_rgba(0.95, 0.85, 0.45, 0.75 * alpha_mult)
            cr.stroke()
            cr.restore()

        # 4. Liquid Glass Celestial Body
        body_pat = cairo.RadialGradient(
            p.x - rad * 0.35, p.y - rad * 0.35, rad * 0.05,
            p.x, p.y, rad
        )
        c = p.color
        body_pat.add_color_stop_rgba(0.0, c[0], c[1], c[2], 0.98 * alpha_mult)
        body_pat.add_color_stop_rgba(0.65, c[0] * 0.55, c[1] * 0.55, c[2] * 0.55, 0.98 * alpha_mult)
        body_pat.add_color_stop_rgba(1.0, 0.02, 0.04, 0.08, 0.98 * alpha_mult)
        cr.set_source(body_pat)
        cr.arc(p.x, p.y, rad, 0, 2 * math.pi)
        cr.fill()

        # 5. Soft Specular Sheen (Curved glass lens reflection)
        spec_pat = cairo.RadialGradient(
            p.x - rad * 0.35, p.y - rad * 0.35, 1.0,
            p.x - rad * 0.25, p.y - rad * 0.25, rad * 0.75
        )
        spec_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.85 * alpha_mult)
        spec_pat.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.20 * alpha_mult)
        spec_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(spec_pat)
        cr.arc(p.x, p.y, rad, 0, 2 * math.pi)
        cr.fill()

        # 6. Ultra-thin Specular Rim (0.9px crisp Apple glass edge)
        rim_pat = cairo.LinearGradient(p.x, p.y - rad, p.x, p.y + rad)
        rim_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.65 * alpha_mult)
        rim_pat.add_color_stop_rgba(0.5, c[0], c[1], c[2], 0.30 * alpha_mult)
        rim_pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.35 * alpha_mult)
        cr.set_source(rim_pat)
        cr.set_line_width(0.9)
        cr.arc(p.x, p.y, rad, 0, 2 * math.pi)
        cr.stroke()

        # 7. Authentic Embedded Vector Icon
        icon_size = max(11, int(rad * 1.05))
        pb = get_pixbuf(p.icon_name, icon_size, "#ffffff")
        if pb:
            cr.save()
            Gdk.cairo_set_source_pixbuf(cr, pb, p.x - icon_size / 2.0, p.y - icon_size / 2.0)
            cr.paint_with_alpha(0.95 * alpha_mult)
            cr.restore()

        cr.restore()

    def _draw_hover_badge(self, cr, p):
        """Draw an Apple-style floating frosted glass badge displaying the app name."""
        cr.save()
        badge_text = p.name
        cr.select_font_face("SF Pro Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(12.0)
        text_ext = cr.text_extents(badge_text)

        bw = text_ext.width + 24.0
        bh = 24.0
        bx = p.x - bw / 2.0
        by = p.y + (p.base_radius * p.scale) + 12.0

        # Pill rounded corners
        br = 12.0
        cr.new_sub_path()
        cr.arc(bx + bw - br, by + br, br, -math.pi / 2, 0)
        cr.arc(bx + bw - br, by + bh - br, br, 0, math.pi / 2)
        cr.arc(bx + br, by + bh - br, br, math.pi / 2, math.pi)
        cr.arc(bx + br, by + br, br, math.pi, 3 * math.pi / 2)
        cr.close_path()

        # Dark glassmorphic background
        cr.set_source_rgba(0.06, 0.10, 0.16, 0.94)
        cr.fill_preserve()

        # Crisp specular border
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.28)
        cr.set_line_width(0.8)
        cr.stroke()

        # Text label
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.98)
        cr.move_to(bx + 12.0, by + 16.5)
        cr.show_text(badge_text)

        cr.restore()
