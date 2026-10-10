import io
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from schemas.transaction import Transaction
from backend.database import init_db, get_db
from backend.ml_service import screening_service
from backend.websocket import manager
from backend import stream_manager
from backend.pdf_exporter import render_dossier_pdf

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    yield

app = FastAPI(
    title="Vigil API",
    description="Autonomous Fraud Investigation Command Center API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint welcoming users and pointing to API documentation."""
    return {
        "message": "Welcome to Vigil Fraud Investigation Command Center API",
        "docs_url": "http://localhost:8000/docs",
        "health_check": "http://localhost:8000/health",
        "active_endpoints": [
            "/api/transactions/stream",
            "/api/transactions/simulate-attack",
            "/api/graph/{transaction_id}",
            "/api/dossier/{transaction_id}",
            "/api/dossier/{transaction_id}/pdf"
        ]
    }


@app.get("/health")
def health_check():
    """System health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "subsystems": {
            "ml_screening": "ready" if screening_service else "not_initialized",
            "database": "connected",
            "stream_manager": "active"
        }
    }


# ==========================================
# PHASE 1 & 2: STREAM & COMMAND CENTER ENDPOINTS
# ==========================================

@app.get("/api/transactions/stream")
def get_transaction_stream(tick: Optional[bool] = Query(False, description="Set true to simulate a background benign transaction tick")):
    """
    Returns the real-time buffer of transactions.
    Optionally ticks a new benign transaction before returning.
    """
    if tick:
        stream_manager.tick_benign_transaction()
    transactions = stream_manager.get_current_stream()
    return {
        "total": len(transactions),
        "transactions": transactions
    }


@app.post("/api/transactions/simulate-attack", status_code=status.HTTP_201_CREATED)
def simulate_attack():
    """
    Injects a high-risk suspicious attack transaction into the live stream buffer.
    """
    attack_tx = stream_manager.inject_simulated_attack()
    return {
        "status": "ATTACK_INJECTED",
        "transaction": attack_tx
    }


@app.get("/api/graph/{transaction_id}")
def get_transaction_graph(transaction_id: str):
    """
    Returns NetworkX graph topology and suspicious path/fraud-ring details.
    """
    is_attack = "TX_FLAGGED_" in transaction_id
    
    if is_attack:
        return {
            "transaction_id": transaction_id,
            "fraud_pattern": "MULTI_ACCOUNT_SMURFING_RING",
            "topology_stats": {
                "total_nodes": 6,
                "total_edges": 7,
                "density": 0.467,
                "suspicious_subgraph_nodes": 5
            },
            "nodes": [
                {"id": transaction_id, "label": "Flagged Transaction", "type": "TRANSACTION", "risk_score": 0.965},
                {"id": "usr_ring_leader_88", "label": "Origin User (usr_ring_leader_88)", "type": "USER_ACCOUNT", "risk_score": 0.920},
                {"id": "ip_185_220_101_4", "label": "Tor Exit Node (185.220.101.4)", "type": "IP_ADDRESS", "risk_score": 0.990},
                {"id": "mule_acc_401", "label": "Mule Account A (mule_acc_401)", "type": "MULE_ACCOUNT", "risk_score": 0.880},
                {"id": "mule_acc_402", "label": "Mule Account B (mule_acc_402)", "type": "MULE_ACCOUNT", "risk_score": 0.895},
                {"id": "dev_guid_9921", "label": "Banned Hardware GUID", "type": "DEVICE", "risk_score": 0.950}
            ],
            "edges": [
                {"source": "usr_ring_leader_88", "target": transaction_id, "relation": "INITIATED"},
                {"source": transaction_id, "target": "ip_185_220_101_4", "relation": "ORIGINATED_FROM"},
                {"source": transaction_id, "target": "mule_acc_401", "relation": "SPLIT_TRANSFER"},
                {"source": transaction_id, "target": "mule_acc_402", "relation": "SPLIT_TRANSFER"},
                {"source": "usr_ring_leader_88", "target": "dev_guid_9921", "relation": "USED_DEVICE"},
                {"source": "mule_acc_401", "target": "dev_guid_9921", "relation": "SHARED_DEVICE"},
                {"source": "mule_acc_402", "target": "ip_185_220_101_4", "relation": "SHARED_IP"}
            ]
        }
    else:
        return {
            "transaction_id": transaction_id,
            "fraud_pattern": "NORMAL_RETAIL_PURCHASE",
            "topology_stats": {
                "total_nodes": 3,
                "total_edges": 2,
                "density": 0.050,
                "suspicious_subgraph_nodes": 0
            },
            "nodes": [
                {"id": transaction_id, "label": "Retail Purchase", "type": "TRANSACTION", "risk_score": 0.045},
                {"id": "usr_benign_101", "label": "Verified Customer", "type": "USER_ACCOUNT", "risk_score": 0.020},
                {"id": "merch_starbucks", "label": "Starbucks Coffee", "type": "MERCHANT", "risk_score": 0.010}
            ],
            "edges": [
                {"source": "usr_benign_101", "target": transaction_id, "relation": "PURCHASED"},
                {"source": transaction_id, "target": "merch_starbucks", "relation": "PAID_TO"}
            ]
        }


@app.get("/api/dossier/{transaction_id}")
def get_transaction_dossier(transaction_id: str):
    """
    Returns the full Judicial Dossier (Prosecution Evidence vs Defense Counter-Evidence & SHAP Explainability).
    """
    is_attack = "TX_FLAGGED_" in transaction_id
    
    if is_attack:
        return {
            "transaction_id": transaction_id,
            "risk_score": 0.965,
            "verdict": "REJECT_AND_FREEZE",
            "classification": "ORGANIZED_SMURFING_ATTACK",
            "executive_summary": "High-confidence smurfing ring attack detected. Transaction velocity exceeds 500% of historical baseline with high-risk IP mismatch across multiple linked mule accounts.",
            "prosecution_evidence": [
                {
                    "title": "Geo-Velocity Anomaly",
                    "description": "Transaction initiated from IP 185.220.101.4 (Tor Exit Node) 12 minutes after authenticating from Tokyo.",
                    "impact": 0.42
                },
                {
                    "title": "Rapid Smurfing Fan-Out",
                    "description": "Funds fragmented across 3 recipient accounts created within the last 24 hours.",
                    "impact": 0.38
                },
                {
                    "title": "Banned Device Fingerprint",
                    "description": "Hardware GUID shared with 4 previously blacklisted fraud accounts.",
                    "impact": 0.16
                }
            ],
            "defense_evidence": [
                {
                    "title": "2FA Step-up Authenticated",
                    "description": "SMS OTP challenge passed successfully (High probability of SIM swap or SS7 exploit)."
                }
            ],
            "explainability_drivers": [
                {"feature": "ip_risk_score", "value": "0.98", "shap_value": 0.412},
                {"feature": "velocity_1h", "value": "14 txns", "shap_value": 0.325},
                {"feature": "amount_vs_avg", "value": "18.4x", "shap_value": 0.228}
            ]
        }
    else:
        return {
            "transaction_id": transaction_id,
            "risk_score": 0.045,
            "verdict": "APPROVE",
            "classification": "BENIGN_RETAIL_TRANSACTION",
            "executive_summary": "Standard transaction matching user historical purchasing patterns and trusted device context.",
            "prosecution_evidence": [],
            "defense_evidence": [
                {
                    "title": "Trusted Device History",
                    "description": "Hardware GUID has 120+ consecutive clean historic sessions."
                },
                {
                    "title": "Habitual Merchant Affinity",
                    "description": "User has executed 14 recurring transactions at this merchant over the past 90 days."
                }
            ],
            "explainability_drivers": [
                {"feature": "device_trust_score", "value": "0.99", "shap_value": -0.310},
                {"feature": "merchant_affinity", "value": "HIGH", "shap_value": -0.245}
            ]
        }


@app.get("/api/dossier/{transaction_id}/pdf")
def export_dossier_pdf(transaction_id: str):
    """
    Compiles the Judicial Dossier into a downloadable PDF binary stream.
    """
    dossier_data = get_transaction_dossier(transaction_id)
    pdf_buffer = render_dossier_pdf(dossier_data)
    
    headers = {
        "Content-Disposition": f"attachment; filename=dossier_{transaction_id}.pdf"
    }
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)


# ==========================================
# WEBSOCKET & LEGACY DB ENDPOINTS
# ==========================================

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/transactions", status_code=status.HTTP_201_CREATED)
async def process_transaction(tx: Transaction):
    """Ingests a new transaction, scores it, saves it to DB, and broadcasts via WS."""
    tx_dict = tx.model_dump()
    try:
        raw_score, raw_level = screening_service.screen(tx_dict)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal ML screening failure"
        )
        
    try:
        risk_score = max(0.0, min(1.0, float(raw_score)))
        if raw_level not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise ValueError(f"Invalid risk_level '{raw_level}' returned by ML service")
        risk_level = raw_level
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid ML inference values: {str(e)}"
        )

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO transactions (
                transaction_id, account_id, amount, currency, device_id, 
                ip, beneficiary_id, timestamp, location, transaction_type, 
                risk_score, risk_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx.transaction_id, tx.account_id, tx.amount, tx.currency, tx.device_id,
            tx.ip, tx.beneficiary_id, tx.timestamp, tx.location, tx.transaction_type,
            risk_score, risk_level
        ))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Database persistence error"
        )
    finally:
        conn.close()

    broadcast_data = {
        "event_type": "TRANSACTION_SCREENED",
        "data": {
            "transaction_id": tx.transaction_id,
            "account_id": tx.account_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "timestamp": tx.timestamp
        }
    }
    import asyncio
    asyncio.create_task(manager.broadcast(broadcast_data))
    
    requires_investigation = risk_level in ["MEDIUM", "HIGH", "CRITICAL"]
    return {
        "transaction_id": tx.transaction_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "requires_investigation": requires_investigation,
        "action_taken": "INVESTIGATION_TRIGGERED" if requires_investigation else "APPROVED"
    }


@app.get("/transactions")
def get_transactions(limit: int = Query(50, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """Retrieve recent transactions from DB."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    
    return {
        "total": len(rows),
        "transactions": [dict(row) for row in rows]
    }
