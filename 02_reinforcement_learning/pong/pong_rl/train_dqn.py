import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms.functional as TF
from collections import deque, namedtuple
import random
import os
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

# ── Configuration ──────────────────────────────────────────────────────────────

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ENV_NAME = "Pong-v5"
BATCH_SIZE = 32
GAMMA = 0.99
EPS_START = 1.0
EPS_END = 0.05
EPS_DECAY = 100_000  # Decays over 100k frames
LR = 1e-4
TARGET_UPDATE = 1000 # Sync target net every 1k steps
REPLAY_CAPACITY = 100_000
MIN_REPLAY_SIZE = 1000
MAX_FRAMES = 1_000_000

Transition = namedtuple('Transition', ('state', 'action', 'reward', 'next_state', 'done'))

# ── Preprocessing ──────────────────────────────────────────────────────────────

def preprocess(frame):
    # frame: (210, 160, 3) uint8 numpy array
    t = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
    t = TF.rgb_to_grayscale(t)         # (1, 210, 160)
    t = TF.resize(t, [84, 84])         # (1, 84, 84)
    return t.squeeze(0).numpy()        # (84, 84) float32

class FrameStack:
    def __init__(self, n=4):
        self.n = n
        self.frames = deque(maxlen=n)
    
    def reset(self, frame):
        processed = preprocess(frame)
        for _ in range(self.n):
            self.frames.append(processed)
        return np.stack(self.frames, axis=0)
    
    def step(self, frame):
        self.frames.append(preprocess(frame))
        return np.stack(self.frames, axis=0)

# ── Model ──────────────────────────────────────────────────────────────────────

class DQN(nn.Module):
    def __init__(self, n_actions=6):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(4, 32, kernel_size=8, stride=4), # (32, 20, 20)
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), # (64, 9, 9)
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), # (64, 7, 7)
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, n_actions),
        )
    
    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, *args):
        self.buffer.append(Transition(*args))
    
    def sample(self, batch_size):
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)

# ── Training Loop ──────────────────────────────────────────────────────────────

def train():
    env = gym.make(ENV_NAME)
    policy_net = DQN().to(DEVICE)
    target_net = DQN().to(DEVICE)
    target_net.load_state_dict(policy_net.state_dict())
    target_net.eval()
    
    optimizer = optim.Adam(policy_net.parameters(), lr=LR)
    buffer = ReplayBuffer(REPLAY_CAPACITY)
    stacker = FrameStack()
    
    frame_count = 0
    episode_reward = 0
    episodes = 0
    
    print(f"Training started on {DEVICE}...")
    
    while frame_count < MAX_FRAMES:
        obs, info = env.reset()
        state = stacker.reset(obs)
        episode_reward = 0
        
        done = False
        while not done:
            # Epsilon-greedy action selection
            epsilon = max(EPS_END, EPS_START - frame_count / EPS_DECAY)
            if random.random() < epsilon:
                action = env.action_space.sample()
            else:
                with torch.no_grad():
                    state_t = torch.FloatTensor(state).unsqueeze(0).to(DEVICE)
                    action = policy_net(state_t).argmax().item()
            
            next_obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            # Reward clipping
            reward = float(np.sign(reward))
            
            next_state = stacker.step(next_obs)
            buffer.push(state, action, reward, next_state, done)
            
            state = next_state
            episode_reward += reward
            frame_count += 1
            
            # Learning step
            if len(buffer) > MIN_REPLAY_SIZE:
                batch = buffer.sample(BATCH_SIZE)
                states = torch.FloatTensor(np.array([t.state for t in batch])).to(DEVICE)
                actions = torch.LongTensor(np.array([t.action for t in batch])).to(DEVICE)
                rewards = torch.FloatTensor(np.array([t.reward for t in batch])).to(DEVICE)
                next_states = torch.FloatTensor(np.array([t.next_state for t in batch])).to(DEVICE)
                dones = torch.FloatTensor(np.array([t.done for t in batch])).to(DEVICE)
                
                q_current = policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    q_target = rewards + GAMMA * target_net(next_states).max(1).values * (1 - dones)
                
                loss = nn.MSELoss()(q_current, q_target)
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(policy_net.parameters(), 10)
                optimizer.step()
            
            if frame_count % TARGET_UPDATE == 0:
                target_net.load_state_dict(policy_net.state_dict())
        
        episodes += 1
        if episodes % 10 == 0:
            print(f"Ep {episodes} | Reward: {episode_reward} | Frames: {frame_count} | Eps: {epsilon:.2f}")
        
        # Save checkpoint
        if episodes % 100 == 0:
            torch.save(policy_net.state_dict(), f"/home/cxiong/pong_rl/pong_dqn_ep{episodes}.pth")

    env.close()

if __name__ == "__main__":
    train()
