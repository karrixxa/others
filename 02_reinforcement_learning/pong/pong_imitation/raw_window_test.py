
import gymnasium as gym
import ale_py
import torch
from stable_baselines3 import PPO
import sys
import os

# Project paths
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

def main():
    # 1. Load Model
    MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
    print(f"Loading model: {MODEL_PATH}")
    model = PPO.load(MODEL_PATH)

    # 2. Setup Environment with render_mode="human"
    # This is the key: "human" mode uses the emulator's native window, NOT OpenCV
    print("Initializing environment in HUMAN mode...")
    ale_py.register_v5_envs()
    env = gym.make("ALE/Pong-v5", render_mode="human")
    
    # We still need the PerceptionWrapper because the model expects 6 channels
    env = PerceptionWrapper(env)
    
    obs, info = env.reset()
    print("\n>>> NATIVE WINDOW STARTING <<<")
    print("If a window appears, you can close it by closing the window or pressing Ctrl+C in terminal.")
    
    try:
        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(int(action))
            
            # In human mode, env.step() automatically handles the rendering
            
            if terminated or truncated:
                obs, info = env.reset()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        env.close()

if __name__ == "__main__":
    main()
