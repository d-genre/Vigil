"""
VIGIL Transaction Lookup Module (graph/lookup.py)
Fetches exact transaction details from active stream buffer, SQLite database, or deterministic mapping.
"""

import sqlite3
import os
import hashlib
from typing import Dict, Any, Optional, List
from backend import stream_manager

DB_PATH = os.environ.get("DB_PATH", "vigil.db")

def get_transaction_details(transaction_id: str) -> Dict[str, Any]:
    """
    Looks up the exact transaction being investigated across VIGIL data sources:
    1. Active stream buffer (stream_manager)
    2. SQLite database (vigil.db)
    3. Deterministic fallback based on transaction_id hash
    """
    tx_id_str = str(transaction_id).strip()
    
    # 1. Check in-memory stream buffer
    stream_txs = stream_manager.get_current_stream()
    for tx in stream_txs:
        if str(tx.get("transaction_id")).strip() == tx_id_str:
            user_id = str(tx.get("user_id", "usr_unknown"))
            user_idx = int(user_id.split("_")[-1]) if "_" in user_id and user_id.split("_")[-1].isdigit() else 101
            return {
                "transaction_id": tx_id_str,
                "user_id": user_id,
                "account_id": user_id,
                "amount": float(tx.get("amount", 100.0)),
                "currency": str(tx.get("currency", "USD")),
                "merchant": str(tx.get("merchant", "Online Merchant")),
                "ip": str(tx.get("ip", f"192.168.1.{user_idx}")),
                "device_id": str(tx.get("device_id", f"dev_trusted_{user_idx}")),
                "beneficiary_id": str(tx.get("beneficiary_id", f"mule_acc_{user_idx + 300}")),
                "timestamp": str(tx.get("timestamp", "2026-10-10T07:00:00Z")),
                "status": str(tx.get("status", "CLEARED")),
                "score": float(tx.get("catboost_score", tx.get("risk_score", 0.05))),
                "is_attack": "TX_FLAGGED_" in tx_id_str.upper() or str(tx.get("status")).upper() == "SUSPICIOUS" or float(tx.get("catboost_score", 0)) >= 0.70,
                "source": "stream_manager"
            }
            
    # 2. Check SQLite database if initialized
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id_str,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                r_dict = dict(row)
                score = float(r_dict.get("risk_score", 0.05))
                is_attack = "TX_FLAGGED_" in tx_id_str.upper() or r_dict.get("risk_level") in ["HIGH", "CRITICAL"] or score >= 0.70
                return {
                    "transaction_id": tx_id_str,
                    "user_id": str(r_dict.get("account_id", "usr_db_user")),
                    "account_id": str(r_dict.get("account_id", "usr_db_user")),
                    "amount": float(r_dict.get("amount", 100.0)),
                    "currency": str(r_dict.get("currency", "USD")),
                    "merchant": str(r_dict.get("merchant", r_dict.get("location", "Retail Merchant"))),
                    "ip": str(r_dict.get("ip", "192.168.1.100")),
                    "device_id": str(r_dict.get("device_id", "dev_db_100")),
                    "beneficiary_id": str(r_dict.get("beneficiary_id", "mule_acc_db")),
                    "timestamp": str(r_dict.get("timestamp", "2026-10-10T07:00:00Z")),
                    "status": str(r_dict.get("risk_level", "CLEARED")),
                    "score": score,
                    "is_attack": is_attack,
                    "source": "database"
                }
        except Exception:
            pass

    # 3. Deterministic hash fallback for custom entered transaction IDs
    hasher = hashlib.md5(tx_id_str.encode("utf-8")).hexdigest()
    hash_num = int(hasher[:8], 16)
    
    is_attack = "TX_FLAGGED_" in tx_id_str.upper() or "ATTACK" in tx_id_str.upper() or "MULE" in tx_id_str.upper() or (hash_num % 100 > 75)
    
    if is_attack:
        user_idx = (hash_num % 15) + 80
        user_id = f"usr_ring_leader_{user_idx}"
        amount = round(4500.0 + (hash_num % 900000) / 100.0, 2)
        merchant = "CryptoExchange_Global_FX" if (hash_num % 2 == 0) else "Offshore_Wire_Transfer"
        ip = f"185.220.101.{(hash_num % 90) + 4}"
        device_id = f"dev_guid_{(hash_num % 999) + 9000}"
        beneficiary_id = f"mule_acc_{(hash_num % 300) + 400}"
        score = round(0.82 + (hash_num % 15) / 100.0, 3)
        status = "SUSPICIOUS"
    else:
        user_idx = (hash_num % 6) + 101
        user_id = f"usr_benign_{user_idx}"
        amount = round(15.0 + (hash_num % 15000) / 100.0, 2)
        merchant = stream_manager.MERCHANTS[hash_num % len(stream_manager.MERCHANTS)]
        ip = f"192.168.1.{100 + user_idx}"
        device_id = f"dev_trusted_{100 + user_idx}"
        beneficiary_id = f"benign_merchant_{(hash_num % 50) + 10}"
        score = round(0.01 + (hash_num % 5) / 100.0, 3)
        status = "CLEARED"
        
    return {
        "transaction_id": tx_id_str,
        "user_id": user_id,
        "account_id": user_id,
        "amount": amount,
        "currency": "USD",
        "merchant": merchant,
        "ip": ip,
        "device_id": device_id,
        "beneficiary_id": beneficiary_id,
        "timestamp": "2026-10-10T07:00:00Z",
        "status": status,
        "score": score,
        "is_attack": is_attack,
        "source": "deterministic_id_lookup"
    }


def find_related_transactions(user_id: str, ip: str, device_id: str, exclude_tx_id: str) -> List[Dict[str, Any]]:
    """
    Finds actual related transactions in stream_manager or DB matching user_id, ip, or device_id.
    """
    related = []
    seen = {exclude_tx_id}
    
    # Check in-memory stream buffer
    for tx in stream_manager.get_current_stream():
        tx_id = str(tx.get("transaction_id")).strip()
        if tx_id in seen:
            continue
        if (str(tx.get("user_id")) == user_id or 
            str(tx.get("ip")) == ip or 
            str(tx.get("device_id")) == device_id):
            related.append({
                "transaction_id": tx_id,
                "user_id": str(tx.get("user_id")),
                "amount": float(tx.get("amount", 100.0)),
                "merchant": str(tx.get("merchant", "Merchant")),
                "ip": str(tx.get("ip", ip)),
                "device_id": str(tx.get("device_id", device_id)),
                "score": float(tx.get("catboost_score", tx.get("risk_score", 0.05))),
                "status": str(tx.get("status", "CLEARED")),
                "relation": "same_user" if str(tx.get("user_id")) == user_id else ("shared_ip" if str(tx.get("ip")) == ip else "shared_device")
            })
            seen.add(tx_id)
            if len(related) >= 4:
                break
                
    # Check SQLite database
    if os.path.exists(DB_PATH) and len(related) < 4:
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM transactions WHERE (account_id = ? OR ip = ? OR device_id = ?) AND transaction_id != ? LIMIT 4",
                (user_id, ip, device_id, exclude_tx_id)
            )
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                r_dict = dict(r)
                tx_id = str(r_dict.get("transaction_id")).strip()
                if tx_id not in seen:
                    related.append({
                        "transaction_id": tx_id,
                        "user_id": str(r_dict.get("account_id")),
                        "amount": float(r_dict.get("amount", 100.0)),
                        "merchant": str(r_dict.get("merchant", "Merchant")),
                        "ip": str(r_dict.get("ip", ip)),
                        "device_id": str(r_dict.get("device_id", device_id)),
                        "score": float(r_dict.get("risk_score", 0.05)),
                        "status": str(r_dict.get("risk_level", "CLEARED")),
                        "relation": "same_user" if str(r_dict.get("account_id")) == user_id else ("shared_ip" if str(r_dict.get("ip")) == ip else "shared_device")
                    })
                    seen.add(tx_id)
        except Exception:
            pass
            
    return related


def ip_to_geo(ip: str, is_attack: bool = False) -> Dict[str, Any]:
    """
    Deterministically maps an IP address to geographic coordinates, city, country, and ISP.
    """
    ip_str = str(ip).strip()
    
    # High-Risk / Offshore Tor Proxy IPs
    if ip_str.startswith("185.220.") or "185.220" in ip_str or is_attack:
        parts = [int(p) if p.isdigit() else 0 for p in ip_str.split(".")]
        last_octet = parts[-1] if len(parts) == 4 else 4
        
        locations = [
            {"city": "Frankfurt", "country": "Germany", "lat": 50.1109, "lon": 8.6821, "isp": "DE-CIX Tor Exit Node"},
            {"city": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050, "isp": "CyberBunker Anonymizer Proxy"},
            {"city": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lon": 4.9041, "isp": "NL-IX Offshore Host"},
            {"city": "Zurich", "country": "Switzerland", "lat": 47.3769, "lon": 8.5417, "isp": "Proton VPN Exit Node"}
        ]
        loc = locations[last_octet % len(locations)]
        return {
            "ip": ip_str,
            "city": loc["city"],
            "country": loc["country"],
            "location_name": f"{loc['city']}, {loc['country']}",
            "lat": loc["lat"],
            "lon": loc["lon"],
            "isp": loc["isp"],
            "is_proxy": True
        }
    elif ip_str.startswith("192.168.") or ip_str.startswith("10.") or ip_str.startswith("172."):
        # Residential / Local broadband IP
        parts = [int(p) if p.isdigit() else 0 for p in ip_str.split(".")]
        last_octet = parts[-1] if len(parts) == 4 else 101
        
        metros = [
            {"city": "New York, NY", "country": "United States", "lat": 40.7128, "lon": -74.0060, "isp": "Verizon Fios Residential"},
            {"city": "San Francisco, CA", "country": "United States", "lat": 37.7749, "lon": -122.4194, "isp": "Comcast Xfinity Broadband"},
            {"city": "Chicago, IL", "country": "United States", "lat": 41.8781, "lon": -87.6298, "isp": "AT&T Fiber Home"},
            {"city": "Austin, TX", "country": "United States", "lat": 30.2672, "lon": -97.7431, "isp": "Spectrum Internet"},
            {"city": "Seattle, WA", "country": "United States", "lat": 47.6062, "lon": -122.3321, "isp": "CenturyLink Fiber"},
            {"city": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278, "isp": "BT Broadband Residential"}
        ]
        loc = metros[(last_octet - 100) % len(metros)]
        return {
            "ip": ip_str,
            "city": loc["city"],
            "country": loc["country"],
            "location_name": f"{loc['city']}, {loc['country']}",
            "lat": loc["lat"],
            "lon": loc["lon"],
            "isp": loc["isp"],
            "is_proxy": False
        }
    else:
        # Public IP address
        hash_val = sum(int(p) if p.isdigit() else ord(p) for p in ip_str.replace(".", ""))
        public_locs = [
            {"city": "New York, NY", "country": "United States", "lat": 40.7128, "lon": -74.0060, "isp": "Verizon Business Net"},
            {"city": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278, "isp": "Virgin Media UK"},
            {"city": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503, "isp": "NTT Communications"},
            {"city": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198, "isp": "Singtel Global Network"},
            {"city": "Toronto", "country": "Canada", "lat": 43.6532, "lon": -79.3832, "isp": "Rogers Communications"},
            {"city": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522, "isp": "Orange S.A."}
        ]
        loc = public_locs[hash_val % len(public_locs)]
        return {
            "ip": ip_str,
            "city": loc["city"],
            "country": loc["country"],
            "location_name": f"{loc['city']}, {loc['country']}",
            "lat": loc["lat"],
            "lon": loc["lon"],
            "isp": loc["isp"],
            "is_proxy": False
        }

