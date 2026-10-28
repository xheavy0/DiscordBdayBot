# ============================
# დაბადების დღის ბარათი (სურათი)
# ============================
# ფონზე ხატავს იუბილარის მრგვალ ავატარს, სახელს და ასაკს.
# ფონი: assets/birthday_bg.png (ან .jpg). თუ არ არის, ბოტი სადა ფონს დახატავს.
# ქართული ფონტი: assets/fonts/-ში ჩადებული .ttf ან სერვერზე დაყენებული Noto Sans Georgian
# (sudo apt install fonts-noto-core). ფონტის გარეშე ბარათი არ იხატება და ბოტი ჩვეულებრივ embed-ს აგზავნის.
import glob
import io
import os
import random

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError:  # Pillow არ არის დაყენებული — ბარათის გარეშე ვმუშაობთ
    Image = None

CARD_W = 1280
NEON_PINK = (255, 79, 216)
NEON_CYAN = (64, 224, 255)
WHITE = (255, 255, 255)
SOFT = (220, 215, 255)

BG_CANDIDATES = ["assets/birthday_bg.png", "assets/birthday_bg.jpg", "assets/birthday_bg.jpeg"]
FONT_CANDIDATES = [
    "assets/fonts/*Georgian*Bold*.ttf",
    "assets/fonts/*.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansGeorgian-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansGeorgian-Regular.ttf",
    "/usr/share/fonts/**/NotoSansGeorgian*.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",  # ლოკალური ტესტისთვის Windows-ზე
    "C:/Windows/Fonts/sylfaen.ttf",
]
LETTER_SPACING = 0.08   # ასოებს შორის დაშორება (ფონტის ზომის წილი)
GLITCH = 0.035          # ციანი/ვარდისფერი „გლიჩ“ წანაცვლება (ფონტის ზომის წილი)


def _find_font():
    for pattern in FONT_CANDIDATES:
        matches = sorted(glob.glob(pattern, recursive=True))
        if matches:
            return matches[0]
    return None


def card_available() -> bool:
    return Image is not None and _find_font() is not None


def _background():
    """ფონი იმავე პროპორციით, რაც ფაილს აქვს (სიგანე CARD_W)."""
    for path in BG_CANDIDATES:
        if os.path.exists(path):
            bg = Image.open(path).convert("RGB")
            height = round(CARD_W * bg.height / bg.width)
            return bg.resize((CARD_W, height), Image.LANCZOS)

    # სადა ფონი კონფეტით, სანამ საკუთარი ფონი არ გვაქვს
    w, h = CARD_W, 720
    bg = Image.new("RGB", (w, h), (24, 20, 60))
    draw = ImageDraw.Draw(bg)
    draw.ellipse((-120, -160, 380, 300), fill=(52, 40, 120))
    draw.ellipse((950, 450, 1450, 950), fill=(100, 30, 80))
    rng = random.Random(7)
    colors = [NEON_PINK, NEON_CYAN, (239, 159, 39), (175, 169, 236)]
    for _ in range(70):
        x, y, s = rng.randint(0, w), rng.randint(0, h), rng.randint(8, 18)
        draw.rectangle((x, y, x + s, y + s // 2), fill=rng.choice(colors))
    return bg


def _has_glyph(font, ch) -> bool:
    missing = font.getmask("\U0010FFFF")
    mask = font.getmask(ch)
    return mask.size != missing.size or bytes(mask) != bytes(missing)


def _cyber_case(text: str, font) -> str:
    """ქართულ ტექსტს მთავრულით (დიდი ასოებით) ვწერთ, თუ ფონტს ეს ასოები აქვს."""
    upper = text.upper()
    if all(_has_glyph(font, ch) for ch in upper if not ch.isspace()):
        return upper
    return text


def _spacing(font):
    return font.size * LETTER_SPACING


def _text_width(draw, text, font):
    return sum(draw.textlength(ch, font=font) for ch in text) + _spacing(font) * max(len(text) - 1, 0)


def _draw_spaced(draw, x, y, text, font, fill):
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill, anchor="la")
        x += draw.textlength(ch, font=font) + _spacing(font)


def _fit_font(draw, text, path, start_size, max_width):
    size = start_size
    while size > 24:
        font = ImageFont.truetype(path, size)
        if _text_width(draw, _cyber_case(text, font), font) <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(path, size)


def _neon_text(card, cx, y, text, font, fill, glow, radius=10, glitch=False) -> int:
    """ნეონის ნათება + სურვილისამებრ „გლიჩ“ ეფექტი. აბრუნებს ხაზის სიმაღლეს."""
    text = _cyber_case(text, font)
    measure = ImageDraw.Draw(card)
    x = cx - _text_width(measure, text, font) / 2

    layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    _draw_spaced(ImageDraw.Draw(layer), x, y, text, font, glow + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    card.alpha_composite(layer)
    card.alpha_composite(layer)  # ორჯერ, რომ ნათება უფრო მკვეთრი იყოს

    if glitch:
        shift = max(2, round(font.size * GLITCH))
        split = Image.new("RGBA", card.size, (0, 0, 0, 0))
        split_draw = ImageDraw.Draw(split)
        _draw_spaced(split_draw, x - shift, y, text, font, NEON_CYAN + (210,))
        _draw_spaced(split_draw, x + shift, y, text, font, NEON_PINK + (210,))
        card.alpha_composite(split)

    _draw_spaced(ImageDraw.Draw(card), x, y, text, font, fill)
    ascent, descent = font.getmetrics()
    return ascent + descent


def render_card(avatar_bytes: bytes, name: str, title: str, age_line: str = "") -> io.BytesIO:
    font_path = _find_font()
    card = _background().convert("RGBA")
    W, H = card.size

    # ცენტრში ოდნავ ვამუქებთ, რომ ტექსტი ნებისმიერ ფონზე იკითხებოდეს
    shade = Image.new("L", card.size, 0)
    ImageDraw.Draw(shade).ellipse((W * 0.22, H * 0.02, W * 0.78, H * 0.68), fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(70))
    dark = Image.new("RGBA", card.size, (5, 3, 20, 255))
    dark.putalpha(shade)
    card = Image.alpha_composite(card, dark)

    # მრგვალი ავატარი ნეონის ჩარჩოთი
    size = int(H * 0.30)
    cx, top = W // 2, int(H * 0.08)
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = ImageOps.fit(avatar, (size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)

    ring = 7
    box = (cx - size // 2 - ring, top - ring, cx + size // 2 + ring, top + size + ring)
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(box, outline=NEON_PINK + (255,), width=ring * 3)
    card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(card).ellipse(box, fill=NEON_PINK)
    card.paste(avatar, (cx - size // 2, top), mask)

    # ტექსტი ავატარის ქვეშ, ცენტრში
    draw = ImageDraw.Draw(card)
    max_w = int(W * 0.60)
    title_font = _fit_font(draw, title, font_path, int(H * 0.058), max_w)
    name_font = _fit_font(draw, name, font_path, int(H * 0.105), max_w)
    age_font = _fit_font(draw, age_line or " ", font_path, int(H * 0.045), max_w)

    y = top + size + int(H * 0.025)
    y += _neon_text(card, cx, y, title, title_font, NEON_CYAN, NEON_CYAN, radius=8)
    y += _neon_text(card, cx, y, name, name_font, WHITE, NEON_PINK, radius=12, glitch=True)
    if age_line:
        _neon_text(card, cx, y, age_line, age_font, SOFT, NEON_PINK, radius=6)

    out = io.BytesIO()
    card.convert("RGB").save(out, "JPEG", quality=90)
    out.seek(0)
    return out
