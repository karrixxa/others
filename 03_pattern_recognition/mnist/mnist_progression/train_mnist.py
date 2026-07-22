import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128), nn.ReLU(), nn.Dropout(0.5),
            nn.Linear(128, 10),
        )
    def forward(self, x):
        return self.fc(self.conv(x))

def train():
    device = torch.device("cpu")
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
    train_set = datasets.MNIST(root='/home/cxiong/mnist_progression/data', train=True, download=True, transform=transform)
    train_loader = DataLoader(train_set, batch_size=64, shuffle=True)

    model = CNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(1): # 1 epoch is enough for ~98% accuracy on MNIST
        for batch_idx, (data, target) in enumerate(train_loader):
            optimizer.zero_grad()
            output = model(data.to(device))
            loss = criterion(output, target.to(device))
            loss.backward()
            optimizer.step()
            if batch_idx % 100 == 0:
                print(f"Batch {batch_idx} Loss: {loss.item():.4f}")
    
    torch.save(model.state_dict(), "/home/cxiong/mnist_progression/mnist_cnn.pth")
    print("Model saved to /home/cxiong/mnist_progression/mnist_cnn.pth")

if __name__ == "__main__":
    train()
