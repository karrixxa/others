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
        self.features = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten()
        )
        self.classifier = nn.Sequential(
            nn.Linear(64 * 7 * 7, 512),
            nn.ReLU(),
            nn.Linear(512, 6)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

def train_lite():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training 'Lite' Student on: {device}")

    npz_path = "/home/cxiong/pong_imitation/expert_data.npz"
    loader = get_dataloader(npz_path, batch_size=64, shuffle=True)
    
    model = StudentCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)

    # ONLY 2 EPOCHS to keep it "semi-low"
    epochs = 2
    model.train()

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        correct = 0
        total = 0
        for X, Y in loader:
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

        print(f"Epoch {epoch}/{epochs} | Loss: {running_loss/len(loader):.4f} | Acc: {100*correct/total:.2f}%")

    torch.save(model.state_dict(), "/home/cxiong/pong_imitation/student_lite.pth")
    print("Semi-low 'Lite' student saved to /home/cxiong/pong_imitation/student_lite.pth")

if __name__ == "__main__":
    train_lite()
