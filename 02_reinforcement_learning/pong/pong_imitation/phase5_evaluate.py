import gymnasium as gym
import torch
import numpy as np
import sys
import os
import ale_py

# Register ALE environments explicitly to avoid NamespaceNotFound errors
ale_py.register_v5_envs()

# Import the student architecture and wrapper from previous phases

# Import the student architecture and wrapper from previous phases
sys.path.append('/home/cxiong/pong_imitation')
from phase4_train import StudentCNN

# Import the PerceptionWrapper from the PPO project
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

def evaluate():
    # 1. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluating on device: {device}")

    # 2. Load the trained student model
    model = StudentCNN().to(device)
    model_path = "/home/cxiong/pong_imitation/student_cnn.pth"
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return
    
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print("Student model loaded successfully.")

    # 3. Setup Environment with HUMAN render mode
    print("Initializing environment with render_mode='human'...")
    # Use Pong-v4 for maximum stability across different ALE versions
    env = gym.make("Pong-v4", render_mode="human")
    env = PerceptionWrapper(env)

    obs, info = env.reset()
    done = False
    total_reward = 0
    episode_length = 0

    print("\n>>> LIVE PLAY STARTING <<<")
    print("You should see a window pop up now. Press Ctrl+C in the terminal to stop.")

    try:
        while not done:
            # Debug: Check if observation is changing (detecting "frozen" game)
            if episode_length > 0:
                diff = np.abs(obs - prev_obs).sum()
                if diff == 0 and episode_length % 100 == 0:
                    print(f"Warning: Observation is frozen at frame {episode_length}!")

            # Convert observation to tensor
            obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(device)
            prev_obs = obs.copy()

            with torch.no_grad():
                outputs = model(obs_tensor)
                action = torch.argmax(outputs, dim=1).item()

            # Step the environment
            obs, reward, terminated, truncated, info = env.step(action)
            
            total_reward += reward
            episode_length += 1
            done = terminated or truncated

        print(f"\nEpisode Finished!")
        print(f"Total Reward: {total_reward}")
        print(f"Episode Length: {episode_length}")

    except KeyboardInterrupt:
        print("\nLive play interrupted by user.")
    finally:
        env.close()

if __name__ == "__main__":
    evaluate()
