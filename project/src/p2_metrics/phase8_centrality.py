"""Phase 8: full centrality suite for the opinion-similarity network."""

from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
P1_SRC = PROJECT_ROOT / "src" / "p1_construction"
sys.path.insert(0, str(P1_SRC))

from utils import apply_plot_style, set_global_seed  # noqa: E402


GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
CENTRALITY_COLUMNS = [
    "degree_centrality",
    "closeness_centrality",
    "betweenness_centrality",
    "eigenvector_centrality",
    "pagerank",
    "harmonic_centrality",
]
DISPLAY_NAMES = {
    "degree_centrality": "Degree",
    "closeness_centrality": "Closeness",
    "betweenness_centrality": "Betweenness",
    "eigenvector_centrality": "Eigenvector",
    "pagerank": "PageRank",
    "harmonic_centrality": "Harmonic",
}


def upsert_marked_section(text, start_marker, end_marker, content, before):
    """Replace a generated Markdown section, or insert it before a stable heading."""
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


def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 8 — FULL CENTRALITY SUITE")
    print("=" * 70)

    full_graph = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    giant_graph = nx.read_graphml(GRAPHS_DIR / "G_giant.graphml")
    nodes = sorted(full_graph.nodes(), key=int)
    giant_nodes = set(giant_graph.nodes())
    print(
        f"Full graph: {full_graph.number_of_nodes()} nodes, "
        f"{full_graph.number_of_edges()} edges; GCC: {giant_graph.number_of_nodes()} nodes"
    )

    # Metrics defined on the full graph.
    raw_degree = dict(full_graph.degree())
    weighted_degree = dict(full_graph.degree(weight="weight"))
    degree = nx.degree_centrality(full_graph)
    eigenvector = nx.eigenvector_centrality(
        full_graph, max_iter=5000, tol=1e-10, weight="weight"
    )
    pagerank = nx.pagerank(full_graph, alpha=0.85, weight="weight")
    harmonic = nx.harmonic_centrality(full_graph)

    # Path centralities are computed only where paths are defined. Isolates receive
    # zero when the GCC results are merged back into the 91-row handoff table.
    closeness_gcc = nx.closeness_centrality(giant_graph)
    betweenness_gcc = nx.betweenness_centrality(
        giant_graph, normalized=True, weight=None
    )
    closeness = {node: closeness_gcc.get(node, 0.0) for node in nodes}
    betweenness = {node: betweenness_gcc.get(node, 0.0) for node in nodes}

    metrics = pd.DataFrame(
        {
            "ResponseID": [int(node) for node in nodes],
            "in_giant_component": [node in giant_nodes for node in nodes],
            "degree": [raw_degree[node] for node in nodes],
            "weighted_degree": [weighted_degree[node] for node in nodes],
            "degree_centrality": [degree[node] for node in nodes],
            "closeness_centrality": [closeness[node] for node in nodes],
            "betweenness_centrality": [betweenness[node] for node in nodes],
            "eigenvector_centrality": [eigenvector[node] for node in nodes],
            "pagerank": [pagerank[node] for node in nodes],
            "harmonic_centrality": [harmonic[node] for node in nodes],
        }
    )

    clustering = pd.read_csv(TABLES_DIR / "clustering_coefficients.csv")
    block_means = pd.read_csv(TABLES_DIR / "respondent_block_means.csv")
    clustering["ResponseID"] = clustering["ResponseID"].astype(int)
    block_means["ResponseID"] = block_means["ResponseID"].astype(int)
    block_means["opinion_mean"] = block_means[["T", "E", "S", "V"]].mean(axis=1)
    metrics = metrics.merge(
        clustering[
            ["ResponseID", "clustering_unweighted", "clustering_weighted"]
        ],
        on="ResponseID",
        how="left",
        validate="one_to_one",
    ).merge(block_means, on="ResponseID", how="left", validate="one_to_one")

    if metrics.isna().any().any() or len(metrics) != full_graph.number_of_nodes():
        raise ValueError("Phase 8 merge did not produce one complete row per graph node")

    metrics.to_csv(TABLES_DIR / "node_metrics.csv", index=False)
    correlation = metrics[CENTRALITY_COLUMNS].corr(method="spearman")
    correlation.to_csv(TABLES_DIR / "centrality_spearman_correlation.csv")

    # Consensus typicality uses ranks from the three handoff-designated measures.
    typical_measures = ["degree_centrality", "eigenvector_centrality", "pagerank"]
    rank_columns = []
    for column in typical_measures:
        rank_column = f"{column}_rank"
        metrics[rank_column] = metrics[column].rank(method="min", ascending=False)
        rank_columns.append(rank_column)
    metrics["typicality_mean_rank"] = metrics[rank_columns].mean(axis=1)
    typical_row = metrics.sort_values(
        ["typicality_mean_rank", "degree_centrality"], ascending=[True, False]
    ).iloc[0]
    bridge_row = metrics.sort_values(
        ["betweenness_centrality", "degree_centrality"], ascending=False
    ).iloc[0]
    maximum_degree = metrics["degree_centrality"].max()
    degree_leader_ids = metrics.loc[
        np.isclose(metrics["degree_centrality"], maximum_degree), "ResponseID"
    ].astype(int).tolist()
    eigenvector_row = metrics.loc[metrics["eigenvector_centrality"].idxmax()]
    pagerank_row = metrics.loc[metrics["pagerank"].idxmax()]

    leaders = pd.DataFrame(
        [
            {
                "role": "opinion_typical_consensus",
                "ResponseID": int(typical_row["ResponseID"]),
                "primary_score": typical_row["typicality_mean_rank"],
                "degree_centrality": typical_row["degree_centrality"],
                "eigenvector_centrality": typical_row["eigenvector_centrality"],
                "pagerank": typical_row["pagerank"],
                "betweenness_centrality": typical_row["betweenness_centrality"],
            },
            {
                "role": "path_critical_bridge",
                "ResponseID": int(bridge_row["ResponseID"]),
                "primary_score": bridge_row["betweenness_centrality"],
                "degree_centrality": bridge_row["degree_centrality"],
                "eigenvector_centrality": bridge_row["eigenvector_centrality"],
                "pagerank": bridge_row["pagerank"],
                "betweenness_centrality": bridge_row["betweenness_centrality"],
            },
        ]
    )
    leaders.to_csv(TABLES_DIR / "centrality_leaders.csv", index=False)

    ranking_frames = []
    for column in CENTRALITY_COLUMNS:
        top = metrics.nlargest(10, column)[["ResponseID", column]].copy()
        top.insert(0, "metric", column)
        all_ranks = metrics[column].rank(method="min", ascending=False).astype(int)
        top.insert(2, "rank", all_ranks.loc[top.index])
        top = top.rename(columns={column: "score"})
        ranking_frames.append(top)
    pd.concat(ranking_frames, ignore_index=True).to_csv(
        TABLES_DIR / "centrality_top10.csv", index=False
    )

    # Spearman heatmap.
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(correlation.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    labels = [DISPLAY_NAMES[column] for column in CENTRALITY_COLUMNS]
    ax.set_xticks(range(len(labels)), labels=labels, rotation=40, ha="right")
    ax.set_yticks(range(len(labels)), labels=labels)
    for row in range(len(labels)):
        for col in range(len(labels)):
            value = correlation.iloc[row, col]
            ax.text(
                col,
                row,
                f"{value:.2f}",
                ha="center",
                va="center",
                color="white" if abs(value) > 0.55 else "black",
                fontsize=9,
            )
    ax.set_title("Spearman Correlation Between Centrality Measures")
    fig.colorbar(image, ax=ax, label="Spearman rho", shrink=0.82)
    fig.tight_layout()
    save_figure(fig, "phase8_centrality_correlation_heatmap.png")

    # Matplotlib pairplot, colored by each respondent's overall block-mean opinion.
    count = len(CENTRALITY_COLUMNS)
    fig, axes = plt.subplots(count, count, figsize=(16, 16))
    color_values = metrics["opinion_mean"].to_numpy()
    norm = plt.Normalize(color_values.min(), color_values.max())
    cmap = plt.get_cmap("viridis")
    for row, y_column in enumerate(CENTRALITY_COLUMNS):
        for col, x_column in enumerate(CENTRALITY_COLUMNS):
            ax = axes[row, col]
            if row == col:
                ax.hist(metrics[x_column], bins=16, color="#4C72B0", alpha=0.85)
            else:
                ax.scatter(
                    metrics[x_column],
                    metrics[y_column],
                    c=color_values,
                    cmap=cmap,
                    norm=norm,
                    s=16,
                    alpha=0.72,
                    edgecolors="none",
                )
            if row == count - 1:
                ax.set_xlabel(DISPLAY_NAMES[x_column], fontsize=9)
            else:
                ax.set_xticklabels([])
            if col == 0:
                ax.set_ylabel(DISPLAY_NAMES[y_column], fontsize=9)
            else:
                ax.set_yticklabels([])
            ax.tick_params(labelsize=7)
    scalar = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    scalar.set_array([])
    fig.colorbar(
        scalar,
        ax=axes,
        label="Mean encoded opinion across T/E/S/V",
        fraction=0.018,
        pad=0.015,
    )
    fig.suptitle("Pairwise Centrality Relationships Colored by Mean Opinion", y=0.995)
    fig.subplots_adjust(left=0.07, right=0.91, bottom=0.06, top=0.965, wspace=0.12, hspace=0.12)
    save_figure(fig, "phase8_centrality_pairplot.png")

    # Strongest and weakest off-diagonal relationships for the interpretation.
    pairs = []
    for row in range(len(CENTRALITY_COLUMNS)):
        for col in range(row + 1, len(CENTRALITY_COLUMNS)):
            pairs.append(
                (
                    correlation.iloc[row, col],
                    CENTRALITY_COLUMNS[row],
                    CENTRALITY_COLUMNS[col],
                )
            )
    strongest = max(pairs, key=lambda item: item[0])
    weakest = min(pairs, key=lambda item: item[0])

    analysis_markdown = f"""
### Centrality Structure

![Centrality correlation heatmap](outputs/figures/phase8_centrality_correlation_heatmap.png)
*Figure: Spearman rank correlations among the six Phase 8 centralities. Path-based closeness and betweenness are computed on the 82-node GCC and assigned zero for the nine isolates when merged into the full 91-row table.*

![Centrality pairplot](outputs/figures/phase8_centrality_pairplot.png)
*Figure: Pairwise relationships among the six centralities. Point color is each respondent's mean encoded opinion across the Technology, Education, Ethics/Society, and Environment block means; color is contextual and is not used to calculate centrality.*
"""
    results_markdown = f"""
## Centrality and Influential Respondents

Respondent **{int(typical_row['ResponseID'])}** is the most consistently opinion-typical node, having the best mean rank across degree centrality, weighted eigenvector centrality, and weighted PageRank (degree centrality = {typical_row['degree_centrality']:.3f}, eigenvector = {typical_row['eigenvector_centrality']:.3f}, PageRank = {typical_row['pagerank']:.4f}). This respondent is strongly embedded in the dense similarity core under both direct-neighbor and recursive-importance definitions.

By individual measure, respondents **{' and '.join(map(str, degree_leader_ids))}** tie for the highest degree centrality ({maximum_degree:.3f}), respondent **{int(eigenvector_row['ResponseID'])}** has the highest weighted eigenvector centrality ({eigenvector_row['eigenvector_centrality']:.3f}), and respondent **{int(pagerank_row['ResponseID'])}** has the highest weighted PageRank ({pagerank_row['pagerank']:.4f}). The consensus designation above resolves these slightly different rankings rather than treating any one measure as definitive.

Respondent **{int(bridge_row['ResponseID'])}** has the highest normalized betweenness centrality ({bridge_row['betweenness_centrality']:.4f}) and is therefore the strongest candidate for the most path-critical bridge in the GCC. Betweenness measures shortest-path brokerage; it does not by itself imply causal influence over opinions.

The closest agreement is between **{DISPLAY_NAMES[strongest[1]]}** and **{DISPLAY_NAMES[strongest[2]]}** ($\\rho={strongest[0]:.3f}$). The weakest association is between **{DISPLAY_NAMES[weakest[1]]}** and **{DISPLAY_NAMES[weakest[2]]}** ($\\rho={weakest[0]:.3f}$). Measures based on neighbor volume or recursive prestige tend to agree because the graph has a dense GCC, whereas betweenness captures the distinct role of lying on shortest paths.
"""

    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE8_ANALYSIS_START -->",
        "<!-- PHASE8_ANALYSIS_END -->",
        analysis_markdown,
        "# Results and Discussion",
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE8_RESULTS_START -->",
        "<!-- PHASE8_RESULTS_END -->",
        results_markdown,
        "## Graph Topology",
    )
    report_path.write_text(report, encoding="utf-8")

    summary_markdown = f"""
### Phase 8: Full Centrality Suite
- **Opinion-typical consensus leader**: Respondent {int(typical_row['ResponseID'])}, selected by mean rank across degree, weighted eigenvector, and weighted PageRank.
- **Individual leaders**: Degree = respondents {' and '.join(map(str, degree_leader_ids))} (tie); weighted eigenvector = respondent {int(eigenvector_row['ResponseID'])}; weighted PageRank = respondent {int(pagerank_row['ResponseID'])}.
- **Path-critical bridge**: Respondent {int(bridge_row['ResponseID'])}, normalized betweenness = {bridge_row['betweenness_centrality']:.4f}.
- **Strongest centrality agreement**: {DISPLAY_NAMES[strongest[1]]} vs. {DISPLAY_NAMES[strongest[2]]}, Spearman rho = {strongest[0]:.3f}.
- **Weakest centrality agreement**: {DISPLAY_NAMES[weakest[1]]} vs. {DISPLAY_NAMES[weakest[2]]}, Spearman rho = {weakest[0]:.3f}.
"""
    summary_path = PROJECT_ROOT / "results_summary.md"
    summary = summary_path.read_text(encoding="utf-8")
    summary = upsert_marked_section(
        summary,
        "<!-- PHASE8_SUMMARY_START -->",
        "<!-- PHASE8_SUMMARY_END -->",
        summary_markdown,
        "### Phase 9",
    )
    summary_path.write_text(summary, encoding="utf-8")

    print(f"Opinion-typical consensus leader: {int(typical_row['ResponseID'])}")
    print(
        f"Path-critical bridge: {int(bridge_row['ResponseID'])} "
        f"(betweenness={bridge_row['betweenness_centrality']:.4f})"
    )
    print(
        f"Strongest rho: {DISPLAY_NAMES[strongest[1]]} vs "
        f"{DISPLAY_NAMES[strongest[2]]} = {strongest[0]:.3f}"
    )
    print(
        f"Weakest rho: {DISPLAY_NAMES[weakest[1]]} vs "
        f"{DISPLAY_NAMES[weakest[2]]} = {weakest[0]:.3f}"
    )
    print("PHASE 8 COMPLETE")


if __name__ == "__main__":
    main()
