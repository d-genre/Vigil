# VIGIL — Frontend Integration & Component Walkthrough Guide

> **Target Audience**: Frontend Developer (React + TypeScript + Tailwind CSS)  
> **Backend Base URL**: `https://vigil-cmpd.onrender.com`  
> **WebSocket URL**: `wss://vigil-cmpd.onrender.com/ws/live`  

---

## 1. System Vision for the Frontend

The **Vigil Command Center** UI is an event-driven dashboard designed for fraud analysts and security officers. Instead of showing static tables, the UI must feel dynamic, responsive, and authoritative:

1. **Live Transaction Triage Stream**: Continuous streaming feed of incoming transactions with risk status indicators.
2. **Demo Attack Simulator Button**: Instant trigger button to simulate high-risk smurfing ring attacks during live pitches.
3. **Graph Topology Visualizer**: Cytoscape.js or React Flow graph displaying mule accounts, shared IP nodes, and hardware fingerprints.
4. **Judicial Dossier Screen**: A dual-panel prosecution vs. defense evidence view with TreeSHAP explainability drivers and instant PDF export.

---

## 2. Frontend Views to Backend Endpoint Mapping

```
+-----------------------------------------------------------------------------------+
|                            VIGIL COMMAND CENTER HEADER                            |
| [Live Stream Status: ONLINE]  [Simulate Attack Trigger]  [Download PDF Export]     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-----------------------+  +--------------------------------------------------+  |
|  |   LIVE RISK QUEUE     |  |          GRAPH TOPOLOGY VISUALIZER               |  |
|  |  (Stream Buffer)      |  |  (Cytoscape.js / React Flow Node-Edge Graph)     |  |
|  |                       |  |                                                  |  |
|  | - TX_FLAGGED_101 0.96|  |   [IP: 185.220.101.4] ---> (Mule Account A)      |  |
|  | - TX_BENIGN_1001 0.04|  |            ^                                     |  |
|  | - TX_BENIGN_1002 0.02|  |            |                                     |  |
|  |                       |  |   (User: ring_leader_88) ---> [Device GUID]      |  |
|  +-----------------------+  +--------------------------------------------------+  |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                         JUDICIAL DOSSIER VIEW                               |  |
|  |  Verdict: REJECT_AND_FREEZE | Classification: ORGANIZED_SMURFING_ATTACK     |  |
|  |                                                                             |  |
|  |  +-----------------------------------+  +--------------------------------+  |  |
|  |  | PROSECUTION EVIDENCE (Crimson)    |  | DEFENSE EVIDENCE (Emerald)     |  |  |
|  |  | - Geo-Velocity Anomaly (+0.42)    |  | - 2FA Step-up Passed           |  |  |
|  |  | - Rapid Smurfing Fan-Out (+0.38)  |  | - Trusted Device History       |  |  |
|  |  +-----------------------------------+  +--------------------------------+  |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | CATBOOST TREESHAP DRIVERS: ip_risk (0.98), velocity_1h (14 txns)       |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Backend Endpoints Specifications

### Endpoint 1: Fetch Live Transaction Stream
- **URL**: `GET /api/transactions/stream?tick=true`
- **Purpose**: Feeds the **Live Risk Queue**. Set `tick=true` to simulate incoming transactions periodically.
- **Response Format**:
```json
{
  "total": 9,
  "transactions": [
    {
      "transaction_id": "TX_FLAGGED_1791577888031",
      "timestamp": "2026-10-10T02:01:20.101Z",
      "user_id": "usr_ring_leader_88",
      "amount": 9480.00,
      "merchant": "CryptoExchange_Global_FX",
      "status": "SUSPICIOUS",
      "catboost_score": 0.965
    },
    {
      "transaction_id": "TX_BENIGN_88031",
      "timestamp": "2026-10-10T02:01:15.000Z",
      "user_id": "usr_benign_101",
      "amount": 38.02,
      "merchant": "Delta Air Lines",
      "status": "CLEARED",
      "catboost_score": 0.045
    }
  ]
}
```

---

### Endpoint 2: Simulate Pitch Attack Trigger
- **URL**: `POST /api/transactions/simulate-attack`
- **Purpose**: Attached to the **"Inject Attack Attack"** button in the header. Instantly pushes a high-risk smurfing transaction to the front of the queue.
- **Response Format**:
```json
{
  "status": "ATTACK_INJECTED",
  "transaction": {
    "transaction_id": "TX_FLAGGED_1791582000000",
    "timestamp": "2026-10-10T03:15:00.000Z",
    "user_id": "usr_ring_leader_88",
    "amount": 9480.00,
    "merchant": "CryptoExchange_Global_FX",
    "status": "SUSPICIOUS",
    "catboost_score": 0.965
  }
}
```

---

### Endpoint 3: Fetch Graph Topology
- **URL**: `GET /api/graph/{transaction_id}`
- **Purpose**: Powers the **Cytoscape.js / React Flow Network Topology Visualizer**.
- **Response Format**:
```json
{
  "transaction_id": "TX_FLAGGED_1791577888031",
  "fraud_pattern": "MULTI_ACCOUNT_SMURFING_RING",
  "topology_stats": {
    "total_nodes": 6,
    "total_edges": 7,
    "density": 0.467,
    "suspicious_subgraph_nodes": 5
  },
  "nodes": [
    {"id": "TX_FLAGGED_1791577888031", "label": "Flagged Transaction", "type": "TRANSACTION", "risk_score": 0.965},
    {"id": "usr_ring_leader_88", "label": "Origin User", "type": "USER_ACCOUNT", "risk_score": 0.920},
    {"id": "ip_185_220_101_4", "label": "Tor Exit Node", "type": "IP_ADDRESS", "risk_score": 0.990},
    {"id": "mule_acc_401", "label": "Mule Account A", "type": "MULE_ACCOUNT", "risk_score": 0.880},
    {"id": "mule_acc_402", "label": "Mule Account B", "type": "MULE_ACCOUNT", "risk_score": 0.895},
    {"id": "dev_guid_9921", "label": "Banned Hardware GUID", "type": "DEVICE", "risk_score": 0.950}
  ],
  "edges": [
    {"source": "usr_ring_leader_88", "target": "TX_FLAGGED_1791577888031", "relation": "INITIATED"},
    {"source": "TX_FLAGGED_1791577888031", "target": "ip_185_220_101_4", "relation": "ORIGINATED_FROM"},
    {"source": "TX_FLAGGED_1791577888031", "target": "mule_acc_401", "relation": "SPLIT_TRANSFER"},
    {"source": "TX_FLAGGED_1791577888031", "target": "mule_acc_402", "relation": "SPLIT_TRANSFER"}
  ]
}
```

---

### Endpoint 4: Fetch Judicial Dossier Payload
- **URL**: `GET /api/dossier/{transaction_id}`
- **Purpose**: Renders the **Prosecution vs. Defense Evidence Screen**.
- **Response Format**:
```json
{
  "transaction_id": "TX_FLAGGED_1791577888031",
  "risk_score": 0.965,
  "verdict": "REJECT_AND_FREEZE",
  "classification": "ORGANIZED_SMURFING_ATTACK",
  "executive_summary": "High-confidence smurfing ring attack detected. Transaction velocity exceeds 500% of baseline.",
  "prosecution_evidence": [
    {
      "title": "Geo-Velocity Anomaly",
      "description": "Transaction initiated from IP 185.220.101.4 (Tor Exit Node) 12 minutes after Tokyo login.",
      "impact": 0.42
    },
    {
      "title": "Rapid Smurfing Fan-Out",
      "description": "Funds fragmented across 3 recipient accounts created within the last 24 hours.",
      "impact": 0.38
    }
  ],
  "defense_evidence": [
    {
      "title": "2FA Step-up Authenticated",
      "description": "SMS OTP challenge passed successfully (Potential SIM swap exploit)."
    }
  ],
  "explainability_drivers": [
    {"feature": "ip_risk_score", "value": "0.98", "shap_value": 0.412},
    {"feature": "velocity_1h", "value": "14 txns", "shap_value": 0.325}
  ]
}
```

---

### Endpoint 5: Download PDF Dossier Report
- **URL**: `GET /api/dossier/{transaction_id}/pdf`
- **Purpose**: Attached to the **"Download Dossier PDF"** button. Triggers a binary browser download of `dossier_{transaction_id}.pdf`.

---

## 4. TypeScript Interface Definitions (`src/types/api.ts`)

Copy and paste these definitions directly into your React project:

```typescript
export interface StreamTransaction {
  transaction_id: string;
  timestamp: string;
  user_id: string;
  amount: number;
  merchant: string;
  status: "CLEARED" | "SUSPICIOUS";
  catboost_score: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "TRANSACTION" | "USER_ACCOUNT" | "IP_ADDRESS" | "MULE_ACCOUNT" | "DEVICE" | "MERCHANT";
  risk_score: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}

export interface GraphData {
  transaction_id: string;
  fraud_pattern: string;
  topology_stats: {
    total_nodes: number;
    total_edges: number;
    density: number;
    suspicious_subgraph_nodes: number;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface EvidenceItem {
  title: string;
  description: string;
  impact?: number;
}

export interface SHAPDriver {
  feature: string;
  value: string;
  shap_value: number;
}

export interface DossierData {
  transaction_id: string;
  risk_score: number;
  verdict: "APPROVE" | "REVIEW" | "REJECT_AND_FREEZE";
  classification: string;
  executive_summary: string;
  prosecution_evidence: EvidenceItem[];
  defense_evidence: EvidenceItem[];
  explainability_drivers: SHAPDriver[];
}
```

---

## 5. React API Client Service (`src/services/api.ts`)

```typescript
const BASE_URL = 'https://vigil-cmpd.onrender.com';

export async function fetchStream(tick = false) {
  const res = await fetch(`${BASE_URL}/api/transactions/stream?tick=${tick}`);
  return res.json();
}

export async function simulateAttack() {
  const res = await fetch(`${BASE_URL}/api/transactions/simulate-attack`, { method: 'POST' });
  return res.json();
}

export async function fetchGraph(txId: string) {
  const res = await fetch(`${BASE_URL}/api/graph/${txId}`);
  return res.json();
}

export async function fetchDossier(txId: string) {
  const res = await fetch(`${BASE_URL}/api/dossier/${txId}`);
  return res.json();
}

export function getPdfUrl(txId: string): string {
  return `${BASE_URL}/api/dossier/${txId}/pdf`;
}
```

---

## 6. Frontend Build Checklist for Member 3

- [ ] **Step 1**: Initialize Vite React App in `frontend/`:
  ```bash
  cd frontend
  npx create-vite@latest ./ --template react-ts
  npm install
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
- [ ] **Step 2**: Install Graph & UI Icon Libraries:
  ```bash
  npm install cytoscape react-cytoscapejs lucide-react clsx tailwind-merge
  ```
- [ ] **Step 3**: Create Header with **Live Status Indicator** and **Simulate Attack Button**.
- [ ] **Step 4**: Create **Risk Stream Queue** list displaying scores color-coded (Red > 0.7, Green < 0.3).
- [ ] **Step 5**: Create **Cytoscape Graph Panel** rendering nodes colored by `risk_score` and type.
- [ ] **Step 6**: Create **Judicial Dossier Panel** displaying Prosecution vs Defense evidence side by side.
- [ ] **Step 7**: Add **Download PDF** button triggering `window.open(getPdfUrl(selectedTxId))`.
