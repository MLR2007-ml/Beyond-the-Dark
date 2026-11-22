# player.py
"""Игрок: ходьба, прыжок, атака мечом и здоровье."""
import glob
import os
import re

import pygame

import settings

WALK_FRAME_TICKS = 5       # скорость анимации ходьбы
ATTACK_FRAME_TICKS = 4     # скорость анимации атаки
ATTACK_COOLDOWN = 10       # пауза после атаки
ATTACK_ACTIVE_FRAMES = (2, 3, 4, 5)   # кадры, на которых работает удар

_FALLBACK_SIZE = (30, 54)


def _numeric_key(path):
    match = re.search(r"(\d+)", os.path.basename(path))
    return int(match.group(1)) if match else 0


def _load_folder(folder):
    """Загружает PNG-кадры из папки в порядке номеров в имени файла."""
    if not os.path.isdir(folder):
        print(f"[ОШИБКА] Папка с кадрами не найдена: {folder}")
        return []

    files = sorted(glob.glob(os.path.join(folder, "*.png")), key=_numeric_key)
    frames = []
    for path in files:
        try:
            frames.append(pygame.image.load(path).convert_alpha())
        except (pygame.error, OSError) as exc:
            print(f"[ОШИБКА] Не удалось загрузить {path}: {exc}")
    if not frames:
        print(f"[ОШИБКА] В папке нет PNG-кадров: {folder}")
    return frames


def _union_bbox(surfaces):
    """Общий bounding box по альфа-каналу — кадры не будут «дёргаться»."""
    boxes = [s.get_bounding_rect(min_alpha=8) for s in surfaces]
    boxes = [b for b in boxes if b.width > 1 and b.height > 1]
    if not boxes:
        return None
    left = min(b.left for b in boxes)
    top = min(b.top for b in boxes)
    right = max(b.right for b in boxes)
    bottom = max(b.bottom for b in boxes)
    return pygame.Rect(left, top, right - left, bottom - top)


def _load_frames():
    """Готовит кадры всех состояний в едином масштабе."""
    raw = {
        "walk_left": _load_folder(settings.PLAYER_WALK_LEFT_DIR),
        "walk_right": _load_folder(settings.PLAYER_WALK_RIGHT_DIR),
        "attack": _load_folder(settings.PLAYER_COMBAT_DIR),
    }
    if not raw["walk_left"] or not raw["walk_right"] or not raw["attack"]:
        return None

    all_frames = raw["walk_left"] + raw["walk_right"] + raw["attack"]
    box = _union_bbox(all_frames)
    if box is None:
        return None

    scale = settings.PLAYER_HEIGHT / box.height
    canvas_size = (max(1, int(round(box.width * scale))),
                   max(1, int(round(box.height * scale))))

    def prepare(surfaces):
        prepared = []
        for surface in surfaces:
            frame = surface.subsurface(box).copy()
            frame = pygame.transform.smoothscale(frame, canvas_size)
            prepared.append(frame)
        return prepared

    walk_left = prepare(raw["walk_left"])
    walk_right = prepare(raw["walk_right"])
    attack_right = prepare(raw["attack"])
    attack_left = [pygame.transform.flip(f, True, False) for f in attack_right]

    frames = {
        "idle_left": [walk_left[0]],
        "idle_right": [walk_right[0]],
        "walk_left": walk_left,
        "walk_right": walk_right,
        "attack_left": attack_left,
        "attack_right": attack_right,
    }
    return frames


class Player(pygame.sprite.Sprite):
    def __init__(self, spawn_x, spawn_bottom):
        super().__init__()

        self.frames = _load_frames()
        if self.frames:
            self.image = self.frames["idle_right"][0]
        else:
            self.image = pygame.Surface(_FALLBACK_SIZE)
            self.image.fill(settings.PLAYER_COLOR)
            print("[ПРЕДУПРЕЖДЕНИЕ] Спрайты игрока не загружены — зелёный прямоугольник")

        # rect — узкая физическая коробка; картинка рисуется по draw_rect
        hit_w = max(18, int(self.image.get_width() * 0.55))
        hit_h = max(30, int(self.image.get_height() * 0.88))
        self.rect = pygame.Rect(0, 0, hit_w, hit_h)
        self.rect.midbottom = (int(spawn_x), int(spawn_bottom))

        # Физика
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5
        self.gravity = 0.7
        self.jump_power = -14.2
        self.on_ground = False

        # Здоровье
        self.max_hp = settings.PLAYER_MAX_HP
        self.hp = self.max_hp
        self.invuln_timer = 0

        # Анимация и бой
        self.state = "idle_right"
        self.facing = "right"
        self.frame_index = 0
        self.anim_timer = 0
        self.attacking = False
        self.attack_frame = 0
        self.attack_timer = 0
        self.attack_cooldown = 0
        self.attack_hit_done = False

        self._refresh_image()

    # --- Вспомогательное ---
    @property
    def draw_rect(self):
        return self.image.get_rect(midbottom=self.rect.midbottom)

    @property
    def visible(self):
        if self.invuln_timer <= 0:
            return True
        return (self.invuln_timer // 6) % 2 == 0

    @property
    def alive(self):
        return self.hp > 0

    def _refresh_image(self):
        if self.frames:
            frames = self.frames[self.state]
            self.image = frames[self.frame_index % len(frames)]

    # --- Управление ---
    def handle_input(self, keys):
        if not self.alive:
            self.vel_x = 0
            return

        self.vel_x = 0
        move_speed = self.speed * (0.35 if self.attacking else 1.0)

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -move_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = move_speed

        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def start_attack(self):
        """Запускает атаку по ЛКМ. Возвращает True, если удар начался."""
        if not self.alive or self.attacking or self.attack_cooldown > 0:
            return False
        self.attacking = True
        self.attack_frame = 0
        self.attack_timer = 0
        self.attack_hit_done = False
        return True

    def attack_rect(self):
        """Зона удара мечом (только в активных кадрах)."""
        if not self.attacking or self.attack_frame not in ATTACK_ACTIVE_FRAMES:
            return None
        width, height = 46, 34
        if self.facing == "right":
            topleft = (self.rect.right + 4, self.rect.centery - height // 2)
        else:
            topleft = (self.rect.left - 4 - width, self.rect.centery - height // 2)
        return pygame.Rect(topleft, (width, height))

    def take_damage(self, amount=1):
        """Наносит урон. Возвращает True, если игрок погиб."""
        if not self.alive or self.invuln_timer > 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = settings.PLAYER_INVULN_TICKS
        return not self.alive

    # --- Физика ---
    def update(self, walls):
        if not self.alive:
            return

        # Горизонталь
        self.rect.x += int(self.vel_x)
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_x > 0:
                    self.rect.right = wall.rect.left
                elif self.vel_x < 0:
                    self.rect.left = wall.rect.right

        # Вертикаль (дробную скорость накапливаем в vel_y)
        self.vel_y += self.gravity
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

        if not self.on_ground and self.vel_y >= 0:
            probe = self.rect.move(0, 1)
            for wall in walls:
                if probe.colliderect(wall.rect):
                    self.on_ground = True
                    break

        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        self._animate()

    # --- Анимация ---
    def _animate(self):
        if not self.frames:
            return

        if self.attacking:
            self.attack_timer += 1
            if self.attack_timer >= ATTACK_FRAME_TICKS:
                self.attack_timer = 0
                self.attack_frame += 1
                if self.attack_frame >= len(self.frames["attack_right"]):
                    self.attacking = False
                    self.attack_cooldown = ATTACK_COOLDOWN
                    self.attack_frame = len(self.frames["attack_right"]) - 1

            if self.attacking:
                self.state = f"attack_{self.facing}"
                self.frame_index = self.attack_frame
                self._refresh_image()
                return
            self.state = f"idle_{self.facing}"
            self.frame_index = 0
            self._refresh_image()
            return

        if not self.on_ground:
            state = f"idle_{self.facing}"
        elif self.vel_x > 0:
            self.facing = "right"
            state = "walk_right"
        elif self.vel_x < 0:
            self.facing = "left"
            state = "walk_left"
        else:
            state = f"idle_{self.facing}"

        frames = self.frames[state]
        if state != self.state:
            self.state = state
            self.frame_index = 0
            self.anim_timer = 0
        elif len(frames) > 1:
            self.anim_timer += 1
            if self.anim_timer >= WALK_FRAME_TICKS:
                self.anim_timer = 0
                self.frame_index = (self.frame_index + 1) % len(frames)

        self.frame_index %= len(frames)
        self._refresh_image()
