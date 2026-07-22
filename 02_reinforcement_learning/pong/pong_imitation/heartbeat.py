
import gymnasium as gym
import torch
from stable_baselines3 import PPO
import sys
import os
import ale_py

sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"

def check_heartbeat():
    print(">>> [HEARTBEAT] Starting test...")
    try:
        print(">>> Checking Env...")
        env = gym.make("ALE/Pong-v5", render_mode=None)
        env = PerceptionWrapper(env)
        print(">>> Env OK.")
        
        print(">>> Checking Model...")
        model = PPO.load(MODEL_PATH, device="cpu")
        print(">>> Model OK.")
        
        print(">>> Testing One Step...")
        obs, info = env.reset()
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(int(action))
        print(f">>> Step OK. Reward: {reward}")
        
        print("\n>>> [RESULT] SYSTEM IS ALIVE! The benchmark is just slow.")
        env.close()
    except Exception as e:
        print(f"\n>>> [RESULT] SYSTEM DEAD. Error: {e}")

if __name__ == "__main__":
    check_heartbeat()
