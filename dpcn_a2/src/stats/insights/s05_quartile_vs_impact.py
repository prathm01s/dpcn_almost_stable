"""Insight 5: Journal Quartile vs. Citation Impact.

Evaluates whether publishing in a SCImago Q1 journal guarantees high citations,
analyzing top-10% papers (within-year normalized) and uncited rates across 2016–2023.
"""

from typing import Dict, List
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.stats.insights.common import papers, save_insight

logger = get_logger("insight_05")


def run() -> dict:
    logger.info("Running Insight 5: Quartile vs Impact...")
    df = papers()

    # Filter to journal papers, publication years 2016-2023, ranked quartiles
    mask = (
        (df["type"] == "journal")
        & (df["year"] >= 2016)
        & (df["year"] <= 2023)
        & (df["quartile"].isin(["Q1", "Q2", "Q3", "Q4"]))
    )
    df_j = df[mask].copy()
    n_total = len(df_j)
    logger.info(f"Eligible ranked journal papers (2016–2023): {n_total}")

    # Top-10% threshold within publication year (90th percentile)
    p90_by_year = df_j.groupby("year")["citations"].transform(lambda s: np.percentile(s, 90))
    df_j["is_top10"] = df_j["citations"] >= p90_by_year
    df_j["is_uncited"] = df_j["citations"] == 0
    df_j["is_mid"] = (~df_j["is_uncited"]) & (~df_j["is_top10"])

    # Metrics
    top10_papers = df_j[df_j["is_top10"]]
    pct_top10_from_nonQ1 = float((top10_papers["quartile"] != "Q1").mean() * 100)

    q1_papers = df_j[df_j["quartile"] == "Q1"]
    pct_Q1_uncited = float((q1_papers["citations"] == 0).mean() * 100)

    q2q3_papers = df_j[df_j["quartile"].isin(["Q2", "Q3"])]
    pct_Q2Q3_in_top10 = float(q2q3_papers["is_top10"].mean() * 100)

    headline = (
        f"{pct_top10_from_nonQ1:.1f}% of the cluster's top-10% most-cited papers were published outside Q1 journals, "
        f"while {pct_Q1_uncited:.1f}% of Q1 papers are still uncited."
    )

    # Breakdown per quartile for 100% stacked bar chart
    quartiles = ["Q1", "Q2", "Q3", "Q4"]
    uncited_pcts = []
    mid_pcts = []
    top10_pcts = []
    counts_by_quartile = {}

    for q in quartiles:
        sub = df_j[df_j["quartile"] == q]
        n_q = len(sub)
        counts_by_quartile[q] = n_q
        if n_q > 0:
            uncited_pcts.append(round(float(sub["is_uncited"].sum() / n_q * 100), 2))
            mid_pcts.append(round(float(sub["is_mid"].sum() / n_q * 100), 2))
            top10_pcts.append(round(float(sub["is_top10"].sum() / n_q * 100), 2))
        else:
            uncited_pcts.append(0.0)
            mid_pcts.append(0.0)
            top10_pcts.append(0.0)

    chart = {
        "type": "stacked_bar",
        "data": {
            "xAxis": {"type": "category", "data": [f"{q} (n={counts_by_quartile[q]:,})" for q in quartiles]},
            "yAxis": {"type": "value", "name": "Share of publications (%)", "min": 0, "max": 100},
            "legend": {"data": ["Uncited (0 citations)", "Cited (not top-10%)", "Top 10% Most Cited"], "bottom": 0},
            "series": [
                {
                    "name": "Uncited (0 citations)",
                    "type": "bar",
                    "stack": "total",
                    "data": uncited_pcts,
                    "itemStyle": {"color": "#ef4444"},
                },
                {
                    "name": "Cited (not top-10%)",
                    "type": "bar",
                    "stack": "total",
                    "data": mid_pcts,
                    "itemStyle": {"color": "#3b82f6"},
                },
                {
                    "name": "Top 10% Most Cited",
                    "type": "bar",
                    "stack": "total",
                    "data": top10_pcts,
                    "itemStyle": {"color": "#10b981"},
                },
            ],
        },
    }

    metrics = {
        "pct_top10_from_nonQ1": round(pct_top10_from_nonQ1, 2),
        "pct_Q1_uncited": round(pct_Q1_uncited, 2),
        "pct_Q2Q3_in_top10": round(pct_Q2Q3_in_top10, 2),
        "eligible_papers": n_total,
        "counts_by_quartile": counts_by_quartile,
    }

    data = {
        "id": "05_quartile_vs_impact",
        "question": "Is a Q1 journal a reliable signal of a highly cited paper?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Evaluated on 10,212 journal papers (2016–2023; 2024–2026 excluded due to citation latency). "
            "Top-10% citation thresholds are normalized within each publication year."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
