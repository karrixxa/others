
import pygame
import sys
import torch
import torch.nn as nn
import numpy as np
from logic import Game, W, H, PADDLE_W, PADDLE_H, BALL_SIZE, FPS

# --- Model Architecture (Must match train_agent.py) ---
class DQN(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(DQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )
    def forward(self, x):
        return self.net(x)

def get_observation(game):
    # The exact same normalization as in pong_env.py
    return np.array([
        (game.ai.y / H) * 2 - 1,
        (game.ball.x / W) * 2 - 1,
        (game.ball.y / H) * 2 - 1,
        # For the live game, we estimate velocity by tracking frames 
        # or we add velocity to the Game state. 
        # Let's assume we have access to ball.vx/vy from logic.py
        game.ball.vx / 14.0,
        game.ball.vy / 14.0,
    ], dtype=np.float32)

def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Pong: You vs Hermes RL")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier New", 64, bold=True)
    small_font = pygame.font.SysFont("Courier New", 14)

    # Game and AI setup
    game = Game()
    game.paused = False
    
    state_dim = 5
    action_dim = 3
    model = DQN(state_dim, action_dim)
    try:
        model.load_state_dict(torch.load("hermes_brain.pth"))
        model.eval()
        print("Elite brain loaded.")
    except FileNotFoundError:
        print("No brain found! Hermes will be clumsy until you run train_agent.py")

    running = True
    while running:
        # 1. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game.winner: game.reset()
                    game.paused = not game.paused
                if event.key == pygame.K_r:
                    game.reset()

        if not game.paused and not game.winner:
            # 2. Player Input
            keys = pygame.key.get_pressed()
            dy = 0
            if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -7
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = 7
            game.player.y += dy
            game.player.clamp()

            # 3. AI Agent Logic (The RL Backend part)
            obs = get_observation(game)
            obs_t = torch.FloatTensor(obs).unsqueeze(0)
            with torch.no_grad():
                q_values = model(obs_t)
            action = torch.argmax(q_values).item()
            
            ai_dy = 0
            if action == 1: ai_dy = -6.0
            if action == 2: ai_dy = 6.0
            game.ai.y += ai_dy
            game.ai.clamp()

            # 4. Game Tick
            # We bypass the internal _move_ai() by setting ai_client to something
            game.ai_client = "pygame_agent" 
            game.tick()
            game.ai_client = None

        # 5. Rendering
        screen.fill((10, 10, 10)) # Dark background

        # Center line
        pygame.draw.line(screen, (34, 34, 34), (W//2, 0), (W//2, H), 2)

        # Scores
        p_score_txt = font.render(str(game.player.score), True, (51, 51, 51))
        ai_score_txt = font.render(str(game.ai.score), True, (51, 51, 51))
        screen.blit(p_score_txt, (W//2 - 100, 20))
        screen.blit(ai_score_txt, (W//2 + 100, 20))

        # Paddles
        pygame.draw.rect(screen, (238, 238, 238), 
                         (40 - PADDLE_W//2, game.player.y - PADDLE_H//2, PADDLE_W, PADDLE_H), border_radius=4)
        pygame.draw.rect(screen, (68, 170, 255), 
                         (W-40 - PADDLE_W//2, game.ai.y - PADDLE_H//2, PADDLE_W, PADDLE_H), border_radius=4)

        # Ball
        pygame.draw.circle(screen, (255, 255, 255), (int(game.ball.x), int(game.ball.y)), BALL_SIZE//2)

        # Overlays
        if game.winner:
            msg = "🎉 You Win!" if game.winner == "You" else "🤖 AI Wins!"
            txt = font.render(msg, True, (238, 238, 238))
            sub = small_font.render("Press SPACE to play again", True, (102, 102, 102))
            screen.blit(txt, (W//2 - txt.get_width()//2, H//2 - 30))
            screen.blit(sub, (W//2 - sub.get_width()//2, H//2 + 20))
        elif game.paused:
            txt = font.render("PONG vs HERMES", True, (238, 238, 238))
            sub = small_font.render("Press SPACE to start", True, (102, 102, 102))
            screen.blit(txt, (W//2 - txt.get_width()//2, H//2 - 30))
            screen.blit(sub, (W//2 - sub.get_width()//2, H//2 + 20))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
