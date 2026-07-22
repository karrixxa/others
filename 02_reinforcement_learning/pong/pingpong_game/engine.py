import pygame
from entities import Ball, Paddle

class GameEngine:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Hermes Agent Ping Pong - High Perf Edition")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 32)
        
        self.player = Paddle(20, height // 2 - 50, 15, 100, (255, 255, 255))
        self.opponent = Paddle(width - 35, height // 2 - 50, 15, 100, (200, 0, 0))
        self.ball = Ball(width // 2, height // 2, 12, (255, 255, 0))
        
        self.player_score = 0
        self.opponent_score = 0

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP]:
            self.player.move(-self.player.speed, dt)
        if keys[pygame.K_DOWN]:
            self.player.move(self.player.speed, dt)

    def update(self, dt, ai_agent):
        self.ball.update(dt)
        ai_agent.update(self.opponent, self.ball, dt)
        
        if self.ball.pos.y <= self.ball.radius or self.ball.pos.y >= self.height - self.ball.radius:
            self.ball.bounce_y()
            if self.ball.pos.y <= self.ball.radius:
                self.ball.pos.y = self.ball.radius + 1
            elif self.ball.pos.y >= self.height - self.ball.radius:
                self.ball.pos.y = self.height - self.ball.radius - 1
            
        ball_rect = pygame.Rect(self.ball.pos.x - self.ball.radius, self.ball.pos.y - self.ball.radius, 
                                self.ball.radius * 2, self.ball.radius * 2)
        
        if ball_rect.colliderect(self.player.rect):
            self.ball.bounce_x()
            self.ball.vel.x *= 1.1
            self.ball.pos.x = self.player.rect.right + self.ball.radius
            
        if ball_rect.colliderect(self.opponent.rect):
            self.ball.bounce_x()
            self.ball.vel.x *= 1.1
            self.ball.pos.x = self.opponent.rect.left - self.ball.radius

        if self.ball.pos.x < 0:
            self.opponent_score += 1
            self.ball.reset()
        elif self.ball.pos.x > self.width:
            self.player_score += 1
            self.ball.reset()

    def draw(self):
        self.screen.fill((30, 30, 30))
        pygame.draw.aaline(self.screen, (100, 100, 100), (self.width // 2, 0), (self.width // 2, self.height))
        self.player.draw(self.screen)
        self.opponent.draw(self.screen)
        self.ball.draw(self.screen)
        
        player_text = self.font.render(f"{self.player_score}", True, (255, 255, 255))
        opp_text = self.font.render(f"{self.opponent_score}", True, (255, 255, 255))
        self.screen.blit(player_text, (self.width // 4, 20))
        self.screen.blit(opp_text, (3 * self.width // 4, 20))
        
        pygame.display.flip()
