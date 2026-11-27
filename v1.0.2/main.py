import os
import sys
import pygame
import settings
from menu import MenuManager
from levels import build_level, get_level_background, load_coin_frames

MUSIC_DIR = os.path.join(settings.BASE_DIR, "music")

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

# Временное окно, чтобы MenuManager мог инициализироваться
screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
pygame.display.set_caption("Beyond the Dark")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 24, bold=True)
font_large = pygame.font.SysFont("Arial", 44, bold=True)

menu = MenuManager(screen, font, font_large)
screen = menu.apply_display()  # применяем выбранный режим (окно / без рамок / полный экран)
print("START SIZE:", screen.get_size(), settings.WINDOW_MODES[settings.current_mode_index])

coin_frames = load_coin_frames()

game_state = "menu"  # "menu" или номер уровня (1, 2, 3)
current_level = None
current_track = None
player = None
walls = None
coins = None
all_sprites = None
score = 0


def _find_music_file(track_name):
    mapped = settings.LEVEL_MUSIC.get(track_name)
    if mapped and os.path.exists(mapped):
        return mapped
    if not os.path.isdir(MUSIC_DIR):
        return None
    for ext in (".mp3", ".ogg", ".wav", ".flac"):
        path = os.path.join(MUSIC_DIR, f"{track_name}{ext}")
        if os.path.exists(path):
            return path
    return None


def play_music(track_name):
    global current_track
    if track_name == current_track:
        return

    current_track = track_name
    if not pygame.mixer.get_init():
        return

    path = _find_music_file(track_name)
    if not path:
        return

    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(max(0.0, min(1.0, getattr(settings, "MUSIC_VOLUME", 0.5))))
        pygame.mixer.music.play(-1)
    except pygame.error:
        pass


def start_level(level_num):
    global game_state, current_level, player, walls, coins, all_sprites, score
    current_level = level_num
    game_state = level_num
    score = 0
    player, walls, coins, all_sprites = build_level(level_num, coin_frames=coin_frames)
    play_music(level_num)


play_music("lobby")

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if game_state == "menu":
            result = menu.handle_event(event)
            screen = menu.screen
            if result == "quit":
                pygame.quit()
                sys.exit()
            elif isinstance(result, int):
                start_level(result)

        elif isinstance(game_state, int):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = "menu"
                play_music("lobby")

    if game_state == "menu":
        menu.draw()

    elif isinstance(game_state, int):
        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        player.update(walls)
        coins.update()

        collected = pygame.sprite.spritecollide(player, coins, True)
        if collected:
            score += len(collected)

        background = get_level_background(current_level, screen.get_size())
        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill(settings.BG_COLOR)

        all_sprites.draw(screen)

        ui_text = font.render(
            f"Уровень: {current_level} | Монет: {score} | ESC - в меню",
            True,
            settings.TEXT_COLOR,
        )
        screen.blit(ui_text, (40, 34))

    pygame.display.flip()
    clock.tick(settings.FPS)
