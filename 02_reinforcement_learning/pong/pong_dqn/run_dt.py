import ale_py
import gymnasium as gym
import torch
from transformers import DecisionTransformerConfig, DecisionTransformerModel
import numpy as np

# Initialize Pong environment
# We MUST import ale_py before making the environment
env = gym.make("Pong-v4", render_mode=None)

# Model configuration for Atari Pong
config = DecisionTransformerConfig(
    state_dim=84 * 84, 
    act_dim=6,         
    id_dim=0,          
    max_episode_seq_len=1000,
    pred_horizon=1,
    max_target_return=21.0, 
    n_layers=3,
    n_heads=4,
    d_model=128,
    d_inner=512,
)

print("Loading Decision Transformer from Hugging Face...")
model = DecisionTransformerModel.from_pretrained("edbeeching/decision_transformer_atari", config=config)
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print(f"Model loaded and moved to {device}")

def play_game():
    obs, _ = env.reset()
    done = False
    total_reward = 0
    
    history_states = []
    history_actions = []
    
    step = 0
    while not done:
        # Preprocess observation
        state = np.mean(obs, axis=2).astype(np.float32) / 255.0
        state = np.resize(state, (84, 84)).flatten()
        state_tensor = torch.tensor(state, device=device).unsqueeze(0)
        
        history_states.append(state_tensor)
        if len(history_states) > config.max_episode_seq_len:
            history_states.pop(0)
            
        if len(history_actions) == 0:
            states = torch.stack([state_tensor] * 1).transpose(0, 1)
            actions = torch.zeros((1, 1, config.act_dim), device=device)
            returns = torch.ones((1, 1), device=device) * 21.0
        else:
            states = torch.stack(history_states[-config.max_episode_seq_len:]).unsqueeze(0).transpose(0, 1)
            actions = torch.stack(history_actions[-config.max_episode_seq_len:]).unsqueeze(0).transpose(0, 1)
            returns = torch.ones((1, len(history_states)), device=device) * 21.0

        with torch.no_grad():
            output = model(states=states, actions=actions, returns=returns)
            action_logits = output.action_preds[:, -1, :]
            action = torch.argmax(action_logits, dim=-1).item()
        
        obs, reward, terminated, truncated, info = env.step(action)
        history_actions.append(torch.tensor([action], device=device).unsqueeze(0))
        
        total_reward += reward
        done = terminated or truncated
        step += 1
        
        if step % 100 == 0:
            print(f"Step: {step} | Current Reward: {total_reward}")

    print(f"Game Finished! Total Reward: {total_reward}")

if __name__ == "__main__":
    play_game()
