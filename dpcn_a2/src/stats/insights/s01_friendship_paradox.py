"""Insight 1: Co-authorship Friendship Paradox.

Evaluates whether researchers' collaborators have, on average, more collaborators
than they do (Feld 1991), comparing <k> with <k^2>/<k>.
"""

import numpy as np
import networkx as nx

from src.common.logging import get_logger
from src.stats.insights.common import coauthor_graph, save_insight

logger = get_logger("insight_01")


def run() -> dict:
    logger.info("Running Insight 1: Friendship Paradox...")
    G = coauthor_graph()
    n_nodes = G.number_of_nodes()

    # Degree and Average Neighbor Degree
    deg = dict(G.degree())
    knn = nx.average_neighbor_degree(G)

    k_arr = np.array([deg[n] for n in G.nodes()])
    knn_arr = np.array([knn[n] for n in G.nodes()])
    fac_flags = np.array([G.nodes[n].get("is_faculty", False) for n in G.nodes()])

    # Paradox: knn_i > k_i
    paradox_all = knn_arr > k_arr
    share_paradox = float(np.mean(paradox_all) * 100)

    # Faculty subset
    fac_indices = np.where(fac_flags)[0]
    n_faculty = len(fac_indices)
    if n_faculty > 0:
        fac_share_paradox = float(np.mean(knn_arr[fac_indices] > k_arr[fac_indices]) * 100)
    else:
        fac_share_paradox = share_paradox

    mean_k = float(np.mean(k_arr))
    mean_k2 = float(np.mean(k_arr ** 2))
    mean_neighbour_k = float(mean_k2 / mean_k) if mean_k > 0 else 0.0

    headline = (
        f"{share_paradox:.1f}% of researchers have fewer co-authors than their co-authors do. "
        f"The average researcher has {mean_k:.1f} co-authors, but the average co-author has {mean_neighbour_k:.1f}."
    )

    # Prepare chart data for ECharts (log-log scatter with faculty highlight)
    # Bin / sort or separate into faculty vs others
    scatter_other = []
    scatter_faculty = []
    for i, node in enumerate(G.nodes()):
        pt = [round(float(k_arr[i]), 1), round(float(knn_arr[i]), 1)]
        if fac_flags[i]:
            scatter_faculty.append(pt)
        else:
            scatter_other.append(pt)

    max_val = max(int(np.max(k_arr)), int(np.max(knn_arr)))
    ref_line = [[1, 1], [max_val, max_val]]

    chart = {
        "type": "scatter",
        "data": {
            "xAxis": {"type": "log", "name": "Degree k (own co-authors)", "min": 1, "max": max_val},
            "yAxis": {"type": "log", "name": "Neighbor Degree knn (co-authors' average)", "min": 1, "max": max_val},
            "series": [
                {
                    "name": "Affiliated Researchers",
                    "type": "scatter",
                    "data": scatter_other,
                    "itemStyle": {"color": "#94a3b8", "opacity": 0.4},
                    "symbolSize": 5,
                },
                {
                    "name": "Roster Faculty",
                    "type": "scatter",
                    "data": scatter_faculty,
                    "itemStyle": {"color": "#4a148c", "opacity": 0.85},
                    "symbolSize": 8,
                },
                {
                    "name": "Equality Line (k = knn)",
                    "type": "line",
                    "data": ref_line,
                    "itemStyle": {"color": "#dc2626"},
                    "lineStyle": {"type": "dashed", "width": 1.5},
                    "symbol": "none",
                },
            ],
        },
    }

    metrics = {
        "share_paradox": round(share_paradox, 2),
        "faculty_share_paradox": round(fac_share_paradox, 2),
        "mean_k": round(mean_k, 2),
        "mean_neighbour_k": round(mean_neighbour_k, 2),
        "n_nodes": n_nodes,
        "n_faculty": n_faculty,
    }

    data = {
        "id": "01_friendship_paradox",
        "question": "Do our researchers' co-authors have more co-authors than they do?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Computed on the co-authorship largest connected component (7,508 researchers). "
            "Neighbor degree is the unweighted average degree of all direct co-authors."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
