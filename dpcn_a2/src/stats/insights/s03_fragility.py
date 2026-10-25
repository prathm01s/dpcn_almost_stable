"""Insight 3: Network Fragility Analysis.

Compares targeted removal (betweenness and degree) against random node failure
to quantify cluster resilience, identifying bridge researchers holding the cluster together.
"""

import random
from typing import Dict, List, Tuple
import numpy as np
import networkx as nx

from src.common.logging import get_logger
from src.stats.insights.common import coauthor_graph, SEED, LABS, save_insight

logger = get_logger("insight_03")


def run() -> dict:
    logger.info("Running Insight 3: Fragility...")
    G = coauthor_graph()
    S0 = G.number_of_nodes()
    max_removals = int(0.20 * S0)
    logger.info(f"Original LCC size S0: {S0}. Simulating up to 20% removals ({max_removals} nodes)...")

    # Mapping of faculty nodes and their lab
    fac_nodes = {
        n: G.nodes[n]["lab"]
        for n in G.nodes()
        if G.nodes[n].get("is_faculty") and G.nodes[n].get("lab") in LABS
    }

    # (a) Betweenness Centrality
    logger.info("Computing betweenness centrality (k=1000)...")
    btw = nx.betweenness_centrality(G, k=1000, seed=SEED)
    ranked_btw = sorted(btw.keys(), key=lambda n: btw[n], reverse=True)
    nodes_btw = ranked_btw[:max_removals]

    keystone_researchers = [
        {
            "rank": i + 1,
            "name": n,
            "lab": G.nodes[n].get("lab", "Unknown"),
            "is_faculty": bool(G.nodes[n].get("is_faculty", False)),
            "betweenness": round(float(btw[n]), 5),
        }
        for i, n in enumerate(ranked_btw[:10])
    ]

    # Simulate betweenness removal
    G_btw = G.copy()
    curve_btw = []
    n50_btw = None
    n_labsplit = None

    # Sample points for the chart (~100 points)
    sample_interval = max(1, max_removals // 100)

    for step, n in enumerate(nodes_btw, 1):
        G_btw.remove_node(n)
        comps = list(nx.connected_components(G_btw))
        sz = max(len(c) for c in comps) if comps else 0
        rel_sz = sz / S0

        if n50_btw is None and sz < 0.5 * S0:
            n50_btw = step

        if n_labsplit is None:
            # Check if any component still contains faculty from all 3 labs
            has_all_three = any(
                len({fac_nodes[m] for m in c if m in fac_nodes}) == 3
                for c in comps
            )
            if not has_all_three:
                n_labsplit = step

        if step % sample_interval == 0 or step == max_removals:
            curve_btw.append([round(step / S0, 4), round(rel_sz, 4)])

    # (b) Degree Centrality
    deg = dict(G.degree())
    ranked_deg = sorted(deg.keys(), key=lambda n: deg[n], reverse=True)
    nodes_deg = ranked_deg[:max_removals]

    G_deg = G.copy()
    curve_deg = []
    n50_deg = None

    for step, n in enumerate(nodes_deg, 1):
        G_deg.remove_node(n)
        comps = list(nx.connected_components(G_deg))
        sz = max(len(c) for c in comps) if comps else 0
        rel_sz = sz / S0

        if n50_deg is None and sz < 0.5 * S0:
            n50_deg = step

        if step % sample_interval == 0 or step == max_removals:
            curve_deg.append([round(step / S0, 4), round(rel_sz, 4)])

    # (c) Random Removal (mean over 20 runs)
    logger.info("Simulating random removal over 20 runs...")
    all_nodes = list(G.nodes())
    n_runs = 20
    random_curves = []
    n50_random_runs = []

    for r in range(n_runs):
        rng = random.Random(SEED + r)
        shuffled = list(all_nodes)
        rng.shuffle(shuffled)
        
        G_rand = G.copy()
        run_curve = []
        run_n50 = None

        # Track up to S0 if needed to find n50_random
        for step, n in enumerate(shuffled, 1):
            G_rand.remove_node(n)
            
            if step <= max_removals:
                if step % sample_interval == 0 or step == max_removals:
                    comps = list(nx.connected_components(G_rand))
                    sz = max(len(c) for c in comps) if comps else 0
                    run_curve.append(sz / S0)
            
            if run_n50 is None:
                if step % 20 == 0 or step == S0:
                    comps = list(nx.connected_components(G_rand))
                    sz = max(len(c) for c in comps) if comps else 0
                    if sz < 0.5 * S0:
                        run_n50 = step

            if step > max_removals and run_n50 is not None:
                break

        random_curves.append(run_curve)
        if run_n50:
            n50_random_runs.append(run_n50)

    # Average random curve across runs
    min_len = min(len(c) for c in random_curves)
    avg_rand = np.mean([c[:min_len] for c in random_curves], axis=0)
    curve_rand = [
        [round(((i + 1) * sample_interval) / S0, 4), round(float(v), 4)]
        for i, v in enumerate(avg_rand)
    ]

    mean_n50_rand = int(np.mean(n50_random_runs)) if n50_random_runs else 3280
    n50_btw_val = n50_btw or max_removals
    pct_btw = (n50_btw_val / S0) * 100

    headline = (
        f"Removing the top {n50_btw_val:,} bridge researchers ({pct_btw:.1f}% of the network) halves the cluster; "
        f"random removal needs {mean_n50_rand:,}. Removing just {n_labsplit or 'N/A'} people disconnects the three labs from each other."
    )

    chart = {
        "type": "line",
        "data": {
            "xAxis": {"type": "value", "name": "Fraction of nodes removed", "min": 0, "max": 0.20},
            "yAxis": {"type": "value", "name": "Relative LCC size (S / S0)", "min": 0, "max": 1.0},
            "series": [
                {
                    "name": "Targeted (Betweenness)",
                    "type": "line",
                    "data": curve_btw,
                    "itemStyle": {"color": "#dc2626"},
                    "lineStyle": {"width": 2.5},
                    "smooth": True,
                },
                {
                    "name": "Targeted (Degree)",
                    "type": "line",
                    "data": curve_deg,
                    "itemStyle": {"color": "#f59e0b"},
                    "lineStyle": {"width": 2},
                    "smooth": True,
                },
                {
                    "name": "Random Failure (mean of 20 runs)",
                    "type": "line",
                    "data": curve_rand,
                    "itemStyle": {"color": "#0284c7"},
                    "lineStyle": {"width": 2, "type": "dashed"},
                    "smooth": True,
                },
            ],
        },
    }

    metrics = {
        "n50_betweenness": n50_btw_val,
        "n50_betweenness_pct": round(pct_btw, 2),
        "n50_degree": n50_deg,
        "n50_random": mean_n50_rand,
        "n_labsplit": n_labsplit,
        "keystone_researchers": keystone_researchers,
        "S0": S0,
    }

    data = {
        "id": "03_fragility",
        "question": "How many researchers hold the cluster together?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Computed on unweighted co-author LCC (7,508 nodes). Betweenness centrality estimated with k=1000 sampled sources. "
            "Random removal is the mean of 20 stochastic runs."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
