"""
Vision Transformer (ViT) on MNIST — Concept first
─────────────────────────────────────────────────────────────────────────────
What this does:
  Trains a Vision Transformer to recognize the same handwritten digits,
  but using a completely different mechanism than the CNN.

How it differs from CNN:
  CNN   → slides local filters across the image (local, spatial)
  ViT   → splits image into patches, then uses attention to find
          relationships between ALL patches simultaneously (global)

The attention mechanism asks:
  "For each patch of the image, which other patches matter most
   for understanding what digit this is?"

This is closer to how the prefrontal cortex works — integrating
information from across the whole input, not just local neighborhoods.

Run:
  python3 vit_mnist.py
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

torch.manual_seed(42)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\nUsing device: {device}")

# ── Data ──────────────────────────────────────────────────────────────────────
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.1307,), (0.3081,))
])

print("Loading MNIST...")
train_data = torchvision.datasets.MNIST('./data', train=True,  download=True, transform=transform)
test_data  = torchvision.datasets.MNIST('./data', train=False, download=True, transform=transform)
train_loader = torch.utils.data.DataLoader(train_data, batch_size=64, shuffle=True)
test_loader  = torch.utils.data.DataLoader(test_data,  batch_size=1000)

# ── Transformer building blocks ───────────────────────────────────────────────

class PatchEmbedding(nn.Module):
    """
    Step 1: Split the image into patches and embed them.

    A 28x28 MNIST image gets split into small patches (e.g. 7x7 pixels each).
    That gives us 16 patches (4x4 grid).

    Each patch is flattened and projected into an embedding vector.
    This is like tokenizing — each patch becomes a "word" in a sequence.

    Then we add a special [CLS] token at the start (borrowed from BERT).
    The CLS token learns to summarize the whole image for classification.

    We also add positional embeddings — the transformer has no built-in
    sense of position, so we tell it where each patch came from.
    """
    def __init__(self, img_size=28, patch_size=7, in_channels=1, embed_dim=64):
        super().__init__()
        self.patch_size  = patch_size
        self.n_patches   = (img_size // patch_size) ** 2   # 16 patches
        patch_dim        = in_channels * patch_size * patch_size  # 49

        # Linear projection of each flattened patch → embedding vector
        self.projection  = nn.Linear(patch_dim, embed_dim)

        # Learnable [CLS] token — added to front of sequence
        self.cls_token   = nn.Parameter(torch.zeros(1, 1, embed_dim))

        # Learnable positional embeddings — one per patch + CLS
        self.pos_embed   = nn.Parameter(torch.zeros(1, self.n_patches + 1, embed_dim))

    def forward(self, x):
        B = x.size(0)   # batch size
        p = self.patch_size

        # Split into patches manually
        # x: [B, 1, 28, 28] → patches: [B, 16, 49]
        x = x.unfold(2, p, p).unfold(3, p, p)          # [B, 1, 4, 4, 7, 7]
        x = x.contiguous().view(B, -1, p * p)           # [B, 16, 49]

        # Project each patch to embedding dimension
        x = self.projection(x)                          # [B, 16, 64]

        # Prepend CLS token
        cls = self.cls_token.expand(B, -1, -1)          # [B, 1, 64]
        x   = torch.cat([cls, x], dim=1)                # [B, 17, 64]

        # Add positional information
        x   = x + self.pos_embed                        # [B, 17, 64]
        return x


class MultiHeadAttention(nn.Module):
    """
    The core of the transformer — attention.

    For each patch (token), attention computes how much it should
    "pay attention to" every other patch when building its representation.

    Multi-head: we run several attention operations in parallel,
    each looking for different kinds of relationships.
    This is like having multiple "aspects" of a scene analyzed at once.

    The math:
      Attention(Q, K, V) = softmax(QK^T / sqrt(d)) V
      Q = query  (what am I looking for?)
      K = key    (what do I contain?)
      V = value  (what information do I carry?)
    """
    def __init__(self, embed_dim=64, n_heads=4):
        super().__init__()
        self.n_heads  = n_heads
        self.head_dim = embed_dim // n_heads
        self.scale    = self.head_dim ** -0.5

        self.qkv  = nn.Linear(embed_dim, embed_dim * 3)
        self.proj = nn.Linear(embed_dim, embed_dim)

    def forward(self, x):
        B, N, C = x.shape
        # Project to Q, K, V
        qkv = self.qkv(x).reshape(B, N, 3, self.n_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]

        # Scaled dot-product attention
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)

        # Weighted sum of values
        x = (attn @ v).transpose(1, 2).reshape(B, N, C)
        x = self.proj(x)
        return x, attn   # return attention weights for visualization


class TransformerBlock(nn.Module):
    """
    One transformer block = attention + feedforward + residual connections.

    Residual connections (x = x + ...) are crucial — they let gradients
    flow cleanly during training and allow deep networks to work.
    LayerNorm stabilizes training.
    """
    def __init__(self, embed_dim=64, n_heads=4, mlp_ratio=4):
        super().__init__()
        self.norm1 = nn.LayerNorm(embed_dim)
        self.attn  = MultiHeadAttention(embed_dim, n_heads)
        self.norm2 = nn.LayerNorm(embed_dim)
        mlp_dim    = embed_dim * mlp_ratio
        self.mlp   = nn.Sequential(
            nn.Linear(embed_dim, mlp_dim),
            nn.GELU(),
            nn.Linear(mlp_dim, embed_dim),
        )
        self.last_attn = None   # store for visualization

    def forward(self, x):
        # Attention with residual
        attn_out, attn_weights = self.attn(self.norm1(x))
        self.last_attn = attn_weights.detach()
        x = x + attn_out
        # Feedforward with residual
        x = x + self.mlp(self.norm2(x))
        return x


class VisionTransformer(nn.Module):
    """
    Full ViT:
      PatchEmbedding → N x TransformerBlock → classify from CLS token
    """
    def __init__(self, img_size=28, patch_size=7, in_channels=1,
                 embed_dim=64, depth=4, n_heads=4, n_classes=10):
        super().__init__()
        self.patch_embed = PatchEmbedding(img_size, patch_size, in_channels, embed_dim)
        self.blocks      = nn.ModuleList([
            TransformerBlock(embed_dim, n_heads) for _ in range(depth)
        ])
        self.norm        = nn.LayerNorm(embed_dim)
        self.head        = nn.Linear(embed_dim, n_classes)

    def forward(self, x):
        x = self.patch_embed(x)
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        # Use only the CLS token for classification
        cls = x[:, 0]
        return self.head(cls)

    def get_attention(self):
        """Return attention weights from last block for visualization."""
        return self.blocks[-1].last_attn


# ── Build model ───────────────────────────────────────────────────────────────
model = VisionTransformer().to(device)
print(f"\nModel architecture:")
print(model)
total_params = sum(p.numel() for p in model.parameters())
print(f"\nTotal parameters: {total_params:,}")
print("(ViT typically needs more params than CNN for MNIST)")

# ── Training ──────────────────────────────────────────────────────────────────
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=10)

EPOCHS = 10
train_losses    = []
test_accuracies = []

print(f"\nTraining for {EPOCHS} epochs...")
print(f"{'Epoch':<8} {'Loss':<12} {'Test Accuracy'}")
print("─" * 35)

for epoch in range(1, EPOCHS + 1):
    model.train()
    running_loss = 0.0
    for images, labels in train_loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    scheduler.step()
    avg_loss = running_loss / len(train_loader)
    train_losses.append(avg_loss)

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

torch.save(model.state_dict(), "vit_mnist.pth")
print("Model saved to vit_mnist.pth")

# ── Visualizations ────────────────────────────────────────────────────────────
print("\nGenerating visualizations...")
os.makedirs("plots", exist_ok=True)

# 1. Training curve
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(train_losses, 'b-o', markersize=4)
plt.title("ViT Training Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss")
plt.grid(True, alpha=0.3)
plt.subplot(1, 2, 2)
plt.plot(test_accuracies, 'g-o', markersize=4)
plt.title("ViT Test Accuracy (%)"); plt.xlabel("Epoch"); plt.ylabel("Accuracy %")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("plots/vit_training_curve.png", dpi=120)
print("  Saved: plots/vit_training_curve.png")

# 2. Attention maps — what does the model look at?
# This is the most interesting visualization for ViT
# Shows which patches the CLS token attends to for each image
model.eval()
batch = next(iter(test_loader))
images, labels = batch
images = images[:8].to(device)

with torch.no_grad():
    outputs = model(images)
    _, predicted = outputs.max(1)
    attn = model.get_attention()   # [B, heads, 17, 17]

# Average attention from CLS token to all patches, across heads
# attn[:, :, 0, 1:] = attention from CLS (pos 0) to each patch (pos 1-16)
cls_attn = attn[:, :, 0, 1:].mean(dim=1)   # [B, 16] — avg over heads
cls_attn = cls_attn.cpu().numpy()

fig, axes = plt.subplots(2, 8, figsize=(14, 5))
fig.suptitle("Attention Maps — where the ViT looks when classifying\n"
             "Top: input image   Bottom: attention heatmap (4x4 patches)", fontsize=10)

for i in range(8):
    # Top row: original image
    axes[0, i].imshow(images[i].cpu().squeeze(), cmap='gray')
    c = predicted[i].item() == labels[i].item()
    axes[0, i].set_title(f"pred:{predicted[i].item()}", fontsize=8,
                         color='green' if c else 'red')
    axes[0, i].axis('off')

    # Bottom row: attention map reshaped to 4x4 patch grid
    attn_map = cls_attn[i].reshape(4, 4)
    axes[1, i].imshow(attn_map, cmap='hot', interpolation='nearest')
    axes[1, i].axis('off')

plt.tight_layout()
plt.savefig("plots/vit_attention_maps.png", dpi=120)
print("  Saved: plots/vit_attention_maps.png")

# 3. Comparison summary
print(f"\n{'─'*40}")
print("CNN vs ViT on MNIST — Summary")
print(f"{'─'*40}")
print(f"ViT final accuracy : {test_accuracies[-1]:.2f}%")
print(f"ViT parameters     : {total_params:,}")
print(f"\nKey differences:")
print("  CNN  — local filters, translation equivariant, data efficient")
print("  ViT  — global attention, position aware, needs more data/epochs")
print("\nCheck plots/vit_attention_maps.png to see what the model attends to.")
print("Brighter patches = the model paid more attention there.")
