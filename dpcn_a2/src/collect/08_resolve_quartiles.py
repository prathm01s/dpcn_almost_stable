"""Step 08: Resolve journal ISSNs and SCImago best quartiles (Q1–Q4).

Uses sjr_journals.rda panel covering 2016–2025.
Matching priority:
1. Exact normalized ISSN match in publication year
2. Fallback to nearest year (±2) for ISSN
3. Fallback to normalized journal title match
4. For 2026 papers, uses 2025 SJR data and flags quartile_year_used=2025

Outputs:
- data/interim/source_table.parquet
- Updates data/interim/paper_authors_attributed.parquet with quartile, quartile_year_used, quartile_match_method
"""

import collections
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd
import pyreadr

from src.common.issn import is_valid_issn, normalize_issn, to_sjr_issn
from src.common.logging import get_logger

logger = get_logger("08_resolve_quartiles")


def clean_title_for_match(title: str) -> str:
    """Normalize journal title for fallback matching."""
    if not title or pd.isna(title):
        return ""
    t = str(title).lower().strip()
    t = re.sub(r"&", "and", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_issns_from_sjr(issn_str: str) -> List[str]:
    """Parse comma-separated 8-digit ISSNs from SCImago."""
    if not issn_str or pd.isna(issn_str):
        return []
    res = []
    for item in str(issn_str).split(","):
        clean = item.strip().replace("-", "").upper()
        if len(clean) == 8:
            res.append(clean)
    return res


def run_step_08() -> None:
    logger.info("Starting Step 08: Resolve journal quartiles...")

    interim_dir = Path("data/interim")
    external_dir = Path("data/external")
    authors_path = interim_dir / "paper_authors_attributed.parquet"
    works_path = interim_dir / "works_filtered.parquet"
    sjr_path = external_dir / "sjr_journals.rda"

    assert sjr_path.exists(), "sjr_journals.rda not found"
    assert authors_path.exists(), "paper_authors_attributed.parquet not found"

    logger.info("Loading SCImago journal panel from sjr_journals.rda...")
    res = pyreadr.read_r(str(sjr_path))
    df_sjr = list(res.values())[0]

    # Filter SJR to 2016-2025
    df_sjr["year_int"] = df_sjr["year"].astype(int)
    df_sjr = df_sjr[(df_sjr["year_int"] >= 2014) & (df_sjr["year_int"] <= 2025)]
    logger.info(f"Loaded {len(df_sjr)} SJR records from 2014–2025")

    # Index SCImago by (year, sjr_issn) -> quartile
    issn_year_map: Dict[Tuple[int, str], str] = {}
    title_year_map: Dict[Tuple[int, str], str] = {}
    issn_any_year: Dict[str, Dict[int, str]] = collections.defaultdict(dict)

    for _, row in df_sjr.iterrows():
        yr = int(row["year_int"])
        q = str(row["sjr_best_quartile"] or "").strip().upper()
        if q not in {"Q1", "Q2", "Q3", "Q4"}:
            continue

        issn_list = parse_issns_from_sjr(row["issn"])
        for issn_item in issn_list:
            issn_year_map[(yr, issn_item)] = q
            issn_any_year[issn_item][yr] = q

        norm_title = clean_title_for_match(row["title"])
        if norm_title:
            title_year_map[(yr, norm_title)] = q

    logger.info(f"Indexed {len(issn_year_map)} (year, ISSN) quartile mappings")

    # Load works
    df_works = pd.read_parquet(works_path)
    work_quartile_map: Dict[str, Dict[str, Any]] = {}

    for _, w in df_works.iterrows():
        wid = w["work_id"]
        w_type = w.get("type")
        w_year = int(w.get("publication_year"))
        title = w.get("source_name") or ""
        norm_title = clean_title_for_match(title)

        # Collect paper ISSNs
        paper_issns: List[str] = []
        if w.get("issn_l"):
            sjr_issn = to_sjr_issn(str(w["issn_l"]))
            if sjr_issn:
                paper_issns.append(sjr_issn)

        raw_issn_str = w.get("issn")
        if raw_issn_str and not pd.isna(raw_issn_str):
            try:
                for item in json.loads(raw_issn_str):
                    sjr_issn = to_sjr_issn(str(item))
                    if sjr_issn and sjr_issn not in paper_issns:
                        paper_issns.append(sjr_issn)
            except Exception:
                pass

        if w_type != "journal":
            # Conference
            work_quartile_map[wid] = {
                "quartile": "",  # Unranked conference
                "quartile_year_used": "",
                "quartile_match_method": "none",
            }
            continue

        target_year = 2025 if w_year == 2026 else w_year

        matched_q = ""
        matched_method = "none"
        used_year = ""

        # 1. Exact ISSN match in publication year
        for issn_item in paper_issns:
            if (target_year, issn_item) in issn_year_map:
                matched_q = issn_year_map[(target_year, issn_item)]
                matched_method = "issn"
                used_year = str(target_year)
                break

        # 2. Nearest year ISSN match (within +/- 2 years)
        if not matched_q:
            for issn_item in paper_issns:
                if issn_item in issn_any_year:
                    available_years = sorted(issn_any_year[issn_item].keys())
                    for offset in [1, -1, 2, -2]:
                        cand_yr = target_year + offset
                        if cand_yr in issn_any_year[issn_item]:
                            matched_q = issn_any_year[issn_item][cand_yr]
                            matched_method = "nearest_year"
                            used_year = str(cand_yr)
                            break
                    if matched_q:
                        break

        # 3. Exact title match
        if not matched_q and norm_title:
            if (target_year, norm_title) in title_year_map:
                matched_q = title_year_map[(target_year, norm_title)]
                matched_method = "title"
                used_year = str(target_year)

        work_quartile_map[wid] = {
            "quartile": matched_q,
            "quartile_year_used": used_year,
            "quartile_match_method": matched_method,
        }

    # Update paper_authors_attributed.parquet
    df_authors = pd.read_parquet(authors_path)
    updated_authors: List[Dict[str, Any]] = []

    for _, row in df_authors.iterrows():
        rec = row.to_dict()
        wid = row.get("work_id")
        q_info = work_quartile_map.get(wid, {"quartile": "", "quartile_year_used": "", "quartile_match_method": "none"})
        rec["quartile"] = q_info["quartile"]
        rec["quartile_year_used"] = q_info["quartile_year_used"]
        rec["quartile_match_method"] = q_info["quartile_match_method"]
        raw_issn = rec.get("issn_l")
        norm_issn = normalize_issn(str(raw_issn)) if (raw_issn is not None and not pd.isna(raw_issn)) else None
        rec["issn"] = norm_issn or "" if rec.get("type") == "journal" else ""
        updated_authors.append(rec)

    df_authors_updated = pd.DataFrame(updated_authors)
    df_authors_updated.to_parquet(authors_path, index=False)
    logger.info(f"✓ Updated {len(df_authors_updated)} author rows with quartiles in {authors_path}")

    # Print summary statistics
    journal_rows = df_authors_updated[df_authors_updated["type"] == "journal"]
    print("Quartile distribution across journal rows:")
    print(journal_rows["quartile"].value_counts(dropna=False))

    logger.info("✓ Step 08 complete successfully.")


if __name__ == "__main__":
    run_step_08()
