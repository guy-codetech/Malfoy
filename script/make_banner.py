"""Render the Malfoy Bot banner using the bundled artwork and fonts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

import config
from core.cards import background, character, font


def main():
    banner = background(2048, 683)
    art = character(650)
    banner.alpha_composite(art, (2048 - art.width - 90, 33))
    draw = ImageDraw.Draw(banner)
    draw.rounded_rectangle((100, 150, 1080, 530), radius=48, fill=(255, 247, 240, 235))
    draw.text((150, 185), "MALFOY", font=font("Bold", 142), fill=config.CARD_THEME["ink"])
    draw.text((160, 355), "B O T", font=font("Bold", 46), fill=config.CARD_THEME["muted"])
    draw.text((160, 445), config.TAGLINE, font=font("Medium", 32), fill=config.CARD_THEME["ink"])
    banner.convert("RGB").save(ROOT / "assets" / "banner.png")


if __name__ == "__main__":
    main()
