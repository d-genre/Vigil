# VIGIL — AI AGENT GOVERNANCE & RULES

> **IMPORTANT**: This document is the primary instruction file for all AI coding agents (and human developers) working on the Vigil repository. All agents MUST strictly adhere to these rules.

---

## 1. General Workflow Rules

Before writing code or making any changes, every AI agent MUST:
1. **Read `AGENTS.md`** (this document).
2. **Read `ARCHITECTURE.md`** to understand the system pipeline and component responsibilities.
3. **Read `CONTRIBUTING.md`** for Git workflow, branching, and PR rules.
4. **Read shared contracts**:
   - `docs/DATA_CONTRACTS.md`
   - `docs/API_CONTRACTS.md`
   - `schemas/`
5. **Inspect the existing repository** and existing module implementation.
6. **Respect module ownership boundaries**.
7. **Do NOT redesign the core architecture** unless explicitly instructed by the human team lead.

---

## 2. Module Ownership & Team Boundaries

The codebase is strictly divided among four team members to allow safe, parallel development. AI agents operate *only* within their assigned member's ownership boundary.

| Role | Team Member | Owned Directories | Core Responsibilities |
|---|---|---|---|
| **ML Engineer** | Member 1 | `ml/` | Dataset preparation, feature engineering, CatBoost classifier, Logistic Regression baseline, model evaluation, prediction interface (`predict()`), saved model artifacts. |
| **Fraud & Graph** | Member 2 | `fraud/`<br>`graph/` | 7 fraud pattern detectors, behavioral pattern logic, NetworkX graph construction, graph feature extraction, suspicious path detection, fraud-ring analysis. |
| **Frontend** | Member 3 | `frontend/` | React + TypeScript + Tailwind CSS UI, Live Feed, Risk Queue, Investigation Screen, Cytoscape.js/React Flow network visualizer, Evidence & Counter-Evidence Display, Attack Lab, Evaluation Dashboard. |
| **Backend & Integration** | Member 4 | `backend/` | FastAPI endpoints, LangGraph orchestration workflow, Evidence Engine, FAISS vector similarity memory, Attack Scheduler, Transaction Generator integration, SQLite persistence, module integration. |
| **Shared (Read-Only for Individuals)** | **ALL** | `schemas/`<br>`docs/` | Shared Pydantic data models (`Transaction`, `Investigation`, `Evidence`, `Case`), Data & API Contracts. |

---

## 3. Critical AI-Agent Rules

### 3.1 MANDATORY BEHAVIORS (Agents MUST)
* **Preserve Working Code**: Do not overwrite or delete existing functional code written by other team members.
* **Follow Shared Schemas**: Use `schemas/` as the single source of truth for all data structures across ML, Fraud, Graph, Backend, and Frontend.
* **Adhere to API Contracts**: Respect `docs/API_CONTRACTS.md` for endpoint routes, request payloads, and response fields.
* **Keep Functions Modular**: Write clean, testable, single-responsibility functions.
* **Write Unit & Integration Tests**: Place unit and integration tests in `tests/` for critical business logic.
* **Use Environment Variables**: Load secrets and configuration from `.env` using `python-dotenv`. Never hardcode secrets.
* **Report Architectural Conflicts**: If an interface mismatch or schema conflict is found, flag it immediately.
* **Keep Artifacts Out of Git**: Ensure large datasets, trained model binaries (`.cbm`, `.pkl`), vector indexes (`.faiss`), and SQLite databases are placed in `data/` or ignored via `.gitignore`.

### 3.2 PROHIBITED BEHAVIORS (Agents MUST NOT)
* ❌ **DO NOT Modify Other Members' Directories**: An agent working for Member 1 must not edit `backend/` or `fraud/`, etc.
* ❌ **DO NOT Make Uncoordinated Changes to Shared Schemas**: Never alter fields in `schemas/` or `docs/` without explicit alignment across all team members.
* ❌ **DO NOT Change API Response Formats Silently**: Frontend and Backend rely on agreed JSON schemas.
* ❌ **DO NOT Over-Engineer or Add Unapproved Infrastructure**: Kafka, Kubernetes, Neo4j, Docker Swarm, Redis, or microservice meshes are strictly out of scope for this hackathon project.
* ❌ **DO NOT Replace Chosen Technologies**: Stick to FastAPI, CatBoost, LangGraph, NetworkX, FAISS, React, and Cytoscape.js.
* ❌ **DO NOT Commit directly to `main`**: All work must be done on designated feature branches (`feature/ml`, `feature/fraud-graph`, `feature/frontend`, `feature/backend`).
* ❌ **DO NOT Fabricate ML Results or Evidence**: The LLM must reason strictly over structured, rule-generated evidence. It must never hallucinate fraud signals or fake transaction records.

---

## 4. Conflict Resolution Procedure

If an AI agent encounters an architectural conflict, ambiguous specification, or schema mismatch:

1. **STOP** writing code immediately.
2. **Explain the conflict clearly** detailing the mismatched modules/schemas.
3. **Ask the human team lead** for explicit direction before proceeding.
