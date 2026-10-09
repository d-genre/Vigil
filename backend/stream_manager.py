import time
import random
import threading
from collections import deque
from datetime import datetime, timezone

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

def _generate_seed_data():
    """Generates 8 initial benign transactions to seed the stream buffer."""
    seed_transactions = []
    base_time = int(time.time()) - 300  # 5 minutes ago
    
    for i in range(8):
        tx_time = datetime.fromtimestamp(base_time + i * 35, tz=timezone.utc).isoformat()
        amount = round(random.uniform(12.50, 145.00), 2)
        user_id = random.choice(BENIGN_USERS)
        merchant = random.choice(MERCHANTS)
        score = round(random.uniform(0.01, 0.12), 3)
        
        tx = {
            "transaction_id": f"TX_BENIGN_{1000 + i}",
            "timestamp": tx_time,
            "user_id": user_id,
            "amount": amount,
            "merchant": merchant,
            "status": "CLEARED",
            "catboost_score": score
        }
        seed_transactions.append(tx)
    return seed_transactions

# Seed buffer upon initialization
with _buffer_lock:
    TRANSACTION_BUFFER.extend(_generate_seed_data())

def tick_benign_transaction():
    """Simulates a new background benign transaction and appends it to the buffer."""
    now_iso = datetime.now(timezone.utc).isoformat()
    amount = round(random.uniform(8.00, 120.00), 2)
    user_id = random.choice(BENIGN_USERS)
    merchant = random.choice(MERCHANTS)
    score = round(random.uniform(0.01, 0.14), 3)
    
    tx = {
        "transaction_id": f"TX_BENIGN_{int(time.time() * 1000) % 100000}",
        "timestamp": now_iso,
        "user_id": user_id,
        "amount": amount,
        "merchant": merchant,
        "status": "CLEARED",
        "catboost_score": score
    }
    
    with _buffer_lock:
        TRANSACTION_BUFFER.appendleft(tx)
    return tx

def inject_simulated_attack():
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
        "amount": 9480.00,
        "merchant": "CryptoExchange_Global_FX",
        "status": "SUSPICIOUS",
        "catboost_score": 0.965
    }
    
    with _buffer_lock:
        TRANSACTION_BUFFER.appendleft(attack_tx)
    return attack_tx

def get_current_stream():
    """Returns a snapshot list of current transactions in the stream buffer."""
    with _buffer_lock:
        return list(TRANSACTION_BUFFER)
