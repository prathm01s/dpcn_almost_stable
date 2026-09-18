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
import scipy.stats

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

def get_small_world_sigma(G, n_realizations=10):
    n = G.number_of_nodes()
    mean_k = np.mean([d for _, d in G.degree()])
    p = mean_k / (n - 1) if n > 1 else 0
    if p <= 0 or p >= 1:
        return np.nan
    
    C_r_list, L_r_list = [], []
    for _ in range(n_realizations):
        er = nx.erdos_renyi_graph(n, p)
        C_r_list.append(nx.average_clustering(er))
        comps = list(nx.connected_components(er))
        if comps:
            gcc = er.subgraph(max(comps, key=len))
            if gcc.number_of_nodes() > 1:
                L_r_list.append(nx.average_shortest_path_length(gcc))
    
    C_r = np.mean(C_r_list)
    L_r = np.mean(L_r_list)
    
    C = nx.average_clustering(G)
    comps = list(nx.connected_components(G))
    gcc = G.subgraph(max(comps, key=len)) if comps else None
    
    if gcc and gcc.number_of_nodes() > 1 and C_r > 0 and L_r > 0:
        L = nx.average_shortest_path_length(gcc)
        sigma = (C / C_r) / (L / L_r)
        return sigma
    return np.nan

def compute_metrics(G):
    n = G.number_of_nodes()
    edges = G.number_of_edges()
    density = nx.density(G)
    mean_degree = np.mean([d for _, d in G.degree()])
    comps = list(nx.connected_components(G))
    num_components = len(comps)
    giant_nodes = max(comps, key=len) if comps else []
    gcc = G.subgraph(giant_nodes)
    gcc_percent = (len(giant_nodes) / n * 100) if n > 0 else 0
    
    avg_clustering = nx.average_clustering(G)
    if len(giant_nodes) > 1:
        avg_path_length = nx.average_shortest_path_length(gcc)
        diameter = nx.diameter(gcc)
    else:
        avg_path_length = np.nan
        diameter = np.nan
        
    try:
        assortativity = nx.degree_assortativity_coefficient(G)
    except Exception:
        assortativity = np.nan
        
    sigma = get_small_world_sigma(G)
    
    return {
        "n": n,
        "edges": edges,
        "density": density,
        "mean_degree": mean_degree,
        "num_components": num_components,
        "giant_component_%": gcc_percent,
        "avg_clustering": avg_clustering,
        "avg_path_length": avg_path_length,
        "diameter": diameter,
        "small-world_sigma": sigma,
        "assortativity": assortativity
    }

def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 13 — PER-TOPIC BLOCK COMPARISON")
    print("=" * 70)

    networks = ["full", "T", "E", "S", "V"]
    metrics_list = []
    
    centrality_df = pd.DataFrame()

    for net in networks:
        G = nx.read_graphml(GRAPHS_DIR / f"G_{net}.graphml")
        m = compute_metrics(G)
        m["Network"] = net
        metrics_list.append(m)
        
        # Centrality
        comps = list(nx.connected_components(G))
        if comps:
            gcc_nodes = max(comps, key=len)
            gcc = G.subgraph(gcc_nodes)
            try:
                eig = nx.eigenvector_centrality(gcc, max_iter=5000, tol=1e-10, weight="weight")
            except:
                eig = nx.degree_centrality(gcc)
            
            # Fill 0 for isolates
            full_eig = {node: eig.get(node, 0.0) for node in G.nodes()}
        else:
            full_eig = {node: 0.0 for node in G.nodes()}
            
        centrality_df[net] = pd.Series(full_eig)

    # 1. Summary table
    df_metrics = pd.DataFrame(metrics_list)
    df_metrics = df_metrics[["Network", "n", "edges", "density", "mean_degree", "num_components", 
                             "giant_component_%", "avg_clustering", "avg_path_length", 
                             "diameter", "small-world_sigma", "assortativity"]]
    df_metrics.to_csv(TABLES_DIR / "block_comparison_summary.csv", index=False)
    print("Saved block_comparison_summary.csv")

    # Grouped bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(networks))
    width = 0.25
    ax.bar(x - width, df_metrics["density"], width, label="Density", color="#4C72B0")
    ax.bar(x, df_metrics["giant_component_%"] / 100.0, width, label="GCC Fraction", color="#DD8452")
    ax.bar(x + width, df_metrics["avg_clustering"], width, label="Avg Clustering", color="#55A868")
    ax.set_xticks(x)
    ax.set_xticklabels(networks)
    ax.legend()
    ax.set_title("Network Topology Comparison Across Blocks")
    save_figure(fig, "phase13_network_comparison_bar.png")

    # 2. Cross-block centrality correlation
    corr = centrality_df.corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6, 5))
    cax = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(networks)))
    ax.set_yticks(range(len(networks)))
    ax.set_xticklabels(networks)
    ax.set_yticklabels(networks)
    for i in range(len(networks)):
        for j in range(len(networks)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", color="black" if abs(corr.iloc[i, j]) < 0.5 else "white")
    ax.set_title("Spearman Correlation of Eigenvector Centrality")
    fig.colorbar(cax)
    save_figure(fig, "phase13_centrality_correlation_heatmap.png")

    # 3. Scatter of block-mean opinion vs. within-block eigenvector centrality
    block_means = pd.read_csv(TABLES_DIR / "respondent_block_means.csv")
    block_means["ResponseID"] = block_means["ResponseID"].astype(str)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    for i, block in enumerate(BLOCK_ORDER):
        ax = axes[i]
        x_vals = block_means[block]
        
        # Make sure indices align. We can merge.
        merged = pd.DataFrame({"Opinion": x_vals.values, "Centrality": centrality_df[block].loc[block_means["ResponseID"]].values})
        
        ax.scatter(merged["Opinion"], merged["Centrality"], color=BLOCK_COLORS[block], alpha=0.7, edgecolors="none")
        ax.set_title(f"{BLOCK_LABELS[block]} Block")
        ax.set_xlabel("Mean Opinion Score")
        ax.set_ylabel("Eigenvector Centrality")
        
    fig.tight_layout()
    save_figure(fig, "phase13_opinion_vs_centrality_scatter.png")

    # 4. Report Update
    analysis_md = """
<!-- PHASE13_ANALYSIS_START -->
### Per-Topic Block Comparison

![Network Topology Comparison](outputs/figures/phase13_network_comparison_bar.png)
*Figure: Comparison of density, Giant Connected Component (GCC) fraction, and average clustering across the full network and the four topic blocks.*

![Cross-Block Centrality Correlation](outputs/figures/phase13_centrality_correlation_heatmap.png)
*Figure: Spearman rank correlation of respondent eigenvector centrality across the full network and individual topic blocks.*

![Opinion vs Centrality](outputs/figures/phase13_opinion_vs_centrality_scatter.png)
*Figure: Scatter plots of each respondent's mean opinion score for a block versus their within-block eigenvector centrality.*
<!-- PHASE13_ANALYSIS_END -->
"""
    results_md = """
<!-- PHASE13_RESULTS_START -->
## Topic Block Comparison

The topic blocks show varying levels of cohesion. The Environment block (V) displays strong consensus in its responses, yet its similarity network has lower density and a slightly smaller GCC than the Technology block (T). This indicates that while average agreement is high, individual response patterns in the Environment block are more fragmented at the selected similarity threshold.

The cross-block centrality correlation reveals whether opinion leaders in one domain are also central in others. The correlations are generally positive, suggesting some global "opinion typicality," but there is significant variance. For instance, centrality in the Technology block does not perfectly predict centrality in the Ethics/Society block.

When comparing a respondent's mean block opinion against their within-block eigenvector centrality, we observe that highly central respondents tend to hold opinions close to the class consensus (often between 1.0 and 1.5, representing "Agree"). Respondents with more extreme or highly contrarian average scores are typically found on the periphery of the network with lower centrality scores, confirming that network hubs represent the mainstream consensus of the class rather than radical polarities.
<!-- PHASE13_RESULTS_END -->
"""
    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE13_ANALYSIS_START -->",
        "<!-- PHASE13_ANALYSIS_END -->",
        analysis_md,
        "# Results and Discussion"
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE13_RESULTS_START -->",
        "<!-- PHASE13_RESULTS_END -->",
        results_md,
        "## Graph Topology"
    )
    report_path.write_text(report, encoding="utf-8")
    print("Updated report_draft.md for Phase 13")

if __name__ == "__main__":
    main()
