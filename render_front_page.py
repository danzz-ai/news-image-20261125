#!/usr/bin/env python3
"""Render the front page of THE WORLD TODAY for 25 November 2026.

Draws a classic broadsheet front page with PIL: masthead, date line, hero
story with a small geometric illustration, six news panels and an
"ALSO TODAY" ticker strip. Output is deterministic: no timestamps, no
randomness, fixed fonts, fixed JPEG quality.
"""

import hashlib
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
PAPER = (253, 253, 248)
INK = (17, 17, 17)
ACCENT = (139, 26, 26)
GOLD = (201, 162, 39)
GREY = (90, 90, 86)
LIGHT_GREY = (210, 210, 204)
BAND = (17, 17, 17)
SKY = (226, 232, 238)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/liberation",
]


def find_font(names):
    for d in FONT_DIRS:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return path
    raise FileNotFoundError("no font found for %r" % (names,))


SERIF_BOLD = find_font(["DejaVuSerif-Bold.ttf", "NotoSerif-Bold.ttf", "LiberationSerif-Bold.ttf"])
SERIF = find_font(["DejaVuSerif.ttf", "NotoSerif-Regular.ttf", "LiberationSerif-Regular.ttf"])
SANS_BOLD = find_font(["DejaVuSans-Bold.ttf", "NotoSans-Bold.ttf", "LiberationSans-Bold.ttf"])
SANS = find_font(["DejaVuSans.ttf", "NotoSans-Regular.ttf", "LiberationSans-Regular.ttf"])


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=fnt) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered(draw, cx, y, text, fnt, fill=INK, tracking=0):
    """Draw text centered on cx, with optional per-character tracking."""
    if tracking == 0:
        w = draw.textlength(text, font=fnt)
        draw.text((cx - w / 2, y), text, font=fnt, fill=fill)
        return draw.textbbox((0, 0), text, font=fnt)[3]
    widths = [draw.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    top = None
    for ch, w in zip(text, widths):
        bbox = draw.textbbox((x, y), ch, font=fnt)
        if top is None:
            top = bbox[3]
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking
    return top


def draw_block(draw, x, y, lines, fnt, fill=INK, line_height=None, align="left", width=None):
    """Draw wrapped lines; returns the y just below the last line."""
    if line_height is None:
        line_height = int(fnt.size * 1.28)
    for line in lines:
        if align == "center":
            w = draw.textlength(line, font=fnt)
            draw.text((x + (width - w) / 2, y), line, font=fnt, fill=fill)
        else:
            draw.text((x, y), line, font=fnt, fill=fill)
        y += line_height
    return y


def draw_refinery(img, x, y, w, h):
    """Geometric refinery skyline, drawn on its own layer so nothing can
    spill outside the illustration box: towers, pipes, flare flame, smoke."""
    layer = Image.new("RGB", (w, h), SKY)
    ld = ImageDraw.Draw(layer)
    ground = h - 18
    # distant haze band
    ld.rectangle([0, ground - 24, w, ground], fill=(198, 206, 212))
    # towers (left to right, varied heights; all fit inside the box)
    towers = [
        (60, ground - 62, 44, 62),
        (150, ground - 82, 54, 82),
        (250, ground - 54, 40, 54),
        (330, ground - 72, 48, 72),
    ]
    for tx, ty, tw, th in towers:
        ld.rectangle([tx, ty, tx + tw, ty + th], fill=(38, 42, 48))
        ld.rectangle([tx + 6, ty + 8, tx + tw - 6, ty + 12], fill=(90, 96, 104))
        ld.rectangle([tx + 6, ty + 24, tx + tw - 6, ty + 28], fill=(90, 96, 104))
        ld.rectangle([tx + 6, ty + 40, tx + tw - 6, ty + 44], fill=(90, 96, 104))
    # horizontal pipes
    ld.rectangle([60, ground - 30, 420, ground - 24], fill=(58, 62, 70))
    ld.rectangle([120, ground - 46, 330, ground - 42], fill=(58, 62, 70))
    # flare stack on the right with flame (tip stays inside the box)
    fx = w - 130
    ld.rectangle([fx, ground - 68, fx + 14, ground], fill=(38, 42, 48))
    flame = [
        (fx + 7, ground - 82),
        (fx - 6, ground - 66),
        (fx - 1, ground - 62),
        (fx + 4, ground - 66),
        (fx + 9, ground - 61),
        (fx + 14, ground - 66),
        (fx + 19, ground - 64),
    ]
    ld.polygon(flame, fill=(198, 62, 28))
    inner = [
        (fx + 7, ground - 75),
        (fx - 1, ground - 66),
        (fx + 5, ground - 63),
        (fx + 11, ground - 66),
        (fx + 14, ground - 64),
    ]
    ld.polygon(inner, fill=(232, 164, 32))
    # smoke puffs from the second tower, drifting up-left inside the box
    sx, sy = 177, ground - 58
    for dx, dy, r in [(0, 0, 8), (13, -6, 10), (26, -10, 11)]:
        ld.ellipse([sx + dx - r, sy + dy - r, sx + dx + r, sy + dy + r], fill=(150, 156, 162))
    # red strike starburst over the flare
    import math
    cx, cy = fx + 7, ground - 68
    for ang in range(0, 360, 30):
        r1, r2 = 17, 8
        a = math.radians(ang)
        a2 = math.radians(ang + 15)
        ld.line(
            [(cx + r2 * math.cos(a2), cy + r2 * math.sin(a2)),
             (cx + r1 * math.cos(a), cy + r1 * math.sin(a))],
            fill=ACCENT, width=3,
        )
    ld.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=ACCENT)
    # ground
    ld.rectangle([0, ground, w, h], fill=(38, 42, 48))
    img.paste(layer, (x, y))


def main():
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    margin = 36
    content_w = W - 2 * margin

    # --- masthead ---
    masthead_f = font(SERIF_BOLD, 82)
    draw_centered(draw, W // 2, 22, "THE WORLD TODAY", masthead_f)
    # double rule
    draw.line([(margin, 122), (W - margin, 122)], fill=INK, width=3)
    draw.line([(margin, 128), (W - margin, 128)], fill=INK, width=1)

    # --- date line ---
    date_f = font(SANS_BOLD, 20)
    draw_centered(draw, W // 2, 140, "WEDNESDAY, 25 NOVEMBER 2026", date_f, tracking=3)
    draw.line([(margin, 170), (W - margin, 170)], fill=INK, width=1)

    # --- kicker ---
    kicker_f = font(SANS_BOLD, 18)
    draw_centered(draw, W // 2, 182, "MIDDLE EAST", kicker_f, fill=ACCENT, tracking=6)

    # --- hero headline (single line, shrink until it fits) ---
    hero = "HOUTHIS HIT SAUDI REFINERY"
    hero_size = 62
    while hero_size > 30:
        hero_f = font(SERIF_BOLD, hero_size)
        if draw.textlength(hero, font=hero_f) <= content_w:
            break
        hero_size -= 2
    draw_centered(draw, W // 2, 208, hero, hero_f)
    # red accent rule under the hero headline
    draw.line([(W // 2 - 120, 276), (W // 2 + 120, 276)], fill=ACCENT, width=3)

    # --- hero standfirst ---
    standfirst = (
        "Yemen's Houthis say they attacked Saudi Arabia's Ras Tanura oil "
        "refinery, the kingdom's largest, and struck Riyadh's tallest tower, "
        "wounding 11 people."
    )
    stand_f = font(SERIF, 23)
    lines = wrap(draw, standfirst, stand_f, content_w - 60)
    y = draw_block(draw, margin + 30, 290, lines, stand_f, line_height=30, align="center", width=content_w - 60)

    # --- illustration ---
    ill_y = y + 14
    ill_h = 108
    draw_refinery(img, margin, ill_y, content_w, ill_h)
    draw.line([(margin, ill_y + ill_h + 10), (W - margin, ill_y + ill_h + 10)], fill=INK, width=2)

    # --- six panels: 3 columns x 2 rows ---
    panels = [
        ("DISASTER", "CAIRO TANKER FIRE KILLS 31",
         "A fuel tanker crash ignites a massive fire on a highway around Cairo, "
         "killing at least 31 people, Egyptian authorities say."),
        ("TRADE", "US TARIFFS HIT 14 PARTNERS",
         "The US proposes tariffs on 14 partners at 20 to 40 percent, capped "
         "by existing deals; nothing takes effect before January 25."),
        ("TECH", "HUAWEI GUILTY IN US TRIAL",
         "A federal court finds Huawei guilty of conspiracy to steal trade "
         "secrets and bank fraud, but not of overarching racketeering."),
        ("CULTURE", "PARADE POSTPONED, FIRST IN 100 YEARS",
         "The Macy's Thanksgiving Day Parade is postponed two days to Saturday "
         "over weather forecasts, the first postponement in 100 years."),
        ("SPACE", "SHENZHOU-24 DOCKS",
         "China's Shenzhou-24 docks at Tiangong carrying Pakistan's Muhammad "
         "Zeeshan Ali, the first foreign astronaut aboard."),
        ("MARKETS", "MARKETS SLIDE",
         "Wall Street slides on AI, inflation and tariff fears: the S&P 500 "
         "fell about 2.2 percent, the Nasdaq 3.2 percent in midday trading."),
    ]
    col_w = (content_w - 2 * 28) // 3
    kick_f = font(SANS_BOLD, 15)
    head_f = font(SERIF_BOLD, 22)
    body_f = font(SERIF, 16)
    panel_top = ill_y + ill_h + 24
    row_h = 176
    for i, (kick, head, body) in enumerate(panels):
        row, col = divmod(i, 3)
        px = margin + col * (col_w + 28)
        py = panel_top + row * row_h
        # vertical divider between columns
        if col > 0:
            draw.line([(px - 14, py + 4), (px - 14, py + row_h - 16)], fill=LIGHT_GREY, width=1)
        draw.text((px, py), kick, font=kick_f, fill=ACCENT)
        head_lines = wrap(draw, head, head_f, col_w)
        hy = draw_block(draw, px, py + 22, head_lines, head_f, line_height=26)
        body_lines = wrap(draw, body, body_f, col_w)
        draw_block(draw, px, hy + 6, body_lines[:4], body_f, line_height=20)

    # --- ticker strip ---
    band_y = panel_top + 2 * row_h + 12
    band_h = H - band_y - 22
    draw.rectangle([0, band_y, W, band_y + band_h], fill=BAND)
    label_f = font(SANS_BOLD, 17)
    tick_f = font(SANS, 15)
    label = "ALSO TODAY"
    draw.text((margin, band_y + 12), label, font=label_f, fill=GOLD)
    ticker = (
        "Iran says more tankers struck mines in the Strait of Hormuz  |  "
        "UN peacekeepers evacuate Ebola response workers trapped by fighting "
        "in eastern Congo  |  Sudanese paramilitary drone strikes kill 19 "
        "civilians  |  Israel's military kills a Hamas colonel in Gaza  |  "
        "The US economy grows strongly in the third quarter but inflation "
        "stays high in October"
    )
    tick_lines = wrap(draw, ticker, tick_f, W - 2 * margin)
    draw_block(draw, margin, band_y + 38, tick_lines, tick_f, fill=(235, 235, 230), line_height=20)

    out_path = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    img.save(out_path, "JPEG", quality=92)
    digest = hashlib.sha256(open(out_path, "rb").read()).hexdigest()
    print("wrote %s sha256=%s" % (out_path, digest))


if __name__ == "__main__":
    main()
