# Project Technical Report: Perception-Enhanced Pong Imitation & Evolution

## 1. Objective
The goal of this project was to develop a high-performance Atari Pong agent by bridging the gap between **Supervised Imitation Learning (SL)** and **Reinforcement Learning (RL)**. The core hypothesis was that starting an RL agent with a "pretrained" imitation brain would significantly accelerate convergence and result in a more stable, strategic player.

## 2. Architectural Innovation: Perception-Enhanced Vision
To reduce the complexity of the learning task, we moved away from raw RGB pixels. We implemented a custom **Perception Wrapper** that provides a 6-channel observation space:
- **Temporal Context (4 Frames)**: A stack of the four most recent grayscale frames to provide the model with velocity and direction of the ball.
- **Motion Map (1 Channel)**: A derived channel calculated as the absolute difference between frames, highlighting moving objects and reducing static background noise.
- **Paddle Marker (1 Channel)**: A binary mask pinpointing the exact location of the player's paddle.

**Architectural Insight**: By engineering the input space, we transformed the problem from "discovering where the ball is" to "deciding how to react to the ball's movement."

## 3. The Implementation Pipeline

### Phase 1 & 2: Expert Trajectory Extraction
Generic pre-trained models from the HuggingFace Hub were tested but rejected due to version incompatibilities and poor performance (rewards around -21). We pivoted to a **custom PPO Master agent**, extracting 100,000 frames of high-quality expert trajectories to serve as the "textbook" for the student.

### Phase 3 & 4: Supervised Mimicry (The Student)
A CNN was trained to predict the expert's actions based on the 6-channel input. 
- **The "Pro" Student**: Trained to 95% accuracy, providing a baseline of expert-level mimicry.
- **The "Lite" Student**: Trained to ~66% accuracy to serve as a "semi-low" starting point for RL evolution.

### Phase 5: Closed-Loop Verification
To bypass rendering bugs in the standard `human` mode, we implemented a custom **OpenCV-based evaluation pipeline**. This allowed for real-time verification of agent behavior and visual confirmation of the Perception Wrapper's accuracy.

### Phase 6: RL Evolution (PPO Fine-Tuning)
We transitioned the Student agents into a PPO (Proximal Policy Optimization) framework. 
- **The Breakthrough**: The "Lite" agent initially plateaued at a reward of -10.8. By implementing a **"Breakout Strategy"** (increasing the entropy coefficient to $\text{0.05}$ and learning rate to $\text{5e-5}$), we forced the agent to move past the local optimum of "safe play" toward active winning.

## 4. Key Engineering Lessons

### The "Patience Protocol" in RL
A critical discovery was the non-linear nature of RL rewards. The "plateau" at -10.8 was not a failure, but a necessary phase of exploration. The project demonstrated that stability in hyperparameters is often more valuable than frequent adjustments.

### Imitation vs. RL
- **Imitation**: Provides a fast, stable start but is limited by the teacher's ceiling.
- **RL**: Slow and unstable initially, but capable of discovering optimal strategies that exceed the teacher.
- **Hybrid Approach**: The most effective path is using SL for the "warm start" and RL for the "polish."

## 5. Final Results
- **Imitation Accuracy**: 95.09%
- **RL Progress**: The agent evolved from a baseline of -10.8 to a current mean reward of **-6.19** and climbing.
- **GitHub Repository**: Organized into a modular pipeline for reproducibility and scalability.
