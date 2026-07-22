---
name: rpg-c2-gateway-integration
description: Guidelines for implementing and troubleshooting the Collaborative Command-and-Control (C2) Gateway for the Hermes RPG project.
---

# RPG C2 Gateway Integration

This skill governs the implementation of the API Bridge (Gateway) that connects AI Agents (Builder, Jarvis) to the Game Engine.

## 🚀 Architectural Workflow
The system operates on a three-stage tactical loop:
1. **Perception**: Gateway calls `get_perception_packet(entity_id)` from the Engine to get Raw Truth.
2. **Reasoning**: Perception + Psychological Brief $\rightarrow$ Strategist Agent $\rightarrow$ Tactical Advice.
3. **Execution**: Advice $\rightarrow$ Plan Buffer (`draft_plan`) $\rightarrow$ `COMMIT_PLAN` to Engine.

## 🛠 Implementation Standards

### Character Creation (The Builder)
- **Input**: Must accept `name`, `char_class`, and `persona` (Aggressive/Defensive/Balanced).
- **Storage**: Profiles MUST be saved as `profile_{entity_id}.json` in the project profiles directory (e.g., /home/cxiong/hermes_rpg/profiles/).
- **Schema**: Output must strictly follow `C2_ENTITY_SCHEMA.md`.
- **Interactive Flow**: Implement a state-driven `CreationSession` (NAME -> CLASS -> SPECIES -> BACKGROUND -> PERSONA -> WEAPON) to provide a conversational, dialogue-driven UX rather than a static form submission.
- **Stability**: Implement a "Safety Net" for stat arrays. If `stat_array` is missing from `character_options.json`, fall back to the Standard Array [15, 14, 13, 12, 10, 8] to prevent 500 Internal Server Errors.

### Tactical Interface (Jarvis/Courier)
- **Transport**: Use WebSockets (`ws://<server-ip>:10001/ws`) for real-time engine communication.
- **State**: Jarvis must remain stateless; all context must be derived from the current Perception Packet and the stored JSON profile.
- **Verification**: Implement an "Arbiter Check" to verify if a suggested action is mechanically legal (e.g., checking spell slots in the profile) before proposing it to the user.

## ⚠️ Common Pitfalls & Fixes

### 1. CORS "Failed to Fetch"
When accessing the API Bridge via a browser (FastAPI/Uvicorn), the browser will block requests due to CORS.
- **Fix**: Add `CORSMiddleware` to the FastAPI app allowing all origins (`allow_origins=["*"]`).

### 2. Dependency Isolation (`uv` vs System)
Running agents with `uv run` creates isolated environments. Libraries installed via `pip install` system-wide may be invisible.
- **Fix**: Use `uv run --with <package>` (e.g., `uv run --with requests --with flask python main.py`) to force dependencies into the runtime.

### 3. The 'stat_array' Crash
A common failure point where `builder.py` crashes if the options JSON is incomplete.
- **Fix**: Ensure `builder.py` uses `.get('stat_array', [15, 14, 13, 12, 10, 8])` rather than direct key access.

## ✅ Verification Steps
- [ ] `/health` endpoint returns `C2_BRIDGE_OPERATIONAL`.
- [ ] `POST /character/create` returns the FULL character object and saves the file to the mandatory path.
- [ ] `POST /jarvis/ask` successfully retrieves a perception packet from the WebSocket gateway before returning advice.
