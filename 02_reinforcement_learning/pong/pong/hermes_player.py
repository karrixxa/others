
import asyncio
import json
import numpy as np
import torch
import torch.nn as nn
import websockets

# Import the same model structure as the trainer
class DQN(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(DQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim)
        )

    def forward(self, x):
        return self.net(x)

async def play():
    uri = "ws://localhost:8765"
    # Model parameters
    state_dim = 5
    action_dim = 3
    
    model = DQN(state_dim, action_dim)
    try:
        model.load_state_dict(torch.load("hermes_brain.pth"))
        print("Brain loaded successfully.")
    except FileNotFoundError:
        print("Brain file not found. Please run train_agent.py first.")
        return

    model.eval()
    
    async with websockets.connect(uri) as ws:
        print("Connected to Pong server. I am now your opponent!")
        
        # Game state tracking
        last_state = None
        
        while True:
            # 1. Receive current state
            raw = await ws.recv()
            data = json.loads(raw)
            
            if data["type"] == "state":
                s = data
                # Extract observation: [ai_paddle_y, ball_x, ball_y, ball_vx, ball_vy]
                # Note: We have to infer vx/vy or have the server send them.
                # Looking at logic.py: state() only returns x, y.
                # We need to check if the server sends vx, vy.
                # It DOES NOT. We must track the ball position over time to estimate velocity.
                
                if last_state is None:
                    last_state = s
                    continue
                
                # Estimate velocity
                vx = s["ball"]["x"] - last_state["ball"]["x"]
                vy = s["ball"]["y"] - last_state["ball"]["y"]
                
                # Normalize for the model
                obs = np.array([
                    (s["ai"]["y"] / 600) * 2 - 1,
                    (s["ball"]["x"] / 800) * 2 - 1,
                    (s["ball"]["y"] / 600) * 2 - 1,
                    vx / 14.0,
                    vy / 14.0
                ], dtype=np.float32)
                
                last_state = s
                
                # 2. Predict Action
                state_t = torch.FloatTensor(obs).unsqueeze(0)
                with torch.no_grad():
                    q_values = model(state_t)
                action = torch.argmax(q_values).item()
                
                # 3. Send Move
                dy = 0
                if action == 1: dy = -6.0 # Up
                if action == 2: dy = 6.0  # Down
                
                await ws.send(json.dumps({"action": "ai_move", "dy": dy}))

if __name__ == "__main__":
    asyncio.run(play())
