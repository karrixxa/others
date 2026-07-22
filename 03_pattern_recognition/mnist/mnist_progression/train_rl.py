import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# For RL/Policy-based approach in MNIST, we typically treat it as a classification problem 
# where the "action" is picking the correct digit. A simple Policy Network is essentially an MLP.
class PolicyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Flatten(),
            nn.Linear(28 * 28, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 10),
            nn.Softmax(dim=1)
        )
    def forward(self, x):
        return self.network(x)

def train():
    device = torch.device("cpu")
    transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
    train_set = datasets.MNIST(root='/home/cxiong/mnist_progression/data', train=True, download=True, transform=transform)
    train_loader = DataLoader(train_set, batch_size=64, shuffle=True)

    model = PolicyNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.NLLLoss() # Using negative log likelihood for policy gradient style

    model.train()
    for epoch in range(2):
        for batch_idx, (data, target) in enumerate(train_loader):
            optimizer.zero_grad()
            # Get log probabilities
            probs = model(data.to(device))
            log_probs = torch.log(probs + 1e-9)
            
            # We want to maximize the probability of the correct digit
            # loss = -log(prob of correct action)
            loss = criterion(log_probs, target.to(device))
            loss.backward()
            optimizer.step()
            if batch_idx % 200 == 0:
                print(f"Epoch {epoch} Batch {batch_idx} Loss: {loss.item():.4f}")
    
    torch.save(model.state_dict(), "/home/cxiong/mnist_progression/mnist_rl.pth")
    print("RL/Policy Model saved to /home/cxiong/mnist_progression/mnist_rl.pth")

if __name__ == "__main__":
    train()
