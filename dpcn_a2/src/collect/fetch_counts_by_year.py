"""Fetch yearly citation counts (counts_by_year) from OpenAlex for candidate sleeping beauty works.

Selects works published 2016–2020 with cited_by_count >= 20.
Caches responses to data/cache/openalex/counts_by_year.json for complete idempotency.
"""

import json
from pathlib import Path
from typing import Dict, List
import pandas as pd
from tqdm import tqdm

from src.common.http import http_client
from src.common.logging import get_logger
from src.stats.insights.common import papers

logger = get_logger("fetch_counts_by_year")

CACHE_DIR = Path("data/cache/openalex")
CACHE_FILE = CACHE_DIR / "counts_by_year.json"


def fetch_counts_by_year(force_refresh: bool = False) -> Dict[str, List[Dict[str, int]]]:
    """Fetch counts_by_year for all eligible candidate sleeping beauties.
    
    Returns a dict mapping work_id -> list of {'year': int, 'cited_by_count': int}.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not force_refresh and CACHE_FILE.exists():
        logger.info(f"Loading cached counts_by_year from {CACHE_FILE}")
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    df_p = papers()
    # Filter candidates: 2016-2020 with >= 20 citations
    cand = df_p[
        (df_p["year"] >= 2016) & (df_p["year"] <= 2020) & (df_p["citations"] >= 20)
    ].copy()
    work_ids = cand["work_id"].tolist()
    logger.info(f"Identified {len(work_ids)} candidate works published 2016–2020 with >= 20 citations")

    results: Dict[str, List[Dict[str, int]]] = {}
    batch_size = 50
    clean_ids = [w.split("/")[-1] for w in work_ids]

    logger.info(f"Querying OpenAlex in batches of {batch_size}...")
    for i in range(0, len(clean_ids), batch_size):
        chunk = clean_ids[i : i + batch_size]
        joined = "|".join(chunk)
        url = "https://api.openalex.org/works"
        params = {
            "filter": f"openalex_id:{joined}",
            "select": "id,publication_year,counts_by_year",
            "per_page": len(chunk),
        }
        try:
            resp = http_client.get_json(url, params=params, use_cache=True)
            for item in resp.get("results", []):
                w_id = item.get("id")
                cby = item.get("counts_by_year", [])
                if w_id:
                    results[w_id] = cby
        except Exception as exc:
            logger.warning(f"Batch fetch error on chunk {i}-{i+len(chunk)}: {exc}")

    logger.info(f"Retrieved counts_by_year for {len(results)} works. Caching to {CACHE_FILE}...")
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f)

    return results


if __name__ == "__main__":
    fetch_counts_by_year()
