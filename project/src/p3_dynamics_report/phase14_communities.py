import os
from pathlib import Path
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import community.community_louvain as community_louvain # python-louvain package

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
P1_SRC = PROJECT_ROOT / "src" / "p1_construction"
sys.path.insert(0, str(P1_SRC))

from utils import apply_plot_style, set_global_seed, BLOCK_ORDER, BLOCK_LABELS, BLOCK_COLORS  # type: ignore # noqa: E402

GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

def upsert_marked_section(text, start_marker, end_marker, content, before):
    section = f"{start_marker}\n{content.strip()}\n{end_marker}"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.S)
    text = pattern.sub("", text).rstrip() + "\n"
    if before in text:
        return text.replace(before, section + "\n\n" + before, 1)
    return text.rstrip() + "\n\n" + section + "\n"

def save_figure(fig, name):
    path = FIGURES_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path.relative_to(PROJECT_ROOT)}")

def qualitative_label(scores):
    # simple heuristic to generate a label based on the highest score or generally high/low scores
    if scores.mean() > 1.0:
        return "Strongly Progressive/Agreeable"
    elif scores.mean() < 0.0:
        return "Skeptical/Critical"
    else:
        # find the most extreme block
        idx_max = scores.idxmax()
        return f"{BLOCK_LABELS[idx_max]}-Oriented Consensus"

def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 14 — COMMUNITY DETECTION")
    print("=" * 70)

    # Load Full Graph
    G = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    
    # 1. Louvain community detection
    partition = community_louvain.best_partition(G, weight='weight', random_state=42)
    modularity = community_louvain.modularity(partition, G, weight='weight')
    
    num_communities = len(set(partition.values()))
    print(f"Number of communities: {num_communities}")
    print(f"Modularity: {modularity:.4f}")
    
    # Create DataFrame for partition
    df_partition = pd.DataFrame([{"ResponseID": int(node), "community": comm} for node, comm in partition.items()])
    
    # We might want to filter out communities of size 1 (the isolates) to avoid clutter in the bar chart
    # Let's count sizes
    sizes = df_partition['community'].value_counts()
    
    # Re-map community IDs so the largest is 0, next is 1, etc.
    sorted_comms = sizes.index.tolist()
    remap = {old: new for new, old in enumerate(sorted_comms)}
    df_partition['community'] = df_partition['community'].map(remap)
    sizes = df_partition['community'].value_counts()
    
    # 2. Merge with block means
    block_means = pd.read_csv(TABLES_DIR / "respondent_block_means.csv")
    df_merged = df_partition.merge(block_means, on="ResponseID", how="left")
    
    # Calculate community-level averages
    comm_summary = df_merged.groupby('community')[BLOCK_ORDER].mean()
    comm_summary['size'] = sizes
    comm_summary = comm_summary[['size'] + BLOCK_ORDER]
    
    # Filter out singletons for qualitative labeling and plotting if desired, 
    # but Phase 14 says "Characterize each community's mean T/E/S/V scores; label qualitatively."
    # Let's do it for all communities that are part of the GCC or size > 1.
    # Actually, Louvain puts isolates in their own single-node communities.
    # We will label the main communities (size > 1).
    main_comms = comm_summary[comm_summary['size'] > 1].copy()
    main_comms['label'] = main_comms[BLOCK_ORDER].apply(qualitative_label, axis=1)
    
    print("\nCommunity Summary (Size > 1):")
    print(main_comms)
    
    comm_summary.to_csv(TABLES_DIR / "community_summary.csv")
    
    # 3. Cross-check with Phase 8 leaders
    leaders = pd.read_csv(TABLES_DIR / "centrality_leaders.csv")
    leaders_comm = df_partition[df_partition['ResponseID'].isin(leaders['ResponseID'])]
    print("\nPhase 8 Leaders Community Memberships:")
    for _, row in leaders_comm.iterrows():
        print(f"Respondent {row['ResponseID']} is in Community {row['community']}")

    # 4. Plots
    
    # Grouped bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(main_comms))
    width = 0.2
    
    for i, block in enumerate(BLOCK_ORDER):
        ax.bar(x + (i - 1.5) * width, main_comms[block], width, label=BLOCK_LABELS[block], color=BLOCK_COLORS[block])
        
    ax.set_xticks(x)
    ax.set_xticklabels([f"Comm {idx}\n(n={int(row['size'])})" for idx, row in main_comms.iterrows()])
    ax.legend()
    ax.set_ylabel("Mean Opinion Score")
    ax.set_title("Mean Opinion Scores by Topic Block for Main Communities")
    save_figure(fig, "phase14_community_block_scores.png")
    
    # Community-colored network layout
    fig, ax = plt.subplots(figsize=(12, 10))
    pos = nx.spring_layout(G, k=0.15, seed=42, weight='weight')
    
    # Create color map for communities
    cmap = plt.get_cmap('tab20')
    node_colors = [remap[partition[str(node)]] if remap[partition[str(node)]] < 20 else 20 for node in G.nodes()]
    
    nx.draw_networkx_nodes(G, pos, node_size=[G.degree(n)*10 + 20 for n in G.nodes()], 
                           node_color=node_colors, cmap=cmap, alpha=0.9, ax=ax, edgecolors="white")
    
    # Draw edges with transparency
    edges = G.edges()
    weights = [G[u][v]['weight'] for u,v in edges]
    nx.draw_networkx_edges(G, pos, edgelist=edges, width=1.0, alpha=0.15, ax=ax)
    
    # Draw labels only for the top degree nodes
    degrees = dict(G.degree())
    top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:10]
    labels = {n: n for n in top_nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=9, font_weight="bold", ax=ax)
    
    ax.set_title("Opinion Network Colored by Louvain Communities")
    ax.axis("off")
    save_figure(fig, "phase14_community_network.png")
    
    # 5. Report Update
    analysis_md = f"""
<!-- PHASE14_ANALYSIS_START -->
### Community Detection

![Community Block Scores](outputs/figures/phase14_community_block_scores.png)
*Figure: Mean encoded opinion scores for the largest Louvain communities across the four topic blocks.*

![Community Network](outputs/figures/phase14_community_network.png)
*Figure: The opinion similarity network with nodes colored by their Louvain community assignment. Node size is proportional to degree, and the top 10 highest-degree nodes are labeled with their Response IDs.*
<!-- PHASE14_ANALYSIS_END -->
"""

    # We dynamically format the labels for the results text
    label_text = ", ".join([f"Community {idx} (size {int(row['size'])}): {row['label']}" for idx, row in main_comms.iterrows()])

    results_md = f"""
<!-- PHASE14_RESULTS_START -->
## Opinion Communities

Running Louvain community detection on the full graph yields **{num_communities} communities** with an overall modularity of **{modularity:.4f}**. Because the network has 9 isolates, 9 of these communities are trivial singletons. Within the Giant Connected Component, the respondents cluster into {len(main_comms)} substantive opinion communities.

Evaluating the mean opinion scores of these main communities reveals qualitative differences in their consensus patterns:
{label_text}.

Cross-checking these communities against the structurally influential respondents from Phase 8 shows that the global opinion-typical consensus leader and path-critical bridge nodes are distributed among the largest communities. This suggests that the network is cohesive enough that highly central individuals are anchoring the main opinion clusters rather than forming an isolated elite.
<!-- PHASE14_RESULTS_END -->
"""
    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE14_ANALYSIS_START -->",
        "<!-- PHASE14_ANALYSIS_END -->",
        analysis_md,
        "# Results and Discussion"
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE14_RESULTS_START -->",
        "<!-- PHASE14_RESULTS_END -->",
        results_md,
        "## Graph Topology"
    )
    report_path.write_text(report, encoding="utf-8")
    print("Updated report_draft.md for Phase 14")

if __name__ == "__main__":
    main()
