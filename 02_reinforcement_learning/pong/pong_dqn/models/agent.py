import numpy as np
import torch
import torch.nn.functional as F
import random
from collections import deque

class ReplayBuffer:
    def __init__(self, capacity=100000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        state, action, reward, next_state, done = zip(*random.sample(self.buffer, batch_size))
        return (np.array(state), np.array(action), np.array(reward), 
                np.array(next_state), np.array(done))

    def __len__(self):
        return len(self.buffer)

class DQNAgent:
    def __init__(self, state_dim, action_size, lr=1e-4, gamma=0.99, epsilon_start=1.0, epsilon_end=0.05, epsilon_decay=250000):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Networks
        from .model import PerceptionDQN
        self.policy_net = PerceptionDQN(action_size).to(self.device)
        self.target_net = PerceptionDQN(action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        
        self.optimizer = torch.optim.Adam(self.policy_net.parameters(), lr=lr)
        
        # Hyperparameters
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.action_size = action_size
        self.steps_done = 0

    def select_action(self, state):
        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            return self.policy_net(state).argmax().item()

    def update_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * (1.0 - 1.0/self.epsilon_decay))
        self.steps_done += 1

    def train_step(self, batch):
        states, actions, rewards, next_states, dones = batch
        
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)

        # Current Q values
        current_q = self.policy_net(states).gather(1, actions).squeeze()
        
        # Target Q values (using Target Network for stability)
        with torch.no_grad():
            max_next_q = self.target_net(next_states).max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * max_next_q
            
        # Huber Loss is more robust to outliers than MSE
        loss = F.huber_loss(current_q, target_q)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        # Return loss and the average current Q value as a confidence metric
        return loss.item(), current_q.mean().item()

    def soft_update_target(self, tau=0.005):
        # Polyak Averaging: target = tau*policy + (1-tau)*target
        for target_param, policy_param in zip(self.target_net.parameters(), self.policy_net.parameters()):
            target_param.data.copy_(tau * policy_param.data + (1.0 - tau) * target_param.data)
