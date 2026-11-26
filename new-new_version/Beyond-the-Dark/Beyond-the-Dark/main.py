# main.py
"""Beyond the Dark — пиксельный платформер: лес, пещера и дракон в финале."""
import math
import os

import pygame

import progress
import settings
from audio import SoundBank
from boss import Dragon
from entities import Bridge, Coin, CoinBurst, Goal, Heart, Lever, Skeleton, Spike, Wall
from pixelfont import PixelFont, draw_hearts, draw_panel
from player import Player

LOGICAL_WIDTH = 800
LOGICAL_HEIGHT = 600
BLOCK = 50
GRID_X = 0
GRID_Y = 100

ROWS = 10

# Спецификации уровней. Сетка ROWS × width: (строка, столбец), блок 50 px.
LEVEL_SPECS = {
    1: {
        "width": 30,
        "pits": [(17, 23)],
        "steps": [(7, 4, 8), (7, 25, 26)],
        # между платформами обязателен зазор в 1 клетку, иначе под верхней
        # не остаётся места для прыжка и до секретной зоны не добраться
        "platforms": [(5, 10, 11), (3, 13, 15)],
        "coins": [(6, 6), (6, 7), (4, 10), (4, 11), (2, 13), (2, 14),
                  (7, 9), (7, 20), (6, 25), (8, 27)],
        "spikes": [(8, 9), (8, 16), (8, 24)],
        "levers": [(8, 14)],
        "hearts": [(8, 11), (8, 15)],
        "goal": (8, 28),
        "spawn": (8, 2),
        "secrets": [pygame.Rect(620, 190, 180, 170)],
    },
    2: {
        "width": 34,
        "pits": [(19, 25)],
        "steps": [(7, 5, 7), (7, 27, 28)],
        "platforms": [(5, 9, 11), (3, 13, 15)],
        "coins": [(8, 4), (6, 5), (6, 6), (4, 9), (4, 10), (2, 13),
                  (2, 14), (7, 21), (6, 27), (8, 31)],
        "spikes": [(8, 13), (8, 14), (8, 29)],
        "levers": [(8, 16)],
        "skeletons": [(8, 8), (8, 12), (8, 17), (8, 26)],
        "hearts": [(8, 10), (8, 30)],
        "goal": (8, 32),
        "spawn": (8, 2),
        "secrets": [pygame.Rect(630, 190, 190, 170)],
    },
    3: {
        "width": 16,
        "pits": [],
        "steps": [],
        "platforms": [],
        "coins": [(8, 2), (8, 5), (8, 8), (8, 11), (8, 13)],
        "spikes": [],
        "levers": [],
        "hearts": [(8, 3), (8, 9)],
        "goal": None,
        "spawn": (8, 1),
        "boss": True,
        "secrets": [],
    },
}


def build_level(spec):
    """Разворачивает спецификацию в сетку символов 10 × width."""
    width = spec["width"]
    rows = [["." for _ in range(width)] for _ in range(ROWS)]
    rows[0] = ["#"] * width
    rows[ROWS - 1] = ["#"] * width
    for row in rows[1:ROWS - 1]:
        row[0] = "#"
        row[-1] = "#"

    # ступени: твёрдый монолит от указанной строки до пола
    for row_index, first, last in spec.get("steps", ()):
        for fill_row in range(row_index, ROWS - 1):
            for col in range(first, last + 1):
                if 0 <= col < width:
                    rows[fill_row][col] = "#"

    for row_index, first, last in spec.get("platforms", ()):
        for col in range(first, last + 1):
            if 0 <= col < width:
                rows[row_index][col] = "#"

    for first, last in spec.get("pits", ()):
        for col in range(first, last + 1):
            rows[ROWS - 1][col] = " "

    for row_index, col in spec.get("spikes", ()):
        rows[row_index][col] = "^"
    for row_index, col in spec.get("coins", ()):
        rows[row_index][col] = "$"
    for row_index, col in spec.get("levers", ()):
        rows[row_index][col] = "L"
    for row_index, col in spec.get("hearts", ()):
        rows[row_index][col] = "H"
    for row_index, col in spec.get("skeletons", ()):
        rows[row_index][col] = "E"
    if spec.get("goal"):
        row_index, col = spec["goal"]
        rows[row_index][col] = "G"
    row_index, col = spec["spawn"]
    rows[row_index][col] = "P"
    return ["".join(row) for row in rows]


LEVELS = {level: build_level(spec) for level, spec in LEVEL_SPECS.items()}

LEVEL_THEMES = {1: 1, 2: 2, 3: 3}

CARD_THEME_COLORS = {
    1: (86, 132, 72),
    2: (84, 90, 128),
    3: (146, 68, 58),
}

CARD_DESCRIPTIONS = {
    1: "Рычаг и тайник",
    2: "Скелеты и мост",
    3: "Дракон-босс",
}


def draw_star(surface, center, radius, filled=True):
    """Рисует пятиконечную звезду для карточек уровней."""
    points = []
    for index in range(10):
        angle = math.radians(-90 + index * 36)
        reach = radius if index % 2 == 0 else radius * 0.44
        points.append((center[0] + math.cos(angle) * reach,
                       center[1] + math.sin(angle) * reach))
    pygame.draw.polygon(surface, (255, 208, 84) if filled else (54, 50, 60), points)
    pygame.draw.polygon(surface, (122, 92, 34) if filled else (92, 86, 98), points, 1)


class HitSpark:
    """Короткая вспышка искр при попадании."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 0
        self.life = 18

    def update(self):
        self.timer += 1

    @property
    def done(self):
        return self.timer >= self.life

    def draw(self, surface, font=None, offset=(0, 0)):
        for index in range(8):
            angle = math.radians(index * 45 + self.timer * 9)
            radius = 5 + self.timer * 2.2
            px = self.x + offset[0] + math.cos(angle) * radius
            py = self.y + offset[1] + math.sin(angle) * radius
            color = (255, 244, 190) if self.timer < 9 else (255, 150, 60)
            pygame.draw.rect(surface, color, (int(px), int(py), 3, 3))


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error as exc:
            print(f"[ПРЕДУПРЕЖДЕНИЕ] Аудио недоступно: {exc}")

        # Громкости из прошлой сессии — применяем до загрузки звуков
        saved_music, saved_sfx = progress.audio_volumes()
        if saved_music is not None:
            settings.MUSIC_VOLUME = saved_music
        if saved_sfx is not None:
            settings.SFX_VOLUME = saved_sfx
        self.sfx = SoundBank()

        pygame.display.set_caption("Beyond the Dark")
        self.screen = self._create_window()
        self.canvas = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.font = PixelFont()

        # Состояния: menu / level_select / settings / playing / victory
        self.state = "menu"
        self.state_time = 0
        self.running = True
        self.music_key = None

        # Игровые данные
        self.level = 1
        self.score = 0
        self.level_start_score = 0
        self.coin_total = 0
        self.player = None
        self.boss = None
        self.walls = []
        self.coins = []
        self.spikes = []
        self.bridges = []
        self.levers = []
        self.skeletons = []
        self.hearts = []
        self.goal = None
        self.effects = []
        self.floor_top = GRID_Y + 9 * BLOCK
        self.level_width = LOGICAL_WIDTH
        self.camera_x = 0.0
        self.kills = 0
        self.skeleton_total = 0
        self.secret_found = False
        self.near_lever = None
        self.stars_earned = 0
        self.transition_collected = 0
        self.message = ""
        self.message_timer = 0
        self.death_timer = 0
        self.transition_timer = 0

        # Слои тьмы уровня
        self._dark_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT),
                                            pygame.SRCALPHA)
        self._lights = {}

        self._backgrounds = {}
        self.ui = {}
        self.dropdown_open = False
        self.dragging_slider = None   # "music" / "sfx" / None — что тянем мышью

        self.play_music("lobby")

    # --- Окно и системные мелочи ---
    def window_flags(self):
        if settings.current_mode_index == 2:
            return pygame.FULLSCREEN
        return pygame.NOFRAME if settings.current_mode_index == 1 else 0

    def _center_window(self, screen):
        """Ставит окно по центру экрана после смены разрешения."""
        if settings.current_mode_index == 2:
            return
        try:
            import ctypes
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            width, height = screen.get_size()
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2)
            flags = 0x0001 | 0x0004 | 0x0010  # NOSIZE | NOZORDER | NOACTIVATE
            user32.SetWindowPos(hwnd, 0, x, y, 0, 0, flags)
        except Exception:  # noqa: BLE001 — центрирование не критично
            pass

    def _create_window(self):
        if settings.current_mode_index == 2:
            try:
                return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error as exc:
                print(f"[ОШИБКА] Полный экран недоступен: {exc}")
                settings.current_mode_index = 0

        size = (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        try:
            screen = pygame.display.set_mode(size, self.window_flags())
        except pygame.error as exc:
            print(f"[ОШИБКА] Не удалось создать окно {size}: {exc}")
            settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = 800, 600
            screen = pygame.display.set_mode((800, 600))
        self._center_window(screen)
        return screen

    def viewport(self):
        """(масштаб, смещение_x, смещение_y) холста внутри окна."""
        width, height = self.screen.get_size()
        scale = min(width / LOGICAL_WIDTH, height / LOGICAL_HEIGHT)
        return scale, (width - LOGICAL_WIDTH * scale) / 2, (height - LOGICAL_HEIGHT * scale) / 2

    def logical_mouse(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self.viewport()
        scale = max(0.0001, scale)
        logical_x = int((mouse_x - offset_x) / scale)
        logical_y = int((mouse_y - offset_y) / scale)
        return (max(0, min(LOGICAL_WIDTH - 1, logical_x)),
                max(0, min(LOGICAL_HEIGHT - 1, logical_y)))

    # --- Ассеты ---
    def background(self, key):
        if key in self._backgrounds:
            return self._backgrounds[key]

        image = None
        path = settings.BACKGROUNDS.get(key)
        if path and os.path.exists(path):
            try:
                image = pygame.image.load(path).convert()
                image = pygame.transform.smoothscale(image, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
            except (pygame.error, OSError) as exc:
                print(f"[ОШИБКА] Фон не загружен ({path}): {exc}")
                image = None
        self._backgrounds[key] = image
        return image

    def draw_background(self, key, dim=0, camera=0):
        image = self.background(key)
        if image is None:
            self.canvas.fill(settings.BG_COLOR)
        elif camera and self.level_width > LOGICAL_WIDTH:
            # лёгкий параллакс: фон прокручивается медленнее мира
            offset = int(-camera * 0.2) % LOGICAL_WIDTH
            self.canvas.blit(image, (offset - LOGICAL_WIDTH, 0))
            self.canvas.blit(image, (offset, 0))
        else:
            self.canvas.blit(image, (0, 0))
        if dim > 0:
            overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, dim))
            self.canvas.blit(overlay, (0, 0))

    def dim_screen(self, alpha=170):
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 10, alpha))
        self.canvas.blit(overlay, (0, 0))

    def light_surface(self, radius):
        """Радиальный градиент света: вычитается из слоя тьмы."""
        if radius in self._lights:
            return self._lights[radius]

        size = radius * 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        steps = 30
        for index in range(steps, 0, -1):
            level = index / steps                      # 1.0 — внешний край
            circle_radius = int(radius * level)
            alpha = int(255 * (1.0 - level) ** 0.75)
            pygame.draw.circle(surface, (0, 0, 0, alpha), (radius, radius), circle_radius)
        self._lights[radius] = surface
        return surface

    def draw_darkness(self):
        """Затемняет весь уровень, оставляя круг света у игрока."""
        alpha = settings.LEVEL_DARKNESS.get(self.level, 0)
        if alpha <= 0 or self.player is None:
            return
        radius = settings.LEVEL_LIGHT_RADIUS.get(self.level, 260)
        light = self.light_surface(radius)
        dark = self._dark_surface
        dark.fill((4, 3, 8, alpha))
        px = int(self.player.rect.centerx - self.camera_x)
        py = int(self.player.rect.centery)
        dark.blit(light, (px - radius, py - radius), special_flags=pygame.BLEND_RGBA_SUB)
        self.canvas.blit(dark, (0, 0))

    def play_music(self, key):
        if key == self.music_key:
            return
        self.music_key = key
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            return

        path = settings.LEVEL_MUSIC.get(key)
        if not path or not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
            pygame.mixer.music.play(-1)
        except pygame.error as exc:
            print(f"[ОШИБКА] Музыка не запущена ({path}): {exc}")

    # --- UI-примитивы ---
    def draw_button(self, rect, label, hovered=False, primary=False):
        if primary:
            fill = (86, 130, 92, 240) if hovered else (52, 84, 62, 238)
        else:
            fill = (62, 56, 76, 240) if hovered else (38, 34, 48, 236)
        border = settings.TEXT_ACCENT if hovered else (118, 104, 78)
        draw_panel(self.canvas, rect, fill=fill, border=border, thickness=2)
        self.font.draw(self.canvas, label, rect.center, anchor="center", shadow=True)

    def draw_muted(self, text, pos, scale=1, anchor="topleft"):
        return self.font.draw(self.canvas, text, pos, scale=scale, anchor=anchor,
                              color=(168, 160, 146))


    # --- Игровой процесс ---
    def start_game(self, level):
        self.score = 0
        self.level_start_score = 0
        self.start_level(level)

    def start_level(self, level):
        self.level = level
        self.state = "playing"
        self.state_time = 0
        self.level_start_score = self.score

        self.player = None
        self.boss = None
        self.walls = []
        self.coins = []
        self.spikes = []
        self.bridges = []
        self.levers = []
        self.skeletons = []
        self.hearts = []
        self.goal = None
        self.effects = []
        self.camera_x = 0.0
        self.kills = 0
        self.secret_found = False
        self.near_lever = None
        self.stars_earned = 0
        self.transition_collected = 0

        rows = LEVELS[level]
        spec = LEVEL_SPECS[level]
        theme = LEVEL_THEMES.get(level, 1)
        self.level_width = len(rows[0]) * BLOCK
        self.floor_top = GRID_Y + (len(rows) - 1) * BLOCK
        spawn = (GRID_X + BLOCK + BLOCK // 2, self.floor_top)

        def is_solid(row_index, col_index):
            """Есть ли твёрдый блок в клетке (за пределами сетки — нет)."""
            if 0 <= row_index < len(rows) and 0 <= col_index < len(rows[0]):
                return rows[row_index][col_index] == "#"
            return False

        spans = []
        for row_index, row in enumerate(rows):
            col_index = 0
            while col_index < len(row):
                cell = row[col_index]
                if cell != "#":
                    x = GRID_X + col_index * BLOCK
                    y = GRID_Y + row_index * BLOCK
                    if cell == "$":
                        self.coins.append(Coin(x + BLOCK // 2, y + BLOCK // 2))
                    elif cell == "^":
                        self.spikes.append(Spike(x + 5, y + BLOCK - Spike.HEIGHT,
                                                 width=BLOCK - 10))
                    elif cell == "L":
                        self.levers.append(Lever(x, self.floor_top))
                    elif cell == "G":
                        self.goal = Goal(x, self.floor_top)
                    elif cell == "H":
                        self.hearts.append(Heart(x, self._floor_top(rows, row_index,
                                                                    col_index), BLOCK))
                    elif cell == "E":
                        floor = self._floor_top(rows, row_index, col_index)
                        self.skeletons.append(Skeleton(x + BLOCK // 2, floor))
                    elif cell == "P":
                        spawn = (x + BLOCK // 2,
                                 self._floor_top(rows, row_index, col_index))
                    col_index += 1
                    continue

                # непрерывная горизонтальная серия блоков
                first = col_index
                while col_index < len(row) and row[col_index] == "#":
                    col_index += 1
                spans.append((row_index, first, col_index - 1))

        # Сплошные плиты: одинаковые по ширине серии соседних рядов сливаются в
        # один монолит — пол, потолок, ступени и стены без внутренних швов.
        monoliths = []
        for row_index, first, last in spans:
            for block in monoliths:
                if (block[1] == first and block[2] == last
                        and block[3] == row_index - 1):
                    block[3] = row_index
                    break
            else:
                monoliths.append([row_index, first, last, row_index])

        for row0, first, last, row1 in monoliths:
            exposed = (any(not is_solid(row0 - 1, col) for col in range(first, last + 1)),
                       any(not is_solid(row1 + 1, col) for col in range(first, last + 1)),
                       any(not is_solid(row, first - 1) for row in range(row0, row1 + 1)),
                       any(not is_solid(row, last + 1) for row in range(row0, row1 + 1)))
            self.walls.append(Wall(GRID_X + first * BLOCK,
                                   GRID_Y + row0 * BLOCK,
                                   (last - first + 1) * BLOCK,
                                   (row1 - row0 + 1) * BLOCK,
                                   theme, exposed))

        for first, last in spec.get("pits", ()):
            self.bridges.append(Bridge(GRID_X + first * BLOCK,
                                       (last - first + 1) * BLOCK, self.floor_top))

        self.coin_total = len(self.coins)
        self.skeleton_total = len(self.skeletons)
        self.player = Player(spawn[0], spawn[1])
        self.player.invuln_timer = settings.PLAYER_SPAWN_INVULN_TICKS
        if spec.get("boss"):
            self.boss = Dragon(self.level_width - 155, self.floor_top, GRID_Y + BLOCK)

        self.death_timer = 0
        self.transition_timer = 0
        self.message = f"Уровень {level} — {settings.LEVEL_NAMES[level]}"
        self.message_timer = 150
        self.play_music(level)

    def _floor_top(self, rows, row_index, col_index):
        """Верх ближайшего твёрдого блока под точкой."""
        for index in range(row_index, len(rows)):
            if rows[index][col_index] == "#":
                return GRID_Y + index * BLOCK
        return GRID_Y + (len(rows) - 1) * BLOCK

    def update_camera(self):
        if self.player is None:
            return
        limit = max(0, self.level_width - LOGICAL_WIDTH)
        target = max(0.0, min(limit, self.player.rect.centerx - LOGICAL_WIDTH / 2))
        self.camera_x += (target - self.camera_x) * 0.14
        if abs(target - self.camera_x) < 0.5:
            self.camera_x = target

    def solids(self):
        return self.walls + [bridge for bridge in self.bridges if bridge.solid]

    def try_interact(self):
        """E — дёрнуть рычаг рядом с игроком и опустить мост."""
        if self.player is None:
            return False
        for lever in self.levers:
            if lever.pulled:
                continue
            if abs(lever.rect.centerx - self.player.rect.centerx) > 90:
                continue
            if abs(lever.rect.bottom - self.player.rect.bottom) > 70:
                continue
            lever.pull()
            for bridge in self.bridges:
                bridge.lower()
            self.message = "Мост опускается!"
            self.message_timer = 130
            self.effects.append(HitSpark(lever.rect.centerx, lever.rect.top))
            return True
        return False

    def finish_level(self):
        if self.transition_timer > 0:
            return
        collected = self.score - self.level_start_score
        self.transition_collected = collected
        self.stars_earned = progress.record(self.level, collected, self.coin_total)
        self.transition_timer = 1

    def restart_level(self):
        self.score = self.level_start_score
        self.start_level(self.level)

    def go_menu(self):
        self.state = "menu"
        self.state_time = 0
        self.player = None
        self.boss = None
        self.walls = []
        self.coins = []
        self.spikes = []
        self.effects = []
        self.death_timer = 0
        self.transition_timer = 0
        self.dropdown_open = False
        self.play_music("lobby")

    def update_playing(self, keys):
        player = self.player
        if player is None:
            return

        if self.message_timer > 0:
            self.message_timer -= 1

        if self.death_timer > 0:
            # Экран смерти висит до нажатия «ЗАНОВО» (или R) — кнопка всегда доступна
            self.death_timer += 1
            return

        if self.transition_timer > 0:
            self.transition_timer += 1
            if self.transition_timer >= 150:
                if self.level < 3:
                    self.start_level(self.level + 1)
                else:
                    self.state = "victory"
                    self.state_time = 0
            return

        solids = self.solids()
        player.handle_input(keys)
        player.update(solids)
        self.update_camera()

        for coin in self.coins:
            coin.update()
        for heart in self.hearts:
            heart.update()
        for spike in self.spikes:
            spike.update(player)
        for lever in self.levers:
            lever.update()
        for bridge in self.bridges:
            bridge.update()
        if self.goal is not None:
            self.goal.update()
        for effect in self.effects:
            effect.update()
        self.effects = [effect for effect in self.effects if not effect.done]

        # Монеты
        for coin in self.coins[:]:
            if player.rect.colliderect(coin.rect):
                self.coins.remove(coin)
                self.score += 1
                self.sfx.play("coin")
                self.effects.append(CoinBurst(coin.rect.centerx, coin.rect.centery))

        # Хилки: поднимаем сердце, только если здоровье не полное
        for heart in self.hearts[:]:
            if player.hp < player.max_hp and player.rect.colliderect(heart.rect):
                self.hearts.remove(heart)
                player.hp = min(player.max_hp, player.hp + heart.heal)
                self.sfx.play("heal")
                self.effects.append(CoinBurst(heart.rect.centerx, heart.rect.centery,
                                              label="+1", color=(255, 120, 138)))

        # Шипы
        if player.alive and player.invuln_timer <= 0:
            for spike in self.spikes:
                if player.rect.colliderect(spike.damage_rect()):
                    player.take_damage(1)
                    player.vel_y = -7
                    self.effects.append(HitSpark(player.rect.centerx, player.rect.bottom - 20))
                    break

        # Рычаг рядом с игроком (подсказка рисуется в HUD)
        self.near_lever = None
        for lever in self.levers:
            if (not lever.pulled
                    and abs(lever.rect.centerx - player.rect.centerx) < 90
                    and abs(lever.rect.bottom - player.rect.bottom) < 70):
                self.near_lever = lever
                break

        # Скелеты
        swing = player.attack_rect()
        for skeleton in self.skeletons:
            skeleton.update(player, solids)
            if skeleton.dead:
                continue
            if swing is not None and not player.attack_hit_done \
                    and swing.colliderect(skeleton.rect):
                player.attack_hit_done = True
                direction = 1 if skeleton.rect.centerx >= player.rect.centerx else -1
                killed = skeleton.take_damage(settings.PLAYER_ATTACK_DAMAGE, direction)
                self.sfx.play("skeleton_hit")
                self.effects.append(HitSpark(skeleton.rect.centerx, skeleton.rect.centery))
                if killed:
                    self.kills += 1
            strike = skeleton.strike_rect()
            if strike is not None and player.alive and player.invuln_timer <= 0 \
                    and strike.colliderect(player.rect):
                player.take_damage(settings.SKELETON_DAMAGE)
                player.vel_y = -6
                self.effects.append(HitSpark(player.rect.centerx, player.rect.centery))
        self.skeletons = [skeleton for skeleton in self.skeletons
                          if not (skeleton.dead and skeleton.death_timer > 50)]

        # Босс
        if self.boss is not None:
            self.boss.update(player, self.walls)
            swing = player.attack_rect()
            if (swing and not player.attack_hit_done and self.boss.alive
                    and swing.colliderect(self.boss.rect)):
                player.attack_hit_done = True
                self.boss.take_damage(settings.PLAYER_ATTACK_DAMAGE)
                self.sfx.play("skeleton_hit")
                self.effects.append(HitSpark(swing.centerx, swing.centery))
            if self.boss.defeated:
                self.finish_level()
                return

        # Падение в пропасть
        if player.rect.top > LOGICAL_HEIGHT + 80:
            player.hp = 0

        # Смерть игрока
        if not player.alive:
            self.death_timer = 1
            return

        # Секретные локации
        if not self.secret_found:
            for zone in LEVEL_SPECS[self.level].get("secrets", ()):
                if zone.colliderect(player.rect):
                    self.secret_found = True
                    self.message = "СЕКРЕТНОЕ МЕСТО НАЙДЕНО!"
                    self.message_timer = 170
                    break

        # Портал в конце уровня
        if self.goal is not None and self.goal.rect.colliderect(player.rect):
            self.finish_level()


    # --- Раскладки интерфейса ---
    def menu_layout(self):
        return {
            "play": pygame.Rect(250, 300, 300, 50),
            "settings": pygame.Rect(250, 366, 300, 50),
            "quit": pygame.Rect(250, 432, 300, 50),
        }

    def level_select_layout(self):
        card_w, card_h, gap = 180, 200, 24
        total = 3 * card_w + 2 * gap
        start_x = (LOGICAL_WIDTH - total) // 2
        cards = {
            level: pygame.Rect(start_x + (level - 1) * (card_w + gap), 190, card_w, card_h)
            for level in (1, 2, 3)
        }
        return {"cards": cards, "back": pygame.Rect(290, 428, 220, 48)}

    def settings_layout(self):
        center_x = LOGICAL_WIDTH // 2
        # два ползунка в ряд: музыка слева, звуки справа
        music_track = pygame.Rect(132, 132, 232, 10)
        sfx_track = pygame.Rect(436, 132, 232, 10)
        res_button = pygame.Rect(center_x - 170, 204, 340, 44)
        options = [pygame.Rect(res_button.x, res_button.bottom + 6 + index * 28,
                               res_button.width, 26)
                   for index in range(len(settings.RESOLUTIONS))]
        mode_width = 160
        mode_total = 3 * mode_width + 2 * 6
        mode_start = center_x - mode_total // 2
        return {
            "panel": pygame.Rect(100, 40, 600, 540),
            "slider_music": music_track,
            "slider_music_hit": music_track.inflate(16, 24),
            "slider_sfx": sfx_track,
            "slider_sfx_hit": sfx_track.inflate(16, 24),
            "res_button": res_button,
            "res_options": options,
            "mode_label_y": 440,
            "mode_window": pygame.Rect(mode_start, 462, mode_width, 40),
            "mode_borderless": pygame.Rect(mode_start + mode_width + 6, 462,
                                           mode_width, 40),
            "mode_fullscreen": pygame.Rect(mode_start + 2 * (mode_width + 6), 462,
                                           mode_width, 40),
            "back": pygame.Rect(center_x - 100, 520, 200, 44),
        }

    # --- Меню ---
    def draw_menu(self, mouse):
        self.draw_background(3, 150)

        for index in range(28):
            x = (index * 97 + int(self.state_time * 0.55)) % (LOGICAL_WIDTH + 20) - 10
            y = LOGICAL_HEIGHT - (index * 61 + int(self.state_time * 0.9)) % (LOGICAL_HEIGHT + 40)
            color = (232, 140, 52) if index % 4 == 0 else (128, 86, 54)
            pygame.draw.rect(self.canvas, color, (x, y, 2, 2))

        self.font.draw(self.canvas, "BEYOND THE DARK", (LOGICAL_WIDTH // 2, 126),
                       scale=4, color=settings.TEXT_ACCENT, anchor="center", shadow=True)
        self.font.draw(self.canvas, "За гранью тьмы", (LOGICAL_WIDTH // 2, 196),
                       scale=2, anchor="center", shadow=True)
        self.draw_muted("Лес · Пещера · Финал", (LOGICAL_WIDTH // 2, 232), anchor="center")

        layout = self.menu_layout()
        for key, label in (("play", "ИГРАТЬ"), ("settings", "НАСТРОЙКИ"), ("quit", "ВЫХОД")):
            self.draw_button(layout[key], label, layout[key].collidepoint(mouse),
                             primary=(key == "play"))
        self.ui = layout

        footer = pygame.Rect(LOGICAL_WIDTH // 2 - 262, 506, 524, 62)
        draw_panel(self.canvas, footer, fill=(10, 9, 14, 208), border=(96, 80, 58),
                   thickness=1, highlight=False)
        self.draw_muted("A/D — идти · ПРОБЕЛ — прыжок · ЛКМ — удар мечом",
                        (LOGICAL_WIDTH // 2, 522), anchor="center")
        self.draw_muted("E / У — рычаг и мост · ESC — меню во время игры",
                        (LOGICAL_WIDTH // 2, 548), anchor="center")

    # --- Выбор уровня ---
    def draw_level_select(self, mouse):
        self.draw_background(2, 145)
        self.font.draw(self.canvas, "ВЫБОР УРОВНЯ", (LOGICAL_WIDTH // 2, 90),
                       scale=3, color=settings.TEXT_ACCENT, anchor="center", shadow=True)
        self.font.draw(self.canvas, f"Звёзды: {progress.total_stars()} / 9",
                       (LOGICAL_WIDTH // 2, 138), anchor="center",
                       color=(244, 232, 204), shadow=True)

        layout = self.level_select_layout()
        for level, rect in layout["cards"].items():
            hovered = rect.collidepoint(mouse)
            color = CARD_THEME_COLORS[level]
            fill = (color[0] + 26, color[1] + 26, color[2] + 26, 236) if hovered \
                else (color[0], color[1], color[2], 226)
            border = settings.TEXT_ACCENT if hovered else (150, 136, 108)
            draw_panel(self.canvas, rect, fill=fill, border=border, thickness=3)

            self.font.draw(self.canvas, f"УРОВЕНЬ {level}", (rect.centerx, rect.top + 14),
                           anchor="midtop", color=(232, 224, 208), shadow=True)
            self.font.draw(self.canvas, str(level), (rect.centerx, rect.top + 46),
                           scale=3, anchor="midtop", shadow=True)
            self.font.draw(self.canvas, settings.LEVEL_NAMES[level],
                           (rect.centerx, rect.top + 104), scale=2, anchor="midtop",
                           shadow=True)
            self.font.draw(self.canvas, CARD_DESCRIPTIONS[level],
                           (rect.centerx, rect.top + 142), anchor="midtop",
                           color=(240, 232, 214), shadow=True)

            best_coins, stars = progress.level_info(level)
            for index in range(3):
                draw_star(self.canvas,
                          (rect.centerx + (index - 1) * 26, rect.bottom - 16), 10,
                          filled=index < stars)
            if best_coins:
                self.font.draw(self.canvas, f"монет {best_coins}",
                               (rect.centerx, rect.top + 158), anchor="midtop",
                               color=(255, 226, 150), shadow=True)

        back = layout["back"]
        self.draw_button(back, "НАЗАД", back.collidepoint(mouse))
        self.ui = {"cards": layout["cards"], "back": back}


    # --- Настройки ---
    def apply_resolution(self, index):
        index %= len(settings.RESOLUTIONS)
        settings.current_res_index = index
        settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = settings.RESOLUTIONS[index]
        self.screen = self._create_window()
        pygame.display.set_caption("Beyond the Dark")

    def apply_window_mode(self, index):
        settings.current_mode_index = index % len(settings.WINDOW_MODES)
        self.screen = self._create_window()
        pygame.display.set_caption("Beyond the Dark")

    def set_music_volume_from_x(self, x):
        track = self.settings_layout()["slider_music"]
        ratio = (x - track.x) / max(1, track.width)
        settings.MUSIC_VOLUME = round(max(0.0, min(1.0, ratio)), 2)
        try:
            pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
        except pygame.error:
            pass

    def set_sfx_volume_from_x(self, x):
        track = self.settings_layout()["slider_sfx"]
        ratio = (x - track.x) / max(1, track.width)
        settings.SFX_VOLUME = round(max(0.0, min(1.0, ratio)), 2)
        self.sfx.set_volume(settings.SFX_VOLUME)

    def draw_slider(self, track, value, hovered=False):
        """Ползунок громкости: жёлоб, заполненная часть и ручка."""
        pygame.draw.rect(self.canvas, (40, 36, 48), track)
        filled = pygame.Rect(track.x, track.y, int(track.width * value), track.height)
        if filled.width > 0:
            pygame.draw.rect(self.canvas, (196, 166, 96), filled)
        pygame.draw.rect(self.canvas, settings.TEXT_ACCENT if hovered else (176, 156, 112),
                         track, 1)
        knob_x = track.x + int(track.width * value)
        pygame.draw.rect(self.canvas, (250, 238, 204) if hovered else (234, 220, 188),
                         (knob_x - 6, track.y - 6, 12, 22))
        pygame.draw.rect(self.canvas, (120, 104, 78), (knob_x - 6, track.y - 6, 12, 22), 1)

    def draw_settings(self, mouse):
        self.draw_background(3, 190)
        layout = self.settings_layout()
        draw_panel(self.canvas, layout["panel"], fill=(16, 14, 22, 234),
                   border=(126, 104, 74), thickness=2)

        self.font.draw(self.canvas, "НАСТРОЙКИ", (LOGICAL_WIDTH // 2, 64),
                       scale=3, color=settings.TEXT_ACCENT, anchor="center", shadow=True)

        music_percent = int(round(settings.MUSIC_VOLUME * 100))
        sfx_percent = int(round(settings.SFX_VOLUME * 100))
        music_track = layout["slider_music"]
        sfx_track = layout["slider_sfx"]
        self.font.draw(self.canvas, f"Громкость музыки: {music_percent}%",
                       (music_track.centerx, 98), anchor="midtop")
        self.draw_slider(music_track, settings.MUSIC_VOLUME,
                         layout["slider_music_hit"].collidepoint(mouse))
        self.font.draw(self.canvas, f"Громкость звуков: {sfx_percent}%",
                       (sfx_track.centerx, 98), anchor="midtop")
        self.draw_slider(sfx_track, settings.SFX_VOLUME,
                         layout["slider_sfx_hit"].collidepoint(mouse))

        self.font.draw(self.canvas, "Разрешение", (LOGICAL_WIDTH // 2, 180),
                       anchor="midtop")
        res_button = layout["res_button"]
        self.draw_button(res_button, f"{settings.SCREEN_WIDTH} × {settings.SCREEN_HEIGHT}  v",
                         res_button.collidepoint(mouse))
        self.draw_muted("Окно центрируется автоматически",
                        (LOGICAL_WIDTH // 2, 412), anchor="center")

        self.font.draw(self.canvas, "Режим окна", (LOGICAL_WIDTH // 2,
                                                   layout["mode_label_y"]), anchor="midtop")
        for index, key in ((0, "mode_window"), (1, "mode_borderless"),
                           (2, "mode_fullscreen")):
            rect = layout[key]
            active = settings.current_mode_index == index
            self.draw_button(rect, settings.WINDOW_MODES[index],
                             rect.collidepoint(mouse) or active, primary=active)

        back = layout["back"]
        self.draw_button(back, "НАЗАД", back.collidepoint(mouse))

        if self.dropdown_open:
            for index, option in enumerate(layout["res_options"]):
                hovered = option.collidepoint(mouse)
                active = index == settings.current_res_index
                if hovered:
                    fill = (74, 66, 88, 248)
                elif active:
                    fill = (52, 76, 56, 248)
                else:
                    fill = (26, 23, 34, 248)
                draw_panel(self.canvas, option, fill=fill,
                           border=settings.TEXT_ACCENT if hovered else (100, 90, 70),
                           thickness=1, highlight=False)
                width, height = settings.RESOLUTIONS[index]
                self.font.draw(self.canvas, f"{width} × {height}", option.center,
                               anchor="center",
                               color=settings.TEXT_ACCENT if active else settings.TEXT_COLOR)

        self.ui = layout

    def handle_settings_click(self, pos):
        layout = self.settings_layout()
        if self.dropdown_open:
            for index, option in enumerate(layout["res_options"]):
                if option.collidepoint(pos):
                    self.apply_resolution(index)
                    self.dropdown_open = False
                    return
            self.dropdown_open = False
            return

        if layout["res_button"].collidepoint(pos):
            self.dropdown_open = True
            return
        if layout["slider_music_hit"].collidepoint(pos):
            self.dragging_slider = "music"
            self.set_music_volume_from_x(pos[0])
            return
        if layout["slider_sfx_hit"].collidepoint(pos):
            self.dragging_slider = "sfx"
            self.set_sfx_volume_from_x(pos[0])
            self.sfx.play("coin")      # сразу слышно, насколько громко стало
            return
        for index, key in ((0, "mode_window"), (1, "mode_borderless"),
                           (2, "mode_fullscreen")):
            if layout[key].collidepoint(pos):
                self.apply_window_mode(index)
                return
        if layout["back"].collidepoint(pos):
            self.state = "menu"
            self.state_time = 0


    # --- Игровая сцена ---
    def draw_hud(self):
        draw_panel(self.canvas, pygame.Rect(0, 0, LOGICAL_WIDTH, 34),
                   fill=(12, 11, 18, 216), border=(88, 78, 64), thickness=1,
                   highlight=False)

        name = settings.LEVEL_NAMES.get(self.level, "")
        name_rect = self.font.draw(self.canvas, name, (14, 9), color=settings.TEXT_ACCENT)
        collected = self.score - self.level_start_score
        self.draw_muted(f"Монеты {collected}/{self.coin_total}",
                        (name_rect.right + 16, 9))

        if self.skeleton_total:
            self.draw_muted(f"Скелеты {self.kills}/{self.skeleton_total}",
                            (LOGICAL_WIDTH - 150, 9), anchor="topright")

        if self.player is not None:
            draw_hearts(self.canvas, (LOGICAL_WIDTH - 12, 26), self.player.hp,
                        self.player.max_hp, scale=2)

        if self.boss is not None and self.boss.alive:
            bar = pygame.Rect(210, 42, 380, 18)
            draw_panel(self.canvas, bar, fill=(22, 14, 16, 224), border=(126, 74, 60),
                       thickness=1, highlight=False)
            ratio = self.boss.hp / max(1, self.boss.max_hp)
            fill = pygame.Rect(bar.x + 2, bar.y + 2,
                               int((bar.width - 4) * ratio), bar.height - 4)
            if fill.width > 0:
                pygame.draw.rect(self.canvas, (196, 52, 42), fill)
                pygame.draw.rect(self.canvas, (240, 124, 82), fill, 1)
            self.font.draw(self.canvas, "ДРАКОН", (bar.x - 10, bar.centery),
                           anchor="midright", color=settings.TEXT_ACCENT, shadow=True)
            self.font.draw(self.canvas, f"{self.boss.hp}/{self.boss.max_hp}",
                           (bar.right - 8, bar.y + 1), anchor="topright",
                           color=(252, 236, 222), shadow=True)

    def draw_playing(self, mouse):
        camera = int(self.camera_x)
        offset = (-camera, 0)
        self.draw_background(self.level, settings.LEVEL_DIM_ALPHA.get(self.level, 0),
                             camera)

        for wall in self.walls:
            rect = wall.rect.move(offset)
            if rect.right > -BLOCK and rect.left < LOGICAL_WIDTH + BLOCK:
                self.canvas.blit(wall.image, rect)
        for bridge in self.bridges:
            bridge.draw(self.canvas, offset)
        for spike in self.spikes:
            rect = spike.rect.move(offset)
            if rect.right > 0 and rect.left < LOGICAL_WIDTH:
                self.canvas.blit(spike.image, rect)
        for coin in self.coins:
            rect = coin.draw_rect.move(offset)
            if rect.right > 0 and rect.left < LOGICAL_WIDTH:
                self.canvas.blit(coin.image, rect)
        for heart in self.hearts:
            if -40 < heart.rect.centerx - camera < LOGICAL_WIDTH + 40:
                heart.draw(self.canvas, offset)
        for lever in self.levers:
            if -60 < lever.rect.centerx - camera < LOGICAL_WIDTH + 60:
                lever.draw(self.canvas, offset)
        if self.goal is not None:
            self.goal.draw(self.canvas, offset)

        if self.boss is not None:
            self.boss.draw(self.canvas, self.font)

        for skeleton in self.skeletons:
            if -90 < skeleton.rect.centerx - camera < LOGICAL_WIDTH + 90:
                skeleton.draw(self.canvas, offset)

        player = self.player
        if player is not None and player.alive and player.visible:
            self.canvas.blit(player.image, player.draw_rect.move(offset))

        if self.boss is not None:
            self.boss.draw_front(self.canvas)

        for effect in self.effects:
            effect.draw(self.canvas, self.font, offset)

        self.draw_darkness()

        if self.near_lever is not None:
            lever = self.near_lever
            box = pygame.Rect(0, 0, 152, 28)
            box.midbottom = (lever.rect.centerx - camera, lever.rect.top - 12)
            draw_panel(self.canvas, box, fill=(14, 12, 20, 228), border=(126, 104, 74),
                       thickness=1, highlight=False)
            self.font.draw(self.canvas, "E / У — рычаг", box.center, anchor="center",
                           color=settings.TEXT_ACCENT, shadow=True)

        self.draw_hud()
        self.ui = {}

        if self.message_timer > 0 and self.death_timer == 0 and self.transition_timer == 0:
            box = pygame.Rect(0, 0, 400, 46)
            box.midtop = (LOGICAL_WIDTH // 2, 72)
            draw_panel(self.canvas, box, fill=(14, 12, 20, 216), border=(126, 104, 74),
                       thickness=2)
            self.font.draw(self.canvas, self.message, box.center, anchor="center",
                           color=settings.TEXT_ACCENT, shadow=True)

        if self.transition_timer > 0:
            self.dim_screen(150)
            self.font.draw(self.canvas, "УРОВЕНЬ ПРОЙДЕН!", (LOGICAL_WIDTH // 2, 210),
                           scale=3, color=settings.TEXT_ACCENT, anchor="center",
                           shadow=True)
            self.font.draw(self.canvas,
                           f"{settings.LEVEL_NAMES.get(self.level, '')}: монет "
                           f"{self.transition_collected}/{self.coin_total}",
                           (LOGICAL_WIDTH // 2, 268), anchor="center", shadow=True)
            for index in range(3):
                draw_star(self.canvas,
                          (LOGICAL_WIDTH // 2 + (index - 1) * 46, 318), 18,
                          filled=index < self.stars_earned)
            self.draw_muted("1 звезда — 50% монет, 2 — 80%, 3 — все монеты",
                            (LOGICAL_WIDTH // 2, 362), anchor="center")

        if self.death_timer > 0:
            self.dim_screen(175)
            self.font.draw(self.canvas, "ВЫ ПОГИБЛИ", (LOGICAL_WIDTH // 2, 210),
                           scale=3, color=(232, 74, 74), anchor="center", shadow=True)
            self.draw_muted("Сердца закончились — нажмите «ЗАНОВО» или R",
                            (LOGICAL_WIDTH // 2, 262), anchor="center")
            restart = pygame.Rect(300, 306, 200, 48)
            self.draw_button(restart, "ЗАНОВО", restart.collidepoint(mouse),
                             primary=True)
            self.draw_muted("R — быстрый перезапуск", (LOGICAL_WIDTH // 2, 372),
                            anchor="center")
            self.ui = {"death_restart": restart}

    def draw_victory(self, mouse):
        self.draw_background(3, 70)
        for index in range(30):
            x = (index * 89 + int(self.state_time * 0.7)) % (LOGICAL_WIDTH + 20) - 10
            y = (LOGICAL_HEIGHT - (index * 57 + int(self.state_time * 0.8))
                 % (LOGICAL_HEIGHT + 40))
            color = (255, 190, 70) if index % 3 == 0 else (150, 96, 54)
            pygame.draw.rect(self.canvas, color, (x, y, 2, 2))
        self.dim_screen(70)

        self.font.draw(self.canvas, "ПОБЕДА!", (LOGICAL_WIDTH // 2, 140),
                       scale=4, color=settings.TEXT_ACCENT, anchor="center", shadow=True)
        self.font.draw(self.canvas, "Дракон повержен", (LOGICAL_WIDTH // 2, 214),
                       scale=2, anchor="center", shadow=True)
        self.draw_muted(f"Собрано монет за игру: {self.score}",
                        (LOGICAL_WIDTH // 2, 258), anchor="center")
        self.font.draw(self.canvas, f"Всего звёзд: {progress.total_stars()} / 9",
                       (LOGICAL_WIDTH // 2, 288), anchor="center",
                       color=(255, 226, 150), shadow=True)

        again = pygame.Rect(LOGICAL_WIDTH // 2 - 165, 320, 150, 48)
        menu = pygame.Rect(LOGICAL_WIDTH // 2 + 15, 320, 150, 48)
        self.draw_button(again, "ЕЩЁ РАЗ", again.collidepoint(mouse), primary=True)
        self.draw_button(menu, "В МЕНЮ", menu.collidepoint(mouse))
        self.draw_muted("Спасибо за игру!", (LOGICAL_WIDTH // 2, 410), anchor="center")
        self.ui = {"again": again, "menu": menu}


    # --- События ---
    def handle_click(self, pos):
        if self.state == "menu":
            layout = self.menu_layout()
            if layout["play"].collidepoint(pos):
                self.state = "level_select"
                self.state_time = 0
            elif layout["settings"].collidepoint(pos):
                self.state = "settings"
                self.state_time = 0
                self.dropdown_open = False
            elif layout["quit"].collidepoint(pos):
                self.running = False
        elif self.state == "level_select":
            layout = self.level_select_layout()
            for level, rect in layout["cards"].items():
                if rect.collidepoint(pos):
                    self.start_game(level)
                    return
            if layout["back"].collidepoint(pos):
                self.state = "menu"
                self.state_time = 0
        elif self.state == "settings":
            self.handle_settings_click(pos)
        elif self.state == "playing":
            if self.death_timer > 0:
                restart = self.ui.get("death_restart")
                if restart is not None and restart.collidepoint(pos):
                    self.restart_level()
                return
            if self.transition_timer > 0:
                return
            if self.player is not None:
                if self.player.start_attack():
                    self.sfx.play("swing")
        elif self.state == "victory":
            if self.ui.get("again") and self.ui["again"].collidepoint(pos):
                self.start_game(3)
            elif self.ui.get("menu") and self.ui["menu"].collidepoint(pos):
                self.go_menu()

    def handle_key(self, key):
        if self.state == "playing":
            if key == pygame.K_ESCAPE:
                self.go_menu()
            elif key == pygame.K_r and self.death_timer > 0:
                self.restart_level()
            elif key == pygame.K_e:
                if self.death_timer == 0 and self.transition_timer == 0:
                    self.try_interact()
            return

        if self.state == "victory":
            if key == pygame.K_ESCAPE:
                self.go_menu()
            return

        if key == pygame.K_ESCAPE:
            if self.state == "settings" and self.dropdown_open:
                self.dropdown_open = False
            elif self.state in ("settings", "level_select"):
                self.state = "menu"
                self.state_time = 0

    # --- Рендер ---
    def draw(self, mouse):
        if self.state == "menu":
            self.draw_menu(mouse)
        elif self.state == "level_select":
            self.draw_level_select(mouse)
        elif self.state == "settings":
            self.draw_settings(mouse)
        elif self.state == "playing":
            self.draw_playing(mouse)
        elif self.state == "victory":
            self.draw_victory(mouse)

    def present(self):
        scale, offset_x, offset_y = self.viewport()
        if abs(scale - 1.0) < 0.001 and offset_x < 1 and offset_y < 1:
            self.screen.blit(self.canvas, (0, 0))
        else:
            width = max(1, int(LOGICAL_WIDTH * scale))
            height = max(1, int(LOGICAL_HEIGHT * scale))
            scaled = pygame.transform.scale(self.canvas, (width, height))
            self.screen.fill((0, 0, 0))
            self.screen.blit(scaled, (int(offset_x), int(offset_y)))
        pygame.display.flip()

    def run(self):
        while self.running:
            mouse = self.logical_mouse()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    progress.save_audio_volumes(settings.MUSIC_VOLUME,
                                                settings.SFX_VOLUME)
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(self.logical_mouse())
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.dragging_slider == "sfx":
                        self.sfx.play("coin")   # проверка громкости после перетаскивания
                    if self.dragging_slider:
                        progress.save_audio_volumes(settings.MUSIC_VOLUME,
                                                    settings.SFX_VOLUME)
                    self.dragging_slider = None
                elif event.type == pygame.MOUSEMOTION and self.dragging_slider:
                    x = self.logical_mouse()[0]
                    if self.dragging_slider == "music":
                        self.set_music_volume_from_x(x)
                    else:
                        self.set_sfx_volume_from_x(x)

            if self.state == "playing":
                self.update_playing(pygame.key.get_pressed())

            self.state_time += 1
            self.draw(mouse)
            self.present()
            self.clock.tick(settings.FPS)

        pygame.quit()


def main():
    Game().run()


if __name__ == "__main__":
    main()
