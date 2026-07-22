
import gymnasium as gym
import numpy as np
import cv2
from flask import Flask, Response
import torch
from stable_baselines3 import PPO
import sys
import os

# Add project paths
sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

app = Flask(__name__)

# Load the best available model
MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
if not os.path.exists(MODEL_PATH):
    # Fallback to any existing model in the folder
    print("Primary model not found, searching for alternatives...")
    MODEL_PATH = "/home/cxiong/pong_imitation/student_cnn.pth"

print(f"Loading model: {MODEL_PATH}")
model = PPO.load(MODEL_PATH)

import ale_py
ale_py.register_v5_envs()
env = gym.make("ALE/Pong-v5", render_mode="rgb_array")
env = PerceptionWrapper(env)
obs, info = env.reset()

def generate_frames():
    global obs
    while True:
        # 1. Predict action
        action, _ = model.predict(obs, deterministic=True)
        
        # 2. Step env
        obs, reward, terminated, truncated, info = env.step(int(action))
        
        # 3. Get the image for rendering
        # PerceptionWrapper's env is the original gym env
        frame = env.unwrapped.render() 
        
        # Convert RGB to BGR for OpenCV
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Encode as JPG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        if terminated or truncated:
            obs, info = env.reset()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '<html><body><h1>Pong RL Live Stream</h1><img src="/video_feed" width="400"></body></html>'

if __name__ == "__main__":
    # Run on port 5001
    app.run(host='0.0.0.0', port=5001, threaded=True)
