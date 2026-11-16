import pygame
import sys
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, TEXT_COLOR
from player import Player
from entities import Wall

# Инициализация
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Комната передвижения")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 20)

# Создаем группы спрайтов
walls = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()

# Строим комнату (границы)
floor = Wall(0, 550, 800, 50)       # Пол
ceiling = Wall(0, 0, 800, 30)       # Потолок
left_wall = Wall(0, 0, 30, 600)     # Левая стена
right_wall = Wall(770, 0, 30, 600)  # Правая стена

# Добавим преграду/платформу внутри комнаты для прыжков
platform = Wall(250, 400, 300, 20)

room_elements = [floor, ceiling, left_wall, right_wall, platform]
for element in room_elements:
    walls.add(element)
    all_sprites.add(element)

# Создаем игрока внутри комнаты
player = Player(100, 480)
all_sprites.add(player)

# Игровой цикл
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                player.jump()

    # Получаем нажатия клавиш и передаем в управление игрока
    keys = pygame.key.get_pressed()
    player.handle_input(keys)

    # Обновляем состояние персонажа (передаем стены для столкновений)
    player.update(walls)

    # Отрисовка
    screen.fill(BG_COLOR)
    all_sprites.draw(screen)

    # Вывод подсказки по управлению
    text = font.render("Управление: A / D или Стрелочки | Прыжок: Пробел / W / Вверх", True, TEXT_COLOR)
    screen.blit(text, (50, 50))

    pygame.display.flip()
    clock.tick(FPS)
