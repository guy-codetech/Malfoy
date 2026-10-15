import asyncio
import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / config.FONT_DIR
ICONS = ROOT / "assets" / "emojis"
CHARACTER = ROOT / "assets" / "character.png"
T = config.CARD_THEME


@lru_cache(maxsize=64)
def font(weight, size):
    try:
        return ImageFont.truetype(str(FONTS / f"Poppins-{weight}.ttf"), size)
    except OSError:
        return ImageFont.load_default()


@lru_cache(maxsize=32)
def icon(name, size):
    path = ICONS / f"{name}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=4)
def character(height):
    art = Image.open(CHARACTER).convert("RGBA")
    art = art.crop(art.getbbox())
    ratio = height / art.height
    return art.resize((int(art.width * ratio), height), Image.LANCZOS)


def fmt(n):
    return f"{int(n):,}"


def short(n):
    n = int(n)
    for limit, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (10_000, "K")):
        if n >= limit:
            value = n / limit
            return f"{value:.1f}".rstrip("0").rstrip(".") + suffix
    return fmt(n)


def gradient(w, h):
    mask = Image.linear_gradient("L").resize((w, h))
    top = Image.new("RGB", (w, h), T["bg_top"])
    bottom = Image.new("RGB", (w, h), T["bg_bottom"])
    return Image.composite(bottom, top, mask).convert("RGBA")


def background(w, h):
    base = gradient(w, h)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx, cy, r in ((w * 0.08, h * 0.95, h * 0.55), (w * 0.92, h * 0.05, h * 0.5), (w * 0.55, h * 1.1, h * 0.5)):
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    base.alpha_composite(glow)
    return base


def panel(base, box, radius=28, alpha=225, shadow=True):
    x0, y0, x1, y1 = [int(v) for v in box]
    if shadow:
        sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 6, x1, y1 + 6], radius=radius, fill=(122, 64, 66, 46))
        base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=T["surface"] + (alpha,))
    base.alpha_composite(layer)


def pill(base, box, fill, text, weight="Bold", size=20, colour=None):
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=fill)
    f = font(weight, size)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((x0 + x1) / 2 - tw / 2 - bbox[0], (y0 + y1) / 2 - th / 2 - bbox[1]), text, font=f, fill=colour or T["ink"])
    base.alpha_composite(layer)


def fit_text(d, text, weight, size, max_width):
    f = font(weight, size)
    if d.textlength(text, font=f) <= max_width:
        return text, f
    while size > 18 and d.textlength(text, font=font(weight, size)) > max_width:
        size -= 2
    f = font(weight, size)
    while len(text) > 3 and d.textlength(text + "...", font=f) > max_width:
        text = text[:-1]
    return (text + "..." if d.textlength(text, font=f) > max_width else text), f


def draw_text(base, xy, text, weight="Bold", size=28, fill=None, max_width=None, anchor="la"):
    d = ImageDraw.Draw(base)
    if max_width:
        text, f = fit_text(d, text, weight, size, max_width)
    else:
        f = font(weight, size)
    d.text(xy, text, font=f, fill=fill or T["ink"], anchor=anchor)


def avatar_circle(base, data, xy, size, ring=8):
    x, y = xy
    ring_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(ring_layer).ellipse([x - ring, y - ring, x + size + ring, y + size + ring], fill=T["accent"] + (255,))
    base.alpha_composite(ring_layer)
    try:
        art = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size), Image.LANCZOS)
    except Exception:
        art = Image.new("RGBA", (size, size), T["accent_soft"] + (255,))
    scale = 4
    mask = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * scale - 1, size * scale - 1], fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    base.paste(art, (x, y), mask)


def bar(base, box, ratio):
    x0, y0, x1, y1 = [int(v) for v in box]
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = (y1 - y0) // 2
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=T["track"] + (255,))
    ratio = max(0.0, min(1.0, ratio))
    if ratio > 0:
        end = max(x0 + (y1 - y0), x0 + int((x1 - x0) * ratio))
        d.rounded_rectangle([x0, y0, end, y1], radius=r, fill=T["accent"] + (255,))
    base.alpha_composite(layer)


def tile(base, box, icon_name, label, value):
    panel(base, box, radius=22, alpha=235, shadow=False)
    x0, y0, x1, y1 = [int(v) for v in box]
    glyph = icon(icon_name, 54)
    if glyph is not None:
        base.alpha_composite(glyph, (x0 + 20, y0 + (y1 - y0 - 54) // 2))
    draw_text(base, (x0 + 90, y0 + 20), label, "Medium", 18, T["muted"])
    draw_text(base, (x0 + 90, y0 + 46), value, "Bold", 30, max_width=x1 - x0 - 105)


def place_character(base, height, right=24, bottom=0, alpha=255):
    art = character(height)
    if alpha < 255:
        art = art.copy()
        art.putalpha(art.getchannel("A").point(lambda v: v * alpha // 255))
    base.alpha_composite(art, (base.width - art.width - right, base.height - art.height - bottom))


def to_png(base):
    out = io.BytesIO()
    base.convert("RGB").save(out, "PNG", optimize=True)
    return out.getvalue()


def profile_card(name, avatar, level, rank, xp, floor, ceil, cash, bank, streak, won, lost, catches, since):
    w, h = 1000, 540
    base = background(w, h)
    panel(base, (30, 30, w - 30, 220))
    place_character(base, 200, right=44, bottom=h - 228 - 0, alpha=255)
    avatar_circle(base, avatar, (62, 62), 130)
    draw_text(base, (230, 58), name, "Bold", 44, max_width=470)
    pill(base, (230, 120, 360, 154), T["accent"] + (255,), f"Level {level}", size=20, colour=(255, 255, 255))
    pill(base, (372, 120, 500, 154), T["accent_soft"] + (255,), f"Rank #{fmt(rank)}", size=20)
    bar(base, (230, 172, 540, 192), (xp - floor) / max(1, ceil - floor))
    draw_text(base, (554, 182), f"{short(xp)} / {short(ceil)} xp", "Medium", 18, T["muted"], anchor="lm")
    xs = (30, 345, 660)
    ys = (244, 374)
    cells = [
        ("coin", "Cash", short(cash)),
        ("bank", "Bank", short(bank)),
        ("chart", "Net Worth", short(cash + bank)),
        ("gift", "Streak", f"{streak} days"),
        ("dice", "Won / Lost", f"{short(won)} / {short(lost)}"),
        ("paw", "Catches", fmt(catches)),
    ]
    for index, (ic, label, value) in enumerate(cells):
        x = xs[index % 3]
        y = ys[index // 3]
        tile(base, (x, y, x + 310, y + 112), ic, label, value)
    draw_text(base, (w / 2, 508), f"Playing since {since}", "Medium", 18, T["muted"], anchor="mm")
    return to_png(base)


def rank_card(name, avatar, level, rank, xp, floor, ceil):
    w, h = 900, 280
    base = background(w, h)
    panel(base, (24, 24, w - 24, h - 24))
    place_character(base, 220, right=34, bottom=18)
    avatar_circle(base, avatar, (56, 62), 150)
    draw_text(base, (240, 54), name, "Bold", 40, max_width=420)
    draw_text(base, (240, 112), f"Level {level}", "Bold", 30, T["accent"])
    draw_text(base, (400, 118), f"Rank #{fmt(rank)}", "Medium", 24, T["muted"])
    bar(base, (240, 170, 620, 196), (xp - floor) / max(1, ceil - floor))
    draw_text(base, (240, 214), f"{fmt(xp)} / {fmt(ceil)} xp", "Medium", 20, T["muted"])
    return to_png(base)


def wallet_card(name, avatar, cash, bank, cap, level):
    w, h = 900, 320
    base = background(w, h)
    panel(base, (24, 24, w - 24, h - 24))
    place_character(base, 210, right=30, bottom=20, alpha=255)
    avatar_circle(base, avatar, (56, 60), 110, ring=6)
    draw_text(base, (190, 60), name, "Bold", 34, max_width=420)
    draw_text(base, (190, 106), f"Level {level} wallet", "Medium", 20, T["muted"])
    coin = icon("coin", 64)
    if coin is not None:
        base.alpha_composite(coin, (56, 196))
    draw_text(base, (136, 190), "Cash", "Medium", 18, T["muted"])
    draw_text(base, (136, 210), fmt(cash), "Bold", 36, max_width=250)
    vault = icon("bank", 64)
    if vault is not None:
        base.alpha_composite(vault, (350, 196))
    draw_text(base, (430, 190), "Bank", "Medium", 18, T["muted"])
    draw_text(base, (430, 210), f"{short(bank)} / {short(cap)}", "Bold", 28, max_width=190)
    bar(base, (350, 276, 610, 290), bank / max(1, cap))
    return to_png(base)


def shop_card(items):
    w, h = 900, 520
    base = background(w, h)
    panel(base, (24, 24, w - 24, 112))
    logo = icon("logo", 72)
    if logo is not None:
        base.alpha_composite(logo, (52, 32))
    draw_text(base, (140, 30), "Lunii Shop", "Bold", 38)
    draw_text(base, (142, 80), "Pick something nice for your adventures", "Medium", 18, T["muted"])
    cols = 2
    tw, th = 400, 150
    for index, item in enumerate(items[:4]):
        col, row = index % cols, index // cols
        x0 = 24 + col * (tw + 52)
        y0 = 136 + row * (th + 22)
        panel(base, (x0, y0, x0 + tw + 0, y0 + th), radius=26, alpha=235)
        glyph = icon(item["icon"].lower(), 84)
        if glyph is not None:
            base.alpha_composite(glyph, (x0 + 26, y0 + 33))
        draw_text(base, (x0 + 134, y0 + 30), item["name"], "Bold", 28, max_width=tw - 150)
        pill(base, (x0 + 134, y0 + 82, x0 + 134 + 176, y0 + 120), T["accent_soft"] + (255,), f"{fmt(item['price'])}", size=22)
        coin = icon("coin", 28)
        if coin is not None:
            base.alpha_composite(coin, (x0 + 134 + 176 + 8, y0 + 87))
    return to_png(base)


async def render(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: fn(*args))
