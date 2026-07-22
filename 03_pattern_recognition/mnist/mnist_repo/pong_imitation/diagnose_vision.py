import gymnasium as gym
import numpy as np
import os
from PIL import Image
import sys
import ale_py

# Register ALE environments explicitly to avoid NamespaceNotFound errors
ale_py.register_v5_envs()

# Setup paths for wrappers

# Setup paths for wrappers
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

def diagnose_vision():
    print("Initializing environment for vision diagnosis...")
    # Use non-human render mode just to collect frames
    # Use PongNoFrameskip-v4 as it's the most compatible ID
    env = gym.make("PongNoFrameskip-v4", render_mode="rgb_array")
    env = PerceptionWrapper(env)
    
    obs, info = env.reset()
    
    # Create a directory to save the vision channels
    save_dir = "/home/cxiong/pong_imitation/vision_debug"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Collecting 10 frames of perception data into {save_dir}...")
    
    for i in range(10):
        # Step the env with a random action to get movement
        obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
        
        # obs shape: (6, 84, 84)
        # Save each channel as an image
        for channel_idx in range(6):
            channel_data = obs[channel_idx]
            # Normalize to 0-255 for image saving
            img_data = (channel_data * 255).astype(np.uint8)
            img = Image.fromarray(img_data)
            
            channel_name = {
                0: "frame_t-3", 1: "frame_t-2", 2: "frame_t-1", 
                3: "frame_t", 4: "motion_map", 5: "paddle_marker"
            }[channel_idx]
            
            img.save(f"{save_dir}/frame_{i}_{channel_name}.png")
        
        if terminated or truncated:
            obs, info = env.reset()

    print("Diagnosis complete. Please check the images in /home/cxiong/pong_imitation/vision_debug")
    env.close()

if __name__ == "__main__":
    diagnose_vision()
