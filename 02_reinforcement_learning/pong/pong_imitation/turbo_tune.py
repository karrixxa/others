import gymnasium as gym
import torch
import torch.nn as nn
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import os
import sys

# Ensure we can access the perception models
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import make_env

class PerceptionCNN(BaseFeaturesExtractor):
    def __init__(self, observation_space, features_dim=512):
        super().__init__(observation_space, features_dim)
        self.cnn = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
        )

    def forward(self, observations):
        return self.cnn(observations)

def turbo_tune_rl():
    # 1. Setup
    NUM_ENVS = 8
    ADDITIONAL_TIMESTEPS = 500_000 
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Turbo-Tuning Master on device: {device.upper()}")

    envs = DummyVecEnv([make_env() for _ in range(NUM_ENVS)])
    envs = VecMonitor(envs)

    policy_kwargs = dict(
        features_extractor_class=PerceptionCNN,
        features_extractor_kwargs=dict(features_dim=512),
        net_arch=dict(pi=[256], vf=[256]),
    )

    model = PPO(
        "CnnPolicy",
        env=envs,
        learning_rate=7e-6, # Lowered slightly for stability
        n_steps=128,
        batch_size=256,
        n_epochs=4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.1,
        ent_coef=0.03, # Boosted from 0.01 to encourage exploration
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=policy_kwargs,
        tensorboard_log="/home/cxiong/pong_imitation/logs/rl_turbo_tune/",
        verbose=1,
        device=device,
    )

    # 2. Load existing Master Weights
    print("Loading existing Master weights for turbo-tuning...")
    master_path = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
    if not os.path.exists(master_path):
        print(f"Error: Master model not found at {master_path}")
        return
    
    model.set_parameters(PPO.load(master_path).get_parameters())
    print("Weights loaded. Starting the push to Super-Master status!")

    try:
        model.learn(total_timesteps=ADDITIONAL_TIMESTEPS, progress_bar=True)
    except KeyboardInterrupt:
        print("\nTraining interrupted.")
    finally:
        model.save("/home/cxiong/pong_imitation/student_rl_super_master.zip")
        envs.close()
        print("Super-Master model saved to /home/cxiong/pong_imitation/student_rl_super_master.zip")

if __name__ == "__main__":
    turbo_tune_rl()
