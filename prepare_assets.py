"""Подготовка ассетов дракона.

Запускать один раз (нужен Pillow):
    python prepare_assets.py

Скрипт:
  * убирает белый фон у boss_dragon.jpg;
  * разбирает attack_dragon.gif на 8 кадров и тоже убирает белый фон;
  * сохраняет кадры в assets/boss/ с общим холстом, чтобы анимация не "дёргалась".

Сама игра использует только pygame и готовые PNG из assets/boss/.
"""

import os

from PIL import Image, ImageSequence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE_DIR, "assets")
OUT_DIR = os.path.join(ASSETS, "boss")

WHITE_CUTOFF = 232   # пиксели светлее этого считаются фоном


def remove_white(image):
    """Возвращает RGBA-копию с прозрачным белым фоном (с мягким краем)."""
    image = image.convert("RGBA")
    pixels = image.load()
    w, h = image.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            whiteness = min(r, g, b)
            if whiteness >= WHITE_CUTOFF:
                pixels[x, y] = (r, g, b, 0)
            elif whiteness >= WHITE_CUTOFF - 18:
                # Мягкий край: полупрозрачные пиксели вместо белой каймы
                alpha = int(255 * (WHITE_CUTOFF - whiteness) / 18)
                pixels[x, y] = (r, g, b, max(0, min(255, alpha)))
            else:
                pixels[x, y] = (r, g, b, 255)
    return image


def union_bbox(images):
    boxes = [im.getbbox() for im in images if im.getbbox()]
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (x0, y0, x1, y1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    idle = remove_white(Image.open(os.path.join(ASSETS, "boss_dragon.jpg")))

    gif = Image.open(os.path.join(ASSETS, "attack_dragon.gif"))
    attack = [remove_white(frame) for frame in ImageSequence.Iterator(gif)]

    # Общий холст: и стойка, и все кадры атаки стоят на одном месте
    box = union_bbox([idle] + attack)
    pad = 2
    box = (max(0, box[0] - pad), max(0, box[1] - pad),
           min(idle.width, box[2] + pad), min(idle.height, box[3] + pad))
    cell = (box[2] - box[0], box[3] - box[1])

    idle.crop(box).save(os.path.join(OUT_DIR, "boss_dragon.png"))
    for index, frame in enumerate(attack, start=1):
        frame.crop(box).save(os.path.join(OUT_DIR, f"attack_{index}.png"))

    print(f"Готово: стойка + {len(attack)} кадров атаки, размер кадра {cell}")
    print(f"Папка: {OUT_DIR}")


if __name__ == "__main__":
    main()
