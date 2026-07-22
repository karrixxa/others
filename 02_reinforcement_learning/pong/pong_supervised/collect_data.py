import gymnasium as gym
import numpy as np
import pickle
import os
from PIL import Image
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

def preprocess(frame):
    # frame: (210, 160, 3) uint8 numpy array from gymnasium
    img = Image.fromarray(frame).convert('L')        # grayscale
    img = img.resize((84, 84), Image.BILINEAR)       # resize
    return np.array(img, dtype=np.float32) / 255.0   # normalize to [0,1]

def find_object_y(frame_84x84, x_min, x_max, threshold=0.6):
    region = frame_84x84[:, x_min:x_max]
    bright = np.where(region > threshold)
    if len(bright[0]) == 0:
        return None
    return float(np.mean(bright[0]))

def find_ball_y(frame_84x84, threshold=0.85):
    """
    Find ball Y centroid in pixel space.
    Masks out:
      - Top 15px (score display)
      - Bottom 5px (floor artifact)
      - Left 10px and right 10px (paddle columns)
    Only searches the actual play area.
    """
    # Mask to play area only
    play_area = frame_84x84[15:79, 10:74].copy()
    
    # Tighter threshold — ball and paddles are ~0.9, UI is same
    # but UI is now excluded by the Y mask
    bright = np.where(play_area > threshold)
    
    if len(bright[0]) == 0:
        return None, None  # ball not found
    
    # Additional filter: ball should be small (< 50 pixels)
    # Score text or artifacts tend to be large blobs
    if len(bright[0]) > 50:
        return None, None  # too many bright pixels — probably not ball
    
    # Return centroid in full frame coordinates (add back offsets)
    ball_y = float(np.mean(bright[0])) + 15.0  # add top mask offset
    ball_x = float(np.mean(bright[1])) + 10.0  # add left mask offset
    
    return ball_y, ball_x

def compute_ball_velocity(prev_ball_y, curr_ball_y, prev_ball_x, curr_ball_x):
    """Compute velocity from two consecutive frames."""
    vy = curr_ball_y - prev_ball_y
    vx = curr_ball_x - prev_ball_x
    return vx, vy

def predict_intercept_y(ball_x, ball_y, vx, vy, paddle_x=72.0,
                         wall_top=15.0, wall_bottom=79.0):
    """
    Project ball trajectory to paddle x-position, accounting for wall bounces.
    All coordinates in 84px space.
    Returns predicted Y at intercept, or None if ball moving away.
    """
    if vx == 0:
        return ball_y  # stationary — use current position

    # Only predict if ball is moving toward our paddle (right side)
    if vx < 0:
        return None   # ball moving left, away from our paddle

    frames_until_arrival = (paddle_x - ball_x) / vx
    if frames_until_arrival < 0:
        return None

    predicted_y = ball_y + vy * frames_until_arrival

    # Simulate wall bounces
    bounces = 0
    while (predicted_y < wall_top or predicted_y > wall_bottom) and bounces < 10:
        if predicted_y < wall_top:
            predicted_y = 2 * wall_top - predicted_y
        if predicted_y > wall_bottom:
            predicted_y = 2 * wall_bottom - predicted_y
        bounces += 1

    return float(np.clip(predicted_y, wall_top, wall_bottom))

def find_paddle_y(frame):
    return find_object_y(frame, x_min=70, x_max=78, threshold=0.6)

def collect(n_frames=80_000, save_path="/home/cxiong/pong_supervised/data/pong_predictive_dataset.pkl"):
    env = gym.make("ALE/Pong-v5", render_mode=None)
    dataset = []   
    
    obs, _ = env.reset()
    env.step(1)    # serve
    
    prev_frame = preprocess(obs)
    prev_ball_x, prev_ball_y = None, None
    frame_count = 0
    skipped = 0
    
    while frame_count < n_frames:
        action = np.random.choice([0, 2, 3])
        obs, reward, terminated, truncated, _ = env.step(action)
        
        if terminated or truncated:
            obs, _ = env.reset()
            env.step(1)
            prev_frame = preprocess(obs)
            prev_ball_x, prev_ball_y = None, None
            continue
        
        current_frame = preprocess(obs)
        res = find_ball_y(current_frame)
        
        if res is None or res[0] is None:
            skipped += 1
            prev_frame = current_frame
            continue
        
        ball_y, ball_x = res
        
        # Predictive Labeling Logic
        if prev_ball_x is not None and prev_ball_y is not None:
            vx, vy = compute_ball_velocity(prev_ball_y, ball_y,
                                            prev_ball_x, ball_x)
            intercept_y = predict_intercept_y(ball_x, ball_y, vx, vy)
            label = intercept_y if intercept_y is not None else ball_y
        else:
            label = ball_y   # first frame, no velocity yet

        prev_ball_x, prev_ball_y = ball_x, ball_y
        
        motion = np.clip(current_frame - prev_frame, 0, 1)
        stacked = np.stack([current_frame, motion], axis=0)
        
        dataset.append((stacked.astype(np.float32), np.float32(label)))
        prev_frame = current_frame
        frame_count += 1
        
        if frame_count % 5000 == 0:
            print(f"Collected {frame_count}/{n_frames} | Skipped: {skipped}")
    
    env.close()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'wb') as f:
        pickle.dump(dataset, f)
    print(f"Saved {len(dataset)} samples to {save_path}")
    print(f"Total skipped (ball not found): {skipped}")
    return dataset

if __name__ == "__main__":
    collect()
