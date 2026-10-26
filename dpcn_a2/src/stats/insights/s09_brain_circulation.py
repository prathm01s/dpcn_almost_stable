"""Insight 9: Brain Circulation and International Scientific Mobility.

Classifies scientists into Returnees, Home-grown, and Foreign-trained using full career
affiliation histories, evaluating whether foreign postdoctoral spells boost citation impact
and international co-authorship.
"""

from collections import Counter
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from src.common.logging import get_logger
from src.stats.insights.common import faculty, papers, LABS, SEED, not_computed, save_insight

logger = get_logger("insight_09")

CAREERS_DIR = Path("data/cache/openalex/careers")
VALIDATION_CSV = Path("stats/tables/insights/09_validation_sample.csv")
FOREIGN_FLAGS_CSV = Path("data/final/work_reference_counts.csv")  # has_foreign_coauthor (Step 18)
QUESTION = ("How many of our scientists trained in India, worked abroad, and came back, "
            "and did time abroad change their research?")


def classify_scientist(timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Classify a scientist's career into Returnee, Home-grown, Foreign-trained, or Unclassifiable."""
    if not timeline:
        return {"predicted_class": "Unclassifiable", "phd_proxy": "Unknown", "host_country": "None", "academic_age": 0}

    # Sort timeline by publication year ascending
    timeline.sort(key=lambda x: (x.get("year") or 9999))

    # Aggregate by year and distinct papers
    by_year: Dict[int, List[Dict[str, Any]]] = {}
    distinct_works: List[Dict[str, Any]] = []
    seen_wids = set()

    for e in timeline:
        y = e.get("year")
        wid = e.get("work_id")
        if y:
            by_year.setdefault(y, []).append(e)
        if wid and wid not in seen_wids:
            seen_wids.add(wid)
            distinct_works.append(e)

    if not by_year:
        return {"predicted_class": "Unclassifiable", "phd_proxy": "Unknown", "host_country": "None", "academic_age": 0}

    sorted_years = sorted(by_year.keys())
    first_pub_year = sorted_years[0]
    academic_age = 2026 - first_pub_year

    # phd_proxy: most frequent institution on first 3 papers
    first_3 = distinct_works[:3]
    insts_first_3 = [e.get("institution_name") for e in first_3 if e.get("institution_name")]
    countries_first_3 = [e.get("country_code") for e in first_3 if e.get("country_code")]

    def top(values):
        return sorted(Counter(values).items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    phd_proxy = top(insts_first_3) if insts_first_3 else "Unknown"
    phd_country = top(countries_first_3) if countries_first_3 else ""

    # Identify abroad spells: >= 2 consecutive years where all affiliations are non-Indian, >= 2 papers
    abroad_years = set()
    abroad_countries_by_year = {}
    for y, elist in by_year.items():
        c_set = set(e.get("country_code") for e in elist if e.get("country_code"))
        if c_set and "IN" not in c_set:
            abroad_years.add(y)
            abroad_countries_by_year[y] = c_set

    has_abroad_spell = False
    abroad_spell_countries = []
    for y in sorted(abroad_years):
        if (y + 1) in abroad_years:
            n_papers_spell = len({e.get("work_id") for e in by_year[y] + by_year[y + 1]})
            if n_papers_spell >= 2:
                has_abroad_spell = True
                abroad_spell_countries.extend(sorted(abroad_countries_by_year[y]))
                abroad_spell_countries.extend(sorted(abroad_countries_by_year[y + 1]))

    # Most frequent spell country; ties broken alphabetically so the result never depends on set order
    host_country = (sorted(Counter(abroad_spell_countries).items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                    if abroad_spell_countries else "None")

    # Classification logic
    if len(distinct_works) < 3 or not phd_country:
        predicted_class = "Unclassifiable"
    elif phd_country != "IN":
        predicted_class = "Foreign-trained"
    elif has_abroad_spell:
        predicted_class = "Returnee"
    else:
        predicted_class = "Home-grown"

    return {
        "predicted_class": predicted_class,
        "phd_proxy": phd_proxy,
        "phd_country": phd_country,
        "host_country": host_country,
        "first_pub_year": first_pub_year,
        "academic_age": academic_age,
    }


def foreign_coauthor_flags() -> Dict[str, bool]:
    """work_id -> has a co-author institution outside India (Step 18, from cached OpenAlex authorships)."""
    df = pd.read_csv(FOREIGN_FLAGS_CSV, dtype=str, keep_default_na=False)
    df = df[df["has_foreign_coauthor"] != ""]
    return dict(zip(df["work_id"], df["has_foreign_coauthor"] == "TRUE"))


def run() -> dict:
    logger.info("Running Insight 9: Brain Circulation...")
    if not CAREERS_DIR.exists() or not any(CAREERS_DIR.glob("*.json")):
        return not_computed("09_brain_circulation", QUESTION,
                            "OpenAlex career cache missing (run make insights-fetch)")
    df_fac = faculty()
    matched = df_fac[df_fac["is_matched"]].copy()

    records = []
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

        cl = classify_scientist(timeline)
        records.append({
            "faculty_id": r["author_id"],
            "name": r["name"],
            "lab": r["lab"],
            "division": r["division"],
            "openalex_author_id": clean_aid,
            "profile_url": f"https://openalex.org/{clean_aid}",
            **cl,
        })

    df_classified = pd.DataFrame(records)
    # A few roster entries share one OpenAlex profile (upstream matching); count each profile once
    n_dup = int(df_classified["openalex_author_id"].duplicated().sum())
    df_classified = df_classified.drop_duplicates("openalex_author_id").reset_index(drop=True)
    logger.info(f"Dropped {n_dup} roster entries that share an OpenAlex profile with another entry")
    n_total = len(df_classified)
    logger.info(f"Classified {n_total} scientists")

    # Export validation sample (30 random scientists); regenerate while no true_class has been filled in
    filled_before = (VALIDATION_CSV.exists() and
                     (pd.read_csv(VALIDATION_CSV, keep_default_na=False)["true_class"] != "").any())
    if not filled_before:
        rng = np.random.default_rng(SEED)
        sample_indices = rng.choice(len(df_classified), size=min(30, len(df_classified)), replace=False)
        val_sample = df_classified.iloc[sample_indices][
            ["name", "lab", "predicted_class", "phd_proxy", "host_country", "profile_url"]
        ].copy()
        val_sample["true_class"] = ""
        val_sample["notes"] = ""
        val_sample.to_csv(VALIDATION_CSV, index=False)
        logger.info(f"✓ Exported validation sample to {VALIDATION_CSV}")

    # Check validation status
    validation_status = "validation pending"
    if VALIDATION_CSV.exists():
        val_df = pd.read_csv(VALIDATION_CSV, keep_default_na=False)
        filled = val_df[val_df["true_class"] != ""]
        if len(filled) >= 10:
            acc = (filled["predicted_class"] == filled["true_class"]).mean() * 100
            validation_status = f"validated ({acc:.1f}% accuracy on n={len(filled)})"

    # Classifiable subset
    classifiable = df_classified[df_classified["predicted_class"].isin(["Returnee", "Home-grown", "Foreign-trained"])].copy()
    n_classifiable = len(classifiable)
    ret_overall_pct = float((classifiable["predicted_class"] == "Returnee").mean() * 100)

    ret_per_lab = {}
    n_class_per_lab = {}
    for lab in LABS:
        sub = classifiable[classifiable["lab"] == lab]
        n_class_per_lab[lab] = int(len(sub))
        ret_per_lab[lab] = round(float((sub["predicted_class"] == "Returnee").mean() * 100), 1) if len(sub) > 0 else None

    # Top host countries
    returnees = df_classified[df_classified["predicted_class"] == "Returnee"]
    top_countries_counts = Counter(returnees["host_country"]).most_common(5)
    top_country_names = [c[0] for c in top_countries_counts]

    # OLS Regression on 2016-2026 citations per paper (Returnees vs Home-grown)
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    fac_metrics = []
    fac_paper_ids: Dict[str, Set[str]] = {}

    for fid, g in df_ext[df_ext["faculty_id"] != ""].groupby("faculty_id"):
        p_distinct = g.drop_duplicates("work_id")
        n_p = len(p_distinct)
        c_tot = int(pd.to_numeric(p_distinct["citations"], errors="coerce").fillna(0).sum())
        cpp = c_tot / n_p if n_p > 0 else 0.0
        fac_metrics.append({"faculty_id": fid, "n_papers": n_p, "citations": c_tot, "cpp": cpp})
        fac_paper_ids[fid] = set(p_distinct["work_id"])

    df_merged = df_classified.merge(pd.DataFrame(fac_metrics), on="faculty_id", how="inner")
    reg_sample = df_merged[df_merged["predicted_class"].isin(["Returnee", "Home-grown"])].copy()
    reg_sample["is_returnee"] = (reg_sample["predicted_class"] == "Returnee").astype(int)
    reg_sample["log1p_cpp"] = np.log1p(reg_sample["cpp"])

    # Design matrix: [1, is_returnee, academic_age, lab_NCL, lab_CECRI]
    X = np.column_stack([
        np.ones(len(reg_sample)),
        reg_sample["is_returnee"].values,
        reg_sample["academic_age"].values,
        (reg_sample["lab"] == "CSIR-NCL").astype(int).values,
        (reg_sample["lab"] == "CSIR-CECRI").astype(int).values,
    ])
    y = reg_sample["log1p_cpp"].values

    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    df_resid = len(y) - X.shape[1]
    residuals = y - X @ beta
    s2 = np.sum(residuals ** 2) / df_resid
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))

    b_ret = float(beta[1])
    se_ret = float(se[1])
    t_crit = float(stats.t.ppf(0.975, df=df_resid))
    ci_lower = b_ret - t_crit * se_ret
    ci_upper = b_ret + t_crit * se_ret

    pct_diff = float((np.exp(b_ret) - 1) * 100)
    pct_ci_lower = float((np.exp(ci_lower) - 1) * 100)
    pct_ci_upper = float((np.exp(ci_upper) - 1) * 100)
    p_val = float(2 * (1 - stats.t.cdf(abs(b_ret / se_ret), df=df_resid)))

    # Fetch foreign coauthors for returnees vs homegrown papers
    ret_works = set().union(*[fac_paper_ids.get(fid, set()) for fid in reg_sample[reg_sample["is_returnee"] == 1]["faculty_id"]])
    hg_works = set().union(*[fac_paper_ids.get(fid, set()) for fid in reg_sample[reg_sample["is_returnee"] == 0]["faculty_id"]])
    all_target_works = list(ret_works.union(hg_works))

    # Foreign co-authorship: papers without data are excluded, never counted as "no"
    foreign_flags = foreign_coauthor_flags()
    ret_known = [foreign_flags[w] for w in ret_works if w in foreign_flags]
    hg_known = [foreign_flags[w] for w in hg_works if w in foreign_flags]
    ret_foreign_pct = float(np.mean(ret_known) * 100) if ret_known else None
    hg_foreign_pct = float(np.mean(hg_known) * 100) if hg_known else None

    # Citation difference statement (no causal claim)
    if ci_lower <= 0 <= ci_upper:
        cite_statement = (f"Their papers' citations do not differ significantly from home-grown peers of similar "
                          f"career age ({pct_diff:+.0f}%, 95% CI {pct_ci_lower:+.0f}% to {pct_ci_upper:+.0f}%)")
    elif pct_diff > 0:
        cite_statement = f"Their papers draw {pct_diff:.0f}% more citations than home-grown peers of similar career age"
    else:
        cite_statement = f"Their papers draw {abs(pct_diff):.0f}% fewer citations than home-grown peers of similar career age"

    def lab_pct(lab: str) -> str:
        v = ret_per_lab.get(lab)
        return f"{lab.replace('CSIR-', '')} {v:.1f}% (n={n_class_per_lab[lab]})" if v is not None else f"{lab.replace('CSIR-', '')} n/a"

    names = {"US": "the US", "DE": "Germany", "JP": "Japan", "GB": "the UK", "FR": "France", "KR": "South Korea",
             "SA": "Saudi Arabia", "CA": "Canada", "AU": "Australia", "SG": "Singapore", "TW": "Taiwan", "CN": "China",
             "IT": "Italy", "ES": "Spain", "NL": "the Netherlands", "SE": "Sweden", "CH": "Switzerland",
             "BE": "Belgium", "IE": "Ireland", "IL": "Israel", "PT": "Portugal", "AT": "Austria", "DK": "Denmark"}
    n_ret = int((classifiable["predicted_class"] == "Returnee").sum())
    via = (f"; their abroad spell was most often in {names.get(top_countries_counts[0][0], top_countries_counts[0][0])} "
           f"({top_countries_counts[0][1]} of {n_ret})") if top_countries_counts else ""
    foreign_part = (f"; {ret_foreign_pct:.1f}% of returnees' papers vs {hg_foreign_pct:.1f}% of home-grown scientists' "
                    f"papers have a foreign co-author" if ret_foreign_pct is not None and hg_foreign_pct is not None else "")
    headline = (
        f"{ret_overall_pct:.1f}% of classifiable CSIR scientists are returnees "
        f"({', '.join(lab_pct(l) for l in ['CSIR-NCL', 'CSIR-IICT', 'CSIR-CECRI'])}){via}. "
        f"{cite_statement}{foreign_part}."
    )

    # Sankey Diagram: PhD Region -> Host Country -> Lab
    sankey_nodes = []
    sankey_links = []
    node_set = set()

    def add_node(name: str):
        if name not in node_set:
            node_set.add(name)
            sankey_nodes.append({"name": name})

    flow_p_to_h = Counter()
    flow_h_to_l = Counter()

    for _, r in classifiable.iterrows():  # unclassifiable scientists have no known PhD region
        # PhD region
        phd_reg = "PhD: India" if r["phd_country"] == "IN" else "PhD: Abroad"
        # Host country
        host = r["host_country"]
        if host in top_country_names:
            host_label = f"Host: {host}"
        elif host == "None":
            host_label = "No Abroad Spell"
        else:
            host_label = "Host: Other"
        # Lab
        lab_label = r["lab"]

        flow_p_to_h[(phd_reg, host_label)] += 1
        flow_h_to_l[(host_label, lab_label)] += 1

    for (src, tgt), val in flow_p_to_h.items():
        add_node(src)
        add_node(tgt)
        sankey_links.append({"source": src, "target": tgt, "value": val})

    for (src, tgt), val in flow_h_to_l.items():
        add_node(src)
        add_node(tgt)
        sankey_links.append({"source": src, "target": tgt, "value": val})

    chart = {
        "type": "sankey",
        "data": {
            "series": [
                {
                    "type": "sankey",
                    "layout": "none",
                    "emphasis": {"focus": "adjacency"},
                    "data": sankey_nodes,
                    "links": sankey_links,
                    "lineStyle": {"color": "gradient", "curveness": 0.5},
                }
            ],
        },
    }

    metrics = {
        "n_total_classified": n_total,
        "n_classifiable": n_classifiable,
        "returnee_pct_overall": round(ret_overall_pct, 2),
        "returnee_pct_by_lab": ret_per_lab,
        "classifiable_by_lab": n_class_per_lab,
        "n_returnees": int((classifiable["predicted_class"] == "Returnee").sum()),
        "n_regression": int(len(reg_sample)),
        "top_host_countries": dict(top_countries_counts),
        "ols_adjusted_diff_pct": round(pct_diff, 2),
        "ols_95ci": [round(pct_ci_lower, 2), round(pct_ci_upper, 2)],
        "ols_pvalue": round(p_val, 4),
        "returnee_foreign_coauthor_pct": round(ret_foreign_pct, 2) if ret_foreign_pct is not None else None,
        "homegrown_foreign_coauthor_pct": round(hg_foreign_pct, 2) if hg_foreign_pct is not None else None,
        "validation_status": validation_status,
    }

    data = {
        "id": "09_brain_circulation",
        "question": QUESTION,
        "headline": headline,
        "metrics": metrics,
        "chart": chart,
        "method_note": (
            f"Full OpenAlex career histories of {n_total} matched roster scientists; {n_classifiable} classifiable. "
            f"PhD proxy = main institution on the first 3 papers; abroad spell = ≥2 consecutive years with only non-Indian "
            f"affiliations and ≥2 papers. OLS on log(1+citations/paper, 2016–26) with academic age and lab. "
            f"Classification validation: {validation_status}."
        ),
    }

    save_insight(data)
    return data


if __name__ == "__main__":
    run()
