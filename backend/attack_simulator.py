import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import ValidationError

from schemas.transaction import Transaction

def _generate_id(prefix: str = "TXN") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"

class AttackSimulator:
    """
    Vigil Attack Triggering & Simulation Engine.
    Generates synthetic payment streams containing normal activity and 7 planted fraud patterns.
    Outputs conform to the Transaction schema without leaking ground truth flags to the schema.
    """
    
    def __init__(self, start_time: datetime = None):
        self.current_time = start_time or datetime.utcnow()
        self.base_locations = ["New York", "London", "San Francisco", "Tokyo", "Berlin"]
        self.currencies = ["USD", "EUR", "GBP", "JPY"]
        self.normal_accounts = [f"ACC_NORM_{i}" for i in range(100)]
        self.normal_devices = [f"DEV_NORM_{i}" for i in range(100)]
        self.normal_ips = [f"192.168.1.{i}" for i in range(1, 200)]
        
    def _advance_time(self, seconds: int = 0, minutes: int = 0) -> str:
        self.current_time += timedelta(seconds=seconds, minutes=minutes)
        return self.current_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _build_tx(self, **kwargs) -> Dict[str, Any]:
        """Validates against the schema and returns a dictionary."""
        account_id = kwargs.get("account_id", random.choice(self.normal_accounts))
        beneficiary_id = kwargs.get("beneficiary_id", _generate_id("BEN"))
        
        tx_data = {
            "transaction_id": kwargs.get("transaction_id", _generate_id()),
            "account_id": account_id,
            "nameOrig": account_id,
            "amount": kwargs.get("amount", round(random.uniform(10.0, 500.0), 2)),
            "currency": kwargs.get("currency", "USD"),
            "device_id": kwargs.get("device_id", random.choice(self.normal_devices)),
            "ip": kwargs.get("ip", random.choice(self.normal_ips)),
            "beneficiary_id": beneficiary_id,
            "nameDest": beneficiary_id,
            "timestamp": kwargs.get("timestamp", self._advance_time(minutes=random.randint(1, 15))),
            "location": kwargs.get("location", random.choice(self.base_locations)),
            "transaction_type": kwargs.get("transaction_type", "TRANSFER"),
        }
        
        # Rigorous schema alignment check
        try:
            Transaction(**tx_data)
        except ValidationError as e:
            print(f"Schema validation failed: {e}")
            raise
            
        return tx_data

    def generate_baseline(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generates legitimate baseline traffic."""
        return [self._build_tx() for _ in range(count)]

    def generate_card_testing(self) -> List[Dict[str, Any]]:
        """Pattern 1: Card Testing (Repeated low-value authorizations)."""
        txs = []
        victim_account = _generate_id("ACC_VICTIM")
        attacker_device = _generate_id("DEV_ATTACK")
        attacker_ip = "10.0.0.99"
        
        for _ in range(5):
            txs.append(self._build_tx(
                account_id=victim_account,
                amount=round(random.uniform(0.50, 2.50), 2), # Low value
                device_id=attacker_device,
                ip=attacker_ip,
                timestamp=self._advance_time(seconds=10), # Rapid succession
                transaction_type="PAYMENT"
            ))
        return txs

    def generate_ato(self) -> List[Dict[str, Any]]:
        """Pattern 2: Account Takeover (Sudden new device/IP, large drain)."""
        account = random.choice(self.normal_accounts)
        
        # 1. Normal baseline tx
        tx1 = self._build_tx(account_id=account)
        
        # 2. ATO tx (New location, new device, high amount)
        self._advance_time(minutes=30)
        tx2 = self._build_tx(
            account_id=account,
            amount=round(random.uniform(5000.0, 10000.0), 2),
            device_id="DEV_ROGUE_999",
            ip="185.15.0.1",
            location="Unknown",
            timestamp=self._advance_time(minutes=1)
        )
        return [tx1, tx2]

    def generate_push_payment_fraud(self) -> List[Dict[str, Any]]:
        """Pattern 3: Push Payment Fraud (Scam to newly added beneficiary)."""
        account = random.choice(self.normal_accounts)
        scam_beneficiary = _generate_id("BEN_SCAMMER")
        
        return [self._build_tx(
            account_id=account,
            amount=round(random.uniform(2000.0, 4500.0), 2),
            beneficiary_id=scam_beneficiary,
            timestamp=self._advance_time(minutes=2)
        )]

    def generate_synthetic_identity(self) -> List[Dict[str, Any]]:
        """Pattern 4: Synthetic Identity Fraud (New account, erratic behavior)."""
        synthetic_account = _generate_id("ACC_SYNTH")
        device = _generate_id("DEV_SYNTH")
        
        txs = []
        for _ in range(3):
            txs.append(self._build_tx(
                account_id=synthetic_account,
                amount=round(random.uniform(500.0, 3000.0), 2),
                device_id=device,
                timestamp=self._advance_time(minutes=5)
            ))
        return txs

    def generate_mule_chain(self) -> List[Dict[str, Any]]:
        """Pattern 5: Mule Account Chain (Multi-hop fund transfer)."""
        txs = []
        amount = 10000.0
        
        hop1 = _generate_id("MULE_1")
        hop2 = _generate_id("MULE_2")
        hop3 = _generate_id("MULE_3")
        
        # Hop 1 to Hop 2
        txs.append(self._build_tx(
            account_id=hop1, beneficiary_id=hop2, amount=amount,
            timestamp=self._advance_time(minutes=1)
        ))
        # Hop 2 to Hop 3 (slightly less due to 'fee')
        txs.append(self._build_tx(
            account_id=hop2, beneficiary_id=hop3, amount=amount * 0.95,
            timestamp=self._advance_time(minutes=2)
        ))
        # Hop 3 Cash out
        txs.append(self._build_tx(
            account_id=hop3, amount=amount * 0.90, transaction_type="CASH_OUT",
            timestamp=self._advance_time(minutes=2)
        ))
        
        return txs

    def generate_device_syndicate(self) -> List[Dict[str, Any]]:
        """Pattern 6: Device Syndicate (Multiple accounts sharing same device ID)."""
        syndicate_device = "DEV_SYNDICATE_MASTER"
        txs = []
        
        for _ in range(4):
            # Distinct accounts using the exact same device footprint
            txs.append(self._build_tx(
                account_id=_generate_id("ACC_SYNDICATE"),
                device_id=syndicate_device,
                amount=round(random.uniform(1000.0, 2000.0), 2),
                timestamp=self._advance_time(minutes=10)
            ))
        return txs

    def generate_fraud_ring(self) -> List[Dict[str, Any]]:
        """Pattern 7: Coordinated Fraud Ring (Synchronized wave)."""
        txs = []
        ring_accounts = [_generate_id("RING_ACC") for _ in range(5)]
        ring_ip = "104.28.10.50"
        target_merchant = _generate_id("BEN_TARGET")
        
        for account in ring_accounts:
            txs.append(self._build_tx(
                account_id=account,
                beneficiary_id=target_merchant,
                ip=ring_ip,
                amount=round(random.uniform(300.0, 500.0), 2),
                timestamp=self._advance_time(seconds=15) # Very coordinated timing
            ))
        return txs

    def generate_full_stream(self) -> List[Dict[str, Any]]:
        """Generates a combined stream of baseline + all 7 attack patterns."""
        stream = []
        stream.extend(self.generate_baseline(20))
        stream.extend(self.generate_card_testing())
        stream.extend(self.generate_baseline(10))
        stream.extend(self.generate_ato())
        stream.extend(self.generate_push_payment_fraud())
        stream.extend(self.generate_baseline(15))
        stream.extend(self.generate_synthetic_identity())
        stream.extend(self.generate_mule_chain())
        stream.extend(self.generate_baseline(5))
        stream.extend(self.generate_device_syndicate())
        stream.extend(self.generate_fraud_ring())
        
        # Sort stream strictly by timestamp to simulate real incoming stream
        stream.sort(key=lambda x: x["timestamp"])
        return stream

if __name__ == "__main__":
    simulator = AttackSimulator()
    stream = simulator.generate_full_stream()
    
    print(f"Generated {len(stream)} synthetic transactions.")
    print("Sample Transaction (Card Testing / Mule / etc):")
    import json
    print(json.dumps(stream[-1], indent=2))
