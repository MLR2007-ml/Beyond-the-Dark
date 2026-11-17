# main.py
import os
import pygame
import sys
import settings
from player import Player
from entities import Wall, Coin
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TEXT_COLOR, LEVEL_MUSIC

pygame.init()
pygame.mixer.init()

# Центрирование окна на экране монитора по центру
os.environ['SDL_VIDEO_CENTERED'] = '1'

# Создание или обновление экрана
screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
pygame.display.set_caption("Beyond the Dark - Меню и Настройки")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)
font_large = pygame.font.SysFont("Arial", 32)

# Применяем стартовую громкость
pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)

LEVELS = {
    1: [
        "################",
        "#$.............#",
        "#....$.........#",
        "#....#####.....#",
        "#..............#",
        "#........###...#",
        "#...$..........#",
        "#...###........#",
        "#.............$#",
        "################"
    ],
    2: [
        "################",
        "#$....$....$..$#",
        "#...###..###...#",
        "#..............#",
        "#.....###......#",
        "#...###........#",
        "#..............#",
        "#..###.....###.#",
        "#..............#",
        "################"
    ],
    3: [
        "################",
        "#$...*...*...$;#",
        "#..#####.#####$#",
        "#..............#",
        "#....###$###...#",
        "#...#..........#",
        "#..$.....$.....#",
        "#...###..###...#",
        "#..............#",
        "################"
    ]
}

def play_music(track_key):
    if track_key in LEVEL_MUSIC:
        try:
            pygame.mixer.music.load(LEVEL_MUSIC[track_key])
            pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
            pygame.mixer.music.play(-1)
        except pygame.error as e:
            print(f"Не удалось загрузить трек {track_key}: {e}")

def load_level(level_num, walls_group, coins_group, sprites_group):
    for sprite in walls_group:
        sprite.kill()
    for sprite in coins_group:
        sprite.kill()
        
    map_data = LEVELS.get(level_num, LEVELS[1])
    block_size = 50
    
    level_width = len(map_data[0]) * block_size
    level_height = len(map_data) * block_size
    
    offset_x = (settings.SCREEN_WIDTH - level_width) // 2
    offset_y = (settings.SCREEN_HEIGHT - level_height) // 2 + 50  # Чуть ниже центра для комфортных прыжков

    for row_idx, row in enumerate(map_data):
        for col_idx, char in enumerate(row):
            x = col_idx * block_size + offset_x
            y = row_idx * block_size + offset_y
            
            if char == '#':
                wall = Wall(x, y, block_size, block_size)
                walls_group.add(wall)
                sprites_group.add(wall)
            elif char == '$' or char == '*':
                coin = Coin(x, y)
                coin.rect.topleft = (x + (block_size - coin.rect.width) // 2, y + (block_size - coin.rect.height) // 2)
                coins_group.add(coin)
                sprites_group.add(coin)

    player_start = (offset_x + 50, offset_y + 400)
    new_player = Player(player_start[0], player_start[1])
    sprites_group.add(new_player)

    play_music(level_num)
    return new_player

walls = pygame.sprite.Group()
coins = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()

game_state = "menu"
current_level = 1
score = 0
player = None

dragging_slider = False
dropdown_open = False  # Состояние выпадающего списка разрешений

play_music("lobby")

# Главный игровой цикл
while True:
    mouse_pos = pygame.mouse.get_pos()
    
    # Единая инициализация координат элементов интерфейса для каждого кадра
    cx = settings.SCREEN_WIDTH // 2
    btn_play_rect = pygame.Rect(cx - 100, 220, 200, 50)
    btn_settings_rect = pygame.Rect(cx - 100, 300, 200, 50)
    btn_exit_rect = pygame.Rect(cx - 100, 380, 200, 50)

    btn_lvl1 = pygame.Rect(cx - 170, 220, 100, 50)
    btn_lvl2 = pygame.Rect(cx - 50, 220, 100, 50)
    btn_lvl3 = pygame.Rect(cx + 70, 220, 100, 50)
    
    btn_back = pygame.Rect(cx - 100, 450, 200, 50)
    
    slider_rect = pygame.Rect(cx - 100, 220, 200, 20)
    btn_res_rect = pygame.Rect(cx - 120, 280, 240, 50)
    btn_mode_rect = pygame.Rect(cx - 120, 350, 240, 50)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "menu":
                if btn_play_rect.collidepoint(mouse_pos):
                    game_state = "level_select"
                elif btn_settings_rect.collidepoint(mouse_pos):
                    game_state = "settings"
                    dropdown_open = False
                elif btn_exit_rect.collidepoint(mouse_pos):
                    pygame.quit()
                    sys.exit()
                    
            elif game_state == "level_select":
                if btn_lvl1.collidepoint(mouse_pos):
                    current_level = 1
                    score = 0
                    player = load_level(current_level, walls, coins, all_sprites)
                    game_state = current_level
                elif btn_lvl2.collidepoint(mouse_pos):
                    current_level = 2
                    score = 0
                    player = load_level(current_level, walls, coins, all_sprites)
                    game_state = current_level
                elif btn_lvl3.collidepoint(mouse_pos):
                    current_level = 3
                    score = 0
                    player = load_level(current_level, walls, coins, all_sprites)
                    game_state = current_level
                elif btn_back.collidepoint(mouse_pos):
                    game_state = "menu"
                    
            elif game_state == "settings":
                dropdown_height = len(settings.RESOLUTIONS) * 35 if dropdown_open else 0
                btn_mode_rect.y = 350 + dropdown_height
                btn_back.y = btn_mode_rect.bottom + 20

                if dropdown_open:
                    clicked_inside_dropdown = False
                    for i, res in enumerate(settings.RESOLUTIONS):
                        opt_rect = pygame.Rect(cx - 120, btn_res_rect.bottom + i * 35, 240, 35)
                        if opt_rect.collidepoint(mouse_pos):
                            settings.current_res_index = i
                            settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT = res
                            
                            os.environ['SDL_VIDEO_CENTERED'] = '1'
                            flags = pygame.NOFRAME if settings.current_mode_index == 1 else 0
                            screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), flags)
                            
                            if isinstance(game_state, int):
                                player = load_level(game_state, walls, coins, all_sprites)
                            
                            dropdown_open = False
                            clicked_inside_dropdown = True
                            break
                    
                    if not clicked_inside_dropdown:
                        if not btn_res_rect.collidepoint(mouse_pos):
                            dropdown_open = False
                else:
                    if slider_rect.collidepoint(mouse_pos):
                        dragging_slider = True
                        rel_x = mouse_pos[0] - slider_rect.x
                        settings.MUSIC_VOLUME = max(0.0, min(1.0, rel_x / slider_rect.width))
                        pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
                    elif btn_res_rect.collidepoint(mouse_pos):
                        dropdown_open = True
                    elif btn_mode_rect.collidepoint(mouse_pos):
                        settings.current_mode_index = (settings.current_mode_index + 1) % len(settings.WINDOW_MODES)
                        
                        os.environ['SDL_VIDEO_CENTERED'] = '1'
                        if settings.current_mode_index == 1:
                            screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.NOFRAME)
                        else:
                            screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
                    elif btn_back.collidepoint(mouse_pos):
                        game_state = "menu"

        elif event.type == pygame.MOUSEMOTION:
            if dragging_slider and game_state == "settings":
                rel_x = mouse_pos[0] - slider_rect.x
                settings.MUSIC_VOLUME = max(0.0, min(1.0, rel_x / slider_rect.width))
                pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            dragging_slider = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if isinstance(game_state, int):
                    game_state = "menu"
                    for s in walls: s.kill()
                    for s in coins: s.kill()
                    if player: player.kill()
                    play_music("lobby")

    # Игровая логика уровней (опрос зажатых клавиш каждый кадр для идеального мульти-нажатия)
    if isinstance(game_state, int) and player:
        keys = pygame.key.get_pressed()
        player.handle_input(keys)
        player.update(walls)

        collected_coins = pygame.sprite.spritecollide(player, coins, True)
        if collected_coins:
            score += len(collected_coins)

        if len(coins) == 0:
            if current_level < len(LEVELS):
                current_level += 1
                player = load_level(current_level, walls, coins, all_sprites)
            else:
                game_state = "menu"
                current_level = 1
                score = 0
                if player: player.kill()
                play_music("lobby")

    # --- Отрисовка ---
    screen.fill(BG_COLOR)

    if game_state == "menu":
        title = font_large.render("BEYOND THE DARK", True, TEXT_COLOR)
        screen.blit(title, (cx - title.get_width() // 2, 100))

        pygame.draw.rect(screen, (70, 130, 180), btn_play_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), btn_settings_rect, border_radius=8)
        pygame.draw.rect(screen, (180, 70, 70), btn_exit_rect, border_radius=8)

        text_play = font.render("Играть", True, (255, 255, 255))
        text_settings = font.render("Настройки", True, (255, 255, 255))
        text_exit = font.render("Выход", True, (255, 255, 255))
            
        screen.blit(text_play, (btn_play_rect.centerx - text_play.get_width() // 2, btn_play_rect.centery - text_play.get_height() // 2))
        screen.blit(text_settings, (btn_settings_rect.centerx - text_settings.get_width() // 2, btn_settings_rect.centery - text_settings.get_height() // 2))
        screen.blit(text_exit, (btn_exit_rect.centerx - text_exit.get_width() // 2, btn_exit_rect.centery - text_exit.get_height() // 2))

    elif game_state == "level_select":
        title = font_large.render("ВЫБОР УРОВНЯ", True, TEXT_COLOR)
        screen.blit(title, (cx - title.get_width() // 2, 100))

        pygame.draw.rect(screen, (50, 205, 50), btn_lvl1, border_radius=6)
        pygame.draw.rect(screen, (50, 205, 50), btn_lvl2, border_radius=6)
        pygame.draw.rect(screen, (50, 205, 50), btn_lvl3, border_radius=6)
        pygame.draw.rect(screen, (120, 120, 120), btn_back, border_radius=6)

        screen.blit(font.render("Ур. 1", True, (255, 255, 255)), (btn_lvl1.centerx - 20, btn_lvl1.centery - 10))
        screen.blit(font.render("Ур. 2", True, (255, 255, 255)), (btn_lvl2.centerx - 20, btn_lvl2.centery - 10))
        screen.blit(font.render("Ур. 3", True, (255, 255, 255)), (btn_lvl3.centerx - 20, btn_lvl3.centery - 10))
        
        back_txt = font.render("Назад в меню", True, (255, 255, 255))
        screen.blit(back_txt, (btn_back.centerx - back_txt.get_width() // 2, btn_back.centery - back_txt.get_height() // 2))

    elif game_state == "settings":
        title = font_large.render("НАСТРОЙКИ", True, TEXT_COLOR)
        screen.blit(title, (cx - title.get_width() // 2, 40))

        vol_label = font.render(f"Громкость музыки: {int(settings.MUSIC_VOLUME * 100)}%", True, TEXT_COLOR)
        screen.blit(vol_label, (cx - vol_label.get_width() // 2, 100))
        
        pygame.draw.rect(screen, (100, 100, 100), slider_rect, border_radius=4)
        handle_x = slider_rect.x + int(slider_rect.width * settings.MUSIC_VOLUME)
        pygame.draw.circle(screen, (50, 205, 50), (handle_x, slider_rect.centery), 10)

        dropdown_height = len(settings.RESOLUTIONS) * 35 if dropdown_open else 0
        btn_mode_rect.y = 350 + dropdown_height
        btn_back.y = btn_mode_rect.bottom + 20

        mode_text = f"Режим: {settings.WINDOW_MODES[settings.current_mode_index]}"
        pygame.draw.rect(screen, (70, 130, 180), btn_mode_rect, border_radius=8)
        mode_label = font.render(mode_text, True, (255, 255, 255))
        screen.blit(mode_label, (btn_mode_rect.centerx - mode_label.get_width() // 2, btn_mode_rect.centery - mode_label.get_height() // 2))

        res_text = f"Разрешение: {settings.SCREEN_WIDTH}x{settings.SCREEN_HEIGHT}  ▼"
        pygame.draw.rect(screen, (70, 130, 180), btn_res_rect, border_radius=8)
        res_label = font.render(res_text, True, (255, 255, 255))
        screen.blit(res_label, (btn_res_rect.centerx - res_label.get_width() // 2, btn_res_rect.centery - res_label.get_height() // 2))

        if dropdown_open:
            for i, res in enumerate(settings.RESOLUTIONS):
                opt_rect = pygame.Rect(cx - 120, btn_res_rect.bottom + i * 35, 240, 35)
                bg_col = (90, 150, 200) if opt_rect.collidepoint(mouse_pos) else (50, 90, 130)
                pygame.draw.rect(screen, bg_col, opt_rect)
                pygame.draw.rect(screen, (30, 30, 40), opt_rect, 1)
                
                opt_label = font.render(f"{res[0]} x {res[1]}", True, (255, 255, 255))
                screen.blit(opt_label, (opt_rect.centerx - opt_label.get_width() // 2, opt_rect.centery - opt_label.get_height() // 2))

        pygame.draw.rect(screen, (120, 120, 120), btn_back, border_radius=6)
        back_txt = font.render("Назад", True, (255, 255, 255))
        screen.blit(back_txt, (btn_back.centerx - back_txt.get_width() // 2, btn_back.centery - back_txt.get_height() // 2))

    elif isinstance(game_state, int):
        all_sprites.draw(screen)
        ui_text = font.render(f"Уровень: {current_level} | Монет: {score} | ESC - в меню", True, TEXT_COLOR)
        screen.blit(ui_text, (50, 20))

    pygame.display.flip()
    clock.tick(FPS)