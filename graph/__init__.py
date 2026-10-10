"""
FRAUD-RING RADAR Graph Module (backend/graph/)
Provides NetworkX heterogeneous fraud graph construction, serialization,
analytics, ego network visualization, and temporal IP map tracking.
"""

from .build_graph import (
    build_fraud_graph,
    save_fraud_graph,
    load_fraud_graph
)
from .graph_queries import (
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
from .graph_analytics import (
    calculate_graph_statistics
)
from .ego_network import (
    generate_ego_network
)
from .temporal_map import (
    generate_temporal_map
)

__all__ = [
    'build_fraud_graph',
    'save_fraud_graph',
    'load_fraud_graph',
    'get_account_neighbors',
    'get_shared_devices',
    'get_shared_ips',
    'get_connected_component',
    'get_account_fan_in',
    'get_account_fan_out',
    'get_transfer_neighbors',
    'get_money_flow_path',
    'get_accounts_sharing_device',
    'get_accounts_sharing_ip',
    'calculate_graph_statistics',
    'generate_ego_network',
    'generate_temporal_map'
]
