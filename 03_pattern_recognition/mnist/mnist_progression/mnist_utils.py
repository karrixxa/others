
import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import numpy as np
import os

ARTIFACTS_DIR = "/home/cxiong/mnist_progression/artifacts"
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def get_mnist_loaders(batch_size=64):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    
    train_set = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
    test_set = datasets.MNIST(root='./data', train=False, download=True, transform=transform)
    
    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_set, batch_size=batch_size, shuffle=False)
    
    return train_loader, test_loader, test_set

def plot_misclassified(model, test_loader, num_examples=9):
    model.eval()
    images, labels = [], []
    preds = []
    
    with torch.no_grad():
        for data, target in test_loader:
            # MLP expects flattened, CNN expects spatial. 
            # We handle this in the specific stage scripts.
            # Here we assume the model has a 'predict' method or we handle logic outside.
            pass

def save_plot(plt_obj, filename):
    path = os.path.join(ARTIFACTS_DIR, filename)
    plt_obj.savefig(path)
    plt.close()
    return path
