
import gymnasium as gym
import torch
from stable_baselines3 import PPO
import sys
import os
import ale_py
import time

# Add path for PerceptionWrapper
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"

def test_single_game():
    print(">>> [STEP 1] Initializing Environment...")
    try:
        env = gym.make("ALE/Pong-v5", render_mode=None)
        env = PerceptionWrapper(env)
        print(">>> [SUCCESS] Env ready.")
    except Exception as e:
        print(f">>> [ERROR] Env failed: {e}")
        return

    print(">>> [STEP 2] Loading Model...")
    try:
        model = PPO.load(MODEL_PATH)
        print(">>> [SUCCESS] Model loaded.")
    except Exception as e:
        print(f">>> [ERROR] Model failed: {e}")
        return

    print(">>> [STEP 3] Running 1 Single Game...")
    obs, info = env.reset()
    done = False
    total_reward = 0
    frames = 0
    
    start_time = time.time()
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(int(action))
        total_reward += reward
        done = terminated or truncated
        frames += 1
        if frames > 10000: # Safety break
            print("Game taking too long, forcing end.")
            break
            
    end_time = time.time()
    print(f"\n>>> [RESULT] Game Finished!")
    print(f"Final Score: {total_reward}")
    print(f"Total Frames: {frames}")
    print(f"Time Taken: {end_time - start_time:.2f}s")
    env.close()

if __name__ == "__main__":
    test_single_game()
