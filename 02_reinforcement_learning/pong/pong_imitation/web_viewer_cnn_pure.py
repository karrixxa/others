
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

# Use the RL evolved model for the "Student" baseline if the .pth is just weights
MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
print(f"Loading model: {MODEL_PATH}")
model = PPO.load(MODEL_PATH)

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
    return '''
    <html>
        <head>
            <title>CNN Pong Stream</title>
            <style>
                body { background-color: #111; color: white; text-align: center; font-family: sans-serif; }
                .video-container { margin-top: 20px; }
                img { 
                    width: 800px; 
                    height: auto; 
                    border: 5px solid #444; 
                    image-rendering: pixelated; 
                    box-shadow: 0 0 20px rgba(0,0,0,0.5);
                }
            </style>
        </head>
        <body>
            <h1>CNN Pure Stream</h1>
            <div class="video-container">
                <img src="/video_feed">
            </div>
            <p>Upscaled for visibility (Pixelated Mode)</p>
        </body>
    </html>
    '''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, threaded=True)
