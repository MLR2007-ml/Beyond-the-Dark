# entities.py
"""Стены, монеты, шипы, рычаги, мосты, порталы и скелеты-враги."""
import glob
import math
import os
import random
import re

import pygame

import settings

# Палитры блоков для разных уровней: (основа, свет, тень, блик)
WALL_THEMES = {
    1: ((52, 72, 50), (78, 104, 64), (30, 44, 32), (104, 134, 78)),
    2: ((50, 52, 72), (78, 80, 106), (28, 30, 44), (110, 112, 140)),
    3: ((58, 40, 44), (88, 62, 66), (30, 20, 24), (126, 78, 76)),
}

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
    def __init__(self, x, y, width, height, theme=1):
        super().__init__()
        base, light, dark, accent = WALL_THEMES.get(theme, WALL_THEMES[1])
        self.image = pygame.Surface((width, height))
        self.image.fill(base)

        # Объём: светлая кромка сверху/слева, тёмная снизу/справа
        pygame.draw.line(self.image, light, (0, 0), (width - 1, 0), 2)
        pygame.draw.line(self.image, light, (0, 0), (0, height - 1), 2)
        pygame.draw.line(self.image, dark, (0, height - 1), (width - 1, height - 1), 2)
        pygame.draw.line(self.image, dark, (width - 1, 0), (width - 1, height - 1), 2)

        rng = random.Random((x * 73856093) ^ (y * 19349663) ^ (width * 83492791))
        for _ in range(max(4, (width * height) // 500)):
            px = rng.randrange(2, max(3, width - 2))
            py = rng.randrange(2, max(3, height - 2))
            self.image.set_at((px, py), rng.choice((light, dark, accent)))

        if theme == 1 and height <= 50:
            # Мох на верхней кромке лесных платформ
            pygame.draw.rect(self.image, (74, 110, 58), (0, 0, width, 3))

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
    """Искры и «+1» при подборе монеты."""

    def __init__(self, x, y):
        self.timer = 0
        self.life = 34
        self.x = x
        self.y = y
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
            color = (255, 226, 120) if self.timer % 4 < 2 else (255, 190, 60)
            pygame.draw.rect(surface, color, (int(x), int(y), 3, 3))
        if font and self.timer < 24:
            font.draw(surface, "+1", (self.x + offset[0],
                                      self.y + offset[1] - 14 - self.timer * 0.9),
                      color=settings.TEXT_ACCENT, anchor="center")


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


class Skeleton:
    """Скелет-воин пещеры: патрулирует, догоняет и бьёт мечом."""

    WIDTH, HEIGHT = 36, 54
    BONE = (236, 234, 222)
    BONE_DARK = (196, 192, 178)
    SOCKET = (26, 22, 30)
    CAPE = (48, 76, 158)
    CAPE_LIGHT = (76, 110, 202)
    CAPE_DARK = (32, 48, 108)
    IRON = (172, 178, 192)
    WOOD = (128, 76, 42)
    WOOD_DARK = (86, 50, 26)

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
        self.frames = {1: self._render(1, False), -1: self._render(-1, False)}
        self.flash_frames = {1: self._render(1, True), -1: self._render(-1, True)}
        self.image = self.frames[1]

    # --- Отрисовка ---
    def _render(self, facing, flash):
        image = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        bone = (255, 255, 255) if flash else self.BONE
        bone_dark = (240, 240, 240) if flash else self.BONE_DARK
        cape = (255, 255, 255) if flash else self.CAPE
        cape_light = (255, 255, 255) if flash else self.CAPE_LIGHT
        cape_dark = (215, 215, 215) if flash else self.CAPE_DARK
        iron = (255, 255, 255) if flash else self.IRON
        wood = (255, 245, 245) if flash else self.WOOD
        wood_dark = (225, 205, 205) if flash else self.WOOD_DARK
        socket = (70, 24, 24) if flash else self.SOCKET

        # ноги и ступни
        pygame.draw.rect(image, bone, (12, 38, 4, 12))
        pygame.draw.rect(image, bone, (20, 38, 4, 12))
        pygame.draw.rect(image, bone_dark, (9, 50, 8, 3))
        pygame.draw.rect(image, bone_dark, (20, 50, 8, 3))
        # таз и рёбра
        pygame.draw.rect(image, bone_dark, (12, 33, 13, 5))
        pygame.draw.rect(image, bone, (11, 22, 15, 12))
        for rib in (25, 28, 31):
            pygame.draw.rect(image, socket, (13, rib, 11, 1))
        pygame.draw.rect(image, bone_dark, (17, 22, 2, 12))
        # накидка
        pygame.draw.polygon(image, cape, ((6, 16), (30, 16), (32, 27), (26, 25),
                                          (23, 35), (14, 35), (11, 25), (4, 27)))
        pygame.draw.line(image, cape_light, (7, 17), (29, 17), 2)
        pygame.draw.line(image, cape_dark, (6, 19), (9, 31), 2)
        pygame.draw.line(image, cape_dark, (29, 19), (26, 31), 2)
        # череп
        pygame.draw.rect(image, bone, (11, 2, 14, 13))
        pygame.draw.rect(image, bone_dark, (12, 14, 12, 3))
        pygame.draw.rect(image, socket, (13, 5, 4, 4))
        pygame.draw.rect(image, socket, (19, 5, 4, 4))
        pygame.draw.rect(image, socket, (17, 10, 2, 3))
        for tooth in range(4):
            pygame.draw.rect(image, socket, (13 + tooth * 3, 14, 1, 3))
        # рука с мечом
        pygame.draw.rect(image, bone, (26, 23, 4, 11))
        pygame.draw.polygon(image, iron, ((29, 24), (33, 22), (34, 4), (30, 3)))
        pygame.draw.line(image, (230, 236, 248), (33, 4), (30, 3), 1)
        pygame.draw.rect(image, wood_dark, (26, 26, 8, 2))
        # щит
        pygame.draw.rect(image, wood, (2, 24, 12, 15))
        pygame.draw.rect(image, wood_dark, (2, 24, 12, 15), 1)
        pygame.draw.circle(image, iron, (8, 31), 3)
        pygame.draw.circle(image, wood_dark, (8, 31), 3, 1)

        if facing < 0:
            image = pygame.transform.flip(image, True, False)
        return image

    # --- Бой ---
    def take_damage(self, amount, direction=1):
        if self.dead:
            return False
        self.hp = max(0, self.hp - amount)
        self.hurt_timer = 12
        self.rect.x += 7 * direction
        if self.hp <= 0:
            self.dead = True
            self.death_timer = 0
        return self.dead

    def strike_rect(self):
        """Зона удара мечом в активных кадрах замаха."""
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
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.dead:
            self.death_timer += 1
            self.image = self.frames[self.facing]
            return

        dx = 0
        player_ok = player is not None and player.alive
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
        self.image = (self.flash_frames if self.hurt_timer > 0 else self.frames)[self.facing]

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
