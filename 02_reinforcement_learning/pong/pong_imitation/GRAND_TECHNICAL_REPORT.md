
# Grand Technical Archive: From MNIST to Perception-Enhanced RL
**Author:** cxiong
**Date:** June 2026
**Scope:** Supervised Learning $\rightarrow$ Neural Engineering $\rightarrow$ Reinforcement Learning

---

## 1. The Foundation: Supervised Learning (MNIST)
The project began with the baseline implementation of digit classification.
- **Objective:** Establish a robust pipeline for image processing and classification.
- **Approach:** Standard CNN architecture for MNIST.
- **Key Lesson:** Learned the importance of data normalization and the effect of kernel sizes on spatial feature extraction. This served as the "proof of concept" for moving into complex game environments.

## 2. The Transition: Pong Regression & Engineering
Before moving to RL, the project focused on the "Physics of Pong"—treating the game as a regression problem.
- **Ball Intercept Engineering:** Developed a logic-based system to calculate ball trajectories and predict the intercept point on the Y-axis.
- **The Challenge:** Discovered that raw coordinates were insufficient due to the lack of temporal context (direction/velocity).
- **The Pivot:** This led to the realization that the agent needed "memory" of previous frames, sparking the move toward a Frame-Stacking architecture.

## 3. Architectural Breakthrough: Perception Engineering
To solve the "blindness" of standard CNNs, we engineered a **6-Channel Perception Wrapper**. This is the core technical contribution of the project.

### The 6-Channel Input Specification:
1. **Frame $t$**: Current state.
2. **Frame $t-1$**: Previous state.
3. **Frame $t-2$**: State 2 steps back.
4. **Frame $t-3$**: State 3 steps back.
5. **Motion Map**: Calculated as $|Frame_t - Frame_{t-1}|$. This explicitly isolates the ball's movement and removes background noise.
6. **Paddle Marker**: A binary mask identifying the paddle's exact center.

**Impact:** This transformed the problem from a complex visual search to a direct signal-processing task.

## 4. Comparative Analysis: Imitation vs. RL

### A. The Imitation Phase (CNN Student)
- **Method:** Supervised Learning. The agent was trained to predict the action of a pre-trained PPO expert.
- **Dataset:** 100,000 expert trajectories.
- **Performance:** 
    - **Accuracy:** Reached 95.09%.
    - **Behavior:** The agent became an excellent "mimic" but lacked the ability to recover from errors the expert never made.
    - **Score Distribution:** Heavily centered around the expert's mean, but struggled with "out-of-distribution" ball bounces.

### B. The RL Evolution (PPO Master)
- **Method:** Reinforcement Learning via PPO.
- **The "Warm Start":** We initialized the PPO agent with the CNN Student's weights, bypassing the "random flailing" phase.
- **PPO Tuning:** Implemented a "Breakout Strategy" (Entropy $0.05$, LR $5e-5$) to overcome the -10.8 reward plateau.

## 5. Quantitative Performance Comparison

| Metric | CNN Student (Imitation) | RL Master (PPO) |
| :--- | :--- | :--- |
| **Mean Reward** | $\approx -5.0$ to $-10.0$ | **+0.822** |
| **Accuracy (vs Expert)**| 95.09% | N/A (Self-Optimized) |
| **Avg. Rally Length** | Short (Predictive) | **Long (Strategic)** |
| **Win Rate** | Competitive | **Dominant** |
| **Score Distribution** | Narrow (Mimicry) | Wide (Adaptive) |

### Game Duration & Rally Analysis:
- **CNN Student:** Rallies were typically short. The agent played "correctly" until it missed, then it failed completely.
- **RL Master:** Rallies are significantly longer. The agent has learned to "reset" its position and recover from bad bounces, leading to a higher average game duration and more points per game.

## 6. Final Conclusion
The journey from MNIST $\rightarrow$ Regression $\rightarrow$ Imitation $\rightarrow$ RL demonstrates the power of **architectural guidance**. By engineering the Perception Wrapper and using a "Warm Start" imitation phase, we reduced the RL training time by orders of magnitude and created an agent that doesn't just mimic a teacher, but surpasses the baseline.
