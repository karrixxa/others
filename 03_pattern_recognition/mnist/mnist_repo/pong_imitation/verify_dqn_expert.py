import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from stable_baselines3 import DQN
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
    
    print("--- Trying sb3/dqn-PongNoFrameskip-v4 with custom_objects fix ---")
    try:
        checkpoint = load_from_hub(
            repo_id="sb3/dqn-PongNoFrameskip-v4", 
            filename="dqn-PongNoFrameskip-v4.zip"
        )
        
        expert = DQN.load(
            checkpoint,
            custom_objects={
                "optimize_memory_usage": False,
                "handle_timeout_termination": False,
            }
        )
        
        score = evaluate_expert(expert, env)
        
        if score <= 0:
            print("\nExpert still scoring poorly. Checking observation space mismatch...")
            print(f"Env observation space: {env.observation_space}")
            print(f"Model observation space: {expert.observation_space}")
            print(f"Model policy observation space: {expert.policy.observation_space}")
            
    except Exception as e:
        print(f"DQN load failed: {e}")

if __name__ == "__main__":
    main()
