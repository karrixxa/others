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

def train_rl_finetune():
    # 1. Setup
    NUM_ENVS = 8
    TOTAL_TIMESTEPS = 500_000 # Starting with a smaller run to see progress
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Fine-tuning on device: {device.upper()}")

    # Setup Environment
    envs = DummyVecEnv([make_env() for _ in range(NUM_ENVS)])
    envs = VecMonitor(envs)

    policy_kwargs = dict(
        features_extractor_class=PerceptionCNN,
        features_extractor_kwargs=dict(features_dim=512),
        net_arch=dict(pi=[256], vf=[256]),
    )

    # 2. Initialize PPO
    model = PPO(
        "CnnPolicy",
        env=envs,
        learning_rate=1e-5, # Lower LR for fine-tuning to avoid destroying the imitation weights
        n_steps=128,
        batch_size=256,
        n_epochs=4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.1,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=policy_kwargs,
        tensorboard_log="/home/cxiong/pong_imitation/logs/rl_finetune/",
        verbose=1,
        device=device,
    )

    # 3. Load Student Weights into the PPO Policy
    # The student model is just the CNN part of the policy
    print("Loading Student CNN weights into PPO policy...")
    student_weights = torch.load("/home/cxiong/pong_imitation/student_rl_start.pth", map_location=device)
    
    # The PPO model has a policy network; we map the student weights to the features_extractor
    # PPO's features_extractor is located at model.policy.features_extractor
    with torch.no_grad():
        # We map StudentCNN weights to PerceptionCNN (they are identical in architecture)
        # We need to handle the naming difference between StudentCNN.features and PerceptionCNN.cnn
        state_dict = model.policy.features_extractor.state_dict()
        student_state = student_weights
        
        # Map 'features.0.weight' -> 'cnn.0.weight' etc.
        new_state_dict = {}
        for k, v in student_state.items():
            # StudentCNN has .features and .classifier. We only want the .features part for the extractor
            if k.startswith('features.'):
                new_key = k.replace('features.', 'cnn.')
                new_state_dict[new_key] = v
        
        model.policy.features_extractor.load_state_dict(new_state_dict, strict=False)
    
    print("Student weights successfully injected. The agent now starts as a Pro!")

    # 4. RL Training
    try:
        model.learn(total_timesteps=TOTAL_TIMESTEPS, progress_bar=True)
    except KeyboardInterrupt:
        print("\nTraining interrupted.")
    finally:
        model.save("/home/cxiong/pong_imitation/student_rl_evolved.zip")
        envs.close()
        print("Evolved model saved to /home/cxiong/pong_imitation/student_rl_evolved.zip")

if __name__ == "__main__":
    train_rl_finetune()
