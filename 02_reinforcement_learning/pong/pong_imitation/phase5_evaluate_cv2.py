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

def evaluate_with_opencv():
    # 1. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Evaluating on device: {device}")

    # 2. Load the trained student model
    model = StudentCNN().to(device)
    model_path = "/home/cxiong/pong_imitation/student_cnn.pth"
    if not os.path.exists(model_path):
        print(f"Error: Model not found at {model_path}")
        return
    
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print("Student model loaded successfully.")

    # 3. Setup Environment with RGB_ARRAY (Bypassing 'human' render mode)
    print("Initializing environment with render_mode='rgb_array'...")
    env = gym.make("Pong-v4", render_mode="rgb_array")
    # We wrap it to get the perception channels, but we'll render the RAW pixels
    wrapped_env = PerceptionWrapper(env)

    obs, info = wrapped_env.reset()
    done = False
    total_reward = 0
    episode_length = 0

    print("\n>>> LIVE PLAY STARTING (OpenCV Window) <<<")
    print("Window name: 'Pong Student Evaluation'. Press 'q' to quit.")

    try:
        while not done:
            # 1. Get the action from the student CNN
            obs_tensor = torch.from_numpy(obs).float().unsqueeze(0).to(device)
            with torch.no_grad():
                outputs = model(obs_tensor)
                action = torch.argmax(outputs, dim=1).item()

            # 2. Step the environment
            obs, reward, terminated, truncated, info = wrapped_env.step(action)
            
            # 3. Get the RAW RGB frame for visualization
            frame = env.render() 
            
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            cv2.imshow("Pong Student Evaluation", frame_bgr)

            cv2.imshow("Pong Student Evaluation", frame_bgr)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            total_reward += reward
            episode_length += 1
            done = terminated or truncated

        print(f"\nEpisode Finished! Total Reward: {total_reward}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cv2.destroyAllWindows()
        env.close()

if __name__ == "__main__":
    evaluate_with_opencv()
