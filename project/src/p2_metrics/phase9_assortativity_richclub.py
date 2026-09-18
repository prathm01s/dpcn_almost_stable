"""Phase 9: degree mixing, nearest-neighbor degree, and rich-club analysis."""

from pathlib import Path
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
P1_SRC = PROJECT_ROOT / "src" / "p1_construction"
sys.path.insert(0, str(P1_SRC))

from utils import SEED, apply_plot_style, set_global_seed  # noqa: E402


GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
NULL_REALIZATIONS = 30
SWAPS_PER_EDGE = 2


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


def rich_club_profile(graph, thresholds, degree_by_node=None):
    """Return unweighted rich-club density for nodes with degree strictly above k."""
    degree_by_node = degree_by_node or dict(graph.degree())
    values = []
    counts = []
    for threshold in thresholds:
        rich_nodes = [
            node for node, degree in degree_by_node.items() if degree > threshold
        ]
        node_count = len(rich_nodes)
        counts.append(node_count)
        if node_count < 2:
            values.append(np.nan)
            continue
        edge_count = graph.subgraph(rich_nodes).number_of_edges()
        values.append(2 * edge_count / (node_count * (node_count - 1)))
    return np.asarray(values, dtype=float), np.asarray(counts, dtype=int)


def degree_preserving_null(graph, seed):
    """Generate a simple degree-preserving null using successful double-edge swaps."""
    null_graph = nx.Graph()
    null_graph.add_nodes_from(graph.nodes())
    null_graph.add_edges_from(graph.edges())
    requested_swaps = SWAPS_PER_EDGE * graph.number_of_edges()
    try:
        nx.double_edge_swap(
            null_graph,
            nswap=requested_swaps,
            max_tries=300 * graph.number_of_edges(),
            seed=seed,
        )
        completed_swaps = requested_swaps
    except nx.NetworkXAlgorithmError:
        # Dense graphs admit fewer valid swaps. Retry from the observed graph at a
        # still-substantial half-edge-count target instead of using a partial run.
        null_graph = nx.Graph()
        null_graph.add_nodes_from(graph.nodes())
        null_graph.add_edges_from(graph.edges())
        completed_swaps = max(1, requested_swaps // 2)
        nx.double_edge_swap(
            null_graph,
            nswap=completed_swaps,
            max_tries=300 * graph.number_of_edges(),
            seed=seed,
        )
    return null_graph, completed_swaps


def format_thresholds(values):
    values = list(map(int, values))
    if not values:
        return "none"
    if len(values) <= 6:
        return ", ".join(map(str, values))
    return f"{values[0]}–{values[-1]} ({len(values)} tested thresholds)"


def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 9 — ASSORTATIVITY, DEGREE CORRELATION, AND RICH CLUB")
    print("=" * 70)

    graph = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    nodes = sorted(graph.nodes(), key=int)
    degrees = dict(graph.degree())

    assortativity = nx.degree_assortativity_coefficient(graph)
    neighbor_degree = nx.average_neighbor_degree(graph)
    node_table = pd.DataFrame(
        {
            "ResponseID": [int(node) for node in nodes],
            "degree": [degrees[node] for node in nodes],
            "average_neighbor_degree": [neighbor_degree[node] for node in nodes],
            "is_isolate": [degrees[node] == 0 for node in nodes],
        }
    )
    node_table.to_csv(TABLES_DIR / "nearest_neighbor_degree_by_node.csv", index=False)

    knn_by_degree = (
        node_table.groupby("degree", as_index=False)
        .agg(
            mean_neighbor_degree=("average_neighbor_degree", "mean"),
            std_neighbor_degree=("average_neighbor_degree", "std"),
            node_count=("ResponseID", "count"),
        )
        .fillna({"std_neighbor_degree": 0.0})
    )
    knn_by_degree.to_csv(TABLES_DIR / "knn_by_degree.csv", index=False)

    non_isolates = node_table.loc[~node_table["is_isolate"]]
    knn_rho, knn_p = spearmanr(
        non_isolates["degree"], non_isolates["average_neighbor_degree"]
    )

    # Rich-club coefficients relative to degree-preserving randomized graphs.
    max_degree = max(degrees.values())
    thresholds = np.arange(0, max_degree, dtype=int)
    observed_phi, rich_counts = rich_club_profile(graph, thresholds, degrees)
    null_profiles = []
    swap_counts = []
    observed_degree_sequence = sorted(degrees.values())
    for realization in range(NULL_REALIZATIONS):
        null_graph, completed_swaps = degree_preserving_null(
            graph, SEED + realization
        )
        if sorted(dict(null_graph.degree()).values()) != observed_degree_sequence:
            raise ValueError("Degree-preserving rich-club null changed the degree sequence")
        null_phi, _ = rich_club_profile(null_graph, thresholds, dict(null_graph.degree()))
        null_profiles.append(null_phi)
        swap_counts.append(completed_swaps)
        print(
            f"  null {realization + 1:02d}/{NULL_REALIZATIONS}: "
            f"{completed_swaps} successful swaps"
        )
    null_profiles = np.asarray(null_profiles)
    null_mean = np.nanmean(null_profiles, axis=0)
    null_std = np.nanstd(null_profiles, axis=0, ddof=1)
    normalized_phi = np.divide(
        observed_phi,
        null_mean,
        out=np.full_like(observed_phi, np.nan),
        where=null_mean > 0,
    )
    empirical_p = np.asarray(
        [
            (1 + np.sum(null_profiles[:, index] >= observed_phi[index]))
            / (NULL_REALIZATIONS + 1)
            if np.isfinite(observed_phi[index])
            else np.nan
            for index in range(len(thresholds))
        ]
    )

    rich_table = pd.DataFrame(
        {
            "degree_threshold_k": thresholds,
            "nodes_with_degree_gt_k": rich_counts,
            "observed_phi": observed_phi,
            "null_phi_mean": null_mean,
            "null_phi_std": null_std,
            "normalized_phi": normalized_phi,
            "empirical_p_one_sided": empirical_p,
            "null_realizations": NULL_REALIZATIONS,
            "swaps_per_null_min": min(swap_counts),
        }
    )
    rich_table.to_csv(TABLES_DIR / "rich_club_coefficients.csv", index=False)

    positive_degrees = np.asarray([degree for degree in degrees.values() if degree > 0])
    high_degree_cutoff = int(np.floor(np.percentile(positive_degrees, 75)))
    supported = rich_table[
        (rich_table["degree_threshold_k"] >= high_degree_cutoff)
        & (rich_table["nodes_with_degree_gt_k"] >= 5)
        & rich_table["normalized_phi"].notna()
    ]
    significant = supported[
        (supported["normalized_phi"] > 1)
        & (supported["empirical_p_one_sided"] < 0.05)
    ]
    if significant.empty:
        rich_club_verdict = "no statistically supported normalized rich club"
        rich_club_detail = (
            f"No high-degree threshold (k ≥ {high_degree_cutoff}, at least five nodes) "
            "exceeded the degree-preserving null at empirical p < 0.05."
        )
    else:
        significant_thresholds = significant["degree_threshold_k"].astype(int).tolist()
        rich_club_verdict = "evidence of a normalized rich club"
        rich_club_detail = (
            f"High-degree thresholds {format_thresholds(significant_thresholds)} "
            "had normalized phi > 1 with one-sided empirical p < 0.05."
        )

    mixing_label = (
        "assortative" if assortativity > 0.05 else
        "disassortative" if assortativity < -0.05 else
        "approximately neutral"
    )
    summary = pd.DataFrame(
        [
            {
                "degree_assortativity": assortativity,
                "mixing_classification": mixing_label,
                "node_degree_vs_neighbor_degree_spearman": knn_rho,
                "node_degree_vs_neighbor_degree_p": knn_p,
                "high_degree_cutoff_75th_percentile": high_degree_cutoff,
                "rich_club_verdict": rich_club_verdict,
                "significant_high_degree_thresholds": format_thresholds(
                    significant["degree_threshold_k"].tolist()
                ),
                "null_realizations": NULL_REALIZATIONS,
                "swaps_per_null_min": min(swap_counts),
            }
        ]
    )
    summary.to_csv(TABLES_DIR / "assortativity_richclub_summary.csv", index=False)

    # k_nn(k) plot.
    plot_knn = knn_by_degree[knn_by_degree["degree"] > 0]
    fig, ax = plt.subplots(figsize=(9, 6))
    sizes = 30 + 12 * np.sqrt(plot_knn["node_count"])
    ax.scatter(
        plot_knn["degree"],
        plot_knn["mean_neighbor_degree"],
        s=sizes,
        color="#4C72B0",
        alpha=0.82,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.plot(
        plot_knn["degree"],
        plot_knn["mean_neighbor_degree"],
        color="#4C72B0",
        alpha=0.35,
        linewidth=1,
    )
    ax.set_xlabel("Node degree k")
    ax.set_ylabel("Mean nearest-neighbor degree k_nn(k)")
    ax.set_title(
        f"Degree Mixing Pattern (assortativity r = {assortativity:.3f})"
    )
    ax.text(
        0.03,
        0.05,
        f"Node-level Spearman rho = {knn_rho:.3f}\np = {knn_p:.3g}",
        transform=ax.transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )
    fig.tight_layout()
    save_figure(fig, "phase9_nearest_neighbor_degree.png")

    # Rich-club plot. Limit to thresholds with enough nodes for interpretation.
    plot_rich = rich_table[rich_table["nodes_with_degree_gt_k"] >= 3]
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhline(1, color="black", linestyle="--", linewidth=1, label="Null expectation")
    ax.plot(
        plot_rich["degree_threshold_k"],
        plot_rich["normalized_phi"],
        color="#C44E52",
        marker="o",
        markersize=3.5,
        linewidth=1.5,
        label="Observed / degree-preserving null",
    )
    ax.axvline(
        high_degree_cutoff,
        color="#555555",
        linestyle=":",
        label=f"High-degree cutoff k = {high_degree_cutoff}",
    )
    if not significant.empty:
        ax.scatter(
            significant["degree_threshold_k"],
            significant["normalized_phi"],
            color="#55A868",
            s=55,
            zorder=4,
            label="Empirical p < 0.05 (N > 4)",
        )
    ax.set_xlabel("Degree threshold k (nodes with degree > k)")
    ax.set_ylabel("Normalized rich-club coefficient")
    ax.set_title(f"Normalized Rich-Club Profile ({NULL_REALIZATIONS} Null Graphs)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    save_figure(fig, "phase9_normalized_rich_club.png")

    analysis_markdown = f"""
### Degree Mixing and Rich-Club Structure

![Nearest-neighbor degree](outputs/figures/phase9_nearest_neighbor_degree.png)
*Figure: Average nearest-neighbor degree $k_{{nn}}(k)$ by node degree. Marker size reflects the number of respondents at each degree. Isolates are excluded from the plotted relationship because they have no neighbors.*

![Normalized rich-club coefficient](outputs/figures/phase9_normalized_rich_club.png)
*Figure: Observed rich-club coefficient divided by the mean from {NULL_REALIZATIONS} seeded degree-preserving randomized graphs. Green points, when present, mark high-degree thresholds with at least five retained nodes and one-sided empirical $p<0.05$.*
"""
    results_markdown = f"""
## Degree Mixing and Rich-Club Result

The network's unweighted degree assortativity is **{assortativity:.3f}**, indicating **{mixing_label} degree mixing**. Consistently, node degree and average neighbor degree have a Spearman association of $\\rho={knn_rho:.3f}$ ($p={knn_p:.3g}$). In practical terms, the most highly connected respondents tend to connect to respondents with somewhat lower degree rather than preferentially connecting only to one another.

The normalized analysis finds **{rich_club_verdict}**. {rich_club_detail} The null ensemble contains {NULL_REALIZATIONS} simple graphs with the exact observed degree sequence and at least {min(swap_counts)} successful double-edge swaps per graph. This distinction matters: a high raw rich-club coefficient is expected in a graph this dense, so evidence requires enrichment beyond the degree-preserving baseline.
"""

    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE9_ANALYSIS_START -->",
        "<!-- PHASE9_ANALYSIS_END -->",
        analysis_markdown,
        "# Results and Discussion",
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE9_RESULTS_START -->",
        "<!-- PHASE9_RESULTS_END -->",
        results_markdown,
        "## Graph Topology",
    )
    report_path.write_text(report, encoding="utf-8")

    summary_markdown = f"""
### Phase 9: Assortativity and Rich Club
- **Degree assortativity**: {assortativity:.4f} ({mixing_label}).
- **Degree vs. mean neighbor degree**: Spearman rho = {knn_rho:.4f}, p = {knn_p:.4g}.
- **Rich-club verdict**: {rich_club_verdict}. {rich_club_detail}
- **Null model**: {NULL_REALIZATIONS} degree-preserving graphs, at least {min(swap_counts)} successful double-edge swaps each.
"""
    summary_path = PROJECT_ROOT / "results_summary.md"
    results_summary = summary_path.read_text(encoding="utf-8")
    results_summary = upsert_marked_section(
        results_summary,
        "<!-- PHASE9_SUMMARY_START -->",
        "<!-- PHASE9_SUMMARY_END -->",
        summary_markdown,
        "### Phase 10",
    )
    summary_path.write_text(results_summary, encoding="utf-8")

    print(f"Degree assortativity: {assortativity:.4f} ({mixing_label})")
    print(f"Degree vs neighbor-degree Spearman rho: {knn_rho:.4f} (p={knn_p:.4g})")
    print(f"Rich-club verdict: {rich_club_verdict}")
    print(f"  {rich_club_detail}")
    print("PHASE 9 COMPLETE")


if __name__ == "__main__":
    main()
