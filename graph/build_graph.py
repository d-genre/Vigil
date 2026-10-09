"""
FRAUD-RING RADAR
Graph Building & Serialization Module (backend/graph/build_graph.py)

Constructs a heterogeneous NetworkX MultiDiGraph from cleaned dataset files.
Preserves entity relationship evidence without using fraud labels.
"""

from pathlib import Path
import os
import joblib
import pandas as pd
import networkx as nx
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CLEAN_DIR = PROJECT_ROOT / "data" / "processed" / "raw_clean"
GRAPH_DIR = PROJECT_ROOT / "data" / "processed" / "graph"
DEFAULT_GRAPH_PATH = GRAPH_DIR / "fraud_graph.gpickle"


def load_clean_datasets(data_dir: Optional[Path] = None):
    """Loads cleaned processed CSV files or falls back to ml.data_loader."""
    dpath = data_dir or RAW_CLEAN_DIR
    if (dpath / "transactions_clean.csv").exists():
        tx_df = pd.read_csv(dpath / "transactions_clean.csv")
        acc_df = pd.read_csv(dpath / "accounts_clean.csv")
        dev_df = pd.read_csv(dpath / "devices_clean.csv")
        ip_df = pd.read_csv(dpath / "ips_clean.csv")
        ben_df = pd.read_csv(dpath / "beneficiaries_clean.csv")
        mer_df = pd.read_csv(dpath / "merchants_clean.csv")
        return tx_df, acc_df, dev_df, ip_df, ben_df, mer_df
    
    from ml import data_loader
    return (
        data_loader.load_transactions(processed=True),
        data_loader.load_accounts(processed=True),
        data_loader.load_devices(processed=True),
        data_loader.load_ips(processed=True),
        data_loader.load_beneficiaries(processed=True),
        data_loader.load_merchants(processed=True)
    )


def build_fraud_graph(data_dir: Optional[Path] = None) -> nx.MultiDiGraph:
    """
    Builds the heterogeneous NetworkX fraud backbone graph.
    
    Node Types:
      - ACCOUNT: prefixed with 'ACCOUNT:'
      - DEVICE: prefixed with 'DEVICE:'
      - IP: prefixed with 'IP:'
      - MERCHANT: prefixed with 'MERCHANT:' (excludes NOMERCH)
      - BENEFICIARY: prefixed with 'BENEFICIARY:'
      
    Edge Types:
      - ACCOUNT_USED_DEVICE (ACCOUNT -> DEVICE)
      - ACCOUNT_USED_IP (ACCOUNT -> IP)
      - ACCOUNT_TRANSACTED_MERCHANT (ACCOUNT -> MERCHANT)
      - P2P_TRANSFER (ACCOUNT -> ACCOUNT)
      - ACCOUNT_HAS_BENEFICIARY (ACCOUNT -> BENEFICIARY)
    """
    tx_df, acc_df, dev_df, ip_df, ben_df, mer_df = load_clean_datasets(data_dir)
    
    G = nx.MultiDiGraph()

    # 1. Add Nodes
    for acc in acc_df['account_id'].dropna().unique():
        G.add_node(f"ACCOUNT:{acc}", node_type="ACCOUNT")
        
    for dev in dev_df['device_id'].dropna().unique():
        G.add_node(f"DEVICE:{dev}", node_type="DEVICE")
        
    for ip in ip_df['ip_address'].dropna().unique():
        G.add_node(f"IP:{ip}", node_type="IP")
        
    for mer in mer_df['merchant_id'].dropna().unique():
        if str(mer).upper() != "NOMERCH":
            G.add_node(f"MERCHANT:{mer}", node_type="MERCHANT")
            
    for ben in ben_df['beneficiary_id'].dropna().unique():
        G.add_node(f"BENEFICIARY:{ben}", node_type="BENEFICIARY")

    # 2. Add Aggregated Edges

    # A. ACCOUNT -> DEVICE
    acc_dev_agg = tx_df.dropna(subset=['nameOrig', 'device_id']).groupby(['nameOrig', 'device_id']).agg(
        transaction_count=('transaction_id', 'count'),
        first_seen=('timestamp', 'min'),
        last_seen=('timestamp', 'max')
    ).reset_index()

    for row in acc_dev_agg.itertuples(index=False):
        u = f"ACCOUNT:{row.nameOrig}"
        v = f"DEVICE:{row.device_id}"
        if not G.has_node(u):
            G.add_node(u, node_type="ACCOUNT")
        if not G.has_node(v):
            G.add_node(v, node_type="DEVICE")
        G.add_edge(u, v, key="ACCOUNT_USED_DEVICE", relation_type="ACCOUNT_USED_DEVICE",
                   transaction_count=int(row.transaction_count),
                   first_seen=str(row.first_seen), last_seen=str(row.last_seen))

    # B. ACCOUNT -> IP
    acc_ip_agg = tx_df.dropna(subset=['nameOrig', 'ip_address']).groupby(['nameOrig', 'ip_address']).agg(
        transaction_count=('transaction_id', 'count'),
        first_seen=('timestamp', 'min'),
        last_seen=('timestamp', 'max')
    ).reset_index()

    for row in acc_ip_agg.itertuples(index=False):
        u = f"ACCOUNT:{row.nameOrig}"
        v = f"IP:{row.ip_address}"
        if not G.has_node(u):
            G.add_node(u, node_type="ACCOUNT")
        if not G.has_node(v):
            G.add_node(v, node_type="IP")
        G.add_edge(u, v, key="ACCOUNT_USED_IP", relation_type="ACCOUNT_USED_IP",
                   transaction_count=int(row.transaction_count),
                   first_seen=str(row.first_seen), last_seen=str(row.last_seen))

    # C. ACCOUNT -> MERCHANT (Exclude NOMERCH)
    tx_mer = tx_df[tx_df['merchant_id'].astype(str).str.upper() != 'NOMERCH'].dropna(subset=['nameOrig', 'merchant_id'])
    acc_mer_agg = tx_mer.groupby(['nameOrig', 'merchant_id']).agg(
        transaction_count=('transaction_id', 'count'),
        total_amount=('amount', 'sum'),
        first_seen=('timestamp', 'min'),
        last_seen=('timestamp', 'max')
    ).reset_index()

    for row in acc_mer_agg.itertuples(index=False):
        u = f"ACCOUNT:{row.nameOrig}"
        v = f"MERCHANT:{row.merchant_id}"
        if not G.has_node(u):
            G.add_node(u, node_type="ACCOUNT")
        if not G.has_node(v):
            G.add_node(v, node_type="MERCHANT")
        G.add_edge(u, v, key="ACCOUNT_TRANSACTED_MERCHANT", relation_type="ACCOUNT_TRANSACTED_MERCHANT",
                   transaction_count=int(row.transaction_count),
                   total_amount=float(row.total_amount),
                   first_seen=str(row.first_seen), last_seen=str(row.last_seen))

    # D. ACCOUNT -> ACCOUNT (P2P Transfers - Exclude self-loops where nameOrig == nameDest)
    p2p_tx = tx_df[(tx_df['nameDest'].astype(str).str.startswith('C')) & (tx_df['nameOrig'] != tx_df['nameDest'])].dropna(subset=['nameOrig', 'nameDest'])
    acc_acc_agg = p2p_tx.groupby(['nameOrig', 'nameDest']).agg(
        transaction_count=('transaction_id', 'count'),
        total_amount=('amount', 'sum'),
        first_seen=('timestamp', 'min'),
        last_seen=('timestamp', 'max')
    ).reset_index()

    for row in acc_acc_agg.itertuples(index=False):
        u = f"ACCOUNT:{row.nameOrig}"
        v = f"ACCOUNT:{row.nameDest}"
        if not G.has_node(u):
            G.add_node(u, node_type="ACCOUNT")
        if not G.has_node(v):
            G.add_node(v, node_type="ACCOUNT")
        G.add_edge(u, v, key="P2P_TRANSFER", relation_type="P2P_TRANSFER",
                   transaction_count=int(row.transaction_count),
                   total_amount=float(row.total_amount),
                   first_seen=str(row.first_seen), last_seen=str(row.last_seen))

    # E. ACCOUNT -> BENEFICIARY (Exclude self-loops if account == beneficiary)
    for row in ben_df.dropna(subset=['account_id', 'beneficiary_id']).itertuples(index=False):
        u = f"ACCOUNT:{row.account_id}"
        v = f"BENEFICIARY:{row.beneficiary_id}"
        if not G.has_node(u):
            G.add_node(u, node_type="ACCOUNT")
        if not G.has_node(v):
            G.add_node(v, node_type="BENEFICIARY")
        G.add_edge(u, v, key="ACCOUNT_HAS_BENEFICIARY", relation_type="ACCOUNT_HAS_BENEFICIARY",
                   beneficiary_id=str(row.beneficiary_id),
                   beneficiary_account=f"ACCOUNT:{row.beneficiary_account}" if pd.notnull(row.beneficiary_account) else "",
                   created_at=str(row.created_at))

    return G


def save_fraud_graph(G: nx.MultiDiGraph, save_path: Optional[Path] = None):
    """Saves the NetworkX graph artifact using joblib serialization."""
    spath = save_path or DEFAULT_GRAPH_PATH
    spath.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(G, spath)
    print(f"Saved graph artifact to {spath}")


def load_fraud_graph(save_path: Optional[Path] = None) -> nx.MultiDiGraph:
    """Loads saved NetworkX graph artifact or builds it if missing."""
    spath = save_path or DEFAULT_GRAPH_PATH
    if spath and spath.exists():
        return joblib.load(spath)
    G = build_fraud_graph()
    if spath:
        try:
            save_fraud_graph(G, spath)
        except Exception:
            pass
    return G


if __name__ == "__main__":
    print("Building fraud graph backbone...")
    G = build_fraud_graph()
    save_fraud_graph(G)
    print(f"Graph constructed successfully with {G.number_of_nodes():,} nodes and {G.number_of_edges():,} edges.")
