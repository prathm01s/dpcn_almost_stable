"""Step 15: Metrics computation for Task 2 (Statistics Report) and Task 3 (Dashboard).

Reads from data/final/group24_data_extended.csv and data/final/faculty_master.csv.
Computes all authoritative metric tables and exports to stats/tables/*.csv.
"""

from collections import Counter
import math
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("metrics")

INSTITUTES = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]


def calculate_cagr(start_val: float, end_val: float, num_years: int) -> float:
    """Calculate Compound Annual Growth Rate (CAGR)."""
    if start_val <= 0 or end_val <= 0 or num_years <= 0:
        return 0.0
    return ((end_val / start_val) ** (1.0 / num_years) - 1.0) * 100.0


def run_metrics_computation() -> None:
    logger.info("Starting metrics computation...")
    tables_dir = Path("stats/tables")
    tables_dir.mkdir(parents=True, exist_ok=True)

    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    df_fac = pd.read_csv("data/final/faculty_master.csv", keep_default_na=False)

    # ---------------------------------------------------------
    # 1. PUBLICATION TREND (Distinct papers per institute x year)
    # ---------------------------------------------------------
    logger.info("1. Computing publication trends...")
    # Distinct paper per (institution, work_id)
    inst_papers = df_ext.drop_duplicates(subset=["institution", "work_id"])
    combined_papers = df_ext.drop_duplicates(subset=["work_id"])

    trend_rows = []
    years = sorted(df_ext["year"].unique())

    for inst in INSTITUTES:
        sub = inst_papers[inst_papers["institution"] == inst]
        yearly_counts = sub["year"].value_counts().to_dict()
        val_2016 = yearly_counts.get(2016, 0)
        val_2025 = yearly_counts.get(2025, 0)
        cagr = calculate_cagr(val_2016, val_2025, 9)

        for y in years:
            cnt = yearly_counts.get(y, 0)
            prev_cnt = yearly_counts.get(y - 1, 0) if y > 2016 else 0
            yoy = ((cnt - prev_cnt) / prev_cnt * 100.0) if prev_cnt > 0 else 0.0
            trend_rows.append({
                "institution": inst,
                "year": y,
                "is_partial_year": bool(y == 2026),
                "papers": cnt,
                "yoy_growth_pct": round(yoy, 2) if y > 2016 else None,
                "cagr_2016_2025": round(cagr, 2),
            })

    # Combined Group 24 view
    comb_counts = combined_papers["year"].value_counts().to_dict()
    comb_2016 = comb_counts.get(2016, 0)
    comb_2025 = comb_counts.get(2025, 0)
    comb_cagr = calculate_cagr(comb_2016, comb_2025, 9)
    for y in years:
        cnt = comb_counts.get(y, 0)
        prev_cnt = comb_counts.get(y - 1, 0) if y > 2016 else 0
        yoy = ((cnt - prev_cnt) / prev_cnt * 100.0) if prev_cnt > 0 else 0.0
        trend_rows.append({
            "institution": "Group 24 Combined",
            "year": y,
            "is_partial_year": bool(y == 2026),
            "papers": cnt,
            "yoy_growth_pct": round(yoy, 2) if y > 2016 else None,
            "cagr_2016_2025": round(comb_cagr, 2),
        })

    df_trend = pd.DataFrame(trend_rows)
    df_trend.to_csv(tables_dir / "publication_trend.csv", index=False)

    # ---------------------------------------------------------
    # 2. PUBLICATION TREND BY TYPE (Journal vs Conference)
    # ---------------------------------------------------------
    type_rows = []
    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers
        else:
            sub = inst_papers[inst_papers["institution"] == inst]

        for y in years:
            y_sub = sub[sub["year"] == y]
            j_cnt = (y_sub["type"] == "journal").sum()
            c_cnt = (y_sub["type"] == "conference").sum()
            tot = len(y_sub)
            type_rows.append({
                "institution": inst,
                "year": y,
                "is_partial_year": bool(y == 2026),
                "journal_papers": j_cnt,
                "conference_papers": c_cnt,
                "total_papers": tot,
                "journal_share_pct": round(j_cnt / tot * 100.0, 2) if tot > 0 else 0.0,
            })
    df_type = pd.DataFrame(type_rows)
    df_type.to_csv(tables_dir / "publication_trend_type.csv", index=False)

    # ---------------------------------------------------------
    # 3. JOURNAL QUARTILE DISTRIBUTION & Q1 FRACTIONS
    # ---------------------------------------------------------
    logger.info("2. Computing journal quartile distributions...")
    q_rows = []
    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers[combined_papers["type"] == "journal"]
        else:
            sub = inst_papers[(inst_papers["institution"] == inst) & (inst_papers["type"] == "journal")]

        # Overall across entire window
        tot_j = len(sub)
        q1 = (sub["quartile"] == "Q1").sum()
        q2 = (sub["quartile"] == "Q2").sum()
        q3 = (sub["quartile"] == "Q3").sum()
        q4 = (sub["quartile"] == "Q4").sum()
        unranked = (sub["quartile"].isin(["", "Unranked"])).sum()
        ranked = q1 + q2 + q3 + q4

        q1_frac_primary = round(q1 / ranked * 100.0, 2) if ranked > 0 else 0.0
        q1_frac_all = round(q1 / tot_j * 100.0, 2) if tot_j > 0 else 0.0
        coverage = round(ranked / tot_j * 100.0, 2) if tot_j > 0 else 0.0

        q_rows.append({
            "institution": inst,
            "period": "2016-2026 Overall",
            "year": "ALL",
            "total_journals": tot_j,
            "q1_count": q1,
            "q2_count": q2,
            "q3_count": q3,
            "q4_count": q4,
            "unranked_count": unranked,
            "ranked_count": ranked,
            "q1_fraction_primary_pct": q1_frac_primary,  # Q1 / ranked
            "q1_fraction_all_pct": q1_frac_all,          # Q1 / all
            "quartile_coverage_pct": coverage,
        })

        # By Year
        for y in years:
            y_sub = sub[sub["year"] == y]
            tot_jy = len(y_sub)
            q1y = (y_sub["quartile"] == "Q1").sum()
            q2y = (y_sub["quartile"] == "Q2").sum()
            q3y = (y_sub["quartile"] == "Q3").sum()
            q4y = (y_sub["quartile"] == "Q4").sum()
            uny = (y_sub["quartile"].isin(["", "Unranked"])).sum()
            ranky = q1y + q2y + q3y + q4y

            q_rows.append({
                "institution": inst,
                "period": str(y),
                "year": y,
                "total_journals": tot_jy,
                "q1_count": q1y,
                "q2_count": q2y,
                "q3_count": q3y,
                "q4_count": q4y,
                "unranked_count": uny,
                "ranked_count": ranky,
                "q1_fraction_primary_pct": round(q1y / ranky * 100.0, 2) if ranky > 0 else 0.0,
                "q1_fraction_all_pct": round(q1y / tot_jy * 100.0, 2) if tot_jy > 0 else 0.0,
                "quartile_coverage_pct": round(ranky / tot_jy * 100.0, 2) if tot_jy > 0 else 0.0,
            })

    df_q = pd.DataFrame(q_rows)
    df_q.to_csv(tables_dir / "quartile_distribution.csv", index=False)

    # ---------------------------------------------------------
    # 4. CITATION SUMMARY
    # ---------------------------------------------------------
    logger.info("3. Computing citation summaries...")
    cite_rows = []
    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers
        else:
            sub = inst_papers[inst_papers["institution"] == inst]

        cites = sub["citations"].astype(int).tolist()
        tot_c = sum(cites)
        n = len(cites)
        uncited = sum(1 for c in cites if c == 0)

        cite_rows.append({
            "institution": inst,
            "period": "2016-2026 Overall",
            "year": "ALL",
            "papers": n,
            "total_citations": tot_c,
            "mean_citations": round(float(np.mean(cites)), 2) if n > 0 else 0.0,
            "median_citations": round(float(np.median(cites)), 2) if n > 0 else 0.0,
            "p75_citations": round(float(np.percentile(cites, 75)), 2) if n > 0 else 0.0,
            "max_citations": max(cites) if n > 0 else 0,
            "uncited_count": uncited,
            "uncited_share_pct": round(uncited / n * 100.0, 2) if n > 0 else 0.0,
        })

        for y in years:
            y_sub = sub[sub["year"] == y]
            ycites = y_sub["citations"].astype(int).tolist()
            yn = len(ycites)
            ytot_c = sum(ycites)
            yuncited = sum(1 for c in ycites if c == 0)

            cite_rows.append({
                "institution": inst,
                "period": str(y),
                "year": y,
                "papers": yn,
                "total_citations": ytot_c,
                "mean_citations": round(float(np.mean(ycites)), 2) if yn > 0 else 0.0,
                "median_citations": round(float(np.median(ycites)), 2) if yn > 0 else 0.0,
                "p75_citations": round(float(np.percentile(ycites, 75)), 2) if yn > 0 else 0.0,
                "max_citations": max(ycites) if yn > 0 else 0,
                "uncited_count": yuncited,
                "uncited_share_pct": round(yuncited / yn * 100.0, 2) if yn > 0 else 0.0,
            })

    df_cite = pd.DataFrame(cite_rows)
    df_cite.to_csv(tables_dir / "citation_summary.csv", index=False)

    # ---------------------------------------------------------
    # 5. H-INDEX DISTRIBUTION (Across roster faculty with >= 1 paper)
    # ---------------------------------------------------------
    logger.info("4. Computing h-index distributions...")
    active_fac = df_fac[df_fac["n_papers_corpus"].astype(int) > 0].copy()
    active_fac["h_index_corpus"] = active_fac["h_index_corpus"].astype(int)

    h_summary_rows = []
    inst_key_map = {
        "CSIR-IICT": "iict",
        "CSIR-NCL": "ncl",
        "CSIR-CECRI": "cecri",
    }

    bin_edges = [0, 5, 10, 15, 20, 25, 30, 35, 1000]
    bin_labels = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35+"]

    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            f_sub = active_fac
        else:
            k = inst_key_map[inst]
            f_sub = active_fac[active_fac["inst_key"] == k]

        h_vals = f_sub["h_index_corpus"].tolist()
        n_fac = len(h_vals)

        h_summary_rows.append({
            "institution": inst,
            "active_faculty_count": n_fac,
            "mean_h_index": round(float(np.mean(h_vals)), 2) if n_fac > 0 else 0.0,
            "median_h_index": round(float(np.median(h_vals)), 2) if n_fac > 0 else 0.0,
            "p25_h_index": round(float(np.percentile(h_vals, 25)), 2) if n_fac > 0 else 0.0,
            "p75_h_index": round(float(np.percentile(h_vals, 75)), 2) if n_fac > 0 else 0.0,
            "max_h_index": max(h_vals) if n_fac > 0 else 0,
        })

    df_h_sum = pd.DataFrame(h_summary_rows)
    df_h_sum.to_csv(tables_dir / "h_index_summary.csv", index=False)

    # Histogram Bins
    h_bin_rows = []
    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            f_sub = active_fac
        else:
            k = inst_key_map[inst]
            f_sub = active_fac[active_fac["inst_key"] == k]

        h_vals = f_sub["h_index_corpus"].tolist()
        tot = len(h_vals)

        for i, label in enumerate(bin_labels):
            low = bin_edges[i]
            high = bin_edges[i + 1]
            cnt = sum(1 for h in h_vals if low <= h < high)
            h_bin_rows.append({
                "institution": inst,
                "bin_label": label,
                "bin_lower": low,
                "bin_upper": high - 1,
                "faculty_count": cnt,
                "share_pct": round(cnt / tot * 100.0, 2) if tot > 0 else 0.0,
            })
    df_h_bins = pd.DataFrame(h_bin_rows)
    df_h_bins.to_csv(tables_dir / "h_index_distribution.csv", index=False)

    # ---------------------------------------------------------
    # 6. TOP 5 JOURNALS PER INSTITUTE (+ COMBINED)
    # ---------------------------------------------------------
    logger.info("5. Computing top journals...")
    journal_rows = []
    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers[combined_papers["type"] == "journal"]
        else:
            sub = inst_papers[(inst_papers["institution"] == inst) & (inst_papers["type"] == "journal")]

        tot_j = len(sub)
        # Group by journal_name
        grouped = sub.groupby("journal_name").agg(
            paper_count=("work_id", "nunique"),
            total_citations=("citations", lambda x: int(x.astype(int).sum())),
            issn=("issn", "first"),
            quartile=("quartile", lambda x: x.mode().iloc[0] if len(x) > 0 else ""),
        ).reset_index()

        # Sort by paper_count descending, tie break by total_citations descending
        sorted_j = grouped.sort_values(by=["paper_count", "total_citations"], ascending=[False, False]).head(5)

        rank = 1
        for _, r in sorted_j.iterrows():
            journal_rows.append({
                "institution": inst,
                "rank": rank,
                "journal_name": r["journal_name"],
                "paper_count": int(r["paper_count"]),
                "share_pct": round(int(r["paper_count"]) / tot_j * 100.0, 2) if tot_j > 0 else 0.0,
                "total_citations": int(r["total_citations"]),
                "quartile": r["quartile"],
                "issn": r["issn"],
            })
            rank += 1

    df_top_j = pd.DataFrame(journal_rows)
    df_top_j.to_csv(tables_dir / "top_journals.csv", index=False)

    # ---------------------------------------------------------
    # 7. TOP 10 MOST CITED PAPERS PER INSTITUTE (+ COMBINED)
    # ---------------------------------------------------------
    logger.info("6. Computing top 10 most cited papers...")
    top_papers_rows = []

    # Map work_id to all in-corpus authors string
    paper_authors_map: Dict[str, str] = {}
    for wid, group in df_ext.groupby("work_id"):
        authors = sorted(group["author"].unique())
        paper_authors_map[wid] = "; ".join(authors)

    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers.copy()
        else:
            sub = inst_papers[inst_papers["institution"] == inst].copy()

        sub["citations_int"] = sub["citations"].astype(int)
        sorted_p = sub.sort_values(by=["citations_int", "year"], ascending=[False, False]).head(10)

        rank = 1
        for _, r in sorted_p.iterrows():
            wid = r["work_id"]
            top_papers_rows.append({
                "institution": inst,
                "rank": rank,
                "title": r["title"],
                "journal_name": r["journal_name"],
                "year": int(r["year"]),
                "citations": int(r["citations_int"]),
                "doi": r["doi"],
                "quartile": r["quartile"],
                "in_corpus_authors": paper_authors_map.get(wid, r["author"]),
                "work_id": wid,
            })
            rank += 1

    df_top_p = pd.DataFrame(top_papers_rows)
    df_top_p.to_csv(tables_dir / "top_cited_papers.csv", index=False)

    # ---------------------------------------------------------
    # 8. RESEARCH AREAS (Field & Subfield)
    # ---------------------------------------------------------
    logger.info("7. Computing research area distributions...")
    field_rows = []
    subfield_rows = []

    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers
        else:
            sub = inst_papers[inst_papers["institution"] == inst]

        tot = len(sub)

        # Field level
        f_counts = sub["field"].replace("", "Unclassified").value_counts()
        for field_name, cnt in f_counts.items():
            field_rows.append({
                "institution": inst,
                "field": field_name,
                "paper_count": cnt,
                "share_pct": round(cnt / tot * 100.0, 2) if tot > 0 else 0.0,
            })

        # Subfield level (top 15)
        sf_counts = sub["subfield"].replace("", "Unclassified").value_counts().head(15)
        for sf_name, cnt in sf_counts.items():
            subfield_rows.append({
                "institution": inst,
                "subfield": sf_name,
                "paper_count": cnt,
                "share_pct": round(cnt / tot * 100.0, 2) if tot > 0 else 0.0,
            })

    df_field = pd.DataFrame(field_rows)
    df_field.to_csv(tables_dir / "research_areas_field.csv", index=False)

    df_subfield = pd.DataFrame(subfield_rows)
    df_subfield.to_csv(tables_dir / "research_areas_subfield.csv", index=False)

    # ---------------------------------------------------------
    # 9. FACULTY PERFORMANCE TABLE
    # ---------------------------------------------------------
    logger.info("8. Computing faculty performance table...")
    # Faculty rows in df_ext have faculty_id non-empty and author_role == "faculty"
    fac_paper_authors = df_ext[df_ext["faculty_id"] != ""].copy()
    fac_paper_authors["citations_int"] = fac_paper_authors["citations"].astype(int)

    fac_perf_rows = []
    # Merge with roster list so all 505 faculty are accounted for
    for _, fac in df_fac.iterrows():
        fid = fac["faculty_id"]
        inst_key = fac["inst_key"]
        inst_name = {"iict": "CSIR-IICT", "ncl": "CSIR-NCL", "cecri": "CSIR-CECRI"}.get(inst_key, inst_key)
        name = fac["full_name"]
        dept = fac["department"]
        desig = fac["designation"]

        sub = fac_paper_authors[fac_paper_authors["faculty_id"] == fid]
        distinct_p = sub.drop_duplicates(subset=["work_id"])
        n_papers = len(distinct_p)

        if n_papers > 0:
            cites = distinct_p["citations_int"].tolist()
            tot_c = sum(cites)
            mean_c = round(tot_c / n_papers, 2)
            q1_cnt = (distinct_p["quartile"] == "Q1").sum()
            q1_pct = round(q1_cnt / n_papers * 100.0, 2)

            # Mode journal
            j_modes = distinct_p["journal_name"].dropna().mode()
            top_j = j_modes.iloc[0] if len(j_modes) > 0 else ""

            # First and corresponding counts
            first_author_cnt = (sub["author_position"] == "first").sum()
            corr_author_cnt = sub["is_corresponding"].astype(bool).sum()

            years_active = sorted(distinct_p["year"].unique())
            active_span = f"{min(years_active)}–{max(years_active)}" if len(years_active) > 1 else str(years_active[0])
            h_corp = int(fac.get("h_index_corpus") or 0)
        else:
            tot_c = 0
            mean_c = 0.0
            q1_cnt = 0
            q1_pct = 0.0
            top_j = ""
            first_author_cnt = 0
            corr_author_cnt = 0
            active_span = "None"
            h_corp = 0

        fac_perf_rows.append({
            "faculty_id": fid,
            "name": name,
            "institution": inst_name,
            "department": dept,
            "designation": desig,
            "papers": n_papers,
            "citations": tot_c,
            "mean_citations_per_paper": mean_c,
            "q1_papers": q1_cnt,
            "q1_share_pct": q1_pct,
            "top_journal": top_j,
            "h_index_corpus": h_corp,
            "first_author_papers": first_author_cnt,
            "corresponding_author_papers": corr_author_cnt,
            "active_years": active_span,
        })

    df_fac_perf = pd.DataFrame(fac_perf_rows)
    # Sort by papers descending, then citations descending
    df_fac_perf = df_fac_perf.sort_values(by=["papers", "citations"], ascending=[False, False])
    df_fac_perf.to_csv(tables_dir / "faculty_performance.csv", index=False)

    # ---------------------------------------------------------
    # 10. DEPARTMENT PERFORMANCE TABLE
    # ---------------------------------------------------------
    logger.info("9. Computing department performance table...")
    dept_rows = []
    # Departments are defined within faculty_performance
    for inst in INSTITUTES:
        inst_fac = df_fac_perf[df_fac_perf["institution"] == inst]
        depts = sorted(inst_fac["department"].unique())

        for dept in depts:
            if not dept or dept == "Unassigned":
                continue
            d_sub = inst_fac[inst_fac["department"] == dept]
            fac_cnt = len(d_sub)
            active_fac_cnt = len(d_sub[d_sub["papers"] > 0])

            # Department papers: papers where >= 1 faculty of this department is author
            dept_fids = set(d_sub["faculty_id"].unique())
            dept_works = fac_paper_authors[fac_paper_authors["faculty_id"].isin(dept_fids)].drop_duplicates(subset=["work_id"])
            p_cnt = len(dept_works)
            c_cnt = int(dept_works["citations_int"].sum()) if p_cnt > 0 else 0
            q1_c = (dept_works["quartile"] == "Q1").sum()
            q1_pct = round(q1_c / p_cnt * 100.0, 2) if p_cnt > 0 else 0.0

            mean_h = round(d_sub[d_sub["papers"] > 0]["h_index_corpus"].mean(), 2) if active_fac_cnt > 0 else 0.0

            # Top field in this department
            top_field = ""
            if p_cnt > 0:
                f_modes = dept_works["field"].replace("", "Unclassified").mode()
                top_field = f_modes.iloc[0] if len(f_modes) > 0 else ""

            dept_rows.append({
                "institution": inst,
                "department": dept,
                "total_faculty": fac_cnt,
                "active_faculty": active_fac_cnt,
                "papers": p_cnt,
                "citations": c_cnt,
                "mean_citations_per_paper": round(c_cnt / p_cnt, 2) if p_cnt > 0 else 0.0,
                "q1_papers": q1_c,
                "q1_share_pct": q1_pct,
                "mean_faculty_h_index": mean_h,
                "top_field": top_field,
            })

    df_dept = pd.DataFrame(dept_rows)
    df_dept = df_dept.sort_values(by=["institution", "papers"], ascending=[True, False])
    df_dept.to_csv(tables_dir / "department_performance.csv", index=False)

    # ---------------------------------------------------------
    # 11. CONFERENCE RANKINGS (CORE A*, A, B, C, Unranked)
    # ---------------------------------------------------------
    logger.info("10. Computing conference rankings...")
    conf_papers = combined_papers[combined_papers["type"] == "conference"]
    conf_rows = []

    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = conf_papers
        else:
            sub = inst_papers[(inst_papers["institution"] == inst) & (inst_papers["type"] == "conference")]

        tot = len(sub)
        core_a_star = (sub["quartile"] == "CORE A*").sum()
        core_a = (sub["quartile"] == "CORE A").sum()
        core_b = (sub["quartile"] == "CORE B").sum()
        core_c = (sub["quartile"] == "CORE C").sum()
        unranked = tot - (core_a_star + core_a + core_b + core_c)

        conf_rows.append({
            "institution": inst,
            "total_conferences": tot,
            "core_a_star": core_a_star,
            "core_a": core_a,
            "core_b": core_b,
            "core_c": core_c,
            "unranked": unranked,
            "ranked_count": core_a_star + core_a + core_b + core_c,
            "note": "Chemistry/Electrochemistry proceedings are largely outside Computer Science CORE portal",
        })

    df_conf = pd.DataFrame(conf_rows)
    df_conf.to_csv(tables_dir / "conference_ranks.csv", index=False)

    # ---------------------------------------------------------
    # 12. INDIAN CONNECTIONS SUMMARY (PREVIEW FOR TASK 4)
    # ---------------------------------------------------------
    logger.info("11. Computing Indian connections summary...")
    conn_rows = []
    top_partner_rows = []

    for inst in INSTITUTES + ["Group 24 Combined"]:
        if inst == "Group 24 Combined":
            sub = combined_papers
        else:
            sub = inst_papers[inst_papers["institution"] == inst]

        tot = len(sub)
        has_coauth = (sub["coauthor_institutes"] != "").sum()
        cites_ind = (sub["cites_indian_inst"] == "TRUE").sum()
        cited_ind = (sub["cited_by_indian_inst"] == "TRUE").sum()

        conn_rows.append({
            "institution": inst,
            "total_papers": tot,
            "papers_with_indian_coauthors": has_coauth,
            "indian_coauthor_pct": round(has_coauth / tot * 100.0, 2) if tot > 0 else 0.0,
            "cites_indian_inst_count": cites_ind,
            "cites_indian_inst_pct": round(cites_ind / tot * 100.0, 2) if tot > 0 else 0.0,
            "cited_by_indian_inst_count": cited_ind,
            "cited_by_indian_inst_pct": round(cited_ind / tot * 100.0, 2) if tot > 0 else 0.0,
        })

        # Top 10 Indian partners
        partner_counts: Counter = Counter()
        for coauth_str in sub["coauthor_institutes"]:
            if coauth_str:
                for p in str(coauth_str).split(";"):
                    p_clean = p.strip()
                    if p_clean:
                        partner_counts[p_clean] += 1

        rank = 1
        for partner_inst, cnt in partner_counts.most_common(10):
            top_partner_rows.append({
                "institution": inst,
                "rank": rank,
                "partner_institution": partner_inst,
                "collaborative_papers": cnt,
                "share_pct": round(cnt / tot * 100.0, 2) if tot > 0 else 0.0,
            })
            rank += 1

    df_conn = pd.DataFrame(conn_rows)
    df_conn.to_csv(tables_dir / "indian_connections_summary.csv", index=False)

    df_partners = pd.DataFrame(top_partner_rows)
    df_partners.to_csv(tables_dir / "indian_partner_institutions.csv", index=False)

    logger.info("✓ All 12 metric tables computed and saved to stats/tables/ successfully.")


if __name__ == "__main__":
    run_metrics_computation()
