import time
import random
import threading
import asyncio
import logging
from collections import deque
from datetime import datetime, timezone

logger = logging.getLogger("vigil.backend.stream_manager")

# Thread-safe buffer for streaming transactions
_buffer_lock = threading.Lock()
TRANSACTION_BUFFER = deque(maxlen=30)

MERCHANTS = [
    "Amazon.com", "Starbucks Coffee", "Uber Rides", "Target Superstore",
    "Walmart Online", "Apple Store", "Netflix Subscription", "Steam Games",
    "Delta Air Lines", "Chevron Gas Station"
]

BENIGN_USERS = [
    "usr_benign_101", "usr_benign_102", "usr_benign_103",
    "usr_benign_104", "usr_benign_105", "usr_benign_106"
]

def _screen_tx(tx_dict: dict):
    """Utility to score transaction via ScreeningService."""
    try:
        from backend.ml_service import screening_service
        score, level = screening_service.screen(tx_dict)
        return score, level
    except Exception as e:
        logger.warning(f"Failed to score stream transaction: {e}")
        amount = float(tx_dict.get("amount", 0.0))
        is_attack = "FLAGGED" in tx_dict.get("transaction_id", "")
        if is_attack or amount > 5000:
            return 0.945, "CRITICAL"
        return 0.042, "LOW"

def _generate_seed_data():
    """Generates 8 initial benign transactions to seed the stream buffer."""
    seed_transactions = []
    base_time = int(time.time()) - 300  # 5 minutes ago
    
    for i in range(8):
        tx_time = datetime.fromtimestamp(base_time + i * 35, tz=timezone.utc).isoformat()
        amount = round(random.uniform(12.50, 145.00), 2)
        user_id = random.choice(BENIGN_USERS)
        merchant = random.choice(MERCHANTS)
        user_idx = int(user_id.split("_")[-1]) if "_" in user_id else 101
        
        tx = {
            "transaction_id": f"TX_BENIGN_{1000 + i}",
            "timestamp": tx_time,
            "user_id": user_id,
            "account_id": user_id,
            "amount": amount,
            "merchant": merchant,
            "location": merchant,
            "status": "CLEARED",
            "ip": f"192.168.1.{user_idx}",
            "device_id": f"dev_trusted_{user_idx}",
            "currency": "USD"
        }
        score, level = _screen_tx(tx)
        tx["catboost_score"] = score
        tx["risk_score"] = score
        tx["risk_level"] = level
        seed_transactions.append(tx)
    return seed_transactions

# Seed buffer upon initialization
with _buffer_lock:
    TRANSACTION_BUFFER.extend(_generate_seed_data())

def generate_simulated_tick(force_benign: bool = False) -> dict:
    """
    Autonomous simulation tick.
    Generates a realistic transaction (~90% benign, ~10% flagged attack),
    scores it using CatBoost ML screening, appends to buffer, and logs stdout.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    timestamp_ms = int(time.time() * 1000) % 100000
    is_attack = False if force_benign else (random.random() < 0.10)
    
    if is_attack:
        user_id = random.choice(["usr_ring_leader_88", "usr_mule_transfer_44", "usr_compromised_77"])
        amount = round(random.uniform(2500.00, 14500.00), 2)
        merchant = random.choice(["CryptoExchange_Global_FX", "Offshore_Wire_Transfer", "LuxGifts_Direct"])
        ip = random.choice(["185.220.101.4", "194.26.29.112", "185.220.102.8"])
        device_id = random.choice(["dev_guid_9921", "dev_emulator_55", "dev_rooted_88"])
        tx_id = f"TX_FLAGGED_{timestamp_ms}"
    else:
        user_id = random.choice(BENIGN_USERS)
        amount = round(random.uniform(8.00, 185.00), 2)
        merchant = random.choice(MERCHANTS)
        user_idx = int(user_id.split("_")[-1]) if "_" in user_id else 101
        ip = f"192.168.1.{user_idx}"
        device_id = f"dev_trusted_{user_idx}"
        tx_id = f"TX_BENIGN_{timestamp_ms}"

    tx = {
        "transaction_id": tx_id,
        "timestamp": now_iso,
        "user_id": user_id,
        "account_id": user_id,
        "amount": amount,
        "merchant": merchant,
        "location": merchant,
        "ip": ip,
        "device_id": device_id,
        "currency": "USD"
    }

    score, level = _screen_tx(tx)
    status_str = "FLAGGED" if (is_attack or score >= 0.70) else "CLEARED"
    tx["catboost_score"] = score
    tx["risk_score"] = score
    tx["risk_level"] = level
    tx["status"] = status_str

    with _buffer_lock:
        TRANSACTION_BUFFER.appendleft(tx)

    # Required log format: [STREAM ENGINE] Ingested TX_{id} | Amount: ${amount} | Score: {score} | Status: {status}
    print(f"[STREAM ENGINE] Ingested {tx_id} | Amount: ${amount:.2f} | Score: {score:.3f} | Status: {status_str}", flush=True)
    return tx

def tick_benign_transaction() -> dict:
    """Forces generation of a benign transaction tick for manual triggers."""
    return generate_simulated_tick(force_benign=True)

def inject_simulated_attack() -> dict:
    """
    Injects a high-risk attack transaction into the buffer for pitch demos.
    Prefixes ID with TX_FLAGGED_ so downstream API routes recognize it as suspicious.
    """
    timestamp_ms = int(time.time() * 1000)
    tx_id = f"TX_FLAGGED_{timestamp_ms}"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    attack_tx = {
        "transaction_id": tx_id,
        "timestamp": now_iso,
        "user_id": "usr_ring_leader_88",
        "account_id": "usr_ring_leader_88",
        "amount": 9480.00,
        "merchant": "CryptoExchange_Global_FX",
        "location": "CryptoExchange_Global_FX",
        "ip": "185.220.101.4",
        "device_id": "dev_guid_9921",
        "currency": "USD"
    }
    
    score, level = _screen_tx(attack_tx)
    status_str = "FLAGGED"
    attack_tx["catboost_score"] = score if score >= 0.70 else 0.965
    attack_tx["risk_score"] = attack_tx["catboost_score"]
    attack_tx["risk_level"] = "CRITICAL"
    attack_tx["status"] = status_str
    
    with _buffer_lock:
        TRANSACTION_BUFFER.appendleft(attack_tx)
        
    print(f"[STREAM ENGINE] Ingested {tx_id} | Amount: ${attack_tx['amount']:.2f} | Score: {attack_tx['catboost_score']:.3f} | Status: {status_str}", flush=True)
    return attack_tx

def get_current_stream():
    """Returns a snapshot list of current transactions in the stream buffer."""
    with _buffer_lock:
        return list(TRANSACTION_BUFFER)

async def start_stream_heartbeat():
    """
    Asynchronous background worker running a 15-second simulation tick loop.
    Starts automatically when FastAPI server boots up.
    """
    print("[STREAM ENGINE] Autonomous 15s Heartbeat Loop Started.", flush=True)
    try:
        while True:
            await asyncio.sleep(15)
            generate_simulated_tick()
    except asyncio.CancelledError:
        print("[STREAM ENGINE] Autonomous 15s Heartbeat Loop Stopped.", flush=True)

