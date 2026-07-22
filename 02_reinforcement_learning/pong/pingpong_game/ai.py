import pygame

class HermesAI:
    def __init__(self, difficulty="medium"):
        self.difficulty = difficulty
        self.reaction_speed = {
            "easy": 400,
            "medium": 600,
            "hard": 900
        }.get(difficulty, 600)
        
        self.error_margin = {
            "easy": 50,
            "medium": 20,
            "hard": 5
        }.get(difficulty, 20)

    def update(self, paddle, ball, dt):
        center_y = paddle.rect.centery
        target_y = ball.pos.y
        
        if ball.vel.x > 0:
            if abs(center_y - target_y) > self.error_margin:
                if center_y < target_y:
                    paddle.move(self.reaction_speed, dt)
                elif center_y > target_y:
                    paddle.move(-self.reaction_speed, dt)
        else:
            target_center = 360 
            if abs(center_y - target_center) > 5:
                if center_y < target_center:
                    paddle.move(self.reaction_speed * 0.5, dt)
                elif center_y > target_center:
                    paddle.move(-self.reaction_speed * 0.5, dt)
