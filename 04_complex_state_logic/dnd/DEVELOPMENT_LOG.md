# PROJECT HERMES: DEVELOPMENT LOG & ARCHITECTURAL ARCHIVE

## 1. Project Vision
Project Hermes is a multiplayer D&D experience powered by a neuro-symbolic AI architecture. The goal was to move away from a "Direct Play" model (where the AI just narrates) to a **Collaborative Command-and-Control (C2) Model**, where an AI Companion (Jarvis) acts as the tactical bridge between the player and the game engine.

---

## 2. Architectural Evolution

### Phase 1: The Prototype (Stateful Intelligence)
*   **Initial Setup:** Implemented `builder.py` as the central rules engine and character creator.
*   **Initial Courier:** `jarvis_agent.py` acted as a simple tactical advisor.
*   **The Problem:** The agent held character state in local memory. As the number of characters/sessions grew, memory consumption spiked, leading to system crashes and state leakage between players.

### Phase 2: The Stability Pivot (Stateless + LRU)
To resolve the stability issues, the architecture was fundamentally shifted:
*   **Statelessness:** Removed all internal state tracking from `JarvisAgent`. The agent now treats every request as a fresh transaction, loading `Profile` and `State` from disk on-demand.
*   **LRU Caching:** Implemented `functools.lru_cache` for static rule lookups and profile data.
    *   **Impact:** Reduced disk I/O latency while keeping RAM usage constant, regardless of the total number of characters in the database.
*   **Verification:** Validated that 50+ rapid-fire requests could be processed in milliseconds without memory growth.

### Phase 3: The C2 Model & The Arbiter
To prevent AI "hallucinations" (e.g., a Fighter attempting to cast a spell), a verification layer was added.
*   **The Pipeline:** `Gateway (Intelligence) -> Courier (Transport) -> Arbiter (Verification) -> User`.
*   **Mechanical Verification:** The Courier now cross-references every AI suggestion against the `builder.py` rules and the character's `gameplay_profile`.
*   **The Retry Loop:** If a suggestion is mechanically illegal, the Courier blocks it and triggers a `RETRY` signal to the Hermes Gateway to regenerate a legal move.

---

## 3. Component Specifications

### 3.1. The Symbolic Engine (`builder.py`)
*   **Responsibility:** The "Hard Truth."
*   **Key Functions:** AC calculation, stat generation, condition management, and character persistence.
*   **Outputs:** Permanent Profile (JSON) and Live State (JSON).

### 3.2. The Courier (`jarvis_agent.py`)
*   **Responsibility:** The "Tactical Bridge."
*   **Core Logic:**
    *   `suggest_action()`: Generates the perception packet.
    *   `verify_with_arbiter()`: The gatekeeper for mechanical legality.
    *   `deliver_response()`: The final delivery pipeline.

### 3.3. The Intelligence (`persona.md`)
*   **Responsibility:** The "Strategic Mind."
*   **Logic:** Class-based tactical priorities (e.g., Rogue = Stealth/Caution, Fighter = Aggression/Frontline).

---

## 4. Final Integration Blueprint (C2 Mandate)
The project concluded with a full technical specification for the game engine developers, defining:
1.  **Unified Entity Schema:** `Entity_ID` linking Profile, State, and Persona.
2.  **Perception Feed:** High-fidelity JSON stream providing raw world data to the AI.
3.  **Plan Buffer:** A sandbox for drafting actions before `COMMIT_PLAN`.
4.  **Event Triggers:** Automatic Courier wake-ups on HP change, turn shifts, or environmental changes.
5.  **Structured Action API:** Translation of AI advice into strict JSON commands for the engine.

---

## 5. Technical Summary
*   **Design Pattern:** Decoupled C2 Architecture.
*   **Memory Model:** Stateless with LRU Caching.
*   **Verification Model:** Two-Stage Arbiter (Mechanical $\rightarrow$ Contextual).
*   **Complexity:** $O(1)$ memory scaling relative to total user base.
