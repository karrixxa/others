import gymnasium as gym
import numpy as np
import torch
import os
from PIL import Image
import ale_py

from models.model import PerceptionDQN
from models.agent import DQNAgent

# Force registration of ALE envs
ale_py.register_v5_envs()

def preprocess(frame):
    img = Image.fromarray(frame).convert('L')
    img = img.resize((84, 84), Image.BILINEAR)
    return np.array(img, dtype=np.float32) / 255.0

def get_perception_channels(current_frame, prev_frame, paddle_y):
    motion = np.clip(current_frame - prev_frame, 0, 1)
    paddle_channel = np.zeros_like(current_frame)
    py = int(np.clip(paddle_y, 0, 83))
    paddle_channel[max(0, py-2):min(84, py+3), 70:78] = 1.0
    return motion, paddle_channel

def get_paddle_y(frame, threshold=0.6):
    region = frame[:, 70:78]
    bright = np.where(region > threshold)
    if len(bright[0]) == 0:
        return 42.0
    return float(np.mean(bright[0]))

def play(weights_path=None):
    # Setup Environment
    env = gym.make("ALE/Pong-v5", render_mode="rgb_array") # Use rgb_array for internal recording if needed
    
    # Setup Agent
    agent = DQNAgent(state_dim=(6, 84, 84), action_size=6)
    
    if weights_path and os.path.exists(weights_path):
        print(f"Loading weights from {weights_path}...")
        agent.policy_net.load_state_dict(torch.load(weights_path, map_location='cpu'))
        agent.policy_net.eval()
    else:
        print("No weights provided or found. Playing with random/initial weights.")

    obs, _ = env.reset()
    prev_frame = preprocess(obs)
    state_stack = [prev_frame] * 4
    
    total_score = 0
    done = False
    episode_frames = 0
    
    print("\nAgent is playing... (Press Ctrl+C to stop)")
    print(f"{'Frame':<10} | {'Score':<10} | {'Action':<10}")
    print("-" * 35)

    try:
        while not done:
            current_frame = preprocess(obs)
            paddle_y = get_paddle_y(current_frame)
            motion, paddle_marker = get_perception_channels(current_frame, prev_frame, paddle_y)
            
            state_stack = state_stack[1:] + [current_frame]
            state = np.stack(state_stack + [motion, paddle_marker], axis=0)
            
            # Greedy action (no exploration)
            action = agent.select_action(state) 
            # Note: select_action uses epsilon. In eval mode, we should set epsilon to 0.
            agent.epsilon = 0 
            
            obs, reward, terminated, truncated, _ = env.step(action)
            
            if reward != 0:
                total_score += reward
                print(f"{episode_frames:<10} | {total_score:<10.1f} | {action:<10}")
            
            done = terminated or truncated
            prev_frame = current_frame
            episode_frames += 1
            
            if done:
                break

    except KeyboardInterrupt:
        pass
    finally:
        print("-" * 35)
        print(f"Final Score: {total_score}")
        print(f"Total Frames: {episode_frames}")
        env.close()

if __name__ == "__main__":
    import sys
    # Allow passing a specific checkpoint path via CLI
    path = sys.argv[1] if len(sys.argv) > 1 else "/home/cxiong/pong_dqn/weights/dqn_final.pth"
    play(path)
