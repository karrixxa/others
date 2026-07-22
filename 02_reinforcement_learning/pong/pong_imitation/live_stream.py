import gymnasium as gym
import torch
import numpy as np
import sys
import os
import cv2
import ale_py
from flask import Flask, Response

# Register ALE environments
ale_py.register_v5_envs()

# Setup paths for wrappers and architecture
sys.path.append('/home/cxiong/pong_imitation')
sys.path.append('/home/cxiong/pong_ppo')
from phase4_train import StudentCNN
from models.perception import PerceptionWrapper

app = Flask(__name__)

# Global state for the stream
class AgentState:
    def __init__(self):
        self.frame = None
        self.done = False
        self.total_reward = 0
        
        # Setup Model
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        rl_model_path = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
        pth_model_path = "/home/cxiong/pong_imitation/student_cnn.pth"
        
        if os.path.exists(rl_model_path):
            from stable_baselines3 import PPO
            self.model = PPO.load(rl_model_path)
            self.is_sb3 = True
        else:
            self.model = StudentCNN().to(self.device)
            self.model.load_state_dict(torch.load(pth_model_path, map_location=self.device))
            self.model.eval()
            self.is_sb3 = False

        # Setup Env
        self.env = gym.make("Pong-v4", render_mode="rgb_array")
        self.wrapped_env = PerceptionWrapper(self.env)
        self.obs, _ = self.wrapped_env.reset()

    def step(self):
        if self.done:
            self.obs, _ = self.wrapped_env.reset()
            self.done = False
            self.total_reward = 0

        if self.is_sb3:
            action, _ = self.model.predict(self.obs, deterministic=True)
        else:
            obs_tensor = torch.from_numpy(self.obs).float().unsqueeze(0).to(self.device)
            with torch.no_grad():
                outputs = self.model(obs_tensor)
                action = torch.argmax(outputs, dim=1).item()

        self.obs, reward, terminated, truncated, _ = self.wrapped_env.step(action)
        self.total_reward += reward
        self.done = terminated or truncated
        self.frame = self.env.render()

state = AgentState()

def generate_frames():
    while True:
        state.step()
        if state.frame is not None:
            # Convert RGB to JPEG
            ret, buffer = cv2.imencode('.jpg', cv2.cvtColor(state.frame, cv2.COLOR_RGB2BGR))
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return '<h1>Pong Master Live Stream</h1><img src="/video_feed" width="400">'

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print("\n>>> STARTING LIVE STREAM SERVER <<<")
    print("1. Ensure you have a tunnel: ssh -L 5000:localhost:5000 cxiong@kant")
    print("2. Open browser to: http://localhost:5000")
    app.run(host='0.0.0.0', port=5001, threaded=True)
