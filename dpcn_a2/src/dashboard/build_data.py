"""Step 18: Build static JavaScript data payload for interactive offline dashboard.

Reads authoritative CSV metrics from stats/tables/ and data/final/
Produces dashboard/data/g24_data.js defining window.G24_DATA.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("build_dashboard_data")

TABLES_DIR = Path("stats/tables")
OUTPUT_JS = Path("dashboard/data/g24_data.js")

INST_KEY_MAP = {
    "Group 24 Combined": "all",
    "CSIR-IICT": "iict",
    "CSIR-NCL": "ncl",
    "CSIR-CECRI": "cecri",
}


def load_csv(filename: str) -> pd.DataFrame:
    p = TABLES_DIR / filename
    if not p.exists():
        logger.warning(f"{p} does not exist!")
        return pd.DataFrame()
    return pd.read_csv(p, keep_default_na=False)


def run_build_dashboard_data() -> None:
    logger.info("Starting dashboard data build...")
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)

    df_trend = load_csv("publication_trend.csv")
    df_type = load_csv("publication_trend_type.csv")
    df_quartile = load_csv("quartile_distribution.csv")
    df_cite = load_csv("citation_summary.csv")
    df_h_sum = load_csv("h_index_summary.csv")
    df_h_bins = load_csv("h_index_distribution.csv")
    df_top_j = load_csv("top_journals.csv")
    df_top_p = load_csv("top_cited_papers.csv")
    df_field = load_csv("research_areas_field.csv")
    df_subfield = load_csv("research_areas_subfield.csv")
    df_fac = load_csv("faculty_performance.csv")
    df_dept = load_csv("department_performance.csv")
    df_conf = load_csv("conference_ranks.csv")
    df_conn = load_csv("indian_connections_summary.csv")
    df_partners = load_csv("indian_partner_institutions.csv")

    # Load compact paper rows for instant client-side multi-filter queries
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    # Deduplicate to paper level per institution
    df_papers_inst = df_ext.drop_duplicates(subset=["institution", "work_id"])

    # Prepare compact records: [work_id, inst_key, year, type, quartile, field, citations, title, journal, doi]
    compact_papers: List[Dict[str, Any]] = []
    for _, r in df_papers_inst.iterrows():
        compact_papers.append({
            "id": r["work_id"],
            "inst": INST_KEY_MAP.get(r["institution"], "other"),
            "yr": int(r["year"]),
            "t": str(r["type"]).lower(),
            "q": str(r["quartile"]),
            "f": str(r["field"]) or "Unclassified",
            "c": int(r["citations"]),
            "ti": str(r["title"]),
            "j": str(r["journal_name"]),
            "doi": str(r["doi"]),
        })

    logger.info(f"Compiled {len(compact_papers)} compact paper records for client-side filtering")

    payload: Dict[str, Any] = {
        "meta": {
            "group": 24,
            "title": "Mapping Indian Research: CSIR Chemistry Cluster",
            "institutes": ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"],
            "collection_date": "2026-10-13",
            "year_window": [2016, 2026],
            "is_partial_2026": True,
            "total_papers": df_ext["work_id"].nunique(),
            "total_authorship_rows": len(df_ext),
            "total_faculty": len(df_fac),
        },
        "by_institute": {},
        "papers_compact": compact_papers,
        "network": {
            "status": "Task 4 Deferred Module",
            "citation_edges_count": 27816,
            "notes": "Directed citation network and undirected authorship network modules reserved for Task 4.",
        },
    }

    # Populate by_institute bundles
    for inst_name, inst_key in INST_KEY_MAP.items():
        # Trend
        sub_trend = df_trend[df_trend["institution"] == inst_name].sort_values("year")
        sub_type = df_type[df_type["institution"] == inst_name].sort_values("year")
        trend_merged = []
        for _, tr in sub_trend.iterrows():
            y = tr["year"]
            ty_row = sub_type[sub_type["year"] == y]
            j_cnt = int(ty_row["journal_papers"].iloc[0]) if len(ty_row) > 0 else 0
            c_cnt = int(ty_row["conference_papers"].iloc[0]) if len(ty_row) > 0 else 0
            trend_merged.append({
                "year": int(y),
                "is_partial": bool(tr["is_partial_year"]),
                "total": int(tr["papers"]),
                "journal": j_cnt,
                "conference": c_cnt,
                "yoy_growth_pct": float(tr["yoy_growth_pct"]) if tr["yoy_growth_pct"] != "" else None,
                "cagr_2016_2025": float(tr["cagr_2016_2025"]),
            })

        # Quartiles
        sub_q_all = df_quartile[(df_quartile["institution"] == inst_name) & (df_quartile["period"] == "2016-2026 Overall")]
        sub_q_years = df_quartile[(df_quartile["institution"] == inst_name) & (df_quartile["period"] != "2016-2026 Overall")].sort_values("year")

        q_overall = {}
        if len(sub_q_all) > 0:
            qr = sub_q_all.iloc[0]
            q_overall = {
                "total_journals": int(qr["total_journals"]),
                "q1": int(qr["q1_count"]),
                "q2": int(qr["q2_count"]),
                "q3": int(qr["q3_count"]),
                "q4": int(qr["q4_count"]),
                "unranked": int(qr["unranked_count"]),
                "q1_fraction_primary_pct": float(qr["q1_fraction_primary_pct"]),
                "q1_fraction_all_pct": float(qr["q1_fraction_all_pct"]),
                "quartile_coverage_pct": float(qr["quartile_coverage_pct"]),
            }

        q_yearly = []
        for _, qr in sub_q_years.iterrows():
            q_yearly.append({
                "year": int(qr["year"]),
                "total_journals": int(qr["total_journals"]),
                "q1": int(qr["q1_count"]),
                "q2": int(qr["q2_count"]),
                "q3": int(qr["q3_count"]),
                "q4": int(qr["q4_count"]),
                "unranked": int(qr["unranked_count"]),
                "q1_fraction_primary_pct": float(qr["q1_fraction_primary_pct"]),
            })

        # Citations
        sub_c_all = df_cite[(df_cite["institution"] == inst_name) & (df_cite["period"] == "2016-2026 Overall")]
        c_summary = {}
        if len(sub_c_all) > 0:
            cr = sub_c_all.iloc[0]
            c_summary = {
                "total_citations": int(cr["total_citations"]),
                "mean_citations": float(cr["mean_citations"]),
                "median_citations": float(cr["median_citations"]),
                "p75_citations": float(cr["p75_citations"]),
                "max_citations": int(cr["max_citations"]),
                "uncited_count": int(cr["uncited_count"]),
                "uncited_share_pct": float(cr["uncited_share_pct"]),
            }

        sub_c_years = df_cite[(df_cite["institution"] == inst_name) & (df_cite["period"] != "2016-2026 Overall")].sort_values("year")
        c_yearly = []
        for _, cr in sub_c_years.iterrows():
            c_yearly.append({
                "year": int(cr["year"]),
                "total_citations": int(cr["total_citations"]),
                "mean_citations": float(cr["mean_citations"]),
                "median_citations": float(cr["median_citations"]),
                "uncited_share_pct": float(cr["uncited_share_pct"]),
            })

        # h-index
        sub_h_sum = df_h_sum[df_h_sum["institution"] == inst_name]
        h_sum = {}
        if len(sub_h_sum) > 0:
            hr = sub_h_sum.iloc[0]
            h_sum = {
                "active_faculty_count": int(hr["active_faculty_count"]),
                "mean_h_index": float(hr["mean_h_index"]),
                "median_h_index": float(hr["median_h_index"]),
                "p25_h_index": float(hr["p25_h_index"]),
                "p75_h_index": float(hr["p75_h_index"]),
                "max_h_index": int(hr["max_h_index"]),
            }

        sub_h_bins = df_h_bins[df_h_bins["institution"] == inst_name]
        h_bins = []
        for _, br in sub_h_bins.iterrows():
            h_bins.append({
                "bin_label": br["bin_label"],
                "faculty_count": int(br["faculty_count"]),
                "share_pct": float(br["share_pct"]),
            })

        # Top Journals
        sub_tj = df_top_j[df_top_j["institution"] == inst_name].sort_values("rank")
        top_journals = []
        for _, jr in sub_tj.iterrows():
            top_journals.append({
                "rank": int(jr["rank"]),
                "journal_name": jr["journal_name"],
                "paper_count": int(jr["paper_count"]),
                "share_pct": float(jr["share_pct"]),
                "total_citations": int(jr["total_citations"]),
                "quartile": jr["quartile"],
                "issn": jr["issn"],
            })

        # Top Cited Papers
        sub_tp = df_top_p[df_top_p["institution"] == inst_name].sort_values("rank")
        top_papers = []
        for _, pr in sub_tp.iterrows():
            top_papers.append({
                "rank": int(pr["rank"]),
                "title": pr["title"],
                "journal_name": pr["journal_name"],
                "year": int(pr["year"]),
                "citations": int(pr["citations"]),
                "doi": pr["doi"],
                "quartile": pr["quartile"],
                "in_corpus_authors": pr["in_corpus_authors"],
            })

        # Research Areas
        sub_fields = df_field[df_field["institution"] == inst_name].sort_values("paper_count", ascending=False)
        fields_list = []
        for _, fr in sub_fields.iterrows():
            fields_list.append({
                "field": fr["field"],
                "paper_count": int(fr["paper_count"]),
                "share_pct": float(fr["share_pct"]),
            })

        sub_sf = df_subfield[df_subfield["institution"] == inst_name].sort_values("paper_count", ascending=False)
        subfields_list = []
        for _, sfr in sub_sf.iterrows():
            subfields_list.append({
                "subfield": sfr["subfield"],
                "paper_count": int(sfr["paper_count"]),
                "share_pct": float(sfr["share_pct"]),
            })

        # Faculty list
        if inst_key == "all":
            sub_fac = df_fac
        else:
            sub_fac = df_fac[df_fac["institution"] == inst_name]
        fac_list = []
        for _, fac in sub_fac.iterrows():
            fac_list.append({
                "faculty_id": fac["faculty_id"],
                "name": fac["name"],
                "institution": fac["institution"],
                "department": fac["department"],
                "designation": fac["designation"],
                "papers": int(fac["papers"]),
                "citations": int(fac["citations"]),
                "mean_citations": float(fac["mean_citations_per_paper"]),
                "q1_papers": int(fac["q1_papers"]),
                "q1_share_pct": float(fac["q1_share_pct"]),
                "top_journal": fac["top_journal"],
                "h_index": int(fac["h_index_corpus"]),
                "active_years": fac["active_years"],
            })

        # Departments
        if inst_key == "all":
            sub_dept = df_dept
        else:
            sub_dept = df_dept[df_dept["institution"] == inst_name]
        dept_list = []
        for _, dr in sub_dept.iterrows():
            dept_list.append({
                "institution": dr["institution"],
                "department": dr["department"],
                "total_faculty": int(dr["total_faculty"]),
                "active_faculty": int(dr["active_faculty"]),
                "papers": int(dr["papers"]),
                "citations": int(dr["citations"]),
                "q1_share_pct": float(dr["q1_share_pct"]),
                "mean_h_index": float(dr["mean_faculty_h_index"]),
                "top_field": dr["top_field"],
            })

        # Conference Ranks
        sub_conf = df_conf[df_conf["institution"] == inst_name]
        conf_data = {}
        if len(sub_conf) > 0:
            cnfr = sub_conf.iloc[0]
            conf_data = {
                "total_conferences": int(cnfr["total_conferences"]),
                "core_a_star": int(cnfr["core_a_star"]),
                "core_a": int(cnfr["core_a"]),
                "core_b": int(cnfr["core_b"]),
                "core_c": int(cnfr["core_c"]),
                "unranked": int(cnfr["unranked"]),
                "note": cnfr["note"],
            }

        # Indian Connections
        sub_conn = df_conn[df_conn["institution"] == inst_name]
        conn_data = {}
        if len(sub_conn) > 0:
            cnr = sub_conn.iloc[0]
            conn_data = {
                "total_papers": int(cnr["total_papers"]),
                "papers_with_indian_coauthors": int(cnr["papers_with_indian_coauthors"]),
                "indian_coauthor_pct": float(cnr["indian_coauthor_pct"]),
                "cites_indian_inst_pct": float(cnr["cites_indian_inst_pct"]),
                "cited_by_indian_inst_pct": float(cnr["cited_by_indian_inst_pct"]),
            }

        sub_part = df_partners[df_partners["institution"] == inst_name].sort_values("rank")
        partners_list = []
        for _, prt in sub_part.iterrows():
            partners_list.append({
                "rank": int(prt["rank"]),
                "partner_institution": prt["partner_institution"],
                "collaborative_papers": int(prt["collaborative_papers"]),
                "share_pct": float(prt["share_pct"]),
            })

        payload["by_institute"][inst_key] = {
            "name": inst_name,
            "trend": trend_merged,
            "quartiles": {
                "overall": q_overall,
                "yearly": q_yearly,
            },
            "citations": {
                "overall": c_summary,
                "yearly": c_yearly,
            },
            "h_index": {
                "summary": h_sum,
                "bins": h_bins,
            },
            "top_journals": top_journals,
            "top_papers": top_papers,
            "research_areas": {
                "fields": fields_list,
                "subfields": subfields_list,
            },
            "faculty": fac_list,
            "departments": dept_list,
            "conference_rank": conf_data,
            "indian_connections": {
                "summary": conn_data,
                "top_partners": partners_list,
            },
        }

    # Write out to dashboard/data/g24_data.js
    js_content = f"window.G24_DATA = {json.dumps(payload, indent=2)};\n"
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    logger.info(f"✓ Saved dashboard payload to {OUTPUT_JS} ({OUTPUT_JS.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    run_build_dashboard_data()
