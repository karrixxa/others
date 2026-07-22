
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

MODEL_PATH = "/home/cxiong/pong_imitation/student_rl_evolved_from_lite_breakout.zip"
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
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pong RL Master</title>
        <style>
            body { 
                margin: 0; padding: 0; background-color: black; 
                display: flex; justify-content: center; align-items: center; 
                height: 100vh; overflow: hidden; font-family: sans-serif;
            }
            .container { position: relative; box-shadow: 0 0 50px rgba(255,255,255,0.1); }
            img { display: block; border: 2px solid #333; }
            .label {
                position: absolute; top: -30px; left: 0; 
                color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="label">RL Master Live Stream</div>
            <img src="/video_feed" width="400">
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, threaded=True)
