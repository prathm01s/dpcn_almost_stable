"""Step 05: Work-level filtering, typing, and DOI deduplication.

Applies:
- Years: 2016–2026
- Exclusion of paratext and non-peer-reviewed types (editorials, errata, book chapters)
- Type mapping: 'journal' vs 'conference'
- Deduplication by lowercase DOI (preserving highest citation count)
- Normalized DOI formatting

Outputs:
- data/interim/works_filtered.parquet
- data/interim/excluded_works.csv
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("05_filter_works")

DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")

ACCEPTED_TYPES = {"article", "review", "letter"}


def clean_str(val: Any) -> str:
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def normalize_doi(raw_doi: Any) -> str:
    """Normalize DOI to standard https://doi.org/10.xxxx/... format."""
    clean = clean_str(raw_doi).lower()
    if not clean:
        return ""
    clean = re.sub(r"^https?://(dx\.)?doi\.org/", "", clean).strip()
    if DOI_REGEX.match(clean):
        return f"https://doi.org/{clean}"
    return ""


def determine_type(row: pd.Series) -> Tuple[Optional[str], str]:
    """Determine whether work is journal or conference, or if it should be excluded."""
    work_type = clean_str(row.get("type")).lower()
    source_type = clean_str(row.get("source_type")).lower()
    is_paratext = bool(row.get("is_paratext")) and not pd.isna(row.get("is_paratext"))

    if is_paratext:
        return None, "paratext"

    if work_type in {"editorial", "erratum", "correction", "dataset", "dissertation", "book-chapter", "book", "monograph", "reference-entry"}:
        return None, f"excluded_work_type_{work_type}"

    # Check for conference
    if source_type == "conference" or work_type in {"proceedings-article", "conference-paper"}:
        return "conference", "conference"

    # Check for journal
    if source_type == "journal" or work_type in ACCEPTED_TYPES:
        return "journal", "journal"

    return None, f"unsupported_source_type_{source_type}"


def run_step_05() -> None:
    logger.info("Starting Step 05: Work-level filtering and typing...")

    interim_dir = Path("data/interim")
    works_path = interim_dir / "works_core.parquet"
    assert works_path.exists(), "works_core.parquet not found"

    df = pd.read_parquet(works_path)
    logger.info(f"Loaded {len(df)} works from {works_path}")

    accepted_rows: List[Dict[str, Any]] = []
    excluded_rows: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        year = int(row.get("publication_year") or 0)
        if year < 2016 or year > 2026:
            rec = row.to_dict()
            rec["exclusion_reason"] = f"year_{year}_out_of_range"
            excluded_rows.append(rec)
            continue

        assigned_type, reason = determine_type(row)
        if assigned_type is None:
            rec = row.to_dict()
            rec["exclusion_reason"] = reason
            excluded_rows.append(rec)
            continue

        norm_doi = normalize_doi(row.get("doi"))

        item = row.to_dict()
        item["type"] = assigned_type
        item["doi"] = norm_doi
        accepted_rows.append(item)

    # Save excluded works
    df_ex = pd.DataFrame(excluded_rows)
    df_ex.to_csv(interim_dir / "excluded_works.csv", index=False)
    logger.info(f"Excluded {len(df_ex)} works; saved to {interim_dir / 'excluded_works.csv'}")

    # Deduplicate accepted works
    df_acc = pd.DataFrame(accepted_rows)

    # Sort so that if duplicate DOIs exist, we keep the one with higher citations
    df_acc = df_acc.sort_values(by=["cited_by_count"], ascending=False)

    # Deduplicate by work_id first
    df_acc = df_acc.drop_duplicates(subset=["work_id"], keep="first")

    # Deduplicate by non-empty DOI
    with_doi = df_acc[df_acc["doi"] != ""]
    without_doi = df_acc[df_acc["doi"] == ""]

    with_doi_dedup = with_doi.drop_duplicates(subset=["doi"], keep="first")
    df_final = pd.concat([with_doi_dedup, without_doi], ignore_index=True)

    out_path = interim_dir / "works_filtered.parquet"
    df_final.to_parquet(out_path, index=False)
    logger.info(f"✓ Saved {len(df_final)} filtered & deduplicated peer-reviewed works to {out_path}")
    logger.info("✓ Step 05 complete successfully.")


if __name__ == "__main__":
    run_step_05()
