# D&D / Hermes Protocol Summery

**Document:** `Documents/Paper/DND_Summery.md`
**Period covered:** 2026-06-09 → 2026-06-26 (internship Eras 3–10); git tip 2026-06-26
**Scope:** Multi-agent D&D simulation platform — Sovereign Gateway, Sovereign Delegation, campaign docs — not production promotion docs.

**Cross-reference:** Internship narrative in **`Internship_Summery.md`** §6 (Project B) and Eras 3–10. **Git remote:** Faraday `git@faraday.lps.umd.edu:cipp/dd_game_design.git`, branch **`game_engine`** @ **`2e075c9`**.

## 1. Title / meta

| Field | Value |
|---|---|
| Document name | **D&D / Hermes Protocol Summery** (intentional spelling: Summery) |
| Period | 2026-06-09 → 2026-06-26 (git tip) |
| Local workspace | `/home/prodrig/Documents/DND_Project` |
| Git remote | Faraday `git@faraday.lps.umd.edu:cipp/dd_game_design.git` |
| Active branch | `game_engine` @ **`2e075c9`** (2026-06-26) |
| Total commits (all branches) | **70** |
| `main` branch | Docs-only (per research) |
| Working tree | Uncommitted modification: **`local_dm_agent.py`** (M) — dirty tree only; no invented commit content |
| Source authority | Project files + git log + `Game_Documentation/*` + `Internship_Summery.md` Eras 3–10 |
| Root README | GitLab template only — **not authoritative** |

## 2. Introduction

The D&D / Hermes Protocol project is a multi-agent tabletop simulation platform: players interact through a browser UI, a central **Gateway** orchestrates specialist agents, and a hybrid **Deterministic Core** keeps game math (dice, positions, HP, initiative) separate from AI-generated narration. The goal is not a single chatbot that “pretends” to be a DM, but a distributed engine where each agent has a clear job—identity, monsters, strategy, voice, prose—while one process alone is allowed to write world state.

**What problem it solves.** Pure LLM dungeon masters drift: they invent rooms that contradict the map, forget HP, or strand players in narrative “voids” with no clear next move. This project attacks those failure modes with architecture. A **Sovereign Gateway** owns persistence. A **Local-DM** loads campaign knowledge and judges rules lightly, then delegates requirement resolution to a **Strat-Bridge** and prose to a **Narrator** (vLLM). Campaign design follows an **Anti-Void / Guided Sandbox** philosophy: always offer 2–3 concrete leads so an AI DM never leaves the party with nowhere to go. The flagship adventure is **The Last Heroes of Dragonfall Gate**.

**How progress unfolded (internship Eras 3–10).**  
Work began in mid-June 2026 with a **Mock Hub**, Gateway Orchestrator, and Textual TUI, plus a Project Charter and Interface Contract for a five-person team. Infrastructure hardened (service scripts, uv environments). On **2026-06-17** the team audited a five-stage user-processing pipeline and stood up a real Hub Agent with a Collaborative Command-and-Control (C2) model for external Character/Jarvis work. By **2026-06-18** the multi-agent mesh was live (Gateway, Hub, Monster, Jarvis). Combat automation, guided narrative character creation, and perception packets followed (**Jun 23**). **Jun 24–25** introduced world materialization, a campaign knowledge base, and a local sovereign DM to stop void loops. **Jun 26** locked the Era 10 tip: Sovereign Delegation (Local-DM → Strat-Bridge → Narrator), Narrator on port **11501**, Strat-Bridge on **40003**, Gateway on **40001**, and a sync commit **`2e075c9`** pushed to Faraday `game_engine`.

**What exists on disk today.** The local tree `/home/prodrig/Documents/DND_Project` tracks Faraday `cipp/dd_game_design` on branch **`game_engine`**. Runtime code centers on `gateway.py`, `local_dm_agent.py`, `strat_bridge.py`, `char_agent_v2.py`, `monster_starter.py`, `common_db.py`, and `index.html` (“D&D Sovereign Engine - Official Interface”). Specs live under `Game_Documentation/`. Campaign material lives in `campaign_outline.md`, `campaign_data/`, and `research/design_philosophy.md`. A nested clone `ai-dungeon-master-ref/` is reference-only (LangGraph / Chainlit patterns) and is **not** wired into the Gateway. Root `README.md` is still the GitLab starter template—ignore it for technical truth.

**What a reader should take away.** This is a cluster-hosted, FastAPI-based multi-agent D&D engine with a strong doctrine: agents propose `commands`; the Gateway executes and persists; the DM speaks; the Strategist resolves; the Narrator writes prose. Ports drifted across eras—always use era labels (see §3 and `Internship_Summery.md` §6.6). One known tip-of-tree bug remains: some Gateway POSTs still hardcode DM port **48099** while Local-DM listens on **40099**.

## 3. Framework

The framework is the set of architectural layers that replaced “one AI does everything” with a controllable service mesh.

**Deterministic Core.**  
Game truth (stats, inventory, positions, combat initiative, room entities) is structured data, not free text. Agents read via `common_db.py` / the Gateway’s in-memory **World State Authority (WSA)**. Agents must not open the SQLite file and write themselves. Changes return as a `commands` list (`update_entity`, movement, dice rolls, narration hooks, and so on). That rule is mandatory in `Game_Documentation/DATA_CONTRACT.md` (“Centralized Authority”).

**Sovereign Gateway (`gateway.py`).**  
Stack: **Python**, **FastAPI**, **Uvicorn**, **WebSockets**, **httpx**, **common_db** (SQLite JSON blobs). Listens on **`0.0.0.0:40001`**. Core classes include **`WorldStateAuthority`** (hot RAM state + dirty-set persistence every ~60s), session/token management, turn management, and WebSocket broadcast to the UI. `ROUTING_MAP` proxies prefixes to specialist services:

- `/dm` → `http://127.0.0.1:40099`  
- `/strat` → `http://127.0.0.1:40003`  
- `/monster` → `http://127.0.0.1:45587`  
- `/char` → `http://127.0.0.1:9090` (legacy alias)  
- `/char_agent` → `http://127.0.0.1:40011`  

Command batches are audited to `command_audit.log`. Debug logging goes to `gateway_debug.log`.

**Sovereign Delegation (Local-DM + Strat-Bridge + Narrator).**  
Earlier eras used an external DM bridge and mock specialists. Era 10’s pattern is explicit:

1. **Local-DM** (`local_dm_agent.py`, port **40099**) — “Voice” / logic. Loads campaign outline and `campaign_data/` through **`KBEngine`**, applies light rule judging (e.g. roll detection), and returns SAS-style `commands` responses.  
2. **Strat-Bridge** (`strat_bridge.py`, port **40003**) — “Brain” proxy. Forwards skill/rule calls to an external Strategist at `http://localhost:8001`.  
3. **Narrator** — “Prose.” Local-DM calls vLLM OpenAI-compatible chat at **`http://localhost:11501/v1/chat/completions`** (model id `/vllm_models/gemma-4-31B-it-FP8` per Jun 26 fix commit).

Flow in words: player intent reaches the Gateway → DM path → Local-DM consults knowledge + Strat-Bridge → Narrator generates immersive text → Gateway applies resulting commands and pushes UI updates.

**Specialist agents.**  
- **Character / Jarvis** (`char_agent_v2.py`, port **40011**) — identity lead: character creation, finalization, C2 bridge behaviors for tactical advice.  
- **Monster** (`monster_starter.py`, mapped **45587**) — spawn and monster action strings; WSA-oriented entity updates.  
- Historical Hub / Lore / Ledger / Chronicler agents appear in internship Eras 5–6 (Hub on **8004**, etc.); the tip tree emphasizes Gateway + Local-DM + Strat + Char + Monster rather than the earlier mock hub cast.

**Persistence (`common_db.py`).**  
Stack: **SQLite**, thread **Lock**, JSON-serialized `entities` table. Configured `DB_PATH` points at the cluster datapool: `/datapool/student_projects/D&D_Game/world_state.db`. Local copies of `world_state.db` may also appear in the project root for offline work. Deep-merge updates preserve nested dict fields.

**UI layer (`index.html`).**  
Stack: static HTML, **Tailwind**-style utility classes, browser **WebSocket** client to the Gateway, title art `Title_Game.png`. Product title: **“D&D Sovereign Engine - Official Interface.”** Players join, build or select characters, enter a lobby, and explore a grid map with auto-reconnect on socket drop.

**Reference subtree (not runtime).**  
`ai-dungeon-master-ref/` is a nested clone of an external LangGraph/Chainlit multi-agent D&D project. Useful for design comparison; **not** imported by `gateway.py`.

**Port evolution (do not flatten).**  
Internship ports moved repeatedly—Gateway **10001 → 40001**, Character **9090 → 10011 → 40011**, DM Bridge **48081/48082**, unified DM experiments on **48099**, Narrator **11501**, Strat-Bridge **40003**. Era 10 tip values above are current for the code under review. Full trail: `Internship_Summery.md` §6.6.

**Known inconsistency at tip.**  
`ROUTING_MAP["/dm"]` correctly targets **40099**, but direct `httpx` POSTs inside `gateway.py` (dice / synopsis paths) still call **`http://127.0.0.1:48099/action`**. `local_dm_agent.py` binds **40099**. Until those hardcodes match, some DM call paths can fail even when routing proxies work.

## 4. Pipelines & data contract

**Five-stage user processing (Era 5 audit).**  
When the Gateway was first mapped end-to-end, player turns followed five conceptual stages: (1) **Input** — WebSocket delivers `user_id` and `user_input`; (2) **Contextualization** — quantitative state (Ledger: stats/inventory) and qualitative memory (Chronicler) gathered in parallel via Hub; (3) **Routing** — merge player text with lore/rules and send toward Strategist / DM; (4) **State Update** — mutate world entities before speaking; (5) **Narration** — return immersive text to the UI. Sovereign Delegation later redistributed stages 3–5 across Local-DM, Strat-Bridge, and Narrator, but the separation of “facts first, prose second” remains.

**Tactical / C2 loop.**  
For combat-aware play, the Collaborative Command-and-Control model described in internship notes runs: Engine → Perception Feed → Jarvis → Plan Buffer → Strategist → DM → Player. Jarvis consumes perception packets (HP, enemies, lighting) so advice stays grounded in live state rather than inventing threats.

**Command processing.**  
Agents respond with structured `commands`. The Gateway’s processor validates batches, appends to `command_audit.log`, updates WSA hot state, and eventually persists dirty entities through `common_db`. Example actions include `update_entity`, room/world updates (`update_room` from world-materialization work), and narration/notify hooks for the UI.

**Data contract schemas (`DATA_CONTRACT.md` v1.0).**  
Team ownership was divided by role:

- **Player (`player_{id}`)** — Character/Jarvis: name, class, level, stats/modifiers, vitals (`hp_current` ≤ `hp_max`), position, inventory, conditions, status.  
- **Monster (`monster_{id}`)** — Monster agent: type, CR, combat stats, vitals, resistances, aggro target, behavior, position.  
- **Combat (`combat_{id}`)** — Strategist: participants sorted by initiative, `current_turn_index`, round, status. Only the Strategist advances turns.  
- **World sector (`sector_{id}`)** — DM reads; Gateway writes: description, entities present, exits, env effects, danger level.

Integration workflow is always: **read** with `get_entity` / WSA → **propose** commands → **Gateway writes**.

## 5. Campaign & UI

**Design philosophy (“Guided Sandbox”).**  
`research/design_philosophy.md` compares linear rails, open sandboxes, and node-based webs. The synthesis for an AI DM is hybrid: sandbox feel for the region, **node-based** plot with 2–3 always-visible leads (Anti-Void), and linear beats for cinematic moments (inciting incident). That doctrine is why campaign docs stress exits, bait, and alternate paths rather than a single railroad.

**Campaign: The Last Heroes of Dragonfall Gate.**  
`campaign_outline.md` sets cosmology (**Shattered Mirror** / Aethelgard, Bleed Zones, Echo Realms), factions (Silver Concordance, Hollow-Walkers, Iron Vanguard), and the starting **Vale of Oakhaven**. The hook **The Silent Bell**: the Stabilizer Anchor goes quiet, Grey Mist traps the valley, Echoes of possible futures appear. Players seek three Resonance Shards (Strength / Knowledge / Spirit) via Marshes, Sanctum, and Crag nodes. Key NPCs include Elder Thorne, Kaelen the Hollow, and Inquisitor Valerius. Local-DM’s `KBEngine` loads this outline plus `campaign_data/` markdown (`campaign_hook.md`, `starting_region.md`, `world_lore.md`). **Lore note:** `campaign_data/world_lore.md` can diverge from the outline’s cosmology—treat each file as its own source rather than assuming one merged canon.

**UI behaviors.**  
The Sovereign Engine UI evolved from a Textual TUI (early internship) to the current web client. Notable features from internship and code: join / character selection / lobby flow; grid map rendering; WebSocket auto-reconnect; guided narrative character chat culminating in `/finalize_character` (sheet mode and world spawn); combat helper `triggerMonsterTurn()` sequencing player attack → strategist resolution → monster response; color cues for monster vs DM messages. Title imagery (`Title_Game.png`) brands the product as the Sovereign Engine.

**Documentation pack.**  
`Game_Documentation/` holds developer README, implementation guide, per-agent specs (DM, Char, Monster, Strat), Strategist JSON guide, SOUL persona notes, project roadmap, and the data contract. These specs sometimes list older ports (8080 / 8001 / 9090); prefer code + Era 10 values when they conflict.

## 6. Status (as of 2026-06-26 tip)

Local `game_engine` matches Faraday `origin/game_engine` at commit **`2e075c9`** (“Sync all current project changes: update char_agent, gateway, and frontend UI”), after **`fe113d6`** fixed Narrator **11501** / model id and Strat-Bridge **40003**. Internship Era 10 recorded E2E verification of Observation, Movement, and Roll loops under Sovereign Delegation.

**Still open or fragile.** Gateway hardcodes DM **48099** in places while Local-DM serves **40099**. Working tree has uncommitted edits to `local_dm_agent.py`. Campaign Anti-Void outline is drafted; internship Era 9 noted a hardcoded position constraint `(0,2)` fix in progress. Cluster DB path in `common_db.py` assumes datapool layout. Root README remains a template. No commits in this clone after 2026-06-26—later internship focus moved to Paradigm / CIPP (see `CIPP_Summery.md`).

**Representative git milestones.** World materialization and `update_room` (**Jun 24**); sovereign `strat_bridge` replacing hardcoded strategist (**Jun 24**); campaign KB + local sovereign DM / void prevention (**Jun 25**); Narrator and Strat port fixes + tip sync (**Jun 26**).

## 7. Source appendix

| Path | Role |
|---|---|
| `gateway.py` | Sovereign Gateway, WSA, ROUTING_MAP, port 40001 |
| `local_dm_agent.py` | Local-DM, KBEngine, Strat + Narrator calls, port 40099 |
| `strat_bridge.py` | Strategist proxy to localhost:8001, port 40003 |
| `char_agent_v2.py` | Character / Jarvis agent, port 40011 |
| `monster_starter.py` | Monster agent entry |
| `common_db.py` | SQLite entity store (cluster DB_PATH) |
| `index.html` | Sovereign Engine web UI |
| `launch_*.py` | Background helpers for gateway / dm / monster / strat |
| `Game_Documentation/*` | Specs, data contract, roadmap |
| `campaign_outline.md` | Dragonfall Gate campaign |
| `campaign_data/` | Hook, region, lore markdown for KBEngine |
| `research/design_philosophy.md` | Guided Sandbox research |
| `ai-dungeon-master-ref/` | Unwired reference clone |
| `Internship_Summery.md` §6 | Internship eras, port evolution, pipelines |
| Faraday `cipp/dd_game_design.git` | Source of truth remote (`game_engine`) |

*End of DND_Summery. Filename spelling intentional. For internship-wide context see `Internship_Summery.md`; for post–Jul 1 Paradigm work see `CIPP_Summery.md`.*
