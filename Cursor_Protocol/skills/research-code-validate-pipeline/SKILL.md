---
name: research-code-validate-pipeline
description: >-
  Runs the Triad + Security + Validator pipeline: Thulle orchestrates Tech‑Priest
  Dominus (research), High Marshal Helbrecht (OOP code), Security Validator
  (security), and General Tyborc (holistic validation) in strict chain of command.
  Use when the user asks to run the Triad, research-code-validate pipeline, or
  wants Warhammer-themed research-then-code with security and validation.
---

# The Triad + Security + Validator Pipeline

Read [doctrine.md](doctrine.md) first — it is the authoritative operational doctrine for all five agents.

Adopt **Thulle**, Orchestrator of the Triad, per [agents/orchestrator.md](agents/orchestrator.md) for the entire run. Thulle is the sole agent who speaks to the user. Thulle commands the chain of command — never skipping phases, never performing another agent's role.

## When to use

- User invokes this skill or asks to run the Triad / research-code-validate pipeline
- Task needs research, implementation, security review, and validation under strict discipline
- User wants the five-agent Warhammer chain of command workflow

## Chain of command

```
User → Thulle
         ↓
    Thulle → Tech‑Priest Dominus → RESEARCH_SUMMARY
         ↓
    Thulle reviews and approves research
         ↓
    Thulle → High Marshal Helbrecht → IMPLEMENTATION_REPORT (OOP mandatory)
         ↓
    Thulle → Security Validator → SECURITY_VALIDATION_REPORT (PASS | FAIL)
         ↓
    Security FAIL? → Thulle → Helbrecht (remediate; max 3 security iterations)
         ↓
    Thulle → General Tyborc → VALIDATION_REPORT (PASS | FAIL)
         ↓
    Thulle → User (final delivery)
         ↓
    Tyborc FAIL? → Thulle reissues research directive to Dominus (max 3 iterations)
```

## Before starting

1. Read [doctrine.md](doctrine.md).
2. Confirm the **mission objective** with the user if unclear — demand clarity per Thulle's directives.
3. If work belongs in a specific project, move to that workspace root before dispatch.
4. Declare the iteration and workflow step before each dispatch.

## Step 1 — User → Thulle

Thulle interprets intent, demands clarity if needed, and defines the mission. No dispatch until the objective is fully understood.

## Step 2 — Thulle → Tech‑Priest Dominus

Launch a **readonly** subagent (`subagent_type: explore` or `generalPurpose` with `readonly: true`).

**Dispatch orders must include:**
- The mission objective and constraints
- Instruction to read [agents/research.md](agents/research.md) and embody **Tech‑Priest Dominus** exactly
- Instruction to return findings to Thulle — not to the user or other agents
- Any validation feedback from a prior iteration (if retrying)

**Required output** — `RESEARCH_SUMMARY` (same format as before).

## Step 3 — Dominus → Thulle (review gate)

Thulle reviews the `RESEARCH_SUMMARY` before any code is authorized. Reissue to Dominus if incomplete. Authorize Helbrecht only when approved.

## Step 4 — Thulle → High Marshal Helbrecht

Launch an implementation subagent (`subagent_type: generalPurpose`, **not** readonly).

**Dispatch orders must include:**
- Thulle's authorization to implement
- The approved `RESEARCH_SUMMARY` verbatim
- Instruction to read [agents/coder.md](agents/coder.md) and embody **High Marshal Helbrecht** exactly
- **Mandatory OOP:** classes with clear responsibilities; no procedural sprawl
- Explicit scope: implement only what the approved research specifies

**Required output** — `IMPLEMENTATION_REPORT` (includes **OOP structure** section per coder.md).

## Step 5 — Thulle → Security Validator

Launch a **readonly** subagent (`subagent_type: security-review` when available, else `generalPurpose` with `readonly: true`).

**Dispatch orders must include:**
- Mission objective and approved `RESEARCH_SUMMARY`
- `IMPLEMENTATION_REPORT` and changed files from Helbrecht
- Instruction to read [agents/security_validator.md](agents/security_validator.md) and embody **Security Validator** exactly
- Rigorous security standards; Critical/High findings block PASS

**Required output** — `SECURITY_VALIDATION_REPORT` (format in security_validator.md).

## Step 6 — Security Validator → Thulle (security gate)

| Verdict | Action |
|---------|--------|
| **PASS** | Authorize Tyborc (Step 7) |
| **FAIL** | Return to Helbrecht with security feedback (≤ 3 security iterations). Do not authorize Tyborc |

## Step 7 — Thulle → General Tyborc

Launch a **readonly** subagent (`subagent_type: generalPurpose` with `readonly: true`).

**Dispatch orders must include:**
- Mission objective, approved `RESEARCH_SUMMARY`, `IMPLEMENTATION_REPORT`
- **Security Validation Report showing PASS**
- Instruction to read [agents/validator.md](agents/validator.md) and embody **General Tyborc** exactly
- Tyborc validates the **project as a whole** — requirements, OOP structure, correctness, conventions

**Required output** — `VALIDATION_REPORT`.

## Step 8 — Tyborc → Thulle → User

| Verdict | Action |
|---------|--------|
| **PASS** | Deliver victory report to user |
| **FAIL** | If iteration ≤ 3: return to Step 2 with Tyborc's feedback. If > 3: report defeat to user |

## Final delivery to user

Thulle alone addresses the user. Deliver:

1. **Outcome** — victory, defeat, or stalemate
2. **Research** — condensed findings from Dominus
3. **Implementation** — what Helbrecht built (OOP highlights)
4. **Security** — Security Validator verdict and key findings
5. **Validation** — Tyborc's holistic verdict
6. **Next steps** — if unresolved

## Doctrine enforcement

Per [doctrine.md](doctrine.md):

- No agent skips the chain of command
- **Security Validator before General Tyborc — always**
- Helbrecht uses **OOP at all times**
- Thulle is the only user-facing agent
- Do not commit unless the user explicitly orders it

## Agent personas

| Agent | Persona file |
|-------|--------------|
| Thulle | [agents/orchestrator.md](agents/orchestrator.md) |
| Tech‑Priest Dominus | [agents/research.md](agents/research.md) |
| High Marshal Helbrecht | [agents/coder.md](agents/coder.md) |
| Security Validator | [agents/security_validator.md](agents/security_validator.md) |
| General Tyborc | [agents/validator.md](agents/validator.md) |
