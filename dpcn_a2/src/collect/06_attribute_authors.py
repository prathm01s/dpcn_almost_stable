"""Step 06: Authorship explosion, institution attribution, and name canonicalization.

Attributes authorships to:
- CSIR-NCL (I3125981224)
- CSIR-IICT (I55664587)
- CSIR-CECRI (I106349282)

Identifies co-author institutions for Step 10.
Generates:
- data/interim/author_aliases.parquet
- data/interim/paper_authors_attributed.parquet
"""

import collections
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import pandas as pd
import yaml

from src.common.logging import get_logger
from src.common.names import clean_name

logger = get_logger("06_attribute_authors")

INSTITUTION_MAP = {
    "https://openalex.org/I3125981224": "CSIR-NCL",
    "https://openalex.org/I55664587": "CSIR-IICT",
    "https://openalex.org/I106349282": "CSIR-CECRI",
}

SHORT_KEY_MAP = {
    "CSIR-NCL": "ncl",
    "CSIR-IICT": "iict",
    "CSIR-CECRI": "cecri",
}

REGEX_NCL = re.compile(r"\b(national\s+chemical\s+laboratory|csir[\s\-–]*ncl|ncl\s*,?\s*pune)\b", re.IGNORECASE)
REGEX_IICT = re.compile(r"\b(indian\s+institute\s+of\s+chemical\s+technology|csir[\s\-–]*iict|iict\s*,?\s*hyderabad|regional\s+research\s+laboratory\s*,?\s*hyderabad)\b", re.IGNORECASE)
REGEX_CECRI = re.compile(r"\b(central\s+electrochemical\s+research\s+institute|csir[\s\-–]*cecri|cecri\s*,?\s*karaikudi)\b", re.IGNORECASE)


def identify_assigned_institutions(authorship: Dict[str, Any]) -> List[str]:
    """Determine which of our three assigned institutes this authorship belongs to."""
    matched_insts: Set[str] = set()

    # 1. Match by OpenAlex Institution IDs
    for inst in authorship.get("institutions") or []:
        iid = inst.get("id")
        if iid in INSTITUTION_MAP:
            matched_insts.add(INSTITUTION_MAP[iid])

    # 2. Match by raw affiliation strings if no ID matched
    if not matched_insts:
        raw_strings = authorship.get("raw_affiliation_strings") or []
        combined_text = " | ".join(raw_strings)
        if combined_text:
            if REGEX_NCL.search(combined_text):
                matched_insts.add("CSIR-NCL")
            if REGEX_IICT.search(combined_text):
                matched_insts.add("CSIR-IICT")
            if REGEX_CECRI.search(combined_text):
                matched_insts.add("CSIR-CECRI")

    return sorted(list(matched_insts))


def run_step_06() -> None:
    logger.info("Starting Step 06: Authorship explosion and attribution...")

    interim_dir = Path("data/interim")
    works_path = interim_dir / "works_filtered.parquet"
    assert works_path.exists(), "works_filtered.parquet not found"

    df = pd.read_parquet(works_path)
    logger.info(f"Processing authorships for {len(df)} peer-reviewed works...")

    author_name_counts: Dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    author_orcids: Dict[str, Set[str]] = collections.defaultdict(set)

    attributed_rows: List[Dict[str, Any]] = []

    for _, work in df.iterrows():
        raw_authorships_str = work.get("raw_authorships")
        if not raw_authorships_str or pd.isna(raw_authorships_str):
            continue

        try:
            authorships = json.loads(raw_authorships_str)
        except Exception:
            continue

        work_id = work.get("work_id")
        doi = work.get("doi") or ""
        title = work.get("title") or ""
        year = int(work.get("publication_year"))
        work_type = work.get("type")
        source_name = work.get("source_name") or ""
        issn_l = work.get("issn_l") or ""
        citations = int(work.get("cited_by_count") or 0)

        # Track external coauthor institutions for Step 10
        external_coauthor_insts: List[Dict[str, Any]] = []

        work_assigned_rows: List[Dict[str, Any]] = []

        for auth in authorships:
            author_obj = auth.get("author") or {}
            author_id = author_obj.get("id") or ""
            author_display_name = author_obj.get("display_name") or auth.get("raw_author_name") or ""
            author_orcid = author_obj.get("orcid") or ""

            if author_id and author_display_name:
                author_name_counts[author_id][author_display_name] += 1
                if author_orcid:
                    author_orcids[author_id].add(author_orcid)

            assigned_institutes = identify_assigned_institutions(auth)

            if assigned_institutes:
                for inst_name in assigned_institutes:
                    work_assigned_rows.append({
                        "work_id": work_id,
                        "doi": doi,
                        "title": title,
                        "year": year,
                        "type": work_type,
                        "journal_name": source_name,
                        "issn_l": issn_l,
                        "citations": citations,
                        "institution": inst_name,
                        "inst_key": SHORT_KEY_MAP[inst_name],
                        "author_id": author_id,
                        "raw_author_name": author_display_name,
                        "author_position": auth.get("author_position"),
                        "is_corresponding": bool(auth.get("is_corresponding")),
                        "multi_inst_authorship": len(assigned_institutes) > 1,
                    })
            else:
                # External coauthor
                for ext_inst in auth.get("institutions") or []:
                    external_coauthor_insts.append({
                        "id": ext_inst.get("id"),
                        "display_name": ext_inst.get("display_name"),
                        "ror": ext_inst.get("ror"),
                        "country_code": ext_inst.get("country_code"),
                        "type": ext_inst.get("type"),
                    })

        # Append assigned rows
        for row in work_assigned_rows:
            row["external_coauthor_insts"] = json.dumps(external_coauthor_insts)
            attributed_rows.append(row)

    # Build canonical name mapping (most frequent display name)
    author_canonical_names = {}
    alias_records = []
    for aid, counter in author_name_counts.items():
        canonical = counter.most_common(1)[0][0]
        author_canonical_names[aid] = canonical
        orcids = list(author_orcids.get(aid, []))
        alias_records.append({
            "author_id": aid,
            "canonical_name": canonical,
            "name_norm": clean_name(canonical),
            "orcid": orcids[0] if orcids else "",
            "aliases": json.dumps(list(counter.keys())),
            "total_authorships": sum(counter.values()),
        })

    # Save author_aliases
    alias_df = pd.DataFrame(alias_records)
    alias_path = interim_dir / "author_aliases.parquet"
    alias_df.to_parquet(alias_path, index=False)
    logger.info(f"Saved {len(alias_df)} author aliases to {alias_path}")

    # Set harmonized author name in attributed rows
    for row in attributed_rows:
        aid = row.get("author_id")
        if aid and aid in author_canonical_names:
            row["author"] = author_canonical_names[aid]
        else:
            row["author"] = row.get("raw_author_name")

    df_attr = pd.DataFrame(attributed_rows)
    # Deduplicate exact (institution, work_id, author_id)
    df_attr = df_attr.drop_duplicates(subset=["institution", "work_id", "author_id"], keep="first")

    out_path = interim_dir / "paper_authors_attributed.parquet"
    df_attr.to_parquet(out_path, index=False)
    logger.info(f"✓ Saved {len(df_attr)} (paper × assigned-institute-author) rows to {out_path}")
    print(df_attr["institution"].value_counts())
    logger.info("✓ Step 06 complete successfully.")


if __name__ == "__main__":
    run_step_06()
