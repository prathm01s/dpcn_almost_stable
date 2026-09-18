"""Phase 11: friendship paradox in the opinion network and one matched ER graph."""

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

from utils import SEED, apply_plot_style, set_global_seed  # noqa: E402


GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def upsert_marked_section(text, start_marker, end_marker, content, before):
    section = f"{start_marker}\n{content.strip()}\n{end_marker}"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.S)
    if pattern.search(text):
        return pattern.sub(lambda _match: section, text, count=1)
    if before in text:
        return text.replace(before, section + "\n\n" + before, 1)
    return text.rstrip() + "\n\n" + section + "\n"


def save_figure(fig, name):
    path = FIGURES_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path.relative_to(PROJECT_ROOT)}")


def per_node_table(graph, scenario):
    degree = dict(graph.degree())
    neighbor_degree = nx.average_neighbor_degree(graph)
    nodes = sorted(graph.nodes(), key=lambda node: int(node))
    return pd.DataFrame(
        {
            "scenario": scenario,
            "node": [str(node) for node in nodes],
            "degree": [degree[node] for node in nodes],
            "average_neighbor_degree": [neighbor_degree[node] for node in nodes],
            "is_isolate": [degree[node] == 0 for node in nodes],
            "friendship_paradox_holds": [
                neighbor_degree[node] > degree[node] if degree[node] > 0 else False
                for node in nodes
            ],
            "neighbor_degree_minus_own": [
                neighbor_degree[node] - degree[node] if degree[node] > 0 else np.nan
                for node in nodes
            ],
        }
    )


def summarize(graph, node_table, scenario, matched_p, target_mean_degree):
    degrees = np.asarray([degree for _, degree in graph.degree()], dtype=float)
    non_isolates = node_table.loc[~node_table["is_isolate"]]
    mean_degree = degrees.mean()
    mean_neighbor_degree = non_isolates["average_neighbor_degree"].mean()
    edge_endpoint_mean = np.sum(degrees**2) / np.sum(degrees)
    return {
        "scenario": scenario,
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "isolates": int(node_table["is_isolate"].sum()),
        "mean_degree_all_nodes": mean_degree,
        "mean_per_node_neighbor_degree_nonisolates": mean_neighbor_degree,
        "neighbor_minus_own_mean": mean_neighbor_degree - mean_degree,
        "edge_endpoint_mean_neighbor_degree_k2_over_k": edge_endpoint_mean,
        "fraction_nonisolates_with_neighbor_degree_gt_own": non_isolates[
            "friendship_paradox_holds"
        ].mean(),
        "median_neighbor_degree_minus_own_nonisolates": non_isolates[
            "neighbor_degree_minus_own"
        ].median(),
        "target_mean_degree": target_mean_degree,
        "poisson_reference_target_mean_degree_plus_1": target_mean_degree + 1,
        "poisson_reference_realized_mean_degree_plus_1": mean_degree + 1,
        "finite_binomial_reference_1_plus_n_minus_2_p": (
            1 + (graph.number_of_nodes() - 2) * matched_p
        ),
        "matched_p": matched_p,
    }


def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 11 — FRIENDSHIP PARADOX")
    print("=" * 70)

    real_graph = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    n = real_graph.number_of_nodes()
    mean_degree_target = np.mean([degree for _, degree in real_graph.degree()])
    matched_p = mean_degree_target / (n - 1)
    er_graph = nx.gnp_random_graph(n, matched_p, seed=SEED, directed=False)

    real_nodes = per_node_table(real_graph, "real_opinion_network")
    er_nodes = per_node_table(er_graph, "matched_er_seed_42")
    per_node = pd.concat([real_nodes, er_nodes], ignore_index=True)
    per_node.to_csv(TABLES_DIR / "friendship_paradox_by_node.csv", index=False)

    summary = pd.DataFrame(
        [
            summarize(
                real_graph,
                real_nodes,
                "real_opinion_network",
                matched_p,
                mean_degree_target,
            ),
            summarize(
                er_graph,
                er_nodes,
                "matched_er_seed_42",
                matched_p,
                mean_degree_target,
            ),
        ]
    )
    summary.to_csv(TABLES_DIR / "friendship_paradox_summary.csv", index=False)
    real_summary = summary.iloc[0]
    er_summary = summary.iloc[1]

    # Scatter requested by the handoff. Isolates remain visible at the origin but
    # are excluded from ratios and averages because they do not have neighbors.
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(
        er_nodes["degree"],
        er_nodes["average_neighbor_degree"],
        s=35,
        alpha=0.48,
        color="#DD8452",
        edgecolors="none",
        label="Matched ER realization (seed 42)",
    )
    ax.scatter(
        real_nodes["degree"],
        real_nodes["average_neighbor_degree"],
        s=46,
        alpha=0.70,
        color="#4C72B0",
        edgecolors="white",
        linewidths=0.4,
        label="Real opinion network",
    )
    upper = max(
        per_node["degree"].max(), per_node["average_neighbor_degree"].max()
    ) + 3
    ax.plot([0, upper], [0, upper], "k--", linewidth=1.2, label="y = x")
    ax.set_xlim(-1, upper)
    ax.set_ylim(-1, upper)
    ax.set_xlabel("Respondent degree k(i)")
    ax.set_ylabel("Average degree of respondent i's neighbors k_nn(i)")
    ax.set_title("Friendship Paradox: Real Opinion Network vs. Matched ER")
    ax.legend(loc="lower right", fontsize=9)
    ax.text(
        0.03,
        0.95,
        (
            f"Real: {real_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.1%} above y=x\n"
            f"ER: {er_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.1%} above y=x"
        ),
        transform=ax.transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.88},
    )
    fig.tight_layout()
    save_figure(fig, "phase11_friendship_paradox.png")

    real_holds = (
        real_summary["mean_per_node_neighbor_degree_nonisolates"]
        > real_summary["mean_degree_all_nodes"]
    )
    verdict = "holds" if real_holds else "does not hold"
    er_poisson_gap = (
        er_summary["mean_per_node_neighbor_degree_nonisolates"]
        - er_summary["poisson_reference_target_mean_degree_plus_1"]
    )

    analysis_markdown = """
### Friendship Paradox

![Friendship paradox scatter](outputs/figures/phase11_friendship_paradox.png)
*Figure: Each node's average neighbor degree versus its own degree for the real opinion network and the seed-42 matched ER realization. Points above the dashed identity line satisfy the individual friendship paradox. Isolates appear at the origin but are excluded from neighbor-based averages and fractions.*
"""
    results_markdown = f"""
## Friendship Paradox

The friendship paradox **{verdict}** in the opinion network. Across non-isolates, the mean per-respondent neighbor degree is **{real_summary['mean_per_node_neighbor_degree_nonisolates']:.2f}**, compared with a network-wide mean degree of **{real_summary['mean_degree_all_nodes']:.2f}**. The classical edge-endpoint expectation $\\langle k^2\\rangle/\\langle k\\rangle$ is {real_summary['edge_endpoint_mean_neighbor_degree_k2_over_k']:.2f}, independently confirming that a randomly encountered opinion-neighbor is more connected than a randomly chosen respondent. At the individual level, **{real_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.1%}** of respondents with at least one connection have $k_{{nn}}(i)>k(i)$.

In the seed-42 matched ER graph, mean per-node neighbor degree is {er_summary['mean_per_node_neighbor_degree_nonisolates']:.2f}, mean degree is {er_summary['mean_degree_all_nodes']:.2f}, and {er_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.1%} of nodes satisfy the individual inequality. Using the matched model mean, the requested Poisson reference $\\langle k\\rangle+1$ is {er_summary['poisson_reference_target_mean_degree_plus_1']:.2f}, a difference of {er_poisson_gap:+.2f} from this single realization (the plug-in reference using the realization's own mean is {er_summary['poisson_reference_realized_mean_degree_plus_1']:.2f}). Because the matched ER degree distribution is finite Binomial rather than exactly Poisson, its exact ensemble reference is $1+(n-2)p={er_summary['finite_binomial_reference_1_plus_n_minus_2_p']:.2f}$.

Intuitively, a typical respondent's opinion-neighbors have more above-threshold connections to the rest of the class than the typical respondent does. The effect is much larger in the real graph than in the ER realization, reflecting the real network's broad and threshold-induced degree heterogeneity; it does not mean that every high-degree respondent experiences the paradox.
"""

    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE11_ANALYSIS_START -->",
        "<!-- PHASE11_ANALYSIS_END -->",
        analysis_markdown,
        "# Results and Discussion",
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE11_RESULTS_START -->",
        "<!-- PHASE11_RESULTS_END -->",
        results_markdown,
        "## Graph Topology",
    )
    report_path.write_text(report, encoding="utf-8")

    summary_markdown = f"""
### Phase 11: Friendship Paradox
- **Real network**: mean degree = {real_summary['mean_degree_all_nodes']:.4f}; mean per-node neighbor degree among non-isolates = {real_summary['mean_per_node_neighbor_degree_nonisolates']:.4f}; individual-paradox fraction = {real_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.4f}.
- **Classical edge-endpoint mean**: {real_summary['edge_endpoint_mean_neighbor_degree_k2_over_k']:.4f}, exceeding the real mean degree.
- **Matched ER seed 42**: mean degree = {er_summary['mean_degree_all_nodes']:.4f}; mean per-node neighbor degree = {er_summary['mean_per_node_neighbor_degree_nonisolates']:.4f}; fraction = {er_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.4f}.
- **Theory checks**: ER Poisson reference from the matched model mean, $\\langle k\\rangle+1$ = {er_summary['poisson_reference_target_mean_degree_plus_1']:.4f}; plug-in reference from the realization's mean = {er_summary['poisson_reference_realized_mean_degree_plus_1']:.4f}; exact finite Binomial reference $1+(n-2)p$ = {er_summary['finite_binomial_reference_1_plus_n_minus_2_p']:.4f}.
- **Verdict**: the friendship paradox {verdict} and is substantially stronger in the real opinion network than in the matched ER realization.
"""
    summary_path = PROJECT_ROOT / "results_summary.md"
    results_summary = summary_path.read_text(encoding="utf-8")
    results_summary = upsert_marked_section(
        results_summary,
        "<!-- PHASE11_SUMMARY_START -->",
        "<!-- PHASE11_SUMMARY_END -->",
        summary_markdown,
        "### Phase 12",
    )
    summary_path.write_text(results_summary, encoding="utf-8")

    print(
        f"Real: <k>={real_summary['mean_degree_all_nodes']:.4f}, "
        f"<k_nn>={real_summary['mean_per_node_neighbor_degree_nonisolates']:.4f}, "
        f"fraction={real_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.4f}"
    )
    print(
        f"ER: <k>={er_summary['mean_degree_all_nodes']:.4f}, "
        f"<k_nn>={er_summary['mean_per_node_neighbor_degree_nonisolates']:.4f}, "
        f"fraction={er_summary['fraction_nonisolates_with_neighbor_degree_gt_own']:.4f}"
    )
    print(f"Verdict: friendship paradox {verdict}")
    print("PHASE 11 COMPLETE")


if __name__ == "__main__":
    main()
