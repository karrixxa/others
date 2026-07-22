import gymnasium as gym
import numpy as np
from PIL import Image
from collections import deque

def preprocess_frame(frame):
    # frame: (210, 160, 3) uint8
    img = Image.fromarray(frame).convert('L')           # grayscale
    img = img.resize((84, 84), Image.BILINEAR)          # resize
    arr = np.array(img, dtype=np.float32) / 255.0       # normalize [0,1]
    return arr  # shape: (84, 84)

def find_paddle_y(frame_84x84, threshold=0.85):
    region = frame_84x84[15:79, 70:78]
    bright = np.where(region > threshold)
    if len(bright[0]) == 0 or len(bright[0]) > 50:
        return None
    return float(np.mean(bright[0])) + 15.0

def build_paddle_channel(frame_84x84):
    paddle_channel = np.zeros((84, 84), dtype=np.float32)
    paddle_y = find_paddle_y(frame_84x84)
    if paddle_y is not None:
        py = int(np.clip(paddle_y, 0, 83))
        paddle_channel[max(0, py-2):min(84, py+3), 70:78] = 1.0
    return paddle_channel

class PerceptionWrapper(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        self.frame_history = deque(maxlen=4)
        self.observation_space = gym.spaces.Box(
            low=0.0, high=1.0,
            shape=(6, 84, 84),
            dtype=np.float32
        )

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        processed = preprocess_frame(obs)
        for _ in range(4):
            self.frame_history.append(processed)
        return self.build_observation(), info

    def observation(self, obs):
        self.frame_history.append(preprocess_frame(obs))
        return self.build_observation()

    def build_observation(self):
        frames = list(self.frame_history)  # [t-3, t-2, t-1, t]
        current = frames[-1]
        prev    = frames[-2]

        motion  = np.clip(current - prev, 0, 1)
        paddle  = build_paddle_channel(current)

        stacked = np.stack([
            frames[0],   # channel 0: t-3
            frames[1],   # channel 1: t-2
            frames[2],   # channel 2: t-1
            frames[3],   # channel 3: t (current)
            motion,      # channel 4: motion map
            paddle,      # channel 5: paddle marker
        ], axis=0)       # shape: (6, 84, 84)

        return stacked.astype(np.float32)

class RewardWrapper(gym.RewardWrapper):
    def reward(self, reward):
        if reward == 0:
            return 0.01    # survival reward
        return reward      # +1.0 for scoring, -1.0 for conceding

def make_env():
    def _init():
        import ale_py
        ale_py.register_v5_envs()
        env = gym.make("ALE/Pong-v5", render_mode=None)
        env = PerceptionWrapper(env)
        env = RewardWrapper(env)
        return env
    return _init
