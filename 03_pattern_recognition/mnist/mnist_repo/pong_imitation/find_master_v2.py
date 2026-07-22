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
    
    # We will try a few high-probability candidates
    candidates = [
        # PPO from a known reliable source
        {"repo": "sb3/ppo-PongNoFrameskip-v4", "model_class": PPO, "file": "ppo-PongNoFrameskip-v4.zip"},
        # DQN from a known reliable source
        {"repo": "sb3/dqn-PongNoFrameskip-v4", "model_class": DQN, "file": "dqn-PongNoFrameskip-v4.zip"},
        # Another PPO variation
        {"repo": "araffin/ppo-PongNoFrameskip-v4", "model_class": PPO, "file": "ppo-PongNoFrameskip-v4.zip"},
    ]
    
    for cand in candidates:
        print(f"\n--- Testing Candidate: {cand['repo']} ---")
        try:
            checkpoint = load_from_hub(cand['repo'], cand['file'])
            
            # We use custom_objects to avoid the ReplayBuffer/OptimizedMemory error we saw earlier
            if cand['model_class'] == DQN:
                model = DQN.load(checkpoint, custom_objects={"optimize_memory_usage": False, "handle_timeout_termination": False})
            else:
                model = PPO.load(checkpoint)
                
            score = evaluate_expert(model, env)
            if score > 0:
                print(f"!!! SUCCESS !!! {cand['repo']} is a valid Master.")
                return
        except Exception as e:
            print(f"Candidate {cand['repo']} failed to load: {e}")

    print("\nNo ready-to-use Master found in the top candidates.")

if __name__ == "__main__":
    main()
