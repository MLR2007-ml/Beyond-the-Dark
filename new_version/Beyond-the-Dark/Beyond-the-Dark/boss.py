# boss.py
"""Дракон-босс финального уровня: погоня, пламя и обвал камней."""
import math
import os
import random

import pygame

import settings


ROCK_CACHE = {}


def _load_boss_frames():
    idle = None
    if os.path.exists(settings.BOSS_IMAGE):
        try:
            idle = pygame.image.load(settings.BOSS_IMAGE).convert_alpha()
        except (pygame.error, OSError) as exc:
            print(f"[ОШИБКА] Не удалось загрузить босса: {exc}")

    attack = []
    for path in settings.BOSS_ATTACK_FRAMES:
        if not os.path.exists(path):
            continue
        try:
            attack.append(pygame.image.load(path).convert_alpha())
        except (pygame.error, OSError) as exc:
            print(f"[ОШИБКА] Не удалось загрузить кадр атаки: {exc}")

    if idle is None and attack:
        idle = attack[0].copy()
    if not attack and idle is not None:
        attack = [idle]
    if idle is None:
        return None, []

    def resize(image):
        height = settings.BOSS_HEIGHT
        width = max(1, round(image.get_width() * height / image.get_height()))
        return pygame.transform.smoothscale(image, (width, height))

    idle = resize(idle)
    attack = [resize(frame) for frame in attack]
    print(f"[УСПЕХ] Дракон: стойка + {len(attack)} кадров атаки")
    return idle, attack


def _strip_white(image):
    """Вырезает белый фон и обрезает прозрачные поля спрайта-сталактита."""
    width, height = image.get_size()
    for px in range(width):
        for py in range(height):
            red, green, blue, _alpha = image.get_at((px, py))
            low, high = min(red, green, blue), max(red, green, blue)
            if low > 186 and high - low < 54:          # белый фон и его шум
                alpha = 0
            elif low > 146 and high - low < 38:        # светлая кромка — полупрозрачная
                alpha = 110
            else:
                alpha = 255
            if alpha != 255:
                image.set_at((px, py), (red, green, blue, alpha))
    box = image.get_bounding_rect(min_alpha=40)
    if box.width > 2 and box.height > 2:
        image = image.subsurface(box).copy()
    return image


def _rock_source():
    """Спрайт big с вырезанным белым фоном (грузится один раз)."""
    if "image" in ROCK_CACHE:
        return ROCK_CACHE["image"]
    image = None
    path = settings.ROCK_IMAGE
    if path and os.path.exists(path):
        try:
            raw = pygame.image.load(path).convert_alpha()
            # Обрабатываем уменьшенную копию: пиксельный проход по 1536 × 1024
            # был бы заметно медленнее на старте боя.
            height = 260
            width = max(1, round(raw.get_width() * height / raw.get_height()))
            image = _strip_white(pygame.transform.smoothscale(raw, (width, height)))
        except (pygame.error, OSError) as exc:
            print(f"[ОШИБКА] Не удалось загрузить сталактит: {exc}")
    ROCK_CACHE["image"] = image
    return image


def _rock_image(size_key):
    """Один и тот же сталактит, отмасштабированный по высоте (пропорции целы)."""
    height = settings.ROCK_SIZES.get(size_key, 84)
    cache_key = ("rock", height)
    if cache_key in ROCK_CACHE:
        return ROCK_CACHE[cache_key]

    source = _rock_source()
    if source is not None:
        width = max(3, round(source.get_width() * height / source.get_height()))
        image = pygame.transform.smoothscale(source, (width, height))
    else:
        width = max(8, int(height * 0.55))
        image = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.polygon(image, (104, 100, 114),
                            ((width * 0.50, 0), (width * 0.96, height * 0.34),
                             (width * 0.64, height * 0.92), (width * 0.36, height * 0.92),
                             (width * 0.04, height * 0.36)))
        pygame.draw.polygon(image, (146, 142, 158),
                            ((width * 0.50, height * 0.06), (width * 0.82, height * 0.34),
                             (width * 0.56, height * 0.28)))
    ROCK_CACHE[cache_key] = image
    return image


class Rock:
    """Сталактит, который дракон обрушивает на арену.

    Сначала глыба трясётся у потолка (по полу видна метка), затем падает:
    попадание по игроку снимает одно сердце и разбивает камень.
    """

    TOP = 4                     # по умолчанию — от верха экрана (см. ceiling)

    def __init__(self, x, floor_top, size_key="medium", top=None):
        self.size_key = size_key
        self.image = _rock_image(size_key)
        top = self.TOP if top is None else int(top)
        self.rect = self.image.get_rect(midtop=(int(x), top))
        self.base_x = self.rect.x
        self.y = float(self.rect.y)
        self.vy = settings.ROCK_FALL_SPEED
        self.timer = 0
        self.warmup = settings.ROCK_WARMUP_TICKS
        self.floor_top = int(floor_top)
        self.dead = False
        self.landed = False
        self.land_timer = 0

    @property
    def falling(self):
        return self.warmup <= 0 and not self.landed

    def _land(self):
        self.landed = True
        self.vy = 0.0

    def update(self, player):
        self.timer += 1
        if self.warmup > 0:
            self.warmup -= 1
            self.rect.x = self.base_x + int(round(math.sin(self.timer * 0.9) * 3))
            return
        if self.landed:
            self.land_timer += 1
            if self.land_timer > 20:
                self.dead = True
            return

        self.vy = min(18.0, self.vy + settings.ROCK_GRAVITY)
        self.y += self.vy
        self.rect.y = int(self.y)
        self.rect.x = self.base_x

        if player is not None and player.alive:
            hit_zone = player.rect.inflate(0, -6)
            if self.rect.inflate(-self.rect.width * 0.4, 0).colliderect(hit_zone):
                player.take_damage(settings.ROCK_DAMAGE)
                self.dead = True
                return

        # Сталактит всегда доходит до пола: стены по бокам его не останавливают.
        if self.rect.bottom >= self.floor_top:
            self.rect.bottom = self.floor_top
            self._land()

    def draw(self, surface):
        if self.landed:
            fade = max(40, 255 - self.land_timer * 11)
            image = self.image.copy()
            image.set_alpha(fade)
            surface.blit(image, self.rect)
            rubble = (128, 124, 138)
            pygame.draw.rect(surface, rubble, (self.rect.centerx - 14,
                                               self.rect.bottom - 5, 9, 4))
            pygame.draw.rect(surface, rubble, (self.rect.centerx + 6,
                                               self.rect.bottom - 4, 7, 3))
            return

        shadow = pygame.Rect(0, 0, self.rect.width, 10)
        shadow.midbottom = (self.base_x + self.rect.width // 2, self.floor_top)
        pygame.draw.ellipse(surface, (12, 10, 16), shadow)
        if self.warmup > 0:
            pulse = 0.5 + 0.5 * math.sin(self.timer * 0.8)
            pygame.draw.ellipse(surface, (255, int(110 + 100 * pulse), 60),
                                shadow, 2)
            drip = (self.timer * 7) % 46
            pygame.draw.rect(surface, (156, 152, 168),
                             (shadow.centerx - 2, self.rect.bottom + drip, 4, 5))
        else:
            # след падения — едва заметные штрихи, чтобы не спорить с фоном
            for index in range(3):
                streak = pygame.Rect(0, 0, 2, 14 + index * 6)
                streak.midtop = (self.rect.centerx - 10 + index * 10, self.rect.top - 22)
                pygame.draw.rect(surface, (104, 92, 116), streak)
        surface.blit(self.image, self.rect)


class Dragon(pygame.sprite.Sprite):
    def __init__(self, center_x, floor_top, ceiling_top=None):
        super().__init__()
        self.idle_image, self.attack_images = _load_boss_frames()
        if self.idle_image is None:
            self.idle_image = pygame.Surface((200, settings.BOSS_HEIGHT))
            self.idle_image.fill((120, 40, 40))
            print("[ПРЕДУПРЕЖДЕНИЕ] Спрайт дракона не найден — красный прямоугольник")
            self.attack_images = [self.idle_image]

        image_w, image_h = self.idle_image.get_size()
        self.rect = pygame.Rect(0, 0, int(image_w * 0.60), int(image_h * 0.84))
        self.rect.midbottom = (int(center_x), int(floor_top))
        # Откуда свисают сталактиты: низ потолочного ряда блоков.
        self.ceiling_top = Rock.TOP if ceiling_top is None else int(ceiling_top)

        self.max_hp = settings.BOSS_MAX_HP
        self.hp = self.max_hp
        self.facing = "left"
        self.state = "idle"
        self.timer = 0
        self.attack_cd = 90
        self.next_action = "flame"
        self.flame_hit = False
        self.flash_timer = 0
        self.dead_timer = 0
        self.anim_timer = 0
        self.anim_frame = 0
        self.bob_timer = 0
        self.rocks = []

    # --- Геометрия ---
    def image_rect(self):
        return self.idle_image.get_rect(midbottom=self.rect.midbottom)

    def mouth_pos(self):
        rect = self.image_rect()
        if self.facing == "right":
            x = rect.left + rect.width * 0.875
        else:
            x = rect.left + rect.width * 0.125
        return int(x), int(rect.top + rect.height * 0.40)

    def flame_rect(self):
        if self.state != "flame":
            return None
        mouth_x, mouth_y = self.mouth_pos()
        width = settings.BOSS_FLAME_RANGE
        top = mouth_y - 14
        bottom = self.rect.bottom - 2
        if self.facing == "right":
            return pygame.Rect(mouth_x, top, width, bottom - top)
        return pygame.Rect(mouth_x - width, top, width, bottom - top)

    # --- Бой ---
    def take_damage(self, amount):
        if self.state == "dead":
            return False
        self.hp = max(0, self.hp - amount)
        self.flash_timer = 5
        if self.hp <= 0:
            self.state = "dead"
            self.timer = 0
            self.dead_timer = 0
            self.rocks.clear()
            return True
        return False

    @property
    def defeated(self):
        return self.state == "dead" and self.dead_timer >= 110

    @property
    def alive(self):
        return self.state != "dead"

    def _set_state(self, state):
        self.state = state
        self.timer = 0
        self.anim_timer = 0
        self.anim_frame = 0

    def _drop_rocks(self, player):
        """Обвал: по глыбе слева и справа от игрока."""
        floor_top = self.rect.bottom
        center = player.rect.centerx if player is not None else self.rect.centerx
        sizes = ("medium", "big")
        for index in range(max(1, settings.ROCK_COUNT)):
            size_key = sizes[index % len(sizes)]
            half = _rock_image(size_key).get_width() // 2
            offset = (-95 if index % 2 == 0 else 95) + random.randint(-14, 14)
            # 56 px — ширина стеновой колонны арены плюс запас: глыба не врезается в стену
            x = max(half + 56, min(settings.SCREEN_WIDTH - half - 56, center + offset))
            self.rocks.append(Rock(x, floor_top, size_key, self.ceiling_top))

    # --- Логика ---
    def update(self, player, walls):
        self.bob_timer += 1
        if self.flash_timer > 0:
            self.flash_timer -= 1

        for rock in self.rocks:
            rock.update(player)
        self.rocks = [rock for rock in self.rocks if not rock.dead]

        if self.state == "dead":
            self.dead_timer += 1
            return

        if player.rect.centerx < self.rect.centerx:
            self.facing = "left"
        else:
            self.facing = "right"

        if self.attack_cd > 0:
            self.attack_cd -= 1

        self.timer += 1
        distance = abs(player.rect.centerx - self.rect.centerx)

        if self.state == "idle":
            # «Бежит» за игроком, но не встаёт вплотную
            if distance > 115:
                direction = 1 if player.rect.centerx > self.rect.centerx else -1
                self.rect.x += int(round(direction * settings.BOSS_CHASE_SPEED))
                self.rect.x = max(8, min(settings.SCREEN_WIDTH - self.rect.width - 8,
                                          self.rect.x))
            if self.attack_cd <= 0:
                self.next_action = "flame" if distance <= settings.BOSS_FLAME_RANGE else "rocks"
                self._set_state("telegraph")

        elif self.state == "telegraph":
            if self.timer >= settings.BOSS_TELEGRAPH_TICKS:
                if self.next_action == "flame":
                    self.flame_hit = False
                    self._set_state("flame")
                else:
                    self._drop_rocks(player)
                    self._set_state("rocks")

        elif self.state == "flame":
            flame = self.flame_rect()
            if flame and not self.flame_hit and flame.colliderect(player.rect):
                self.flame_hit = True
                player.take_damage(1)     # одно попадание = одно сердце
            if self.timer >= settings.BOSS_FLAME_TICKS:
                self._set_state("recover")

        elif self.state == "rocks":
            # Камни падают сами; босс «отдыхает», пока не упадут все
            if self.timer >= 46 and not self.rocks:
                self._set_state("recover")

        elif self.state == "recover":
            if self.timer >= settings.BOSS_RECOVER_TICKS:
                self.attack_cd = settings.BOSS_ATTACK_COOLDOWN
                self._set_state("idle")

        # Анимация кадров атаки
        if self.state in ("flame", "rocks"):
            self.anim_timer += 1
            if self.anim_timer >= 5:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % len(self.attack_images)

        # Контактный урон
        if player.alive:
            contact = self.rect.inflate(-self.rect.width * 0.35, -20)
            if contact.colliderect(player.rect):
                player.take_damage(1)

    # --- Отрисовка ---
    def _draw_flame(self, surface):
        mouth_x, mouth_y = self.mouth_pos()
        direction = 1 if self.facing == "right" else -1
        length = settings.BOSS_FLAME_RANGE
        ground = self.rect.bottom - 6
        step = 6
        # Слой: (доля длины, цвет, толщина у пасти)
        layers = (
            (1.00, (172, 38, 8), 19),
            (0.86, (232, 104, 14), 15),
            (0.64, (255, 184, 64), 10),
            (0.44, (255, 244, 198), 6),
        )
        for scale, color, thickness in layers:
            reach = int(length * scale)
            for x in range(0, reach, step):
                t = x / max(1, reach)
                # Струя опускается к полу
                center = mouth_y + (ground - 34 - mouth_y) * (t ** 1.25)
                # Профиль языка: широкий у пасти, сходит на нет к кончику
                profile = math.sin(math.pi * min(1.0, 0.10 + t * 0.94))
                noise = math.sin(x * 0.21 + self.bob_timer * 0.33 + scale * 9.0)
                half = thickness * (0.30 + 0.90 * profile) * (1.0 + 0.22 * noise) \
                    * (1.0 - 0.30 * t)
                if half < 1.5:
                    continue
                block = pygame.Rect(0, 0, step + 1, max(2, int(2 * half)))
                block.midtop = (int(mouth_x + direction * x), int(center - half))
                pygame.draw.rect(surface, color, block)

        # Искры у кончика пламени
        for index in range(6):
            phase = self.bob_timer * 0.4 + index * 1.7
            spark_x = mouth_x + direction * (length * 0.72 + (index * 17) % 55)
            spark_y = ground - 34 + math.sin(phase) * (12 + index * 2)
            pygame.draw.rect(surface, (255, 176, 60),
                             (int(spark_x), int(spark_y), 3, 3))

    def draw(self, surface, font=None):
        if self.state == "dead":
            image = self.idle_image.copy()
            image.set_alpha(max(15, 255 - self.dead_timer * 2))
            sink = int(self.dead_timer * 0.28)
            rect = image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + sink))
            if self.facing == "left":
                image = pygame.transform.flip(image, True, False)
            surface.blit(image, rect)
            # Тлеющие искры
            for index in range(10):
                px = self.rect.left + (index * 67 + self.bob_timer * 2) % self.rect.width
                py = rect.top + 30 + (index * 43 - self.bob_timer * 2) % 130
                pygame.draw.rect(surface, (220, 90, 30), (int(px), int(py), 3, 3))
            return

        if self.state in ("flame", "rocks", "recover") and self.attack_images:
            image = self.attack_images[self.anim_frame % len(self.attack_images)]
        else:
            image = self.idle_image

        bob = 0
        if self.state == "idle":
            bob = int(math.sin(self.bob_timer * 0.07) * 2)
        if self.state == "telegraph":
            bob = int(math.sin(self.bob_timer * 0.5) * 2)

        image_rect = image.get_rect(midbottom=(self.rect.centerx, self.rect.bottom + bob))
        if self.facing == "left":
            image = pygame.transform.flip(image, True, False)
        if self.flash_timer > 0:
            image = image.copy()
            image.fill((130, 130, 130, 0), special_flags=pygame.BLEND_RGBA_ADD)
        surface.blit(image, image_rect)

        if self.state == "telegraph":
            head_x = image_rect.left + image_rect.width * (0.72 if self.facing == "right" else 0.28)
            box = pygame.Rect(0, 0, 22, 26)
            box.center = (int(head_x), image_rect.top - 14 + int(math.sin(self.bob_timer * 0.4) * 2))
            pygame.draw.rect(surface, (26, 20, 30), box)
            pygame.draw.rect(surface, settings.TEXT_ACCENT, box, 2)
            if font:
                font.draw(surface, "!", box.center, scale=2,
                          color=settings.TEXT_ACCENT, anchor="center")

    def draw_front(self, surface):
        """Пламя и падающие камни — поверх игрока, чтобы читался урон."""
        for rock in self.rocks:
            rock.draw(surface)
        if self.state == "flame":
            self._draw_flame(surface)
