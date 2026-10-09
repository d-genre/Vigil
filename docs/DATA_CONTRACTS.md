# VIGIL — SHARED DATA CONTRACTS BY TEAM ROLE

This document defines the standardized data contracts shared across all four team roles (`ml`, `fraud/graph`, `frontend`, `backend`). These contracts serve as the single source of truth for inter-module communication.

---

## 1. Member 1 — ML Engineer Data Contracts (`ml/`)

### 1.1 Incoming Transaction Screening Input
Target transaction object consumed by `predict()` interface.

```json
{
  "transaction_id": "TX8421",
  "account_id": "C102",
  "amount": 28900.0,
  "currency": "USD",
  "device_id": "D901",
  "ip": "10.20.4.5",
  "beneficiary_id": "B221",
  "timestamp": "2026-10-08T20:40:00Z",
  "location": "Chennai",
  "transaction_type": "TRANSFER"
}
```

### 1.2 CatBoost ML Prediction Output Contract (`MLPrediction`)
Returned by `predict()` screening method:

```json
{
  "transaction_id": "TX8421",
  "fraud_probability": 0.91,
  "risk_level": "HIGH",
  "model_version": "catboost_v1.0"
}
```

* **`fraud_probability`**: `float` between `0.0` and `1.0`.
* **`risk_level`**: Enum string (`"LOW"`, `"MEDIUM"`, `"HIGH"`).

---

## 2. Member 2 — Fraud & Graph Data Contracts (`fraud/`, `graph/`)

### 2.1 Fraud Pattern Result Contract (`FraudPatternResult`)
Returned by individual pattern detectors evaluating against registered fraud patterns:

```json
{
  "pattern_name": "Account Takeover (ATO)",
  "detected": true,
  "confidence": 0.88,
  "matched_rules": [
    "NEW_DEVICE_AND_IP",
    "HIGH_AMOUNT_ABOVE_HISTORICAL_AVG"
  ],
  "details": {
    "device_switch": "D101 -> D901",
    "historical_avg_amount": 1200.0,
    "current_amount": 28900.0
  }
}
```

* **Registered Fraud Pattern Enums (`FraudPatternType`)**:
  1. `"CARD_TESTING"` (or `"Card Testing"`)
  2. `"ACCOUNT_TAKEOVER"` (or `"Account Takeover (ATO)"`)
  3. `"MULE_CHAIN"` (or `"Mule Account Chain"`)
  4. `"SYNTHETIC_IDENTITY"` (or `"Synthetic Identity Fraud"`)
  5. `"PUSH_PAYMENT_SCAM"` (or `"Push Payment Scam"`)
  6. `"BENEFICIARY_ATO"` (or `"Beneficiary / Account Takeover"`)
  7. `"COORDINATED_FRAUD_RING"` (or `"Coordinated Fraud Ring"`)
  8. **`"IMPOSSIBLE_TRAVEL"`**: Rapid geolocation/IP change in physically impossible timeframe.
  9. **`"DEVICE_SYNDICATE"`**: Interconnected group of accounts operating through a single/shared device with identical behavioral signatures.
  10. **`"VELOCITY_BURST"`**: Spike in transaction frequency or rapid-fire actions within a short time window.

---

### 2.2 New Fraud Pattern Details & Contracts

#### A. `IMPOSSIBLE_TRAVEL`
* **Definition**: Rapid change of IP addresses or geolocations across sequential transactions within physically impossible travel timeframes.
* **Triggering Indicators**: Speed between consecutive events > 800 km/h or < 30 minutes between distinct cities/countries.
* **Expected `details` Structure**:
  ```json
  {
    "prev_location": "Chennai",
    "current_location": "London",
    "time_delta_seconds": 120,
    "calculated_speed_kmh": 24000.0,
    "prev_ip": "10.20.4.5",
    "current_ip": "185.220.101.4",
    "distance_km": 8000.0
  }
  ```

#### B. `DEVICE_SYNDICATE`
* **Definition**: Group of user accounts interconnected through a single or shared device fingerprint exhibiting synchronized or identical behavior patterns.
* **Triggering Indicators**: Device ID linked to $\ge 3$ distinct customer accounts within 24 hours performing similar transfer patterns.
* **Expected `details` Structure**:
  ```json
  {
    "shared_device_id": "D901",
    "connected_account_count": 5,
    "account_ids": ["C102", "C105", "C109", "C220", "C312"],
    "syndicate_cluster_id": "SYN_901",
    "behavior_similarity_score": 0.92,
    "shared_ip_addresses": ["10.20.4.5", "10.20.4.6"]
  }
  ```

#### C. `VELOCITY_BURST`
* **Definition**: Sudden spike in transaction frequency or rapid-fire payment attempts (e.g., rapid micro-transactions or successive automated attempts).
* **Triggering Indicators**: Transaction count > 5 within a 60-second sliding window or velocity Z-score > 3.5 over account baseline.
* **Expected `details` Structure**:
  ```json
  {
    "transaction_count_window": 8,
    "window_duration_seconds": 45,
    "average_time_between_tx_sec": 5.6,
    "total_burst_amount": 3400.0,
    "velocity_z_score": 4.2
  }
  ```

---

### 2.3 Network Graph Analysis Contract (`GraphAnalysisResult`)
Returned by NetworkX engine after topology and hub analysis:

```json
{
  "account_id": "C102",
  "is_ring_member": true,
  "ring_id": "RING_402",
  "hub_score": 0.76,
  "graph_paths": [
    {
      "path_id": "PATH_101",
      "nodes": ["C102", "D901", "C904", "B221"],
      "edges": [
        {"source": "C102", "target": "D901", "type": "USED_DEVICE"},
        {"source": "C904", "target": "D901", "type": "USED_DEVICE"},
        {"source": "C904", "target": "B221", "type": "TRANSFERRED_TO"}
      ],
      "path_type": "DEVICE_SYNDICATE",
      "risk_score": 0.85
    }
  ],
  "suspicious_connections": [
    {
      "entity_type": "device",
      "entity_id": "D901",
      "shared_account_count": 5
    }
  ]
}
```

---

## 3. Member 3 — Frontend Data Contracts (`frontend/`)

### 3.1 Live Feed & Risk Queue View Contract
Structure received by React dashboard via REST and WebSocket `/ws/live`:

```json
{
  "case_id": "CASE_8421",
  "transaction_id": "TX8421",
  "account_id": "C102",
  "amount": 28900.0,
  "currency": "USD",
  "risk_score": 89.5,
  "risk_level": "HIGH",
  "status": "PENDING_REVIEW",
  "created_at": "2026-10-08T20:41:00Z"
}
```

### 3.2 Human Decision Payload (`HumanDecisionRequest`)
Submitted by analyst from Frontend:

```json
{
  "action": "BLOCK",
  "reason": "Confirmed DEVICE_SYNDICATE and IMPOSSIBLE_TRAVEL patterns.",
  "analyst_id": "ANALYST_42"
}
```

---

## 4. Member 4 — Backend & Integration Data Contracts (`backend/`)

### 4.1 Positive Evidence Item Contract (`EvidenceItem`)
```json
{
  "id": "EV_101",
  "type": "IMPOSSIBLE_TRAVEL",
  "description": "Location jump from Chennai to London in 120 seconds (24,000 km/h).",
  "source": "fraud_rules",
  "timestamp": "2026-10-08T20:40:30Z",
  "related_entity": "185.220.101.4",
  "observed_value": "8000 km in 2 min",
  "severity": "CRITICAL"
}
```

### 4.2 Counter-Evidence Item Contract (`CounterEvidenceItem`)
```json
{
  "id": "CEV_201",
  "type": "KYC_VERIFIED",
  "description": "Account C102 completed biometric verification 2 days ago.",
  "source": "customer_database",
  "timestamp": "2026-10-06T10:00:00Z",
  "related_entity": "C102",
  "observed_value": "Level 3 KYC",
  "relevance_score": 0.4
}
```

### 4.3 Vector Memory Match Contract (`SimilarAttackResult`)
```json
{
  "attack_id": "ATTACK_2025_089",
  "similarity_score": 0.94,
  "pattern_type": "DEVICE_SYNDICATE",
  "historical_outcome": "CONFIRMED_FRAUD",
  "key_features": ["shared_device_id", "rapid_multi_account_access"]
}
```

### 4.4 Full Investigation Case Contract (`InvestigationCase`)
Master container managed across LangGraph state steps:

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
      "matched_rules": ["RULE_GEOLOCATION_JUMP_IMPOSSIBLE_SPEED"],
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
    }
  ],
  "graph_analysis": {
    "account_id": "C102",
    "is_ring_member": true,
    "ring_id": "RING_402",
    "hub_score": 0.76,
    "graph_paths": [],
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
  "counter_evidences": [
    {
      "id": "CEV_201",
      "type": "KYC_VERIFIED",
      "description": "Account C102 completed biometric verification 2 days ago.",
      "source": "customer_database",
      "timestamp": "2026-10-06T10:00:00Z",
      "related_entity": "C102",
      "observed_value": "Level 3 KYC",
      "relevance_score": 0.4
    }
  ],
  "similar_cases": [
    {
      "attack_id": "ATTACK_2025_089",
      "similarity_score": 0.94,
      "pattern_type": "DEVICE_SYNDICATE",
      "historical_outcome": "CONFIRMED_FRAUD",
      "key_features": ["shared_device_id"]
    }
  ],
  "risk_score": 92.5,
  "ai_explanation": "Critical risk due to IMPOSSIBLE_TRAVEL (Chennai -> London in 2m) combined with a DEVICE_SYNDICATE cluster across 5 accounts.",
  "recommended_action": "BLOCK",
  "status": "PENDING_REVIEW"
}
```
