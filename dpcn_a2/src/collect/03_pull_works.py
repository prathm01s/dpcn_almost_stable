"""Step 03: Pull all works per institute (OpenAlex) 2016–2026.

Fetches works using cursor pagination, saves raw pages to:
  data/raw/openalex/works/<inst>/<year>/page_NNNN.jsonl.gz
Records manifest:
  data/raw/openalex/works/manifest.json
Compiles:
  data/interim/works_core.parquet
"""

import gzip
import json
import os
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import yaml

from src.common.http import http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE

logger = get_logger("03_pull_works")

SELECT_FIELDS = (
    "id,doi,title,display_name,publication_year,publication_date,type,language,"
    "is_retracted,is_paratext,cited_by_count,counts_by_year,authorships,"
    "primary_location,best_oa_location,biblio,primary_topic,topics,"
    "referenced_works,referenced_works_count,ids"
)


def pull_institute_year(
    inst_key: str,
    openalex_id: str,
    year: int,
    raw_base_dir: Path,
) -> Dict[str, Any]:
    """Fetch all works for a given institute and year using cursor pagination."""
    year_dir = raw_base_dir / inst_key / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    clean_id = openalex_id.split("/")[-1]
    url = f"{OPENALEX_BASE}/works"
    params = {
        "filter": f"authorships.institutions.id:{clean_id},publication_year:{year}",
        "select": SELECT_FIELDS,
        "per_page": 100,
        "cursor": "*",
    }

    manifest_record = {
        "inst_key": inst_key,
        "year": year,
        "openalex_id": openalex_id,
        "expected_count": 0,
        "fetched_count": 0,
        "pages": 0,
        "status": "in_progress",
    }

    page_idx = 1
    total_fetched = 0
    all_works: List[Dict[str, Any]] = []

    while True:
        page_file = year_dir / f"page_{page_idx:04d}.jsonl.gz"

        # Check if page file already exists on disk
        page_data = None
        if page_file.exists():
            try:
                page_works = []
                with gzip.open(page_file, "rt", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            page_works.append(json.loads(line))
                total_fetched += len(page_works)
                all_works.extend(page_works)
                page_idx += 1
                # If page had < 100, that was the last page
                if len(page_works) < 100:
                    break
                continue
            except Exception:
                page_data = None

        # Network fetch via cached http client
        data = http_client.get_json(url, params=params, use_cache=True)
        meta = data.get("meta", {})
        if page_idx == 1:
            manifest_record["expected_count"] = meta.get("count", 0)

        results = data.get("results", [])
        if not results:
            break

        # Save to page file
        with gzip.open(page_file, "wt", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item) + "\n")

        total_fetched += len(results)
        all_works.extend(results)
        page_idx += 1

        next_cursor = meta.get("next_cursor")
        if not next_cursor or len(results) < 100:
            break
        params["cursor"] = next_cursor

    manifest_record["fetched_count"] = total_fetched
    manifest_record["pages"] = page_idx - 1
    manifest_record["status"] = "complete"

    expected = manifest_record["expected_count"]
    if expected > 0:
        assert total_fetched == expected, (
            f"Count mismatch for {inst_key} {year}: fetched {total_fetched} != expected {expected}"
        )

    logger.info(f"✓ {inst_key} {year}: fetched {total_fetched}/{expected} works in {page_idx-1} pages")
    return manifest_record


def run_step_03() -> None:
    logger.info("Starting Step 03: Pull all works per institute 2016–2026...")

    with open("config/institutions.yaml", "r", encoding="utf-8") as f:
        inst_config = yaml.safe_load(f)

    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    start_year = settings["years"]["start"]
    end_year = settings["years"]["end"]

    raw_base_dir = Path("data/raw/openalex/works")
    raw_base_dir.mkdir(parents=True, exist_ok=True)
    interim_dir = Path("data/interim")
    interim_dir.mkdir(parents=True, exist_ok=True)

    manifest_records = []
    all_collected_works: List[Dict[str, Any]] = []
    seen_work_ids = set()

    for inst_key in ["ncl", "iict", "cecri"]:
        meta = inst_config.get(inst_key, {})
        oa_ids = meta.get("openalex_institution_ids", [])
        assert len(oa_ids) > 0, f"No OpenAlex ID configured for {inst_key}"
        oa_id = oa_ids[0]

        for year in range(start_year, end_year + 1):
            rec = pull_institute_year(inst_key, oa_id, year, raw_base_dir)
            manifest_records.append(rec)

    # Save manifest
    manifest_path = raw_base_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_records, f, indent=2)
    logger.info(f"Saved manifest to {manifest_path}")

    # Now assemble all raw works into a unified works_core table
    logger.info("Compiling works into data/interim/works_core.parquet...")
    for inst_key in ["ncl", "iict", "cecri"]:
        for year in range(start_year, end_year + 1):
            year_dir = raw_base_dir / inst_key / str(year)
            for page_file in sorted(year_dir.glob("page_*.jsonl.gz")):
                with gzip.open(page_file, "rt", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        w = json.loads(line)
                        wid = w.get("id")
                        if wid and wid not in seen_work_ids:
                            seen_work_ids.add(wid)
                            # Flatten minimal row for interim dataframe
                            primary_loc = w.get("primary_location") or {}
                            source = primary_loc.get("source") or {}
                            primary_topic = w.get("primary_topic") or {}

                            all_collected_works.append({
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

    df = pd.DataFrame(all_collected_works)
    parquet_path = interim_dir / "works_core.parquet"
    df.to_parquet(parquet_path, index=False)
    logger.info(f"✓ Saved {len(df)} distinct works to {parquet_path}")
    logger.info("✓ Step 03 complete successfully.")


if __name__ == "__main__":
    run_step_03()
