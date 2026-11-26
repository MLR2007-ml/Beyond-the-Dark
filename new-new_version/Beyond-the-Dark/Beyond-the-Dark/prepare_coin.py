"""Подготовка кадров вращения монеты (запускать один раз, нужен Pillow).

    python prepare_coin.py

На листе assets/coin.jpg монеты нарисованы на зелёном фоне (35, 177, 77).
Скрипт вырезает 7 фаз вращения, выравнивает их по общему центру и
сохраняет готовые PNG в assets/coin_spin/ (игра использует только их).
"""

import os

from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")
SOURCE = os.path.join(ASSETS, "coin.jpg")
OUT_DIR = os.path.join(ASSETS, "coin_spin")

BG = (35, 177, 77)
TARGET_HEIGHT = 40
PADDING = 4


def is_green(pixel):
    r, g, b = pixel[:3]
    return g > r + 35 and g > b + 35


def remove_green(image):
    image = image.convert("RGBA")
    pixels = image.load()
    w, h = image.size
    for y in range(h):
        for x in range(w):
            r, g, b, _ = pixels[x, y]
            distance = abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2])
            if is_green((r, g, b)) and distance > 30:
                pixels[x, y] = (r, g, b, 0)
            elif distance < 55:
                pixels[x, y] = (r, g, b, 0)
            elif distance < 110:
                alpha = int(255 * (distance - 55) / 55)
                if is_green((r, g, b)):
                    r = min(255, (r + b) // 2)
                pixels[x, y] = (r, g, b, max(0, min(255, alpha)))
            else:
                pixels[x, y] = (r, g, b, 255)
    return image


def column_runs(image):
    """Ищет непрерывные вертикальные полосы с непрозрачным содержимым."""
    w, h = image.size
    alpha = image.getchannel("A")
    data = alpha.load()
    runs, start = [], None
    for x in range(w + 1):
        filled = x < w and any(data[x, y] > 20 for y in range(h))
        if filled and start is None:
            start = x
        elif not filled and start is not None:
            runs.append((start, x))
            start = None
    return runs


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sheet = remove_green(Image.open(SOURCE))

    runs = column_runs(sheet)
    print("Фаз вращения:", len(runs), runs)

    frames = []
    for left, right in runs:
        frame = sheet.crop((left, 0, right, sheet.height))
        bbox = frame.getbbox()
        frames.append(frame.crop(bbox))

    width = max(f.width for f in frames)
    height = max(f.height for f in frames)
    canvas_w = width + PADDING * 2
    canvas_h = height + PADDING * 2

    scale = TARGET_HEIGHT / canvas_h
    out_w = max(1, round(canvas_w * scale))
    out_h = max(1, round(canvas_h * scale))

    for index, frame in enumerate(frames, start=1):
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        canvas.paste(frame, ((canvas_w - frame.width) // 2, (canvas_h - frame.height) // 2))
        canvas = canvas.resize((out_w, out_h), Image.LANCZOS)
        canvas.save(os.path.join(OUT_DIR, f"coin_{index}.png"))

    print(f"Готово: {len(frames)} кадров {out_w}x{out_h} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
