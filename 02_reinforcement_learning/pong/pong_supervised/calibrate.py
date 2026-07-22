import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

def preprocess(frame):
    img = Image.fromarray(frame).convert('L')
    img = img.resize((84, 84), Image.BILINEAR)
    return np.array(img, dtype=np.float32) / 255.0

def find_ball_y(frame_84x84, threshold=0.85):
    play_area = frame_84x84[15:79, 10:74].copy()
    bright = np.where(play_area > threshold)
    if len(bright[0]) == 0 or len(bright[0]) > 50:
        return None, None
    ball_y = float(np.mean(bright[0])) + 15.0
    ball_x = float(np.mean(bright[1])) + 10.0
    return ball_y, ball_x

env = gym.make("ALE/Pong-v5", render_mode=None)
obs, _ = env.reset()
env.step(1)  # serve

print("Frame | Ball Y | Ball X | Bright Pixels")
for i in range(20):
    obs, _, _, _, _ = env.step(2)
    frame = preprocess(obs)
    
    # Verification of detection logic
    play_area = frame[15:79, 10:74].copy()
    bright = np.where(play_area > 0.85)
    num_bright = len(bright[0])
    
    by, bx = find_ball_y(frame)
    
    # Handle None values for printing
    by_str = f"{by:6.1f}" if by is not None else "  None"
    bx_str = f"{bx:6.1f}" if bx is not None else "  None"
    
    print(f"  {i:3d} | {by_str} | {bx_str} | {num_bright:4d}")

plt.figure(figsize=(10, 4))
plt.subplot(1,2,1)
plt.imshow(frame, cmap='gray')
plt.title("Preprocessed frame")
plt.subplot(1,2,2)
# Show exactly what find_ball_y sees
mask = np.zeros_like(frame)
mask[15:79, 10:74] = (frame[15:79, 10:74] > 0.85)
plt.imshow(mask, cmap='gray')
plt.title("Filtered Ball Detection")
plt.savefig("/home/cxiong/pong_supervised/calibration.png")
plt.close()
env.close()
print("\nSaved calibration.png — check that only the ball is white and score is gone.")
