# player.py
import os
import pygame
from settings import PLAYER_COLOR, PLAYER_SPRITE_SHEET

# --- Параметры спрайт-листа персонажа (assets/animations.jpg) ---
SPRITE_BG_COLOR = (255, 255, 255)          # белый фон листа (JPG без прозрачности)
SPRITE_BG_TOLERANCE = (40, 40, 40, 255)    # допуск на "почти белый" (артефакты JPG)
SPRITE_MIN_WIDTH = 60                      # отсекаем мечи и монету в нижней части листа
SPRITE_MIN_HEIGHT = 150
ROW_TOLERANCE = 40                         # рамки в одной строке, если y отличается не более чем на это

PLAYER_HEIGHT = 40                         # высота персонажа на экране (под высоту блока 50)
RUN_FRAME_TICKS = 7                        # тиков на один кадр ходьбы


def _read_sheet():
    """Загружает лист и убирает белый фон. Возвращает (поверхность, маска) или None."""
    if not os.path.exists(PLAYER_SPRITE_SHEET):
        print(f"[ОШИБКА] Файл не найден: {PLAYER_SPRITE_SHEET}")
        return None

    try:
        sheet = pygame.image.load(PLAYER_SPRITE_SHEET)
    except pygame.error as e:
        print(f"[ОШИБКА] Не удалось загрузить спрайт-лист: {e}")
        return None

    # Копия с альфа-каналом: JPG не умеет в прозрачность
    art = pygame.Surface(sheet.get_size(), pygame.SRCALPHA)
    art.blit(sheet, (0, 0))

    mask = pygame.mask.from_threshold(art, SPRITE_BG_COLOR, SPRITE_BG_TOLERANCE)
    mask.invert()   # 1 — пиксели персонажа, 0 — белый фон
    alpha = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    art.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return art, mask


def _split_rows(mask):
    """Делит найденные рамки на строки листа (каждая строка отсортирована слева направо)."""
    rects = [r for r in mask.get_bounding_rects()
             if r.width >= SPRITE_MIN_WIDTH and r.height >= SPRITE_MIN_HEIGHT]
    if not rects:
        return []

    rects.sort(key=lambda r: (r.y, r.x))
    rows = []
    for rect in rects:
        if rows and abs(rect.y - rows[-1][0].y) <= ROW_TOLERANCE:
            rows[-1].append(rect)
        else:
            rows.append([rect])

    for row in rows:
        row.sort(key=lambda r: r.x)
    return rows


def _make_frame(art, rect, scale, canvas_size, flip=False):
    """Вырезает кадр, масштабирует и ставит на общий холст (по центру, ноги — внизу)."""
    frame = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    frame.blit(art, (0, 0), rect)

    size = (max(1, int(round(rect.width * scale))),
            max(1, int(round(rect.height * scale))))
    # scale (не smoothscale) — чтобы пиксель-арт оставался чётким
    scaled = pygame.transform.scale(frame, size)
    if flip:
        scaled = pygame.transform.flip(scaled, True, False)

    canvas = pygame.Surface(canvas_size, pygame.SRCALPHA)
    canvas.blit(scaled, scaled.get_rect(midbottom=(canvas_size[0] // 2, canvas_size[1])))
    return canvas.convert_alpha()


def _load_frames():
    """Нарезает лист на кадры по состояниям. Возвращает словарь кадров или None."""
    loaded = _read_sheet()
    if not loaded:
        return None
    art, mask = loaded

    rows = _split_rows(mask)
    if not rows:
        print("[ОШИБКА] На спрайт-листе не найдено персонажей.")
        return None

    # Первая строка листа: стойка — самый первый кадр
    idle_rects = [rows[0][0]]

    # Вторая строка: два кадра ходьбы влево, два — вправо, последний — прыжок (рука вверх)
    walk_left_rects, walk_right_rects, jump_rects = [], [], []
    if len(rows) > 1:
        second = rows[1]
        walk_left_rects = second[0:2]
        walk_right_rects = second[2:4]
        jump_rects = second[4:5]

    # Страховки, если лист оказался другим или кадров меньше
    if not walk_left_rects:
        walk_left_rects = idle_rects
    if walk_right_rects:
        flip_right = False
    else:
        # правых кадров нет — зеркалим левые
        walk_right_rects = walk_left_rects
        flip_right = True
    if not jump_rects:
        jump_rects = idle_rects

    used = idle_rects + walk_left_rects + walk_right_rects + jump_rects
    scale = PLAYER_HEIGHT / max(1, rows[0][0].height)
    canvas_size = (max(max(1, int(round(r.width * scale))) for r in used),
                   max(max(1, int(round(r.height * scale))) for r in used))

    frames = {
        "idle": [_make_frame(art, r, scale, canvas_size) for r in idle_rects],
        "walk_left": [_make_frame(art, r, scale, canvas_size) for r in walk_left_rects],
        "walk_right": [_make_frame(art, r, scale, canvas_size, flip=flip_right)
                       for r in walk_right_rects],
        "jump": [_make_frame(art, r, scale, canvas_size) for r in jump_rects],
    }

    print(f"[УСПЕХ] Загружено кадров: Стойка={len(frames['idle'])}, "
          f"Ходьба влево={len(frames['walk_left'])}, "
          f"Ходьба вправо={len(frames['walk_right'])}, "
          f"Прыжок={len(frames['jump'])} (кадр {canvas_size[0]}x{canvas_size[1]})")
    return frames


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.frames = _load_frames()

        # Если спрайты не загрузились, используем зеленый квадрат
        if not self.frames:
            self.frames = {}
            self.image = pygame.Surface((30, 40))
            self.image.fill(PLAYER_COLOR)
            print("[ПРЕДУПРЕЖДЕНИЕ] Используется зеленый квадрат вместо спрайта!")
        else:
            self.image = self.frames["idle"][0]

        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # Физические переменные
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5
        self.gravity = 0.6
        self.jump_power = -12
        self.on_ground = False

        # --- ПЕРЕМЕННЫЕ АНИМАЦИИ ---
        self.state = "idle"
        self.frame_index = 0
        self.anim_timer = 0

    def handle_input(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = self.speed

        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def _animate(self):
        """Выбирает состояние и кадр анимации (все кадры одного размера)."""
        if not self.frames:
            return

        if not self.on_ground:
            state = "jump"
        elif self.vel_x > 0:
            state = "walk_right"
        elif self.vel_x < 0:
            state = "walk_left"
        else:
            state = "idle"

        frames = self.frames[state]

        if state != self.state:
            # Смена состояния — начинаем анимацию сначала
            self.state = state
            self.frame_index = 0
            self.anim_timer = 0
        elif len(frames) > 1:
            self.anim_timer += 1
            if self.anim_timer >= RUN_FRAME_TICKS:
                self.anim_timer = 0
                self.frame_index = (self.frame_index + 1) % len(frames)

        self.image = frames[self.frame_index % len(frames)]

    def update(self, walls):
        # --- ФИЗИКА И КОЛЛИЗИИ ---
        self.rect.x += self.vel_x
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_x > 0:
                    self.rect.right = wall.rect.left
                elif self.vel_x < 0:
                    self.rect.left = wall.rect.right

        self.vel_y += self.gravity
        self.rect.y += self.vel_y

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

        # Rect хранит целые координаты, поэтому при vel_y < 1 px шаг может "не дойти"
        # до стены — дополнительно проверяем 1 px под ногами
        if not self.on_ground and self.vel_y >= 0:
            probe = self.rect.move(0, 1)
            for wall in walls:
                if probe.colliderect(wall.rect):
                    self.on_ground = True
                    break

        # --- ЛОГИКА АНИМАЦИИ (после физики: on_ground уже актуален) ---
        self._animate()


