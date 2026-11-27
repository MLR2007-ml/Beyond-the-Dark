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
SFX_VOLUME = 0.7

BG_COLOR = (18, 16, 28)
WALL_COLOR = (80, 80, 100)
PLAYER_COLOR = (50, 205, 50)
TEXT_COLOR = (232, 228, 214)
TEXT_ACCENT = (255, 214, 92)
TEXT_SHADOW = (14, 12, 20)

# Получаем путь к папке, где лежит этот файл
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# --- ПИКСЕЛЬНЫЙ ШРИФТ ---
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "PixelifySans.ttf")
FONT_SIZE = 16

# --- СПРАЙТЫ ---
PLAYER_WALK_LEFT_DIR = os.path.join(ASSETS_DIR, "animation_player", "walk_left")
PLAYER_WALK_RIGHT_DIR = os.path.join(ASSETS_DIR, "animation_player", "walk_right")
PLAYER_COMBAT_DIR = os.path.join(ASSETS_DIR, "animation_player", "combat")
PLAYER_HEIGHT = 58
PLAYER_MAX_HP = 3
PLAYER_INVULN_TICKS = 90      # ~1.5 сек неуязвимости после урона
PLAYER_SPAWN_INVULN_TICKS = 70  # неуязвимость сразу после появления на уровне
PLAYER_ATTACK_DAMAGE = 40

COIN_IMAGE = os.path.join(ASSETS_DIR, "coin.jpg")
COIN_SIZE = 40

BOSS_IMAGE = os.path.join(ASSETS_DIR, "boss", "boss_dragon.png")
BOSS_ATTACK_FRAMES = [
    os.path.join(ASSETS_DIR, "boss", f"attack_{i}.png") for i in range(1, 9)
]
BOSS_HEIGHT = 200                    # ~2 высоты игрока: босс, но не перекрывает арену
BOSS_GROUND_OFFSET = 0               # низ спрайта заходит на плиту пола — лапы стоят, а не парят
BOSS_MAX_HP = 480                    # 12 ударов мечом вместо 25
BOSS_CHASE_SPEED = 1.2
BOSS_FLAME_RANGE = 185               # ближе этого — атака пламенем, дальше — скалы
BOSS_ATTACK_COOLDOWN = 130           # тиков между атаками
BOSS_TELEGRAPH_TICKS = 40            # сколько висит "!" перед атакой
BOSS_FLAME_TICKS = 60
BOSS_RECOVER_TICKS = 34
BOSS_CONTACT_DAMAGE = 1

# --- СКАЛЫ БОССА (вместо фаерболов) ---
# Один спрайт-сталактит: белый фон вырезается при загрузке (boss.py).
ROCK_IMAGE = os.path.join(ASSETS_DIR, "stalactites", "big.jpg")
# Высота сталактита в пикселях; ширина считается по пропорциям спрайта.
ROCK_SIZES = {"small": 64, "medium": 84, "big": 108}
ROCK_GRAVITY = 0.55
ROCK_FALL_SPEED = 2.0
ROCK_WARMUP_TICKS = 24               # скала трясётся под потолком перед падением
ROCK_COUNT = 2                       # сколько глыб падает за одну атаку
ROCK_DAMAGE = 1

# --- ХИЛКИ ---
HEART_HEAL = 1

# --- ФОНЫ УРОВНЕЙ ---
BACKGROUNDS = {
    1: os.path.join(ASSETS_DIR, "background", "background_1lvl.jpg"),
    2: os.path.join(ASSETS_DIR, "background", "background_2lvl.jpg"),
    3: os.path.join(ASSETS_DIR, "background", "dragon_background.jpg"),
}

# Затемнение фона по уровням (основная тьма — отдельным слоем с кругом света)
LEVEL_DIM_ALPHA = {
    1: 30,
    2: 55,
    3: 0,
}

LEVEL_NAMES = {
    1: "Лес",
    2: "Пещера",
    3: "Финал",
}

# И привязываем пути к музыке через os.path.join
LEVEL_MUSIC = {
    "lobby": os.path.join(BASE_DIR, "music", "menu.mp3"),
    1: os.path.join(BASE_DIR, "music", "lvl1.mp3"),
    2: os.path.join(BASE_DIR, "music", "lvl2.mp3"),
    3: os.path.join(BASE_DIR, "music", "lvl3.mp3"),
}

# --- ЗВУКОВЫЕ ЭФФЕКТЫ ---
SOUNDS = {
    "swing": os.path.join(BASE_DIR, "music", "sword-saber-swing-in-the-air-2.mp3"),
    "skeleton_hit": os.path.join(BASE_DIR, "music", "a-loud-clear-cracking-sound.mp3"),
    "coin": os.path.join(BASE_DIR, "music", "svetilo-dobyito--siyanie.mp3"),
    "heal": os.path.join(BASE_DIR, "music", "serdechko--jizn-1.mp3"),
}

WINDOW_MODES = ["Оконный", "Без рамок", "Полный экран"]
current_mode_index = 0

# --- ПРОГРЕСС ---
SAVE_FILE = os.path.join(BASE_DIR, "save.json")
STAR_THRESHOLDS = (0.5, 0.8)   # 50% монет — 1 звезда, 80% — 2, 100% — 3

# --- ВРАГИ: СКЕЛЕТЫ ПЕЩЕРЫ ---
SKELETON_SHEET = os.path.join(ASSETS_DIR, "skeleton.jpg")   # лист из 4 кадров
SKELETON_HEIGHT = 58           # высота фигуры скелета на экране
SKELETON_HP = 80
SKELETON_SPEED = 1.6           # патруль
SKELETON_CHASE_SPEED = 2.6     # погоня
SKELETON_DETECT_RANGE = 330
SKELETON_ATTACK_RANGE = 56
SKELETON_ATTACK_WINDUP = 18    # тиков до удара топором
SKELETON_ATTACK_TICKS = 34
SKELETON_ATTACK_COOLDOWN = 95
SKELETON_DAMAGE = 1
SKELETON_WAKE_TICKS = 55       # пауза перед погоней после старта уровня
SKELETON_HURT_STUN = 30        # скелет не контратакует сразу после попадания

# --- ТЬМА УРОВНЕЙ: затемнение всего уровня + круг света вокруг игрока ---
LEVEL_DARKNESS = {1: 96, 2: 190, 3: 44}
LEVEL_LIGHT_RADIUS = {1: 300, 2: 205, 3: 340}
