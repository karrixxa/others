import pygame
from engine import GameEngine
from ai import HermesAI

def main():
    pygame.init()
    game = GameEngine()
    ai = HermesAI(difficulty="medium")
    
    running = True
    while running:
        dt = game.clock.tick(60) / 1000.0 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        game.handle_input(dt)
        game.update(dt, ai)
        game.draw()
    pygame.quit()

if __name__ == "__main__":
    main()
