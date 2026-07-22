
import gymnasium as gym
import numpy as np
import torch
from stable_baselines3 import PPO
import sys
import os
import ale_py
import pandas as pd
import matplotlib.pyplot as plt
import time

sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

STUDENT_MODEL = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
MASTER_MODEL = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
LOG_FILE = "/home/cxiong/pong_imitation/benchmark_progress.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    print(msg)

def evaluate_agent(model_path, agent_name, num_episodes=100):
    log(f"\n>>> [INIT] Loading {agent_name} on CPU...")
    try:
        env = gym.make("ALE/Pong-v5", render_mode=None)
        env = PerceptionWrapper(env)
        model = PPO.load(model_path, device="cpu")
        log(f">>> [SUCCESS] {agent_name} loaded.")
    except Exception as e:
        log(f">>> [ERROR] Failed to load {agent_name}: {e}")
        return None

    scores = []
    wins = 0
    rally_lengths = []
    
    log(f">>> [START] Running {num_episodes} games for {agent_name}...")
    start_time = time.time()
    
    for ep in range(1, num_episodes + 1):
        obs, info = env.reset()
        done = False
        total_reward = 0
        rally_count = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(int(action))
            total_reward += reward
            if reward > 0: rally_count += 1
            done = terminated or truncated
            
        scores.append(total_reward)
        if total_reward > 0: wins += 1
        rally_lengths.append(rally_count)
        
        log(f"Game {ep}/{num_episodes} | Score: {total_reward} | Avg: {np.mean(scores):.2f}")

    env.close()
    return {
        "mean_score": np.mean(scores),
        "win_rate": (wins / num_episodes) * 100,
        "avg_rally": np.mean(rally_lengths),
        "scores": scores
    }

# Clear previous log
with open(LOG_FILE, "w") as f:
    f.write("--- Benchmark Started ---\n")

results = {}
results["CNN_Student"] = evaluate_agent(STUDENT_MODEL, "CNN_Student")
results["RL_Master"] = evaluate_agent(MASTER_MODEL, "RL_Master")

if results["CNN_Student"] and results["RL_Master"]:
    df = pd.DataFrame({
        "Agent": results.keys(),
        "Mean Score": [v["mean_score"] for v in results.values()],
        "Win Rate (%)": [v["win_rate"] for v in results.values()],
        "Avg Rally": [v["avg_rally"] for v in results.values()]
    })
    df.to_csv("/home/cxiong/pong_imitation/benchmark_results_cpu.csv", index=False)
    log(">>> [DONE] Results saved to benchmark_results_cpu.csv")
