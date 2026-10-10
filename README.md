# VIGIL — Autonomous AI Fraud Governance & Judicial Command Center

> **One-Line Pitch**: Vigil replaces opaque binary fraud scoring with an **Autonomous Judicial Investigation Engine** — screening live transactions using CatBoost and TreeSHAP, detecting complex behavioral patterns, mapping dynamic fraud ring graph topologies, and synthesizing auditable **Prosecution vs. Defense Evidence** into downloadable Judicial Dossiers.

---

## 📸 System Architecture & End-to-End Pipeline

```
                     +---------------------------------------+
                     |         Live Transaction Stream       |
                     | (StreamManager / DB / Ingestion API)  |
                     +-------------------+-------------------+
                                         |
                                         v
                     +-------------------+-------------------+
                     |      ML Screening Service (CatBoost)   |
                     |   Calculates Risk Score & SHAP Values |
                     +-------------------+-------------------+
                                         |
                                         v
       +---------------------------------+---------------------------------+
       |                                                                   |
       v                                                                   v
+------+-----------------------------+             +-----------------------+------+
|     7 Fraud Pattern Detectors      |             |     NetworkX Graph Engine       |
| - Impossible Travel  - Mule Chain  |             | - Fraud Ring Discovery        |
| - Velocity Burst     - ATO         |             | - Suspicious Subgraph Trace   |
| - Device Syndicate   - Card Test   |             | - Topology Stats (Density)    |
| - Rapid Drain                      |             +-----------------------+------+
|                                    |                                     |
+------+-----------------------------+                                     |
       |                                                                   |
       +---------------------------------+---------------------------------+
                                         |
                                         v
                     +-------------------+-------------------+
                     |     Vigil Judicial Dossier Engine     |
                     |                                       |
                     |  - Prosecution Evidence (Incriminating)|
                     |  - Defense Evidence (Mitigating)     |
                     |  - TreeSHAP Risk Drivers             |
                     |  - Network Topology Summary           |
                     |  - Final Verdict & Action             |
                     +-------------------+-------------------+
                                         |
                                         v
                     +-------------------+-------------------+
                     |    FastAPI Event-Driven Command Center|
                     |                                       |
                     |  - /api/transactions/stream           |
                     |  - /api/transactions/simulate-attack  |
                     |  - /api/graph/{id}                    |
                     |  - /api/dossier/{id}                  |
                     |  - /api/dossier/{id}/pdf              |
                     +---------------------------------------+
```

---

## 🧠 How Vigil Works: The 5 Core Pillars

### Pillar 1: High-Throughput ML Screening & TreeSHAP Explainability (`ml/`)
- Powered by a **CatBoost classifier** trained on 30+ dynamic behavioral features (velocity windows, haversine location distance, device reuse ratios, historical baseline deviations).
- Generates feature-level **TreeSHAP explainability drivers** (`ip_risk_score: +0.412`, `device_trust_score: -0.310`) to quantify exact risk contributors without black-box ambiguity.

### Pillar 2: 7 Specialized Behavioral Pattern Detectors (`fraud/`)
1. **Impossible Travel**: Flags transactions occurring at physical distances requiring impossible speeds (> 900 km/h).
2. **Velocity Burst**: Detects sudden spikes in transaction volume within short windows (< 60s).
3. **Mule Chain / Smurfing**: Identifies multi-hop money laundering fan-outs where funds are split across newly created accounts.
4. **Account Takeover (ATO)**: Detects credential stuffing followed by immediate high-value password/MFA resets and money transfers.
5. **Device Syndicate**: Flags hardware fingerprint GUIDs shared across multiple unrelated bank accounts.
6. **Card Testing**: Spots automated micro-purchases ($0.50, $1.00) used by fraudsters to test stolen credit card validity.
7. **Rapid Drain**: Flags accounts emptying > 90% of their total balance within minutes of receiving a transfer.

### Pillar 3: Heterogeneous Network Topology Engine (`graph/`)
- Constructs a heterogeneous **NetworkX graph** mapping entity nodes (`TRANSACTION`, `USER_ACCOUNT`, `IP_ADDRESS`, `DEVICE`, `MULE_ACCOUNT`, `MERCHANT`) and relationship edges (`INITIATED`, `ORIGINATED_FROM`, `USED_DEVICE`, `SPLIT_TRANSFER`).
- Detects multi-account smurfing rings, calculates subgraph density, and flags shared suspicious infrastructure (Tor exit nodes, banned GUIDs).

### Pillar 4: Judicial Dossier Engine (`backend/dossier_service.py`)
- Functions like a digital fraud prosecutor:
  - **Prosecution Evidence**: Compiles incriminating signals with positive impact scores.
  - **Defense Counter-Evidence**: Evaluates mitigating factors (e.g., 2FA step-up passed, 120+ clean historic sessions, habitual merchant affinity) to prevent false positives and protect legitimate customers.
  - **Final Verdict**: Issues auditable judgments (`APPROVE`, `REVIEW`, `REJECT_AND_FREEZE`).

### Pillar 5: On-Demand PDF Report Exporter (`backend/pdf_exporter.py`)
- Dynamically compiles Judicial Dossiers into downloadable, legal-grade PDF binary buffers (`/api/dossier/{id}/pdf`) using `fpdf2` with automated unicode sanitization.

---

## ⚡ Command Center API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | API Welcome & Endpoint Index |
| `GET` | `/health` | System health check (ML, DB, Stream status) |
| `GET` | `/api/transactions/stream` | Live transaction stream buffer (Supports `?tick=true`) |
| `POST` | `/api/transactions/simulate-attack` | Injects high-risk attack transaction (`TX_FLAGGED_...`) for pitch demos |
| `GET` | `/api/graph/{transaction_id}` | NetworkX graph nodes, edges, density, and fraud ring pattern |
| `GET` | `/api/dossier/{transaction_id}` | Full JSON Judicial Dossier (Prosecution vs. Defense) |
| `GET` | `/api/dossier/{transaction_id}/pdf` | Downloadable binary PDF Dossier Report stream |
| `WS` | `/ws/live` | WebSocket connection for real-time dashboard UI updates |

---

## 🛠️ Technology Stack

| Domain | Technologies |
|---|---|
| **Core & Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, SQLite |
| **ML & Analytics** | CatBoost, TreeSHAP, Pandas, NumPy, Scikit-learn |
| **Fraud & Graph** | NetworkX, Custom Behavioral Pattern Detectors |
| **PDF Generation** | FPDF2 |
| **Frontend Stack** | React 18, Vite, TypeScript, Tailwind CSS, Cytoscape.js |

---

## 👥 Team & Ownership Boundaries

| Role | Team Member | Owned Directories | Responsibilities |
|---|---|---|---|
| **ML Engineer** | Member 1 | `ml/` | Dataset preparation, feature engineering, CatBoost classifier, model evaluation, prediction interface. |
| **Fraud & Graph** | Member 2 | `fraud/`, `graph/` | 7 pattern detectors, NetworkX graph construction, suspicious path detection, fraud ring analysis. |
| **Frontend** | Member 3 | `frontend/` | React UI, Live Feed, Risk Queue, Cytoscape visualizer, Dossier view. |
| **Backend & Integration** | Member 4 | `backend/` | FastAPI routes, Dossier Engine, Stream Manager, PDF exporter, SQLite integration. |
| **Shared** | All | `schemas/`, `docs/` | Shared Pydantic data models & API contracts. |

---

## 💻 Quick Start & Execution

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)

### 2. Environment Setup
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Launch Backend API Server
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Interactive API Documentation
Open your browser and navigate to:  
👉 `http://localhost:8000/docs`

### 5. Run Verification Audit Suite
```bash
python scratch/verify_all_6_layers.py
```

---

## 📄 Core Documentation Links

- [`AGENTS.md`](file:///c:/Divya/College/hackathons/agnitia/AGENTS.md): AI Agent Governance & Team Rules
- [`PROJECT_WALKTHROUGH.md`](file:///c:/Divya/College/hackathons/agnitia/docs/PROJECT_WALKTHROUGH.md): Detailed Codebase & Architectural Walkthrough
- [`FRONTEND_INTEGRATION_GUIDE.md`](file:///c:/Divya/College/hackathons/agnitia/docs/FRONTEND_INTEGRATION_GUIDE.md): React UI Component & API Integration Guide
