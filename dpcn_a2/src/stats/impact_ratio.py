"""Citation impact ratio and impact-based "Q1" classification.

Definitions
- Paper impact ratio  IR = citations received / citations made
                         = OpenAlex cited_by_count (13 Oct 2026) / number of references
- Institute impact ratio = sum of citations received / sum of references made,
                           over the institute's distinct papers that have >= 1 reference
- A paper is "IR-Q1" when IR > T, where T is the quartile_percentile (75th) of IR over
  all papers (config/settings.yaml), so IR-Q1 is the top 25% of papers — the same share a
  quartile covers. Optional fixed thresholds (impact_ratio.thresholds) are reported too.
- Papers with 0 references in OpenAlex have no defined IR; they are counted but excluded.

This differs from the journal quartile (SJR Q1), which ranks the journal, not the paper.

Outputs (stats/tables/):
- impact_ratio_summary.csv  per institute + combined: institute IR, IR-Q1 shares, SJR Q1 share
- impact_ratio_by_year.csv  IR-Q1 shares by publication year (older papers have had longer to be cited)
- impact_ratio_vs_sjr.csv   IR-Q1 shares within each SJR quartile
- impact_ratio_top_papers.csv  top 10 papers by IR (all three labs)
"""

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import yaml

from src.common.logging import get_logger

logger = get_logger("stats_impact_ratio")

LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
ALL = "Group 24 Combined"
TABLES_DIR = Path("stats/tables")


def settings() -> Dict:
    with open("config/settings.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f).get("impact_ratio", {})
    return {"thresholds": [float(t) for t in cfg.get("thresholds") or []],
            "percentile": float(cfg.get("quartile_percentile", 75))}


def label(t: float) -> str:
    return f"{t:g}"


def paper_table() -> pd.DataFrame:
    """One row per (institute, paper) with citations, references and IR."""
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False,
                      usecols=["work_id", "institution", "title", "journal_name", "year", "type", "doi",
                               "citations", "quartile"])
    refs = pd.read_csv("data/final/work_reference_counts.csv", dtype={"references_count": "Int64"})
    p = ext.drop_duplicates(["institution", "work_id"]).merge(refs, on="work_id", how="left")
    p["citations"] = p["citations"].astype(int)
    p["year"] = p["year"].astype(int)
    p["has_refs"] = p["references_count"].fillna(0) > 0
    p["ir"] = np.where(p["has_refs"], p["citations"] / p["references_count"].astype(float).fillna(1), np.nan)
    p["sjr"] = np.where(p["type"] == "conference", "Conference", p["quartile"].replace("", "Unranked"))
    return p


def groups(p: pd.DataFrame):
    for lab in LABS:
        yield lab, p[p["institution"] == lab]
    yield ALL, p.drop_duplicates("work_id")


def summarise(g: pd.DataFrame, thresholds: List[float]) -> Dict:
    r = g[g["has_refs"]]
    row = {
        "papers": len(g),
        "papers_with_references": len(r),
        "papers_without_references": len(g) - len(r),
        "citations_received": int(r["citations"].sum()),
        "references_made": int(r["references_count"].sum()),
        "institute_impact_ratio": round(r["citations"].sum() / r["references_count"].sum(), 4) if len(r) else None,
        "median_paper_ir": round(float(r["ir"].median()), 4) if len(r) else None,
    }
    for t in thresholds:
        n = int((r["ir"] > t).sum())
        row[f"ir_q1_gt_{label(t)}"] = n
        row[f"ir_q1_gt_{label(t)}_pct"] = round(n / len(r) * 100, 2) if len(r) else None
    j = g[g["sjr"].isin(["Q1", "Q2", "Q3", "Q4"])]
    row["sjr_q1_pct"] = round((j["sjr"] == "Q1").mean() * 100, 2) if len(j) else None
    return row


def run_impact_ratio() -> None:
    logger.info("Computing citation impact ratio and IR-based Q1 classification...")
    cfg = settings()
    p = paper_table()
    pctl = float(np.percentile(p.drop_duplicates("work_id").query("has_refs")["ir"], cfg["percentile"]))
    pctl = round(pctl, 2)
    thresholds = cfg["thresholds"] + [pctl]

    summary = []
    for name, g in groups(p):
        summary.append({"institution": name, **summarise(g, thresholds)})
    df = pd.DataFrame(summary)
    df.insert(1, "percentile_threshold", pctl)
    df.insert(2, "percentile", cfg["percentile"])
    df.to_csv(TABLES_DIR / "impact_ratio_summary.csv", index=False)

    yearly = []
    for name, g in groups(p):
        for y in range(2016, 2027):
            yearly.append({"institution": name, "year": y, **summarise(g[g["year"] == y], thresholds)})
    pd.DataFrame(yearly).to_csv(TABLES_DIR / "impact_ratio_by_year.csv", index=False)

    cross = []
    for name, g in groups(p):
        for q in ["Q1", "Q2", "Q3", "Q4", "Unranked", "Conference"]:
            s = summarise(g[g["sjr"] == q], thresholds)
            s.pop("sjr_q1_pct")
            cross.append({"institution": name, "sjr_quartile": q, **s})
    pd.DataFrame(cross).to_csv(TABLES_DIR / "impact_ratio_vs_sjr.csv", index=False)

    allp = p[p["has_refs"]].copy()
    labs = allp.groupby("work_id")["institution"].agg(lambda s: "; ".join(sorted(set(s))))
    top = allp.drop_duplicates("work_id").sort_values(["ir", "citations"], ascending=False).head(10)
    pd.DataFrame([{
        "rank": i, "title": r.title, "journal_name": r.journal_name, "year": r.year, "institutions": labs[r.work_id],
        "citations": r.citations, "references": int(r.references_count), "impact_ratio": round(r.ir, 2),
        "sjr_quartile": r.sjr, "doi": r.doi,
    } for i, r in enumerate(top.itertuples(), 1)]).to_csv(TABLES_DIR / "impact_ratio_top_papers.csv", index=False)

    allrow = df[df["institution"] == ALL].iloc[0]
    logger.info(f"✓ Impact ratio: institute IR {allrow['institute_impact_ratio']}, P{cfg['percentile']:g} threshold {pctl}; "
                + ", ".join(f"IR>{label(t)}: {allrow[f'ir_q1_gt_{label(t)}_pct']}%" for t in thresholds))


if __name__ == "__main__":
    run_impact_ratio()
