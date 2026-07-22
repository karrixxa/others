import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pickle
import numpy as np
import matplotlib.pyplot as plt
import os

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Training on: {DEVICE}")

class PongDataset(Dataset):
    def __init__(self, data):
        self.data = data
    def __len__(self):
        return len(self.data)
    def __getitem__(self, idx):
        stacked, ball_y = self.data[idx]
        return torch.tensor(stacked), torch.tensor(ball_y / 84.0)

class BallTracker(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(2, 32, kernel_size=8, stride=4),  
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), 
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), 
            nn.ReLU(),
        )
        self.fc = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 1),
            nn.Sigmoid(),   
        )
    def forward(self, x):
        x = self.conv(x)
        x = x.view(x.size(0), -1)
        return self.fc(x).squeeze(1)

def train():
    data_path = "/home/cxiong/pong_supervised/pong_dataset.pkl"
    if not os.path.exists(data_path):
        print(f"Error: Dataset {data_path} not found. Run collect_data.py first.")
        return

    with open(data_path, "rb") as f:
        data = pickle.load(f)
    
    split = int(0.9 * len(data))
    train_data, val_data = data[:split], data[split:]
    
    train_loader = DataLoader(PongDataset(train_data), batch_size=64, shuffle=True)
    val_loader = DataLoader(PongDataset(val_data), batch_size=64, shuffle=False)
    
    model = BallTracker().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    train_losses, val_losses = [], []
    
    for epoch in range(20):
        model.train()
        epoch_loss = []
        for stacked, ball_y in train_loader:
            stacked, ball_y = stacked.to(DEVICE), ball_y.to(DEVICE)
            optimizer.zero_grad()
            pred = model(stacked)
            loss = criterion(pred, ball_y)
            loss.backward()
            optimizer.step()
            epoch_loss.append(loss.item())
        
        model.eval()
        val_loss = []
        with torch.no_grad():
            for stacked, ball_y in val_loader:
                stacked, ball_y = stacked.to(DEVICE), ball_y.to(DEVICE)
                pred = model(stacked)
                val_loss.append(criterion(pred, ball_y).item())
        
        train_l = np.mean(epoch_loss)
        val_l = np.mean(val_loss)
        train_losses.append(train_l)
        val_losses.append(val_l)
        
        pixel_error = np.sqrt(val_l) * 84
        print(f"Epoch {epoch+1}/20 | Train: {train_l:.4f} | Val: {val_l:.4f} | Pixel error: {pixel_error:.1f}px")
    
    torch.save(model.state_dict(), "/home/cxiong/pong_supervised/ball_tracker.pth")
    
    plt.figure()
    plt.plot(train_losses, label='train')
    plt.plot(val_losses, label='val')
    plt.xlabel('Epoch')
    plt.ylabel('MSE Loss')
    plt.legend()
    plt.savefig("/home/cxiong/pong_supervised/training_curve.png")
    print(f"Saved ball_tracker.pth. Final pixel error: {np.sqrt(val_losses[-1])*84:.1f}px")

if __name__ == "__main__":
    train()
