# VIGIL — ARCHITECTURE SPECIFICATION

Vigil is an **Autonomous Fraud Investigation Agent** designed to detect suspicious financial transactions, reconstruct fraud networks, identify complex attack patterns, retrieve similar historical attacks, gather auditable evidence, explain risk transparently, and present actionable recommendations for human decision-making.

---

## 1. System Architecture & Flow

```
                     +----------------------------------------+
                     |   PaySim + Synthetic Attack Generator  |
                     +----------------------------------------+
                                         |
                                         v
                     +----------------------------------------+
                     | Live Transaction Generator / Simulator |
                     +----------------------------------------+
                                         |
                                         v
                     +----------------------------------------+
                     |    Fast ML Screening (CatBoost)       |
                     |     "Is transaction suspicious?"      |
                     +----------------------------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                   [ LOW Risk ]                     [ MEDIUM / HIGH Risk ]
                       |                                   |
                       v                                   v
             +-------------------+             +-----------------------+
             |  AUTO-APPROVE     |             | Investigation Agent   |
             +-------------------+             |      (LangGraph)      |
                                               +-----------------------+
                                                           |
                 +-----------------------------------------+-----------------------------------------+
                 |                         |                       |                                 |
                 v                         v                       v                                 v
    +-------------------------+ +---------------------+ +-----------------------+       +---------------------+
    | Behavioral & Historical | | Fraud Pattern Logic | | NetworkX Fraud Graph  |       | FAISS Vector Memory |
    |      Pattern Check      | |    (7 Patterns)     | | (Ring & Path Analysis)|       |  (Similar Attacks)  |
    +-------------------------+ +---------------------+ +-----------------------+       +---------------------+
                 |                         |                       |                                 |
                 +-------------------------+-----------------------+---------------------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               |    Evidence Engine    |
                                               | (Signals & Counter-Ev)|
                                               +-----------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               | Risk Scoring Engine   |
                                               +-----------------------+
                                               | LLM Explanation Engine|
                                               | (Structured Reasoning)|
                                               +-----------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               |  Recommended Action   |
                                               +-----------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               |     HUMAN REVIEW      |
                                               | [APPROVE/HOLD/ESCALATE|
                                               |      /BLOCK]          |
                                               +-----------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               |  Case Recording & DB  |
                                               +-----------------------+
                                                           |
                                                           v
                                               +-----------------------+
                                               |  Attack Memory &      |
                                               | Evaluation Dashboard  |
                                               +-----------------------+
```

---

## 2. Core Architecture Principles

### 2.1 Fast ML Screening vs. Pattern Detection
* **CatBoost Classifier**: Acts as the rapid, low-latency screening tier. Its sole responsibility is to answer: *"Is this transaction suspicious?"* (returns `fraud_probability` and `risk_level`: LOW, MEDIUM, HIGH).
* **Fraud Pattern & Behavioral Engine**: CatBoost does **NOT** directly classify all seven fraud patterns. Specific pattern identification is handled by rule-based, behavioral, and graph analytics within the investigation agent.

### 2.2 The 7 Finalized Fraud Patterns
Vigil evaluates suspicious cases against exactly seven finalized fraud patterns:
1. **Card Testing**: Rapid sequence of small-value transactions used to validate stolen credit card credentials.
2. **Account Takeover (ATO)**: Sudden changes in device, IP, location, or behavioral metrics followed by high-value transfers.
3. **Mule Account Chain**: Fast multi-hop fund transfers across a chain of accounts designed to obfuscate money flow.
4. **Synthetic Identity Fraud**: Newly created or mismatched identity attributes coupled with abnormal credit usage.
5. **Push Payment Scam**: Authorized push payment deception where victims are manipulated into sending funds to fraudulent accounts.
6. **Beneficiary / Account Takeover**: Modification of account payout/beneficiary details prior to large transfer requests.
7. **Coordinated Fraud Ring**: Graph-detected networks sharing device IDs, IP addresses, phone numbers, or mule nodes across multiple accounts.

### 2.3 Agentic Orchestration with LangGraph
When CatBoost flags a transaction as `MEDIUM` or `HIGH` risk:
- **LangGraph** orchestrates the multi-step investigation pipeline statefully.
- State steps include: history lookup -> behavioral analysis -> pattern detection -> graph analysis -> vector memory search -> evidence synthesis -> LLM reasoning.

### 2.4 Graph Analytics with NetworkX
- **NetworkX** maintains an in-memory graph of accounts, devices, IPs, merchants, and transactions.
- Detects cycles, hub nodes, shared identifiers, and suspicious multi-hop paths.

### 2.5 Vector Memory with FAISS & Embeddings
- Historical fraud cases and attack signatures are stored in a **FAISS** vector database using **Sentence-Transformers** embeddings.
- Enables semantic retrieval of similar past attack topologies and strategies to enrich current case context.

### 2.6 Grounded LLM Reasoning & Evidence Engine
- The **Evidence Engine** aggregates structured signals (positive risk indicators) and counter-evidence ("why NOT to block").
- The **LLM** receives *only* structured evidence JSON and produces human-readable explanations and action recommendations.
- **Rule**: The LLM is strictly prohibited from inventing or hallucinating evidence.

### 2.7 Human-in-the-Loop Governance
- Vigil does not execute irreversible blocks autonomously without oversight.
- Final decisions (`APPROVE`, `HOLD`, `ESCALATE`, `BLOCK`) are made or confirmed by human fraud analysts through the frontend dashboard.
