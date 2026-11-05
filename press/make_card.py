#!/usr/bin/env python3
"""Draw press/card.png (1280x640). Link cards on X and others lay a title bar over the bottom of the image,
so every line of text stays above y=500 and the bottom 140 px hold nothing but background.
Run: uv run --python 3.12 --with pillow python3 press/make_card.py"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640
INK, TEXT, ACCENT, MUTED = "#12211a", "#e5ede7", "#3cc38b", "#93a39a"
SAFE_BOTTOM = 500  # nothing below this line

def font(name: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(name, size, index=index)

sans = "/System/Library/Fonts/HelveticaNeue.ttc"
mono = "/System/Library/Fonts/Menlo.ttc"
img = Image.new("RGB", (W, H), INK)
d = ImageDraw.Draw(img)

# logo tile: a still line with one proven step (same geometry as press/logo.svg, scaled to 120 px)
x0, y0, s = 96, 96, 120 / 256
d.rounded_rectangle((x0, y0, x0 + 120, y0 + 120), radius=int(56 * s), fill="#1b2b23")
d.rounded_rectangle((x0 + 56 * s, y0 + 124 * s, x0 + 200 * s, y0 + 132 * s), radius=2, fill=TEXT)
d.line([(x0 + 152 * s, y0 + 100 * s), (x0 + 172 * s, y0 + 120 * s), (x0 + 212 * s, y0 + 80 * s)], fill=ACCENT, width=7, joint="curve")

d.text((244, 96), "Stillwright", font=font(sans, 92, index=0), fill=TEXT)
d.text((96, 268), "A quiet maker for your AI agent.", font=font(sans, 38), fill=MUTED)
body = font(sans, 30)
d.text((96, 338), "Plans your goals. Vets tools by reading their code.", font=body, fill=TEXT)
d.text((96, 382), "Proves every step. Speaks only when it needs you.", font=body, fill=TEXT)
cmd = font(mono, 26)
d.text((96, 446), "pip install stillwright", font=cmd, fill=ACCENT)
d.text((520, 446), "·", font=cmd, fill=MUTED)
d.text((576, 446), "npx skills add HamzaIlyas/stillwright", font=cmd, fill=ACCENT)

# guard: no text pixel below the safe line
assert all(img.getpixel((x, y)) == (0x12, 0x21, 0x1a) for y in range(SAFE_BOTTOM, H, 4) for x in range(0, W, 8)), "text below the safe zone"
img.save("press/card.png", optimize=True)
print("wrote press/card.png")
