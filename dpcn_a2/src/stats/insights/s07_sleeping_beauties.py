"""Insight 7: Sleeping Beauties in Science.

Identifies publications that received little initial recognition followed by a sudden
surge in citations, implementing the Ke et al. (2015, PNAS) beauty coefficient B.
"""

import json
from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.collect.fetch_counts_by_year import fetch_counts_by_year
from src.stats.insights.common import papers, save_insight

logger = get_logger("insight_07")


def compute_sleeping_beauty(pub_year: int, c_by_year: Dict[int, int]) -> dict:
    """Compute Ke et al. (2015) beauty coefficient B and awakening year."""
    years_range = list(range(pub_year, 2027))
    c_t = [c_by_year.get(y, 0) for y in years_range]
    tot_cites = sum(c_t)

    if tot_cites < 20:
        return {}

    t_m = int(np.argmax(c_t))
    if t_m < 3:
        return {}  # Peak citation must be >= 3 years after publication

    c_0 = c_t[0]
    c_tm = c_t[t_m]
    slope = (c_tm - c_0) / t_m

    b_val = 0.0
    dists = []
    for t in range(t_m + 1):
        chord_y = slope * t + c_0
        b_term = (chord_y - c_t[t]) / max(1, c_t[t])
        b_val += b_term
        dists.append(chord_y - c_t[t])

    if b_val <= 0:
        return {}

    t_a = int(np.argmax(dists))
    awakening_year = pub_year + t_a

    # Pre-awakening rate
    pre_years = max(1, t_a)
    pre_cites = sum(c_t[:t_a]) if t_a > 0 else c_t[0]
    avg_pre = pre_cites / pre_years

    # Post-awakening rate
    post_cites = c_t[t_a:]
    avg_post = sum(post_cites) / len(post_cites) if post_cites else 0.0

    return {
        "B": float(b_val),
        "t_m": t_m,
        "peak_year": pub_year + t_m,
        "t_a": t_a,
        "awakening_year": awakening_year,
        "avg_pre": float(avg_pre),
        "avg_post": float(avg_post),
        "total_cites": tot_cites,
        "c_t": c_t,
        "years": years_range,
    }


def run() -> dict:
    logger.info("Running Insight 7: Sleeping Beauties...")
    # Load cached counts_by_year
    cby_data = fetch_counts_by_year()
    if not cby_data:
        data = {
            "id": "07_sleeping_beauties",
            "question": "Which papers were ignored for years and then suddenly took off?",
            "headline": "Not computed – counts_by_year cache missing.",
            "metrics": {},
            "chart": {"type": "line", "data": {}},
            "method_note": "Requires OpenAlex counts_by_year API cache.",
        }
        save_insight(data)
        return data

    df_p = papers().set_index("work_id")
    ext_path = "data/final/group24_data_extended.csv"
    title_lookup = {}
    if Path(ext_path).exists():
        df_ext = pd.read_csv(ext_path, usecols=["work_id", "title"], keep_default_na=False).drop_duplicates("work_id")
        title_lookup = dict(zip(df_ext["work_id"], df_ext["title"]))

    results = []
    for wid, cby in cby_data.items():
        if wid not in df_p.index:
            continue
        p_info = df_p.loc[wid]
        pub_yr = int(p_info["year"])
        if not (2016 <= pub_yr <= 2020):
            continue

        c_by_y = {item["year"]: item["cited_by_count"] for item in cby}
        sb = compute_sleeping_beauty(pub_yr, c_by_y)
        if not sb:
            continue

        results.append({
            "work_id": wid,
            "doi": str(p_info["doi"]),
            "title": title_lookup.get(wid, str(p_info["journal"])),
            "lab": str(p_info["labs"]),
            "journal": str(p_info["journal"]),
            "year": pub_yr,
            "B": sb["B"],
            "t_m": sb["t_m"],
            "peak_year": sb["peak_year"],
            "t_a": sb["t_a"],
            "awakening_year": sb["awakening_year"],
            "avg_pre": sb["avg_pre"],
            "avg_post": sb["avg_post"],
            "total_cites": sb["total_cites"],
            "c_t": sb["c_t"],
            "years": sb["years"],
        })

    df_sb = pd.DataFrame(results).sort_values("B", ascending=False)
    n_eligible = len(df_sb)
    logger.info(f"Identified {n_eligible} qualifying sleeping beauties with B > 0")

    b_p99 = float(np.percentile(df_sb["B"], 99))
    top1_count = int((df_sb["B"] >= b_p99).sum())

    top5 = df_sb.head(5).copy()
    strongest = top5.iloc[0]

    # Pre-awakening duration
    t_years = strongest["t_a"]

    headline = (
        f"{top1_count} papers show delayed recognition. The strongest, '{strongest['title']}' "
        f"({strongest['lab']}, {strongest['year']}), averaged {strongest['avg_pre']:.1f} citations/yr for {t_years} years, "
        f"then jumped to {strongest['avg_post']:.1f}/yr from {strongest['awakening_year']}."
    )

    # Chart data: multi-line of the top 5
    colors = ["#4a148c", "#0284c7", "#10b981", "#f59e0b", "#ef4444"]
    chart_series = []
    top5_table = []

    for idx, (_, r) in enumerate(top5.iterrows()):
        line_data = [[y, r["c_t"][i]] for i, y in enumerate(r["years"])]
        chart_series.append({
            "name": f"{r['title'][:40]}... ({r['year']})",
            "type": "line",
            "data": line_data,
            "itemStyle": {"color": colors[idx % len(colors)]},
            "lineStyle": {"width": 2},
            "markPoint": {
                "data": [
                    {
                        "name": "Awakening",
                        "coord": [r["awakening_year"], r["c_t"][r["t_a"]]],
                        "symbol": "pin",
                        "symbolSize": 30,
                        "label": {"show": False},
                    }
                ]
            },
        })
        top5_table.append({
            "title": str(r["title"]),
            "lab": str(r["lab"]),
            "journal": str(r["journal"]),
            "year": int(r["year"]),
            "doi": str(r["doi"]),
            "B": round(float(r["B"]), 2),
            "awakening_year": int(r["awakening_year"]),
            "total_citations": int(r["total_cites"]),
        })

    chart = {
        "type": "line",
        "data": {
            "xAxis": {"type": "category", "data": list(range(2016, 2027)), "name": "Year"},
            "yAxis": {"type": "value", "name": "Annual Citations"},
            "legend": {"bottom": 0},
            "series": chart_series,
            "top5_table": top5_table,
        },
    }

    metrics = {
        "n_top1_percent": top1_count,
        "b_p99_threshold": round(b_p99, 2),
        "n_eligible_sleeping_beauties": n_eligible,
        "strongest": {
            "title": str(strongest["title"]),
            "lab": str(strongest["lab"]),
            "year": int(strongest["year"]),
            "B": round(float(strongest["B"]), 2),
            "t_a": int(strongest["t_a"]),
            "awakening_year": int(strongest["awakening_year"]),
            "avg_pre": round(float(strongest["avg_pre"]), 2),
            "avg_post": round(float(strongest["avg_post"]), 2),
            "total_citations": int(strongest["total_cites"]),
        },
        "top5": top5_table,
    }

    data = {
        "id": "07_sleeping_beauties",
        "question": "Which papers were ignored for years and then suddenly took off?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Computed using the Ke et al. (2015, PNAS) parameter-free B coefficient on papers published 2016–2020 with >=20 citations. "
            "Note: The 10-year observation window only captures short sleeps."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
