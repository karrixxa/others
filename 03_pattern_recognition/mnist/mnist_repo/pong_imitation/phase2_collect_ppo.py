import gymnasium as gym
import ale_py
import numpy as np
import os
import sys
from collections import Counter
from tqdm import tqdm
from huggingface_sb3 import load_from_hub
from stable_baselines3 import PPO

# IMPORTANT: Import the EXACT wrapper used during PPO training to ensure
# the expert sees the same perception channels (Motion Maps, Paddle Markers, etc.)
sys.path.append('/home/cxiong/pong_ppo')
try:
    from train import PerceptionWrapper, RewardWrapper
except ImportError:
    # Fallback in case the classes are in a different file in the ppo project
    from models.perception import PerceptionWrapper 

def make_collection_env():
    # Use the exact same environment ID and wrapper sequence as PPO training
    env = gym.make("ALE/Pong-v5", render_mode=None)
    env = PerceptionWrapper(env) 
    return env

def main():
    # 1. Setup Environment
    print("Initializing environment with PPO PerceptionWrapper...")
    env = make_collection_env()
    
    # 2. Load the PPO expert (The Master)
    model_path = "/home/cxiong/pong_ppo/weights/ppo_pong_final.zip"
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return

    print(f"Loading PPO expert from {model_path}...")
    model = PPO.load(model_path)
    
    # 3. Data Collection
    target_frames = 100000
    observations = []
    actions = []
    
    obs, info = env.reset()
    print(f"Collecting {target_frames} frames of expert data...")
    
    pbar = tqdm(total=target_frames)
    while len(observations) < target_frames:
        # Predict action from the Master
        action, _ = model.predict(obs, deterministic=True)
        
        # Store the perception-enhanced observation and the action
        observations.append(np.array(obs))
        actions.append(int(action))
        
        # Step environment
        obs, reward, terminated, truncated, info = env.step(int(action))
        
        if terminated or truncated:
            obs, info = env.reset()
        
        pbar.update(1)
    pbar.close()
    
    # Convert to numpy arrays
    X = np.array(observations, dtype=np.float32) # Perception maps are usually float
    Y = np.array(actions, dtype=np.int64)
    
    # 4. Verification & Distribution
    print("\n--- Data Collection Summary ---")
    print(f"X shape: {X.shape}") 
    print(f"Y shape: {Y.shape}") 
    
    action_names = {0:'NOOP', 1:'FIRE', 2:'RIGHT/UP', 3:'LEFT/DOWN', 4:'RIGHT+FIRE', 5:'LEFT+FIRE'}
    counts = Counter(Y)
    print("\nAction Distribution:")
    for a in range(6):
        count = counts.get(a, 0)
        print(f"Action {a} ({action_names[a]}): {count:6d} ({100*count/len(Y):.1f}%)")
    
    # 5. Export
    save_path = "/home/cxiong/pong_imitation/expert_data.npz"
    np.savez_compressed(save_path, X=X, Y=Y)
    print(f"\nSuccessfully saved expert data to {save_path}")
    
    env.close()

if __name__ == "__main__":
    main()
