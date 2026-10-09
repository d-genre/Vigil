import asyncio
import httpx
import uuid
from datetime import datetime, timezone

# URL of the local Vigil FastAPI server
API_URL = "http://localhost:8000/transactions"

def generate_tx(amount: float, desc: str) -> dict:
    return {
        "transaction_id": f"TX_{uuid.uuid4().hex[:8].upper()}",
        "account_id": "ACC_DEMO_01",
        "amount": amount,
        "currency": "INR",
        "device_id": "DEV_DEMO",
        "ip": "192.168.1.100",
        "beneficiary_id": "BEN_DEMO_99",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": "Mumbai, IN",
        "transaction_type": "TRANSFER",
        "_desc": desc  # Used for local printing, will be ignored/stripped by API if not in schema, wait Pydantic might reject unknown fields if extra='forbid', but schemas/transaction.py has populate_by_name=True and frozen=False. Let's remove it from payload to be safe.
    }

async def stream_transactions():
    """Streams exactly 3 sample transactions for the jury pitch."""
    print("=" * 60)
    print(f"🚀 Starting Vigil Demo Stream against {API_URL}")
    print("=" * 60)
    
    # Define the 3 sample scenarios
    scenarios = [
        {"desc": "Low risk (Coffee)", "amount": 250.0},
        {"desc": "Normal (Rent)", "amount": 4500.0},
        {"desc": "High-value attack", "amount": 55000.0}
    ]

    async with httpx.AsyncClient() as client:
        for idx, scenario in enumerate(scenarios, 1):
            # Create payload
            tx_payload = {
                "transaction_id": f"TX_{uuid.uuid4().hex[:8].upper()}",
                "account_id": "ACC_DEMO_01",
                "amount": scenario["amount"],
                "currency": "INR",
                "device_id": "DEV_DEMO",
                "ip": "192.168.1.100",
                "beneficiary_id": "BEN_DEMO_99",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "location": "Mumbai, IN",
                "transaction_type": "TRANSFER"
            }
            
            print(f"\n[{idx}/3] Sending: {scenario['desc']} (₹{scenario['amount']})")
            print(f"ID: {tx_payload['transaction_id']}")
            
            try:
                response = await client.post(API_URL, json=tx_payload)
                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"✅ SUCCESS: Risk={result.get('risk_level')}, Score={result.get('risk_score', 0.0):.3f}")
                    print(f"   Action Taken: {result.get('action_taken')}")
                else:
                    print(f"❌ FAILED ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"❌ Connection Error: {e}")
            
            await asyncio.sleep(2.0) # Pause for dramatic effect during pitch

    print("\n" + "=" * 60)
    print("🏁 Demo Stream Completed.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(stream_transactions())
