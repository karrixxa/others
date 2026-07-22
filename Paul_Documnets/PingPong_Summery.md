# Agent PING-PONG Summery

**Document:** `Documents/Paper/PingPong_Summery.md`
**Period covered:** 2026-06-08 → 2026-06-16+ (per available artifacts and logs)
**Scope:** Atari Pong imitation-to-RL pipeline, web tournament deployment, symbolic PPO, and CNN StarBank DQN — not production promotion docs.

**Cross-reference:** Internship narrative in **`Internship_Summery.md`** §5 (Project A — Agent PING-PONG). Historical path `Hermes_Docs/PingPong_Game` referenced in internship sources is **missing**; this document uses the surviving workspace **`/home/prodrig/Documents/PingPong`**.

## 1. Title / meta

| Field | Value |
|---|---|
| Document name | **Agent PING-PONG Summery** (intentional spelling: Summery) |
| Period | 2026-06-08 → 2026-06-16+ |
| Primary workspace | `/home/prodrig/Documents/PingPong` |
| Historical internship path | `Hermes_Docs/PingPong_Game` — **not present** on disk |
| Version control | None (no git repository) |
| Source authority | Project files + `research_report.md` + `Internship_Summery.md` + daily/weekly summery logs |
| Cluster context | Hermes cluster, IP **10.30.0.39** (per internship Era 1–2) |

## 2. Project identity

Agent PING-PONG began as a cluster-native Pygame prototype and matured into a full imitation-to-reinforcement-learning system for Atari Pong, with a web-facing tournament layer for live play and spectator access. The through-line of the project is practical: teach an agent to play Pong well enough to hold rallies against the Atari baseline, then expose that agent over a stable client–server stack that works on shared Hermes infrastructure.

**Progress in detail**

On **2026-06-08**, work started under the original tree `Hermes_Docs/PingPong_Game` (artifacts now live in `Documents/PingPong`). A dedicated `game_env` virtualenv was created. The first shippable surface was a Pygame window with X11 forwarding so a GUI running on the cluster could render on a local machine. The UI used dynamic sizing (about half the screen), a four-row main menu (Title, Start, Credits, Quit), and a custom title asset. Alongside the game shell, a **Dynamic Discovery** system scanned `ps aux` for Hermes users who had an idle `hermes chat` session and were not busy with a task; the Lobby screen showed that live roster. This phase proved cluster logistics—display, discovery, and a playable entry point—before any serious learning stack existed.

On **2026-06-09**, research into Atari Gymnasium forced a strategic pivot. A local Pygame GUI was the wrong long-term shape for accessibility, spectators, and cluster stability. The design shifted to a **client–server web architecture**: HTML5 Canvas court, Agent Lobby panel, and Live Feed ticker, with cluster IP **10.30.0.39** and dynamic porting to avoid address-in-use conflicts. The same day, the ML spine was stood up: Gymnasium **ALE/Pong-v5**, Atari preprocessing, a HuggingFace / stable-baselines3 expert, extraction of **100,000** state–action pairs into `expert_pong_data.npz`, Behavioral Cloning on a custom CNN, then Warm-Start PPO after covariate shift made pure imitation fail in live play. Peak Warm-Start performance reached **-1.0** (see §6). Hardware audits and a brief MNIST side project ran in parallel but did not continue as Ping-PONG scope.

Through **mid-June**, the project closed the loop between training and deployment. FastAPI WebSocket servers (`server.py`, later `tournament_server.py` on fixed port **10001**) streamed match state to a browser; `agent_closed_loop.py` drove the fine-tuned PPO against the live environment. Research deliverables landed as markdown and PDF reports, architecture diagrams, and `ppo_gameplay.mp4`. Marathon PPO fine-tuning continued from `pong_ppo_finetuned.zip` with time-bounded checkpoints under `checkpoints/`.

In a **second track**, the custom headless `PongEngine` (normalized coordinates) fed a separate **CNN_Learning** DQN experiment on `StarBankEnv`, completing **500** episodes with jump-start checkpoints. A **Symbolic PPO** track (`train_symbolic_ppo.py`) bridged the Atari PPO agent to TimeLineProject symbolic memory components, producing dated checkpoints under `checkpoints/symbolic_ppo_checkpoint_*.zip`. A small DuckDuckGo search sidecar (`ddg_server.py` on port **10002**) sat beside the tournament stack as tooling, not as core gameplay.

**What the project is today.** The authoritative survivor tree is `/home/prodrig/Documents/PingPong` (no git). It preserves the expert dataset, BC and PPO weights, tournament and closed-loop web code, research PDFs, gameplay video, and both the Atari BC→PPO lineage and the StarBank DQN / Symbolic PPO extensions. The identity of Agent PING-PONG is therefore not a single script but a progression: cluster Pygame lobby → web tournament → imitation learning → warm-start RL → live closed-loop play, with optional symbolic and custom-engine DQN branches.

## 3. Framework

The framework is the set of runtime layers the project used as it moved from a local GUI to a cluster-friendly web + RL system. Each layer kept a clear job: discovery and lobby, physics or Atari simulation, learning, and browser delivery.

**Bootstrap layer (Pygame + Hermes discovery).**  
Stack: **Python**, **Pygame**, **subprocess** (`ps aux`), X11 forwarding, venv `game_env`.  
`main.py` owns START and LOBBY states. Discovery treats a user as available when they have `hermes chat` and are not running task/work/`-q` processes. This layer does not train models; it establishes how humans and agents meet on the cluster.

**Simulation layer (two environments).**  
1. **Atari path (primary for BC/PPO):** **Gymnasium**, **ALE / ale_py**, environment **ALE/Pong-v5**, wrappers **AtariPreprocessing** (grayscale 84×84, `scale_obs=False`, `frame_skip=1`) and **FrameStack** of size **4**. Used by `tournament_server.py`, `server.py`, `train_ppo.py`, and evaluation scripts.  
2. **Custom engine path (CNN_Learning):** **`PongEngine`** in `game_engine.py` — headless physics with normalized 0–1 coordinates, paddle actions NOOP/UP/DOWN, ball speed increments on hit. Wrapped by **`StarBankEnv`** for DQN with star-bank rewards and side mirroring. This path is parallel to Atari, not a drop-in replacement for the BC→PPO pipeline.

**Learning layer.**  
Stack: **PyTorch** (BC CNN, StarBank DQN), **stable-baselines3** (PPO, CnnPolicy), **HuggingFace SB3** expert weights for trajectory collection, **NumPy** for datasets and frame math. Behavioral Cloning trains a CNN on `expert_pong_data.npz`. Warm-Start PPO continues from that policy (internship sources describe a custom **HardLockedPPO** with learning rate locked at **5e-4** because SB3’s scheduler could override LR). Later marathon fine-tuning in `train_ppo.py` reloads `pong_ppo_finetuned.zip` and lowers LR to **1e-4** for long runs with `MarathonCallback` checkpoints. Symbolic training imports TimeLineProject modules (`SymbolicMemoryParser`, `TemporalAnalyzer`, `SymbolicReporter`, `PongSymbolicBridge`) into a PPO loop. The StarBank track uses a policy/target **PongCNN**, Adam, experience replay, and epsilon-greedy DQN.

**Delivery layer (web tournament and closed loop).**  
Stack: **FastAPI**, **Uvicorn**, **WebSockets**, **Pydantic**, static HTML/Canvas (`index.html`, `assets/`), optional **StaticFiles**. Fixed tournament port **10001**. The server hosts ALE Pong, accepts actions, and streams RGB / coordinate state to the browser (“AI vs CPU”). `agent_closed_loop.py` is the automated player client against that socket. A DuckDuckGo helper API on **10002** (`ddg_server.py`) is a side tool for search, not part of the Pong control loop.

**How the pieces connect.**  
Early progress used Pygame alone. After the Jun 9 pivot, Atari + SB3 became the training spine while FastAPI became the public surface. Custom `PongEngine` + DQN explored learning without ALE. Symbolic PPO tried to attach external temporal/symbolic memory to the already fine-tuned Atari agent. Declared `requirements.txt` lists only `numpy`, `pygame`, `fastapi`, `uvicorn`, `pydantic` — incomplete relative to the real stack (torch, gymnasium, ale_py, stable-baselines3, and so on), which must be read from the code and venvs.

**Network footprint.** Tournament / RL WebSocket services listen on **10001**; DDG sidecar on **10002**; cluster access historically via **10.30.0.39**.

## 4. ML pipeline

The primary learning pipeline is **expert demonstration → Behavioral Cloning → Warm-Start PPO**, built on Atari observations that give the network enough temporal context to see ball motion.

**Environment and observation.**  
Games run in Gymnasium **ALE/Pong-v5**. Each frame is converted to grayscale and resized to **84×84** via AtariPreprocessing. Four consecutive frames are stacked into a tensor of shape **(4, 84, 84)** so the CNN can infer velocity rather than only position. Pixel values used for supervised training are cast to **float32** and scaled into **[0.0, 1.0]**; uint8 left uncast breaks PyTorch training.

**Expert collection.**  
A pre-trained PPO expert (HuggingFace / stable-baselines3) is rolled out with **`deterministic=True`** so labels stay consistent for supervised learning. Trajectories are written to **`expert_pong_data.npz`**: **100,000** state–action pairs, about **15.13 MB**. That file is the sole supervised dataset for the Atari BC stage.

**Behavioral Cloning.**  
A custom CNN (three convolutional layers with BatchNorm and ReLU, then a linear head — per `research_report.md`) is trained as a classifier / imitator over the NPZ. A first “Fragile” run reached high training accuracy but collapsed in live play. The daily log for 2026-06-09 records training accuracy above **90%** while live scores remained poor — classic **covariate shift**: one mistake drives the agent into states never seen in the expert set, and errors compound. Robust BC added **random spatial shift** and **Gaussian noise** during training. The robust training log shows **15 epochs** on CUDA, accuracy climbing from ~70% (epoch 1) to **91.75%** (epoch 15). Weights are saved as **`pong_cnn_expert.pth`** (~7.29 MB).

**Warm-Start PPO.**  
The robust CNN seeds a PPO actor–critic with a CNN policy (stable-baselines3). Instead of learning Pong from scratch, PPO explores from a policy that already looks like the expert, then optimizes for environment reward. Internship notes record average scores moving from roughly **-21** toward **-10**, with a best game of **-1.0**. A custom **HardLockedPPO** forced learning rate **5e-4** when SB3’s internal scheduler tried to change it. The packaged fine-tuned agent is **`pong_ppo_finetuned.zip`** (~20.48 MB). Later marathon scripts continue from that zip with a lower LR (**1e-4**) and periodic zip checkpoints under `checkpoints/`.

**Closed-loop evaluation.**  
Live play uses the same Atari wrappers as training. The WebSocket server steps the env; the agent client sends discrete actions. Evaluation scripts such as `final_eval_ppo.py` and gameplay capture (`ppo_gameplay.mp4`) document that the warm-started agent can sustain longer rallies than pure BC.

**Parallel pipelines (not the BC→PPO spine).**  
- **Symbolic PPO:** loads `pong_ppo_finetuned.zip`, attaches TimeLineProject symbolic bridges, logs from **2026-06-16**, saves `symbolic_ppo_checkpoint_*.zip`.  
- **StarBank DQN:** `PongCNN` on **(4, 64, 64)** binary grids, Q-values for `[NOOP, UP, DOWN]`, Adam **lr=0.001**, γ=0.99, replay size 10 000, ε from 1.0 → 0.01, **500** episodes with jump-start from latest `checkpoint_ep*.pth`, final weights `pong_cnn_starbank.pth`.

## 5. Model versions & results

Comparative numbers below come from `research_report.md` / `Final_Report_Assets/research_report.md`, written to explain why Warm-Start PPO was necessary after imitation alone plateaued.

**Fragile CNN (pure Behavioral Cloning).**  
Trained only to match expert actions, with no augmentation and no environment reward. Training looked healthy — high accuracy on the NPZ — but average live scores sat around **-15 to -20**. The failure mode is covariate shift: the policy is brittle off the expert state distribution. One missed return puts the ball and paddles into unfamiliar configurations; the imitator has no recovery strategy, so errors cascade for the rest of the episode.

**Robust CNN (BC + augmentation).**  
Same supervised objective, but training images were randomly shifted and corrupted with Gaussian noise so the network would not overfit exact expert pixels. Live average score improved to about **-8.2**, with noticeably more stable play. Robust BC raised the floor but still hit an **imitation ceiling**: the agent could copy expert habits and tolerate small visual noise, yet it could not invent better recoveries than those present in the dataset.

**PPO Fine-Tuned (Warm-Start RL).**  
Initialized from the robust CNN and optimized with PPO against ALE reward. Reported average score in the research report is about **-12.7** — not always better than Robust BC on the mean, but described as having the **highest potential**: the agent learned recovery behaviors and rally maintenance that pure imitation never produced. Internship live evaluation recorded a **peak game score of -1.0**, which is the best single-episode result documented for the Warm-Start phase (see §6). The research conclusion is explicit: imitation is an excellent starting point, but active exploration is required for mastery against the Atari baseline.

**Artifacts that correspond to these versions.**  
Fragile/Robust lineage culminates in `pong_cnn_expert.pth` after robust training. Warm-Start / fine-tuned PPO is packaged as `pong_ppo_finetuned.zip`. Expert data remains `expert_pong_data.npz`. Side tracks (Symbolic PPO checkpoints, StarBank DQN episode checkpoints) are separate experiments and should not be conflated with the Fragile / Robust / PPO Fine-Tuned comparison table in the research report.

## 6. Internship peak score

The internship daily summary for **2026-06-09** and **`Internship_Summery.md`** §5.3 record the headline Warm-Start result:

- **Peak game score:** **-1.0** (Warm-Start PPO)  
- **Training trajectory (same day):** averages moved from about **-21** toward **-10** as PPO broke the imitation plateau  
- **BC training accuracy:** **>90%** (does not imply live success; covariate shift still applied until augmentation + RL)  
- **Expert dataset:** **100,000** state–action pairs  
- **HardLockedPPO learning rate:** **5e-4**

This peak is the internship’s canonical success metric for Agent PING-PONG. The research report’s average scores (Fragile / Robust / PPO Fine-Tuned) describe version-level means; **-1.0** is the best observed live game under Warm-Start PPO and should be cited whenever summarizing internship outcomes.

## 7. Source appendix

| Path | Role |
|---|---|
| `main.py` | Pygame bootstrap + Dynamic Discovery lobby |
| `game_engine.py` | Headless `PongEngine` (custom physics) |
| `tournament_server.py` / `server.py` | FastAPI WebSocket Atari servers (port 10001) |
| `agent_closed_loop.py` | PPO client closed loop |
| `train_ppo.py` | Marathon PPO fine-tuning |
| `train_symbolic_ppo.py` | Symbolic PPO + TimeLineProject |
| `CNN_Learning/train_cnn.py`, `cnn_model.py`, `star_bank_env.py` | StarBank DQN track |
| `research_report.md`, `Final_Report_Assets/research_report.md` | Model comparison narrative |
| `expert_pong_data.npz`, `pong_cnn_expert.pth`, `pong_ppo_finetuned.zip` | Core ML artifacts |
| `Internship_Summery.md` §5 | Internship eras, peak **-1.0**, cluster IP |
| `summery/Week_23/2026-06-09/DailySummary.txt` | BC→PPO daily learnings |
| `Summeries/summery.txt` | Jun 8–9 bootstrap and web pivot |

*End of PingPong_Summery. Filename spelling intentional. Prefer this workspace over missing `Hermes_Docs/PingPong_Game` for artifact truth.*
