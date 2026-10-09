import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# 1. Build Multi-Layer Fraud Network (Degrees of Separation)
G = nx.Graph()

fraudster = "Fraudster_ACC_001"
G.add_node(fraudster, layer=0, type="Fraudster")

# Ring 1: Attacks / Transactions performed by the fraudster
attacks = ["tx_velocity_burst", "tx_card_testing", "tx_rapid_drain", "tx_mule_transfer"]
for i, tx in enumerate(attacks):
    G.add_node(tx, layer=1, type="Attack")
    G.add_edge(fraudster, tx, relation="executed")

# Ring 2: Targeted Merchants and Infrastructure connected to the attacks
targets = {
    "tx_velocity_burst": ["Merchant_A", "IP_192.168.1.50"],
    "tx_card_testing": ["Merchant_B", "Merchant_C", "Device_X"],
    "tx_rapid_drain": ["Merchant_A", "Device_Y"],
    "tx_mule_transfer": ["Merchant_D", "IP_45.176.12.88"]
}

for tx, endpoints in targets.items():
    for ep in endpoints:
        G.add_node(ep, layer=2, type="Target/Infra")
        G.add_edge(tx, ep, relation="targeted")

# 2. Compute Concentric Shell Layout (True Degrees of Separation)
# Layer 0 in center, Layer 1 in inner ring, Layer 2 in outer ring
layer_0 = [n for n, d in G.nodes(data=True) if d["layer"] == 0]
layer_1 = [n for n, d in G.nodes(data=True) if d["layer"] == 1]
layer_2 = [n for n, d in G.nodes(data=True) if d["layer"] == 2]

pos = nx.shell_layout(G, nlist=[layer_0, layer_1, layer_2])

# 3. Extract Coordinates for Plotly
edge_x, edge_y = [], []
for edge in G.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=1.5, color="#888"),
    hoverinfo="none",
    mode="lines"
)

node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
for node in G.nodes():
    x, y = pos[node]
    node_x.append(x)
    node_y.append(y)
    node_text.append(node)
    
    node_data = G.nodes[node]
    if node_data["layer"] == 0:
        node_color.append("#111111")  # Center: Fraudster (Dark Black/Core)
        node_size.append(35)
    elif node_data["layer"] == 1:
        node_color.append("#2ca02c")  # Ring 1: Attacks (Green)
        node_size.append(25)
    else:
        node_color.append("#1f77b4")  # Ring 2: Targets/Infra (Blue)
        node_size.append(20)

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode="markers+text",
    text=node_text,
    textposition="top center",
    hoverinfo="text",
    marker=dict(
        showscale=False,
        color=node_color,
        size=node_size,
        line=dict(width=2, color="#fff")
    )
)

# 4. Render Concentric Branching Figure
fig = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title="Vigil: Fraudster Ego Network (Degrees of Separation)",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=20, r=20, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
)

print("Opening concentric fraud network in browser...")
fig.show()
