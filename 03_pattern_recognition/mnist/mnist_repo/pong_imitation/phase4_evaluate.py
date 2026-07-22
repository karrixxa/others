import torch
import torch.nn as nn
import gymnasium as gym
import numpy as np
import os
from tqdm import tqdm

# Import the perception wrapper from the PPO project to ensure matching observations
import sys
sys.path.append("/home/cxiong/pong_ppo")
from models.perception import PerceptionWrapper

# --- Configuration ---
MODEL_PATH = "/home/cxiong/pong_imitation/student_cnn.pth"
ENV_NAME = "ALE/Pong-v5"
NUM_EPISODES = 10
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class ImitationCNN(nn.Module):
    def __init__(self):
        super(ImitationCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten(),
        )
        self.classifier = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 6)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def main():
    print(f"Using device: {DEVICE}")
    
    # 1. Load Model
    if not os.path.exists(MODEL_PATH):
        print(f"Error: Model file {MODEL_PATH} not found.")
        return
    
    model = ImitationCNN().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval()
    print("Student model loaded successfully.")

    # 2. Setup Environment
    # We use the exact same wrapper the model was trained on
    env = gym.make(ENV_NAME)
    env = PerceptionWrapper(env)
    
    scores = []
    
    print(f"Evaluating Student over {NUM_EPISODES} episodes...")
    
    for episode in range(NUM_EPISODES):
        obs = env.reset()
        done = False
        total_reward = 0
        
        # Observation is (6, 84, 84)
        # Convert to tensor and add batch dimension: (1, 6, 84, 84)
        obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(DEVICE)
        
        while not done:
            with torch.no_grad():
                output = model(obs_tensor)
                action = output.argmax(1).item()
            
            obs, reward, done, info = env.step(action)
            total_reward += reward
            
            obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(DEVICE)
            
        scores.append(total_reward)
        print(f"Episode {episode+1}/{NUM_EPISODES} | Score: {total_reward}")

    env.close()
    
    mean_score = np.mean(scores)
    print("\n" + "="*30)
    print(f"FINAL EVALUATION RESULTS")
    print(f"Mean Score over {NUM_EPISODES} games: {mean_score:.2f}")
    print(f"Max Score: {max(scores)}")
    print(f"Min Score: {min(scores)}")
    print("="*30)
    
    if mean_score > 0:
        print("RESULT: The Student is WINNING! Imitation Successful. 🏆")
    else:
        print("RESULT: The Student is losing. Imitation failed to translate to gameplay. ❌")

if __name__ == "__main__":
    main()
