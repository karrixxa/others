import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from sb3_contrib import QRDQN
import numpy as np
import os

def main():
    # 1. Instantiate PongNoFrameskip-v4
    print("Creating environment...")
    env = gym.make("PongNoFrameskip-v4", render_mode=None)
    
    # 2. Preprocessing: Crop, grayscale, downscale to (84, 84)
    env = AtariPreprocessing(env, scale_obs=False, grayscale_obs=True, frame_skip=1)
    
    # 3. FrameStack: (4, 84, 84)
    env = FrameStackObservation(env, stack_size=4)
    
    # 4. Load the expert model from HuggingFace
    print("Loading expert model from HuggingFace...")
    zip_path = load_from_hub("sb3/qrdqn-PongNoFrameskip-v4", "qrdqn-PongNoFrameskip-v4.zip")
    
    # Use a custom_objects map to bypass the ReplayBuffer conflict
    custom_objects = {
        "optimize_memory_usage": False,
        "handle_timeout_termination": False,
        "lr_schedule": lambda _: 0.0001,
        "exploration_schedule": lambda _: 0.1
    }
    
    try:
        # Use QRDQN instead of DQN because the model is a Quantile Regression DQN
        model = QRDQN.load(zip_path, custom_objects=custom_objects)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # Test a single step to verify pipeline
    obs, info = env.reset()
    print(f"Observation shape: {obs.shape}") # Expected: (4, 84, 84)
    
    action, _states = model.predict(obs, deterministic=True)
    print(f"Expert action predicted: {action}")
    
    next_obs, reward, terminated, truncated, info = env.step(action)
    print("Successfully stepped the environment.")

if __name__ == "__main__":
    main()
