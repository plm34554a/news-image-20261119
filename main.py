#!/usr/bin/env python3
"""Sum up 19 November 2026's world news in one image.

Draws a 1024x1024 front-page newspaper collage with Pillow only --
no external image files, no network. The output is deterministic:
fixed pixels, no timestamps, no randomness, no PNG metadata, so two
runs produce byte-identical files.

Usage: python3 main.py [output_path]   (default /output/entry.png)
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- constants

W = H = 1024
MARGIN = 24
CONTENT_W = W - 2 * MARGIN

PAPER = (247, 243, 232)
INK = (22, 22, 22)
RULE = (22, 22, 22)
WHITE = (255, 255, 255)

SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- helpers

def wrap(draw, text, fnt, max_width):
    """Split text into lines that fit max_width."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, x, y, text, fnt, fill, max_width, line_gap=4):
    """Draw wrapped text at (x, y); return the y just below it."""
    ascent, descent = fnt.getmetrics()
    step = ascent + descent + line_gap
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += step
    return y


def panel(draw, box, fill, outline=INK, width=2):
    draw.rounded_rectangle(box, radius=10, fill=fill, outline=outline, width=width)


def kicker(draw, x, y, text, color):
    draw.text((x, y), text, font=font(SANS_BOLD, 15), fill=color)
    return y + 22


# ---------------------------------------------------------------- icons

def icon_court(draw, cx, cy):
    """Courthouse columns with scales of justice in front."""
    # pediment
    draw.polygon([(cx - 62, cy - 58), (cx + 62, cy - 58), (cx, cy - 88)], fill=(38, 58, 99))
    draw.rectangle([cx - 68, cy - 54, cx + 68, cy - 44], fill=(38, 58, 99))
    # columns
    for dx in (-52, -26, 0, 26, 52):
        draw.rectangle([cx + dx - 7, cy - 40, cx + dx + 7, cy + 38], fill=(226, 222, 208), outline=INK, width=2)
    draw.rectangle([cx - 68, cy + 42, cx + 68, cy + 54], fill=(38, 58, 99))
    # scales: beam, post and two pans
    draw.line([cx - 44, cy - 6, cx + 44, cy - 6], fill=(176, 32, 40), width=5)
    draw.line([cx, cy - 30, cx, cy + 30], fill=(176, 32, 40), width=5)
    draw.ellipse([cx - 7, cy - 37, cx + 7, cy - 23], fill=(176, 32, 40))
    for sx in (-44, 44):
        draw.line([sx + cx, cy - 6, sx + cx - 14, cy + 20], fill=(176, 32, 40), width=3)
        draw.line([sx + cx, cy - 6, sx + cx + 14, cy + 20], fill=(176, 32, 40), width=3)
        draw.arc([sx + cx - 17, cy + 8, sx + cx + 17, cy + 34], 0, 180, fill=(176, 32, 40), width=4)


def icon_flags(draw, x, y):
    """Three flags -- USA, Russia, China -- above a summit table."""
    fw, fh = 72, 42
    for i in range(3):
        draw.line([x + 36 + i * 84, y - 8, x + 36 + i * 84, y + fh + 14], fill=INK, width=3)
    # USA: stripes + blue canton
    ux, uy = x, y
    for i in range(6):
        draw.rectangle([ux, uy + i * 8, ux + fw, uy + i * 8 + 8],
                       fill=(176, 32, 40) if i % 2 == 0 else WHITE, outline=INK)
    draw.rectangle([ux, uy, ux + 32, uy + 24], fill=(38, 58, 99))
    for r in range(3):
        for c in range(4):
            draw.ellipse([ux + 4 + c * 7, uy + 4 + r * 7, ux + 7 + c * 7, uy + 7 + r * 7], fill=WHITE)
    # Russia: white / blue / red bands
    rx = x + 84
    for i, col in enumerate([WHITE, (38, 84, 168), (176, 32, 40)]):
        draw.rectangle([rx, y + i * 16, rx + fw, y + i * 16 + 16], fill=col, outline=INK)
    # China: red with yellow stars
    cx0 = x + 168
    draw.rectangle([cx0, y, cx0 + fw, y + fh], fill=(196, 24, 32), outline=INK)
    draw.ellipse([cx0 + 8, y + 8, cx0 + 22, y + 22], fill=(250, 205, 40))
    for dx, dy in ((30, 6), (36, 14), (36, 24), (30, 32)):
        draw.ellipse([cx0 + dx, y + dy, cx0 + dx + 7, y + dy + 7], fill=(250, 205, 40))
    # summit table
    draw.rectangle([x + 8, y + fh + 10, x + 232, y + fh + 20], fill=(110, 72, 38))
    draw.rectangle([x + 28, y + fh + 20, x + 40, y + fh + 32], fill=(110, 72, 38))
    draw.rectangle([x + 200, y + fh + 20, x + 212, y + fh + 32], fill=(110, 72, 38))


def icon_climate(draw, cx, cy):
    """Sun and globe with a thermometer (compact: fits a 76px band)."""
    # sun rays behind (side and lower rays only: the headline sits above)
    for dx, dy in ((-50, 0), (42, 42), (0, 50), (-42, 42)):
        draw.line([cx + dx, cy + dy, cx + dx * 1.22, cy + dy * 1.22], fill=(232, 150, 20), width=5)
    # globe
    r = 32
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(64, 140, 200), outline=INK, width=2)
    draw.polygon([(cx - 24, cy - 13), (cx - 7, cy - 23), (cx - 3, cy - 5), (cx - 16, cy + 4)],
                 fill=(62, 160, 84))
    draw.polygon([(cx + 5, cy + 7), (cx + 23, cy + 1), (cx + 25, cy + 19), (cx + 9, cy + 24)],
                 fill=(62, 160, 84))
    # thermometer
    tx = cx + 48
    draw.rounded_rectangle([tx - 7, cy - 36, tx + 7, cy + 16], radius=7, fill=WHITE, outline=INK, width=2)
    draw.rectangle([tx - 3, cy - 6, tx + 3, cy + 16], fill=(196, 24, 32))
    draw.ellipse([tx - 12, cy + 10, tx + 12, cy + 32], fill=(196, 24, 32), outline=INK, width=2)
    for i in range(3):
        draw.line([tx + 9, cy - 28 + i * 14, tx + 17, cy - 28 + i * 14], fill=INK, width=2)


def icon_vangogh(draw, x, y, w, h):
    """Swirly starry-night motif, drawn to fit the (w, h) box given."""
    draw.rectangle([x, y, x + w, y + h], fill=(24, 32, 92), outline=INK, width=2)
    cy = y + h // 2
    # spiral swirls
    for cx, r in ((x + 62, 20), (x + 150, 14), (x + 226, 17)):
        for k in range(3):
            draw.arc([cx - r + k * 5, cy - r + k * 5, cx + r - k * 5, cy + r - k * 5],
                     20, 320, fill=(140, 180, 235), width=3)
    # stars
    for cx, sy in ((x + 26, y + 14), (x + 196, y + 12), (x + 292, y + h - 14), (x + 104, y + h - 12)):
        draw.ellipse([cx - 7, sy - 7, cx + 7, sy + 7], fill=(250, 214, 80))
        draw.ellipse([cx - 3, sy - 3, cx + 3, sy + 3], fill=(255, 240, 170))
    # crescent moon
    draw.ellipse([x + w - 40, y + 6, x + w - 12, y + 34], fill=(250, 214, 80))
    draw.ellipse([x + w - 33, y + 4, x + w - 7, y + 30], fill=(24, 32, 92))
    # rolling hills along the bottom edge
    draw.arc([x - 20, y + h - 30, x + w * 0.7, y + h + 16], 180, 360, fill=(70, 110, 70), width=5)
    draw.arc([x + w * 0.3, y + h - 24, x + w + 20, y + h + 18], 180, 360, fill=(70, 110, 70), width=5)


def icon_baseball(draw, cx, cy, r):
    """A baseball with red stitching."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE, outline=INK, width=3)
    draw.arc([cx - r - 18, cy - r, cx + 6, cy + r], 300, 60, fill=(196, 24, 32), width=4)
    draw.arc([cx - 6, cy - r, cx + r + 18, cy + r], 120, 240, fill=(196, 24, 32), width=4)
    for t in (-0.6, -0.3, 0.0, 0.3, 0.6):
        yy = cy + int(t * r * 1.4)
        draw.line([cx - r * 0.52, yy - 5, cx - r * 0.34, yy + 5], fill=(196, 24, 32), width=3)
        draw.line([cx + r * 0.52, yy - 5, cx + r * 0.34, yy + 5], fill=(196, 24, 32), width=3)


def icon_tanker(draw, x, y):
    """An oil tanker sailing through a strait."""
    # strait banks
    draw.polygon([(x, y + 78), (x + 70, y + 52), (x + 120, y + 78)], fill=(198, 168, 104))
    draw.polygon([(x + 300, y + 78), (x + 230, y + 52), (x + 180, y + 78)], fill=(198, 168, 104))
    # hull
    draw.polygon([(x + 52, y + 34), (x + 248, y + 34), (x + 232, y + 62), (x + 72, y + 62)],
                 fill=(176, 32, 40), outline=INK, width=2)
    # deck, tanks and bridge
    draw.rectangle([x + 66, y + 22, x + 196, y + 34], fill=(90, 90, 90))
    for i in range(3):
        draw.rectangle([x + 76 + i * 40, y + 8, x + 106 + i * 40, y + 22], fill=(220, 220, 220), outline=INK, width=2)
    draw.rectangle([x + 204, y + 2, x + 234, y + 34], fill=(240, 240, 240), outline=INK, width=2)
    draw.rectangle([x + 210, y + 8, x + 228, y + 16], fill=(64, 140, 200))
    # waves
    for i in range(6):
        wx = x + 26 + i * 44
        draw.arc([wx, y + 66, wx + 34, y + 84], 0, 180, fill=(64, 140, 200), width=3)


# ---------------------------------------------------------------- sections

def masthead(draw):
    draw.rectangle([0, 0, W, H], fill=PAPER)
    title = "THE WORLD IN ONE DAY"
    f = font(SERIF_BOLD, 52)
    draw.text(((W - draw.textlength(title, font=f)) / 2, 20), title, font=f, fill=INK)
    draw.line([MARGIN, 88, W - MARGIN, 88], fill=RULE, width=4)
    draw.line([MARGIN, 94, W - MARGIN, 94], fill=RULE, width=1)
    date = "THURSDAY 19 NOVEMBER 2026"
    f = font(SANS_BOLD, 43)
    draw.text(((W - draw.textlength(date, font=f)) / 2, 102), date, font=f, fill=(150, 20, 28))
    sub = "THE WHOLE PLANET'S FRONT PAGE  •  ALL THE NEWS THAT MATTERED, IN ONE PICTURE"
    f = font(SANS_BOLD, 16)
    draw.text(((W - draw.textlength(sub, font=f)) / 2, 152), sub, font=f, fill=INK)
    draw.line([MARGIN, 178, W - MARGIN, 178], fill=RULE, width=3)


def top_story(draw):
    box = [MARGIN, 186, W - MARGIN, 362]
    panel(draw, box, (252, 248, 236), width=3)
    icon_court(draw, 118, 278)
    x = 208
    y = kicker(draw, x, 196, "★ TOP STORY — THE HAGUE", (150, 20, 28))
    y = text_block(draw, x, y,
                   "WORLD COURT: MYANMAR COMMITTED GENOCIDE AGAINST THE ROHINGYA",
                   font(SANS_BOLD, 31), INK, W - MARGIN - x - 16, line_gap=5)
    text_block(draw, x, y + 8,
               "The International Court of Justice rules in Gambia v. Myanmar — "
               "a landmark 9–6 vote at The Hague.",
               font(SANS, 19), (60, 60, 60), W - MARGIN - x - 16, line_gap=4)


def summit_panel(draw, box):
    panel(draw, box, (238, 244, 252))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(draw, x, y, "APEC • SHENZHEN, CHINA", (38, 58, 99))
    y = text_block(draw, x, y, "TRUMP, PUTIN & XI MEET IN SHENZHEN",
                   font(SANS_BOLD, 25), INK, box[2] - x - 16, line_gap=4)
    icon_flags(draw, box[0] + 106, y + 6)
    text_block(draw, box[0] + 16, box[3] - 54,
               "Trilateral summit signs a “Declaration Toward Peace”; Ukraine dominates the talks.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 32, line_gap=3)


def climate_panel(draw, box):
    panel(draw, box, (240, 248, 238))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(draw, x, y, "CLIMATE • TÜRKIYE", (30, 110, 60))
    y = text_block(draw, x, y, "COP31: MINISTERS RACE TO UNBLOCK TALKS IN ANTALYA",
                   font(SANS_BOLD, 24), INK, box[2] - x - 16, line_gap=4)
    icon_climate(draw, box[0] + 218, y + 30)
    text_block(draw, box[0] + 16, box[3] - 32,
               "Negotiators scramble to save the climate deal.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 32, line_gap=3)


def vangogh_panel(draw, box):
    panel(draw, box, (246, 242, 228))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(draw, x, y, "ART • AUCTION RECORD", (120, 84, 10))
    y = text_block(draw, x, y, "VAN GOGH SELLS FOR $190.4M — AN ARTIST RECORD",
                   font(SANS_BOLD, 24), INK, box[2] - x - 16, line_gap=4)
    icon_vangogh(draw, box[0] + 80, y + 8, 320, 60)


def rose_panel(draw, box):
    panel(draw, box, (252, 240, 238))
    x, y = box[0] + 16, box[1] + 12
    y = kicker(draw, x, y, "BASEBALL • WASHINGTON", (150, 20, 28))
    y = text_block(draw, x, y, "TRUMP PARDONS PETE ROSE",
                   font(SANS_BOLD, 25), INK, box[2] - x - 16, line_gap=4)
    icon_baseball(draw, box[0] + 92, y + 52, 36)
    text_block(draw, box[0] + 150, y + 30,
               "A posthumous pardon for the baseball legend.",
               font(SANS, 16), (60, 60, 60), box[2] - box[0] - 166, line_gap=3)


def senate_hormuz_panel(draw, box):
    panel(draw, box, (238, 240, 246), width=3)
    x, y = box[0] + 16, box[1] + 12
    y = kicker(draw, x, y, "WASHINGTON • THE GULF", (38, 58, 99))
    y = text_block(draw, x, y, "SENATE REJECTS IRAN WAR-POWERS BILL 51–48",
                   font(SANS_BOLD, 22), INK, 620, line_gap=4)
    text_block(draw, x, y + 4, "HORMUZ CRISIS: IEA WARNS ON ENERGY SECURITY",
               font(SANS_BOLD, 20), (150, 20, 28), 612, line_gap=3)
    icon_tanker(draw, box[0] + 640, box[1] + 20)


def briefs_strip(draw):
    box = [MARGIN, 924, W - MARGIN, 1008]
    panel(draw, box, (30, 30, 34), width=2)
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
        draw.ellipse([x, y + 5, x + 9, y + 14], fill=(250, 205, 40))
        text_block(draw, x + 16, y, item, f, WHITE, col_w - 22, line_gap=2)


# ---------------------------------------------------------------- main

def build():
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    masthead(draw)
    top_story(draw)

    # middle grid: two columns
    gap = 16
    col_w = (CONTENT_W - gap) // 2
    left_x, right_x = MARGIN, MARGIN + col_w + gap
    summit_panel(draw, [left_x, 372, left_x + col_w, 604])
    climate_panel(draw, [right_x, 372, right_x + col_w, 604])
    vangogh_panel(draw, [left_x, 614, left_x + col_w, 790])
    rose_panel(draw, [right_x, 614, right_x + col_w, 790])

    senate_hormuz_panel(draw, [MARGIN, 800, W - MARGIN, 916])
    briefs_strip(draw)
    return img


def main(argv):
    out = Path(argv[1]) if len(argv) > 1 else Path("/output/entry.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    # No pnginfo / metadata is attached: the file is pixels only,
    # which keeps repeated runs byte-identical.
    build().save(out, format="PNG", optimize=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main(sys.argv)
