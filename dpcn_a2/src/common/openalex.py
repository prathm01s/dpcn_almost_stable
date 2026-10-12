"""OpenAlex API client helper wrapping cursor paging and batch requests."""

import os
from typing import Any, Dict, Generator, List, Optional
from src.common.http import http_client
from src.common.logging import get_logger

logger = get_logger("openalex")

OPENALEX_BASE = "https://api.openalex.org"


def fetch_cursor_pages(
    endpoint: str,
    params: Dict[str, Any],
    max_pages: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Generator yielding OpenAlex page responses using cursor-based pagination."""
    params_copy = dict(params)
    params_copy["cursor"] = "*"
    params_copy["per_page"] = min(int(params_copy.get("per_page", 100)), 100)

    url = f"{OPENALEX_BASE}/{endpoint.lstrip('/')}"
    page_count = 0

    while True:
        data = http_client.get_json(url, params=params_copy)
        yield data
        page_count += 1

        if max_pages and page_count >= max_pages:
            break

        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        if not next_cursor:
            break
        params_copy["cursor"] = next_cursor


def fetch_all_results(
    endpoint: str,
    params: Dict[str, Any],
    max_results: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all results across cursor pages."""
    results: List[Dict[str, Any]] = []
    for page in fetch_cursor_pages(endpoint, params):
        page_results = page.get("results", [])
        results.extend(page_results)
        if max_results and len(results) >= max_results:
            results = results[:max_results]
            break
    return results


def batch_fetch_by_ids(
    endpoint: str,
    id_list: List[str],
    id_param: str = "openalex_id",
    select: Optional[str] = None,
    batch_size: int = 100,
) -> List[Dict[str, Any]]:
    """Batch lookup entities by OpenAlex IDs (up to 100 per call)."""
    clean_ids = [i.split("/")[-1] if "/" in i else i for i in id_list]
    results: List[Dict[str, Any]] = []

    for i in range(0, len(clean_ids), batch_size):
        chunk = clean_ids[i : i + batch_size]
        joined_ids = "|".join(chunk)
        params: Dict[str, Any] = {
            "filter": f"{id_param}:{joined_ids}",
            "per_page": len(chunk),
        }
        if select:
            params["select"] = select
        url = f"{OPENALEX_BASE}/{endpoint.lstrip('/')}"
        data = http_client.get_json(url, params=params)
        results.extend(data.get("results", []))

    return results
