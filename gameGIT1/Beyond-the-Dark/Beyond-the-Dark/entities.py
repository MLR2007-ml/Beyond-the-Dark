import os
import pygame
from settings import WALL_COLOR, BASE_DIR

# --- Вид монеты: спрайт-лист assets/coin.jpg ---
COIN_SIZE = 34                          # размер кадра монеты на экране
COIN_IMAGE = os.path.join(BASE_DIR, "assets", "coin.jpg")
COIN_BG_COLOR = (255, 255, 255)         # белый фон спрайт-листа
COIN_BG_TOLERANCE = (34, 34, 34, 255)   # допуск на "почти белый"

_coin_frames_cache = None


def _frame_with_alpha(sheet, rect):
    """Вырезает кадр из листа и делает белый фон прозрачным."""
    frame = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), rect)

    mask = pygame.mask.from_threshold(frame, COIN_BG_COLOR, COIN_BG_TOLERANCE)
    mask.invert()   # 1 — пиксели монеты, 0 — белый фон
    alpha = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    frame.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return frame


def _load_coin_frames():
    """Нарезает спрайт-лист на кадры вращения (слева направо)."""
    try:
        sheet = pygame.image.load(COIN_IMAGE)
    except (pygame.error, FileNotFoundError, OSError):
        return [], 0

    mask = pygame.mask.from_threshold(sheet, COIN_BG_COLOR, COIN_BG_TOLERANCE)
    mask.invert()   # оставляем только сами монеты, фон отбрасываем
    rects = [r for r in mask.get_bounding_rects() if r.width > 4 and r.height > 4]
    if not rects:
        return [], 0
    rects.sort(key=lambda r: r.x)

    scale = COIN_SIZE / max(r.height for r in rects)
    frames = []
    for rect in rects:
        frame = _frame_with_alpha(sheet, rect)
        size = (max(1, int(round(frame.get_width() * scale))),
                max(1, int(round(frame.get_height() * scale))))
        scaled = pygame.transform.smoothscale(frame, size)

        canvas = pygame.Surface((COIN_SIZE, COIN_SIZE), pygame.SRCALPHA)
        canvas.blit(scaled, scaled.get_rect(center=(COIN_SIZE // 2, COIN_SIZE // 2)))
        frames.append(canvas)

    return frames, max(range(len(rects)), key=lambda i: rects[i].width)


def _build_fallback_frames():
    """Резервные кадры (рисуются кодом), если спрайт-лист не найден."""
    base = COIN_SIZE // 2
    height = base - 2
    widths = [3, 6, 9, 13, base, 13, 9, 6]
    frames = []
    for w in widths:
        art = pygame.Surface((base, base), pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, w, height)
        rect.center = (base // 2, base // 2)
        pygame.draw.ellipse(art, (163, 98, 0), rect)

        inner = rect.inflate(-2, -2)
        if inner.width > 0 and inner.height > 0:
            pygame.draw.ellipse(art, (255, 182, 18), inner)

        light = rect.inflate(-4, -4)
        if light.width > 0 and light.height > 0:
            light.move_ip(-1, -1)
            pygame.draw.ellipse(art, (255, 224, 112), light)

        frames.append(pygame.transform.scale(art, (COIN_SIZE, COIN_SIZE)))
    return frames, widths.index(max(widths))


def _get_coin_frames():
    """Кадры монеты (кэшируются, грузятся при первом обращении)."""
    global _coin_frames_cache
    if _coin_frames_cache is None:
        frames, front_index = _load_coin_frames()
        if not frames:
            frames, front_index = _build_fallback_frames()
        _coin_frames_cache = (frames, front_index)
    return _coin_frames_cache


# Направления разлетающихся искр при сборе монеты
_COIN_SPARKS = ((-1.0, -0.35), (0.95, -0.6), (0.35, 1.0), (-0.9, 0.65))


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(WALL_COLOR)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


class Coin(pygame.sprite.Sprite):
    SPIN_SPEED = 4          # тиков на один кадр вращения
    COLLECT_DURATION = 18   # тиков на анимацию сбора

    def __init__(self, x, y):
        super().__init__()
        self.frame_index = 0
        self.anim_timer = 0
        self.collecting = False
        self.collect_timer = 0

        self.frames, self.front_index = _get_coin_frames()
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.x = x + 15
        self.rect.y = y + 15

    def update(self):
        # Анимация сбора доигрывается, пока спрайт не удалится
        if self.collecting:
            self.collect_timer += 1
            self._draw_collect(self.collect_timer / self.COLLECT_DURATION)
            if self.collect_timer >= self.COLLECT_DURATION:
                self.kill()
            return

        # Постоянное вращение монеты
        self.anim_timer += 1
        if self.anim_timer >= self.SPIN_SPEED:
            self.anim_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            center = self.rect.center
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=center)

    def collect(self):
        """Запускает анимацию сбора: кольцо + растворяющаяся монета + искры."""
        if self.collecting:
            return
        self.collecting = True
        self.collect_timer = 0

        center = self.rect.center
        size = COIN_SIZE * 2 + 24
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=center)
        self._fx_center = (size // 2, size // 2)
        self._draw_collect(0.0)

    def _draw_collect(self, progress):
        progress = max(0.0, min(1.0, progress))
        fade = 1.0 - progress
        self.image.fill((0, 0, 0, 0))
        cx, cy = self._fx_center

        # Расходящееся кольцо
        ring_alpha = int(210 * fade)
        if ring_alpha > 0:
            radius = int(9 + 17 * progress)
            pygame.draw.circle(self.image, (255, 215, 0, ring_alpha), (cx, cy), radius, 2)

        # Монета подрастает, подпрыгивает и растворяется
        grown = max(1, int(COIN_SIZE * (1 + 0.7 * progress)))
        coin = pygame.transform.scale(self.frames[self.front_index], (grown, grown))
        coin.set_alpha(int(255 * fade))
        self.image.blit(coin, coin.get_rect(center=(cx, cy - int(16 * progress))))

        # Разлетающиеся искры
        spark_alpha = int(255 * fade)
        if spark_alpha > 0:
            for dx, dy in _COIN_SPARKS:
                dist = 5 + 20 * progress
                spark_pos = (cx + int(dx * dist), cy + int(dy * dist))
                pygame.draw.circle(self.image, (255, 236, 150, spark_alpha), spark_pos, 2)
