# pixelfont.py
"""Пиксельный шрифт и простые UI-примитивы в ретро-стиле."""
import os

import pygame

import settings

# Шаблон сердечка 7x6 (для полоски здоровья)
_HEART = (
    ".XX.XX.",
    "XXXXXXX",
    "XXXXXXX",
    ".XXXXX.",
    "..XXX..",
    "...X...",
)

# В PixelifySans кириллические «О» и «П» отсутствуют (вместо них пустая рамка).
# «О» совпадает по форме с латинской «O», а «П» дорисовываем на сетке шрифта:
# штрихи 2px, высота 10px (строки 5..14 базового кегля), ширина 9px.
_SUBSTITUTES = {"О": "O"}
_CUSTOM_GLYPHS = {
    "П": ((1, 5, 7, 2),     # верхняя перекладина
          (1, 5, 2, 10),    # левая стойка
          (7, 5, 1, 10)),   # правая стойка
}
_CUSTOM_ADVANCE = {"П": 9}

_HEART_COLOR = (224, 62, 70)
_HEART_HIGHLIGHT = (255, 132, 122)
_HEART_EMPTY = (66, 58, 74)
_HEART_EMPTY_EDGE = (96, 84, 104)
_HEART_OUTLINE = (48, 16, 26)


class PixelFont:
    """Обёртка над pygame.font.Font с кэшем и целочисленным масштабом.

    Шрифт рендерится в базовом размере без сглаживания и увеличивается
    целым множителем — так буквы остаются чёткими и пиксельными.
    """

    def __init__(self, path=None, size=None):
        self.path = path or settings.FONT_PATH
        self.size = size or settings.FONT_SIZE
        self._cache = {}
        self._glyphs = {}
        self._font = None

        try:
            if os.path.exists(self.path):
                self._font = pygame.font.Font(self.path, self.size)
            else:
                raise FileNotFoundError(self.path)
        except (pygame.error, FileNotFoundError, OSError) as exc:
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Пиксельный шрифт не загружен ({exc}), используется Arial")
            self._font = pygame.font.SysFont("Arial", self.size)

    def _advance(self, ch):
        """Ширина символа с учётом подмен и дорисованных глифов."""
        if ch in _SUBSTITUTES:
            return self._font.size(_SUBSTITUTES[ch])[0]
        if ch in _CUSTOM_GLYPHS:
            return _CUSTOM_ADVANCE[ch]
        return self._font.size(ch)[0]

    def _glyph(self, ch, color):
        """Готовый символ базового кегля (подмена/дорисовка) или None."""
        substitute = _SUBSTITUTES.get(ch)
        if substitute is not None:
            return self._font.render(substitute, False, color)

        rects = _CUSTOM_GLYPHS.get(ch)
        if rects is None:
            return None
        key = (ch, tuple(color))
        glyph = self._glyphs.get(key)
        if glyph is None:
            glyph = pygame.Surface((_CUSTOM_ADVANCE[ch], self._font.get_height()),
                                   pygame.SRCALPHA)
            for rect in rects:
                pygame.draw.rect(glyph, color, rect)
            self._glyphs[key] = glyph
        return glyph

    def _render_string(self, text, color):
        """Рендер строки: обычный путь, а при подменах — по символам."""
        if not any(ch in _SUBSTITUTES or ch in _CUSTOM_GLYPHS for ch in text):
            return self._font.render(text, False, color)

        width = sum(self._advance(ch) for ch in text)
        surface = pygame.Surface((max(1, width), self._font.get_height()),
                                 pygame.SRCALPHA)
        x = 0
        for ch in text:
            glyph = self._glyph(ch, color) or self._font.render(ch, False, color)
            surface.blit(glyph, (x, 0))
            x += self._advance(ch)
        return surface

    def render(self, text, scale=1, color=None):
        color = color or settings.TEXT_COLOR
        key = (text, scale, tuple(color))
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        surface = self._render_string(text, color)
        if scale != 1:
            surface = pygame.transform.scale(
                surface, (surface.get_width() * scale, surface.get_height() * scale)
            )
        self._cache[key] = surface
        return surface

    def draw(self, target, text, pos, scale=1, color=None, anchor="topleft", shadow=False):
        surface = self.render(text, scale, color)
        rect = surface.get_rect(**{anchor: pos})
        if shadow:
            shadow_surface = self.render(text, scale, settings.TEXT_SHADOW)
            target.blit(shadow_surface, rect.move(2 * scale, 2 * scale))
        target.blit(surface, rect)
        return rect

    def line_height(self, scale=1):
        return self._font.get_linesize() * scale


def draw_panel(surface, rect, fill=(24, 21, 34, 222), border=(126, 104, 74), thickness=2,
               highlight=True):
    """Прямоугольная панель с пиксельной рамкой и лёгким бликом сверху."""
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill(fill)
    surface.blit(panel, rect.topleft)
    pygame.draw.rect(surface, border, rect, thickness)
    if highlight:
        pygame.draw.line(surface, (200, 176, 128), rect.topleft, (rect.right - 1, rect.top))
    return rect


def draw_heart(surface, topleft, scale=2, filled=True):
    """Рисует одно пиксельное сердечко."""
    x0, y0 = topleft
    for row_index, row in enumerate(_HEART):
        for col_index, cell in enumerate(row):
            if cell != "X":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    color = _HEART_COLOR if filled else _HEART_EMPTY
                    if filled and row_index == 1 and col_index == 1:
                        color = _HEART_HIGHLIGHT
                    if not filled and row_index in (0, 5):
                        color = _HEART_EMPTY_EDGE
                    pygame.draw.rect(surface, color, (
                        x0 + col_index * scale + dx,
                        y0 + row_index * scale + dy,
                        1, 1,
                    ))
    # Тёмный контур снизу для объёма
    if filled:
        for col_index, cell in enumerate(_HEART[-1]):
            if cell == "X":
                pygame.draw.rect(surface, _HEART_OUTLINE, (
                    x0 + col_index * scale, y0 + 6 * scale - 1, scale, 1
                ))


def draw_hearts(surface, topright, hp, max_hp, scale=2, gap=None):
    """Полоска здоровья из сердечек, выровненная по правому краю."""
    gap = scale if gap is None else gap
    heart_w = 7 * scale
    heart_h = 6 * scale
    total_w = max_hp * heart_w + (max_hp - 1) * gap
    x = topright[0] - total_w
    for index in range(max_hp):
        draw_heart(surface, (x + index * (heart_w + gap), topright[1] - heart_h),
                   scale=scale, filled=index < hp)


def draw_keycap(surface, font, key_text, topleft, scale=1):
    """Маленькая «клавиша» с подписью — для подсказок."""
    label = font.render(key_text, scale, settings.TEXT_COLOR)
    rect = pygame.Rect(topleft, (label.get_width() + 10, label.get_height() + 6))
    pygame.draw.rect(surface, (52, 46, 62), rect)
    pygame.draw.rect(surface, (150, 136, 108), rect, 1)
    surface.blit(label, label.get_rect(center=rect.center))
    return rect
