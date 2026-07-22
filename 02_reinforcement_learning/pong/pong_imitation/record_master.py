import gymnasium as gym
import torch
import numpy as np
import sys
import os
import cv2
import ale_py

# Register ALE environments explicitly
ale_py.register_v5_envs()

# Setup paths for wrappers and architecture
sys.path.append('/home/cxiong/pong_imitation')
sys.path.append('/home/cxiong/pong_ppo')
from phase4_train import StudentCNN
from models.perception import PerceptionWrapper

def record_master_game():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluating on device: {device}")

    rl_model_path = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
    pth_model_path = "/home/cxiong/pong_imitation/student_cnn.pth"
    
    if os.path.exists(rl_model_path):
        print(f"Loading RL Master Model from: {rl_model_path}")
        from stable_baselines3 import PPO
        model = PPO.load(rl_model_path)
        is_sb3 = True
    elif os.path.exists(pth_model_path):
        print(f"Loading Student CNN from: {pth_model_path}")
        model = StudentCNN().to(device)
        model.load_state_dict(torch.load(pth_model_path, map_location=device))
        model.eval()
        is_sb3 = False
    else:
        print("Error: No model found!")
        return

    print("Initializing environment...")
    env = gym.make("Pong-v4", render_mode="rgb_array")
    wrapped_env = PerceptionWrapper(env)

    obs, info = wrapped_env.reset()
    done = False
    total_reward = 0
    frames = []

    print("RECORDING GAMEPLAY...")
    try:
        while not done:
            if is_sb3:
                action, _ = model.predict(obs, deterministic=True)
            else:
                obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(device)
                with torch.no_grad():
                    outputs = model(obs_tensor)
                    action = torch.argmax(outputs, dim=1).item()

            obs, reward, terminated, truncated, info = wrapped_env.step(action)
            frame = env.render() 
            frames.append(frame)
            total_reward += reward
            done = terminated or truncated

        print(f"Game Finished! Total Reward: {total_reward}")

        output_path = "/home/cxiong/pong_imitation/master_gameplay.mp4"
        if len(frames) > 0:
            height, width, layers = frames[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            video = cv2.VideoWriter(output_path, fourcc, 30, (width, height))
            for frame in frames:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                video.write(frame_bgr)
            video.release()
            print(f"SUCCESS: Video saved to {output_path}")
        else:
            print("No frames captured.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        env.close()

if __name__ == "__main__":
    record_master_game()
