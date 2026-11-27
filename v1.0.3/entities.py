# entities.py
"""Стены, монеты, шипы, рычаги, мосты, порталы и скелеты-враги."""
import glob
import math
import os
import random
import re

import pygame

import settings

# Палитры блоков по уровням: основа, свет, тень, блик и цвет нароста на верхней
# кромке. style задаёт мелкие детали: мох в лесу, выщербленный камень в пещере,
# угольки в финале.
WALL_THEMES = {
    1: {"base": (70, 82, 52), "light": (118, 138, 86), "dark": (34, 42, 30),
        "accent": (150, 172, 102), "top": (104, 156, 76), "soil": (104, 84, 56),
        "style": "moss"},
    2: {"base": (64, 66, 88), "light": (100, 104, 132), "dark": (32, 34, 52),
        "accent": (128, 134, 162), "soil": (78, 74, 84), "style": "stone"},
    3: {"base": (84, 54, 56), "light": (158, 110, 90), "dark": (34, 22, 26),
        "accent": (250, 132, 64), "soil": (102, 62, 50), "style": "ember"},
}

_BLOCK_TILE = 50          # сторона клетки сетки уровня (main.BLOCK)


def _clamp_byte(value):
    return max(0, min(255, int(round(value))))


def _shift(color, delta):
    """Осветляет (delta > 0) или затемняет цвет на delta."""
    return tuple(_clamp_byte(channel + delta) for channel in color)


def _mix(color, other, ratio):
    """Смешивает два цвета: ratio = 0 — color, ratio = 1 — other."""
    return tuple(int(round(color[i] + (other[i] - color[i]) * ratio)) for i in range(3))


def _block_seed(x, y):
    """Постоянный seed для блока по его мировым координатам."""
    return ((int(x) // _BLOCK_TILE) * 73856093) ^ ((int(y) // _BLOCK_TILE) * 19349663)


def _stone_patch(image, center_x, center_y, radius_x, radius_y, color, rng,
                 edge_color=None):
    """Рыхлое пятно породы: рваный край тает в основе блока.

    edge_color — цвет основы: края подмешиваются к нему, поэтому вкрапление
    не выглядит наклейкой поверх камня.
    """
    width, height = image.get_size()
    rim = _mix(color, edge_color if edge_color else color, 0.55)
    light_color = _shift(color, 3)
    dark_color = _shift(color, -5)
    for offset_y in range(-radius_y, radius_y + 1):
        ratio = 1.0 - (offset_y / (radius_y + 0.6)) ** 2
        half = int(round(radius_x * math.sqrt(max(0.0, ratio))))
        if half <= 0:
            continue
        row = center_y + offset_y
        if not 0 <= row < height:
            continue
        left = max(1, center_x - half)
        right = min(width - 1, center_x + half + 1)
        while left < right and rng.random() < 0.4:      # рваный край
            left += 1
        while right > left and rng.random() < 0.4:
            right -= 1
        if right - left < 3:
            continue
        if abs(offset_y) >= radius_y:
            tone = rim
        elif offset_y < 0:
            tone = light_color
        elif offset_y > radius_y // 2:
            tone = dark_color
        else:
            tone = color
        image.fill(tone, (left, row, right - left, 1))
        if left - 1 > 0 and rng.random() < 0.3:          # крошка у края
            image.fill(rim, (left - 1, row, 1, 1))
        if right < width - 1 and rng.random() < 0.3:
            image.fill(rim, (right, row, 1, 1))


def _paint_block(image, theme, seed, exposed=(True, True, True, True)):
    """Рисует текстуру блока: грунт, крапины, трещины и объём по граням.

    exposed — (сверху, снизу, слева, справа): True, если соседнего блока с этой
    стороны нет. Открытые грани получают светлую/тёмную кромку, скрытые — тонкий
    шов, поэтому ряд блоков читается как кладка, а не как одна плоская плита.
    """
    palette = WALL_THEMES.get(theme, WALL_THEMES[1])
    base, light, dark = palette["base"], palette["light"], palette["dark"]
    accent, style = palette["accent"], palette["style"]
    width, height = image.get_size()
    rng = random.Random(seed)
    tone = rng.randint(-6, 6)          # блоки чуть отличаются по яркости

    # 1. Основа: сверху светлее, к низу темнее — появляется объём.
    # Скрытая верхняя грань не подсвечивается, иначе в стопке блоков виден светлый шов.
    top_open, bottom_open, left_open, right_open = exposed
    bands = max(10, height // 5)      # высокие монолиты не должны «полосить»
    band_height = height / bands
    top_shade = _shift(base, (18 if top_open else -6) + tone)
    bottom_shade = _shift(base, (-26 if bottom_open else -15) + tone)
    for band in range(bands):
        top = int(round(band * band_height))
        bottom = int(round((band + 1) * band_height))
        image.fill(_mix(top_shade, bottom_shade, band / (bands - 1)),
                   (0, top, width, max(1, bottom - top)))

    # 2. Пятна породы: мелкие вкрапления, блок перестаёт быть однотонным.
    # Количество зависит от площади — длинная полоса пола не остаётся пустой.
    patch_count = max(2, int(width * height / 1600))
    max_radius_x = max(4, min(14, width // 10))
    max_radius_y = max(3, height // 13)
    for _ in range(patch_count):
        radius_x = rng.randint(3, max_radius_x)
        radius_y = rng.randint(2, max_radius_y)
        center_x = rng.randint(radius_x + 2, max(radius_x + 3, width - radius_x - 3))
        center_y = rng.randint(radius_y + 7, max(radius_y + 8, height - radius_y - 4))
        mix_ratio = rng.uniform(0.12, 0.26)
        target = light if rng.random() < 0.3 else dark
        _stone_patch(image, center_x, center_y, radius_x, radius_y,
                     _mix(base, target, mix_ratio), rng, base)

    # 3. Слоистость: прерывистая линия — намёк на осадочную породу
    for _ in range(max(1, width // 130)):
        line_y = rng.randrange(height // 3, max(height // 3 + 1, height - 5))
        start = rng.randrange(2, max(3, width - 14))
        end = min(width - 2, start + rng.randint(10, max(11, min(width // 2, 130))))
        image.fill(_mix(base, dark, 0.18), (start, line_y, end - start, 1))
        if end - start > 12:
            image.fill(_mix(base, dark, 0.11),
                       (start + 5, line_y + 1, end - start - 9, 1))

    # 4. Зерно: редкие неяркие крапины дают «каменную» фактуру
    soft_light = _mix(light, base, 0.5)
    soft_dark = _mix(dark, base, 0.3)
    ember_dust = 0.2 if style == "ember" else 0.05   # угольки — только у лавы
    for _ in range(max(8, width * height // 150)):
        px = rng.randrange(2, max(3, width - 2))
        py = rng.randrange(6, max(7, height - 3))
        size = 1 if rng.random() < 0.7 else 2
        roll = rng.random()
        if roll < ember_dust:
            color = accent
        elif roll < ember_dust + 0.4:
            color = soft_light
        else:
            color = soft_dark
        image.fill(color, (px, py, size, size))

    # 5. Трещины: короткие изломы, у угольной темы — светящиеся прожилки
    for _ in range(max(1, width // 90)):
        cx = rng.randrange(6, max(7, width - 10))
        cy = rng.randrange(6, max(7, height - 12))
        points = [(cx, cy)]
        for _ in range(rng.randint(2, 3)):
            cx = max(2, min(width - 3, cx + rng.choice((-2, -1, 1, 2))))
            cy = max(2, min(height - 3, cy + rng.randint(2, 4)))
            points.append((cx, cy))
        crack = _mix(dark, base, 0.35)          # мягкий излом, а не чёрный волос
        if style == "ember" and rng.random() < 0.35:
            crack = _mix(accent, base, 0.2)   # светящаяся прожилка

        pygame.draw.lines(image, crack, False, points, 1)

    # 6. Шов кладки по низу: тёмная линия с разрывами, чтобы блоки читались
    seam = _mix(dark, base, 0.15)
    x = 0
    while x < width:
        run = rng.randint(5, 13)
        if rng.random() < 0.85:
            image.fill(seam, (x, height - 1, min(run, width - x), 1))
        x += run

    # 7. Верхняя грань: светлая кромка и нарост (мох, камень, угольки)
    if top_open:
        if style == "moss":
            moss = palette["top"]
            soil = palette["soil"]
            moss_light = _mix(moss, accent, 0.5)
            depth = 4
            for x in range(width):
                depth += rng.choice((-1, 0, 0, 1))     # волнистая кромка мха
                depth = max(2, min(7, depth))
                if rng.random() < 0.05:
                    depth = 1
                image.fill(moss, (x, 0, 1, depth))
                if rng.random() < 0.45:
                    image.fill(moss_light, (x, 0, 1, 1))
                if rng.random() < 0.14:                # свисающая травинка
                    image.fill(_mix(moss, dark, 0.3), (x, depth, 1, rng.randint(1, 3)))
                # под мхом — полоска грунта, чтобы платформа читалась объёмно
                image.fill(_mix(soil, base, 0.3 + rng.random() * 0.35), (x, depth, 1, 2))
        else:
            image.fill(light, (0, 0, width, 2))
            image.fill(_mix(light, accent, 0.5), (0, 0, width, 1))
        if style == "stone":
            for x in range(width):
                if rng.random() < 0.3:       # выщербленная кромка
                    image.fill(dark, (x, 2, 1, 1))
                if rng.random() < 0.16:
                    image.fill(accent, (x, 0, 1, 1))
            image.fill(_mix(light, base, 0.45), (0, 2, width, 2))   # жёлоб под кромкой
            # тень под кромкой, чтобы плита не выглядела плоской
            image.fill(_mix(base, dark, 0.45), (2, 4, max(1, width - 4), 1))
        elif style == "ember":               # тлеющие угольки
            for x in range(width):
                if rng.random() < 0.18:
                    image.fill(_mix(accent, base, 0.25), (x, 0, 1, 1))
            image.fill(_mix(light, base, 0.5), (0, 2, width, 2))    # жёлоб под кромкой
            image.fill(_mix(base, dark, 0.45), (2, 4, max(1, width - 4), 1))

    # 8. Остальные грани: сначала бока, потом низ — низ перекрывает углы
    if left_open:
        image.fill(light, (0, 0, 2, height))
        image.fill(_mix(light, accent, 0.35), (0, 0, 1, height))
    if right_open:
        image.fill(dark, (width - 2, 0, 2, height))
    if bottom_open:
        image.fill(dark, (0, height - 2, width, 2))
        image.fill(_shift(dark, -12), (0, height - 1, width, 1))

    # 9. Швы с соседними блоками — тонкая линия вместо жёсткой сетки
    seam_soft = _mix(base, dark, 0.62)
    if not top_open:
        image.fill(seam_soft, (0, 0, width, 1))
    if not left_open:
        image.fill(seam_soft, (0, 0, 1, height))


_COIN_FRAME_DIR = os.path.join(settings.ASSETS_DIR, "coin_spin")
_coin_frames_cache = None


def _numeric_key(path):
    match = re.search(r"(\d+)", os.path.basename(path))
    return int(match.group(1)) if match else 0


def load_coin_frames():
    """Загружает готовые PNG-кадры вращения монеты (assets/coin_spin)."""
    global _coin_frames_cache
    if _coin_frames_cache is not None:
        return _coin_frames_cache

    frames = []
    if os.path.isdir(_COIN_FRAME_DIR):
        paths = sorted(glob.glob(os.path.join(_COIN_FRAME_DIR, "*.png")), key=_numeric_key)
        for path in paths:
            try:
                image = pygame.image.load(path).convert_alpha()
            except (pygame.error, OSError) as exc:
                print(f"[ОШИБКА] Не удалось загрузить {path}: {exc}")
                continue
            height = settings.COIN_SIZE
            width = max(1, round(image.get_width() * height / image.get_height()))
            frames.append(pygame.transform.smoothscale(image, (width, height)))

    if not frames:
        fallback = pygame.Surface((settings.COIN_SIZE, settings.COIN_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (240, 200, 70), (settings.COIN_SIZE // 2,) * 2,
                           settings.COIN_SIZE // 2)
        frames = [fallback]
        print("[ПРЕДУПРЕЖДЕНИЕ] Кадры монеты не найдены — используется круг")

    _coin_frames_cache = frames
    print(f"[УСПЕХ] Монета: {len(frames)} кадров вращения")
    return frames


class Wall(pygame.sprite.Sprite):
    """Блок уровня: текстура зависит от темы, объём — от открытых граней."""

    def __init__(self, x, y, width, height, theme=1,
                 exposed=(True, True, True, True)):
        super().__init__()
        self.image = pygame.Surface((width, height))
        _paint_block(self.image, theme, _block_seed(x, y), exposed)
        self.rect = self.image.get_rect(topleft=(x, y))


class Spike(pygame.sprite.Sprite):
    """Спрятанные шипы: тускло поблёскивают, но ранят игрока."""

    HEIGHT = 20          # высота зубьев над полом
    COUNT = 3            # сколько зубьев на один блок

    def __init__(self, x, y, width=40):
        super().__init__()
        self.width = width
        self.image = pygame.Surface((width, self.HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pulse = False
        self._draw(False)

    def _draw(self, highlighted):
        self.image.fill((0, 0, 0, 0))
        if highlighted:
            body, shade, edge, tip = (170, 162, 178), (88, 82, 98), (240, 234, 246), (255, 252, 255)
        else:
            body, shade, edge, tip = (78, 72, 90), (38, 35, 46), (146, 138, 158), (198, 190, 208)

        bottom = self.HEIGHT - 1
        step = self.width / self.COUNT
        for index in range(self.COUNT):
            left = int(index * step) + 1
            right = int((index + 1) * step) - 1
            if right - left < 6:
                continue
            middle = (left + right) // 2
            apex = (middle, 2)
            # Тело зуба и затемнённая правая грань — объём
            pygame.draw.polygon(self.image, body, ((left, bottom), apex, (right, bottom)))
            pygame.draw.polygon(self.image, shade, (apex, (right, bottom), (middle, bottom)))
            # Светлая кромка по левому скату: зуб читается даже на тёмном полу
            pygame.draw.lines(self.image, edge, False,
                              ((middle, bottom), (left, bottom), apex))
            pygame.draw.rect(self.image, tip, (middle - 1, 2, 2, 2))
        # Тёмное основание, чтобы полоса шипов отделялась от пола
        pygame.draw.rect(self.image, shade, (0, bottom - 2, self.width, 3))
        # В покое шипы приглушены, но силуэт остаётся виден
        self.image.set_alpha(255 if highlighted else 205)

    def update(self, player):
        near = abs(player.rect.centerx - self.rect.centerx) < 95
        if near != self.pulse:
            self.pulse = near
            self._draw(near)

    def damage_rect(self):
        return pygame.Rect(self.rect.x, self.rect.y + 6,
                           self.rect.width, self.rect.height - 6)


class Coin(pygame.sprite.Sprite):
    SPIN_SEQUENCE = (0, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1)
    FRAME_TICKS = 4

    def __init__(self, x, y):
        super().__init__()
        self.frames = load_coin_frames()
        self.frame_index = 0
        self.anim_timer = 0
        self.bob_timer = random.randint(0, 120)
        self.image = self.frames[0]

        self.rect = pygame.Rect(0, 0, max(16, self.image.get_width() - 8),
                                max(16, self.image.get_height() - 10))
        self.rect.center = (int(x), int(y))
        self.draw_rect = self.image.get_rect(center=self.rect.center)

    def update(self):
        self.anim_timer += 1
        if self.anim_timer >= self.FRAME_TICKS:
            self.anim_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.SPIN_SEQUENCE)

        self.bob_timer += 1
        bob = int(round(2.5 * pygame.math.Vector2(1, 0).rotate(self.bob_timer * 4).y))
        self.image = self.frames[self.SPIN_SEQUENCE[self.frame_index]]
        self.draw_rect = self.image.get_rect(center=(self.rect.centerx,
                                                     self.rect.centery + bob))


class CoinBurst:
    """Искры и «+1» при подборе монеты или хилки."""

    def __init__(self, x, y, label="+1", color=(255, 226, 120)):
        self.timer = 0
        self.life = 34
        self.x = x
        self.y = y
        self.label = label
        self.color = color
        rng = random.Random(x * 131 + y)
        self.particles = []
        for _ in range(9):
            angle = rng.uniform(0, 360)
            speed = rng.uniform(1.0, 3.0)
            self.particles.append((angle, speed))

    def update(self):
        self.timer += 1

    @property
    def done(self):
        return self.timer >= self.life

    def draw(self, surface, font=None, offset=(0, 0)):
        for base_angle, speed in self.particles:
            angle = base_angle + self.timer * 7
            radius = speed * self.timer * 1.3
            direction = pygame.math.Vector2(1, 0).rotate(angle)
            x = self.x + offset[0] + direction.x * radius
            y = self.y + offset[1] + direction.y * radius + self.timer * 0.35
            color = self.color if self.timer % 4 < 2 else (255, 190, 60)
            pygame.draw.rect(surface, color, (int(x), int(y), 3, 3))
        if font and self.timer < 24:
            font.draw(surface, self.label, (self.x + offset[0],
                                            self.y + offset[1] - 14 - self.timer * 0.9),
                      color=settings.TEXT_ACCENT, anchor="center")


class Heart:
    """Хилка: поднимает одно сердце здоровья, если оно потеряно."""

    WIDTH, HEIGHT = 26, 24

    def __init__(self, x, floor_top, block=50, heal=None):
        self.heal = settings.HEART_HEAL if heal is None else heal
        self.image = self._render()
        self.rect = self.image.get_rect(midbottom=(int(x + block // 2),
                                                   int(floor_top - 4)))
        self.timer = random.randint(0, 90)
        self.bob = 0
        self.glow = pygame.Surface((self.WIDTH + 20, self.HEIGHT + 20), pygame.SRCALPHA)
        for radius, alpha in ((16, 26), (12, 40), (8, 60)):
            pygame.draw.circle(self.glow, (255, 90, 110, alpha),
                               (self.glow.get_width() // 2, self.glow.get_height() // 2),
                               radius)

    def _render(self):
        image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        red, light, dark = (222, 52, 66), (255, 138, 148), (138, 22, 38)
        pygame.draw.rect(image, red, (2, 6, 9, 6))
        pygame.draw.rect(image, red, (14, 6, 9, 6))
        pygame.draw.rect(image, red, (4, 12, 18, 5))
        pygame.draw.rect(image, red, (7, 17, 12, 4))
        pygame.draw.rect(image, red, (10, 21, 6, 3))
        pygame.draw.rect(image, dark, (2, 6, 9, 2))
        pygame.draw.rect(image, dark, (14, 6, 9, 2))
        pygame.draw.rect(image, dark, (4, 16, 18, 2))
        pygame.draw.rect(image, light, (5, 7, 4, 3))
        pygame.draw.rect(image, light, (15, 9, 3, 2))
        return image

    def update(self):
        self.timer += 1
        self.bob = int(round(math.sin(self.timer * 0.09) * 2.5))

    def draw(self, surface, offset=(0, 0)):
        center = (self.rect.x + offset[0] + self.WIDTH // 2,
                  self.rect.y + offset[1] + self.HEIGHT // 2 + self.bob)
        glow = self.glow
        glow.set_alpha(150 + int(60 * math.sin(self.timer * 0.09)))
        surface.blit(glow, (center[0] - glow.get_width() // 2,
                            center[1] - glow.get_height() // 2))
        surface.blit(self.image, (center[0] - self.WIDTH // 2,
                                  center[1] - self.HEIGHT // 2))


class Lever(pygame.sprite.Sprite):
    """Рычаг: дёргается по E и опускает мост через пропасть."""

    WIDTH, HEIGHT = 44, 48

    def __init__(self, x, floor_top, block=50):
        super().__init__()
        self.image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_rect(midbottom=(x + block // 2, floor_top))
        self.pulled = False
        self.progress = 0.0
        self.timer = 0
        self._render()

    def _render(self):
        self.image.fill((0, 0, 0, 0))
        cx = self.WIDTH // 2
        base_y = self.HEIGHT - 4
        # каменная тумба
        pygame.draw.rect(self.image, (58, 54, 66), (cx - 14, base_y - 9, 28, 11))
        pygame.draw.rect(self.image, (96, 90, 106), (cx - 14, base_y - 9, 28, 3))
        pygame.draw.rect(self.image, (34, 31, 40), (cx - 14, base_y - 1, 28, 3))
        # стойка
        pygame.draw.rect(self.image, (78, 72, 88), (cx - 3, base_y - 27, 6, 20))
        axle = (cx, base_y - 25)
        angle = math.radians(-40 + 80 * self.progress)
        length = 22
        tip = (axle[0] + math.sin(angle) * length,
               axle[1] - math.cos(angle) * length)
        pygame.draw.line(self.image, (156, 156, 172), axle, tip, 4)
        pygame.draw.circle(self.image, (34, 26, 20), axle, 4)
        knob = (214, 176, 74) if self.pulled else (168, 140, 96)
        pygame.draw.circle(self.image, knob, (int(tip[0]), int(tip[1])), 5)
        pygame.draw.circle(self.image, (58, 44, 26), (int(tip[0]), int(tip[1])), 5, 1)
        if self.pulled:
            pygame.draw.circle(self.image, (255, 224, 132), (int(tip[0]) - 1,
                                                             int(tip[1]) - 1), 2)

    def pull(self):
        """Возвращает True при первом срабатывании."""
        if self.pulled:
            return False
        self.pulled = True
        return True

    def update(self):
        self.timer += 1
        target = 1.0 if self.pulled else 0.0
        if abs(self.progress - target) > 0.02:
            self.progress += 0.08 if target > self.progress else -0.08
            self.progress = max(0.0, min(1.0, self.progress))
            self._render()

    def draw(self, surface, offset=(0, 0)):
        surface.blit(self.image, (self.rect.x + offset[0], self.rect.y + offset[1]))


class Bridge:
    """Мост через пропасть: пока не опущен — просто цепи между опорами."""

    THICKNESS = 14

    def __init__(self, x, width, top):
        self.rect = pygame.Rect(int(x), int(top), int(width), self.THICKNESS)
        self.progress = 0.0
        self.lowering = False
        self.solid = False

    def lower(self):
        self.lowering = True

    def update(self):
        if self.lowering and self.progress < 1.0:
            self.progress = min(1.0, self.progress + 0.025)
            if self.progress >= 1.0:
                self.solid = True

    def draw(self, surface, offset=(0, 0)):
        x = self.rect.x + offset[0]
        y = self.rect.y + offset[1]
        width = self.rect.width
        height = self.rect.height
        # опоры по краям
        for post_x in (x - 7, x + width - 1):
            pygame.draw.rect(surface, (56, 44, 32), (post_x, y - 30, 8, 30))
            pygame.draw.rect(surface, (92, 74, 52), (post_x, y - 30, 8, 3))
        # цепи
        chain_y = y - 26
        for i in range(0, width, 6):
            pygame.draw.rect(surface, (92, 88, 82), (x + i, chain_y, 3, 2))
        drawn = int(width * self.progress)
        plank = max(14, width // 7)
        for i in range(0, drawn, plank):
            w = min(plank - 1, drawn - i)
            pygame.draw.rect(surface, (110, 78, 46), (x + i, y, w, height))
            pygame.draw.rect(surface, (146, 108, 64), (x + i, y, w, 3))
            pygame.draw.rect(surface, (70, 48, 28), (x + i, y + height - 2, w, 2))


class Goal:
    """Светящийся портал в конце уровня."""

    WIDTH, HEIGHT = 42, 76

    def __init__(self, x, floor_top, block=50):
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self.rect.midbottom = (x + block // 2, floor_top)
        self.timer = 0
        self.glow = pygame.Surface((self.WIDTH - 12, self.HEIGHT - 18), pygame.SRCALPHA)

    def update(self):
        self.timer += 1

    def draw(self, surface, offset=(0, 0)):
        x = self.rect.x + offset[0]
        y = self.rect.y + offset[1]
        w, h = self.rect.size
        pulse = 120 + int(70 * math.sin(self.timer * 0.07))
        self.glow.fill((0, 0, 0, 0))
        self.glow.fill((70, 196, 214, pulse))
        pygame.draw.rect(self.glow, (176, 248, 252, min(255, pulse + 70)), (2, 0, w - 16, 4))
        surface.blit(self.glow, (x + 6, y + 10))
        # каменная арка
        stone, light = (72, 70, 82), (116, 116, 132)
        pygame.draw.rect(surface, stone, (x, y + 8, 7, h - 8))
        pygame.draw.rect(surface, stone, (x + w - 7, y + 8, 7, h - 8))
        pygame.draw.rect(surface, stone, (x, y, w, 10))
        pygame.draw.rect(surface, light, (x, y, w, 2))
        pygame.draw.rect(surface, (44, 42, 52), (x + w - 7, y + 8, 2, h - 8))
        # искры
        for index in range(4):
            px = x + 9 + (index * 9 + self.timer // 5) % max(1, w - 20)
            py = y + h - 14 - (self.timer // 3 + index * 19) % max(1, h - 30)
            pygame.draw.rect(surface, (206, 252, 255), (px, py, 2, 2))


# --- СПРАЙТ-ЛИСТ СКЕЛЕТА: assets/skeleton.jpg (4 кадра на белом фоне) ---
_SKELETON_BG = (254, 254, 254)        # цвет фона листа
_SKELETON_BG_TOLERANCE = 18           # запас на JPEG-шум вокруг фигуры
_SKELETON_HURT_TINT = (255, 96, 96)   # оттенок при попадании по скелету
_skeleton_frames_cache = None


def _skeleton_mask(surface):
    """Маска фигуры: всё, что светлее фона листа, становится прозрачным."""
    tolerance = (_SKELETON_BG_TOLERANCE,) * 3 + (255,)
    mask = pygame.mask.from_threshold(surface, _SKELETON_BG, tolerance)
    mask.invert()
    return mask


def _sheet_bands(sheet, strip=6, gap_ratio=0.03, min_gap=20):
    """Горизонтальные полосы кадров в спрайт-листе: [(x0, x1), ...]."""
    width, height = sheet.get_size()
    gap = max(min_gap, int(height * gap_ratio))
    occupied = []
    for x in range(0, width, strip):
        part = sheet.subsurface(pygame.Rect(x, 0, min(strip, width - x), height))
        occupied.append(_skeleton_mask(part).count() > 0)

    bands, start, blank = [], None, 0
    for index, hit in enumerate(occupied):
        x = index * strip
        if hit:
            if start is None:
                start = x
            blank = 0
        elif start is not None:
            blank += 1
            if blank * strip >= gap:
                bands.append((start, x - blank * strip + strip - 1))
                start, blank = None, 0
    if start is not None:
        bands.append((start, width - 1))
    return bands


def _cut_skeleton(band):
    """Вырезает фигуру из полосы листа и убирает белый фон (alpha)."""
    mask = _skeleton_mask(band)
    rects = mask.get_bounding_rects()
    if not rects:
        return None, None
    crop = band.subsurface(rects[0].unionall(rects[1:])).copy()
    mask = _skeleton_mask(crop)
    silhouette = mask.to_surface(setcolor=(255, 255, 255, 255),
                                 unsetcolor=(0, 0, 0, 0))
    frame = crop.convert_alpha()
    # оставляем цвет фигуры, но берём прозрачность из маски
    frame.blit(silhouette, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return frame, mask


def _foot_center(mask, rows=10):
    """Центр X ступней по нижней полосе кадра. Топор тоже лежит в этой полосе,
    поэтому в skeleton_frames() берётся медиана по всем кадрам."""
    width, height = mask.get_size()
    left = right = None
    for x in range(width):
        if any(mask.get_at((x, y)) for y in range(max(0, height - rows), height)):
            left = x if left is None else left
            right = x
    if left is None:
        return width / 2
    return (left + right) / 2


def _fallback_skeleton():
    """Простой костяной силуэт, если спрайт-лист не загрузился."""
    image = pygame.Surface((32, 54), pygame.SRCALPHA)
    bone = (236, 234, 222)
    pygame.draw.rect(image, bone, (9, 4, 14, 15))              # череп
    pygame.draw.rect(image, bone, (13, 19, 6, 10))             # позвоночник
    pygame.draw.rect(image, bone, (7, 29, 18, 8))              # таз
    pygame.draw.rect(image, bone, (7, 37, 5, 15))              # нога
    pygame.draw.rect(image, bone, (20, 37, 5, 15))             # нога
    pygame.draw.rect(image, (26, 22, 30), (11, 8, 4, 4))       # глазницы
    pygame.draw.rect(image, (26, 22, 30), (17, 8, 4, 4))
    pygame.draw.rect(image, (128, 76, 42), (25, 22, 3, 24))    # рукоять топора
    pygame.draw.rect(image, (172, 178, 192), (22, 16, 10, 10))  # лезвие
    return image


def skeleton_frames():
    """Кадры скелета из листа: {'right': [...], 'left': [...],
    'flash_right': [...], 'flash_left': [...]}. Результат кэшируется."""
    global _skeleton_frames_cache
    if _skeleton_frames_cache is not None:
        return _skeleton_frames_cache

    sheet = None
    try:
        sheet = pygame.image.load(settings.SKELETON_SHEET).convert()
    except (pygame.error, OSError) as exc:
        print(f"[ОШИБКА] Не удалось загрузить спрайт скелета: {exc}")

    cut = []
    if sheet is not None:
        height = sheet.get_height()
        for left, right in _sheet_bands(sheet):
            band = sheet.subsurface(
                pygame.Rect(left, 0, right - left + 1, height)).copy()
            frame, mask = _cut_skeleton(band)
            if frame is not None:
                cut.append((frame, _foot_center(mask)))

    if not cut:
        fallback = _fallback_skeleton()
        _skeleton_frames_cache = {
            "right": [fallback],
            "left": [pygame.transform.flip(fallback, True, False)],
        }
        return _skeleton_frames_cache

    heights = sorted(frame.get_height() for frame, _ in cut)
    body_height = heights[len(heights) // 2]        # медиана: кадр с замахом выше
    scale = settings.SKELETON_HEIGHT / max(1, body_height)

    anchors = sorted(anchor for _, anchor in cut)
    anchor = anchors[len(anchors) // 2]             # общий якорь, чтобы не «прыгало»
    half = max(max(anchor, frame.get_width() - anchor) for frame, _ in cut) * scale
    canvas_w = max(1, int(round(half * 2)))
    canvas_h = max(1, int(round(heights[-1] * scale)))

    def prepare(frame, flash):
        size = (max(1, int(round(frame.get_width() * scale))),
                max(1, int(round(frame.get_height() * scale))))
        scaled = pygame.transform.smoothscale(frame, size)
        if flash:      # красный оттенок при попадании: альфа костей сохраняется
            scaled.fill(_SKELETON_HURT_TINT, special_flags=pygame.BLEND_RGB_MULT)
        canvas = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
        canvas.blit(scaled, (int(round(canvas_w / 2 - anchor * scale)),
                             canvas_h - size[1]))
        return canvas

    right = [prepare(frame, False) for frame, _ in cut]
    flashes = [prepare(frame, True) for frame, _ in cut]
    _skeleton_frames_cache = {
        "right": right,
        "left": [pygame.transform.flip(frame, True, False) for frame in right],
        "flash_right": flashes,
        "flash_left": [pygame.transform.flip(frame, True, False) for frame in flashes],
    }
    return _skeleton_frames_cache


class Skeleton:
    """Скелет-воин пещеры: патрулирует, догоняет и бьёт топором."""

    # Кадры спрайт-листа: 0 — шаг вперёд, 1 — замах, 2 — удар, 3 — стойка
    IDLE_POSE = 3
    WALK_POSES = (0, 3)
    ATTACK_POSES = (1, 2, 3)
    IDLE_TICKS = 14
    WALK_TICKS = 8

    def __init__(self, x, floor_top):
        self.rect = pygame.Rect(0, 0, 26, 46)
        self.rect.midbottom = (int(x), int(floor_top))
        self.spawn_x = self.rect.centerx
        self.patrol = 150
        self.hp = settings.SKELETON_HP
        self.max_hp = settings.SKELETON_HP
        self.facing = -1
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.hurt_timer = 0
        self.dead = False
        self.death_timer = 0
        self.anim = 0
        self.wake_timer = settings.SKELETON_WAKE_TICKS
        # Готовые кадры: frames[facing][kind][index]
        self.frames = {facing: self._poses(facing) for facing in (1, -1)}
        self.flash_frames = {facing: self._poses(facing, flash=True)
                             for facing in (1, -1)}
        self.image = self.frames[1]["idle"][0]

    # --- Отрисовка ---
    def _poses(self, facing, flash=False):
        """Раскладывает кадры спрайт-листа по состояниям."""
        bank = skeleton_frames()
        key = ("left" if facing < 0 else "right") + ("_flash" if flash else "")
        sheet = bank.get(key) or []
        if not sheet:
            image = _fallback_skeleton()
            if facing < 0:
                image = pygame.transform.flip(image, True, False)
            return {"idle": [image], "walk": [image], "attack": [image]}

        def pick(index):
            return sheet[min(index, len(sheet) - 1)]

        return {
            "idle": [pick(self.IDLE_POSE)],
            "walk": [pick(index) for index in self.WALK_POSES],
            "attack": [pick(index) for index in self.ATTACK_POSES],
        }

    # --- Бой ---
    def take_damage(self, amount, direction=1):
        if self.dead:
            return False
        self.hp = max(0, self.hp - amount)
        self.hurt_timer = 12
        self.rect.x += 7 * direction
        # Попадание сбивает замах: скелет не может мгновенно контратаковать
        self.attack_timer = 0
        self.attack_cooldown = max(self.attack_cooldown, settings.SKELETON_HURT_STUN)
        if self.hp <= 0:
            self.dead = True
            self.death_timer = 0
        return self.dead

    def strike_rect(self):
        """Зона удара топором в активных кадрах замаха."""
        if self.dead or self.attack_timer <= 0:
            return None
        if not (settings.SKELETON_ATTACK_WINDUP
                <= self.attack_timer <= settings.SKELETON_ATTACK_WINDUP + 10):
            return None
        if self.facing > 0:
            return pygame.Rect(self.rect.right, self.rect.y + 4, 46, 34)
        return pygame.Rect(self.rect.left - 46, self.rect.y + 4, 46, 34)

    # --- Логика ---
    def update(self, player, walls):
        self.anim += 1
        if self.wake_timer > 0:
            self.wake_timer -= 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.dead:
            self.death_timer += 1
            self._update_animation()
            return

        dx = 0
        player_ok = player is not None and player.alive and self.wake_timer <= 0
        if player_ok:
            dx = player.rect.centerx - self.rect.centerx

        if player_ok and abs(dx) < settings.SKELETON_DETECT_RANGE:
            self.facing = 1 if dx > 0 else -1
            if abs(dx) > settings.SKELETON_ATTACK_RANGE:
                self.vel_x = self.facing * settings.SKELETON_CHASE_SPEED
            else:
                self.vel_x = 0.0
                if self.attack_timer <= 0 and self.attack_cooldown <= 0:
                    self.attack_timer = 1
        else:
            if self.rect.centerx <= self.spawn_x - self.patrol:
                self.facing = 1
            elif self.rect.centerx >= self.spawn_x + self.patrol:
                self.facing = -1
            self.vel_x = self.facing * settings.SKELETON_SPEED

        if self.attack_timer > 0:
            self.vel_x = 0.0
            self.attack_timer += 1
            if self.attack_timer >= settings.SKELETON_ATTACK_TICKS:
                self.attack_timer = 0
                self.attack_cooldown = settings.SKELETON_ATTACK_COOLDOWN

        # не сходим с уступа в пропасть
        if self.on_ground and self.vel_x != 0 and walls:
            probe = pygame.Rect(self.rect.centerx + (6 if self.vel_x > 0 else -10),
                                self.rect.bottom, 4, 8)
            if not any(probe.colliderect(wall.rect) for wall in walls):
                self.vel_x = 0.0

        self._physics(walls)
        if self.rect.top > settings.SCREEN_HEIGHT + 120:   # упал в пропасть
            self.dead = True
            self.death_timer = 60
        self._update_animation()

    def _update_animation(self):
        """Выбирает кадр: ожидание, ходьба или удар."""
        if self.dead:
            self.image = self.frames[self.facing]["idle"][0]
            return
        if self.attack_timer > 0:
            kind = "attack"
            frames = self.frames[self.facing][kind]
            windup = settings.SKELETON_ATTACK_WINDUP
            if self.attack_timer < windup:
                index = 0            # замах: топор поднят над головой
            elif self.attack_timer <= windup + 10:
                index = 1            # удар: топор в земле + дуга (активные кадры)
            else:
                index = 2            # возврат в стойку
            index = min(index, len(frames) - 1)
        elif abs(self.vel_x) > 0.2:
            kind = "walk"
            frames = self.frames[self.facing][kind]
            index = (self.anim // self.WALK_TICKS) % len(frames)
        else:
            kind = "idle"
            frames = self.frames[self.facing][kind]
            index = (self.anim // self.IDLE_TICKS) % len(frames)
        if self.hurt_timer > 0:
            flash = self.flash_frames[self.facing][kind]
            self.image = flash[index % len(flash)]
        else:
            self.image = frames[index]

    def _physics(self, walls):
        self.rect.x += int(self.vel_x)
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_x > 0:
                    self.rect.right = wall.rect.left
                elif self.vel_x < 0:
                    self.rect.left = wall.rect.right

        self.vel_y = min(15.0, self.vel_y + 0.7)
        self.rect.y += int(self.vel_y)
        self.on_ground = False
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_y > 0:
                    self.rect.bottom = wall.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = wall.rect.bottom
                    self.vel_y = 0

    # --- Отрисовка на экране ---
    def draw(self, surface, offset=(0, 0)):
        x = self.rect.midbottom[0] + offset[0]
        y = self.rect.midbottom[1] + offset[1]
        image = self.image
        if self.dead:
            fade = max(30, 255 - self.death_timer * 7)
            image.set_alpha(fade)
            surface.blit(image, image.get_rect(
                midbottom=(x, y + min(16, self.death_timer // 2))))
            image.set_alpha(255)
            return

        sway = -5 * self.facing if 0 < self.attack_timer <= settings.SKELETON_ATTACK_TICKS else 0
        rect = image.get_rect(midbottom=(x + sway, y))
        surface.blit(image, rect)
        if self.hp < self.max_hp or abs(rect.centerx - LOGICAL_CENTER) < 240:
            self._draw_hp(surface, rect.centerx, rect.top - 8)

    def _draw_hp(self, surface, cx, bottom):
        width, height = 40, 5
        bar = pygame.Rect(0, 0, width, height)
        bar.midbottom = (int(cx), int(bottom))
        pygame.draw.rect(surface, (16, 13, 18), bar.inflate(4, 4))
        ratio = self.hp / max(1, self.max_hp)
        if ratio > 0:
            pygame.draw.rect(surface, (198, 54, 44),
                             (bar.x, bar.y, max(1, int(width * ratio)), height))
        pygame.draw.rect(surface, (236, 150, 112), bar, 1)


LOGICAL_CENTER = 400
