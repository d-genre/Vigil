# VIGIL — BACKEND API CONTRACTS

This document specifies the REST API endpoints and WebSocket channels for the Vigil backend service.

---

## 1. System & Health

### `GET /health`
* **Purpose**: Verify backend service readiness and subsystem health status.
* **Request**: None
* **Response** (200 OK):
  ```json
  {
    "status": "ok",
    "version": "1.0.0",
    "subsystems": {
      "ml_screening": "ready",
      "graph_engine": "ready",
      "vector_memory": "ready",
      "database": "connected"
    }
  }
  ```

---

## 2. Transactions & Streaming

### `GET /transactions`
* **Purpose**: Retrieve paginated list of processed transactions.
* **Query Parameters**:
  - `limit` (int, default: 50)
  - `offset` (int, default: 0)
  - `risk_level` (string, optional: `LOW`, `MEDIUM`, `HIGH`)
* **Response** (200 OK):
  ```json
  {
    "total": 120,
    "transactions": [
      {
        "transaction_id": "TX8421",
        "timestamp": "2026-10-08T20:40:00",
        "account_id": "C102",
        "amount": 28900.0,
        "risk_level": "HIGH",
        "fraud_probability": 0.91
      }
    ]
  }
  ```

### `GET /transactions/live`
* **Purpose**: Fetch recent live transactions buffer for dashboard display.
* **Response** (200 OK): Returns list of recent transactions.

### `POST /transactions`
* **Purpose**: Submit a single incoming transaction for real-time screening and processing.
* **Request Body**: `Transaction` object (see `DATA_CONTRACTS.md`).
* **Response** (201 Created):
  ```json
  {
    "transaction_id": "TX8421",
    "fraud_probability": 0.91,
    "risk_level": "HIGH",
    "action_taken": "INVESTIGATION_TRIGGERED",
    "case_id": "CASE_8421"
  }
  ```

---

## 3. Autonomous Investigations

### `GET /investigations/{case_id}`
* **Purpose**: Retrieve full investigation details, collected evidence, counter-evidence, graph topology, and LLM explanation.
* **Response** (200 OK / 404 Not Found): Full `InvestigationState` object.

### `POST /investigations`
* **Purpose**: Manually trigger an autonomous investigation on an arbitrary transaction ID.
* **Request Body**: `{"transaction_id": "TX8421"}`
* **Response** (202 Accepted): `{"case_id": "CASE_8421", "status": "INVESTIGATING"}`

---

## 4. Case Management & Human-in-the-Loop

### `GET /cases`
* **Purpose**: List flagged cases in the analyst risk queue.
* **Query Parameters**: `status` (`PENDING_REVIEW`, `RESOLVED`), `risk_level` (`HIGH`, `MEDIUM`).
* **Response** (200 OK): List of `Case` objects.

### `GET /cases/{case_id}`
* **Purpose**: Get specific case metadata and analyst decision history.
* **Response** (200 OK): Single `Case` object.

### `POST /cases/{case_id}/decision`
* **Purpose**: Submit human analyst decision for a flagged case.
* **Request Body**:
  ```json
  {
    "action": "BLOCK",
    "reason": "Confirmed ATO pattern via device sharing analysis.",
    "analyst_id": "ANALYST_42"
  }
  ```
* **Response** (200 OK):
  ```json
  {
    "case_id": "CASE_8421",
    "status": "RESOLVED",
    "decision": "BLOCK",
    "updated_at": "2026-10-08T20:45:12Z"
  }
  ```

---

## 5. Attack Simulator & Attack Memory

### `GET /attacks`
* **Purpose**: Get list of available synthetic attack scenarios in the Attack Lab.
* **Response** (200 OK):
  ```json
  {
    "scenarios": [
      {
        "scenario_id": "ATO_BURST_01",
        "name": "Account Takeover Surge",
        "description": "Simulates 50 ATO transactions across high-value accounts."
      }
    ]
  }
  ```

### `POST /attacks/trigger`
* **Purpose**: Launch a synthetic attack scenario into the transaction stream.
* **Request Body**: `{"scenario_id": "ATO_BURST_01", "rate_per_sec": 10}`
* **Response** (202 Accepted): `{"simulation_id": "SIM_901", "status": "RUNNING"}`

### `GET /memory/similar/{case_id}`
* **Purpose**: Retrieve top-N historical attack vectors similar to the current case using FAISS vector search.
* **Query Parameters**: `top_k` (int, default: 3)
* **Response** (200 OK): List of `SimilarAttackResult` objects.

---

## 6. Evaluation & Metrics

### `GET /evaluation`
* **Purpose**: Get live performance and benchmark metrics for the evaluation dashboard.
* **Response** (200 OK):
  ```json
  {
    "total_screened": 15000,
    "flagged_cases": 320,
    "precision": 0.94,
    "recall": 0.91,
    "f1_score": 0.925,
    "avg_investigation_time_ms": 420
  }
  ```

---

## 7. WebSockets

### `ws://localhost:8000/ws/live`
* **Purpose**: Real-time push feed for live transaction streaming, immediate high-risk alerts, and investigation state updates.
* **Event Types**:
  - `TRANSACTION_SCREENED`: Sent for every processed transaction.
  - `CASE_FLAGGED`: Sent when CatBoost or rules flag high risk.
  - `INVESTIGATION_UPDATE`: Sent when agent completes evidence collection.
