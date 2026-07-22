"""
CNN on MNIST — Concept first
─────────────────────────────────────────────────────────────────────────────
What this does:
  Trains a Convolutional Neural Network to recognize handwritten digits 0-9.

Why it matters:
  A CNN mirrors the visual cortex hierarchy we discussed:
    Conv layer 1  →  edge detectors    (like V1 neurons)
    Conv layer 2  →  shapes/curves     (like V2/V4)
    Fully connected → digit category   (like IT cortex)

  After training you can literally visualize layer 1 filters and see
  they look like oriented edge detectors — same as biological V1.

Run:
  python3 cnn_mnist.py
─────────────────────────────────────────────────────────────────────────────
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import numpy as np
import os

# ── Reproducibility ───────────────────────────────────────────────────────────
torch.manual_seed(42)

# ── Device ────────────────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\nUsing device: {device}")

# ── Data ──────────────────────────────────────────────────────────────────────
# MNIST: 70,000 grayscale 28x28 images of handwritten digits 0-9
# normalize to mean=0.1307, std=0.3081 (pre-computed for MNIST)
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

print("\nDownloading MNIST dataset (first run only)...")
train_data = torchvision.datasets.MNIST('./data', train=True,  download=True, transform=transform)
test_data  = torchvision.datasets.MNIST('./data', train=False, download=True, transform=transform)

train_loader = torch.utils.data.DataLoader(train_data, batch_size=64, shuffle=True)
test_loader  = torch.utils.data.DataLoader(test_data,  batch_size=1000)

print(f"Training samples : {len(train_data):,}")
print(f"Test samples     : {len(test_data):,}")
print(f"Image size       : 28x28 pixels, 1 channel (grayscale)")

# ── Model ─────────────────────────────────────────────────────────────────────
class CNN(nn.Module):
    """
    Two convolutional layers followed by two fully connected layers.

    Input:  [batch, 1, 28, 28]  — grayscale 28x28 image
    Output: [batch, 10]         — score for each digit 0-9

    Architecture:
      Conv1 → ReLU → MaxPool   edge detectors (like V1)
      Conv2 → ReLU → MaxPool   shape detectors (like V2/V4)
      Flatten
      FC1   → ReLU             high level features (like IT cortex)
      FC2                      final digit scores
    """
    def __init__(self):
        super().__init__()

        # First conv layer:
        # - 1 input channel (grayscale)
        # - 32 filters, each 3x3 pixels
        # - Each filter learns to detect a different edge/pattern
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, padding=1)

        # Second conv layer:
        # - 32 input channels (from conv1)
        # - 64 filters — learns combinations of edges = shapes
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)

        # MaxPool halves the spatial size each time (28→14→7)
        self.pool  = nn.MaxPool2d(2, 2)

        # ReLU: anything negative becomes 0 — adds non-linearity
        self.relu  = nn.ReLU()

        # Dropout: randomly zeroes 25% of neurons during training
        # prevents overfitting (memorizing instead of generalizing)
        self.drop  = nn.Dropout(0.25)

        # Fully connected layers
        # After 2x pool: 64 channels × 7 × 7 spatial = 3136
        self.fc1   = nn.Linear(64 * 7 * 7, 128)
        self.fc2   = nn.Linear(128, 10)   # 10 output classes (digits 0-9)

    def forward(self, x):
        # x shape: [batch, 1, 28, 28]
        x = self.pool(self.relu(self.conv1(x)))  # → [batch, 32, 14, 14]
        x = self.pool(self.relu(self.conv2(x)))  # → [batch, 64,  7,  7]
        x = self.drop(x)
        x = x.view(x.size(0), -1)               # flatten → [batch, 3136]
        x = self.relu(self.fc1(x))               # → [batch, 128]
        x = self.drop(x)
        x = self.fc2(x)                          # → [batch, 10]
        return x

model = CNN().to(device)
print(f"\nModel architecture:")
print(model)
total_params = sum(p.numel() for p in model.parameters())
print(f"\nTotal parameters: {total_params:,}")

# ── Training ──────────────────────────────────────────────────────────────────
# CrossEntropyLoss: measures how wrong the model's digit predictions are
# Adam: adaptive optimizer — adjusts learning rate automatically
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

EPOCHS = 5
train_losses = []
test_accuracies = []

print(f"\nTraining for {EPOCHS} epochs...")
print(f"{'Epoch':<8} {'Loss':<12} {'Test Accuracy'}")
print("─" * 35)

for epoch in range(1, EPOCHS + 1):
    # ── train ──────────────────────────────────────────────────────────────
    model.train()
    running_loss = 0.0
    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()          # clear old gradients
        outputs = model(images)        # forward pass
        loss = criterion(outputs, labels)
        loss.backward()                # backprop — compute gradients
        optimizer.step()               # update weights
        running_loss += loss.item()

    avg_loss = running_loss / len(train_loader)
    train_losses.append(avg_loss)

    # ── evaluate ───────────────────────────────────────────────────────────
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for images, labels in test_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            correct += (predicted == labels).sum().item()
            total   += labels.size(0)

    accuracy = 100 * correct / total
    test_accuracies.append(accuracy)
    print(f"{epoch:<8} {avg_loss:<12.4f} {accuracy:.2f}%")

print(f"\nFinal test accuracy: {test_accuracies[-1]:.2f}%")
print("(Human-level on MNIST is ~98-99%)")

# ── Save model ────────────────────────────────────────────────────────────────
torch.save(model.state_dict(), "cnn_mnist.pth")
print("\nModel saved to cnn_mnist.pth")

# ── Visualizations ────────────────────────────────────────────────────────────
print("\nGenerating visualizations...")
os.makedirs("plots", exist_ok=True)

# 1. Training curve
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(train_losses, 'b-o', markersize=4)
plt.title("Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.grid(True, alpha=0.3)

plt.subplot(1, 2, 2)
plt.plot(test_accuracies, 'g-o', markersize=4)
plt.title("Test Accuracy (%)"); plt.xlabel("Epoch"); plt.ylabel("Accuracy %")
plt.ylim([95, 100]); plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("plots/training_curve.png", dpi=120)
print("  Saved: plots/training_curve.png")

# 2. Conv1 filters — this is the interesting one
# These should look like oriented edge detectors (Gabor filters)
# exactly like V1 neurons in the visual cortex
filters = model.conv1.weight.data.cpu()   # shape: [32, 1, 3, 3]
fig, axes = plt.subplots(4, 8, figsize=(12, 6))
fig.suptitle("Conv Layer 1 Filters — learned edge detectors\n(compare to V1 oriented receptive fields)", 
             fontsize=11)
for i, ax in enumerate(axes.flat):
    f = filters[i, 0].numpy()
    ax.imshow(f, cmap='RdBu_r', interpolation='nearest')
    ax.axis('off')
plt.tight_layout()
plt.savefig("plots/conv1_filters.png", dpi=120)
print("  Saved: plots/conv1_filters.png")

# 3. Sample predictions
model.eval()
examples = next(iter(test_loader))
images, labels = examples
images, labels = images[:16].to(device), labels[:16]
with torch.no_grad():
    outputs = model(images)
    _, predicted = outputs.max(1)

fig, axes = plt.subplots(2, 8, figsize=(14, 4))
fig.suptitle("Sample Predictions (green=correct, red=wrong)", fontsize=11)
for i, ax in enumerate(axes.flat):
    img = images[i].cpu().squeeze().numpy()
    ax.imshow(img, cmap='gray')
    correct = predicted[i].item() == labels[i].item()
    color   = 'green' if correct else 'red'
    ax.set_title(f"pred:{predicted[i].item()}\ntrue:{labels[i].item()}",
                 fontsize=8, color=color)
    ax.axis('off')
plt.tight_layout()
plt.savefig("plots/predictions.png", dpi=120)
print("  Saved: plots/predictions.png")

print("\nDone. Check the plots/ folder for visualizations.")
print("The conv1_filters.png is especially worth looking at —")
print("you should see oriented edge detectors, just like V1 neurons.")
