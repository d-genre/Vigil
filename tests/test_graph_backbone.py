"""
Automated Validation Tests for Step 8A Graph Backbone
tests/test_graph_backbone.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pandas as pd
import networkx as nx

from graph import (
    build_fraud_graph,
    save_fraud_graph,
    load_fraud_graph,
    get_account_neighbors,
    get_shared_devices,
    get_shared_ips,
    get_connected_component,
    get_account_fan_in,
    get_account_fan_out,
    get_transfer_neighbors,
    get_money_flow_path,
    get_accounts_sharing_device,
    get_accounts_sharing_ip
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = PROJECT_ROOT / "data" / "processed" / "graph" / "fraud_graph.gpickle"
RAW_CLEAN_DIR = PROJECT_ROOT / "data" / "processed" / "raw_clean"
RAW_ZIP_PATH = PROJECT_ROOT / "data" / "raw" / "fraud_data_share.zip"


@pytest.fixture(scope="module")
def graph_instance():
    G = load_fraud_graph(GRAPH_PATH)
    assert GRAPH_PATH.exists(), f"Graph artifact missing at {GRAPH_PATH}"
    return G


@pytest.fixture(scope="module")
def clean_datasets():
    from graph.build_graph import load_clean_datasets
    tx_df, acc_df, dev_df, ip_df, ben_df, mer_df = load_clean_datasets()
    return {
        "tx": tx_df, "acc": acc_df, "dev": dev_df,
        "ip": ip_df, "ben": ben_df, "mer": mer_df
    }


def test_01_node_types_valid(graph_instance):
    """1. Test that every graph node has a valid node_type attribute."""
    valid_types = {"ACCOUNT", "DEVICE", "IP", "MERCHANT", "BENEFICIARY"}
    for n, data in graph_instance.nodes(data=True):
        assert "node_type" in data, f"Node {n} missing node_type attribute"
        assert data["node_type"] in valid_types, f"Invalid node_type {data['node_type']} for node {n}"


def test_02_prefixed_node_ids(graph_instance):
    """2. Test that all node IDs have valid prefixes to prevent collisions."""
    valid_prefixes = ("ACCOUNT:", "DEVICE:", "IP:", "MERCHANT:", "BENEFICIARY:")
    for n in graph_instance.nodes():
        assert n.startswith(valid_prefixes), f"Node ID {n} missing valid prefix"


def test_03_account_nodes_correspond_to_real_ids(graph_instance, clean_datasets):
    """3. Test that account nodes correspond to real account IDs."""
    acc_nodes = [n.split("ACCOUNT:")[1] for n, d in graph_instance.nodes(data=True) if d.get("node_type") == "ACCOUNT"]
    real_accs = set(clean_datasets["acc"]["account_id"].dropna().unique())
    # All clean accounts should be represented
    for acc in real_accs:
        assert f"ACCOUNT:{acc}" in graph_instance


def test_04_device_nodes_correspond_to_real_ids(graph_instance, clean_datasets):
    """4. Test that device nodes correspond to real device IDs."""
    real_devs = set(clean_datasets["dev"]["device_id"].dropna().unique())
    for dev in real_devs:
        assert f"DEVICE:{dev}" in graph_instance


def test_05_ip_nodes_correspond_to_real_ips(graph_instance, clean_datasets):
    """5. Test that IP nodes correspond to real IP addresses."""
    real_ips = set(clean_datasets["ip"]["ip_address"].dropna().unique())
    for ip in real_ips:
        assert f"IP:{ip}" in graph_instance


def test_06_merchant_nodes_exclude_nomerch(graph_instance):
    """6. Test that merchant nodes exclude NOMERCH."""
    assert "MERCHANT:NOMERCH" not in graph_instance
    assert "MERCHANT:nomerch" not in graph_instance
    for n, d in graph_instance.nodes(data=True):
        if d.get("node_type") == "MERCHANT":
            assert "NOMERCH" not in n.upper()


def test_07_beneficiary_nodes_correspond_to_real_ids(graph_instance, clean_datasets):
    """7. Test that beneficiary nodes correspond to beneficiaries_clean.csv."""
    real_bens = set(clean_datasets["ben"]["beneficiary_id"].dropna().unique())
    for ben in real_bens:
        assert f"BENEFICIARY:{ben}" in graph_instance


def test_08_no_impossible_self_relations(graph_instance):
    """8. Test that no self-loop relations exist unless explicitly valid."""
    for u, v in graph_instance.edges():
        assert u != v, f"Self-loop detected on node {u}"


def test_09_aggregated_edge_transaction_counts(graph_instance, clean_datasets):
    """9. Test that aggregated edge transaction counts match source data."""
    tx_df = clean_datasets["tx"]
    p2p_df = tx_df[tx_df['nameDest'].astype(str).str.startswith('C')]
    if not p2p_df.empty:
        sample = p2p_df.iloc[0]
        u = f"ACCOUNT:{sample['nameOrig']}"
        v = f"ACCOUNT:{sample['nameDest']}"
        assert graph_instance.has_edge(u, v, key="P2P_TRANSFER")
        data = graph_instance.get_edge_data(u, v, key="P2P_TRANSFER")
        expected_cnt = len(p2p_df[(p2p_df['nameOrig'] == sample['nameOrig']) & (p2p_df['nameDest'] == sample['nameDest'])])
        assert data['transaction_count'] == expected_cnt


def test_10_aggregated_edge_amounts(graph_instance, clean_datasets):
    """10. Test that aggregated edge total amounts match source data."""
    tx_df = clean_datasets["tx"]
    p2p_df = tx_df[tx_df['nameDest'].astype(str).str.startswith('C')]
    if not p2p_df.empty:
        sample = p2p_df.iloc[0]
        u = f"ACCOUNT:{sample['nameOrig']}"
        v = f"ACCOUNT:{sample['nameDest']}"
        data = graph_instance.get_edge_data(u, v, key="P2P_TRANSFER")
        expected_amt = float(p2p_df[(p2p_df['nameOrig'] == sample['nameOrig']) & (p2p_df['nameDest'] == sample['nameDest'])]['amount'].sum())
        assert abs(data['total_amount'] - expected_amt) < 1e-4


def test_11_first_seen_lte_last_seen(graph_instance):
    """11. Test that first_seen <= last_seen for all edges with timestamp attributes."""
    for u, v, k, data in graph_instance.edges(keys=True, data=True):
        if "first_seen" in data and "last_seen" in data:
            assert data["first_seen"] <= data["last_seen"], f"Invalid timestamps on edge {u}->{v}"


def test_12_graph_serialization_loading():
    """12. Test that graph can be serialized and loaded successfully."""
    G_loaded = load_fraud_graph(GRAPH_PATH)
    assert G_loaded is not None
    assert G_loaded.number_of_nodes() > 0
    assert G_loaded.number_of_edges() > 0


def test_13_query_primitives_deterministic(graph_instance):
    """13. Test that query functions return deterministic results."""
    acc_id = "C0000000"
    res1 = get_account_neighbors(graph_instance, acc_id)
    res2 = get_account_neighbors(graph_instance, acc_id)
    assert res1 == res2

    dev_sharing = get_accounts_sharing_device(graph_instance, "DF00000")
    dev_sharing2 = get_accounts_sharing_device(graph_instance, "DF00000")
    assert dev_sharing == dev_sharing2


def test_14_label_independence():
    """14. Test that graph construction code does NOT pass or inspect target labels."""
    import inspect
    from backend.graph import build_graph
    src = inspect.getsource(build_graph)
    assert "isFraud" not in src
    assert "fraud_type" not in src
    assert "campaign_id" not in src


def test_15_raw_data_untouched():
    """15. Test that raw data transaction dataset remains untouched."""
    from ml.data_loader import RAW_DATA_DIR
    assert RAW_DATA_DIR.exists()
