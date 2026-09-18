"""Phase 10: Erdős–Rényi benchmark and small-world coefficient."""

from pathlib import Path
import math
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import binom


THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
P1_SRC = PROJECT_ROOT / "src" / "p1_construction"
sys.path.insert(0, str(P1_SRC))

from utils import SEED, apply_plot_style, set_global_seed  # noqa: E402


GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
REALIZATIONS = 100


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


def graph_metrics(graph):
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    giant = graph.subgraph(components[0])
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "mean_degree": np.mean([degree for _, degree in graph.degree()]),
        "average_clustering": nx.average_clustering(graph),
        "gcc_average_path_length": nx.average_shortest_path_length(giant),
        "gcc_diameter": nx.diameter(giant),
        "gcc_size": giant.number_of_nodes(),
        "gcc_fraction": giant.number_of_nodes() / graph.number_of_nodes(),
        "components": len(components),
    }


def simulate_er_ensemble(n, probability, scenario, seed_offset):
    rows = []
    for run in range(REALIZATIONS):
        graph = nx.gnp_random_graph(
            n, probability, seed=SEED + seed_offset + run, directed=False
        )
        row = graph_metrics(graph)
        row.update(
            {
                "scenario": scenario,
                "run": run + 1,
                "seed": SEED + seed_offset + run,
                "p": probability,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def comparison_rows(real_metrics, runs, n, p, mean_degree):
    classical_path = math.log(n) / math.log(mean_degree)
    # For dense ER graphs, almost every non-edge has a two-hop path, giving this
    # useful finite-size approximation; the assignment-requested formula is also saved.
    dense_path = 2 - p
    specifications = [
        ("average_clustering", "average_clustering", p, "ER: C ≈ p"),
        (
            "average_path_length",
            "gcc_average_path_length",
            classical_path,
            "ER sparse asymptotic: ln(n)/ln(<k>)",
        ),
        ("diameter", "gcc_diameter", np.nan, "no single formula used"),
        ("giant_component_size", "gcc_size", np.nan, "no single formula used"),
        ("giant_component_fraction", "gcc_fraction", np.nan, "no single formula used"),
    ]
    rows = []
    for metric_name, column, theoretical, theory_label in specifications:
        real_key = {
            "average_path_length": "gcc_average_path_length",
            "diameter": "gcc_diameter",
            "giant_component_size": "gcc_size",
            "giant_component_fraction": "gcc_fraction",
        }.get(metric_name, metric_name)
        rows.append(
            {
                "metric": metric_name,
                "real_value": real_metrics[real_key],
                "er_mean": runs[column].mean(),
                "er_std": runs[column].std(ddof=1),
                "theoretical_value": theoretical,
                "theoretical_reference": theory_label,
                "dense_two_hop_path_approximation": (
                    dense_path if metric_name == "average_path_length" else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 10 — ERDŐS–RÉNYI BENCHMARK")
    print("=" * 70)

    full_graph = nx.read_graphml(GRAPHS_DIR / "G_full.graphml")
    giant_graph = nx.read_graphml(GRAPHS_DIR / "G_giant.graphml")
    full_metrics = graph_metrics(full_graph)
    giant_metrics = graph_metrics(giant_graph)

    n_full = full_graph.number_of_nodes()
    mean_degree_full = full_metrics["mean_degree"]
    p_full = mean_degree_full / (n_full - 1)
    n_gcc = giant_graph.number_of_nodes()
    mean_degree_gcc = giant_metrics["mean_degree"]
    p_gcc = mean_degree_gcc / (n_gcc - 1)

    print(
        f"Primary ER match: n={n_full}, <k>={mean_degree_full:.4f}, p={p_full:.6f}"
    )
    primary_runs = simulate_er_ensemble(
        n_full, p_full, "full_matched", seed_offset=0
    )
    print(
        f"GCC sensitivity match: n={n_gcc}, <k>={mean_degree_gcc:.4f}, p={p_gcc:.6f}"
    )
    gcc_runs = simulate_er_ensemble(
        n_gcc, p_gcc, "gcc_matched", seed_offset=10000
    )
    all_runs = pd.concat([primary_runs, gcc_runs], ignore_index=True)
    all_runs.to_csv(TABLES_DIR / "er_benchmark_runs.csv", index=False)

    comparison = comparison_rows(
        full_metrics, primary_runs, n_full, p_full, mean_degree_full
    )
    comparison.insert(0, "comparison_basis", "full_n_and_mean_degree")
    comparison.to_csv(TABLES_DIR / "er_benchmark_comparison.csv", index=False)

    c_er = primary_runs["average_clustering"].mean()
    l_er = primary_runs["gcc_average_path_length"].mean()
    sigma_primary = (
        (full_metrics["average_clustering"] / c_er)
        / (full_metrics["gcc_average_path_length"] / l_er)
    )
    c_er_gcc = gcc_runs["average_clustering"].mean()
    l_er_gcc = gcc_runs["gcc_average_path_length"].mean()
    sigma_gcc = (
        (giant_metrics["average_clustering"] / c_er_gcc)
        / (giant_metrics["gcc_average_path_length"] / l_er_gcc)
    )
    small_world_supported = sigma_primary > 1 and sigma_gcc > 1
    verdict = (
        "small-world-like relative to matched ER graphs"
        if small_world_supported
        else "not consistently small-world-like under both ER comparisons"
    )

    log_n = math.log(n_full)
    regime = (
        "dense, well above the ER connectivity scale"
        if mean_degree_full > log_n
        else "below or near the ER connectivity scale"
    )
    theory_clustering = p_full
    theory_path = math.log(n_full) / math.log(mean_degree_full)
    dense_path = 2 - p_full
    theory_summary = pd.DataFrame(
        [
            {
                "full_nodes": n_full,
                "full_edges": full_graph.number_of_edges(),
                "observed_mean_degree": mean_degree_full,
                "matched_er_p": p_full,
                "ln_n_connectivity_scale": log_n,
                "mean_degree_regime": regime,
                "real_clustering_full": full_metrics["average_clustering"],
                "er_clustering_mean": c_er,
                "theoretical_er_clustering_p": theory_clustering,
                "real_gcc_path_length": full_metrics["gcc_average_path_length"],
                "er_gcc_path_length_mean": l_er,
                "theoretical_sparse_path_ln_n_over_ln_k": theory_path,
                "dense_two_hop_path_approximation_2_minus_p": dense_path,
                "small_world_sigma_primary": sigma_primary,
                "small_world_sigma_gcc_sensitivity": sigma_gcc,
                "small_world_verdict": verdict,
                "realizations_per_scenario": REALIZATIONS,
            }
        ]
    )
    theory_summary.to_csv(TABLES_DIR / "small_world_summary.csv", index=False)

    # Requested real-vs-ER metric comparison.
    metric_labels = ["Clustering", "Path length", "Diameter"]
    real_values = [
        full_metrics["average_clustering"],
        full_metrics["gcc_average_path_length"],
        full_metrics["gcc_diameter"],
    ]
    er_columns = ["average_clustering", "gcc_average_path_length", "gcc_diameter"]
    er_means = [primary_runs[column].mean() for column in er_columns]
    er_stds = [primary_runs[column].std(ddof=1) for column in er_columns]
    positions = np.arange(len(metric_labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 6))
    real_bars = ax.bar(
        positions - width / 2,
        real_values,
        width,
        label="Real network",
        color="#4C72B0",
    )
    er_bars = ax.bar(
        positions + width / 2,
        er_means,
        width,
        yerr=er_stds,
        capsize=5,
        label=f"ER mean ± SD ({REALIZATIONS} runs)",
        color="#DD8452",
    )
    ax.set_xticks(positions, metric_labels)
    ax.set_ylabel("Metric value")
    ax.set_title("Real Opinion Network vs. Matched Erdős–Rényi Graphs")
    ax.legend()
    ax.bar_label(real_bars, fmt="%.3g", padding=3)
    ax.bar_label(er_bars, fmt="%.3g", padding=3)
    fig.tight_layout()
    save_figure(fig, "phase10_er_metric_comparison.png")

    # Real degree counts against the exact matched Binomial expectation.
    degrees = np.asarray([degree for _, degree in full_graph.degree()])
    degree_axis = np.arange(0, n_full)
    observed_counts = np.bincount(degrees, minlength=n_full)
    expected_counts = n_full * binom.pmf(degree_axis, n_full - 1, p_full)
    degree_table = pd.DataFrame(
        {
            "degree": degree_axis,
            "real_node_count": observed_counts,
            "er_binomial_expected_count": expected_counts,
        }
    )
    degree_table.to_csv(TABLES_DIR / "er_degree_distribution_comparison.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    nonzero = observed_counts > 0
    ax.bar(
        degree_axis[nonzero],
        observed_counts[nonzero],
        width=0.85,
        alpha=0.58,
        color="#4C72B0",
        label="Real degree counts",
    )
    ax.plot(
        degree_axis,
        expected_counts,
        color="#C44E52",
        linewidth=2.2,
        label=f"ER Binomial expectation (n={n_full}, p={p_full:.3f})",
    )
    ax.set_xlim(-1, max(degrees) + 4)
    ax.set_xlabel("Degree k")
    ax.set_ylabel("Expected / observed node count")
    ax.set_title("Degree Distribution: Real Network vs. Matched ER Expectation")
    ax.legend()
    fig.tight_layout()
    save_figure(fig, "phase10_degree_distribution_er.png")

    analysis_markdown = f"""
### Erdős–Rényi Benchmark

![Real versus ER metrics](outputs/figures/phase10_er_metric_comparison.png)
*Figure: Real-network clustering and GCC path metrics compared with the mean ± standard deviation from {REALIZATIONS} $G(n,p)$ realizations matched to $n={n_full}$ and $p={p_full:.3f}$. Path length and diameter are evaluated on each graph's largest connected component.*

![Degree distribution versus ER](outputs/figures/phase10_degree_distribution_er.png)
*Figure: Observed degree counts compared with the exact Binomial degree expectation for the matched ER model. The real network's isolated nodes and concentration of high-degree respondents differ visibly from the homogeneous random-connection baseline.*
"""
    results_markdown = f"""
## Erdős–Rényi Benchmark and Small-World Verdict

The primary ER ensemble matches the full network's $n={n_full}$ and mean degree $\\langle k\\rangle={mean_degree_full:.2f}$, giving $p={p_full:.3f}$. Across {REALIZATIONS} realizations, mean clustering is {c_er:.3f} (real full-network value {full_metrics['average_clustering']:.3f}), mean GCC path length is {l_er:.3f} (real GCC value {full_metrics['gcc_average_path_length']:.3f}), and mean GCC size is {primary_runs['gcc_size'].mean():.1f} of {n_full} nodes (real: {full_metrics['gcc_size']}). The real network is therefore more clustered than a homogeneous random graph while retaining similarly short paths, although it also has nine threshold-induced isolates.

The resulting small-world coefficient is **$\\sigma={sigma_primary:.3f}$** for the full-network-matched benchmark. A second benchmark matched directly to the 82-node GCC gives **$\\sigma={sigma_gcc:.3f}$**. Because both exceed one, the network is classified as **{verdict}**. This is a relative ER statement, not evidence that the degree distribution is scale-free.

The ER clustering approximation $C\\approx p$ predicts {theory_clustering:.3f}, close to the simulated mean {c_er:.3f}. The requested sparse-graph path approximation $\\ln(n)/\\ln\\langle k\\rangle$ gives {theory_path:.3f}, whereas the simulations average {l_er:.3f}; it underestimates distance because this network is far outside the sparse asymptotic regime. For this dense case, the two-hop approximation $2-p={dense_path:.3f}$ is much closer. Since $\\langle k\\rangle={mean_degree_full:.2f} \\gg \\ln(n)={log_n:.2f}$, the matched ER model lies in a **{regime}**, with near-certain connectivity.
"""

    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE10_ANALYSIS_START -->",
        "<!-- PHASE10_ANALYSIS_END -->",
        analysis_markdown,
        "# Results and Discussion",
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE10_RESULTS_START -->",
        "<!-- PHASE10_RESULTS_END -->",
        results_markdown,
        "## Graph Topology",
    )
    report_path.write_text(report, encoding="utf-8")

    summary_markdown = f"""
### Phase 10: Erdős–Rényi Benchmark
- **Primary match**: n = {n_full}, mean degree = {mean_degree_full:.4f}, p = {p_full:.6f}, {REALIZATIONS} realizations.
- **Real vs. ER clustering**: {full_metrics['average_clustering']:.4f} vs. {c_er:.4f}; theoretical p = {theory_clustering:.4f}.
- **Real vs. ER GCC path length**: {full_metrics['gcc_average_path_length']:.4f} vs. {l_er:.4f}; sparse formula = {theory_path:.4f}, dense two-hop approximation = {dense_path:.4f}.
- **Small-world coefficients**: primary sigma = {sigma_primary:.4f}; GCC-matched sensitivity sigma = {sigma_gcc:.4f}.
- **Verdict**: {verdict}; mean degree is far above ln(n), placing the matched ER graph in the dense connected regime.
"""
    summary_path = PROJECT_ROOT / "results_summary.md"
    results_summary = summary_path.read_text(encoding="utf-8")
    results_summary = upsert_marked_section(
        results_summary,
        "<!-- PHASE10_SUMMARY_START -->",
        "<!-- PHASE10_SUMMARY_END -->",
        summary_markdown,
        "### Phase 11",
    )
    summary_path.write_text(results_summary, encoding="utf-8")

    print(
        f"Primary sigma={sigma_primary:.4f}; GCC sensitivity sigma={sigma_gcc:.4f}"
    )
    print(f"Verdict: {verdict}")
    print(
        f"ER clustering mean={c_er:.4f} (theory p={theory_clustering:.4f}); "
        f"path mean={l_er:.4f} (sparse theory={theory_path:.4f}, dense approx={dense_path:.4f})"
    )
    print("PHASE 10 COMPLETE")


if __name__ == "__main__":
    main()
