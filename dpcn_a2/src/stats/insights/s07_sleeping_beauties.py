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
from src.collect.fetch_counts_by_year import CACHE_FILE
from src.stats.insights.common import not_computed, papers, save_insight

LAST_FULL_YEAR = 2025   # 2026 is partial (to Oct) and would depress late counts
MIN_TOTAL_CITES = 20
MIN_PEAK_CITES = 10     # the peak year needs real volume, so one or two citations cannot drive B

logger = get_logger("insight_07")


def compute_sleeping_beauty(pub_year: int, c_by_year: Dict[int, int]) -> dict:
    """Compute Ke et al. (2015) beauty coefficient B and awakening year over complete years."""
    years_range = list(range(pub_year, LAST_FULL_YEAR + 1))
    c_t = [c_by_year.get(y, 0) for y in years_range]
    tot_cites = sum(c_t)

    if tot_cites < MIN_TOTAL_CITES:
        return {}

    t_m = int(np.argmax(c_t))
    if t_m < 3 or c_t[t_m] < MIN_PEAK_CITES:
        return {}  # peak must come >= 3 years after publication and carry >= MIN_PEAK_CITES citations

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

    # Rates: years before awakening, and from awakening to the peak
    if t_a == 0:
        return {}  # no sleeping period
    avg_pre = sum(c_t[:t_a]) / t_a
    rise = c_t[t_a:t_m + 1]
    avg_post = sum(rise) / len(rise)
    # Sustained awakening: after the peak the paper keeps >= half its peak rate (None if the peak is the last year)
    after = c_t[t_m + 1:]
    avg_after_peak = sum(after) / len(after) if after else None
    sustained = (avg_after_peak >= 0.5 * c_t[t_m]) if after else None

    return {
        "B": float(b_val),
        "t_m": t_m,
        "peak_year": pub_year + t_m,
        "t_a": t_a,
        "awakening_year": awakening_year,
        "avg_pre": float(avg_pre),
        "avg_post": float(avg_post),
        "peak_cites": int(c_t[t_m]),
        "avg_after_peak": avg_after_peak,
        "sustained": sustained,
        "total_cites": tot_cites,
        "c_t": c_t,
        "years": years_range,
    }


def run() -> dict:
    logger.info("Running Insight 7: Sleeping Beauties...")
    question = "Which papers were ignored for years and then suddenly took off?"
    if not CACHE_FILE.exists():
        return not_computed("07_sleeping_beauties", question,
                            "OpenAlex counts_by_year cache missing (run make insights-fetch)")
    cby_data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

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
            "peak_cites": sb["peak_cites"],
            "avg_after_peak": sb["avg_after_peak"],
            "sustained": sb["sustained"],
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

    top1 = df_sb[df_sb["B"] >= b_p99]
    n_sustained = int((top1["sustained"] == True).sum())  # noqa: E712 (None = peak in last year)
    n_spikes = int((top1["sustained"] == False).sum())  # noqa: E712

    def short(t: str) -> str:
        return t if len(t) <= 70 else t[:67].rstrip() + "…"

    sus = top1[top1["sustained"] == True]  # noqa: E712
    if n_sustained == 0:
        after = strongest["avg_after_peak"]
        after_txt = f" and fell back to {after:.1f}/yr" if after is not None else ""
        headline = (
            f"No sustained 'sleeping beauties': {n_spikes} of the {top1_count} strongest candidates (top 1% of "
            f"{n_eligible} papers by Ke's B) are 1–2-year citation spikes. The top one, '{short(strongest['title'])}' "
            f"({strongest['lab'].replace('CSIR-', '')}, {strongest['year']}), drew {strongest['avg_pre']:.1f} "
            f"citations/yr for {t_years} years, peaked at {strongest['peak_cites']} in {strongest['peak_year']}{after_txt}."
        )
    else:
        best = sus.iloc[0]
        headline = (
            f"{n_sustained} of the {top1_count} strongest candidates (top 1% of {n_eligible} papers by Ke's B) show "
            f"sustained delayed recognition. The strongest, '{short(best['title'])}' "
            f"({best['lab'].replace('CSIR-', '')}, {best['year']}), drew {best['avg_pre']:.1f} citations/yr for "
            f"{best['t_a']} years, then {best['avg_post']:.1f}/yr from {best['awakening_year']}."
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
            "xAxis": {"type": "category", "data": list(range(2016, LAST_FULL_YEAR + 1)), "name": "Year"},
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
        "n_top1_sustained": n_sustained,
        "n_top1_spikes": n_spikes,
        "strongest": {
            "title": str(strongest["title"]),
            "lab": str(strongest["lab"]),
            "year": int(strongest["year"]),
            "B": round(float(strongest["B"]), 2),
            "t_a": int(strongest["t_a"]),
            "awakening_year": int(strongest["awakening_year"]),
            "avg_pre": round(float(strongest["avg_pre"]), 2),
            "avg_post": round(float(strongest["avg_post"]), 2),
            "peak_cites": int(strongest["peak_cites"]),
            "peak_year": int(strongest["peak_year"]),
            "avg_after_peak": (round(float(strongest["avg_after_peak"]), 2)
                               if strongest["avg_after_peak"] is not None else None),
            "sustained": strongest["sustained"],
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
            f"Ke et al. (2015, PNAS) beauty coefficient B on yearly citations (OpenAlex counts_by_year, 2016–{LAST_FULL_YEAR}) of "
            f"papers published 2016–2020 with ≥{MIN_TOTAL_CITES} citations, a peak ≥3 years after publication and "
            f"≥{MIN_PEAK_CITES} citations in the peak year. Sustained = after the peak the paper keeps ≥50% of its "
            f"peak yearly citations. The ≤10-year window only captures short sleeps."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
