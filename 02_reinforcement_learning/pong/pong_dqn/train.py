import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import os
from PIL import Image
import ale_py
import torchvision.transforms as T

# Force registration of ALE envs
ale_py.register_v5_envs()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def preprocess_gpu(frames):
    # frames: (num_envs, 210, 160, 3) -> (num_envs, 1, 84, 84)
    with torch.no_grad():
        # Convert to tensor and normalize
        t = torch.from_numpy(frames).permute(0, 3, 1, 2).float().to(device) / 255.0
        # Simple grayscale by averaging channels
        gray = t.mean(dim=1, keepdim=True) # (num_envs, 1, 210, 160)
        resized = F.interpolate(gray, size=(84, 84), mode='bilinear', align_corners=False)
        return resized # (num_envs, 1, 84, 84)

def get_perception_gpu(current_frames, prev_frames, paddle_ys):
    # current_frames: (num_envs, 1, 84, 84)
    motion = torch.clamp(current_frames - prev_frames, 0, 1)
    
    paddle_channels = torch.zeros_like(current_frames)
    for i in range(current_frames.shape[0]):
        py = int(np.clip(paddle_ys[i], 0, 83))
        paddle_channels[i, 0, max(0, py-2):min(84, py+3), 70:78] = 1.0
    
    return motion, paddle_channels

def get_paddle_y_fast(frame_tensors):
    # frame_tensors: (num_envs, 1, 84, 84)
    paddle_ys = []
    for i in range(frame_tensors.shape[0]):
        region = frame_tensors[i, 0, :, 70:78]
        bright = torch.where(region > 0.6)
        if bright[0].numel() == 0:
            paddle_ys.append(42.0)
        else:
            paddle_ys.append(bright[0].float().mean().item())
    return np.array(paddle_ys)

def train():
    # Hyperparameters
    NUM_ENVS = 8
    BATCH_SIZE = 128 
    GAMMA = 0.99
    LR = 1e-4
    EPS_DECAY = 250000
    TARGET_UPDATE_TAU = 0.005
    TOTAL_FRAMES = 500_000 
    SAVE_INTERVAL = 20000
    SURVIVAL_REWARD = 0.01
    
    # Vectorized Environment
    envs = gym.vector.AsyncVectorEnv([
        lambda: gym.make("ALE/Pong-v5", render_mode=None) for _ in range(NUM_ENVS)
    ])
    
    from models.model import PerceptionDQN, load_pretrained_weights
    from models.agent import DQNAgent, ReplayBuffer
    
    agent = DQNAgent(state_dim=(6, 84, 84), action_size=6, lr=LR, gamma=GAMMA, epsilon_decay=EPS_DECAY)
    
    checkpoint_path = "/home/cxiong/pong_dqn/weights/dqn_checkpoint_200000.pth"
    if os.path.exists(checkpoint_path):
        print(f"Restarting from checkpoint: {checkpoint_path}")
        agent.policy_net.load_state_dict(torch.load(checkpoint_path, map_location=device))
        agent.target_net.load_state_dict(agent.policy_net.state_dict())
        frame_count = 200000
    else:
        frame_count = 0

    buffer = ReplayBuffer(capacity=200000)
    
    obs, _ = envs.reset()
    current_frames_gpu = preprocess_gpu(obs)
    prev_frames_gpu = current_frames_gpu.clone()
    
    # State stacks for each env: (num_envs, 4, 84, 84)
    state_stacks = torch.cat([prev_frames_gpu] * 4, dim=1)
    
    episode_rewards = np.zeros(NUM_ENVS)
    episode_wins = np.zeros(NUM_ENVS)
    episode_losses = np.zeros(NUM_ENVS)
    episode_frames = np.zeros(NUM_ENVS)
    running_avg_q = 0.0
    
    print(f"VECTORED GUIDED PIPELINE STARTING at {frame_count} frames. Target: {TOTAL_FRAMES}")
    
    try:
        while frame_count < TOTAL_FRAMES:
            # 1. Perception
            current_frames_gpu = preprocess_gpu(obs)
            paddle_ys = get_paddle_y_fast(current_frames_gpu)
            motion, paddle_markers = get_perception_gpu(current_frames_gpu, prev_frames_gpu, paddle_ys)
            
            # Update state stacks
            state_stacks = torch.cat([state_stacks[:, 1:], current_frames_gpu], dim=1)
            
            # Create full states (num_envs, 6, 84, 84)
            full_states = torch.cat([state_stacks, motion, paddle_markers], dim=1).cpu().numpy()
            
            # 2. Act
            actions = np.array([agent.select_action(s) for s in full_states])
            next_obs, rewards, terminations, truncations, infos = envs.step(actions)
            
            # 3. Reward Shaping: Add survival reward
            # Standard Pong reward is +1/-1 only when a point is scored.
            # We add +0.01 for every frame the ball is in play (reward == 0).
            shaped_rewards = np.array(rewards)
            survival_mask = (shaped_rewards == 0)
            shaped_rewards[survival_mask] += SURVIVAL_REWARD
            
            # Track actual wins/losses for logging
            for i in range(NUM_ENVS):
                if rewards[i] > 0: episode_wins[i] += 1
                if rewards[i] < 0: episode_losses[i] += 1

            # 4. Next State
            next_frames_gpu = preprocess_gpu(next_obs)
            next_paddle_ys = get_paddle_y_fast(next_frames_gpu)
            next_motion, next_paddle_markers = get_perception_gpu(next_frames_gpu, current_frames_gpu, next_paddle_ys)
            
            next_state_stacks = torch.cat([state_stacks[:, 1:], next_frames_gpu], dim=1)
            next_full_states = torch.cat([next_state_stacks, next_motion, next_paddle_markers], dim=1).cpu().numpy()
            
            # 5. Store in Buffer
            for i in range(NUM_ENVS):
                done = terminations[i] or truncations[i]
                buffer.push(full_states[i], actions[i], shaped_rewards[i], next_full_states[i], done)
            
            # 6. Train
            if len(buffer) > BATCH_SIZE:
                batch = buffer.sample(BATCH_SIZE)
                loss, avg_q = agent.train_step(batch)
                agent.soft_update_target(tau=TARGET_UPDATE_TAU)
                running_avg_q = 0.99 * running_avg_q + 0.01 * avg_q
            
            agent.update_epsilon()
            prev_frames_gpu = current_frames_gpu
            obs = next_obs
            frame_count += NUM_ENVS
            episode_rewards += shaped_rewards
            episode_frames += 1
            
            # Handle resets and logging
            dones = np.logical_or(terminations, truncations)
            if np.any(dones):
                for i in range(NUM_ENVS):
                    if dones[i]:
                        print(f"Env {i} | Frame: {frame_count} | Total Reward: {episode_rewards[i]:.2f} | Wins: {episode_wins[i]} | Losses: {episode_losses[i]} | Rally: {int(episode_frames[i])} | AvgQ: {running_avg_q:.4f}")
                        episode_rewards[i] = 0
                        episode_wins[i] = 0
                        episode_losses[i] = 0
                        episode_frames[i] = 0
            
            if frame_count % SAVE_INTERVAL == 0:
                torch.save(agent.policy_net.state_dict(), f"/home/cxiong/pong_dqn/weights/dqn_checkpoint_{frame_count}.pth")
                print(f"Saved checkpoint at {frame_count} frames")

    except KeyboardInterrupt:
        print("\nTraining interrupted.")
    finally:
        torch.save(agent.policy_net.state_dict(), "/home/cxiong/pong_dqn/weights/dqn_final.pth")
        envs.close()

if __name__ == "__main__":
    train()
