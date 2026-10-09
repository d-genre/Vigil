"""
FRAUD-RING RADAR
Graph Query Primitives (backend/graph/graph_queries.py)

Reusable graph primitive functions for fraud investigation, money flow tracing,
and entity sharing discovery.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
import networkx as nx


def _prefix_node(node_id: str, prefix: str) -> str:
    """Helper to ensure node_id has proper prefix."""
    if not node_id.startswith(f"{prefix}:"):
        return f"{prefix}:{node_id}"
    return node_id


def get_account_neighbors(G: nx.MultiDiGraph, account_id: str) -> List[str]:
    """Returns all neighbor nodes connected to the specified account."""
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return []
    # Both successor and predecessor nodes in MultiDiGraph
    succs = set(G.successors(acc_node))
    preds = set(G.predecessors(acc_node))
    return sorted(list(succs | preds))


def get_shared_devices(G: nx.MultiDiGraph, account_id: str) -> List[str]:
    """Returns device nodes connected to account_id that are shared with other accounts."""
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return []
    
    shared_devices = []
    for neighbor in G.successors(acc_node):
        if G.nodes[neighbor].get("node_type") == "DEVICE":
            # Check if this device is connected to >1 account
            account_count = sum(
                1 for p in G.predecessors(neighbor) if G.nodes[p].get("node_type") == "ACCOUNT"
            )
            if account_count > 1:
                shared_devices.append(neighbor)
    return sorted(shared_devices)


def get_shared_ips(G: nx.MultiDiGraph, account_id: str) -> List[str]:
    """Returns IP nodes connected to account_id that are shared with other accounts."""
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return []
    
    shared_ips = []
    for neighbor in G.successors(acc_node):
        if G.nodes[neighbor].get("node_type") == "IP":
            # Check if this IP is connected to >1 account
            account_count = sum(
                1 for p in G.predecessors(neighbor) if G.nodes[p].get("node_type") == "ACCOUNT"
            )
            if account_count > 1:
                shared_ips.append(neighbor)
    return sorted(shared_ips)


def get_connected_component(G: nx.MultiDiGraph, account_id: str) -> List[str]:
    """Returns list of all nodes in the weakly connected component containing account_id."""
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return []
    # Convert to undirected view for weakly connected component search
    undirected_G = G.to_undirected(as_view=True)
    comp = nx.node_connected_component(undirected_G, acc_node)
    return sorted(list(comp))


def get_account_fan_in(G: nx.MultiDiGraph, account_id: str) -> Dict[str, Any]:
    """
    Returns incoming P2P transfer statistics for account_id:
    - fan_in_count: number of incoming transfer edges
    - total_incoming_txs: total aggregated transaction count
    - total_incoming_amount: total amount transferred in
    - source_accounts: list of sender account nodes
    """
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return {"fan_in_count": 0, "total_incoming_txs": 0, "total_incoming_amount": 0.0, "source_accounts": []}

    sources = []
    tot_txs = 0
    tot_amt = 0.0

    for pred in G.predecessors(acc_node):
        if G.nodes[pred].get("node_type") == "ACCOUNT":
            # Check P2P_TRANSFER edge data
            if G.has_edge(pred, acc_node, key="P2P_TRANSFER"):
                edge_data = G.get_edge_data(pred, acc_node, key="P2P_TRANSFER")
                sources.append(pred)
                tot_txs += edge_data.get("transaction_count", 1)
                tot_amt += edge_data.get("total_amount", 0.0)

    return {
        "fan_in_count": len(sources),
        "total_incoming_txs": tot_txs,
        "total_incoming_amount": tot_amt,
        "source_accounts": sorted(sources)
    }


def get_account_fan_out(G: nx.MultiDiGraph, account_id: str) -> Dict[str, Any]:
    """
    Returns outgoing P2P transfer statistics for account_id:
    - fan_out_count: number of outgoing transfer edges
    - total_outgoing_txs: total aggregated transaction count
    - total_outgoing_amount: total amount transferred out
    - target_accounts: list of recipient account nodes
    """
    acc_node = _prefix_node(account_id, "ACCOUNT")
    if not G.has_node(acc_node):
        return {"fan_out_count": 0, "total_outgoing_txs": 0, "total_outgoing_amount": 0.0, "target_accounts": []}

    targets = []
    tot_txs = 0
    tot_amt = 0.0

    for succ in G.successors(acc_node):
        if G.nodes[succ].get("node_type") == "ACCOUNT":
            # Check P2P_TRANSFER edge data
            if G.has_edge(acc_node, succ, key="P2P_TRANSFER"):
                edge_data = G.get_edge_data(acc_node, succ, key="P2P_TRANSFER")
                targets.append(succ)
                tot_txs += edge_data.get("transaction_count", 1)
                tot_amt += edge_data.get("total_amount", 0.0)

    return {
        "fan_out_count": len(targets),
        "total_outgoing_txs": tot_txs,
        "total_outgoing_amount": tot_amt,
        "target_accounts": sorted(targets)
    }


def get_transfer_neighbors(G: nx.MultiDiGraph, account_id: str) -> List[str]:
    """Returns list of account nodes that sent money to or received money from account_id."""
    fin = get_account_fan_in(G, account_id)
    fout = get_account_fan_out(G, account_id)
    transfer_nodes = set(fin["source_accounts"]) | set(fout["target_accounts"])
    return sorted(list(transfer_nodes))


def get_money_flow_path(G: nx.MultiDiGraph, source_account: str, target_account: str) -> Optional[List[str]]:
    """
    Finds the shortest directed P2P transfer path between source_account and target_account.
    Returns list of node IDs along the path, or None if no directed path exists.
    """
    src_node = _prefix_node(source_account, "ACCOUNT")
    tgt_node = _prefix_node(target_account, "ACCOUNT")
    if not G.has_node(src_node) or not G.has_node(tgt_node):
        return None
    
    # Subgraph view containing only P2P_TRANSFER edges
    p2p_edges = [
        (u, v, k) for u, v, k in G.edges(keys=True) if k == "P2P_TRANSFER"
    ]
    p2p_G = nx.MultiDiGraph()
    p2p_G.add_edges_from(p2p_edges)

    try:
        path = nx.shortest_path(p2p_G, source=src_node, target=tgt_node)
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def get_accounts_sharing_device(G: nx.MultiDiGraph, device_id: str) -> List[str]:
    """Returns list of account nodes sharing the specified device_id."""
    dev_node = _prefix_node(device_id, "DEVICE")
    if not G.has_node(dev_node):
        return []
    
    accounts = []
    for pred in G.predecessors(dev_node):
        if G.nodes[pred].get("node_type") == "ACCOUNT":
            accounts.append(pred)
    return sorted(accounts)


def get_accounts_sharing_ip(G: nx.MultiDiGraph, ip_address: str) -> List[str]:
    """Returns list of account nodes sharing the specified ip_address."""
    ip_node = _prefix_node(ip_address, "IP")
    if not G.has_node(ip_node):
        return []
    
    accounts = []
    for pred in G.predecessors(ip_node):
        if G.nodes[pred].get("node_type") == "ACCOUNT":
            accounts.append(pred)
    return sorted(accounts)
