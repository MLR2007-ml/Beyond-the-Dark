import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_COLOR

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 30
        self.height = 40
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill((50, 205, 50))  # Зеленый прямоугольник игрока
        
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        # Физические переменные
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5          # Скорость бега
        self.gravity = 0.6      # Сила гравитации
        self.jump_power = -12   # Мощность прыжка (отрицательная, так как ось Y идет вниз)
        self.on_ground = False

    def handle_input(self, keys):
        # Движение влево/вправо с поддержкой мульти-нажатия
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = self.speed
            
        # Прыжок теперь тоже работает по зажатию/опросу клавиш (мгновенно и без багов)
        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

    def update(self, walls):
        # Горизонтальное движение и коллизии
        self.rect.x += self.vel_x
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_x > 0:
                    self.rect.right = wall.rect.left
                elif self.vel_x < 0:
                    self.rect.left = wall.rect.right

        # Вертикальное движение (гравитация) и коллизии
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