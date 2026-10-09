from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from schemas.transaction import Transaction
from backend.database import init_db, get_db
from backend.ml_service import screening_service
from backend.websocket import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    yield

app = FastAPI(
    title="Vigil API",
    description="Autonomous Fraud Investigation Agent Backend",
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
            "database": "connected"
        }
    }


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
    """
    Ingests a new transaction, scores it, saves it to DB, and broadcasts via WS.
    """
    tx_dict = tx.model_dump()
    
    # 1. Screen the transaction safely
    try:
        raw_score, raw_level = screening_service.screen(tx_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal ML screening failure"
        )
        
    # Enforce clamping and valid enum levels at the API boundary
    try:
        risk_score = max(0.0, min(1.0, float(raw_score)))
        if raw_level not in ["LOW", "MEDIUM", "HIGH"]:
            raise ValueError(f"Invalid risk_level '{raw_level}' returned by ML service")
        risk_level = raw_level
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid ML inference values: {str(e)}"
        )

    # 2. Persist to SQLite
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
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Database persistence error"
        )
    finally:
        conn.close()

    # 3. Broadcast to frontend
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
    # Ensure event loop scheduling doesn't block response
    import asyncio
    asyncio.create_task(manager.broadcast(broadcast_data))
    
    # 4. Return summary
    requires_investigation = risk_level in ["MEDIUM", "HIGH"]
    return {
        "transaction_id": tx.transaction_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "requires_investigation": requires_investigation,
        "action_taken": "INVESTIGATION_TRIGGERED" if requires_investigation else "APPROVED"
    }


@app.get("/transactions")
def get_transactions(limit: int = Query(50, ge=1, le=1000), offset: int = Query(0, ge=0)):
    """Retrieve recent transactions."""
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
