import torch
import torch.nn as nn
import torch.nn.functional as F

class PerceptionDQN(nn.Module):
    def __init__(self, action_size=6):
        super(PerceptionDQN, self).__init__()
        
        # Input: 6 channels (4 frames + 1 motion map + 1 paddle marker)
        # Standard Atari DQN architecture: 3 Conv layers
        self.conv1 = nn.Conv2d(6, 32, kernel_size=8, stride=4)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=4, stride=2)
        self.conv3 = nn.Conv2d(64, 64, kernel_size=3, stride=1)
        
        # The output of conv3 is 64 x 7 x 7 (for 84x84 input)
        # 64 * 7 * 7 = 3136
        self.fc1 = nn.Linear(64 * 7 * 7, 512)
        self.fc2 = nn.Linear(512, action_size)

    def forward(self, x):
        # x shape: (batch, 6, 84, 84)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        
        x = x.view(x.size(0), -1) # Flatten
        x = F.relu(self.fc1(x))
        return self.fc2(x) # Output: Q-values for each action

def load_pretrained_weights(model, weights_path):
    """
    Loads weights from a pretrained 4-channel DQN into our 6-channel DQN.
    """
    try:
        state_dict = torch.load(weights_path, map_location='cpu')
        # Handle cases where state_dict is wrapped in 'model' or 'state_dict' keys
        if 'model' in state_dict: state_dict = state_dict['model']
        elif 'state_dict' in state_dict: state_dict = state_dict['state_dict']
        
        # We only want to load weights for the layers that match
        # The first conv layer in pretrained is 4 channels, ours is 6.
        # We'll load the 4 channels and leave the other 2 as random.
        with torch.no_grad():
            # Conv1: Load only first 4 channels
            pretrained_conv1_weight = state_dict['conv1.weight']
            model.conv1.weight[:4, :, :, :] = pretrained_conv1_weight
            
            # Load all other layers as they match in shape
            for name, param in state_dict.items():
                if name != 'conv1.weight' and name in model.state_dict():
                    model.state_dict()[name].copy_(param)
                    
        print(f"Successfully partially loaded weights from {weights_path}")
    except Exception as e:
        print(f"Warning: Could not load pretrained weights ({e}). Starting from scratch.")
