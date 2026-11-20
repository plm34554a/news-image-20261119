#!/usr/bin/env python3
"""Sum up 19 November 2026's world news in one image.

Draws a 1024x1024 front-page newspaper collage. Pure Python standard
library only -- no Pillow, no system fonts, no network: the pixel
buffer, the shape rasterizers, the PNG encoder and the text renderer
are all implemented here, and the glyph coverage bitmaps come from
fontdata.py (an atlas generated from the DejaVu fonts by
tools/make_atlas.py). The output is deterministic: fixed pixels, no
timestamps, no randomness, no PNG metadata, so two runs produce
byte-identical files.

Usage: python3 main.py [output_path]
       (default: $MAKEFUN_OUTPUT_DIR/entry.png, else /output/entry.png)
"""

import base64
import os
import sys
import zlib
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontdata

# ---------------------------------------------------------------- fonts

FONTS = {}
for _face, _sizes in fontdata.DATA.items():
    for _size, _d in _sizes.items():
        FONTS[(_face, _size)] = (
            _d["ascent"],
            _d["descent"],
            zlib.decompress(base64.b64decode(_d["blob"])),
            _d["glyphs"],
        )

SERIF_BOLD = "serif_bold"
SANS_BOLD = "sans_bold"
SANS = "sans"


def font(face, size):
    return (face, size)


def text_width(text, fnt):
    glyphs = FONTS[fnt][3]
    total = 0.0
    for ch in text:
        g = glyphs.get(ch)
        if g is not None:
            total += g[0]
    return total


# ---------------------------------------------------------------- canvas

W = H = 1024
MARGIN = 24
CONTENT_W = W - 2 * MARGIN

PAPER = (247, 243, 232)
INK = (22, 22, 22)
RULE = (22, 22, 22)
WHITE = (255, 255, 255)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(color)

    def blend_px(self, x, y, color, alpha):
        if 0 <= x < self.w and 0 <= y < self.h and alpha:
            i = (y * self.w + x) * 3
            if alpha == 255:
                self.buf[i:i + 3] = bytes(color)
            else:
                inv = 255 - alpha
                self.buf[i] = (color[0] * alpha + self.buf[i] * inv) // 255
                self.buf[i + 1] = (color[1] * alpha + self.buf[i + 1] * inv) // 255
                self.buf[i + 2] = (color[2] * alpha + self.buf[i + 2] * inv) // 255

    def fill_span(self, y, xa, xb, color):
        if 0 <= y < self.h:
            xa = max(0, xa)
            xb = min(self.w - 1, xb)
            if xa <= xb:
                row = y * self.w * 3
                self.buf[row + xa * 3:row + (xb + 1) * 3] = \
                    bytes(color) * (xb - xa + 1)


def _ceil(v):
    i = int(v)
    return i if v <= i else i + 1


def _floor(v):
    i = int(v)
    return i if v >= i else i - 1


# ---------------------------------------------------------------- shapes

def fill_rect(cv, x0, y0, x1, y1, color):
    for y in range(max(0, y0), min(cv.h - 1, y1) + 1):
        cv.fill_span(y, x0, x1, color)


def rectangle(cv, box, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    if fill is not None:
        fill_rect(cv, x0, y0, x1, y1, fill)
    if outline is not None and width > 0:
        fill_rect(cv, x0, y0, x1, y0 + width - 1, outline)
        fill_rect(cv, x0, y1 - width + 1, x1, y1, outline)
        fill_rect(cv, x0, y0, x0 + width - 1, y1, outline)
        fill_rect(cv, x1 - width + 1, y0, x1, y1, outline)


def _rounded_fill(cv, x0, y0, x1, y1, radius, color):
    if x1 < x0 or y1 < y0:
        return
    radius = max(0, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
    for y in range(max(0, y0), min(cv.h - 1, y1) + 1):
        yc = y + 0.5
        if yc < y0 + radius:
            dy = (y0 + radius) - yc
        elif yc > y1 - radius + 1:
            dy = yc - (y1 - radius + 1)
        else:
            dy = 0.0
        if dy > 0.0:
            dx = (radius * radius - dy * dy) ** 0.5
            left = x0 + radius - dx
            right = x1 - radius + dx + 1
        else:
            left = float(x0)
            right = float(x1 + 1)
        cv.fill_span(y, _ceil(left - 0.5), _floor(right - 0.5), color)


def rounded_rectangle(cv, box, radius, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    if fill is not None and outline is not None and width > 0:
        _rounded_fill(cv, x0, y0, x1, y1, radius, outline)
        _rounded_fill(cv, x0 + width, y0 + width, x1 - width, y1 - width,
                      radius - width, fill)
    elif fill is not None:
        _rounded_fill(cv, x0, y0, x1, y1, radius, fill)
    elif outline is not None:
        _rounded_fill(cv, x0, y0, x1, y1, radius, outline)


def stamp(cv, px, py, r, color):
    if r <= 0.75:
        cv.set_px(int(px), int(py), color)
        return
    r2 = r * r + 0.25
    for yy in range(int(py - r - 1), int(py + r + 1) + 1):
        for xx in range(int(px - r - 1), int(px + r + 1) + 1):
            ddx = xx + 0.5 - px
            ddy = yy + 0.5 - py
            if ddx * ddx + ddy * ddy <= r2:
                cv.set_px(xx, yy, color)


def line(cv, points, fill, width=1):
    r = width / 2.0
    for i in range(len(points) - 1):
        xa, ya = points[i]
        xb, yb = points[i + 1]
        if ya == yb:
            # axis-aligned: Pillow fills a rectangle whose span starts
            # (width - 1) // 2 rows above the line's y
            y0 = int(ya) - (width - 1) // 2
            fill_rect(cv, int(round(min(xa, xb))), y0,
                      int(round(max(xa, xb))), y0 + width - 1, fill)
        elif xa == xb:
            x0 = int(xa) - (width - 1) // 2
            fill_rect(cv, x0, int(round(min(ya, yb))),
                      x0 + width - 1, int(round(max(ya, yb))), fill)
        else:
            steps = int(max(abs(xb - xa), abs(yb - ya)) / 0.4) + 1
            for s in range(steps + 1):
                t = s / steps
                stamp(cv, xa + (xb - xa) * t, ya + (yb - ya) * t, r, fill)


def _ellipse_fill(cv, box, color):
    x0, y0, x1, y1 = (float(v) for v in box)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    if rx <= 0 or ry <= 0:
        return
    for y in range(max(0, int(y0)), min(cv.h - 1, int(y1) + 1) + 1):
        dy = (y + 0.5 - cy) / ry
        if -1.0 < dy < 1.0:
            dx = rx * (1.0 - dy * dy) ** 0.5
            cv.fill_span(y, _ceil(cx - dx - 0.5), _floor(cx + dx - 0.5), color)


def ellipse(cv, box, fill=None, outline=None, width=1):
    if fill is not None and outline is not None and width > 0:
        _ellipse_fill(cv, box, outline)
        inner = [box[0] + width, box[1] + width,
                 box[2] - width, box[3] - width]
        _ellipse_fill(cv, inner, fill)
    elif fill is not None:
        _ellipse_fill(cv, box, fill)
    elif outline is not None:
        _ellipse_fill(cv, box, outline)


_PI = 3.141592653589793


def _sin(x):
    x = x % (2.0 * _PI)
    if x > _PI:
        x -= 2.0 * _PI
    term = x
    total = x
    x2 = x * x
    for n in range(1, 13):
        term *= -x2 / ((2 * n) * (2 * n + 1))
        total += term
    return total


def _cos(x):
    x = x % (2.0 * _PI)
    if x > _PI:
        x -= 2.0 * _PI
    term = 1.0
    total = 1.0
    x2 = x * x
    for n in range(1, 13):
        term *= -x2 / ((2 * n - 1) * (2 * n))
        total += term
    return total


def arc(cv, box, start, end, fill, width=1):
    x0, y0, x1, y1 = (float(v) for v in box)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    if rx <= 0 or ry <= 0:
        return
    while end < start:
        end += 360.0
    sweep = end - start
    steps = int(sweep * max(rx, ry) * 0.035) + 2
    r = width / 2.0
    for i in range(steps + 1):
        t = (start + sweep * i / steps) * _PI / 180.0
        stamp(cv, cx + rx * _cos(t), cy + ry * _sin(t), r, fill)


def polygon(cv, points, fill=None, outline=None, width=1):
    if fill is not None:
        ys = [p[1] for p in points]
        n = len(points)
        for y in range(max(0, int(min(ys))), min(cv.h - 1, int(max(ys))) + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                xa, ya = points[i]
                xb, yb = points[(i + 1) % n]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                cv.fill_span(y, _ceil(xs[i] - 0.5), _floor(xs[i + 1] - 0.5),
                             fill)
    if outline is not None:
        line(cv, list(points) + [points[0]], outline, width)


# ---------------------------------------------------------------- text

def draw_text(cv, x, y, text, fnt, fill):
    _asc, _desc, raw, glyphs = FONTS[fnt]
    pen = float(x)
    gy_base = int(round(y))
    for ch in text:
        g = glyphs.get(ch)
        if g is None:
            continue
        adv, dx, dy, w, h, off, ln = g
        if ln:
            gx = int(round(pen)) + dx
            gy = gy_base + dy
            for row in range(h):
                yy = gy + row
                if 0 <= yy < cv.h:
                    src = off + row * w
                    for col in range(w):
                        a = raw[src + col]
                        if a:
                            cv.blend_px(gx + col, yy, fill, a)
        pen += adv


def wrap(text, fnt, max_width):
    """Split text into lines that fit max_width."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if text_width(trial, fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(cv, x, y, text, fnt, fill, max_width, line_gap=4):
    """Draw wrapped text at (x, y); return the y just below it."""
    ascent, descent = FONTS[fnt][0], FONTS[fnt][1]
    step = ascent + descent + line_gap
    for ln in wrap(text, fnt, max_width):
        draw_text(cv, x, y, ln, fnt, fill)
        y += step
    return y


def panel(cv, box, fill, outline=INK, width=2):
    rounded_rectangle(cv, box, 10, fill=fill, outline=outline, width=width)


def kicker(cv, x, y, text, color):
    draw_text(cv, x, y, text, font(SANS_BOLD, 15), color)
    return y + 22


# ---------------------------------------------------------------- icons

def icon_court(cv, cx, cy):
    """Courthouse columns with scales of justice in front."""
    # pediment
    polygon(cv, [(cx - 62, cy - 58), (cx + 62, cy - 58), (cx, cy - 88)],
            fill=(38, 58, 99))
    rectangle(cv, [cx - 68, cy - 54, cx + 68, cy - 44], fill=(38, 58, 99))
    # columns
    for dx in (-52, -26, 0, 26, 52):
        rectangle(cv, [cx + dx - 7, cy - 40, cx + dx + 7, cy + 38],
                  fill=(226, 222, 208), outline=INK, width=2)
    rectangle(cv, [cx - 68, cy + 42, cx + 68, cy + 54], fill=(38, 58, 99))
    # scales: beam, post and two pans
    line(cv, [(cx - 44, cy - 6), (cx + 44, cy - 6)], (176, 32, 40), width=5)
    line(cv, [(cx, cy - 30), (cx, cy + 30)], (176, 32, 40), width=5)
    ellipse(cv, [cx - 7, cy - 37, cx + 7, cy - 23], fill=(176, 32, 40))
    for sx in (-44, 44):
        line(cv, [(sx + cx, cy - 6), (sx + cx - 14, cy + 20)],
             (176, 32, 40), width=3)
        line(cv, [(sx + cx, cy - 6), (sx + cx + 14, cy + 20)],
             (176, 32, 40), width=3)
        arc(cv, [sx + cx - 17, cy + 8, sx + cx + 17, cy + 34], 0, 180,
            (176, 32, 40), width=4)


def icon_flags(cv, x, y):
    """Three flags -- USA, Russia, China -- above a summit table."""
    fw, fh = 72, 42
    for i in range(3):
        line(cv, [(x + 36 + i * 84, y - 8), (x + 36 + i * 84, y + fh + 14)],
             INK, width=3)
    # USA: stripes + blue canton
    ux, uy = x, y
    for i in range(6):
        rectangle(cv, [ux, uy + i * 8, ux + fw, uy + i * 8 + 8],
                  fill=(176, 32, 40) if i % 2 == 0 else WHITE, outline=INK)
    rectangle(cv, [ux, uy, ux + 32, uy + 24], fill=(38, 58, 99))
    for r in range(3):
        for c in range(4):
            ellipse(cv, [ux + 4 + c * 7, uy + 4 + r * 7,
                         ux + 7 + c * 7, uy + 7 + r * 7], fill=WHITE)
    # Russia: white / blue / red bands
    rx = x + 84
    for i, col in enumerate([WHITE, (38, 84, 168), (176, 32, 40)]):
        rectangle(cv, [rx, y + i * 16, rx + fw, y + i * 16 + 16],
                  fill=col, outline=INK)
    # China: red with yellow stars
    cx0 = x + 168
    rectangle(cv, [cx0, y, cx0 + fw, y + fh], fill=(196, 24, 32), outline=INK)
    ellipse(cv, [cx0 + 8, y + 8, cx0 + 22, y + 22], fill=(250, 205, 40))
    for dx, dy in ((30, 6), (36, 14), (36, 24), (30, 32)):
        ellipse(cv, [cx0 + dx, y + dy, cx0 + dx + 7, y + dy + 7],
                fill=(250, 205, 40))
    # summit table
    rectangle(cv, [x + 8, y + fh + 10, x + 232, y + fh + 20],
              fill=(110, 72, 38))
    rectangle(cv, [x + 28, y + fh + 20, x + 40, y + fh + 32],
              fill=(110, 72, 38))
    rectangle(cv, [x + 200, y + fh + 20, x + 212, y + fh + 32],
              fill=(110, 72, 38))


def icon_climate(cv, cx, cy):
    """Sun and globe with a thermometer (compact: fits a 76px band)."""
    # sun rays behind (side and lower rays only: the headline sits above)
    for dx, dy in ((-50, 0), (42, 42), (0, 50), (-42, 42)):
        line(cv, [(cx + dx, cy + dy), (cx + dx * 1.22, cy + dy * 1.22)],
             (232, 150, 20), width=5)
    # globe
    r = 32
    ellipse(cv, [cx - r, cy - r, cx + r, cy + r], fill=(64, 140, 200),
            outline=INK, width=2)
    polygon(cv, [(cx - 24, cy - 13), (cx - 7, cy - 23), (cx - 3, cy - 5),
                 (cx - 16, cy + 4)], fill=(62, 160, 84))
    polygon(cv, [(cx + 5, cy + 7), (cx + 23, cy + 1), (cx + 25, cy + 19),
                 (cx + 9, cy + 24)], fill=(62, 160, 84))
    # thermometer
    tx = cx + 48
    rounded_rectangle(cv, [tx - 7, cy - 36, tx + 7, cy + 16], 7, fill=WHITE,
                      outline=INK, width=2)
    rectangle(cv, [tx - 3, cy - 6, tx + 3, cy + 16], fill=(196, 24, 32))
    ellipse(cv, [tx - 12, cy + 10, tx + 12, cy + 32], fill=(196, 24, 32),
            outline=INK, width=2)
    for i in range(3):
        line(cv, [(tx + 9, cy - 28 + i * 14), (tx + 17, cy - 28 + i * 14)],
             INK, width=2)


def icon_vangogh(cv, x, y, w, h):
    """Swirly starry-night motif, drawn to fit the (w, h) box given."""
    rectangle(cv, [x, y, x + w, y + h], fill=(24, 32, 92), outline=INK,
              width=2)
    cy = y + h // 2
    # spiral swirls
    for cx, r in ((x + 62, 20), (x + 150, 14), (x + 226, 17)):
        for k in range(3):
            arc(cv, [cx - r + k * 5, cy - r + k * 5,
                     cx + r - k * 5, cy + r - k * 5],
                20, 320, (140, 180, 235), width=3)
    # stars
    for cx, sy in ((x + 26, y + 14), (x + 196, y + 12),
                   (x + 292, y + h - 14), (x + 104, y + h - 12)):
        ellipse(cv, [cx - 7, sy - 7, cx + 7, sy + 7], fill=(250, 214, 80))
        ellipse(cv, [cx - 3, sy - 3, cx + 3, sy + 3], fill=(255, 240, 170))
    # crescent moon
    ellipse(cv, [x + w - 40, y + 6, x + w - 12, y + 34], fill=(250, 214, 80))
    ellipse(cv, [x + w - 33, y + 4, x + w - 7, y + 30], fill=(24, 32, 92))
    # rolling hills along the bottom edge
    arc(cv, [x - 20, y + h - 30, x + w * 0.7, y + h + 16], 180, 360,
        (70, 110, 70), width=5)
    arc(cv, [x + w * 0.3, y + h - 24, x + w + 20, y + h + 18], 180, 360,
        (70, 110, 70), width=5)


def icon_baseball(cv, cx, cy, r):
    """A baseball with red stitching."""
    ellipse(cv, [cx - r, cy - r, cx + r, cy + r], fill=WHITE, outline=INK,
            width=3)
    arc(cv, [cx - r - 18, cy - r, cx + 6, cy + r], 300, 60, (196, 24, 32),
        width=4)
    arc(cv, [cx - 6, cy - r, cx + r + 18, cy + r], 120, 240, (196, 24, 32),
        width=4)
    for t in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = cy + int(t * r * 1.4)
        line(cv, [(cx - r * 0.52, yy - 5), (cx - r * 0.34, yy + 5)],
             (196, 24, 32), width=3)
        line(cv, [(cx + r * 0.52, yy - 5), (cx + r * 0.34, yy + 5)],
             (196, 24, 32), width=3)


def icon_tanker(cv, x, y):
    """An oil tanker sailing through a strait."""
    # strait banks
    polygon(cv, [(x, y + 78), (x + 70, y + 52), (x + 120, y + 78)],
            fill=(198, 168, 104))
    polygon(cv, [(x + 300, y + 78), (x + 230, y + 52), (x + 180, y + 78)],
            fill=(198, 168, 104))
    # hull
    polygon(cv, [(x + 52, y + 34), (x + 248, y + 34), (x + 232, y + 62),
                 (x + 72, y + 62)], fill=(176, 32, 40), outline=INK, width=2)
    # deck, tanks and bridge
    rectangle(cv, [x + 66, y + 22, x + 196, y + 34], fill=(90, 90, 90))
    for i in range(3):
        rectangle(cv, [x + 76 + i * 40, y + 8, x + 106 + i * 40, y + 22],
                  fill=(220, 220, 220), outline=INK, width=2)
    rectangle(cv, [x + 204, y + 2, x + 234, y + 34], fill=(240, 240, 240),
              outline=INK, width=2)
    rectangle(cv, [x + 210, y + 8, x + 228, y + 16], fill=(64, 140, 200))
    # waves
    for i in range(6):
        wx = x + 26 + i * 44
        arc(cv, [wx, y + 66, wx + 34, y + 84], 0, 180, (64, 140, 200),
            width=3)


# ---------------------------------------------------------------- sections

def masthead(cv):
    title = "THE WORLD IN ONE DAY"
    f = font(SERIF_BOLD, 52)
    draw_text(cv, (W - text_width(title, f)) / 2, 20, title, f, INK)
    line(cv, [(MARGIN, 88), (W - MARGIN, 88)], RULE, width=4)
    line(cv, [(MARGIN, 94), (W - MARGIN, 94)], RULE, width=1)
    date = "THURSDAY 19 NOVEMBER 2026"
    f = font(SANS_BOLD, 43)
    draw_text(cv, (W - text_width(date, f)) / 2, 102, date, f, (150, 20, 28))
    sub = "THE WHOLE PLANET'S FRONT PAGE  •  ALL THE NEWS THAT MATTERED, IN ONE PICTURE"
    f = font(SANS_BOLD, 16)
    draw_text(cv, (W - text_width(sub, f)) / 2, 152, sub, f, INK)
    line(cv, [(MARGIN, 178), (W - MARGIN, 178)], RULE, width=3)


def top_story(cv):
    box = [MARGIN, 186, W - MARGIN, 362]
    panel(cv, box, (252, 248, 236), width=3)
    icon_court(cv, 118, 278)
    x = 208
    y = kicker(cv, x, 196, "★ TOP STORY — THE HAGUE", (150, 20, 28))
    y = text_block(cv, x, y,
                   "WORLD COURT: MYANMAR COMMITTED GENOCIDE AGAINST THE ROHINGYA",
                   font(SANS_BOLD, 31), INK, W - MARGIN - x - 16, line_gap=5)
    text_block(cv, x, y + 8,
               "The International Court of Justice rules in Gambia v. Myanmar — "
               "a landmark 9–6 vote at The Hague.",
               font(SANS, 19), (60, 60, 60), W - MARGIN - x - 16, line_gap=4)


def summit_panel(cv, box):
    panel(cv, box, (238, 244, 252))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(cv, x, y, "APEC • SHENZHEN, CHINA", (38, 58, 99))
    y = text_block(cv, x, y, "TRUMP, PUTIN & XI MEET IN SHENZHEN",
                   font(SANS_BOLD, 25), INK, box[2] - x - 16, line_gap=4)
    icon_flags(cv, box[0] + 106, y + 6)
    text_block(cv, box[0] + 16, box[3] - 54,
               "Trilateral summit signs a “Declaration Toward Peace”; Ukraine dominates the talks.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 32, line_gap=3)


def climate_panel(cv, box):
    panel(cv, box, (240, 248, 238))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(cv, x, y, "CLIMATE • TÜRKIYE", (30, 110, 60))
    y = text_block(cv, x, y, "COP31: MINISTERS RACE TO UNBLOCK TALKS IN ANTALYA",
                   font(SANS_BOLD, 24), INK, box[2] - x - 16, line_gap=4)
    icon_climate(cv, box[0] + 218, y + 30)
    text_block(cv, box[0] + 16, box[3] - 32,
               "Negotiators scramble to save the climate deal.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 32, line_gap=3)


def vangogh_panel(cv, box):
    panel(cv, box, (246, 242, 228))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(cv, x, y, "ART • AUCTION RECORD", (120, 84, 10))
    y = text_block(cv, x, y, "VAN GOGH SELLS FOR $190.4M — AN ARTIST RECORD",
                   font(SANS_BOLD, 24), INK, box[2] - x - 16, line_gap=4)
    icon_vangogh(cv, box[0] + 80, y + 8, 320, 60)


def rose_panel(cv, box):
    panel(cv, box, (252, 240, 238))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(cv, x, y, "BASEBALL • WASHINGTON", (150, 20, 28))
    y = text_block(cv, x, y, "TRUMP PARDONS PETE ROSE",
                   font(SANS_BOLD, 25), INK, box[2] - x - 16, line_gap=4)
    icon_baseball(cv, box[0] + 92, y + 52, 36)
    text_block(cv, box[0] + 150, y + 30,
               "A posthumous pardon for the baseball legend.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 166, line_gap=3)


def senate_hormuz_panel(cv, box):
    panel(cv, box, (238, 240, 246), width=3)
    x, y = box[0] + 16, box[1] + 12
    y = kicker(cv, x, y, "WASHINGTON • THE GULF", (38, 58, 99))
    y = text_block(cv, x, y, "SENATE REJECTS IRAN WAR-POWERS BILL 51–48",
                   font(SANS_BOLD, 22), INK, 620, line_gap=4)
    text_block(cv, x, y + 4, "HORMUZ CRISIS: IEA WARNS ON ENERGY SECURITY",
               font(SANS_BOLD, 20), (150, 20, 28), 612, line_gap=3)
    icon_tanker(cv, box[0] + 640, box[1] + 20)


def briefs_strip(cv):
    box = [MARGIN, 924, W - MARGIN, 1008]
    panel(cv, box, (30, 30, 34), width=2)
    items = [
        "EU PROPOSES €45BN LOAN FOR UKRAINE",
        "BANGLADESH: VIOLENCE IN 28 DISTRICTS",
        "BUKELE SEEKS THIRD TERM IN EL SALVADOR",
        "FIONA THE HIPPO DIES AT CINCINNATI ZOO",
    ]
    f = font(SANS_BOLD, 16)
    col_w = (CONTENT_W - 32) // 2
    for i, item in enumerate(items):
        x = MARGIN + 16 + (i % 2) * col_w
        y = box[1] + 12 + (i // 2) * 38
        ellipse(cv, [x, y + 5, x + 9, y + 14], fill=(250, 205, 40))
        text_block(cv, x + 16, y, item, f, WHITE, col_w - 22, line_gap=2)


# ---------------------------------------------------------------- PNG out

def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _filter_row(kind, row, prev):
    """PNG-filter one scanline (bytes, no filter byte). Kinds 0/1/2."""
    if kind == 0:
        return row
    out = bytearray(len(row))
    if kind == 1:  # Sub
        for i, v in enumerate(row):
            left = row[i - 3] if i >= 3 else 0
            out[i] = (v - left) & 0xFF
    else:  # Up
        for i, v in enumerate(row):
            up = prev[i] if prev is not None else 0
            out[i] = (v - up) & 0xFF
    return bytes(out)


def _filter_score(filtered):
    total = 0
    for v in filtered:
        total += v if v < 128 else 256 - v
    return total


def write_png(path, cv):
    stride = cv.w * 3
    raw = bytearray()
    prev = None
    for y in range(cv.h):
        row = bytes(cv.buf[y * stride:(y + 1) * stride])
        best_kind, best = 0, None
        for kind in (0, 1, 2):
            cand = _filter_row(kind, row, prev)
            score = _filter_score(cand)
            if best is None or score < best[0]:
                best_kind, best = kind, (score, cand)
        raw.append(best_kind)
        raw += best[1]
        prev = row
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


# ---------------------------------------------------------------- main

def build():
    cv = Canvas(W, H, PAPER)

    masthead(cv)
    top_story(cv)

    # middle grid: two columns
    gap = 16
    col_w = (CONTENT_W - gap) // 2
    left_x, right_x = MARGIN, MARGIN + col_w + gap
    summit_panel(cv, [left_x, 372, left_x + col_w, 604])
    climate_panel(cv, [right_x, 372, right_x + col_w, 604])
    vangogh_panel(cv, [left_x, 614, left_x + col_w, 790])
    rose_panel(cv, [right_x, 614, right_x + col_w, 790])

    senate_hormuz_panel(cv, [MARGIN, 800, W - MARGIN, 916])
    briefs_strip(cv)
    return cv


def main(argv):
    if len(argv) > 1:
        out = argv[1]
    elif os.environ.get("MAKEFUN_OUTPUT_DIR"):
        out = os.path.join(os.environ["MAKEFUN_OUTPUT_DIR"], "entry.png")
    else:
        out = "/output/entry.png"
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    # Pixels only, no metadata chunks: repeated runs are byte-identical.
    write_png(out, build())
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv)
