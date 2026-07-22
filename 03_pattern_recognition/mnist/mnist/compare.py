"""
CNN vs ViT — Side by side comparison
─────────────────────────────────────────────────────────────────────────────
Run this AFTER training both models:
  python3 cnn_mnist.py
  python3 vit_mnist.py
  python3 compare.py

What this shows:
  - Accuracy comparison
  - How each model represents the same digit internally
  - What each model gets wrong (confusion matrix)
  - The fundamental difference in how they "see"
─────────────────────────────────────────────────────────────────────────────
"""

import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import numpy as np
import os

# ── Load both models ──────────────────────────────────────────────────────────
# Import architectures
from cnn_mnist import CNN
from vit_mnist import VisionTransformer

device = torch.device("cpu")

if not os.path.exists("cnn_mnist.pth"):
    print("cnn_mnist.pth not found — run cnn_mnist.py first"); exit()
if not os.path.exists("vit_mnist.pth"):
    print("vit_mnist.pth not found — run vit_mnist.py first"); exit()

cnn = CNN().to(device)
vit = VisionTransformer().to(device)
cnn.load_state_dict(torch.load("cnn_mnist.pth", map_location=device))
vit.load_state_dict(torch.load("vit_mnist.pth", map_location=device))
cnn.eval(); vit.eval()
print("Both models loaded.")

# ── Data ──────────────────────────────────────────────────────────────────────
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])
test_data   = torchvision.datasets.MNIST('./data', train=False, download=True, transform=transform)
test_loader = torch.utils.data.DataLoader(test_data, batch_size=1000)

# ── Full accuracy for both ────────────────────────────────────────────────────
def evaluate(model, loader):
    correct = total = 0
    all_pred = []; all_true = []
    with torch.no_grad():
        for images, labels in loader:
            outputs   = model(images)
            _, predicted = outputs.max(1)
            correct  += (predicted == labels).sum().item()
            total    += labels.size(0)
            all_pred.extend(predicted.numpy())
            all_true.extend(labels.numpy())
    return 100*correct/total, np.array(all_pred), np.array(all_true)

print("\nEvaluating both models on full test set...")
cnn_acc, cnn_pred, true = evaluate(cnn, test_loader)
vit_acc, vit_pred, _    = evaluate(vit, test_loader)

print(f"\nCNN accuracy : {cnn_acc:.2f}%")
print(f"ViT accuracy : {vit_acc:.2f}%")

# ── Confusion matrices ────────────────────────────────────────────────────────
os.makedirs("plots", exist_ok=True)

def confusion_matrix(pred, true, n=10):
    cm = np.zeros((n, n), dtype=int)
    for p, t in zip(pred, true):
        cm[t][p] += 1
    return cm

cnn_cm = confusion_matrix(cnn_pred, true)
vit_cm = confusion_matrix(vit_pred, true)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for ax, cm, title in zip(axes, [cnn_cm, vit_cm], ['CNN', 'ViT']):
    im = ax.imshow(cm, cmap='Blues')
    ax.set_title(f"{title} Confusion Matrix\n(row=true, col=predicted)", fontsize=11)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_xticks(range(10)); ax.set_yticks(range(10))
    for i in range(10):
        for j in range(10):
            ax.text(j, i, str(cm[i,j]), ha='center', va='center',
                    fontsize=7, color='white' if cm[i,j] > cm.max()*0.5 else 'black')
plt.tight_layout()
plt.savefig("plots/confusion_matrices.png", dpi=120)
print("  Saved: plots/confusion_matrices.png")

# ── Where they disagree ───────────────────────────────────────────────────────
# Find examples where CNN and ViT give different answers
disagree = np.where(cnn_pred != vit_pred)[0]
print(f"\nExamples where CNN and ViT disagree: {len(disagree)}")

if len(disagree) >= 8:
    fig, axes = plt.subplots(2, 8, figsize=(14, 4))
    fig.suptitle("Disagreements — CNN and ViT predict different digits\n"
                 "Green=correct  Red=wrong", fontsize=10)
    for col, idx in enumerate(disagree[:8]):
        img, label = test_data[idx]
        img_np = img.squeeze().numpy()
        cnn_p  = cnn_pred[idx]
        vit_p  = vit_pred[idx]

        axes[0, col].imshow(img_np, cmap='gray')
        axes[0, col].set_title(f"true: {label}", fontsize=8)
        axes[0, col].axis('off')

        axes[1, col].imshow(img_np, cmap='gray', alpha=0.3)
        axes[1, col].set_title(
            f"CNN:{cnn_p} {'✓' if cnn_p==label else '✗'}\n"
            f"ViT:{vit_p} {'✓' if vit_p==label else '✗'}",
            fontsize=7,
            color='gray'
        )
        axes[1, col].axis('off')

    plt.tight_layout()
    plt.savefig("plots/disagreements.png", dpi=120)
    print("  Saved: plots/disagreements.png")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"""
{'─'*50}
CNN vs ViT — What this tells us
{'─'*50}
CNN  {cnn_acc:.2f}%  — local edge detectors → shapes → digit
ViT  {vit_acc:.2f}%  — global patch attention → relationships → digit

CNN tends to be more accurate on MNIST because:
  - MNIST is a local task (digit shape is local structure)
  - CNN's inductive bias (translation equivariance) fits it well
  - Less data needed to learn useful filters

ViT tends to need more training because:
  - No built-in spatial bias — must learn position from scratch
  - Stronger on tasks requiring long-range relationships
  - Scales much better with more data (ImageNet, etc.)

Connection to neuroscience:
  CNN  ≈ feedforward visual cortex (V1→V2→V4→IT)
  ViT  ≈ attention-driven prefrontal integration
  Brain ≈ both, tightly coupled with feedback loops
{'─'*50}
""")
