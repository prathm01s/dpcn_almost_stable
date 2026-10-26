"""Insight 2: Co-authorship Rich Club Analysis.

Tests whether the most-connected scientists preferentially collaborate with one another
compared to degree-preserving randomized null graphs.
"""

from collections import Counter
import numpy as np
import networkx as nx

from src.common.logging import get_logger
from src.stats.insights.common import coauthor_graph, SEED, save_insight

logger = get_logger("insight_02")


def run(n_nulls: int = 20) -> dict:
    logger.info("Running Insight 2: Rich Club...")
    G = coauthor_graph()
    E = G.number_of_edges()

    # Empirical unnormalized rich club coefficient
    rc_emp = nx.rich_club_coefficient(G, normalized=False)
    k_vals = sorted(rc_emp.keys())

    # Degree distribution and 99th percentile degree k*
    degrees = [d for _, d in G.degree()]
    k_star = int(np.percentile(degrees, 99))

    # Top 1% nodes (degree >= k_star)
    top1_nodes = [n for n, d in G.degree() if d >= k_star]
    top1_faculty = [n for n in top1_nodes if G.nodes[n].get("is_faculty", False)]
    top1_labs = Counter([G.nodes[n].get("lab", "Unknown") for n in top1_nodes])

    # 20 rewired null graphs
    logger.info(f"Generating {n_nulls} degree-preserving rewired graphs (nswap=10*E)...")
    nswap = 10 * E
    null_rcs = {k: [] for k in k_vals}

    for i in range(n_nulls):
        G_rand = G.copy()
        nx.double_edge_swap(G_rand, nswap=nswap, max_tries=100 * nswap, seed=SEED + i)
        rc_rand = nx.rich_club_coefficient(G_rand, normalized=False)
        for k in k_vals:
            if k in rc_rand:
                null_rcs[k].append(rc_rand[k])

    # Compute normalized rich club: rho_norm(k) = rho(k) / mean(rho_rand(k))
    rho_norm = {}
    chart_data = []
    for k in k_vals:
        rands = null_rcs[k]
        if rands and np.mean(rands) > 0:
            val = float(rc_emp[k] / np.mean(rands))
            rho_norm[k] = val
            chart_data.append([int(k), round(val, 3)])

    # networkx rho(k) covers nodes with degree > k; the top-1% set is degree >= k_star, i.e. rho(k_star - 1)
    rho_at_kstar = rho_norm.get(k_star - 1)
    if rho_at_kstar is None:
        raise ValueError(f"No rich-club value at k = {k_star - 1}; cannot evaluate the top-1% set")

    # Dynamic headline based on true result
    n_fac = len(top1_faculty)
    n_top = len(top1_nodes)
    if rho_at_kstar >= 1.05:
        headline = (
            f"The top 1% most-connected researchers are {rho_at_kstar:.2f}× more interconnected than chance "
            f"(ρ_norm = {rho_at_kstar:.2f}). {n_fac} of them are CSIR faculty."
        )
    elif rho_at_kstar <= 0.95:
        headline = (
            f"The top 1% most-connected researchers show no rich-club effect and are less interconnected than chance "
            f"(ρ_norm = {rho_at_kstar:.2f}). {n_fac} of {n_top} are CSIR faculty."
        )
    else:
        headline = (
            f"The top 1% most-connected researchers are no more interconnected than chance "
            f"(ρ_norm = {rho_at_kstar:.2f} ≈ 1). {n_fac} of {n_top} are CSIR faculty."
        )

    chart = {
        "type": "line",
        "data": {
            "xAxis": {"type": "value", "name": "Degree threshold k", "min": min(k_vals), "max": max(k_vals)},
            "yAxis": {"type": "value", "name": "Normalized Rich Club ρ_norm(k)"},
            "series": [
                {
                    "name": "ρ_norm(k)",
                    "type": "line",
                    "data": chart_data,
                    "itemStyle": {"color": "#0284c7"},
                    "lineStyle": {"width": 2},
                    "smooth": True,
                    "markLine": {
                        "data": [{"yAxis": 1.0, "name": "Chance level", "lineStyle": {"color": "#dc2626", "type": "dashed"}}],
                        "symbol": "none",
                    },
                }
            ],
            "markPoint": {
                "k_star": k_star,
                "rho_k_star": round(rho_at_kstar, 3),
                "note": "rho_norm at k*-1 = normalised density among nodes with degree >= k*",
            },
        },
    }

    metrics = {
        "k_star": k_star,
        "rho_norm_at_k_star": round(rho_at_kstar, 3),
        "n_top1_percent": n_top,
        "n_top1_faculty": n_fac,
        "top1_labs": dict(top1_labs),
        "n_nulls": n_nulls,
    }

    data = {
        "id": "02_rich_club",
        "question": "Do the most-connected scientists collaborate mainly with each other?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            f"Normalized against {n_nulls} degree-preserving rewired null graphs (nx.double_edge_swap). "
            f"Evaluated on the co-author LCC for the {n_top} researchers with degree >= k* = {k_star} "
            f"(99th percentile)."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
