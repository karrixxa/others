import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import pickle
import os
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────────
DATA_PATH = "/home/cxiong/pong_supervised/data/pong_predictive_dataset.pkl"
MODEL_PATH = "/home/cxiong/pong_supervised/pong_cnn_classifier.pth"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BATCH_SIZE = 64
EPOCHS = 10
LR = 0.001

# ── Dataset ─────────────────────────────────────────────────────────────────────

class PongDataset(Dataset):
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = pickle.load(f)
            
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        # Upgrade 2: current, prev, label
        current, prev, label = self.data[idx]
        
        # Compute motion map (Frame Differencing)
        # Using clip to handle negative values as per common failure modes
        motion = np.clip(current.astype(np.float32) - prev.astype(np.float32), 0, 1.0)
        
        # Stack into 2-channel tensor: (2, 84, 84)
        stacked = np.stack([current.astype(np.float32), motion], axis=0)
        
        return torch.tensor(stacked), torch.tensor(label)

# ── Model Architecture ─────────────────────────────────────────────────────────

class PongClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            # Upgrade 2: Change input channels from 1 to 2
            nn.Conv2d(2, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 512), nn.ReLU(),
            nn.Linear(512, 3),
        )
        
    def forward(self, x):
        return self.fc(self.conv(x))

# ── Training Loop ──────────────────────────────────────────────────────────────

def train():
    print(f"Loading dataset from {DATA_PATH}...")
    dataset = PongDataset(DATA_PATH)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    model = PongClassifier().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    
    print(f"Training on {DEVICE}...")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        acc = 100 * correct / total
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {total_loss/len(loader):.4f} | Acc: {acc:.2f}%")
        
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
