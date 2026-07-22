import gymnasium as gym
import ale_py
from gymnasium.wrappers import AtariPreprocessing, FrameStackObservation
from huggingface_sb3 import load_from_hub
from stable_baselines3 import DQN
import numpy as np
from collections import Counter

def make_expert_env():
    env = gym.make("PongNoFrameskip-v4", render_mode=None)
    env = AtariPreprocessing(env, scale_obs=False, grayscale_obs=True, frame_skip=1)
    env = FrameStackObservation(env, stack_size=4)
    return env

def main():
    env = make_expert_env()
    
    print("Loading DQN expert from Hub...")
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
    
    print("Analyzing action distribution over 200 steps...")
    obs, info = env.reset()
    actions_taken = []
    
    for i in range(200):
        # Ensure obs is a numpy array
        action, _ = expert.predict(np.array(obs), deterministic=True)
        action_int = int(action)
        actions_taken.append(action_int)
        
        obs, reward, terminated, truncated, info = env.step(action_int)
        if terminated or truncated:
            obs, info = env.reset()
            
    print("\nAction Distribution:")
    print(Counter(actions_taken))
    
    env.close()

if __name__ == "__main__":
    main()
