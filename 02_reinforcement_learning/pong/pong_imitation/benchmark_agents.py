
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

# Add path for PerceptionWrapper
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

# Model Paths
STUDENT_MODEL = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
MASTER_MODEL = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"

def evaluate_agent(model_path, agent_name, num_episodes=100):
    print(f"\n>>> [INIT] Loading {agent_name}...")
    
    try:
        # Create env ONLY for Pong to minimize overhead
        env = gym.make("ALE/Pong-v5", render_mode=None)
        env = PerceptionWrapper(env)
        model = PPO.load(model_path)
        print(f">>> [SUCCESS] {agent_name} loaded and environment ready.")
    except Exception as e:
        print(f">>> [ERROR] Failed to load {agent_name}: {e}")
        return None

    scores = []
    wins = 0
    rally_lengths = []
    
    print(f">>> [START] Running {num_episodes} games for {agent_name}...")
    
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
        if total_reward > 0:
            wins += 1
        rally_lengths.append(rally_count)
        
        # High-frequency progress updates
        if ep % 5 == 0:
            elapsed = time.time() - start_time
            avg_score = np.mean(scores)
            print(f"Progress: {ep}/{num_episodes} | Avg Score: {avg_score:.2f} | Elapsed: {elapsed:.1f}s")

    env.close()
    print(f">>> [FINISHED] {agent_name} evaluation complete.")
    return {
        "mean_score": np.mean(scores),
        "win_rate": (wins / num_episodes) * 100,
        "avg_rally": np.mean(rally_lengths),
        "scores": scores
    }

# Run Benchmarks
results = {}
results["CNN_Student"] = evaluate_agent(STUDENT_MODEL, "CNN_Student")
results["RL_Master"] = evaluate_agent(MASTER_MODEL, "RL_Master")

if results["CNN_Student"] and results["RL_Master"]:
    print("\n>>> [FINALIZING] Saving results and generating plots...")
    df = pd.DataFrame({
        "Agent": results.keys(),
        "Mean Score": [v["mean_score"] for v in results.values()],
        "Win Rate (%)": [v["win_rate"] for v in results.values()],
        "Avg Rally": [v["avg_rally"] for v in results.values()]
    })
    df.to_csv("/home/cxiong/pong_imitation/benchmark_results.csv", index=False)

    plt.figure(figsize=(10, 6))
    plt.bar(df["Agent"], df["Win Rate (%)"], color=['skyblue', 'royalblue'])
    plt.ylabel("Win Rate (%)")
    plt.title("Win Rate Comparison: CNN Student vs RL Master")
    plt.ylim(0, 100)
    plt.savefig("/home/cxiong/pong_imitation/benchmark_comparison.png")
    print(">>> [DONE] benchmark_results.csv and benchmark_comparison.png created.")
else:
    print("\n>>> [CRITICAL] Benchmark failed to complete.")
