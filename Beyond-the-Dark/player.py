import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_COLOR

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.width = 30
        self.height = 40
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(PLAYER_COLOR)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        self.vel_x = 0
        self.vel_y = 0
        self.speed = 5
        self.jump_force = -11
        self.gravity = 0.5
        self.on_ground = False

    def handle_input(self, keys):
        """Обработка управления персонажем"""
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = self.speed

    def update(self, walls):
        # Движение по горизонтали и коллизии
        self.rect.x += self.vel_x
        self.handle_collision_x(walls)

        # Движение по вертикали (гравитация) и коллизии
        self.vel_y += self.gravity
        self.rect.y += self.vel_y
        self.on_ground = False
        self.handle_collision_y(walls)

    def handle_collision_x(self, walls):
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_x > 0:
                    self.rect.right = wall.rect.left
                elif self.vel_x < 0:
                    self.rect.left = wall.rect.right

    def handle_collision_y(self, walls):
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if self.vel_y > 0:
                    self.rect.bottom = wall.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = wall.rect.bottom
                    self.vel_y = 0

    def jump(self):
        if self.on_ground:
            self.vel_y = self.jump_force
            self.on_ground = False
