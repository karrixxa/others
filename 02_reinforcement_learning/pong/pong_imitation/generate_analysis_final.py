
import matplotlib.pyplot as plt
import numpy as np
import os

# Data based on project logs
phases = ['Lite Student', 'RL Plateau', 'RL Master']
rewards = [-21.0, -10.8, 0.822] 
accuracy = [66.4, 91.2, 95.1]

plt.style.use('dark_background')
plt.figure(figsize=(12, 5))

# Plot 1: Reward Evolution
plt.subplot(1, 2, 1)
plt.plot(phases, rewards, marker='o', linestyle='-', color='#00ffcc', linewidth=2, markersize=8)
plt.axhline(y=0, color='white', linestyle='--', alpha=0.5)
plt.title('Agent Reward Evolution', fontsize=14)
plt.ylabel('Mean Reward', fontsize=12)
plt.grid(True, alpha=0.3)

# Plot 2: Imitation Accuracy
plt.subplot(1, 2, 2)
plt.bar(phases, accuracy, color=['#444444', '#555555', '#00ffcc'])
plt.title('Imitation Accuracy (%)', fontsize=14)
plt.ylabel('Accuracy', fontsize=12)
plt.ylim(0, 100)
plt.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('/home/cxiong/pong_imitation/quantitative_analysis.png', dpi=300)
print("Successfully saved quantitative_analysis.png")
