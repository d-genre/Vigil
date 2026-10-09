import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "vigil.db")

def get_db():
    """Returns a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the SQLite database with required tables and indexes."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create transactions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            account_id TEXT,
            amount REAL,
            currency TEXT,
            device_id TEXT,
            ip TEXT,
            beneficiary_id TEXT,
            timestamp TEXT,
            location TEXT,
            transaction_type TEXT,
            risk_score REAL,
            risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add indexes for frequent queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_transaction_id ON transactions (transaction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_account_id ON transactions (account_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_risk_level ON transactions (risk_level)")
    
    conn.commit()
    conn.close()

# Auto-initialize database on import if not existing
init_db()

if __name__ == "__main__":
    init_db()

