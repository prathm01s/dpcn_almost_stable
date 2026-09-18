"""
Phase 4 — Threshold Selection & Adjacency/Graph Construction
=============================================================
1. Threshold sweep (50th-99th percentile) on similarity matrices.
2. Select tau* (knee-point where GCC >= 90%).
3. Build thresholded graphs (Full + 4 blocks) and mutual k-NN (k=8) graph.
4. Save to `graphs/*.graphml`.
5. Plot dual-axis sweep curve and spring layouts of graphs.
6. Update report.
"""

import os
import sys
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    PROCESSED_DATA_DIR, TABLES_DIR, FIGURES_DIR, GRAPHS_DIR, PROJECT_ROOT,
    BLOCK_ORDER, BLOCK_LABELS, apply_plot_style, save_figure, set_global_seed, SEED
)

set_global_seed()
apply_plot_style()

print("=" * 70)
print("PHASE 4 — Threshold Selection & Graph Construction")
print("=" * 70)

# ──────────────────────────────────────────────────────────────
# 1. Load Data
# ──────────────────────────────────────────────────────────────
print("\n[Step 1] Loading similarity matrices and IDs...")
encoded_matrix_path = os.path.join(PROCESSED_DATA_DIR, "encoded_matrix.csv")
df_full = pd.read_csv(encoded_matrix_path)
node_ids = df_full["ResponseID"].astype(str).tolist()
n_nodes = len(node_ids)

sim_cosine_full = np.load(os.path.join(PROJECT_ROOT, "similarity_cosine_full.npy"))

sim_cosine_blocks = {}
for block in BLOCK_ORDER:
    sim_cosine_blocks[block] = np.load(os.path.join(PROJECT_ROOT, f"similarity_cosine_{block}.npy"))

# ──────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────
def run_threshold_sweep(sim_matrix, network_name):
    # Extract off-diagonals
    upper_tri_indices = np.triu_indices(n_nodes, k=1)
    off_diag = sim_matrix[upper_tri_indices]
    
    # 50th to 99th percentile, 2-point steps
    percentiles = np.arange(50, 100, 2)
    taus = np.percentile(off_diag, percentiles)
    
    results = []
    for p, tau in zip(percentiles, taus):
        # Build temp graph
        G_temp = nx.Graph()
        G_temp.add_nodes_from(range(n_nodes))
        
        # Edges
        rows, cols = np.where(sim_matrix >= tau)
        for r, c in zip(rows, cols):
            if r < c: # undirected, avoid self-loops and duplicates
                G_temp.add_edge(r, c)
                
        # Stats
        edges = G_temp.number_of_edges()
        density = nx.density(G_temp)
        components = list(nx.connected_components(G_temp))
        n_components = len(components)
        if n_components > 0:
            gcc_size = max(len(c) for c in components)
        else:
            gcc_size = 0
            
        gcc_pct = (gcc_size / n_nodes) * 100
        mean_degree = np.mean([d for _, d in G_temp.degree()]) if n_nodes > 0 else 0
        
        results.append({
            "network": network_name,
            "percentile": p,
            "tau": tau,
            "edges": edges,
            "density": density,
            "n_components": n_components,
            "gcc_size": gcc_size,
            "gcc_pct": gcc_pct,
            "mean_degree": mean_degree
        })
        
    df_sweep = pd.DataFrame(results)
    
    # Select tau* (highest tau where gcc_pct >= 90%)
    valid_taus = df_sweep[df_sweep['gcc_pct'] >= 90.0]
    if not valid_taus.empty:
        best_row = valid_taus.iloc[-1] # the last one has the highest percentile/tau
    else:
        # Fallback to the maximum GCC if none > 90%
        best_idx = df_sweep['gcc_pct'].idxmax()
        best_row = df_sweep.loc[best_idx]
        
    return df_sweep, best_row['tau'], best_row['percentile']

def build_threshold_graph(sim_matrix, tau, node_ids):
    G = nx.Graph()
    # Add nodes with IDs
    for i, nid in enumerate(node_ids):
        G.add_node(nid, label=nid)
        
    rows, cols = np.where(sim_matrix >= tau)
    for r, c in zip(rows, cols):
        if r < c:
            G.add_edge(node_ids[r], node_ids[c], weight=float(sim_matrix[r, c]))
    return G

def build_mutual_knn_graph(sim_matrix, node_ids, k=8):
    G = nx.Graph()
    for i, nid in enumerate(node_ids):
        G.add_node(nid, label=nid)
        
    # For each node, find top k neighbors (excluding self)
    top_k_neighbors = {}
    for i in range(n_nodes):
        # Sort indices by similarity descending
        sorted_indices = np.argsort(sim_matrix[i])[::-1]
        # Remove self
        sorted_indices = sorted_indices[sorted_indices != i]
        top_k_neighbors[i] = set(sorted_indices[:k])
        
    # Add mutual edges
    for i in range(n_nodes):
        for j in range(i+1, n_nodes):
            if j in top_k_neighbors[i] and i in top_k_neighbors[j]:
                G.add_edge(node_ids[i], node_ids[j], weight=float(sim_matrix[i, j]))
                
    return G

# ──────────────────────────────────────────────────────────────
# 2. Threshold Sweeps & Graph Generation
# ──────────────────────────────────────────────────────────────
print("\n[Step 2] Running threshold sweeps and building graphs...")

sweep_results = []
tau_stars = {}

# Full network
print("  Processing: Full Network")
df_full_sweep, tau_star_full, pct_full = run_threshold_sweep(sim_cosine_full, "Full")
sweep_results.append(df_full_sweep)
tau_stars["Full"] = tau_star_full
print(f"    Selected tau* = {tau_star_full:.4f} (at {pct_full}th percentile)")

G_full = build_threshold_graph(sim_cosine_full, tau_star_full, node_ids)
nx.write_graphml(G_full, os.path.join(GRAPHS_DIR, "G_full.graphml"))

# k-NN network
G_knn = build_mutual_knn_graph(sim_cosine_full, node_ids, k=8)
nx.write_graphml(G_knn, os.path.join(GRAPHS_DIR, "G_knn.graphml"))

# Block networks
G_blocks = {}
for block in BLOCK_ORDER:
    print(f"  Processing: Block {block}")
    df_sweep, t_star, pct = run_threshold_sweep(sim_cosine_blocks[block], block)
    sweep_results.append(df_sweep)
    tau_stars[block] = t_star
    print(f"    Selected tau* = {t_star:.4f} (at {pct}th percentile)")
    
    G_b = build_threshold_graph(sim_cosine_blocks[block], t_star, node_ids)
    G_blocks[block] = G_b
    nx.write_graphml(G_b, os.path.join(GRAPHS_DIR, f"G_{block}.graphml"))
    
# Combine sweep results and save
df_all_sweeps = pd.concat(sweep_results, ignore_index=True)
df_all_sweeps.to_csv(os.path.join(TABLES_DIR, "threshold_sweep.csv"), index=False)
print("  → Saved threshold_sweep.csv and all .graphml files")

# ──────────────────────────────────────────────────────────────
# 3. Plots
# ──────────────────────────────────────────────────────────────
print("\n[Step 3] Generating visualizations...")

# Plot A: Dual axis sweep curve for Full Network
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Threshold (tau)')
ax1.set_ylabel('Density', color=color)
ax1.plot(df_full_sweep['tau'], df_full_sweep['density'], color=color, marker='o')
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('Giant Component Size (%)', color=color)
ax2.plot(df_full_sweep['tau'], df_full_sweep['gcc_pct'], color=color, marker='s')
ax2.tick_params(axis='y', labelcolor=color)

# Mark the chosen tau*
ax1.axvline(tau_star_full, color='black', linestyle='--', alpha=0.7, label=f'Chosen tau* = {tau_star_full:.3f}')
fig.legend(loc="upper right", bbox_to_anchor=(0.85, 0.85))

plt.title("Threshold Sweep for Full Opinion Network")
fig.tight_layout()
save_figure(fig, "phase4_threshold_sweep.png")
plt.close(fig)

# Plot B: Spring Layouts (Basic unstyled for P2 to sanity-check)
# Use a fixed seed for layouts
layout_seed = SEED

fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()

# Helper for drawing
def draw_basic_graph(G, ax, title):
    pos = nx.spring_layout(G, seed=layout_seed, k=0.15)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=20, node_color="#4C72B0")
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.3, width=0.5)
    ax.set_title(title, fontsize=12)
    ax.axis('off')

draw_basic_graph(G_full, axes[0], f"Full Network (tau={tau_stars['Full']:.3f})")
draw_basic_graph(G_blocks['T'], axes[1], f"Technology Block (tau={tau_stars['T']:.3f})")
draw_basic_graph(G_blocks['E'], axes[2], f"Education Block (tau={tau_stars['E']:.3f})")
draw_basic_graph(G_blocks['S'], axes[3], f"Ethics/Society Block (tau={tau_stars['S']:.3f})")
draw_basic_graph(G_blocks['V'], axes[4], f"Environment Block (tau={tau_stars['V']:.3f})")
draw_basic_graph(G_knn, axes[5], "Alternative: Mutual k-NN (k=8)")

plt.tight_layout()
save_figure(fig, "phase4_graph_layouts.png")
plt.close(fig)

# ──────────────────────────────────────────────────────────────
# 4. Update Markdown Files
# ──────────────────────────────────────────────────────────────
print("\n[Step 4] Updating report_draft.md and results_summary.md...")

report_path = os.path.join(PROJECT_ROOT, "report_draft.md")
with open(report_path, "r", encoding="utf-8") as f:
    report_content = f.read()

pipeline_update = f"""
## Graph Construction

To binarize the dense similarity matrix into a network structure, we performed a threshold sweep across the 50th to 99th percentiles of pairwise similarities. Our objective was to identify the sparsest structure (the "knee-point") that still maintains a cohesive global topology, defined as a Giant Connected Component (GCC) retaining at least 90% of the respondents.

The selected thresholds ($\\tau^*$) are:
- **Full Network**: {tau_stars['Full']:.3f}
- **Technology Block (T)**: {tau_stars['T']:.3f}
- **Education Block (E)**: {tau_stars['E']:.3f}
- **Ethics/Society Block (S)**: {tau_stars['S']:.3f}
- **Environment Block (V)**: {tau_stars['V']:.3f}

Edges with similarities below these thresholds were discarded, while remaining edges form the unweighted topology. The original similarity values are preserved as edge weights. Additionally, an alternative mutual k-Nearest Neighbor graph (k=8) was constructed as a robust topological baseline.

![Threshold Sweep Selection](outputs/figures/phase4_threshold_sweep.png)
*Figure: Dual-axis plot of the threshold sweep for the full network, showing the tradeoff between density and Giant Component size. The selected threshold $\\tau^*$ is marked by the dashed line.*
"""

report_content = report_content.replace(
    "# Analysis and Visualizations", 
    pipeline_update.strip() + "\n\n# Analysis and Visualizations"
)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_content)

# Update Results Summary
summary_path = os.path.join(PROJECT_ROOT, "results_summary.md")
with open(summary_path, "a", encoding="utf-8") as f:
    f.write("\n### Phase 4: Graph Construction\n")
    f.write(f"- **Thresholds**: Applied knee-point thresholding (GCC >= 90%). Full network $\\tau^*$ = {tau_stars['Full']:.3f}.\n")
    f.write("- **Graphs Created**: 5 primary threshold graphs (Full, T, E, S, V) and 1 alternative (mutual k-NN, k=8).\n")

print("  → Updated report_draft.md and results_summary.md")

print(f"\n{'=' * 70}")
print("PHASE 4 COMPLETE")
print(f"{'=' * 70}")
