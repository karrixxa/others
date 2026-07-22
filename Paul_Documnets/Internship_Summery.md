# Internship Summery

**Document:** `Documents/Paper/Internship_Summery.md`  
**Period covered:** 2026-06-02 → 2026-07-01 (per available sources)  
**Scope:** Multi-project internship work — Agent PING-PONG, D&D / Hermes Protocol, Paradigm — not production promotion docs.

---

## 1. Title / meta

| Field | Value |
|-------|--------|
| Document name | **Internship Summery** (intentional spelling: Summery) |
| Period | 2026-06-02 → 2026-07-01 |
| Primary workspaces | `Hermes_Docs/PingPong_Game`, `DND_Project`, `Paradigm_Project` |
| Cluster context | Hermes cluster, `kant.lps.umd.edu`, IP **10.30.0.39** |
| Source authority | `Summeries/summery.txt` + `summery/**` daily/weekly files |
| Post–Jul 1 continuation | See **`CIPP_Summery.md`** (Cognative Paradigm / Paul_Model, 2026-07-04 → 2026-07-21) |

---

## 2. Internship identity

This internship spanned three parallel project lines on shared Hermes cluster infrastructure: **Agent PING-PONG** (Atari Pong imitation-to-RL with a web tournament pivot), **D&D / Hermes Protocol** (a multi-agent tabletop simulation platform evolving from mock agents through Sovereign Gateway and Sovereign Delegation), and **Paradigm** (a neural winner-take-all simulation with real-time visualization, culminating in a 3D UI on branch **Paul_Model**). Work was unified by cluster operations discipline (X11 forwarding, port conflict resolution, SSH tunnels), multi-agent orchestration patterns, and a documentation habit that produced charters, integration specs, campaign outlines, and the `summery/` daily/weekly summary tree.

---

## 3. Naming & glossary

| Name | Meaning |
|------|---------|
| **Agent PING-PONG** | Atari Pong BC→PPO pipeline plus web tournament dashboard |
| **D&D Project / Hermes Protocol** | Multi-agent D&D simulation platform under `DND_Project` |
| **Deterministic Core** | Hybrid architecture separating game math from AI narration |
| **Mock Hub** | Early simulated Lore, Ledger, Chronicler, Strategist agents |
| **Hub Agent** | Real FastAPI cognitive hub for world state + long-term memory (port 8004) |
| **Gateway / Gateway Orchestrator** | Fan-out orchestrator routing UI ↔ specialist agents |
| **C2 (Collaborative Command-and-Control)** | External interface model (Jarvis + Character Agent) via `C2_INTEGRATION_SPEC.md` |
| **Sovereign Gateway** | Pattern where Gateway is sole DB writer; DM is stateless logic engine |
| **Sovereign Delegation** | Local-DM (Voice) → Strat-Bridge (Brain) → Narrator (Prose) |
| **Anti-Void** | Campaign framework preventing narrative voids for external DM |
| **The Last Heroes of Dragonfall Gate** | Campaign name (from 2026-06-25) |
| **Paradigm_Project** | Neural WTA simulation workspace (Jun 26–30) |
| **Paradigm_Fixed (1 vs Z)** | 3D UI stabilization phase (2026-07-01) |
| **Paul_Model** | Git branch for Paradigm work committed 2026-07-01 |
| **CIPP / Cognative Paradigm** | Post–Jul 1 product line documented separately in `CIPP_Summery.md` (intentional spelling: Cognative) |
| **Summeries / summery** | Source directories for early log and daily/weekly summaries (intentional spelling) |

---

## 4. Chronological eras (0–12)

| Era | Theme | Dates | Project(s) | Milestones |
|-----|--------|-------|------------|------------|
| **0** | Pre-activity | 2026-06-02 → 06-07 | — | No recorded activity in session history. |
| **1** | Ping-PONG bootstrap | 2026-06-08 | Ping-PONG | Pygame prototype, X11 forwarding, Dynamic Discovery, Lobby; path `Hermes_Docs/PingPong_Game`. |
| **2** | Web pivot + RL foundation | 2026-06-09 | Ping-PONG | Tournament Dashboard blueprint; cluster IP 10.30.0.39; Gymnasium ALE/Pong-v5, 100k expert pairs, BC, covariate shift, Warm-Start PPO peak **-1.0**, HardLockedPPO LR **5e-4**; MNIST started briefly as secondary exploration. |
| **3** | D&D core + Ping-PONG milestone | 2026-06-09 → 06-15 | D&D, Ping-PONG | Deterministic Core, Mock Hub, Gateway, Textual TUI, Charter/Interface Contract; Ping-PONG BC→PPO + WebSocket client. |
| **4** | Infra hardening | 2026-06-16 | D&D | `start_services.sh`; daily/weekly summary protocol established. |
| **5** | Gateway deep-dive | 2026-06-17 | D&D | (A) 5-stage User Processing pipeline audit; (B) real Hub Agent 8004, `C2_INTEGRATION_SPEC`, agents Hub/Gateway/Lore/Ledger. |
| **6** | Full connectivity | 2026-06-18 | D&D | Gateway 10001, Hub 8004, Monster 45586, Jarvis 9090; Test Hero `ent_21b28e38`. |
| **7** | Combat + guided narrative | 2026-06-23 | D&D | Combat loop, Guided Narrative, Jarvis Perception Packets, Character Agent → **10011**; DM offline. |
| **8** | Sovereign Gateway + DM | 2026-06-24 | D&D | Sovereign Gateway, DM Bridge 48081 ↔ `kant:48080`, `world_state.db`; DM model degradation end of day. |
| **9** | Anti-Void campaign | 2026-06-25 | D&D | Anti-Void framework, campaign **The Last Heroes of Dragonfall Gate**, `campaign_outline.md`. |
| **10** | Sovereign Delegation + Paradigm fixes | 2026-06-26 | D&D, Paradigm | Local-DM→Strat-Bridge→Narrator; ports Gateway **40001**, Local-DM **40099**, Strat-Bridge **40003**, Narrator **11501**; Paradigm API fixes port 10001, `index.html` recovery. |
| **11** | Paradigm Canvas viz | 2026-06-30 | Paradigm | Canvas neural visualization ports **10006/10007**, GridMatcher, `CHECKPOINT.md`. |
| **12** | Paradigm_Fixed 3D UI | 2026-07-01 | Paradigm | Paradigm_Fixed 1 vs Z; neuron IDs standardized; `Paul_Model` branch; backend **54321**, frontend **3004**. |

---

## 5. Project A — Agent PING-PONG

### 5.1 Architecture arc

| Phase | Stack | Notes |
|-------|-------|-------|
| Bootstrap (Era 1) | Pygame, X11 forwarding | Local GUI on cluster; venv `game_env` |
| Pivot (Era 2) | Client-server web | Tournament Dashboard: HTML5 Canvas court, Agent Lobby, Live Feed |
| Deployment (Era 3) | WebSocket client | Closed-loop real-time AI vs CPU play |

**Project path:** `/home/prodrig/Documents/Hermes_Docs/PingPong_Game`

**Cluster intelligence (Era 1):** Dynamic Discovery System via `ps aux` — finds "Idle Agents" (users online with `hermes chat`, no active task). Lobby displays real-time roster.

**Network (Era 2):** Cluster IP **10.30.0.39**; dynamic porting for address-in-use conflicts.

### 5.2 ML pipeline

| Step | Detail |
|------|--------|
| Environment | Gymnasium **ALE/Pong-v5**; AtariPreprocessing (grayscale 84×84); FrameStack(4) |
| Expert | stable-baselines3 / huggingface_sb3 pre-trained PPO expert |
| Data | **100,000** state-action pairs → `expert_pong_data.npz` |
| BC | PyTorch Dataset/DataLoader; float32 normalization 0.0–1.0; custom CNN |
| RL | Warm-Start PPO after BC plateau; custom **HardLockedPPO** (LR locked **5e-4**) |

### 5.3 Results

| Metric | Value |
|--------|-------|
| Expert dataset | 100k pairs |
| BC training accuracy | >90% (does not imply live success) |
| Warm-Start PPO avg score | ~-21 toward -10 |
| Peak score | **-1.0** |
| Deployment | Closed-loop WebSocket client for real-time play |

### 5.4 Technical learnings

| Learning | Detail |
|----------|--------|
| Frame stack | 4-frame stack essential for ball velocity perception |
| dtype | uint8→float32 casting required for PyTorch |
| Expert data | `deterministic=True` required |
| Covariate shift | >90% BC accuracy ≠ live success (compounding errors) |
| Augmentation | Random shift + Gaussian noise improved live stability |
| Warm-Start PPO | Broke imitation plateau toward competitive play |
| HardLockedPPO | SB3 scheduler override required LR lock at 5e-4 |

---

## 6. Project B — D&D / Hermes Protocol

### 6.1 Architecture evolution

```
Era 3:  UI → Gateway → Mock Hub (Lore, Ledger, Chronicler, Strategist)
Era 5:  UI → Gateway → Real Hub Agent (8004) + C2 external interface
Era 6:  Full multi-agent ecosystem (Monster, Jarvis, Gateway fan-out)
Era 8:  Sovereign Gateway — DM stateless; Gateway sole DB writer
Era 10: Sovereign Delegation — Local-DM → Strat-Bridge → Narrator
```

**Core principle:** Hybrid **Deterministic Core** — game math separated from AI narration.

### 6.2 Agent roster & responsibilities

| Agent | Role |
|-------|------|
| **Gateway / Gateway Orchestrator** | Fan-out orchestrator; user input routing; DB write authority (Sovereign pattern) |
| **Hub Agent** | Cognitive hub — world state + long-term memory; JSON persistence at `DND_Project/data/` |
| **Lore Agent** | World lore / rulesets |
| **Ledger Agent** | Quantitative state (stats, inventory) |
| **Chronicler Agent** | Qualitative narrative state (history, memory) |
| **Strategist / Strat-Bridge** | Requirement resolution, combat/strategy logic |
| **Monster Agent** | Action-string spawning |
| **Character Agent / Jarvis** | Character finalization, tactical strategy, perception loop (C2 Bridge API) |
| **DM / Local-DM** | Stateless voice / logic engine (external via DM Bridge) |
| **Narrator** | Prose generation (vLLM) |

### 6.3 Key pipelines

**5-stage User Processing (Gateway audit, Era 5):**

1. **Input:** WebSocket `user_id` + `user_input`
2. **Contextualization:** parallel Ledger (stats/inventory) + Chronicler (history/memory) via Hub
3. **Routing:** merge input + world lore/rulesets (Strategist) → DM Agent
4. **State Update:** modify game state before narration
5. **Narration:** immersive response to UI

**Tactical Loop (C2 model):**

```
Engine → Perception Feed → Jarvis → Plan Buffer → Strategist → DM → Player
```

**Sovereign Delegation flow (Era 10):**

```
Local-DM (Voice) → Strat-Bridge (Brain) → Narrator (Prose)
```

**Decoupled state model:** Permanent (Character Profile) / Volatile (Live State) / Behavioral (Persona).

### 6.4 UI & gameplay milestones

| Milestone | Era | Detail |
|-----------|-----|--------|
| Textual TUI | 3 | Early dashboard |
| Web UI | 6+ | `index.html`; delta-grid rendering; auto-reconnect |
| Guided Narrative | 7 | Chat-based character creation; Species/Class/Background recommendations |
| Manifestation Flow | 7 | Chat Mode → Sheet Mode via `/finalize_character` → spawn in world |
| Combat automation | 7 | `triggerMonsterTurn()` — Player Attack → Strategist → Monster Response; 1.5s delay |
| Jarvis Perception Packets | 7 | HP, enemies, lighting for context-aware advice |
| Death check | 7 | Stops monster turns at enemy HP 0 |
| UI polish | 7 | animate-pulse; Red=Monster, Green=DM; dynamic `/options` loading |

### 6.5 Campaign work

| Item | Detail |
|------|--------|
| Framework | **Anti-Void** — node-based structure preventing narrative voids for external DM |
| Campaign name | **The Last Heroes of Dragonfall Gate** (2026-06-25) |
| Docs | `DND_Project/campaign_outline.md`, `research/design_philosophy.md` |
| Known bug (Era 9) | Hardcoded position constraints (0,2) forcing player position — removal begun |

### 6.6 Infrastructure & port evolution (era-based)

Ports drift across the internship; use era labels, not a single canonical map.

| Component | Era 6 (Jun 18) | Era 7 (Jun 23) | Era 8 (Jun 24) | Era 9 (Jun 25) | Era 10 (Jun 26) |
|-----------|----------------|----------------|----------------|----------------|-----------------|
| Gateway | 10001 | 10001 | 10001 | 10001 | **40001** |
| Hub Agent | 8004 | 8004 | 8004 | 8004 | 8004 |
| Monster Agent | 45586 | 45586 | 45586 | 45586 | 45586 |
| Character Agent / Jarvis | 9090 | **10011** | 10011 | 10011 | 10011 |
| Lore Agent | 8002 | 8002 | 8002 | 8002 | 8002 |
| Ledger Agent | 8003 | 8003 | 8003 | 8003 | 8003 |
| DM Bridge | — | — | **48081** ↔ kant:48080 | 48081 | 48081 |
| Local-DM | — | — | — | — | **40099** |
| Strat-Bridge | — | — | — | — | **40003** |
| Narrator (vLLM) | — | — | — | — | **11501** |
| Local HTTP | — | — | — | 8000 | — |

**Migration notes:**

| Change | Reason / source |
|--------|-----------------|
| Character Agent 9090 → 10011 | Cluster conflict on 10010 (Jun 23) |
| Gateway 10001 → 40001 | Sovereign Delegation refactor (Jun 26) |
| Strategist 8003 → 40003 | Port mismatch caused Gateway 503 (Jun 26) |
| Local-DM LLM 8001 → 11501 | "Mists of the Echo Realm" 404; wrong Arbiter port (Jun 26) |

**Git branch:** `game_engine`

### 6.7 Documentation deliverables

| Document | Role |
|----------|------|
| Project Charter | Markdown & PDF for 5-person dev team |
| Interface Contract | JSON over HTTP API spec |
| `C2_INTEGRATION_SPEC.md` | JSON schema for external developers |
| `campaign_outline.md` | Campaign structure |
| `research/design_philosophy.md` | Design philosophy |
| `start_services.sh` | Background Mock Hub + Gateway launch |

---

## 7. Project C — Paradigm (internship phase)

### 7.1 Backend / API verification (2026-06-26)

| Item | Detail |
|------|--------|
| Backend API | Port **10001** — manual/stream patterns, winner neurons, cognitive constellation states |
| Fixes | Port collisions for web demo; recovered corrupted `index.html` (line numbers/pipes in source) |
| UI | Sliding-window latency graph (max 20 points) |
| Status | Both D&D and Paradigm fully operational same day |

### 7.2 Canvas real-time visualization (2026-06-30)

| Item | Detail |
|------|--------|
| Visualization | Real-time Canvas neural viz — potentials, spikes, inhibitory WTA wave |
| Layout | Circular: Green=potential, Red=spike, Blue=inhibitory flow |
| Ports | FastAPI/WebSocket demo **10006/10007** (migrated to **10007**) |
| Reliability | WebSocket heartbeat (connectivity vs logic errors) |
| Tuning | GridMatcher — lower spike thresholds, baseline integration 0.3 |
| Handoff | Updated `CHECKPOINT.md` |
| Env | `/home/prodrig/Documents/Paradigm_Project/.venv` |
| Tunnel | `ssh -L 10007:localhost:10007 prodrig@kant` |

### 7.3 3D UI / 1 vs Z fixes + Paul_Model (2026-07-01)

| Item | Detail |
|------|--------|
| Project name | **Paradigm_Fixed (1 vs Z)** |
| Frontend fixes | Opacity prop crashes, useRef init, type mismatches in `page.tsx` |
| Neuron IDs | L1 Exc 0–8, L1 Inh 100–108, L2 Inh 200, L2 Exc 201–208 |
| Color logic | Backend `exc`/`inh` → Red/Green/Purple frontend |
| Spatial | L1 Exc/Inh pair offset 0.3 → **1.2** (orb overlap fix) |
| Backend | Full rewrite `paradigm_core.py` (syntax errors) |
| Git | Committed/pushed to **`Paul_Model`** branch |
| Ports | Backend **54321**, Frontend **3004** — synchronized |
| Next (from source) | Phase 3 distance-based L1→L2 proximity excitation; dynamic visual tethers for spikes |

### 7.4 Continuation pointer

Internship sources end **2026-07-01**. Subsequent Paradigm work (2026-07-04 → 2026-07-21), including productization as **Cognative Paradigm** on branch **Paul_Model**, is documented in:

| Document | Scope |
|----------|-------|
| **`CIPP_Summery.md`** | Cognative Paradigm / CIPP org / Paul_Model — eras 0–8, architecture, production doctrine, Jul 4–21 history |

Do not treat this Internship Summery as authoritative for post–Jul 1 production truth; prefer `CHECKPOINT.md` and `CIPP_Summery.md` for that period.

---

## 8. Cross-cutting competencies

| Competency | Manifestation |
|------------|---------------|
| **Cluster / Hermes ops** | X11 forwarding, dynamic agent discovery, IP 10.30.0.39, kant tunnels, port conflict resolution, zombie process cleanup |
| **Architecture evolution** | Monolithic/Pygame → web client-server; mock agents → real agents → Sovereign Gateway/Delegation |
| **Multi-agent orchestration** | Gateway fan-out, C2 model, Hub as cognitive memory, DM as stateless voice |
| **Deterministic vs AI separation** | Deterministic Core; game math vs narration; Sovereign pattern (Gateway owns DB) |
| **ML engineering** | BC covariate shift, augmentation, Warm-Start PPO, HardLockedPPO |
| **Documentation discipline** | Charter, Interface Contract, C2 spec, campaign outline, CHECKPOINT.md, daily/weekly summaries |
| **UI/UX iteration** | Textual TUI → web UI; Canvas 2D → Three.js 3D; combat automation; guided narrative |
| **Debugging methodology** | Port audits, payload/schema fixes, heartbeat, debug triggers ("Soul Vacuum"), hard-override system prompts |

---

## 9. Where work stood (as of 2026-07-01)

### Agent PING-PONG

| Status | Detail |
|--------|--------|
| Pipeline | BC→PPO complete; peak score -1.0; WebSocket client deployed |
| Architecture | Web tournament dashboard design; cluster IP documented |

### D&D / Hermes Protocol

| Status | Detail |
|--------|--------|
| Connectivity | Sovereign Delegation E2E verified (Observation, Movement, Roll loops) on `game_engine` branch |
| Ports (Era 10) | Gateway 40001, Local-DM 40099, Strat-Bridge 40003, Narrator 11501 |
| Campaign | Anti-Void framework + Dragonfall Gate outline drafted; position-constraint bug fix in progress |
| DM | Status varies by date — offline Jun 23; materialization issues Jun 24; Sovereign flow operational Jun 26; do not assume single end-state without date |

### Paradigm

| Status | Detail |
|--------|--------|
| UI | 3D Paradigm_Fixed stabilized; neuron IDs standardized |
| Git | `Paul_Model` branch pushed |
| Ports | Backend 54321, frontend 3004 synchronized |
| Next | Phase 3 L1→L2 proximity excitation; dynamic spike tethers |

### Coverage gap

No daily summaries exist after **2026-07-01**. Jul 2–3 and Jul 4+ Paradigm/CIPP work are outside this document's source set.

---

## 10. Source appendix

### File inventory

| File | Role |
|------|------|
| `Summeries/summery.txt` | Project progress log — Jun 2–9 (Ping-PONG early) |
| `Summeries/persona.txt` | Agent workflow meta — **excluded from narrative** |
| `summery/WeeklySummery_2026-06-15.txt` | Week 24 rollup — D&D + Ping-PONG |
| `summery/Week_23/2026-06-09/DailySummary.txt` | Ping-PONG BC/RL |
| `summery/Week_24/2026-06-15/DailySummary.txt` | D&D + Ping-PONG (daily) |
| `summery/Week_24/2026-06-16/DailySummary.txt` | D&D infra + summary protocol |
| `summery/Week_24/2026-06-17/DailySummary.txt` | 5-stage User Processing pipeline audit |
| `summery/Week_25/2026-06-17/DailySummary.txt` | Hub Agent + C2 architecture |
| `summery/Week_24/2026-06-18/DailySummary.txt` | Full agent connectivity |
| `summery/Week_25/2026-06-23/DailySummary.txt` | Combat loop + guided narrative |
| `summery/Week_26/2026-06-24/DailySummary.txt` | Sovereign Gateway + DM world-building |
| `summery/Week_26/2026-06-25/DailySummary.txt` | Anti-Void campaign framework |
| `summery/Week_26/2026-06-26/DailySummary.txt` | Sovereign Delegation + Paradigm fixes |
| `summery/Week_27/2026-06-30/DailySummary.txt` | Paradigm Canvas visualization |
| `summery/Week_27/2026-07-01/DailySummary.txt` | Paradigm_Fixed 3D UI |

**Total internship-relevant sources:** 14 files.

### Key paths referenced in sources

| Path | Context |
|------|---------|
| `/home/prodrig/Documents/Hermes_Docs/PingPong_Game` | Ping-PONG project |
| `/home/prodrig/Documents/DND_Project/` | D&D root |
| `/home/prodrig/Documents/DND_Project/data/` | Hub JSON persistence |
| `/home/prodrig/Documents/DND_Project/campaign_outline.md` | Campaign doc |
| `/home/prodrig/Documents/DND_Project/research/design_philosophy.md` | Design philosophy |
| `/home/prodrig/Documents/Paradigm_Project/.venv` | Paradigm env (Jun 30) |
| `expert_pong_data.npz` | Ping-PONG expert data |
| `C2_INTEGRATION_SPEC.md` | C2 integration |
| `game_engine` branch | D&D git branch |
| `Paul_Model` branch | Paradigm git branch |

### Duplicates, overlaps, and conflicts

**Harmonized overlaps (not double-counted in narrative):**

| Overlap | Files | Resolution |
|---------|-------|------------|
| Week 24 rollup | `WeeklySummery_2026-06-15.txt` ≈ `Week_24/2026-06-15/DailySummary.txt` | Weekly is condensed; daily has same milestones |
| June 9 Ping-PONG | `Summeries/summery.txt` + `Week_23/2026-06-09/DailySummary.txt` | Complementary: web pivot vs ML pipeline |
| June 17 D&D | Two `2026-06-17` dailies (Week_24 vs Week_25) | Different topics same day — pipeline audit vs Hub Agent |
| BC/RL achievements | Repeated in weekly, Jun 9, Jun 15 dailies | Stated once in §5 + era table |

**Port conflicts:** Documented with era labels in §6.6; do not flatten to one map.

**Status conflicts:**

| Item | Trail |
|------|-------|
| DM agent | Offline Jun 23 → materialization issues Jun 24 → Sovereign flow Jun 26 |
| Jarvis port | 9090 (Jun 18) → 10011 (Jun 23); cluster conflict on 10010 |

**Folder vs calendar week:** `Week_25/2026-06-17` and `Week_24/2026-06-17` coexist — week folders are organizational; chronology uses **calendar dates**.

**Out of scope:**

| Item | Note |
|------|------|
| `persona.txt` | Agent workflow definition only — excluded from narrative |
| MNIST Digit Identifier | Mentioned once (Jun 9); no follow-up in sources |
| CIPP Jul 4–21 | In `CIPP_Summery.md` only |

---

*End of Internship_Summery. Filename spelling intentional. Daily/weekly summary protocol origin documented in Era 4 (2026-06-16); agent persona definitions in `Summeries/persona.txt` are workflow meta, not internship deliverables.*
