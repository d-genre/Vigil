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
        "timestamp": "2026-10-08T20:40:00Z",
        "account_id": "C102",
        "amount": 28900.0,
        "currency": "USD",
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
* **Response** (200 OK / 404 Not Found):
  ```json
  {
    "case_id": "CASE_8421",
    "transaction": {
      "transaction_id": "TX8421",
      "account_id": "C102",
      "amount": 28900.0,
      "currency": "USD",
      "device_id": "D901",
      "ip": "185.220.101.4",
      "beneficiary_id": "B221",
      "timestamp": "2026-10-08T20:40:00Z",
      "location": "London",
      "transaction_type": "TRANSFER"
    },
    "ml_risk_score": {
      "transaction_id": "TX8421",
      "fraud_probability": 0.91,
      "risk_level": "HIGH",
      "model_version": "catboost_v1.0"
    },
    "matched_patterns": [
      {
        "pattern_name": "IMPOSSIBLE_TRAVEL",
        "detected": true,
        "confidence": 0.96,
        "matched_rules": ["RULE_GEOLOCATION_JUMP"],
        "details": {
          "prev_location": "Chennai",
          "current_location": "London",
          "calculated_speed_kmh": 24000.0
        }
      },
      {
        "pattern_name": "DEVICE_SYNDICATE",
        "detected": true,
        "confidence": 0.91,
        "matched_rules": ["RULE_SHARED_DEVICE_MULTI_ACCOUNT"],
        "details": {
          "shared_device_id": "D901",
          "connected_account_count": 5
        }
      },
      {
        "pattern_name": "VELOCITY_BURST",
        "detected": true,
        "confidence": 0.85,
        "matched_rules": ["RULE_RAPID_FIRE_BURST"],
        "details": {
          "transaction_count_window": 8,
          "window_duration_seconds": 45
        }
      }
    ],
    "graph_analysis": {
      "account_id": "C102",
      "is_ring_member": true,
      "ring_id": "RING_402",
      "hub_score": 0.76,
      "graph_paths": [
        {
          "path_id": "PATH_101",
          "nodes": ["C102", "D901", "C904", "B221"],
          "edges": [],
          "path_type": "DEVICE_SYNDICATE",
          "risk_score": 0.88
        }
      ],
      "suspicious_connections": []
    },
    "evidences": [
      {
        "id": "EV_101",
        "type": "IMPOSSIBLE_TRAVEL",
        "description": "Location jump from Chennai to London in 120 seconds.",
        "source": "fraud_rules",
        "timestamp": "2026-10-08T20:40:30Z",
        "related_entity": "185.220.101.4",
        "observed_value": "8000 km in 2 min",
        "severity": "CRITICAL"
      }
    ],
    "counter_evidences": [],
    "similar_cases": [],
    "risk_score": 94.0,
    "ai_explanation": "Critical risk due to IMPOSSIBLE_TRAVEL (Chennai -> London in 2m), DEVICE_SYNDICATE across 5 accounts, and a VELOCITY_BURST spike.",
    "recommended_action": "BLOCK",
    "status": "PENDING_REVIEW"
  }
  ```

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
    "reason": "Confirmed IMPOSSIBLE_TRAVEL and DEVICE_SYNDICATE patterns.",
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
      },
      {
        "scenario_id": "TRAVEL_JUMP_01",
        "name": "Impossible Travel Wave",
        "description": "Simulates rapid cross-country geolocation jumps."
      },
      {
        "scenario_id": "SYNDICATE_BURST_01",
        "name": "Device Syndicate Rapid Fire",
        "description": "Simulates multi-account device sharing and velocity burst."
      }
    ]
  }
  ```

### `POST /attacks/trigger`
* **Purpose**: Launch a synthetic attack scenario into the transaction stream.
* **Request Body**: `{"scenario_id": "SYNDICATE_BURST_01", "rate_per_sec": 10}`
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

### `wss://vigil-cmpd.onrender.com/ws/live`
* **Purpose**: Real-time push feed for live transaction streaming, immediate high-risk alerts, and investigation state updates.
* **Event Types**:
  - `TRANSACTION_SCREENED`: Sent for every processed transaction.
  - `CASE_FLAGGED`: Sent when CatBoost or rules flag high risk.
  - `INVESTIGATION_UPDATE`: Sent when agent completes evidence collection.
