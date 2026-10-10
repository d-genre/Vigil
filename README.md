# Vigil — Autonomous Fraud Investigation Agent

**One-Line Pitch:** Vigil streams live transactions, screens them using CatBoost and TreeSHAP, reconstructs dynamic fraud graphs and geo-travel maps, synthesizes judicial prosecution vs. defense evidence, and generates audit-grade PDF dossiers for human-in-the-loop decisions.

---

## 🚀 Overview

**Vigil** is an AI-powered autonomous fraud investigation and triage platform designed for modern financial compliance.

Unlike traditional static fraud classifiers that merely output opaque binary flags, Vigil operates as an end-to-end autonomous investigation cockpit:

1. **Continuous Ingestion & Ticking Stream:** Ingests live transactional data via an automated 15-second simulation loop backed by an in-memory ring buffer.
2. **Behavioral Screening & TreeSHAP Drivers:** Evaluates 30+ features using CatBoost and extracts exact feature-level TreeSHAP contributions to quantify risk drivers without black-box ambiguity.
3. **Behavioral Pattern Recognition:** Analyzes 7 specialized fraud signatures (Impossible Travel, Velocity Burst, Smurfing, ATO, Device Syndicates, Card Testing, and Rapid Drain).
4. **Dynamic Network & Geo Forensics:** Reconstructs fraudster ego networks (degrees of separation across merchants, IPs, and devices) and tracks global IP hops with impossible travel velocity calculations.
5. **Judicial Evidence Synthesis:** Functions as a digital fraud prosecutor, balancing incriminating **Prosecution Evidence** against mitigating **Defense Counter-Evidence** ("Why NOT to block").
6. **Live Pitch Attack Injection:** Features an unlabelled, single-click attack trigger to inject anomalies directly into the stream for live validation.
7. **On-Demand PDF Dossier Exporter:** Generates full, multi-section binary PDF investigation case files for human analysts, compliance officers, and legal auditors.

---

## ✨ Key Features

* ⚡ **15-Second Automated Stream Engine:** In-memory `deque` buffer running an autonomous background heartbeat, continuously scoring benign transactions alongside anomalous edge cases.
* 🎯 **Single-Click Live Attack Trigger:** On-demand injection endpoint (`/api/transactions/simulate-attack`) that routes an untagged synthetic attack into the live screening pipeline without exposing pre-selected fraud labels.
* 🌲 **TreeSHAP Explainability Layer:** Direct mathematical attribution of risk factors (e.g., `geo_velocity: +0.412`, `device_trust_score: -0.310`) to justify flags transparently.
* 🔍 **7 Behavioral Anomaly Detectors:** Dedicated heuristic modules targeting Impossible Travel (>800 km/h), Velocity Bursts, Mule Chains, Account Takeover (ATO), Device Syndicates, Card Testing, and Rapid Balance Drain.
* 🕸️ **Dynamic Fraudster Ego Network:** Topology graph derived dynamically per transaction, visually mapping hops across accounts, compromised devices, Tor exit IPs, and mule endpoints with narrative analysis.
* 🌍 **Temporal Geo-Velocity Map:** Global interactive IP hop tracker calculating geographical transit speed ($\Delta t$ vs distance) to pinpoint physical impossibility violations.
* ⚖️ **Judicial Dossier Engine:** Balanced investigative evaluation contrasting positive risk flags with mitigating factors (3DS verification, habitual merchant match, trusted billing zip).
* 📑 **Audit-Ready PDF Dossier Exporter:** High-resolution PDF generation endpoint (`/api/dossier/{id}/pdf`) compiling the case summary, quantitative feature tables, dual-column evidence files, and recommended remediation protocols.
* 👤 **Human-in-the-Loop Governance:** Defensible verdict recommendations (`APPROVE`, `STEP_UP_VERIFICATION`, `DECLINE_AND_FREEZE`) preserving final decision authority for fraud analysts.

---

## 🛠️ Technology Stack

| Domain | Technologies |
| --- | --- |
| **Core & Backend** | Python 3.10+, FastAPI, Uvicorn, Pydantic v2, `asyncio` |
| **ML & Explainability** | CatBoost Classifier, TreeSHAP, NumPy, Pandas |
| **Graph & Spatial Analysis** | NetworkX, GeoPy, Plotly Geo / Mapbox |
| **Dossier & Document Export** | ReportLab / fpdf2, in-memory `io.BytesIO` Streaming |
| **Frontend UI** | React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons |
