import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from sb3_contrib import QRDQN
import numpy as np

def evaluate_expert(model, env, n_episodes=3):
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
    print(f"Mean Score over {n_episodes} episodes: {mean_score}")
    return mean_score

def main():
    env = gym.make("PongNoFrameskip-v4", render_mode=None)
    env = AtariPreprocessing(env, scale_obs=False, grayscale_obs=True, frame_skip=1)
    env = FrameStackObservation(env, stack_size=4)
    
    zip_path = load_from_hub("sb3/qrdqn-PongNoFrameskip-v4", "qrdqn-PongNoFrameskip-v4.zip")
    custom_objects = {
        "optimize_memory_usage": False,
        "handle_timeout_termination": False,
        "lr_schedule": lambda _: 0.0001,
        "exploration_schedule": lambda _: 0.1
    }
    model = QRDQN.load(zip_path, custom_objects=custom_objects)
    
    print("Verifying expert performance...")
    evaluate_expert(model, env)

if __name__ == "__main__":
    main()
