"""Render the Malfoy Bot banner using the bundled artwork and fonts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

import config
from core.cards import character, font


def main():
    banner = Image.new("RGBA", (2048, 683), (16, 39, 31, 255))
    draw = ImageDraw.Draw(banner)
    gold = (237, 207, 129)
    cream = (247, 244, 227)
    draw.polygon(((1100, 0), (2048, 0), (2048, 683), (970, 683)), fill=(27, 62, 46))
    draw.ellipse((1160, 20, 1880, 740), fill=(39, 82, 58), outline=gold, width=2)
    draw.ellipse((1190, 50, 1850, 710), outline=(77, 111, 75), width=2)
    draw.line((100, 106, 270, 106), fill=gold, width=4)
    draw.text((100, 128), "ECONOMY / GAMES / ROLEPLAY", font=font("Medium", 24), fill=gold)
    draw.text((92, 183), "MALFOY", font=font("Bold", 148), fill=cream)
    draw.text((102, 362), "B O T", font=font("Bold", 50), fill=gold)
    draw.text((102, 486), config.TAGLINE, font=font("Medium", 31), fill=cream)
    draw.line((102, 566, 900, 566), fill=(77, 111, 75), width=2)
    art = character(650)
    banner.alpha_composite(art, (1320, 33))
    draw = ImageDraw.Draw(banner)
    for x, y, radius in ((1100, 164, 12), (1900, 480, 18), (1810, 110, 10)):
        draw.polygon(((x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)), fill=gold)
    banner.convert("RGB").save(ROOT / "assets" / "banner.png")


if __name__ == "__main__":
    main()
