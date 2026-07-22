import gymnasium as gym
import numpy as np
import torch
import torch.nn as nn
import torchvision.transforms.functional as TF
import matplotlib.pyplot as plt
from collections import deque
import ale_py

# Force registration of ALE envs
ale_py.register_v5_envs()

# ── Configuration ──────────────────────────────────────────────────────────────

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
ENV_NAME = "ALE/Pong-v5" 

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

# ── The CNN Brain (from the DQN) ────────────────────────────────────────────────

class PongCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(4, 32, kernel_size=8, stride=4) # (32, 20, 20)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv2d(32, 64, kernel_size=4, stride=2) # (64, 9, 9)
        self.relu2 = nn.ReLU()
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1) # (64, 7, 7)
        self.relu3 = nn.ReLU()
        
    def forward(self, x):
        x1 = self.conv1(x)
        x1 = self.relu1(x1)
        x2 = self.conv2(x1)
        x2 = self.relu2(x2)
        x3 = self.conv3(x2)
        x3 = self.relu3(x3)
        return x1, x2, x3

# ── Visualization Function ─────────────────────────────────────────────────────

def visualize_cnn_vision(frame_stack):
    model = PongCNN().to(DEVICE)
    model.eval()
    
    # Convert state to tensor
    state_t = torch.FloatTensor(frame_stack).unsqueeze(0).to(DEVICE)
    
    with torch.no_grad():
        layer1, layer2, layer3 = model(state_t)
    
    # Move to CPU and numpy for plotting
    l1 = layer1[0].cpu().numpy()
    l2 = layer2[0].cpu().numpy()
    l3 = layer3[0].cpu().numpy()
    
    # Create a grid of feature maps for the first layer
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # Original Stack (first frame)
    axes[0].imshow(frame_stack[0], cmap='gray')
    axes[0].set_title("Agent's Input (Frame 0)")
    axes[0].axis('off')
    
    # Layer 1: First few feature maps
    axes[1].imshow(np.mean(l1, axis=0), cmap='viridis')
    axes[1].set_title("Layer 1 Activations (Mean)")
    axes[1].axis('off')
    
    # Layer 3: Final high-level features
    axes[2].imshow(np.mean(l3, axis=0), cmap='magma')
    axes[2].set_title("Layer 3 Activations (Mean)")
    axes[2].axis('off')
    
    plt.tight_layout()
    plt.savefig("/home/cxiong/pong_rl/cnn_vision_test.png")
    print("Vision test saved to /home/cxiong/pong_rl/cnn_vision_test.png")

# ── Execution ──────────────────────────────────────────────────────────────────

def run_test():
    try:
        # Use ALE/Pong-v5 now that we've registered it
        env = gym.make(ENV_NAME)
        print(f"Successfully created environment: {ENV_NAME}")

        obs, info = env.reset()
        stacker = FrameStack()
        state = stacker.reset(obs)
        
        print("Analyzing CNN vision...")
        visualize_cnn_vision(state)
        
        env.close()
        print("Vision test completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_test()
