
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from logic import Game, W, H, PADDLE_H, BALL_SIZE

class PongEnv(gym.Env):
    """
    A Gymnasium wrapper for the custom Pong logic.
    State: [ai_paddle_y, ball_x, ball_y, ball_vx, ball_vy]
    Actions: 0: Stay, 1: Up, 2: Down
    """
    def __init__(self):
        super(PongEnv, self).__init__()
        
        # Action space: 0=Stay, 1=Up, 2=Down
        self.action_space = spaces.Discrete(3)
        
        # Observation space: 
        # Paddle Y, Ball X, Ball Y, Ball VX, Ball VY
        # Using Box for continuous values normalized to [0, 1] or [-1, 1]
        self.observation_space = spaces.Box(
            low=-1, high=1, shape=(5,), dtype=np.float32
        )
        
        self.game = Game()
        self.game.paused = False
        self.game.winner = None

    def _get_obs(self):
        # Normalize values to help the RL agent learn faster
        obs = np.array([
            (self.game.ai.y / H) * 2 - 1,
            (self.game.ball.x / W) * 2 - 1,
            (self.game.ball.y / H) * 2 - 1,
            self.game.ball.vx / 14.0, # Normalized by MAX_SPEED
            self.game.ball.vy / 14.0,
        ], dtype=np.float32)
        return obs

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game.reset()
        self.game.paused = False
        return self._get_obs(), {}

    def step(self, action):
        # Map discrete action to movement
        # In logic.py, ai.y is modified by a 'dy'
        # We'll use a fixed speed for the RL agent to match our difficulty settings
        dy = 0
        if action == 1: dy = -6.0 # Up
        if action == 2: dy = 6.0  # Down
        
        # Apply move to the AI paddle
        self.game.ai.y += dy
        self.game.ai.clamp()
        
        # Step the game forward
        self.game.tick()
        
        # Reward logic:
        # +1 for hitting the ball
        # +1 for winning the point
        # -1 for losing the point
        reward = 0.0
        
        # Check if AI just hit the ball (rally increased)
        # Since we don't have a 'just_hit' flag, we check the ball's x direction
        # If ball was moving right and now moves left, it's a hit.
        # This is slightly imperfect but works for a basic RL wrap.
        # We'll use the rally count as a proxy.
        
        # Simplest reward: keep ball in play, penalize losing
        if self.game.ball.x < 0: # AI scores
            reward = 1.0
        elif self.game.ball.x > W: # Player scores
            reward = -1.0
        
        # Bonus for hitting the ball
        # We can use the rally value to provide a small positive reward
        # for every tick the rally stays alive (or just check the hit)
        
        terminated = False
        if self.game.winner:
            terminated = True
            
        truncated = False
        
        return self._get_obs(), reward, terminated, truncated, {}

    def render(self):
        # This env is headless; rendering happens via the server.py WebSocket
        pass
