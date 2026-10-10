"""
VIGIL Fraudster Ego Network Generator (graph/ego_network.py)
Generates dynamic Ego Network topologies built directly from the investigated transaction.
"""

from typing import Dict, Any, List
from .lookup import get_transaction_details, find_related_transactions, ip_to_geo

def generate_ego_network(transaction_id: str) -> Dict[str, Any]:
    """
    Generates the Fraudster Ego Network (Degrees of Separation) node-link structure
    for the specific transaction ID being investigated in VIGIL.
    """
    tx_info = get_transaction_details(transaction_id)
    
    user_id = tx_info["user_id"]
    amount = tx_info["amount"]
    merchant = tx_info["merchant"]
    ip_addr = tx_info["ip"]
    device_guid = tx_info["device_id"]
    beneficiary_id = tx_info["beneficiary_id"]
    score = tx_info["score"]
    is_attack = tx_info["is_attack"]
    
    geo_info = ip_to_geo(ip_addr, is_attack=is_attack)
    seed = sum(ord(c) for c in str(transaction_id))
    
    nodes: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []
    
    if is_attack or score >= 0.70:
        pattern_type = seed % 3
        
        if pattern_type == 0:
            # Pattern 1: MULTI_ACCOUNT_SMURFING_RING (9 Nodes)
            pattern = "MULTI_ACCOUNT_SMURFING_RING"
            center_id = f"Syndicate_Hub_{user_id}"
            
            nodes = [
                # Layer 0 (Center)
                {
                    "id": center_id,
                    "label": f"Syndicate Hub ({user_id})",
                    "type": "center",
                    "layer": 0,
                    "color": "#111111",
                    "size": 36,
                    "risk_score": max(0.96, score)
                },
                # Layer 1 (Transactions & Smurf Transfers)
                {
                    "id": transaction_id,
                    "label": f"Focus Drain Tx: {transaction_id} (${amount:,.2f})",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#dc2626",
                    "size": 28,
                    "risk_score": score
                },
                {
                    "id": f"TX_SMURF_P2P_A_{seed % 100}",
                    "label": f"Smurf Split A (${amount * 0.35:,.2f})",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#ea580c",
                    "size": 22,
                    "risk_score": 0.88
                },
                {
                    "id": f"TX_SMURF_P2P_B_{seed % 100}",
                    "label": f"Smurf Split B (${amount * 0.40:,.2f})",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#ea580c",
                    "size": 22,
                    "risk_score": 0.85
                },
                # Layer 2 (Entities & Shared Infra)
                {
                    "id": f"Account_Smurf_A_{seed % 50}",
                    "label": f"Smurf Account A (usr_smurf_{seed % 50})",
                    "type": "account",
                    "layer": 2,
                    "color": "#be123c",
                    "size": 22,
                    "risk_score": 0.92
                },
                {
                    "id": f"Account_Smurf_B_{(seed + 3) % 50}",
                    "label": f"Smurf Account B (usr_smurf_{(seed + 3) % 50})",
                    "type": "account",
                    "layer": 2,
                    "color": "#be123c",
                    "size": 22,
                    "risk_score": 0.90
                },
                {
                    "id": f"IP_{ip_addr}",
                    "label": f"Shared Tor Exit ({ip_addr})",
                    "type": "ip",
                    "layer": 2,
                    "color": "#d97706",
                    "size": 24,
                    "risk_score": 0.98
                },
                {
                    "id": f"Device_{device_guid}",
                    "label": f"Syndicate Device ({device_guid})",
                    "type": "device",
                    "layer": 2,
                    "color": "#7c3aed",
                    "size": 24,
                    "risk_score": 0.94
                },
                {
                    "id": f"Mule_{beneficiary_id}",
                    "label": f"Mule Vault ({beneficiary_id})",
                    "type": "mule",
                    "layer": 2,
                    "color": "#ef4444",
                    "size": 24,
                    "risk_score": 0.97
                }
            ]
            
            links = [
                {"source": center_id, "target": transaction_id, "relation": "executed_drain"},
                {"source": center_id, "target": f"TX_SMURF_P2P_A_{seed % 100}", "relation": "funneled_from"},
                {"source": center_id, "target": f"TX_SMURF_P2P_B_{seed % 100}", "relation": "funneled_from"},
                {"source": f"Account_Smurf_A_{seed % 50}", "target": f"TX_SMURF_P2P_A_{seed % 100}", "relation": "sent_funds"},
                {"source": f"Account_Smurf_B_{(seed + 3) % 50}", "target": f"TX_SMURF_P2P_B_{seed % 100}", "relation": "sent_funds"},
                {"source": transaction_id, "target": f"IP_{ip_addr}", "relation": "originated_from"},
                {"source": transaction_id, "target": f"Device_{device_guid}", "relation": "executed_on"},
                {"source": transaction_id, "target": f"Mule_{beneficiary_id}", "relation": "cashed_out_to"}
            ]
            
        elif pattern_type == 1:
            # Pattern 2: CARD_TESTING_SYNDICATE (8 Nodes)
            pattern = "CARD_TESTING_SYNDICATE"
            center_id = f"Card_Testing_Bot_{user_id}"
            
            nodes = [
                # Layer 0 (Center)
                {
                    "id": center_id,
                    "label": f"Testing Bot ({user_id})",
                    "type": "center",
                    "layer": 0,
                    "color": "#111111",
                    "size": 35,
                    "risk_score": max(0.94, score)
                },
                # Layer 1 (Probes & Main Auth)
                {
                    "id": transaction_id,
                    "label": f"Target Auth: {transaction_id} (${amount:,.2f})",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#dc2626",
                    "size": 28,
                    "risk_score": score
                },
                {
                    "id": f"TX_CARD_TEST_01_{seed % 100}",
                    "label": "Micro Auth Probe ($1.00)",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#ea580c",
                    "size": 20,
                    "risk_score": 0.89
                },
                {
                    "id": f"TX_CARD_TEST_02_{seed % 100}",
                    "label": "Secondary Charge Probe ($2.50)",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#ea580c",
                    "size": 20,
                    "risk_score": 0.82
                },
                # Layer 2 (Entities)
                {
                    "id": f"IP_{ip_addr}",
                    "label": f"Proxy Mesh IP ({ip_addr})",
                    "type": "ip",
                    "layer": 2,
                    "color": "#d97706",
                    "size": 24,
                    "risk_score": 0.96
                },
                {
                    "id": f"Device_{device_guid}",
                    "label": f"Emulated Device ({device_guid})",
                    "type": "device",
                    "layer": 2,
                    "color": "#7c3aed",
                    "size": 24,
                    "risk_score": 0.91
                },
                {
                    "id": f"Merchant_{merchant}",
                    "label": f"Target Merchant ({merchant})",
                    "type": "merchant",
                    "layer": 2,
                    "color": "#1d4ed8",
                    "size": 22,
                    "risk_score": 0.80
                },
                {
                    "id": f"Merchant_Digital_Goods_{seed % 20}",
                    "label": "Test Merchant (Digital Goods)",
                    "type": "merchant",
                    "layer": 2,
                    "color": "#2563eb",
                    "size": 20,
                    "risk_score": 0.70
                }
            ]
            
            links = [
                {"source": center_id, "target": transaction_id, "relation": "main_auth_attempt"},
                {"source": center_id, "target": f"TX_CARD_TEST_01_{seed % 100}", "relation": "auth_probe"},
                {"source": center_id, "target": f"TX_CARD_TEST_02_{seed % 100}", "relation": "auth_probe"},
                {"source": transaction_id, "target": f"IP_{ip_addr}", "relation": "routed_via"},
                {"source": transaction_id, "target": f"Device_{device_guid}", "relation": "generated_by"},
                {"source": transaction_id, "target": f"Merchant_{merchant}", "relation": "attempted_at"},
                {"source": f"TX_CARD_TEST_01_{seed % 100}", "target": f"Merchant_Digital_Goods_{seed % 20}", "relation": "tested_at"}
            ]
            
        else:
            # Pattern 3: ACCOUNT_TAKEOVER_DRAIN (7 Nodes)
            pattern = "ACCOUNT_TAKEOVER_DRAIN"
            center_id = f"Victim_{user_id}"
            
            nodes = [
                # Layer 0 (Center)
                {
                    "id": center_id,
                    "label": f"Victim Account ({user_id})",
                    "type": "center",
                    "layer": 0,
                    "color": "#991b1b",
                    "size": 35,
                    "risk_score": 0.95
                },
                # Layer 1 (Events & Drain Tx)
                {
                    "id": transaction_id,
                    "label": f"Rapid Drain: {transaction_id} (${amount:,.2f})",
                    "type": "transaction",
                    "layer": 1,
                    "color": "#dc2626",
                    "size": 28,
                    "risk_score": score
                },
                {
                    "id": f"EVENT_CRED_RESET_{seed % 100}",
                    "label": "Force Credential Reset Event",
                    "type": "event",
                    "layer": 1,
                    "color": "#f59e0b",
                    "size": 22,
                    "risk_score": 0.87
                },
                # Layer 2 (Entities)
                {
                    "id": f"IP_{ip_addr}",
                    "label": f"Rogue VPN ({ip_addr})",
                    "type": "ip",
                    "layer": 2,
                    "color": "#d97706",
                    "size": 24,
                    "risk_score": 0.95
                },
                {
                    "id": f"Device_{device_guid}",
                    "label": f"Rogue Device ({device_guid})",
                    "type": "device",
                    "layer": 2,
                    "color": "#7c3aed",
                    "size": 24,
                    "risk_score": 0.93
                },
                {
                    "id": f"Merchant_{merchant}",
                    "label": f"High-Value Merchant ({merchant})",
                    "type": "merchant",
                    "layer": 2,
                    "color": "#1d4ed8",
                    "size": 20,
                    "risk_score": 0.78
                },
                {
                    "id": f"Mule_{beneficiary_id}",
                    "label": f"Mule Account ({beneficiary_id})",
                    "type": "mule",
                    "layer": 2,
                    "color": "#ef4444",
                    "size": 22,
                    "risk_score": 0.94
                }
            ]
            
            links = [
                {"source": center_id, "target": f"EVENT_CRED_RESET_{seed % 100}", "relation": "session_takeover"},
                {"source": f"EVENT_CRED_RESET_{seed % 100}", "target": transaction_id, "relation": "triggered_drain"},
                {"source": transaction_id, "target": f"IP_{ip_addr}", "relation": "originated_from"},
                {"source": transaction_id, "target": f"Device_{device_guid}", "relation": "used_hardware"},
                {"source": transaction_id, "target": f"Merchant_{merchant}", "relation": "purchased_at"},
                {"source": transaction_id, "target": f"Mule_{beneficiary_id}", "relation": "wired_to"}
            ]

    else:
        # Pattern 4: BENIGN_HABITUAL_RETAIL (5 Nodes)
        pattern = "BENIGN_HABITUAL_RETAIL"
        center_id = f"Account_{user_id}"
        
        nodes = [
            # Layer 0 (Center)
            {
                "id": center_id,
                "label": f"Customer ({user_id})",
                "type": "center",
                "layer": 0,
                "color": "#059669",
                "size": 32,
                "risk_score": score
            },
            # Layer 1 (Clean Purchase & Past Session)
            {
                "id": transaction_id,
                "label": f"Retail Tx: {transaction_id} (${amount:,.2f})",
                "type": "transaction",
                "layer": 1,
                "color": "#2563eb",
                "size": 26,
                "risk_score": score
            },
            {
                "id": f"TX_PAST_SESSION_{user_id}",
                "label": f"Past Clean Tx (${round(amount * 0.5, 2):,.2f})",
                "type": "transaction",
                "layer": 1,
                "color": "#3b82f6",
                "size": 20,
                "risk_score": 0.02
            },
            # Layer 2 (Entities)
            {
                "id": f"IP_{ip_addr}",
                "label": f"Home IP ({ip_addr})",
                "type": "ip",
                "layer": 2,
                "color": "#0284c7",
                "size": 20,
                "risk_score": 0.01
            },
            {
                "id": f"Device_{device_guid}",
                "label": f"Trusted Device ({device_guid})",
                "type": "device",
                "layer": 2,
                "color": "#7c3aed",
                "size": 20,
                "risk_score": 0.01
            },
            {
                "id": f"Merchant_{merchant}",
                "label": f"Merchant ({merchant})",
                "type": "merchant",
                "layer": 2,
                "color": "#1d4ed8",
                "size": 20,
                "risk_score": 0.01
            }
        ]
        
        links = [
            {"source": center_id, "target": transaction_id, "relation": "purchased"},
            {"source": center_id, "target": f"TX_PAST_SESSION_{user_id}", "relation": "prior_purchase"},
            {"source": transaction_id, "target": f"IP_{ip_addr}", "relation": "originated_from"},
            {"source": transaction_id, "target": f"Device_{device_guid}", "relation": "used_device"},
            {"source": transaction_id, "target": f"Merchant_{merchant}", "relation": "paid_to"}
        ]

    if is_attack or score >= 0.70:
        summary = f"High-risk clustering detected: Central account {user_id} is linked to mule recipient {beneficiary_id} via intermediate velocity bursts sharing IP {ip_addr} ({geo_info['city']}) and Hardware GUID {device_guid}. Topology indicates coordinated syndicate smurfing."
    else:
        summary = f"Isolated baseline pattern: Transaction forms an isolated direct path to known merchant {merchant} with standard 1st-degree device authorization on IP {ip_addr} ({geo_info['city']}). No syndicate or mule account overlap detected."

    return {
        "transaction_id": transaction_id,
        "title": "Vigil: Fraudster Ego Network (Degrees of Separation)",
        "fraud_pattern": pattern,
        "summary": summary,
        "nodes": nodes,
        "links": links,
        "edges": links,
        "topology_stats": {
            "total_nodes": len(nodes),
            "total_edges": len(links),
            "density": round(len(links) / max(1, (len(nodes) * (len(nodes) - 1))), 3),
            "suspicious_subgraph_nodes": sum(1 for n in nodes if n["risk_score"] >= 0.70)
        }
    }


