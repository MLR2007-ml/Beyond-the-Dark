
import os
import pygame
import settings
from player import Player
from entities import Wall, Coin

ASSETS_DIR = "assets"


def _find_asset(base_name):
    """Ищет файл в папке assets независимо от расширения (.jpg, .png и т.д.)."""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = os.path.join(ASSETS_DIR, f"{base_name}{ext}")
        if os.path.exists(path):
            return path
    return None


def load_coin_frames(target_size=(24, 24)):
    """Загружает анимацию монетки из assets/coin.* (спрайт-лист или один кадр)."""
    path = _find_asset("coin")
    if not path:
        return []

    try:
        sheet = pygame.image.load(path).convert_alpha()
        sw, sh = sheet.get_size()

        if sw > sh * 1.5:
            num_frames = max(1, round(sw / sh))
            frame_w = sw // num_frames
            frames = []
            for i in range(num_frames):
                frame = pygame.Surface((frame_w, sh), pygame.SRCALPHA)
                frame.blit(sheet, (0, 0), (i * frame_w, 0, frame_w, sh))
                frames.append(pygame.transform.scale(frame, target_size))
            return frames

        return [pygame.transform.scale(sheet, target_size)]
    except Exception:
        return []


def _create_coin(cx, cy, coin_frames):
    """Создаёт экземпляр Coin независимо от того, ждёт ли он frames или только (x, y)."""
    if coin_frames:
        try:
            return Coin(cx, cy, coin_frames)
        except TypeError:
            coin = Coin(cx, cy)
            coin.image = coin_frames[0]
            coin.rect = coin.image.get_rect(center=(cx, cy))
            return coin
    return Coin(cx, cy)


def get_level_background(level_num, size):
    """Возвращает фон уровня. Для 1-го уровня берёт assets/background_1lvl.*."""
    w, h = size
    if level_num == 1:
        bg_path = _find_asset("background_1lvl")
        if bg_path:
            try:
                bg = pygame.image.load(bg_path).convert()
                return pygame.transform.scale(bg, (w, h))
            except Exception:
                pass

    surf = pygame.Surface((w, h))
    surf.fill((36, 39, 48))
    return surf


def build_level(level_num, coin_frames=None):
    """
    Создаёт группы спрайтов и игрока для выбранного уровня (1, 2 или 3).
    Возвращает: (player, walls, coins, all_sprites)
    """
    if coin_frames is None:
        coin_frames = load_coin_frames()

    walls = pygame.sprite.Group()
    coins = pygame.sprite.Group()
    all_sprites = pygame.sprite.Group()

    # Берём актуальный размер экрана из settings,
    # который синхронизируется в MenuManager.apply_display()
    w, h = settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT
    wall_t = 28
    floor_y = h - wall_t

    room_walls = [
        Wall(0, floor_y, w, wall_t),          # Пол
        Wall(0, 0, w, wall_t),               # Потолок
        Wall(0, 0, wall_t, h),               # Левая стена
        Wall(w - wall_t, 0, wall_t, h),      # Правая стена
    ]

    player_start = (wall_t + 30, floor_y - 50)
    coin_coords = []

    if level_num == 1:
        p1 = pygame.Rect(int(w * 0.18), floor_y - 88, int(w * 0.24), 20)
        p2 = pygame.Rect(int(w * 0.48), p1.top - 92, int(w * 0.24), 20)
        p3 = pygame.Rect(int(w * 0.22), p2.top - 92, int(w * 0.30), 20)

        room_walls.extend([
            Wall(p1.x, p1.y, p1.w, p1.h),
            Wall(p2.x, p2.y, p2.w, p2.h),
            Wall(p3.x, p3.y, p3.w, p3.h),
        ])
        coin_coords = [
            (p1.centerx, p1.top - 24),
            (p2.centerx, p2.top - 24),
            (p3.centerx, p3.top - 24),
        ]

    elif level_num == 2:
        # Прыжок персонажа ~120 px, поэтому между платформами
        # по высоте оставляем не больше ~95 px.
        # Строим "лесенку" от пола вверх.

        # Нижний ярус (близко к полу)
        p1 = pygame.Rect(int(w * 0.10), floor_y - 95, int(w * 0.22), 20)
        p2 = pygame.Rect(int(w * 0.40), floor_y - 95, int(w * 0.22), 20)
        p3 = pygame.Rect(int(w * 0.68), floor_y - 95, int(w * 0.22), 20)

        # Средний ярус (на ~95 px выше нижнего)
        p4 = pygame.Rect(int(w * 0.22), p1.top - 95, int(w * 0.22), 20)
        p5 = pygame.Rect(int(w * 0.52), p1.top - 95, int(w * 0.22), 20)

        # Верхний ярус (ещё на ~95 px выше)
        p6 = pygame.Rect(int(w * 0.34), p4.top - 95, int(w * 0.22), 20)
        p7 = pygame.Rect(int(w * 0.62), p4.top - 95, int(w * 0.22), 20)

        room_walls.extend([
            Wall(p1.x, p1.y, p1.w, p1.h),
            Wall(p2.x, p2.y, p2.w, p2.h),
            Wall(p3.x, p3.y, p3.w, p3.h),
            Wall(p4.x, p4.y, p4.w, p4.h),
            Wall(p5.x, p5.y, p5.w, p5.h),
            Wall(p6.x, p6.y, p6.w, p6.h),
            Wall(p7.x, p7.y, p7.w, p7.h),
        ])

        coin_coords = [
            (p2.centerx, p2.top - 24),
            (p4.centerx, p4.top - 24),
            (p5.centerx, p5.top - 24),
            (p6.centerx, p6.top - 24),
            (p7.centerx, p7.top - 24),
        ]

    else:  # Уровень 3
        low_l = pygame.Rect(int(w * 0.14), floor_y - 85, int(w * 0.24), 20)
        low_r = pygame.Rect(int(w * 0.56), floor_y - 85, int(w * 0.24), 20)

        mid_l = pygame.Rect(int(w * 0.28), low_l.top - 88, int(w * 0.22), 20)
        mid_r = pygame.Rect(int(w * 0.56), low_l.top - 88, int(w * 0.22), 20)

        step_l = pygame.Rect(wall_t + 10, mid_l.top - 85, int(w * 0.14), 20)
        top_l = pygame.Rect(int(w * 0.26), step_l.top - 85, int(w * 0.24), 20)
        top_r = pygame.Rect(int(w * 0.56), top_l.top, int(w * 0.26), 20)

        room_walls.extend([
            Wall(low_l.x, low_l.y, low_l.w, low_l.h),
            Wall(low_r.x, low_r.y, low_r.w, low_r.h),
            Wall(mid_l.x, mid_l.y, mid_l.w, mid_l.h),
            Wall(mid_r.x, mid_r.y, mid_r.w, mid_r.h),
            Wall(step_l.x, step_l.y, step_l.w, step_l.h),
            Wall(top_l.x, top_l.y, top_l.w, top_l.h),
            Wall(top_r.x, top_r.y, top_r.w, top_r.h),
        ])
        coin_coords = [
            (low_r.centerx, low_r.top - 24),
            (mid_l.centerx, mid_l.top - 24),
            (mid_r.centerx, mid_r.top - 24),
            (step_l.centerx, step_l.top - 24),
            (top_l.centerx, top_l.top - 24),
            (top_r.centerx, top_r.top - 24),
        ]

    for wall in room_walls:
        walls.add(wall)
        all_sprites.add(wall)

    for cx, cy in coin_coords:
        coin = _create_coin(cx, cy, coin_frames)
        coins.add(coin)
        all_sprites.add(coin)

    player = Player(*player_start)
    all_sprites.add(player)

    return player, walls, coins, all_sprites
