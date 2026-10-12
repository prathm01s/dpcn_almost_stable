"""Step 14: Export final primary dataset group24_data.csv and extended dataset.

Produces:
- data/final/group24_data.csv (exact 14 required columns in exact order)
- data/final/group24_data_extended.csv (same rows + rich metadata)
- data/MANIFEST.json
"""

import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("14_export")

COLLECTED_AT = "2026-10-13T01:00:00Z"

MAIN_COLUMNS = [
    "group",
    "institution",
    "author",
    "title",
    "year",
    "type",
    "journal_name",
    "issn",
    "doi",
    "citations",
    "quartile",
    "coauthor_institutes",
    "cites_indian_inst",
    "cited_by_indian_inst",
]


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def run_step_14() -> None:
    logger.info("Starting Step 14: Final export...")

    interim_dir = Path("data/interim")
    final_dir = Path("data/final")
    final_dir.mkdir(parents=True, exist_ok=True)

    authors_path = interim_dir / "paper_authors_attributed.parquet"
    works_path = interim_dir / "works_filtered.parquet"

    assert authors_path.exists(), "paper_authors_attributed.parquet not found"
    assert works_path.exists(), "works_filtered.parquet not found"

    df_authors = pd.read_parquet(authors_path)
    df_works = pd.read_parquet(works_path)

    # Join topic hierarchy from works_filtered
    work_topic_map = {}
    for _, w in df_works.iterrows():
        work_topic_map[w["work_id"]] = {
            "source_id": w.get("source_id") or "",
            "source_type": w.get("source_type") or "",
            "field": w.get("field") or "Unclassified",
            "subfield": w.get("subfield") or "Unclassified",
            "domain": w.get("domain") or "Unclassified",
            "primary_topic": w.get("primary_topic_name") or "Unclassified",
            "is_retracted": bool(w.get("is_retracted")),
        }

    # Ensure consistent sorting: institution, year (descending), title, author
    df_authors = df_authors.sort_values(by=["institution", "year", "title", "author"], ascending=[True, False, True, True])

    # Build main dataset rows
    main_rows: List[Dict[str, Any]] = []
    extended_rows: List[Dict[str, Any]] = []

    for _, row in df_authors.iterrows():
        wid = row["work_id"]
        topic_info = work_topic_map.get(wid, {})

        # Clean string fields to prevent CSV formatting issues
        title_clean = str(row.get("title") or "").replace("\r", " ").replace("\n", " ").strip()
        j_val = row.get("journal_name")
        if pd.isna(j_val) or str(j_val).lower() == "nan":
            journal_clean = ""
        else:
            journal_clean = str(j_val).replace("\r", " ").replace("\n", " ").strip()
        author_clean = str(row.get("author") or "").replace("\r", " ").replace("\n", " ").strip()

        # 14 primary columns
        main_rec = {
            "group": 24,
            "institution": str(row["institution"]),
            "author": author_clean,
            "title": title_clean,
            "year": int(row["year"]),
            "type": str(row["type"]).lower(),
            "journal_name": journal_clean,
            "issn": str(row.get("issn") or "").strip() if str(row.get("type")).lower() == "journal" else "",
            "doi": str(row.get("doi") or "").strip(),
            "citations": int(row.get("citations") or 0),
            "quartile": str(row.get("quartile") or "").strip(),
            "coauthor_institutes": str(row.get("coauthor_institutes") or "").strip(),
            "cites_indian_inst": str(row["cites_indian_inst"]).upper(),
            "cited_by_indian_inst": str(row["cited_by_indian_inst"]).upper(),
        }
        main_rows.append(main_rec)

        # Extended dataset record
        ext_rec = dict(main_rec)
        ext_rec["work_id"] = wid
        ext_rec["author_openalex_id"] = str(row.get("author_id") or "")
        ext_rec["faculty_id"] = str(row.get("faculty_id") or "")
        ext_rec["author_role"] = str(row.get("author_role") or "")
        ext_rec["department"] = str(row.get("department") or "")
        ext_rec["designation"] = str(row.get("designation") or "")
        ext_rec["is_corresponding"] = bool(row.get("is_corresponding"))
        ext_rec["author_position"] = str(row.get("author_position") or "")
        ext_rec["source_id"] = topic_info.get("source_id", "")
        ext_rec["source_type"] = topic_info.get("source_type", "")
        ext_rec["issn_l"] = str(row.get("issn_l") or "")
        ext_rec["quartile_year_used"] = str(row.get("quartile_year_used") or "")
        ext_rec["quartile_match_method"] = str(row.get("quartile_match_method") or "")
        ext_rec["field"] = topic_info.get("field", "")
        ext_rec["subfield"] = topic_info.get("subfield", "")
        ext_rec["domain"] = topic_info.get("domain", "")
        ext_rec["primary_topic"] = topic_info.get("primary_topic", "")
        ext_rec["is_retracted"] = topic_info.get("is_retracted", False)
        ext_rec["is_partial_year"] = bool(row["year"] == 2026)
        ext_rec["multi_inst_authorship"] = bool(row.get("multi_inst_authorship"))
        ext_rec["collected_at"] = COLLECTED_AT
        extended_rows.append(ext_rec)

    # 1. Export group24_data.csv
    df_main = pd.DataFrame(main_rows)[MAIN_COLUMNS]
    main_csv_path = final_dir / "group24_data.csv"
    df_main.to_csv(main_csv_path, index=False, encoding="utf-8")
    logger.info(f"✓ Saved primary dataset to {main_csv_path} ({len(df_main)} rows, exactly {len(MAIN_COLUMNS)} columns)")

    # 2. Export group24_data_extended.csv
    df_ext = pd.DataFrame(extended_rows)
    ext_csv_path = final_dir / "group24_data_extended.csv"
    df_ext.to_csv(ext_csv_path, index=False, encoding="utf-8")
    logger.info(f"✓ Saved extended dataset to {ext_csv_path} ({len(df_ext)} rows, {len(df_ext.columns)} columns)")

    # 3. Export auxiliary and network files required by assignment
    from itertools import combinations
    import shutil

    faculty_src = interim_dir / "faculty_master.csv"
    faculty_dest = final_dir / "faculty_master.csv"
    if faculty_src.exists():
        shutil.copy2(faculty_src, faculty_dest)
        logger.info(f"✓ Copied {faculty_dest}")

    citations_src = interim_dir / "citation_edges_raw.parquet"
    citations_dest = final_dir / "citation_edges_raw.parquet"
    if citations_src.exists():
        shutil.copy2(citations_src, citations_dest)
        logger.info(f"✓ Copied {citations_dest}")

    works_dest = final_dir / "works_table.parquet"
    df_works.to_parquet(works_dest, index=False)
    logger.info(f"✓ Exported {works_dest}")

    # 4. Export citation_network.csv (Required Week 2 deliverable)
    cite_net_path = final_dir / "citation_network.csv"
    if citations_src.exists():
        df_cite_edges = pd.read_parquet(citations_src)
        cite_cols = ["source_doi", "target_doi", "source_inst", "target_inst", "year"]
        df_cite_net = df_cite_edges[cite_cols].copy()
        df_cite_net.to_csv(cite_net_path, index=False, encoding="utf-8")
        logger.info(f"✓ Saved citation network to {cite_net_path} ({len(df_cite_net)} directed edges)")
    else:
        df_cite_net = pd.DataFrame(columns=["source_doi", "target_doi", "source_inst", "target_inst", "year"])
        df_cite_net.to_csv(cite_net_path, index=False, encoding="utf-8")

    # 5. Export authorship_network.csv (Required Week 2 deliverable)
    auth_edges = []
    grouped_papers = df_authors.groupby("work_id")
    for wid, group in grouped_papers:
        if len(group) < 2:
            continue
        doi_val = str(group["doi"].iloc[0] if "doi" in group.columns else "").strip()
        yr_val = int(group["year"].iloc[0])
        distinct_authors = group[["author", "institution"]].drop_duplicates().to_dict("records")
        for a1, a2 in combinations(distinct_authors, 2):
            if a1["author"] == a2["author"]:
                continue
            if a1["author"] > a2["author"]:
                a1, a2 = a2, a1
            auth_edges.append({
                "author_a": a1["author"],
                "author_b": a2["author"],
                "paper_doi": doi_val,
                "inst_a": a1["institution"],
                "inst_b": a2["institution"],
                "year": yr_val,
            })
    df_auth_net = pd.DataFrame(auth_edges)
    auth_net_path = final_dir / "authorship_network.csv"
    df_auth_net.to_csv(auth_net_path, index=False, encoding="utf-8")
    logger.info(f"✓ Saved authorship network to {auth_net_path} ({len(df_auth_net)} undirected edges)")

    # 6. Export indian_connections.csv (Required Week 2 deliverable)
    papers_uniq = df_authors[["institution", "work_id", "citations", "coauthor_institutes"]].drop_duplicates(subset=["institution", "work_id"])
    conn_records = []
    for _, prow in papers_uniq.iterrows():
        y_inst = prow["institution"]
        c_cnt = int(prow["citations"])
        co_str = str(prow.get("coauthor_institutes") or "").strip()
        if not co_str:
            continue
        p_list = [p.strip() for p in co_str.split(";") if p.strip()]
        for p in set(p_list):
            conn_records.append({"your_inst": y_inst, "partner_inst": p, "citations": c_cnt})
    if conn_records:
        df_conn_all = pd.DataFrame(conn_records)
        df_conn_grouped = df_conn_all.groupby(["your_inst", "partner_inst"]).agg(
            shared_papers=("citations", "count"),
            total_citations=("citations", "sum")
        ).reset_index().sort_values(by=["your_inst", "shared_papers"], ascending=[True, False])
    else:
        df_conn_grouped = pd.DataFrame(columns=["your_inst", "partner_inst", "shared_papers", "total_citations"])
    conn_path = final_dir / "indian_connections.csv"
    df_conn_grouped.to_csv(conn_path, index=False, encoding="utf-8")
    logger.info(f"✓ Saved Indian connections to {conn_path} ({len(df_conn_grouped)} partner connections)")

    # 7. Write data/MANIFEST.json and sync to data/final/MANIFEST.json
    manifest_data = {
        "group": 24,
        "cluster": "CSIR Chemistry (Synthetic & Organic Chemistry)",
        "institutions": ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"],
        "collection_date": "2026-10-13",
        "collected_at_utc": COLLECTED_AT,
        "year_window": [2016, 2026],
        "total_rows": len(df_main),
        "total_distinct_papers": df_ext["work_id"].nunique(),
        "rows_by_institution": df_main["institution"].value_counts().to_dict(),
        "files": {
            "group24_data.csv": {
                "path": "data/final/group24_data.csv",
                "sha256": compute_file_sha256(main_csv_path),
                "rows": len(df_main),
                "columns": len(df_main.columns),
            },
            "group24_data_extended.csv": {
                "path": "data/final/group24_data_extended.csv",
                "sha256": compute_file_sha256(ext_csv_path),
                "rows": len(df_ext),
                "columns": len(df_ext.columns),
            },
            "citation_network.csv": {
                "path": "data/final/citation_network.csv",
                "sha256": compute_file_sha256(cite_net_path),
                "rows": len(df_cite_net),
                "columns": len(df_cite_net.columns),
            },
            "authorship_network.csv": {
                "path": "data/final/authorship_network.csv",
                "sha256": compute_file_sha256(auth_net_path),
                "rows": len(df_auth_net),
                "columns": len(df_auth_net.columns),
            },
            "indian_connections.csv": {
                "path": "data/final/indian_connections.csv",
                "sha256": compute_file_sha256(conn_path),
                "rows": len(df_conn_grouped),
                "columns": len(df_conn_grouped.columns),
            },
            "faculty_master.csv": {
                "path": "data/final/faculty_master.csv",
                "sha256": compute_file_sha256(faculty_dest) if faculty_dest.exists() else "",
            },
            "citation_edges_raw.parquet": {
                "path": "data/final/citation_edges_raw.parquet",
                "sha256": compute_file_sha256(citations_dest) if citations_dest.exists() else "",
            },
            "works_table.parquet": {
                "path": "data/final/works_table.parquet",
                "sha256": compute_file_sha256(works_dest),
                "rows": len(df_works),
            },
        },
    }

    manifest_file = Path("data/MANIFEST.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info(f"✓ Saved manifest to {manifest_file}")

    manifest_dest = final_dir / "MANIFEST.json"
    shutil.copy2(manifest_file, manifest_dest)
    logger.info(f"✓ Synced manifest to {manifest_dest}")

    logger.info("✓ Step 14 complete successfully.")


if __name__ == "__main__":
    run_step_14()
