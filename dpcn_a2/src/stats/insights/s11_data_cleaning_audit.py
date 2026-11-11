"""Extract exact figures, exclusion audit, and funnel statistics for the cadre faculty cleaning page.

Generates stats/tables/insights/11_data_cleaning_stats.json.
"""

import json
from collections import Counter
from pathlib import Path
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("s11_data_cleaning_audit")

OUTPUT_JSON = Path("stats/tables/insights/11_data_cleaning_stats.json")


def audit_data_cleaning() -> dict:
    fm = pd.read_csv("data/final/faculty_master.csv", keep_default_na=False)
    ex = pd.read_csv("data/review/roster_excluded.csv", keep_default_na=False)
    ov = pd.read_csv("config/overrides/roster_overrides.csv", keep_default_na=False)
    ext = pd.read_csv("data/final/group24_data_extended.csv", usecols=["author_role", "institution", "department", "designation", "faculty_id", "doi"], keep_default_na=False)

    # 1. Funnel stats
    # Raw roster before cleanup
    # Total raw = len(fm) + len(ex) = 385 + 120 = 505
    raw_total = len(fm) + len(ex)
    raw_by_lab = {
        "CSIR-IICT": int((fm["inst_key"] == "iict").sum() + (ex["inst_key"] == "iict").sum()),
        "CSIR-NCL": int((fm["inst_key"] == "ncl").sum() + (ex["inst_key"] == "ncl").sum()),
        "CSIR-CECRI": int((fm["inst_key"] == "cecri").sum() + (ex["inst_key"] == "cecri").sum()),
    }

    # Exclusions
    tech_staff_count = int(ex["job_title"].str.strip().ne("").sum())
    dup_count = int((ex["job_title"].str.strip().eq("") & ex["reason"].str.contains("duplicate", case=False)).sum())
    unmatched_count = int((ov["action"] == "unmatch").sum())

    clean_roster_total = len(fm)
    clean_roster_by_lab = {
        "CSIR-IICT": int((fm["inst_key"] == "iict").sum()),
        "CSIR-NCL": int((fm["inst_key"] == "ncl").sum()),
        "CSIR-CECRI": int((fm["inst_key"] == "cecri").sum()),
    }

    # Faculty with >= 1 paper in 2016-2026 corpus
    matched_faculty = fm[fm["author_id"].str.strip().ne("")]
    active_total = len(matched_faculty)
    active_by_lab = {
        "CSIR-IICT": int((matched_faculty["inst_key"] == "iict").sum()),
        "CSIR-NCL": int((matched_faculty["inst_key"] == "ncl").sum()),
        "CSIR-CECRI": int((matched_faculty["inst_key"] == "cecri").sum()),
    }

    # 2. Excluded staff breakdown by job title / category
    tech_title_counts = Counter()
    for jt in ex["job_title"]:
        jt_clean = jt.strip()
        if not jt_clean:
            continue
        # simplify e.g. "Sr. Technical Officer (3)" -> "Sr. Technical Officer"
        base_title = jt_clean.split("(")[0].strip()
        tech_title_counts[base_title] += 1

    excluded_records = []
    for _, r in ex.iterrows():
        excluded_records.append({
            "faculty_id": r["faculty_id"],
            "lab": "CSIR-IICT" if r["inst_key"] == "iict" else ("CSIR-NCL" if r["inst_key"] == "ncl" else "CSIR-CECRI"),
            "full_name": r["full_name"],
            "job_title": r["job_title"] if r["job_title"] else "Duplicate Roster Listing",
            "department": r["department"],
            "papers_in_corpus": int(r["n_papers_corpus"]) if r["n_papers_corpus"] else 0,
            "reason": r["reason"]
        })

    # 3. Clean Cadre Faculty Designation Distribution
    designations = Counter(matched_faculty["designation"].str.strip())
    top_designations = [{"designation": k, "count": v} for k, v in designations.most_common()]

    # 4. Department Distribution among Active Cadre Faculty
    dept_counts = Counter(matched_faculty["department"].str.strip())
    top_depts = [{"department": k, "count": v} for k, v in dept_counts.most_common(12)]

    # 5. Paper attribution impact
    fac_ext = ext[ext["author_role"] == "faculty"]
    total_fac_paper_rows = len(fac_ext)
    distinct_fac_dois = fac_ext["doi"].replace("", None).dropna().nunique()

    audit_summary = {
        "funnel": {
            "stage_1_raw_scraped": {
                "total": raw_total,
                "by_lab": raw_by_lab,
                "description": "Raw staff directories scraped directly from official institute websites."
            },
            "stage_2_excluded_technical_and_duplicates": {
                "total_excluded": len(ex),
                "technical_staff_excluded": tech_staff_count,
                "duplicates_removed": dup_count,
                "unmatched_wrong_profiles": unmatched_count,
                "description": "Rule-based filtering removing non-scientific cadre staff (Technical Officers/Technicians), duplicate listings and page text scraped as names (D-40)."
            },
            "stage_3_clean_roster": {
                "total": clean_roster_total,
                "by_lab": clean_roster_by_lab,
                "description": "Legitimate permanent scientific cadre (Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist, Director)."
            },
            "stage_4_active_cadre_with_papers": {
                "total": active_total,
                "by_lab": active_by_lab,
                "description": "Tenured cadre faculty with >=1 matched paper in the 2016-2026 corpus."
            }
        },
        "technical_titles_breakdown": [{"title": k, "count": v} for k, v in tech_title_counts.most_common()],
        "top_designations": top_designations,
        "top_departments": top_depts,
        "paper_attribution": {
            "faculty_paper_rows": total_fac_paper_rows,
            "distinct_faculty_dois": distinct_fac_dois,
        },
        # Excluded staff stay in the dataset as ordinary authors (affiliated_author); only faculty statistics
        # and the faculty networks leave them out
        "excluded_staff_publishing": {
            "with_papers": int((pd.to_numeric(ex["n_papers_corpus"], errors="coerce").fillna(0) > 0).sum()),
            "papers_total": int(pd.to_numeric(ex["n_papers_corpus"], errors="coerce").fillna(0).sum()),
        },
        "sample_excluded": excluded_records
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(audit_summary, indent=2), encoding="utf-8")
    logger.info(f"✓ Saved data cleaning audit to {OUTPUT_JSON}")
    return audit_summary


if __name__ == "__main__":
    audit_data_cleaning()
