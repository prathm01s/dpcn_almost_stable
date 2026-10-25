"""Insight 4: Price's Law and Scientific Inequality.

Evaluates Lotka/Price's law of productivity (√N scientists produce 50% of papers)
and computes Gini inequality coefficients for publications and citations.
"""

import math
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.stats.insights.common import faculty, save_insight

logger = get_logger("insight_04")


def gini(arr: np.ndarray) -> float:
    """Compute Gini coefficient of a non-negative 1D array."""
    y = np.sort(arr)
    n = len(y)
    total = float(np.sum(y))
    if n == 0 or total == 0:
        return 0.0
    return float(np.sum((2 * np.arange(1, n + 1) - n - 1) * y) / (n * total))


def run() -> dict:
    logger.info("Running Insight 4: Price's Law & Inequality...")
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    df_fac = faculty()
    matched_fids = set(df_fac[df_fac["is_matched"]]["author_id"])

    # Faculty papers
    fac_rows = df_ext[df_ext["faculty_id"].isin(matched_fids)].copy()
    grouped = fac_rows.groupby("faculty_id")

    all_fac_papers = set()
    fac_stats = []
    for fid, g in grouped:
        p_set = set(g["work_id"])
        all_fac_papers.update(p_set)
        distinct_p = g.drop_duplicates("work_id")
        c_sum = int(pd.to_numeric(distinct_p["citations"], errors="coerce").fillna(0).sum())
        fac_stats.append({
            "faculty_id": fid,
            "n_papers": len(p_set),
            "citations": c_sum,
            "papers": p_set,
        })

    df_active = pd.DataFrame(fac_stats).sort_values("n_papers", ascending=False).reset_index(drop=True)
    N = len(df_active)
    total_faculty_papers = len(all_fac_papers)

    # Price's law: top ceil(sqrt(N)) scientists
    n_sqrt = math.ceil(math.sqrt(N))
    top_sqrt_papers = set().union(*df_active.iloc[:n_sqrt]["papers"])
    price_share = (len(top_sqrt_papers) / total_faculty_papers) * 100

    # Top 10% scientists
    n_top10 = math.ceil(0.10 * N)
    top10_papers = set().union(*df_active.iloc[:n_top10]["papers"])
    top10_share = (len(top10_papers) / total_faculty_papers) * 100

    # Gini coefficients
    paper_counts = df_active["n_papers"].values
    citation_counts = df_active["citations"].values
    g_papers = gini(paper_counts)
    g_citations = gini(citation_counts)

    headline = (
        f"√N = {n_sqrt} scientists produce {price_share:.1f}% of the cluster's papers (Price's law predicts 50%). "
        f"The top 10% produce {top10_share:.1f}%; Gini = {g_papers:.2f} (papers), {g_citations:.2f} (citations)."
    )

    # Lorenz curve (cumulative share of scientists vs cumulative share of papers)
    # Sorted ascending for Lorenz curve
    sorted_papers = np.sort(paper_counts)
    cum_scientists = np.linspace(0, 1, N + 1)
    cum_papers = np.concatenate(([0.0], np.cumsum(sorted_papers) / np.sum(sorted_papers)))

    lorenz_data = [
        [round(float(cum_scientists[i]), 4), round(float(cum_papers[i]), 4)]
        for i in range(N + 1)
    ]
    equality_line = [[0.0, 0.0], [1.0, 1.0]]

    # Sqrt(N) point on the Lorenz curve
    # Fraction of scientists from bottom = 1 - (n_sqrt / N)
    sqrt_x = 1.0 - (n_sqrt / N)
    idx_sqrt = int(round(sqrt_x * N))
    sqrt_y = float(cum_papers[idx_sqrt])

    chart = {
        "type": "line",
        "data": {
            "xAxis": {"type": "value", "name": "Cumulative share of scientists", "min": 0, "max": 1.0},
            "yAxis": {"type": "value", "name": "Cumulative share of publications", "min": 0, "max": 1.0},
            "series": [
                {
                    "name": "Lorenz Curve (Papers)",
                    "type": "line",
                    "data": lorenz_data,
                    "itemStyle": {"color": "#4a148c"},
                    "lineStyle": {"width": 2.5},
                    "smooth": True,
                },
                {
                    "name": "Line of Perfect Equality",
                    "type": "line",
                    "data": equality_line,
                    "itemStyle": {"color": "#94a3b8"},
                    "lineStyle": {"type": "dashed", "width": 1.5},
                    "symbol": "none",
                },
            ],
            "markPoint": {
                "name": "√N Threshold",
                "coord": [round(sqrt_x, 4), round(sqrt_y, 4)],
                "label": f"Top √N ({n_sqrt})",
            },
        },
    }

    metrics = {
        "N_active_faculty": N,
        "n_sqrt": n_sqrt,
        "price_share_pct": round(price_share, 2),
        "top10_percent_count": n_top10,
        "top10_share_pct": round(top10_share, 2),
        "gini_papers": round(g_papers, 3),
        "gini_citations": round(g_citations, 3),
        "total_faculty_papers": total_faculty_papers,
    }

    data = {
        "id": "04_price_law",
        "question": "Is output concentrated in a few scientists?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            f"Population: {N} active roster faculty with ≥1 paper (2016–2026). "
            f"Union counting is used for collaborative output. Price's law predicts √N produce 50%."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
