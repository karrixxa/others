import pygame

class Paddle:
    def __init__(self, x, y, width, height, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.speed = 800  # Pixels per second

    def move(self, dy, dt):
        # dy is either speed or -speed
        self.rect.y += dy * dt
        self.rect.clamp_ip(pygame.Rect(0, 0, 1280, 720))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

class Ball:
    def __init__(self, x, y, radius, color):
        self.pos = pygame.Vector2(x, y)
        self.base_speed = 600 
        self.vel = pygame.Vector2(self.base_speed, self.base_speed)
        self.radius = radius
        self.color = color

    def update(self, dt):
        self.pos += self.vel * dt

    def bounce_y(self):
        self.vel.y *= -1

    def bounce_x(self):
        self.vel.x *= -1

    def reset(self):
        self.pos = pygame.Vector2(640, 360)
        direction = 1 if self.vel.x < 0 else -1
        self.vel = pygame.Vector2(self.base_speed * direction, self.base_speed)

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)
