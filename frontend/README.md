# FRAUD_RING RADAR — FRONTEND APPLICATION ARCHITECTURE

> **VIGIL-Aligned React + TypeScript UI Dashboard Workspace Structure**

This directory defines the 7-dashboard UI architecture for the investigator workspace:

1. **Fraud Ring Investigation**: Cytoscape.js network visualizer & ring topology inspector.
2. **Case Management**: Risk queue (`PENDING_REVIEW`, `RESOLVED`) & analyst decision modal (`APPROVE`, `HOLD`, `ESCALATE`, `BLOCK`).
3. **Screening & API Operations**: Real-time transaction submission & CatBoost screening latency monitor.
4. **Security & Platform Administration**: Role-based access control, audit logs, and API health status.
5. **VIGIL Investigator Workspace**: Full investigation state viewer, structured evidence/counter-evidence feed, and LLM explanation panel.
6. **Real-Time Monitoring**: Live WebSocket (`/ws/live`) transaction streaming ticker and instant alert toasts.
7. **Historical Case Intelligence**: Vector similarity memory (FAISS) search & historical attack topology browser.
