# boss.py
"""Дракон-босс финального уровня: погоня, пламя и фаерболы."""
import math
import os

import pygame

import settings


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


class Fireball:
    def __init__(self, x, y, vx, vy):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.radius = 9
        self.life = 210
        self.dead = False
        self.timer = 0
        self.trail = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def update(self, walls):
        self.timer += 1
        self.life -= 1
        if self.life <= 0:
            self.dead = True
            return
        self.trail.append((self.x, self.y))
        if len(self.trail) > 7:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                self.dead = True
                return

    def draw(self, surface):
        for index, (tx, ty) in enumerate(self.trail):
            size = max(2, 6 - index // 2)
            pygame.draw.circle(surface, (190, 60, 16), (int(tx), int(ty)), size)
        pygame.draw.circle(surface, (236, 92, 18), (int(self.x), int(self.y)), self.radius + 2)
        pygame.draw.circle(surface, (255, 170, 40), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (255, 240, 170), (int(self.x), int(self.y)), self.radius // 2)


class Dragon(pygame.sprite.Sprite):
    def __init__(self, center_x, floor_top):
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
        self.fireballs = []

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
            self.fireballs.clear()
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

    def _shoot(self, player):
        mouth_x, mouth_y = self.mouth_pos()
        target_x = player.rect.centerx
        target_y = player.rect.centery
        base_angle = math.atan2(target_y - mouth_y, target_x - mouth_x)
        for offset in (-0.12, 0.08):
            angle = base_angle + offset
            vx = math.cos(angle) * settings.FIREBALL_SPEED
            vy = math.sin(angle) * settings.FIREBALL_SPEED
            self.fireballs.append(Fireball(mouth_x, mouth_y, vx, vy))

    # --- Логика ---
    def update(self, player, walls):
        self.bob_timer += 1
        if self.flash_timer > 0:
            self.flash_timer -= 1

        for fireball in self.fireballs:
            fireball.update(walls)
            if not fireball.dead and fireball.rect.colliderect(player.rect):
                fireball.dead = True
                player.take_damage(1)
        self.fireballs = [fb for fb in self.fireballs if not fb.dead]

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
                self.next_action = "flame" if distance <= settings.BOSS_FLAME_RANGE else "fireball"
                self._set_state("telegraph")

        elif self.state == "telegraph":
            if self.timer >= settings.BOSS_TELEGRAPH_TICKS:
                if self.next_action == "flame":
                    self.flame_hit = False
                    self._set_state("flame")
                else:
                    self._shoot(player)
                    self._set_state("shoot")

        elif self.state == "flame":
            flame = self.flame_rect()
            if flame and not self.flame_hit and flame.colliderect(player.rect):
                self.flame_hit = True
                player.take_damage(1)     # одно попадание = одно сердце
            if self.timer >= settings.BOSS_FLAME_TICKS:
                self._set_state("recover")

        elif self.state == "shoot":
            if self.timer >= 28:
                self._set_state("recover")

        elif self.state == "recover":
            if self.timer >= settings.BOSS_RECOVER_TICKS:
                self.attack_cd = settings.BOSS_ATTACK_COOLDOWN
                self._set_state("idle")

        # Анимация кадров атаки
        if self.state in ("flame", "shoot"):
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

        if self.state in ("flame", "shoot", "recover") and self.attack_images:
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
        """Пламя и фаерболы — поверх игрока, чтобы читался урон."""
        for fireball in self.fireballs:
            fireball.draw(surface)
        if self.state == "flame":
            self._draw_flame(surface)
