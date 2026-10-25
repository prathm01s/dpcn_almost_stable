"""Insight 8: COVID Shock on Output and Thematic Direction.

Quantifies the pandemic output gap against 2016–2019 pre-pandemic linear trends,
evaluates COVID-related chemical/antiviral synthesis research volume,
and measures structural subfield redistribution via Jensen-Shannon divergence.
"""

import re
from typing import Dict, List
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from src.common.logging import get_logger
from src.stats.insights.common import papers, LABS, save_insight

logger = get_logger("insight_08")


def run() -> dict:
    logger.info("Running Insight 8: COVID Shock...")
    df = papers()
    ext_path = "data/final/group24_data_extended.csv"
    df_ext = pd.read_csv(ext_path, usecols=["work_id", "title", "primary_topic", "subfield"], keep_default_na=False).drop_duplicates("work_id").set_index("work_id")

    years_all = list(range(2016, 2026))  # 2016-2025 full years
    years_pre = [2016, 2017, 2018, 2019]

    # 1. Output gap: Combined and per lab
    counts_comb = [len(df[df["year"] == y]) for y in years_pre]
    slope_c, int_c = np.polyfit(years_pre, counts_comb, 1)
    pred_2020_c = slope_c * 2020 + int_c
    pred_2021_c = slope_c * 2021 + int_c
    act_2020_c = len(df[df["year"] == 2020])
    act_2021_c = len(df[df["year"] == 2021])

    gap_2020_c = ((act_2020_c - pred_2020_c) / pred_2020_c) * 100
    gap_2021_c = ((act_2021_c - pred_2021_c) / pred_2021_c) * 100

    lab_gaps = {}
    lab_actuals = {}
    lab_projections = {}

    for lab in LABS:
        sub = df[df["labs"].str.contains(lab)]
        counts_lab = [len(sub[sub["year"] == y]) for y in years_pre]
        slope, intercept = np.polyfit(years_pre, counts_lab, 1)
        p20 = slope * 2020 + intercept
        p21 = slope * 2021 + intercept
        a20 = len(sub[sub["year"] == 2020])
        a21 = len(sub[sub["year"] == 2021])
        lab_gaps[lab] = {
            "slope": round(float(slope), 2),
            "pred_2020": round(float(p20), 1),
            "act_2020": a20,
            "gap_2020_pct": round(float((a20 - p20) / p20 * 100), 2),
            "pred_2021": round(float(p21), 1),
            "act_2021": a21,
            "gap_2021_pct": round(float((a21 - p21) / p21 * 100), 2),
        }
        lab_actuals[lab] = [len(sub[sub["year"] == y]) for y in years_all]
        lab_projections[lab] = [round(float(slope * y + intercept), 1) for y in [2020, 2021]]

    # 2. Topic Shift: match COVID keywords
    covid_regex = re.compile(r"covid|sars-cov-2|coronavirus|pandemic|antiviral|favipiravir|remdesivir", re.I)

    df["search_text"] = df["work_id"].map(
        lambda wid: (
            f"{df_ext.loc[wid, 'title']} {df_ext.loc[wid, 'primary_topic']} {df_ext.loc[wid, 'subfield']}"
            if wid in df_ext.index else ""
        )
    )
    df["is_covid"] = df["search_text"].str.contains(covid_regex)

    covid_records = []
    for lab in LABS:
        sub = df[df["labs"].str.contains(lab) & df["year"].isin([2020, 2021, 2022])]
        for y in [2020, 2021, 2022]:
            y_sub = sub[sub["year"] == y]
            n_y = len(y_sub)
            n_cov = int(y_sub["is_covid"].sum())
            share = (n_cov / n_y * 100) if n_y > 0 else 0.0
            covid_records.append({
                "lab": lab,
                "year": y,
                "share": round(share, 2),
                "covid_papers": n_cov,
                "total_papers": n_y,
            })

    df_cov = pd.DataFrame(covid_records).sort_values("share", ascending=False)
    top_cov = df_cov.iloc[0]

    # 3. Structural Shift: Jensen-Shannon Divergence
    def subfield_vector(years: List[int], all_subfields: List[str]) -> np.ndarray:
        sub = df[df["year"].isin(years) & (df["subfield"] != "")]
        counts = sub["subfield"].value_counts()
        vec = counts.reindex(all_subfields, fill_value=0).values.astype(float)
        tot = vec.sum()
        return (vec / tot) if tot > 0 else vec

    all_subfields = sorted(set(df[df["subfield"] != ""]["subfield"]))
    p_16_17 = subfield_vector([2016, 2017], all_subfields)
    p_18_19 = subfield_vector([2018, 2019], all_subfields)
    p_20_21 = subfield_vector([2020, 2021], all_subfields)

    jsd_baseline = float(jensenshannon(p_16_17, p_18_19))
    jsd_shock = float(jensenshannon(p_18_19, p_20_21))
    jsd_ratio = float(jsd_shock / jsd_baseline) if jsd_baseline > 0 else 1.0

    dir_20 = "above" if gap_2020_c >= 0 else "below"
    dir_21 = "above" if gap_2021_c >= 0 else "below"

    headline = (
        f"Output was {abs(gap_2020_c):.1f}% {dir_20} trend in 2020 and {abs(gap_2021_c):.1f}% {dir_21} in 2021. "
        f"COVID-related work peaked at {top_cov['share']:.1f}% of {top_cov['lab']}'s papers in {int(top_cov['year'])}; "
        f"the topic mix shifted {jsd_ratio:.2f}× more than in a normal period."
    )

    # Chart construction: actual papers per lab (2016–2025) + dashed projection 2020–2021
    lab_colors = {
        "CSIR-IICT": "#2b5c8f",
        "CSIR-NCL": "#2e7d32",
        "CSIR-CECRI": "#d95f02",
    }
    series_list = []
    for lab in LABS:
        # Actual line
        series_list.append({
            "name": f"{lab} (Actual)",
            "type": "line",
            "data": [[y, lab_actuals[lab][i]] for i, y in enumerate(years_all)],
            "itemStyle": {"color": lab_colors[lab]},
            "lineStyle": {"width": 2},
            "smooth": True,
        })
        # Projected trend segment (2020-2021)
        series_list.append({
            "name": f"{lab} (Projected Trend)",
            "type": "line",
            "data": [[2020, lab_projections[lab][0]], [2021, lab_projections[lab][1]]],
            "itemStyle": {"color": lab_colors[lab]},
            "lineStyle": {"width": 2, "type": "dashed"},
            "symbol": "circle",
        })

    chart = {
        "type": "line",
        "data": {
            "xAxis": {"type": "category", "data": years_all, "name": "Year"},
            "yAxis": {"type": "value", "name": "Annual Distinct Papers"},
            "legend": {"bottom": 0},
            "series": series_list,
        },
    }

    metrics = {
        "combined_gap_2020_pct": round(gap_2020_c, 2),
        "combined_gap_2021_pct": round(gap_2021_c, 2),
        "lab_gaps": lab_gaps,
        "covid_peak": {
            "lab": str(top_cov["lab"]),
            "year": int(top_cov["year"]),
            "share_pct": float(top_cov["share"]),
            "covid_papers": int(top_cov["covid_papers"]),
        },
        "all_covid_records": covid_records,
        "jsd_baseline": round(jsd_baseline, 4),
        "jsd_shock": round(jsd_shock, 4),
        "jsd_ratio": round(jsd_ratio, 3),
    }

    data = {
        "id": "08_covid_shock",
        "question": "How much output did COVID cost, and did research shift?",
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            "Pre-pandemic linear trend fitted on 2016–2019 annual papers. "
            "Publication lag implies 2020 papers primarily reflect pre-pandemic projects; impact shows in 2021."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
