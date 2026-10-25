"""Fetch full career publication timelines from OpenAlex for roster faculty.

Queries all career works for matched roster faculty (any publication year)
to extract (year, institution_id, institution_name, country_code) for each author.
Caches individual author career timelines in data/cache/openalex/careers/<clean_id>.json.
"""

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import httpx
import pandas as pd
from tqdm import tqdm

from src.common.http import http_client, DEFAULT_USER_AGENT
from src.common.logging import get_logger
from src.stats.insights.common import faculty

logger = get_logger("fetch_author_careers")

CACHE_DIR = Path("data/cache/openalex/careers")


def fetch_author_timeline(clean_author_id: str, max_pages: int = 10) -> List[Dict[str, Any]]:
    """Fetch all career authorship events for a given OpenAlex author ID."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{clean_author_id}.json"

    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    timeline: List[Dict[str, Any]] = []
    base_url = "https://api.openalex.org/works"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    # Use basic page pagination sorted by publication year ascending
    for page in range(1, max_pages + 1):
        params = {
            "filter": f"author.id:{clean_author_id}",
            "select": "id,publication_year,authorships",
            "sort": "publication_year:asc",
            "per_page": 100,
            "page": page,
        }
        try:
            resp = http_client.client.get(base_url, params=params, headers=headers)
            if resp.status_code == 429:
                time.sleep(2.0)
                resp = http_client.client.get(base_url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"HTTP {resp.status_code} on author {clean_author_id} page {page}")
                break

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for w in results:
                pub_yr = w.get("publication_year")
                w_id = w.get("id")
                # Find author's own entry
                for a in w.get("authorships", []):
                    author_obj = a.get("author") or {}
                    raw_aid = author_obj.get("id") or ""
                    aid = raw_aid.split("/")[-1] if raw_aid else ""
                    if aid == clean_author_id:
                        insts = a.get("institutions", [])
                        if not insts:
                            timeline.append({
                                "work_id": w_id,
                                "year": pub_yr,
                                "institution_id": "",
                                "institution_name": "",
                                "country_code": "",
                            })
                        else:
                            for inst in insts:
                                timeline.append({
                                    "work_id": w_id,
                                    "year": pub_yr,
                                    "institution_id": inst.get("id", ""),
                                    "institution_name": inst.get("display_name", ""),
                                    "country_code": inst.get("country_code", ""),
                                })
            # If fewer than 100 results returned, we have reached the end
            if len(results) < 100:
                break

            time.sleep(0.08)  # Polite sleep

        except Exception as exc:
            logger.warning(f"Error fetching author {clean_author_id} page {page}: {exc}")
            break

    # Cache timeline
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2)

    return timeline


def fetch_all_careers(force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch career timelines for all matched roster faculty."""
    df_fac = faculty()
    matched = df_fac[df_fac["is_matched"] & df_fac["openalex_author_id"].notna() & (df_fac["openalex_author_id"] != "")].copy()
    logger.info(f"Matched faculty to fetch careers for: {len(matched)}")
    logger.info(f"Confidence counts: {matched['match_confidence'].value_counts().to_dict()}")

    all_careers = {}
    for _, r in tqdm(matched.iterrows(), total=len(matched), desc="Fetching author careers"):
        full_aid = r["openalex_author_id"]
        clean_id = full_aid.split("/")[-1]
        cache_path = CACHE_DIR / f"{clean_id}.json"

        if not force_refresh and cache_path.exists():
            with open(cache_path, "r", encoding="utf-8") as f:
                all_careers[clean_id] = json.load(f)
            continue

        timeline = fetch_author_timeline(clean_id)
        all_careers[clean_id] = timeline

    logger.info(f"Successfully processed {len(all_careers)} author career timelines")
    return all_careers


if __name__ == "__main__":
    fetch_all_careers()
