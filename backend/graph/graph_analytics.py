"""
FRAUD-RING RADAR
Graph Analytics Module (backend/graph/graph_analytics.py)

Calculates graph structural metrics, degree distributions, connected components,
and entity sharing statistics.
"""

from typing import Dict, Any
import numpy as np
import networkx as nx


def calculate_graph_statistics(G: nx.MultiDiGraph) -> Dict[str, Any]:
    """
    Computes comprehensive structural statistics for the NetworkX fraud graph.
    """
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    # Node count by node_type
    node_types = {}
    for n, data in G.nodes(data=True):
        nt = data.get("node_type", "UNKNOWN")
        node_types[nt] = node_types.get(nt, 0) + 1

    # Edge count by relation_type
    edge_types = {}
    for u, v, k, data in G.edges(keys=True, data=True):
        rel = data.get("relation_type", k)
        edge_types[rel] = edge_types.get(rel, 0) + 1

    # Connected Components (Weakly Connected Components on directed graph)
    weak_components = list(nx.weakly_connected_components(G))
    num_components = len(weak_components)
    comp_sizes = [len(c) for c in weak_components]
    largest_comp_size = max(comp_sizes) if comp_sizes else 0
    mean_comp_size = float(np.mean(comp_sizes)) if comp_sizes else 0.0

    # Degrees across node types
    account_degrees = [d for n, d in G.degree() if G.nodes[n].get("node_type") == "ACCOUNT"]
    device_degrees = [d for n, d in G.degree() if G.nodes[n].get("node_type") == "DEVICE"]
    ip_degrees = [d for n, d in G.degree() if G.nodes[n].get("node_type") == "IP"]
    merchant_degrees = [d for n, d in G.degree() if G.nodes[n].get("node_type") == "MERCHANT"]

    # Sharing Statistics
    shared_device_count = 0
    for n in G.nodes():
        if G.nodes[n].get("node_type") == "DEVICE":
            # Connected accounts count
            acc_count = sum(1 for p in G.predecessors(n) if G.nodes[p].get("node_type") == "ACCOUNT")
            if acc_count > 1:
                shared_device_count += 1

    shared_ip_count = 0
    for n in G.nodes():
        if G.nodes[n].get("node_type") == "IP":
            acc_count = sum(1 for p in G.predecessors(n) if G.nodes[p].get("node_type") == "ACCOUNT")
            if acc_count > 1:
                shared_ip_count += 1

    stats = {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_types": node_types,
        "edge_types": edge_types,
        "connected_components": {
            "total_components": num_components,
            "largest_component_size": largest_comp_size,
            "mean_component_size": mean_comp_size
        },
        "degrees": {
            "account_mean_degree": float(np.mean(account_degrees)) if account_degrees else 0.0,
            "account_max_degree": int(np.max(account_degrees)) if account_degrees else 0,
            "device_mean_degree": float(np.mean(device_degrees)) if device_degrees else 0.0,
            "device_max_degree": int(np.max(device_degrees)) if device_degrees else 0,
            "ip_mean_degree": float(np.mean(ip_degrees)) if ip_degrees else 0.0,
            "ip_max_degree": int(np.max(ip_degrees)) if ip_degrees else 0,
            "merchant_mean_degree": float(np.mean(merchant_degrees)) if merchant_degrees else 0.0,
            "merchant_max_degree": int(np.max(merchant_degrees)) if merchant_degrees else 0,
        },
        "sharing_stats": {
            "shared_devices_count": shared_device_count,
            "shared_ips_count": shared_ip_count
        }
    }

    return stats


if __name__ == "__main__":
    from backend.graph.build_graph import load_fraud_graph
    G = load_fraud_graph()
    stats = calculate_graph_statistics(G)
    print("Graph Statistics Summary:")
    print(stats)
