"""Fetch full career publication timelines from OpenAlex for matched roster faculty.

For each matched scientist, pulls every work (any year) with
filter=authorships.author.id:<A..>, select=id,publication_year,authorships, cursor paging,
through the project's OpenAlex client (API key, data/cache/ response cache, retries,
budget tracking). Only that author's own authorship entry is kept:
(work_id, year, institution_id, institution_name, country_code).

Timelines are written to data/cache/openalex/careers/<author_id>.json (derived data, gitignored).
A fetch error stops the run instead of caching a partial timeline.
Used by Insights 9 (brain circulation) and 10 (succession risk).
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from src.common.http import budget_tracker
from src.common.logging import get_logger
from src.common.openalex import fetch_cursor_pages
from src.stats.insights.common import faculty

logger = get_logger("fetch_author_careers")

CACHE_DIR = Path("data/cache/openalex/careers")


def fetch_author_timeline(author_id: str) -> List[Dict[str, Any]]:
    """All authorship events of one OpenAlex author (short id, e.g. A5012345678)."""
    timeline: List[Dict[str, Any]] = []
    for page in fetch_cursor_pages("works", {
        "filter": f"authorships.author.id:{author_id}",
        "select": "id,publication_year,authorships",
        "per_page": 100,
    }):
        for w in page.get("results", []):
            for a in w.get("authorships") or []:
                if ((a.get("author") or {}).get("id") or "").rsplit("/", 1)[-1] != author_id:
                    continue
                insts = a.get("institutions") or [{}]
                for inst in insts:
                    timeline.append({
                        "work_id": w.get("id"),
                        "year": w.get("publication_year"),
                        "institution_id": inst.get("id", "") or "",
                        "institution_name": inst.get("display_name", "") or "",
                        "country_code": inst.get("country_code", "") or "",
                    })
    return timeline


def fetch_all_careers(force_refresh: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch (or load) career timelines for all matched roster faculty."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df_fac = faculty()
    matched = df_fac[df_fac["is_matched"] & (df_fac["openalex_author_id"] != "")]
    logger.info(f"Matched faculty: {len(matched)}; confidence: {matched['match_confidence'].value_counts().to_dict()}")

    careers: Dict[str, List[Dict[str, Any]]] = {}
    for full_id in sorted(set(matched["openalex_author_id"])):
        aid = full_id.rsplit("/", 1)[-1]
        path = CACHE_DIR / f"{aid}.json"
        if path.exists() and not force_refresh:
            careers[aid] = json.loads(path.read_text(encoding="utf-8"))
            continue
        careers[aid] = fetch_author_timeline(aid)
        path.write_text(json.dumps(careers[aid]), encoding="utf-8")
    logger.info(f"Career timelines: {len(careers)} authors | network calls {budget_tracker.network_calls}, "
                f"est. spend ${budget_tracker.estimated_spend_usd:.3f}")
    return careers


def main() -> None:
    fetch_all_careers()


if __name__ == "__main__":
    main()
