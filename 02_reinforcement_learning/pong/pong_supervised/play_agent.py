import gymnasium as gym
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

def preprocess(frame):
    img = Image.fromarray(frame).convert('L')
    img = img.resize((84, 84), Image.BILINEAR)
    return np.array(img, dtype=np.float32) / 255.0

def find_paddle_y(frame):
    # Right paddle: x roughly 70-78
    region = frame[:, 70:78]
    bright = np.where(region > 0.6)
    if len(bright[0]) == 0:
        return None
    return float(np.mean(bright[0]))

class BallTracker(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(2, 32, kernel_size=8, stride=4),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 1),
            nn.Sigmoid(),
        )
    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x).squeeze(1)

DEVICE = torch.device("cpu")

def get_action(predicted_ball_y, paddle_y, dead_zone=5):
    if predicted_ball_y is None or paddle_y is None:
        return 0  # NOOP
    if predicted_ball_y < paddle_y - dead_zone:
        return 2  # UP (Right in v5)
    elif predicted_ball_y > paddle_y + dead_zone:
        return 3  # DOWN (Left in v5)
    return 0      # NOOP

def play(n_episodes=10, render=True):
    render_mode = "human" if render else None
    env = gym.make("ALE/Pong-v5", render_mode=render_mode)
    
    model = BallTracker().to(DEVICE)
    model.load_state_dict(torch.load("/home/cxiong/pong_supervised/ball_tracker.pth", map_location=DEVICE))
    model.eval()
    
    results = []
    for ep in range(n_episodes):
        obs, _ = env.reset()
        env.step(1)   # serve
        prev_frame = preprocess(obs)
        score = 0
        done = False
        
        while not done:
            current_frame = preprocess(obs)
            motion = np.clip(current_frame - prev_frame, 0, 1)
            stacked = np.stack([current_frame, motion], axis=0)
            tensor = torch.tensor(stacked).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                pred_y_norm = model(tensor).item()
            predicted_ball_y = pred_y_norm * 84.0
            paddle_y = find_paddle_y(current_frame)
            
            action = get_action(predicted_ball_y, paddle_y)
            obs, reward, terminated, truncated, _ = env.step(action)
            score += reward
            done = terminated or truncated
            prev_frame = current_frame
        
        results.append(score)
        print(f"Episode {ep+1}: score = {score:+.0f}")
    
    env.close()
    print(f"\nMean score: {np.mean(results):+.2f}")
    print(f"Win rate: {sum(r > 0 for r in results)/len(results)*100:.0f}%")
    return results

if __name__ == "__main__":
    play(n_episodes=10, render=True)
