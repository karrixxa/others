import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from sb3_contrib import QRDQN
import numpy as np
import os
from tqdm import tqdm

def main():
    # --- Configuration ---
    TARGET_FRAMES = 100000
    SAVE_PATH = "/home/cxiong/pong_imitation/expert_data.npz"
    
    # 1. Setup Environment
    print("Creating environment...")
    env = gym.make("PongNoFrameskip-v4", render_mode=None)
    env = AtariPreprocessing(env, scale_obs=False, grayscale_obs=True, frame_skip=1)
    env = FrameStackObservation(env, stack_size=4)
    
    # 2. Load Expert
    print("Loading expert model...")
    zip_path = load_from_hub("sb3/qrdqn-PongNoFrameskip-v4", "qrdqn-PongNoFrameskip-v4.zip")
    custom_objects = {
        "optimize_memory_usage": False,
        "handle_timeout_termination": False,
        "lr_schedule": lambda _: 0.0001,
        "exploration_schedule": lambda _: 0.1
    }
    model = QRDQN.load(zip_path, custom_objects=custom_objects)
    
    # 3. Data Collection
    observations = []
    actions = []
    
    obs, info = env.reset()
    frames_collected = 0
    
    print(f"Collecting {TARGET_FRAMES} frames of expert data...")
    pbar = tqdm(total=TARGET_FRAMES)
    
    while frames_collected < TARGET_FRAMES:
        # Predict deterministic action
        action, _ = model.predict(obs, deterministic=True)
        
        # Store data
        observations.append(obs)
        actions.append(action)
        
        # Step environment
        obs, reward, terminated, truncated, info = env.step(action)
        
        frames_collected += 1
        pbar.update(1)
        
        if terminated or truncated:
            obs, info = env.reset()
            
    pbar.close()
    
    # 4. Export to .npz
    print(f"Converting to numpy arrays and saving to {SAVE_PATH}...")
    X = np.array(observations, dtype=np.uint8)
    Y = np.array(actions, dtype=np.int64)
    
    np.savez_compressed(SAVE_PATH, x=X, y=Y)
    print(f"Saved successfully! X shape: {X.shape}, Y shape: {Y.shape}")

if __name__ == "__main__":
    main()
