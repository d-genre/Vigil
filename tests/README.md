# VIGIL — TEST SUITE DOCUMENTATION

This directory contains test suites for Vigil components.

---

## Intended Test Structure

During implementation phases (Phases 1-4), tests will be organized as follows:

```
tests/
├── unit/
│   ├── test_ml.py             <- ML feature engineering & CatBoost screening tests
│   ├── test_fraud_rules.py    <- 7 Fraud pattern detector unit tests
│   ├── test_graph.py          <- NetworkX ring & path calculation tests
│   └── test_schemas.py        <- Pydantic contract validation tests
├── integration/
│   ├── test_api.py            <- FastAPI REST endpoint & WebSocket integration tests
│   └── test_evidence.py       <- Evidence Engine & FAISS retriever integration tests
└── e2e/
    └── test_pipeline.py       <- Full end-to-end transaction screening -> LangGraph investigation pipeline tests
```

---

## Running Tests

Execute tests using `pytest`:

```bash
pytest tests/
```
