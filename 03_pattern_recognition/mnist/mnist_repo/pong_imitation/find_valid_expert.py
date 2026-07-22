import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from stable_baselines3 import PPO, DQN
import numpy as np

def make_expert_env():
    env = gym.make("PongNoFrameskip-v4", render_mode=None)
    env = AtariPreprocessing(env, scale_obs=False, grayscale_obs=True, frame_skip=1)
    env = FrameStackObservation(env, stack_size=4)
    return env

def evaluate_expert(model, env, n_episodes=3):
    print(f"Evaluating model: {type(model).__name__}...")
    total_rewards = []
    for i in range(n_episodes):
        obs, info = env.reset()
        done = False
        episode_reward = 0
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated
        total_rewards.append(episode_reward)
        print(f"Episode {i+1}: Score = {episode_reward}")
    
    mean_score = np.mean(total_rewards)
    print(f"Mean Score: {mean_score}")
    return mean_score

def main():
    env = make_expert_env()
    
    # Option 1: araffin/ppo-PongNoFrameskip-v4
    print("\n--- Trying Option 1: araffin/ppo-PongNoFrameskip-v4 ---")
    try:
        ckpt1 = load_from_hub(repo_id="araffin/ppo-PongNoFrameskip-v4", filename="ppo-PongNoFrameskip-v4.zip")
        model1 = PPO.load(ckpt1)
        if evaluate_expert(model1, env) > 0:
            print("SUCCESS: Option 1 is a valid expert.")
            return
    except Exception as e:
        print(f"Option 1 failed: {e}")

    # Option 2: sb3/dqn-PongNoFrameskip-v4
    print("\n--- Trying Option 2: sb3/dqn-PongNoFrameskip-v4 ---")
    try:
        ckpt2 = load_from_hub(repo_id="sb3/dqn-PongNoFrameskip-v4", filename="dqn-PongNoFrameskip-v4.zip")
        model2 = DQN.load(ckpt2)
        if evaluate_expert(model2, env) > 0:
            print("SUCCESS: Option 2 is a valid expert.")
            return
    except Exception as e:
        print(f"Option 2 failed: {e}")

    print("\nAll provided expert options failed to score positively.")

if __name__ == "__main__":
    main()
