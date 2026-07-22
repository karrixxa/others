import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from phase3_pipeline import get_dataloader
import numpy as np
import os

class StudentCNN(nn.Module):
    def __init__(self):
        super(StudentCNN, self).__init__()
        # Input: (batch, 6, 84, 84)
        self.features = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=8, stride=4), nn.ReLU(), # 84 -> 20
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(), # 20 -> 9
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(), # 9 -> 7
            nn.Flatten()
        )
        # 64 * 7 * 7 = 3136
        self.classifier = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 6) # 6 Pong actions
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def train():
    # 1. Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    npz_path = "/home/cxiong/pong_imitation/expert_data.npz"
    loader = get_dataloader(npz_path, batch_size=64, shuffle=True)
    
    model = StudentCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)

    epochs = 30 # Increased from 10 to 30 for polishing
    model.train()

    print(f"Starting training for {epochs} epochs...")
    
    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        correct = 0
        total = 0
        
        for i, (X, Y) in enumerate(loader):
            X, Y = X.to(device), Y.to(device)
            
            optimizer.zero_grad()
            outputs = model(X)
            loss = criterion(outputs, Y)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += Y.size(0)
            correct += (predicted == Y).sum().item()
            
            if (i + 1) % 100 == 0:
                print(f"Epoch [{epoch}/{epochs}], Batch [{i+1}/{len(loader)}], Loss: {loss.item():.4f}")

        epoch_loss = running_loss / len(loader)
        epoch_acc = 100 * correct / total
        print(f"\n===> Epoch {epoch} Summary: Loss = {epoch_loss:.4f}, Accuracy = {epoch_acc:.2f}%")
        
        if epoch_acc > 95.0:
            print("Target accuracy achieved! Stopping early.")
            break

    # Save the student model
    torch.save(model.state_dict(), "/home/cxiong/pong_imitation/student_cnn.pth")
    print(f"Student model saved to /home/cxiong/pong_imitation/student_cnn.pth")

if __name__ == "__main__":
    train()
