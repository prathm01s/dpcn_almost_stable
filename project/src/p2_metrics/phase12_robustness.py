"""Phase 12: random-failure and targeted-attack robustness analysis."""

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
RANDOM_ORDERINGS = 100


def upsert_marked_section(text, start_marker, end_marker, content, before):
    section = f"{start_marker}\n{content.strip()}\n{end_marker}"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.S)
    if pattern.search(text):
        return pattern.sub(lambda _match: section, text, count=1)
    if before in text:
        return text.replace(before, section + "\n\n" + before, 1)
    return text.rstrip() + "\n\n" + section + "\n"


def largest_component_size(graph):
    return max((len(component) for component in nx.connected_components(graph)), default=0)


def removal_curve(graph, removal_order):
    """Return GCC size after 0..N removals, normalized by original N."""
    original_n = graph.number_of_nodes()
    working = graph.copy()
    sizes = [largest_component_size(working)]
    for node in removal_order:
        working.remove_node(node)
        sizes.append(largest_component_size(working))
    sizes = np.asarray(sizes, dtype=int)
    return sizes, sizes / original_n


def static_attack_rankings(graph):
    """Rank nodes once on the intact graph, with numeric ID as the tie-breaker."""
    degrees = dict(graph.degree())
    giant_nodes = max(nx.connected_components(graph), key=len)
    giant = graph.subgraph(giant_nodes)
    betweenness_giant = nx.betweenness_centrality(giant, normalized=True)
    betweenness = {
        node: betweenness_giant.get(node, 0.0) for node in graph.nodes()
    }

    degree_order = sorted(graph.nodes(), key=lambda node: (-degrees[node], int(node)))
    betweenness_order = sorted(
        graph.nodes(), key=lambda node: (-betweenness[node], int(node))
    )

    degree_rank = {node: rank for rank, node in enumerate(degree_order, start=1)}
    betweenness_rank = {
        node: rank for rank, node in enumerate(betweenness_order, start=1)
    }
    ranking_table = pd.DataFrame(
        {
            "ResponseID": [int(node) for node in sorted(graph.nodes(), key=int)],
            "degree": [degrees[node] for node in sorted(graph.nodes(), key=int)],
            "degree_attack_rank": [
                degree_rank[node] for node in sorted(graph.nodes(), key=int)
            ],
            "betweenness_centrality_gcc": [
                betweenness[node] for node in sorted(graph.nodes(), key=int)
            ],
            "betweenness_attack_rank": [
                betweenness_rank[node] for node in sorted(graph.nodes(), key=int)
            ],
        }
    )
    return degree_order, betweenness_order, ranking_table


def threshold_row(strategy, curve, original_n, random_orderings=None):
    crossing = np.flatnonzero(curve < 0.5)
    removal_count = int(crossing[0]) if len(crossing) else original_n
    previous_index = max(0, removal_count - 1)
    return {
        "strategy": strategy,
        "threshold_definition": "first fraction removed where GCC/original_N < 0.5",
        "removal_count_at_threshold": removal_count,
        "fraction_removed_at_threshold": removal_count / original_n,
        "gcc_fraction_before_threshold": curve[previous_index],
        "gcc_fraction_at_threshold": curve[removal_count],
        "robustness_auc": np.sum((curve[:-1] + curve[1:]) / 2) / original_n,
        "random_orderings": random_orderings,
    }


def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 12 — ROBUSTNESS / ATTACK TOLERANCE")
    print("=" * 70)

    graph = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    nodes = np.asarray(sorted(graph.nodes(), key=int), dtype=object)
    original_n = graph.number_of_nodes()
    removed_count = np.arange(original_n + 1)
    fraction_removed = removed_count / original_n

    degree_order, betweenness_order, ranking_table = static_attack_rankings(graph)
    ranking_table.to_csv(TABLES_DIR / "robustness_attack_rankings.csv", index=False)

    degree_sizes, degree_curve = removal_curve(graph, degree_order)
    betweenness_sizes, betweenness_curve = removal_curve(graph, betweenness_order)

    random_curves = []
    random_run_rows = []
    for run in range(RANDOM_ORDERINGS):
        seed = SEED + run
        order = np.random.default_rng(seed).permutation(nodes)
        sizes, curve = removal_curve(graph, order)
        random_curves.append(curve)
        random_run_rows.extend(
            {
                "run": run + 1,
                "seed": seed,
                "removed_count": int(step),
                "fraction_removed": step / original_n,
                "gcc_size": int(size),
                "gcc_fraction_original_n": fraction,
            }
            for step, (size, fraction) in enumerate(zip(sizes, curve))
        )
    random_curves = np.asarray(random_curves)
    random_mean = random_curves.mean(axis=0)
    random_std = random_curves.std(axis=0, ddof=1)
    pd.DataFrame(random_run_rows).to_csv(
        TABLES_DIR / "random_failure_runs.csv", index=False
    )

    curves = pd.DataFrame(
        {
            "removed_count": removed_count,
            "fraction_removed": fraction_removed,
            "random_failure_mean_gcc_fraction": random_mean,
            "random_failure_std_gcc_fraction": random_std,
            "degree_attack_gcc_size": degree_sizes,
            "degree_attack_gcc_fraction": degree_curve,
            "betweenness_attack_gcc_size": betweenness_sizes,
            "betweenness_attack_gcc_fraction": betweenness_curve,
        }
    )
    curves.to_csv(TABLES_DIR / "robustness_curves.csv", index=False)

    thresholds = pd.DataFrame(
        [
            threshold_row(
                "random_failure_mean", random_mean, original_n, RANDOM_ORDERINGS
            ),
            threshold_row("static_degree_attack", degree_curve, original_n),
            threshold_row(
                "static_betweenness_attack", betweenness_curve, original_n
            ),
        ]
    )
    thresholds.to_csv(TABLES_DIR / "robustness_thresholds.csv", index=False)
    threshold_by_strategy = thresholds.set_index("strategy")

    random_threshold = threshold_by_strategy.loc[
        "random_failure_mean", "fraction_removed_at_threshold"
    ]
    degree_threshold = threshold_by_strategy.loc[
        "static_degree_attack", "fraction_removed_at_threshold"
    ]
    betweenness_threshold = threshold_by_strategy.loc[
        "static_betweenness_attack", "fraction_removed_at_threshold"
    ]

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.fill_between(
        fraction_removed,
        np.clip(random_mean - random_std, 0, 1),
        np.clip(random_mean + random_std, 0, 1),
        color="#4C72B0",
        alpha=0.16,
        linewidth=0,
        label="Random failure ±1 SD",
    )
    ax.plot(
        fraction_removed,
        random_mean,
        color="#4C72B0",
        linewidth=2.4,
        label=f"Random failure mean ({RANDOM_ORDERINGS} orderings)",
    )
    ax.plot(
        fraction_removed,
        degree_curve,
        color="#DD8452",
        linewidth=2.2,
        label="Static degree attack",
    )
    ax.plot(
        fraction_removed,
        betweenness_curve,
        color="#55A868",
        linewidth=2.2,
        label="Static betweenness attack",
    )
    ax.axhline(0.5, color="black", linestyle="--", linewidth=1.2, label="50% GCC")
    for threshold, color in [
        (random_threshold, "#4C72B0"),
        (degree_threshold, "#DD8452"),
        (betweenness_threshold, "#55A868"),
    ]:
        ax.scatter(threshold, 0.5, s=52, color=color, edgecolor="white", zorder=5)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Fraction of original respondents removed")
    ax.set_ylabel("Giant component size / original network size")
    ax.set_title("Network Robustness Under Random Failure and Targeted Attack")
    ax.legend(loc="upper right", fontsize=9)
    ax.text(
        0.03,
        0.08,
        (
            f"50% thresholds\nRandom: {random_threshold:.1%}\n"
            f"Degree: {degree_threshold:.1%}\n"
            f"Betweenness: {betweenness_threshold:.1%}"
        ),
        transform=ax.transAxes,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9},
    )
    fig.tight_layout()
    figure_path = FIGURES_DIR / "phase12_robustness_attacks.png"
    fig.savefig(figure_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {figure_path.relative_to(PROJECT_ROOT)}")

    random_auc = threshold_by_strategy.loc["random_failure_mean", "robustness_auc"]
    degree_auc = threshold_by_strategy.loc["static_degree_attack", "robustness_auc"]
    betweenness_auc = threshold_by_strategy.loc[
        "static_betweenness_attack", "robustness_auc"
    ]

    analysis_markdown = """
### Robustness and Attack Tolerance

![Robustness curves](outputs/figures/phase12_robustness_attacks.png)
*Figure: Giant-component size, normalized by the original 91-node network, as respondents are removed. Random failure is the mean of 100 seeded removal orderings with a ±1 SD band. Degree and betweenness attacks use rankings computed once on the intact graph; colored markers show the first removal fraction at which the GCC falls below 50% of the original network.*
"""
    results_markdown = f"""
## Robustness and Attack Tolerance

The network exhibits a **robust-yet-fragile** pattern. Under random respondent failure, the mean giant component first falls below 50% of the original network after **{int(round(random_threshold * original_n))} of {original_n} removals ({random_threshold:.1%})**. The corresponding threshold occurs earlier under static degree attack, after **{int(round(degree_threshold * original_n))} removals ({degree_threshold:.1%})**, and earliest under static betweenness attack, after **{int(round(betweenness_threshold * original_n))} removals ({betweenness_threshold:.1%})**.

The full-curve robustness areas reinforce this ordering: {random_auc:.3f} for random failure, {degree_auc:.3f} for degree attack, and {betweenness_auc:.3f} for betweenness attack. Thus, arbitrary respondent loss is comparatively well tolerated, while removing the most connected or most path-critical respondents causes faster fragmentation. The comparison uses static attack rankings computed on the intact network, not adaptive re-ranking after every removal. GCC fractions use the original 91 respondents as the denominator, and the nine initial isolates therefore keep the baseline at 82/91 = 90.1%.
"""

    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE12_ANALYSIS_START -->",
        "<!-- PHASE12_ANALYSIS_END -->",
        analysis_markdown,
        "# Results and Discussion",
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE12_RESULTS_START -->",
        "<!-- PHASE12_RESULTS_END -->",
        results_markdown,
        "## Graph Topology",
    )
    report_path.write_text(report, encoding="utf-8")

    summary_markdown = f"""
### Phase 12: Robustness and Attack Tolerance
- **Random failure**: 100 seeded orderings; mean GCC falls below 50% at {random_threshold:.4f} removed ({int(round(random_threshold * original_n))}/{original_n}); robustness AUC = {random_auc:.4f}.
- **Static degree attack**: threshold = {degree_threshold:.4f} ({int(round(degree_threshold * original_n))}/{original_n}); robustness AUC = {degree_auc:.4f}.
- **Static betweenness attack**: threshold = {betweenness_threshold:.4f} ({int(round(betweenness_threshold * original_n))}/{original_n}); robustness AUC = {betweenness_auc:.4f}.
- **Convention**: GCC size is divided by the original network size; attack rankings are computed once on the intact graph.
- **Verdict**: robust-yet-fragile—random failures are tolerated longer than targeted removal of high-degree or high-betweenness respondents.
"""
    summary_path = PROJECT_ROOT / "results_summary.md"
    results_summary = summary_path.read_text(encoding="utf-8")
    results_summary = upsert_marked_section(
        results_summary,
        "<!-- PHASE12_SUMMARY_START -->",
        "<!-- PHASE12_SUMMARY_END -->",
        summary_markdown,
        "### Phase 13",
    )
    summary_path.write_text(results_summary, encoding="utf-8")

    print(f"Random-failure 50% threshold: {random_threshold:.4f}")
    print(f"Degree-attack 50% threshold: {degree_threshold:.4f}")
    print(f"Betweenness-attack 50% threshold: {betweenness_threshold:.4f}")
    print("PHASE 12 COMPLETE")


if __name__ == "__main__":
    main()
