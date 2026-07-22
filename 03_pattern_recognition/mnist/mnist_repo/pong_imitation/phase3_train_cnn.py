import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
import os
from tqdm import tqdm

# --- Configuration ---
DATA_PATH = "/home/cxiong/pong_imitation/expert_data.npz"
MODEL_SAVE_PATH = "/home/cxiong/pong_imitation/student_cnn.pth"
BATCH_SIZE = 64
EPOCHS = 7
LEARNING_RATE = 1e-4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class ImitationCNN(nn.Module):
    def __init__(self):
        super(ImitationCNN, self).__init__()
        # Input shape: (Batch, 6, 84, 84)
        self.features = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten(),
        )
        
        # Calculate flatten size: 84 -> 20 -> 9 -> 7
        # 64 * 7 * 7 = 3136
        self.classifier = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 6) # 6 possible Atari Pong actions
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def main():
    print(f"Using device: {DEVICE}")
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        print(f"Error: Data file {DATA_PATH} not found.")
        return
        
    print("Loading expert data...")
    data = np.load(DATA_PATH)
    X = data['X'] # (100000, 6, 84, 84)
    Y = data['Y'] # (100000,)
    
    # Convert to Tensors
    X_tensor = torch.from_numpy(X).float()
    Y_tensor = torch.from_numpy(Y).long()
    
    dataset = TensorDataset(X_tensor, Y_tensor)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 2. Initialize Model
    model = ImitationCNN().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    print(f"Starting training for {EPOCHS} epochs...")
    
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        pbar = tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
        for inputs, targets in pbar:
            inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()
            
            pbar.set_postfix({"Loss": f"{running_loss/(pbar.n+1):.4f}", "Acc": f"{100.*correct/total:.2f}%"})
            
        epoch_loss = running_loss / len(loader)
        epoch_acc = 100. * correct / total
        print(f"Epoch {epoch+1} Summary: Loss={epoch_loss:.4f}, Acc={epoch_acc:.2f}%")
        
        # Save checkpoint after every epoch to prevent data loss
        torch.save(model.state_dict(), MODEL_SAVE_PATH)
        print(f"Checkpoint saved to {MODEL_SAVE_PATH}")


if __name__ == "__main__":
    main()
