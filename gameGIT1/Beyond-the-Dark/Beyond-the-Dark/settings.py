# settings.py
import os
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Расширенный диапазон разрешений до 1920x1080
RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080)
]
current_res_index = 0

MUSIC_VOLUME = 0.5

BG_COLOR = (30, 30, 40)
WALL_COLOR = (80, 80, 100)
PLAYER_COLOR = (50, 205, 50)
TEXT_COLOR = (220, 220, 220)

# Получаем путь к папке, где лежит этот файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# И привязываем пути к музлу через os.path.join
LEVEL_MUSIC = {
    "lobby": os.path.join(BASE_DIR, "music", "menu.mp3"),
    1: os.path.join(BASE_DIR, "music", "lvl1.mp3"),
    2: os.path.join(BASE_DIR, "music", "lvl2.mp3"),
    3: os.path.join(BASE_DIR, "music", "lvl3.mp3"),
}

WINDOW_MODES = ["Оконный", "Без рамок"]
current_mode_index = 0