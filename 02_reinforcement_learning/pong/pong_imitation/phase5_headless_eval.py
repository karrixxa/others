import gymnasium as gym
import numpy as np
from stable_baselines3 import PPO
import ale_py
import sys
import os

# The PerceptionWrapper lives in the PPO project folder
sys.path.append('/home/cxiong/pong_ppo')
try:
    from models.perception import PerceptionWrapper
except ImportError:
    print("Error: Could not find PerceptionWrapper in /home/cxiong/pong_ppo/models/perception.py")
    sys.exit(1)

# Register ALE environments
ale_py.register_v5_envs()

def evaluate_model(model_path, episodes=100):
    # Use the same environment as training
    env = gym.make("ALE/Pong-v5", render_mode="rgb_array")
    env = PerceptionWrapper(env)
    
    model = PPO.load(model_path)
    
    total_rewards = []
    wins = 0
    
    print(f"Evaluating model: {model_path}")
    print(f"Playing {episodes} episodes... please wait.")
    
    for i in range(episodes):
        obs, info = env.reset()
        done = False
        truncated = False
        episode_reward = 0
        
        while not (done or truncated):
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            episode_reward += reward
            
        total_rewards.append(episode_reward)
        if episode_reward > 0:
            wins += 1
            
        if (i + 1) % 10 == 0:
            print(f"Episode {i+1}/{episodes} | Current Mean Reward: {np.mean(total_rewards):.2f}")

    mean_reward = np.mean(total_rewards)
    win_rate = (wins / episodes) * 100
    
    print("\n" + "="*30)
    print("   FINAL EVALUATION REPORT")
    print("="*30)
    print(f"Total Episodes: {episodes}")
    print(f"Mean Reward:    {mean_reward:.2f}")
    print(f"Win Rate:       {win_rate:.1f}%")
    print(f"Max Score:      {max(total_rewards)}")
    print(f"Min Score:      {min(total_rewards)}")
    print("="*30)

if __name__ == "__main__":
    MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
    evaluate_model(MODEL_PATH)
