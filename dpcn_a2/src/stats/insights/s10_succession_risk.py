"""Insight 10: Succession and Retirement Exposure Risk.

Quantifies institutional dependency on senior faculty nearing CSIR superannuation
(academic age >= 30, with sensitivity at 28 and 32), evaluating recent papers (2021–2025)
led solely by senior researchers.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from src.common.logging import get_logger
from src.stats.insights.common import faculty, papers, LABS, not_computed, save_insight

QUESTION = "How much of each lab's output depends on scientists close to retirement?"

logger = get_logger("insight_10")

CAREERS_DIR = Path("data/cache/openalex/careers")


def run() -> dict:
    logger.info("Running Insight 10: Succession Risk...")
    if not CAREERS_DIR.exists() or not any(CAREERS_DIR.glob("*.json")):
        return not_computed("10_succession_risk", QUESTION, "OpenAlex career cache missing (run make insights-fetch)")
    df_fac = faculty()
    matched = df_fac[df_fac["is_matched"]].copy()

    # Determine academic age per matched faculty
    age_map = {}
    for _, r in matched.iterrows():
        raw_aid = r["openalex_author_id"]
        if not raw_aid:
            continue
        clean_aid = raw_aid.split("/")[-1]
        c_path = CAREERS_DIR / f"{clean_aid}.json"
        if not c_path.exists():
            continue
        with open(c_path, "r", encoding="utf-8") as f:
            timeline = json.load(f)
        years = [e.get("year") for e in timeline if e.get("year")]
        if years:
            first_year = min(years)
            age_map[r["author_id"]] = 2026 - first_year

    logger.info(f"Resolved academic age for {len(age_map)} faculty members")

    # Focus on distinct papers 2021–2025
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    p_recent = df_ext[(df_ext["year"] >= 2021) & (df_ext["year"] <= 2025)].copy()

    # Compute risk metrics across sensitivity thresholds: 28, 30, 32
    thresholds = [28, 30, 32]
    lab_metrics = {}

    for lab in LABS:
        sub = p_recent[p_recent["institution"] == lab].copy()
        grouped = sub.groupby("work_id")

        lab_metrics[lab] = {}
        for T in thresholds:
            n_tot = 0
            n_any = 0
            n_sole = 0
            c_tot = 0
            c_any = 0
            c_sole = 0

            for wid, g in grouped:
                fac_in_paper = [fid for fid in g["faculty_id"].unique() if fid in age_map]
                if not fac_in_paper:
                    continue

                n_tot += 1
                distinct_row = g.iloc[0]
                c = int(distinct_row["citations"]) if str(distinct_row["citations"]).isdigit() else 0
                c_tot += c

                at_risk_fac = [fid for fid in fac_in_paper if age_map[fid] >= T]
                if len(at_risk_fac) >= 1:
                    n_any += 1
                    c_any += c
                if len(at_risk_fac) == len(fac_in_paper):
                    n_sole += 1
                    c_sole += c

            lab_metrics[lab][T] = {
                "total_papers": n_tot,
                "total_citations": c_tot,
                "share_any_papers": round(float(n_any / n_tot * 100), 2) if n_tot else 0.0,
                "share_sole_papers": round(float(n_sole / n_tot * 100), 2) if n_tot else 0.0,
                "share_any_citations": round(float(c_any / c_tot * 100), 2) if c_tot else 0.0,
                "share_sole_citations": round(float(c_sole / c_tot * 100), 2) if c_tot else 0.0,
            }

    # Department / Division with highest share_sole at T=30 (minimum 20 papers)
    div_stats = []
    for div, g_div in p_recent[p_recent["department"] != ""].groupby("department"):
        grouped = g_div.groupby("work_id")
        n_tot = 0
        n_sole = 0
        for wid, g in grouped:
            facs = [fid for fid in g["faculty_id"].unique() if fid in age_map]
            if not facs:
                continue
            n_tot += 1
            if all(age_map[fid] >= 30 for fid in facs):
                n_sole += 1
        if n_tot >= 20:
            div_stats.append({
                "division": div,
                "lab": g_div.iloc[0]["institution"],
                "total_papers": n_tot,
                "sole_papers": n_sole,
                "share_sole": round(float(n_sole / n_tot * 100), 2),
            })

    df_div = pd.DataFrame(div_stats).sort_values("share_sole", ascending=False)
    top_div = df_div.iloc[0]

    div_label = str(top_div["division"]).title() if str(top_div["division"]).isupper() else str(top_div["division"])
    div_label = div_label.replace(" And ", " and ").replace(" Of ", " of ")
    # Highlight the lab with the highest share of papers whose only roster authors are at risk
    highlight_lab = max(LABS, key=lambda l: lab_metrics[l][30]["share_sole_papers"])
    h_data = lab_metrics[highlight_lab][30]
    others = ", ".join(f"{l.replace('CSIR-', '')} {lab_metrics[l][30]['share_sole_papers']:.1f}%"
                       for l in LABS if l != highlight_lab)

    headline = (
        f"In {highlight_lab.replace('CSIR-', '')}, {h_data['share_sole_papers']:.1f}% of recent papers "
        f"({h_data['share_sole_citations']:.1f}% of their citations) have only roster authors likely to retire within "
        f"~5 years ({others}). Highest exposure: {div_label}, {top_div['lab'].replace('CSIR-', '')} "
        f"({top_div['share_sole']:.1f}% of {int(top_div['total_papers'])} papers)."
    )

    # Chart construction: Grouped bar per lab (share_sole papers vs citations at T=30) with T=28/32 range
    categories = LABS
    papers_bar = [lab_metrics[lab][30]["share_sole_papers"] for lab in categories]
    cites_bar = [lab_metrics[lab][30]["share_sole_citations"] for lab in categories]

    # Whiskers [low (T=32), high (T=28)]
    papers_range = [
        [lab_metrics[lab][32]["share_sole_papers"], lab_metrics[lab][28]["share_sole_papers"]]
        for lab in categories
    ]
    cites_range = [
        [lab_metrics[lab][32]["share_sole_citations"], lab_metrics[lab][28]["share_sole_citations"]]
        for lab in categories
    ]

    chart = {
        "type": "grouped_bar",
        "data": {
            "xAxis": {"type": "category", "data": categories},
            "yAxis": {"type": "value", "name": "Share of recent output (%)"},
            "legend": {"data": ["Papers with only at-risk roster authors", "Citations of those papers"], "bottom": 0},
            "series": [
                {
                    "name": "Papers with only at-risk roster authors",
                    "type": "bar",
                    "data": papers_bar,
                    "itemStyle": {"color": "#2563eb"},
                    "error_range": papers_range,
                },
                {
                    "name": "Citations of those papers",
                    "type": "bar",
                    "data": cites_bar,
                    "itemStyle": {"color": "#dc2626"},
                    "error_range": cites_range,
                },
            ],
            "sensitivity_table": {
                lab: {
                    f"T_{t}": lab_metrics[lab][t] for t in thresholds
                }
                for lab in LABS
            },
        },
    }

    metrics = {
        "threshold_used": 30,
        "highlight_lab": highlight_lab,
        "n_scientists_with_age": len(age_map),
        "sensitivity_thresholds": [28, 30, 32],
        "lab_metrics": lab_metrics,
        "top_exposed_division": {
            "division": str(top_div["division"]),
            "lab": str(top_div["lab"]),
            "total_papers": int(top_div["total_papers"]),
            "sole_papers": int(top_div["sole_papers"]),
            "share_sole_pct": float(top_div["share_sole"]),
        },
        "all_exposed_divisions": div_stats[:10],
    }

    data = {
        "id": "10_succession_risk",
        "question": QUESTION,
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            f"Distinct 2021–2025 papers with ≥1 matched roster author ({len(age_map)} scientists with career data). "
            "Academic age = 2026 − first OpenAlex publication year; at risk = age ≥30, a proxy for ≤~5 years to CSIR "
            "superannuation at 60 (no birth dates available). Divisions with ≥20 papers. Tooltips show thresholds 28 and 32."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
