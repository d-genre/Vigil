import time
import json
import random
from backend.attack_simulator import AttackSimulator

def stream_live_transactions():
    print("🔴 Starting Vigil Live Transaction Streamer...")
    print("Press Ctrl+C to stop streaming.\n")
    
    simulator = AttackSimulator()
    
    try:
        while True:
            # Generate a small batch or single stream packet
            # The simulator can provide baseline or mixed patterns on the fly
            stream = simulator.generate_full_stream()
            
            for tx in stream:
                # Print the live event cleanly to the terminal
                print(f"📡 [LIVE TX STREAM] ID: {tx['transaction_id']} | Account: {tx['account_id']} | Amount: ${tx['amount']} | Type: {tx.get('transaction_type', 'TRANSFER')}")
                
                # Optional: Append live transactions to a live log file or push to a queue here
                
                # Wait a realistic number of seconds before the next transaction
                time.sleep(random.uniform(0.5, 1.5))
                
    except KeyboardInterrupt:
        print("\n🛑 Live stream stopped by user.")

if __name__ == "__main__":
    stream_live_transactions()
