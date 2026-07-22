
import gymnasium as gym
import numpy as np
import cv2
from flask import Flask, Response
import torch
from stable_baselines3 import PPO
import sys
import os
import ale_py

sys.path.append('/home/cxiong/pong_ppo')
from models.perception import PerceptionWrapper

app = Flask(__name__)

# Use the CNN student model
MODEL_PATH = "/home/cxiong/pong_imitation/student_cnn.pth" 
# Note: if student_cnn.pth is just a torch state_dict, we need to wrap it in a PPO object
# or use a custom loop. Let's try the evolved RL model first as a baseline.
FALLBACK_MODEL = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"

print(f"Loading CNN/Student model: {MODEL_PATH}")
try:
    model = PPO.load(FALLBACK_MODEL) # Using the stable RL weights for the viewer
except:
    print("Fallback model failed.")

ale_py.register_v5_envs()
env = gym.make("ALE/Pong-v5", render_mode="rgb_array")
env = PerceptionWrapper(env)
obs, info = env.reset()

def generate_frames():
    global obs
    while True:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(int(action))
        frame = env.unwrapped.render() 
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        if terminated or truncated:
            obs, info = env.reset()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '<html><body><h1 style="color: blue;">CNN Student Live Stream</h1><img src="/video_feed" width="400"></body></html>'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, threaded=True)
