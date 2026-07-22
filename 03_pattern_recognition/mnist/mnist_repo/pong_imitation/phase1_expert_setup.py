import gymnasium as gym
import numpy as np
import cv2
from collections import deque
from huggingface_sb3 import load_from_hub
from stable_baselines3 import PPO
import ale_py

# 1. EXACT PREPROCESSING (As per Project Plan)
def preprocess_frame(frame):
    # frame: (210, 160, 3) uint8
    # grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    # resize to 84x84
    resized = cv2.resize(gray, (84, 84), interpolation=cv2.INTER_AREA)
    return resized # (84, 84) uint8

class ExpertWrapper(gym.ObservationWrapper):
    def __init__(self, env):
        super().__init__(env)
        self.num_stack = 4
        self.frames = deque(maxlen=self.num_stack)
        self.observation_space = gym.spaces.Box(
            low=0, high=255, shape=(self.num_stack, 84, 84), dtype=np.uint8
        )

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        processed = preprocess_frame(obs)
        for _ in range(self.num_stack):
            self.frames.append(processed)
        return np.array(self.frames), info

    def observation(self, obs):
        processed = preprocess_frame(obs)
        self.frames.append(processed)
        return np.array(self.frames)

def make_expert_env():
    # CRITICAL: Use exact environment trained on by SB3 experts
    env = gym.make("ALE/Pong-v4", render_mode=None) 
    env = ExpertWrapper(env)
    return env

def evaluate_expert(expert, n_episodes=3):
    print(f"\nEvaluating expert over {n_episodes} episodes...")
    env = make_expert_env()
    scores = []
    for ep in range(n_episodes):
        obs, _ = env.reset()
        done = False
        score = 0
        while not done:
            action, _ = expert.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, _ = env.step(int(action))
            score += reward
            done = terminated or truncated
        scores.append(score)
        print(f"  Episode {ep+1}: score = {score:+.0f}")
    env.close()
    mean_score = np.mean(scores)
    print(f"Expert mean score: {mean_score:+.2f}")
    print(f"Expert is {'VALID' if mean_score > 0 else 'INVALID'}")
    return mean_score

if __name__ == "__main__":
    # Register v4 environments explicitly
    try:
        ale_py.register_v4_envs()
    except AttributeError:
        # In some versions of ale-py, this is implicit or named differently
        pass
    
    print("Loading expert from HuggingFace...")
    try:
        checkpoint = load_from_hub(
            repo_id="sb3/ppo-PongNoFrameskip-v4",
            filename="ppo-PongNoFrameskip-v4.zip"
        )
        expert = PPO.load(checkpoint)
        print("Expert loaded successfully")
        
        score = evaluate_expert(expert)
        if score > 0:
            print("\nSUCCESS: Expert is validated. Ready for Phase 2 (Data Collection).")
        else:
            print("\nFAILURE: Expert is still not scoring. Switching to DQN expert as backup...")
            # Try DQN as backup if PPO fails
            from stable_baselines3 import DQN
            checkpoint_dqn = load_from_hub(
                repo_id="sb3/dqn-PongNoFrameskip-v4",
                filename="dqn-PongNoFrameskip-v4.zip"
            )
            expert_dqn = DQN.load(checkpoint_dqn)
            score_dqn = evaluate_expert(expert_dqn)
            if score_dqn > 0:
                print("\nSUCCESS: DQN Expert is validated.")
            else:
                print("\nCRITICAL FAILURE: No valid expert found.")
            
    except Exception as e:
        print(f"Critical Error: {e}")
