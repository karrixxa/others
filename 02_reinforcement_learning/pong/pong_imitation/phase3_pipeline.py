import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import os

class PongExpertDataset(Dataset):
    def __init__(self, npz_path):
        print(f"Loading expert data from {npz_path}...")
        data = np.load(npz_path)
        
        # X: (Num_Steps, 6, 84, 84), Y: (Num_Steps,)
        self.X = torch.from_numpy(data['X']).float()
        self.Y = torch.from_numpy(data['Y']).long()
        
        print(f"Dataset loaded. X shape: {self.X.shape}, Y shape: {self.Y.shape}")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.Y[idx]

def get_dataloader(npz_path, batch_size=64, shuffle=True):
    dataset = PongExpertDataset(npz_path)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, num_workers=4)
    return loader

if __name__ == "__main__":
    # Test the pipeline
    npz_path = "/home/cxiong/pong_imitation/expert_data.npz"
    if not os.path.exists(npz_path):
        print(f"Error: {npz_path} not found")
    else:
        loader = get_dataloader(npz_path)
        # Fetch one batch to verify
        X_batch, Y_batch = next(iter(loader))
        print(f"Batch verification successful:")
        print(f"X batch shape: {X_batch.shape}") # Expect (64, 6, 84, 84)
        print(f"Y batch shape: {Y_batch.shape}") # Expect (64,)
        print(f"X dtype: {X_batch.dtype}, Y dtype: {Y_batch.dtype}")
