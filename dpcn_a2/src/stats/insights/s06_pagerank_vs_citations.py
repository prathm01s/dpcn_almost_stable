"""Insight 6: Local PageRank Influence vs. Global Citation Impact.

Identifies 'hidden gems'—papers with disproportionate in-cluster intellectual influence
(top 5% PageRank) despite modest global citation counts (below publication year median).
"""

from typing import Dict, List
import numpy as np
import pandas as pd
import networkx as nx
from scipy.stats import spearmanr

from src.common.logging import get_logger
from src.stats.insights.common import citation_graph, papers, save_insight

logger = get_logger("insight_06")


def run() -> dict:
    logger.info("Running Insight 6: PageRank vs Global Citations...")
    G = citation_graph()
    pr = nx.pagerank(G, alpha=0.85, max_iter=100)
    in_deg = dict(G.in_degree())

    df_p = papers()
    ext_path = "data/final/group24_data_extended.csv"
    title_lookup = {}
    if pd.Series(ext_path).pipe(lambda s: pd.Path(s.iloc[0]).exists() if hasattr(pd, "Path") else True):
        df_ext = pd.read_csv(ext_path, usecols=["doi", "title"], keep_default_na=False).drop_duplicates("doi")
        title_lookup = dict(zip(df_ext["doi"], df_ext["title"]))

    p_df = df_p.set_index("doi")
    eligible_dois = [n for n in G.nodes() if in_deg[n] >= 1 and n in p_df.index]
    logger.info(f"Corpus papers with in-cluster in-degree >= 1: {len(eligible_dois)}")

    prs = np.array([pr[d] for d in eligible_dois])
    global_cites = np.array([p_df.loc[d, "citations"] for d in eligible_dois])
    years = np.array([p_df.loc[d, "year"] for d in eligible_dois])

    # Spearman rank correlation
    rho, pval = spearmanr(prs, global_cites)
    rho_val = float(rho)

    if rho_val < 0.30:
        strength_word = "weakly"
    elif rho_val <= 0.60:
        strength_word = "moderately"
    else:
        strength_word = "strongly"

    # Identify hidden gems: top 5% PR and below median global citations of pub year
    df_sub = pd.DataFrame({
        "doi": eligible_dois,
        "pr": prs,
        "cites": global_cites,
        "year": years,
        "in_deg": [in_deg[d] for d in eligible_dois],
    })
    med_by_year = df_sub.groupby("year")["cites"].transform("median")
    df_sub["median_year_cites"] = med_by_year

    pr_p95 = float(np.percentile(prs, 95))
    df_sub["is_top5_pr"] = df_sub["pr"] >= pr_p95
    df_sub["is_below_med"] = df_sub["cites"] < df_sub["median_year_cites"]
    df_sub["is_hidden_gem"] = df_sub["is_top5_pr"] & df_sub["is_below_med"]

    gems = df_sub[df_sub["is_hidden_gem"]].sort_values("pr", ascending=False)
    n_gems = len(gems)

    top5_gems = []
    for _, r in gems.head(5).iterrows():
        d = r["doi"]
        p_row = p_df.loc[d]
        top5_gems.append({
            "doi": d,
            "title": title_lookup.get(d, p_row["journal"]),
            "lab": str(p_row["labs"]),
            "year": int(p_row["year"]),
            "journal": str(p_row["journal"]),
            "in_degree": int(r["in_deg"]),
            "global_cites": int(r["cites"]),
            "pagerank": round(float(r["pr"]), 6),
        })

    headline = (
        f"In-cluster influence and global citations correlate only {strength_word} (Spearman ρ = {rho_val:.2f}). "
        f"{n_gems} papers are 'hidden gems': top-5% internal influence, below-median global citations."
    )

    # Prepare scatter data: log1p(citations) vs log(PageRank)
    gem_dois = set(gems["doi"])
    scatter_normal = []
    scatter_gems = []

    for _, r in df_sub.iterrows():
        # [x: global citations, y: pagerank]
        pt = [int(r["cites"]), round(float(r["pr"]), 7)]
        if r["doi"] in gem_dois:
            scatter_gems.append(pt)
        else:
            scatter_normal.append(pt)

    chart = {
        "type": "scatter",
        "data": {
            "xAxis": {"type": "log", "name": "Global Citations (log scale)", "min": 1},
            "yAxis": {"type": "log", "name": "In-Cluster PageRank (log scale)"},
            "series": [
                {
                    "name": "Corpus Publications",
                    "type": "scatter",
                    "data": scatter_normal,
                    "itemStyle": {"color": "#94a3b8", "opacity": 0.35},
                    "symbolSize": 5,
                },
                {
                    "name": "Hidden Gems (Top 5% PR, < Median Cites)",
                    "type": "scatter",
                    "data": scatter_gems,
                    "itemStyle": {"color": "#d97706", "opacity": 0.9},
                    "symbolSize": 8,
                },
            ],
            "top_gems_table": top5_gems,
        },
    }

    metrics = {
        "spearman_rho": round(rho_val, 3),
        "spearman_pvalue": float(pval),
        "correlation_strength": strength_word,
        "n_eligible_papers": len(eligible_dois),
        "n_hidden_gems": n_gems,
        "pr_p95_threshold": round(pr_p95, 7),
        "top5_gems": top5_gems,
    }

    data = {
        "id": "06_pagerank_vs_citations",
        "question": "Are the papers most influential inside our cluster the same as the world's most-cited?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Computed on the in-corpus citation network (alpha=0.85). Restricted to 7,627 papers with internal in-degree >= 1. "
            "Median citations are normalized by publication year."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
