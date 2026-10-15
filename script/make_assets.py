import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
EMOJIS = ASSETS / "emojis"
FONT_BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MED = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"

INK = (122, 64, 66, 255)
PINK = (255, 176, 160, 255)
PINK_L = (255, 224, 212, 255)
CREAM = (255, 247, 240, 255)
GOLD = (255, 207, 112, 255)
GOLD_D = (214, 148, 70, 255)
MINT = (186, 226, 190, 255)
SKY = (178, 208, 238, 255)
LILAC = (226, 190, 214, 255)
RED = (240, 118, 124, 255)
WHITE = (255, 255, 255, 255)

S = 4
N = 128 * S


def canvas():
    return Image.new("RGBA", (N, N), (0, 0, 0, 0))


def finish(img, name):
    out = img.resize((128, 128), Image.LANCZOS)
    out.save(EMOJIS / f"{name}.png")


def p(v):
    return int(round(v * S))


def circle(d, cx, cy, r, fill, outline=INK, w=5):
    d.ellipse([p(cx - r), p(cy - r), p(cx + r), p(cy + r)], fill=fill, outline=outline, width=p(w) // 2)


def rrect(d, box, r, fill, outline=INK, w=5):
    d.rounded_rectangle([p(box[0]), p(box[1]), p(box[2]), p(box[3])], radius=p(r), fill=fill, outline=outline, width=p(w) // 2)


def poly(d, pts, fill, outline=INK, w=5):
    pp = [(p(x), p(y)) for x, y in pts]
    d.polygon(pp, fill=fill)
    d.line(pp + [pp[0]], fill=outline, width=p(w) // 2, joint="curve")


def line(d, pts, fill=INK, w=6):
    d.line([(p(x), p(y)) for x, y in pts], fill=fill, width=p(w) // 2, joint="curve")


def star_pts(cx, cy, ro, ri, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = ro if i % 2 == 0 else ri
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def face(d, cx, cy, s=1.0):
    circle(d, cx - 13 * s, cy, 3.4 * s, INK, INK, 1)
    circle(d, cx + 13 * s, cy, 3.4 * s, INK, INK, 1)
    circle(d, cx - 21 * s, cy + 7 * s, 4.5 * s, (255, 150, 170, 200), (255, 150, 170, 0), 0)
    circle(d, cx + 21 * s, cy + 7 * s, 4.5 * s, (255, 150, 170, 200), (255, 150, 170, 0), 0)
    d.arc([p(cx - 6 * s), p(cy - 2 * s), p(cx + 6 * s), p(cy + 9 * s)], 20, 160, fill=INK, width=p(2.4 * s))


def font(path, size):
    return ImageFont.truetype(path, size)


def centered_text(d, text, cx, cy, size, fill=INK, path=FONT_BOLD):
    f = font(path, size * S)
    bbox = d.textbbox((0, 0), text, font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((p(cx) - w / 2 - bbox[0], p(cy) - h / 2 - bbox[1]), text, font=f, fill=fill)


CHARACTER = ASSETS / "character.png"


def character_crop(box, size):
    art = Image.open(CHARACTER).convert("RGBA")
    return art.crop(box).resize((size, size), Image.LANCZOS)


def e_logo():
    art = Image.open(CHARACTER).convert("RGBA")
    bbox = art.getbbox()
    art = art.crop(bbox)
    side = max(art.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(art, ((side - art.width) // 2, (side - art.height) // 2), art)
    sq.resize((128, 128), Image.LANCZOS).save(EMOJIS / "logo.png")


def e_coin():
    im = canvas()
    d = ImageDraw.Draw(im)
    circle(d, 64, 64, 58, GOLD, INK, 6)
    circle(d, 64, 64, 49, (255, 232, 160, 255), GOLD_D, 4)
    inner = 46
    face = character_crop((170, 140, 1090, 1060), p(inner * 2))
    mask = Image.new("L", (p(inner * 2), p(inner * 2)), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, p(inner * 2) - 1, p(inner * 2) - 1], fill=255)
    back = Image.new("RGBA", (p(inner * 2), p(inner * 2)), CREAM)
    back.alpha_composite(face)
    im.paste(back, (p(64 - inner), p(64 - inner)), mask)
    d.ellipse([p(18), p(18), p(110), p(110)], outline=GOLD_D, width=p(1.5))
    d.arc([p(14), p(14), p(114), p(114)], 200, 250, fill=WHITE, width=p(3))
    finish(im, "coin")


def e_bank():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, [(64, 14), (112, 44), (16, 44)], PINK, INK, 6)
    for x in (28, 50, 72, 94):
        rrect(d, (x, 50, x + 12, 96), 3, CREAM, INK, 5)
    rrect(d, (14, 98, 114, 112), 5, PINK_L, INK, 5)
    circle(d, 64, 33, 5, GOLD, INK, 3)
    finish(im, "bank")


def e_games():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (10, 36, 118, 96), 28, LILAC, INK, 6)
    line(d, [(34, 52), (34, 80)], INK, 8)
    line(d, [(20, 66), (48, 66)], INK, 8)
    circle(d, 88, 59, 6, PINK, INK, 4)
    circle(d, 100, 74, 6, MINT, INK, 4)
    finish(im, "games")


def e_info():
    im = canvas()
    d = ImageDraw.Draw(im)
    circle(d, 64, 64, 48, SKY, INK, 6)
    circle(d, 64, 40, 6, INK, INK, 1)
    rrect(d, (57, 54, 71, 92), 6, INK, INK, 1)
    finish(im, "info")


def e_clock():
    im = canvas()
    d = ImageDraw.Draw(im)
    circle(d, 64, 64, 48, CREAM, INK, 6)
    for i in range(12):
        a = math.radians(i * 30)
        line(d, [(64 + 38 * math.sin(a), 64 - 38 * math.cos(a)), (64 + 43 * math.sin(a), 64 - 43 * math.cos(a))], INK, 5)
    line(d, [(64, 64), (64, 38)], INK, 7)
    line(d, [(64, 64), (84, 74)], PINK, 7)
    circle(d, 64, 64, 5, INK, INK, 1)
    finish(im, "clock")


def e_settings():
    im = canvas()
    d = ImageDraw.Draw(im)
    pts = []
    teeth = 8
    for i in range(teeth * 2):
        a0 = math.radians(i * 180 / teeth - 90)
        r = 50 if i % 2 == 0 else 38
        pts.append((64 + r * math.cos(a0), 64 + r * math.sin(a0)))
    pts2 = []
    for i in range(teeth):
        for off, r in ((-9, 38), (-6, 52), (6, 52), (9, 38)):
            a = math.radians(i * 360 / teeth + off - 90)
            pts2.append((64 + r * math.cos(a), 64 + r * math.sin(a)))
    poly(d, pts2, MINT, INK, 6)
    circle(d, 64, 64, 30, MINT, INK, 5)
    circle(d, 64, 64, 14, CREAM, INK, 5)
    finish(im, "settings")


def e_tick():
    im = canvas()
    d = ImageDraw.Draw(im)
    circle(d, 64, 64, 48, MINT, INK, 6)
    line(d, [(40, 66), (58, 84), (90, 46)], INK, 11)
    finish(im, "tick")


def e_denied():
    im = canvas()
    d = ImageDraw.Draw(im)
    circle(d, 64, 64, 48, RED, INK, 6)
    line(d, [(44, 44), (84, 84)], INK, 11)
    line(d, [(84, 44), (44, 84)], INK, 11)
    finish(im, "denied")


def e_warn():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, [(64, 14), (116, 104), (12, 104)], GOLD, INK, 6)
    rrect(d, (59, 44, 69, 78), 4, INK, INK, 1)
    circle(d, 64, 91, 5, INK, INK, 1)
    finish(im, "warn")


def e_arrow():
    im = canvas()
    d = ImageDraw.Draw(im)
    line(d, [(30, 64), (96, 64)], (246, 246, 250, 255), 14)
    line(d, [(70, 36), (98, 64), (70, 92)], (246, 246, 250, 255), 14)
    finish(im, "arrow")


def e_arrow_grey():
    im = canvas()
    d = ImageDraw.Draw(im)
    g = (150, 140, 156, 255)
    line(d, [(30, 64), (96, 64)], g, 14)
    line(d, [(70, 36), (98, 64), (70, 92)], g, 14)
    finish(im, "arrow_grey")


def e_arrow_left():
    src = Image.open(EMOJIS / "arrow.png").convert("RGBA")
    src.transpose(Image.FLIP_LEFT_RIGHT).save(EMOJIS / "arrow_left.png")


def e_heart():
    im = canvas()
    d = ImageDraw.Draw(im)
    pts = []
    for t in range(0, 360, 3):
        a = math.radians(t)
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((64 + x * 3.1, 58 - y * 3.1))
    poly(d, pts, PINK, INK, 6)
    d.arc([p(36), p(30), p(60), p(54)], 200, 260, fill=WHITE, width=p(3))
    finish(im, "heart")


def e_star():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, star_pts(64, 68, 54, 24), GOLD, INK, 6)
    finish(im, "star")


def e_gift():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (22, 54, 106, 108), 8, PINK, INK, 6)
    rrect(d, (16, 38, 112, 62), 8, PINK_L, INK, 6)
    rrect(d, (57, 38, 71, 108), 2, GOLD, INK, 4)
    d.arc([p(36), p(14), p(66), p(42)], 90, 330, fill=INK, width=p(3))
    d.arc([p(62), p(14), p(92), p(42)], 210, 450, fill=INK, width=p(3))
    finish(im, "gift")


def e_dice():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (16, 16, 112, 112), 22, CREAM, INK, 6)
    for x, y in ((38, 38), (90, 38), (64, 64), (38, 90), (90, 90)):
        circle(d, x, y, 7, PINK, INK, 3)
    finish(im, "dice")


def e_cards():
    im = canvas()
    d = ImageDraw.Draw(im)
    back = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    bd = ImageDraw.Draw(back)
    rrect(bd, (30, 22, 94, 108), 10, CREAM, INK, 6)
    centered_text(bd, "A", 52, 44, 26, RED)
    circle(bd, 62, 76, 12, RED, INK, 3)
    back = back.rotate(-14, resample=Image.BICUBIC, center=(p(62), p(65)))
    im.alpha_composite(back)
    front = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    fd = ImageDraw.Draw(front)
    rrect(fd, (30, 22, 94, 108), 10, PINK_L, INK, 6)
    centered_text(fd, "K", 48, 44, 26, INK)
    poly(fd, star_pts(64, 76, 14, 7), LILAC, INK, 3)
    front = front.rotate(10, resample=Image.BICUBIC, center=(p(62), p(65)))
    im.alpha_composite(front)
    finish(im, "cards")


def e_trophy():
    im = canvas()
    d = ImageDraw.Draw(im)
    d.arc([p(14), p(24), p(46), p(60)], 90, 270, fill=INK, width=p(3))
    d.arc([p(82), p(24), p(114), p(60)], 270, 90, fill=INK, width=p(3))
    poly(d, [(34, 18), (94, 18), (88, 62), (64, 78), (40, 62)], GOLD, INK, 6)
    rrect(d, (56, 76, 72, 94), 3, GOLD_D, INK, 4)
    rrect(d, (36, 94, 92, 110), 6, GOLD, INK, 5)
    finish(im, "trophy")


def e_paw():
    im = canvas()
    d = ImageDraw.Draw(im)
    for x, y, r in ((28, 56, 12), (50, 36, 12), (78, 36, 12), (100, 56, 12)):
        circle(d, x, y, r, PINK, INK, 5)
    d.ellipse([p(34), p(62), p(94), p(112)], fill=PINK, outline=INK, width=p(3))
    finish(im, "paw")


def e_bag():
    im = canvas()
    d = ImageDraw.Draw(im)
    d.arc([p(40), p(10), p(88), p(56)], 180, 360, fill=INK, width=p(3.4))
    rrect(d, (22, 38, 106, 112), 18, LILAC, INK, 6)
    circle(d, 64, 70, 10, CREAM, INK, 4)
    finish(im, "bag")


def e_fish():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, [(86, 64), (116, 38), (116, 90)], SKY, INK, 5)
    d.ellipse([p(10), p(36), p(96), p(92)], fill=SKY, outline=INK, width=p(3))
    circle(d, 32, 58, 5, INK, INK, 1)
    d.arc([p(44), p(46), p(76), p(82)], 300, 60, fill=INK, width=p(2.4))
    finish(im, "fish")


def e_hammer():
    im = canvas()
    d = ImageDraw.Draw(im)
    line(d, [(36, 100), (78, 52)], INK, 14)
    line(d, [(36, 100), (78, 52)], (214, 170, 120, 255), 8)
    poly(d, [(58, 24), (104, 54), (92, 70), (46, 40)], (190, 190, 205, 255), INK, 6)
    finish(im, "hammer")


def e_lock():
    im = canvas()
    d = ImageDraw.Draw(im)
    d.arc([p(36), p(10), p(92), p(66)], 180, 360, fill=INK, width=p(3.6))
    line(d, [(38, 38), (38, 54)], INK, 7)
    line(d, [(90, 38), (90, 54)], INK, 7)
    rrect(d, (24, 50, 104, 110), 16, GOLD, INK, 6)
    circle(d, 64, 74, 8, INK, INK, 1)
    rrect(d, (61, 76, 67, 94), 2, INK, INK, 1)
    finish(im, "lock")


def e_chart():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (16, 66, 40, 108), 5, MINT, INK, 5)
    rrect(d, (52, 40, 76, 108), 5, PINK, INK, 5)
    rrect(d, (88, 18, 112, 108), 5, LILAC, INK, 5)
    finish(im, "chart")


def e_slot_cherry():
    im = canvas()
    d = ImageDraw.Draw(im)
    line(d, [(46, 78), (60, 30), (92, 22)], (96, 170, 96, 255), 7)
    line(d, [(86, 84), (60, 30)], (96, 170, 96, 255), 7)
    circle(d, 44, 86, 22, RED, INK, 6)
    circle(d, 88, 90, 22, RED, INK, 6)
    d.arc([p(32), p(74), p(46), p(88)], 200, 260, fill=WHITE, width=p(3))
    poly(d, [(92, 22), (110, 30), (96, 40)], MINT, INK, 4)
    finish(im, "slot_cherry")


def e_slot_lemon():
    im = canvas()
    d = ImageDraw.Draw(im)
    d.ellipse([p(12), p(28), p(116), p(100)], fill=(255, 238, 120, 255), outline=INK, width=p(3))
    poly(d, [(100, 34), (122, 26), (112, 50)], (255, 238, 120, 255), INK, 5)
    d.ellipse([p(26), p(40), p(98), p(88)], outline=(240, 200, 60, 255), width=p(2))
    d.arc([p(24), p(38), p(60), p(66)], 190, 260, fill=WHITE, width=p(3))
    finish(im, "slot_lemon")


def e_slot_bell():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, [(64, 14), (92, 28), (96, 72), (112, 94), (16, 94), (32, 72), (36, 28)], GOLD, INK, 6)
    circle(d, 64, 104, 9, GOLD_D, INK, 4)
    circle(d, 64, 14, 6, GOLD_D, INK, 3)
    d.arc([p(40), p(36), p(60), p(62)], 190, 260, fill=WHITE, width=p(3))
    finish(im, "slot_bell")


def e_slot_gem():
    im = canvas()
    d = ImageDraw.Draw(im)
    poly(d, [(34, 22), (94, 22), (116, 50), (64, 110), (12, 50)], SKY, INK, 6)
    line(d, [(12, 50), (116, 50)], INK, 4)
    line(d, [(34, 22), (46, 50), (64, 110)], INK, 3)
    line(d, [(94, 22), (82, 50), (64, 110)], INK, 3)
    finish(im, "slot_gem")


def e_slot_seven():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (12, 12, 116, 116), 28, PINK_L, INK, 6)
    centered_text(d, "7", 64, 66, 84, RED)
    finish(im, "slot_seven")


def e_slot_clover():
    im = canvas()
    d = ImageDraw.Draw(im)
    g = (110, 205, 140, 255)
    for cx, cy in ((46, 46), (82, 46), (46, 82), (82, 82)):
        circle(d, cx, cy, 20, g, INK, 5)
    circle(d, 64, 64, 9, g, g, 0)
    line(d, [(70, 80), (88, 112)], INK, 7)
    finish(im, "slot_clover")


def e_slot_spin():
    im = canvas()
    d = ImageDraw.Draw(im)
    rrect(d, (12, 12, 116, 116), 28, (240, 232, 246, 255), INK, 6)
    for i in range(3):
        d.arc([p(30), p(30), p(98), p(98)], 20 + i * 120, 90 + i * 120, fill=LILAC, width=p(5))
    finish(im, "slot_spin")


def make_emojis():
    EMOJIS.mkdir(parents=True, exist_ok=True)
    fns = [
        e_logo, e_coin, e_bank, e_games, e_info, e_clock, e_settings, e_tick, e_denied, e_warn,
        e_arrow, e_arrow_left, e_arrow_grey, e_heart, e_star, e_gift, e_dice, e_cards, e_trophy, e_paw, e_bag,
        e_fish, e_hammer, e_lock, e_chart, e_slot_cherry, e_slot_lemon, e_slot_bell, e_slot_gem,
        e_slot_seven, e_slot_clover, e_slot_spin,
    ]
    for fn in fns:
        fn()
    manifest = {path.stem.upper(): path.name for path in sorted(EMOJIS.glob("*.png"))}
    (ROOT / "emojis.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    make_emojis()
