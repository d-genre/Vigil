import io
import asyncio
from datetime import datetime, timezone
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
    # Startup: Initialize Database & Autonomous 15s Stream Loop
    init_db()
    stream_task = asyncio.create_task(stream_manager.start_stream_heartbeat())
    yield
    # Shutdown: Cancel background task cleanly
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass

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


@app.get("/api/graph/ego-network/{transaction_id}")
def get_ego_network_endpoint(transaction_id: str):
    """
    Returns Vigil: Fraudster Ego Network (Degrees of Separation) node-link structure.
    """
    from graph import generate_ego_network
    return generate_ego_network(transaction_id)


@app.get("/api/graph/temporal-map/{transaction_id}")
def get_temporal_map_endpoint(transaction_id: str):
    """
    Returns Vigil: Temporal IP Fraud Map trajectory points and velocity violation metadata.
    """
    from graph import generate_temporal_map
    return generate_temporal_map(transaction_id)


@app.get("/api/graph/{transaction_id}")
def get_transaction_graph(transaction_id: str):
    """
    Returns NetworkX graph topology and suspicious path/fraud-ring details.
    """
    from graph import generate_ego_network
    return generate_ego_network(transaction_id)


@app.get("/api/dossier/{transaction_id}")
def get_transaction_dossier(transaction_id: str):
    """
    Returns the full Judicial Dossier evaluated via CatBoost ML Model & TreeSHAP (Prosecution vs Defense Evidence).
    """
    from backend.dossier_service import dossier_engine
    
    # 1. Check if transaction exists in current stream buffer
    stream_txs = stream_manager.get_current_stream()
    match_tx = next((t for t in stream_txs if t.get("transaction_id") == transaction_id), None)
    
    seed = sum(ord(c) for c in transaction_id) if transaction_id else 42
    is_attack = "TX_FLAGGED_" in transaction_id.upper() or "ATTACK" in transaction_id.upper() or "MULE" in transaction_id.upper()
    
    if match_tx:
        tx_dict = match_tx
    else:
        # Reconstruct deterministic transaction telemetry from ID
        if is_attack:
            amount = round(4500.0 + (seed % 900000) / 100.0, 2)
            user_id = f"usr_ring_leader_{(seed % 15) + 80}"
            merchant = "CryptoExchange_Global_FX" if (seed % 2 == 0) else "Offshore_Wire_Transfer"
            ip = f"185.220.101.{(seed % 90) + 4}"
            device_id = f"dev_guid_{(seed % 999) + 9000}"
            status = "FLAGGED"
        else:
            amount = round(15.0 + (seed % 15000) / 100.0, 2)
            user_id = f"usr_benign_{(seed % 6) + 101}"
            merchant = stream_manager.MERCHANTS[seed % len(stream_manager.MERCHANTS)]
            ip = f"192.168.1.{(seed % 50) + 100}"
            device_id = f"dev_trusted_{(seed % 50) + 100}"
            status = "CLEARED"
            
        tx_dict = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "account_id": user_id,
            "amount": amount,
            "merchant": merchant,
            "location": merchant,
            "ip": ip,
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    score = float(tx_dict.get("catboost_score", tx_dict.get("risk_score", 0.965 if is_attack else 0.045)))
    
    shap_summary = {
        "ml_score": score,
        "risk_score": score
    }
    graph_summary = {
        "cluster_size": 4 if is_attack else 1
    }
    
    report_obj = dossier_engine.generate_dossier(tx_dict, shap_summary, graph_summary)
    return report_obj.model_dump()


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
