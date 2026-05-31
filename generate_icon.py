"""Generates icon.png — a rounded-square V mark for Verbic."""
from PIL import Image, ImageDraw, ImageFont
import os
import sys

SIZE = 512
RADIUS = 96
BG_TOP = (40, 95, 168)       # indigo
BG_BOTTOM = (24, 138, 191)   # teal-blue
ACCENT = (255, 200, 80)       # warm yellow accent dot


def _vertical_gradient(size, top, bottom):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(size):
            px[x, y] = (r, g, b, 255)
    return img


def _font_for_v(size_px):
    candidates = [
        os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "segoeuib.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "arialbd.ttf"),
        os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts", "arial.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size_px)
    return ImageFont.load_default()


def main():
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Rounded rectangle mask
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE, SIZE), radius=RADIUS, fill=255)

    # Gradient background
    gradient = _vertical_gradient(SIZE, BG_TOP, BG_BOTTOM)
    canvas.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)

    # Big white V
    font = _font_for_v(380)
    text = "V"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - w) // 2 - bbox[0]
    y = (SIZE - h) // 2 - bbox[1] - 14  # nudge up so the dot sits below
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    # Accent: small yellow dot at the bottom-right of the V
    dot_r = 30
    dot_cx = SIZE // 2 + 105
    dot_cy = SIZE - 130
    draw.ellipse(
        (dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r),
        fill=ACCENT + (255,),
    )

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
    canvas.save(out_path, "PNG")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
