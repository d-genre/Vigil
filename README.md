# Vigil — Autonomous Fraud Investigation Agent

> **One-Line Pitch**: Vigil detects suspicious transactions, reconstructs fraud networks, identifies attack patterns, retrieves similar historical attacks, collects auditable evidence, explains the risk, and pauses for human decision.

---

## 🚀 Overview

Vigil is an AI-powered autonomous fraud investigation system developed for the **APEX06 / Fraud-Ring Radar** 36-hour hackathon. 

Unlike traditional static fraud classifiers that merely output binary flags, Vigil performs end-to-end autonomous investigation:
1. **Screening**: Screens incoming transactions instantly via a fast CatBoost model.
2. **Orchestration**: Triggers a LangGraph investigation agent for medium/high risk cases.
3. **Pattern & Graph Analysis**: Evaluates 7 complex fraud pattern signatures and constructs NetworkX fraud topology graphs.
4. **Vector Memory**: Searches historical attack vectors using FAISS vector similarity.
5. **Auditable Evidence**: Gathers positive risk indicators alongside counter-evidence ("Why NOT to block").
6. **LLM Reasoning**: Generates structured, explainable case summaries and recommended actions without hallucinated data.
7. **Human Governance**: Presents findings to human fraud analysts for final decision (`APPROVE`, `HOLD`, `ESCALATE`, `BLOCK`).

---

## ✨ Key Features

* ⚡ **Real-time Transaction Screening**: High-throughput screening layer powered by CatBoost.
* 🔍 **Seven Specialized Fraud Pattern Detectors**: Card Testing, ATO, Mule Account Chain, Synthetic Identity, Push Payment Scam, Beneficiary ATO, and Coordinated Fraud Ring.
* 🕸️ **Fraud Network Graph**: Reconstructs account-device-IP relationships and detects multi-hop money laundering paths using NetworkX.
* 🛡️ **Evidence & Counter-Evidence Engine**: Collects balance of evidence supporting both risk escalation and approval justification.
* 🧠 **Vector Similarity Memory**: FAISS-backed semantic search for matching current topologies to historical attack databases.
* 🤖 **Autonomous Agentic Workflow**: LangGraph state machine orchestrating multi-step investigation processes.
* 💬 **Grounded LLM Explanation**: Transparent, auditable natural language explanations derived strictly from structured evidence.
* 👤 **Human-in-the-Loop Control**: Analyst decision dashboard preserving human control over blocking actions.
* 🧪 **Attack Lab & Simulator**: Interactive attack pattern injection for testing system resiliency.
* 📊 **Evaluation Dashboard**: Live tracking of precision, recall, detection latency, and false positive rates.

---

## 🛠️ Technology Stack

| Domain | Technologies |
|---|---|
| **Core & Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic, SQLite |
| **ML & Analytics** | CatBoost, Pandas, NumPy, Logistic Regression |
| **Orchestration** | LangGraph |
| **Graph & Vectors** | NetworkX, FAISS (`faiss-cpu`), Sentence Transformers |
| **Frontend UI** | React, TypeScript, Tailwind CSS, Cytoscape.js, Recharts |

---

## 👥 Team & Module Ownership

| Member | Domain | Owned Directories | Focus |
|---|---|---|---|
| **Member 1** | ML Engineer | `ml/` | CatBoost classifier, feature engineering, baselines, model evaluation. |
| **Member 2** | Fraud & Graph | `fraud/`, `graph/` | 7 fraud pattern detectors, behavioral rules, NetworkX graph analysis. |
| **Member 3** | Frontend | `frontend/` | React dashboard, live stream, network visualizer, evaluation UI. |
| **Member 4** | Backend & Integration | `backend/` | FastAPI routes, LangGraph workflow, FAISS memory, SQLite integration. |
| **Shared** | Architecture & Contracts | `schemas/`, `docs/` | Shared Pydantic schemas, data/API specifications. |

---

## 💻 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend development)

### Setup & Backend Execution
1. Clone the repository and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables configuration:
   ```bash
   cp .env.example .env
   ```
5. Launch the backend API server:
   ```bash
   uvicorn backend.main:app --reload
   ```
6. Access the API documentation at `http://localhost:8000/docs`.

---

## 📄 Documentation

- [AGENTS.md](file:///c:/Divya/College/hackathons/agnitia/AGENTS.md): AI Agent governance and rules.
- [ARCHITECTURE.md](file:///c:/Divya/College/hackathons/agnitia/ARCHITECTURE.md): System architecture and data pipeline specification.
- [CONTRIBUTING.md](file:///c:/Divya/College/hackathons/agnitia/CONTRIBUTING.md): Git branching model and PR standards.
- [DATA_CONTRACTS.md](file:///c:/Divya/College/hackathons/agnitia/docs/DATA_CONTRACTS.md): Shared Pydantic and JSON data schemas.
- [API_CONTRACTS.md](file:///c:/Divya/College/hackathons/agnitia/docs/API_CONTRACTS.md): REST API and WebSocket specifications.
