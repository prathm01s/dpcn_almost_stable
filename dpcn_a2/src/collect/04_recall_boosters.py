"""Step 04: Recall Booster to find papers OpenAlex mis-tagged or tagged only to parent CSIR/AcSIR.

Searches:
1. Parent CSIR (I66760702) works mentioning NCL/Pune, IICT/Hyderabad, CECRI/Karaikudi
2. AcSIR (I99364266) works mentioning NCL, IICT, CECRI

Validates raw affiliation strings against exclusion lists and adds verified works to works_core.
Output:
- data/interim/recall_candidates.parquet
- Updates data/interim/works_core.parquet
"""

import gzip
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import pandas as pd
import yaml

from src.common.http import http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE, fetch_cursor_pages

logger = get_logger("04_recall_boosters")

SELECT_FIELDS = (
    "id,doi,title,display_name,publication_year,publication_date,type,language,"
    "is_retracted,is_paratext,cited_by_count,counts_by_year,authorships,"
    "primary_location,best_oa_location,biblio,primary_topic,topics,"
    "referenced_works,referenced_works_count,ids"
)

# Regex patterns for validation
REGEX_NCL = re.compile(r"\b(national\s+chemical\s+laboratory|csir[\s\-–]*ncl|ncl\s*,?\s*pune)\b", re.IGNORECASE)
REGEX_IICT = re.compile(r"\b(indian\s+institute\s+of\s+chemical\s+technology|csir[\s\-–]*iict|iict\s*,?\s*hyderabad|regional\s+research\s+laboratory\s*,?\s*hyderabad)\b", re.IGNORECASE)
REGEX_CECRI = re.compile(r"\b(central\s+electrochemical\s+research\s+institute|csir[\s\-–]*cecri|cecri\s*,?\s*karaikudi)\b", re.IGNORECASE)

EXCLUDE_NCL = re.compile(r"\b(newcastle|institute\s+of\s+chemical\s+technology|ict\s+mumbai|iicb)\b", re.IGNORECASE)
EXCLUDE_IICT = re.compile(r"\b(institute\s+of\s+chemical\s+technology|ict\s+mumbai|iicb|ccmb|csmcri|clri|cftri|niist|nml|npl)\b", re.IGNORECASE)
EXCLUDE_CECRI = re.compile(r"\b(ceeri|cmeri|crri|cbri|cimfr|cdri|clri)\b", re.IGNORECASE)


def validate_work_affiliation(work: Dict[str, Any], inst_key: str) -> Tuple[bool, str]:
    """Validate whether work's raw affiliations truly belong to the institute."""
    authorships = work.get("authorships") or []
    all_raw_strings = []
    for a in authorships:
        for s in (a.get("raw_affiliation_strings") or []):
            all_raw_strings.append(s)

    combined_text = " | ".join(all_raw_strings)
    if not combined_text:
        return False, "No raw affiliation strings"

    if inst_key == "ncl":
        if REGEX_NCL.search(combined_text) and not EXCLUDE_NCL.search(combined_text):
            return True, "Validated NCL variant"
    elif inst_key == "iict":
        if REGEX_IICT.search(combined_text) and not EXCLUDE_IICT.search(combined_text):
            return True, "Validated IICT variant"
    elif inst_key == "cecri":
        if REGEX_CECRI.search(combined_text) and not EXCLUDE_CECRI.search(combined_text):
            return True, "Validated CECRI variant"

    return False, "Failed string validation or matched excluded entity"


def run_step_04() -> None:
    logger.info("Starting Step 04: Recall boosters...")

    interim_dir = Path("data/interim")
    works_core_path = interim_dir / "works_core.parquet"
    assert works_core_path.exists(), "works_core.parquet not found. Run step 03 first."

    df_core = pd.read_parquet(works_core_path)
    seen_work_ids: Set[str] = set(df_core["work_id"].dropna().tolist())
    logger.info(f"Loaded {len(seen_work_ids)} existing works from works_core.parquet")

    cand_path = interim_dir / "recall_candidates.parquet"
    if cand_path.exists():
        cand_df = pd.read_parquet(cand_path)
        logger.info(f"Loaded existing {len(cand_df)} candidates from {cand_path}")
        logger.info("✓ Step 04 complete successfully (re-used existing candidates).")
        return

    parent_queries = [
        ("ncl", "I66760702", "Pune"),
        ("iict", "I66760702", "Hyderabad"),
        ("cecri", "I66760702", "Karaikudi"),
        ("ncl", "I99364266", "NCL"),
        ("iict", "I99364266", "IICT"),
        ("cecri", "I99364266", "CECRI"),
    ]

    candidate_records: List[Dict[str, Any]] = []
    new_validated_works: List[Dict[str, Any]] = []

    for inst_key, parent_id, query_term in parent_queries:
        logger.info(f"Querying booster: {inst_key} via parent {parent_id} with search '{query_term}'...")
        params = {
            "filter": f"authorships.institutions.id:{parent_id},raw_affiliation_strings.search:{query_term},publication_year:2016-2026",
            "select": SELECT_FIELDS,
            "per_page": 100,
        }

        try:
            for page in fetch_cursor_pages("works", params, max_pages=15):
                results = page.get("results", [])
                if not results:
                    break

                for w in results:
                    wid = w.get("id")
                    if not wid:
                        continue

                    is_already_known = wid in seen_work_ids
                    valid, reason = validate_work_affiliation(w, inst_key)

                    candidate_records.append({
                        "work_id": wid,
                        "target_inst": inst_key,
                        "booster_source": parent_id,
                        "query_term": query_term,
                        "is_already_known": is_already_known,
                        "is_valid": valid,
                        "reason": reason,
                        "title": w.get("title") or w.get("display_name"),
                        "publication_year": w.get("publication_year"),
                    })

                    if valid and not is_already_known:
                        seen_work_ids.add(wid)
                        primary_loc = w.get("primary_location") or {}
                        source = primary_loc.get("source") or {}
                        primary_topic = w.get("primary_topic") or {}

                        new_validated_works.append({
                            "work_id": wid,
                            "doi": (w.get("doi") or "").lower(),
                            "title": w.get("title") or w.get("display_name") or "",
                            "publication_year": w.get("publication_year"),
                            "publication_date": w.get("publication_date"),
                            "type": w.get("type"),
                            "language": w.get("language"),
                            "is_retracted": bool(w.get("is_retracted")),
                            "is_paratext": bool(w.get("is_paratext")),
                            "cited_by_count": int(w.get("cited_by_count") or 0),
                            "counts_by_year": json.dumps(w.get("counts_by_year") or []),
                            "source_id": source.get("id"),
                            "source_name": source.get("display_name"),
                            "source_type": source.get("type"),
                            "issn_l": source.get("issn_l"),
                            "issn": json.dumps(source.get("issn") or []),
                            "primary_topic_id": primary_topic.get("id"),
                            "primary_topic_name": primary_topic.get("display_name"),
                            "subfield": (primary_topic.get("subfield") or {}).get("display_name"),
                            "field": (primary_topic.get("field") or {}).get("display_name"),
                            "domain": (primary_topic.get("domain") or {}).get("display_name"),
                            "referenced_works": json.dumps(w.get("referenced_works") or []),
                            "referenced_works_count": int(w.get("referenced_works_count") or 0),
                            "raw_authorships": json.dumps(w.get("authorships") or []),
                            "is_partial_year": bool(w.get("publication_year") == 2026),
                        })
        except Exception as e:
            logger.warning(f"Booster query for {inst_key} ({query_term}) stopped: {e}")
            continue

    # Save candidates
    cand_df = pd.DataFrame(candidate_records)
    cand_path = interim_dir / "recall_candidates.parquet"
    cand_df.to_parquet(cand_path, index=False)
    logger.info(f"Saved {len(cand_df)} candidates to {cand_path}")

    # Append new validated works if any
    if new_validated_works:
        logger.info(f"Adding {len(new_validated_works)} recall-boosted works to works_core.parquet")
        df_new = pd.DataFrame(new_validated_works)
        df_combined = pd.concat([df_core, df_new], ignore_index=True).drop_duplicates(subset=["work_id"])
        df_combined.to_parquet(works_core_path, index=False)
        logger.info(f"Updated works_core.parquet has {len(df_combined)} total distinct works")
    else:
        logger.info("No new previously uncaptured works found; works_core remains at full recall.")

    logger.info("✓ Step 04 complete successfully.")


if __name__ == "__main__":
    run_step_04()
