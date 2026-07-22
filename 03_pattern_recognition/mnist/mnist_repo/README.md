# AI Agent Portfolio: From Digit Recognition to Imitation Learning

This repository contains a series of machine learning projects exploring the transition from basic supervised classification to complex reinforcement learning (RL) agents.

## 🚀 Projects Overview

### 1. MNIST Digit Classification
An exploration of computer vision basics. This project implements a neural network to classify handwritten digits, focusing on:
- **Architecture**: Convolutional Neural Networks (CNNs).
- **Dataset**: MNIST handwritten digits.
- **Goal**: Achieving high accuracy in digit recognition through iterative model tuning.

### 2. Pong Imitation Learning Pipeline
A sophisticated RL project that implements a "Teacher-Student" framework to create a high-performing Atari Pong agent without the need for millions of frames of random exploration.

#### 🛠 The Architectural Approach (The "Architect's" Plan)
Instead of training from scratch, this project uses a 5-Phase pipeline:
- **Phase 1 & 2: Expert Extraction**: Using a pre-trained PPO "Master" agent to generate 100,000 frames of professional gameplay.
- **Phase 3: Data Pipeline**: Building a PyTorch pipeline to handle high-dimensional observation data.
- **Phase 4: Supervised Mimicry**: Training a Student CNN to predict the Master's actions with >95% accuracy.
- **Phase 5: Closed-Loop Evaluation**: A custom OpenCV-based renderer to verify the agent's performance in real-time.
- **Phase 6: RL Evolution**: Fine-tuning the Student agent using PPO to evolve from a "mimic" into a "master."

#### 👁️ Perception-Enhanced Vision
To improve learning efficiency, the agent does not see raw pixels. It uses a custom **Perception Wrapper** providing 6 channels:
- **4 Frame Stack**: For temporal awareness (velocity and direction).
- **Motion Map**: Highlighting changes between frames to isolate the ball.
- **Paddle Marker**: A dedicated channel to pinpoint the player's paddle location.

## ⚙️ Installation & Usage

### Prerequisites
- Python 3.12+
- Gymnasium & ALE (Atari Learning Environment)
- PyTorch

### Setup
```bash
# Clone the repo
git clone git@faraday.lps.umd.edu:cxiong/charis.git
cd charis

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install torch gymnasium[atari,accept-rom-license] stable-baselines3 opencv-python numpy
```

### Running the Pong Pipeline
Run the phases in order to rebuild the agent:
1. `python pong_imitation/phase2_collect_ppo.py` (Collect Expert Data)
2. `python pong_imitation/phase3_train_cnn.py` (Train Student)
3. `python pong_imitation/phase5_evaluate_cv2.py` (Watch the Agent play)
4. `python pong_imitation/phase6_rl_lite_evolve.py` (Evolve via RL)

## 🧠 Key Learning Outcomes
- **Imitation vs. RL**: Understanding the trade-off between fast convergence (Imitation) and peak performance (RL).
- **Perception Engineering**: Learning how to augment input data to simplify a model's learning task.
- **System Architecture**: Designing a modular pipeline that allows for "Warm Starts" and iterative improvement.
