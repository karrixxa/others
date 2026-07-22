import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms.functional as TF
import os
import time
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

# ── Configuration ──────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
MODEL_PATH = "/home/cxiong/pong_supervised/pong_cnn_classifier.pth"
ENV_NAME = "ALE/Pong-v5"

def preprocess(frame):
    # Frame is (210, 160, 3)
    t = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
    t = TF.rgb_to_grayscale(t)
    t = TF.resize(t, [84, 84])
    return t.squeeze(0).numpy()

class PongClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(2, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 512), nn.ReLU(),
            nn.Linear(512, 3),
        )
        
    def forward(self, x):
        return self.fc(self.conv(x))

def main():
    # 1. Setup Environment with HUMAN render mode for X11
    try:
        env = gym.make(ENV_NAME, render_mode="human")
        print(f"Successfully created {ENV_NAME} in human mode.")
    except Exception as e:
        print(f"Error creating environment: {e}")
        print("Tip: Ensure you connected with 'ssh -X' or 'ssh -Y' and have an X server running.")
        return

    # 2. Load the Model
    model = PongClassifier().to(DEVICE)
    if os.path.exists(MODEL_PATH):
        model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        print("Trained model loaded!")
    else:
        print(f"Model not found at {MODEL_PATH}. Please wait for training to finish.")
        return
    
    model.eval()
    
    # 3. Play Loop
    obs, info = env.reset()
    prev_frame = preprocess(obs)
    done = False
    
    print("Launching window... (Press Ctrl+C in terminal to stop)")
    
    try:
        while not done:
            current_frame = preprocess(obs)
            
            # Compute motion map for the 2-channel input
            motion = np.clip(current_frame.astype(np.float32) - prev_frame.astype(np.float32), 0, 1.0)
            stacked = np.stack([current_frame.astype(np.float32), motion], axis=0)
            tensor = torch.tensor(stacked).unsqueeze(0).to(DEVICE)
            
            with torch.no_grad():
                output = model(tensor)
                action_idx = torch.argmax(output).item()
            
            # Map CNN classes to Gymnasium actions
            # 0: UP, 1: DOWN, 2: STAY
            action_map = {0: 2, 1: 3, 2: 1}
            action = action_map.get(action_idx, 1)
            
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Slow down the game so it's watchable on X11
            time.sleep(0.02) 
            
            prev_frame = current_frame
            
    except KeyboardInterrupt:
        print("\nStopping agent...")
    finally:
        env.close()
        print("Environment closed.")

if __name__ == "__main__":
    main()
