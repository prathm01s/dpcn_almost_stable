"""Disk-based cache for HTTP GET requests.

Caches every response by sha256(url_without_api_key).
Guarantees idempotency and zero API budget expenditure on repeat runs.
"""

import gzip
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Optional, Union

CACHE_DIR = Path("data/cache")


import urllib.parse

def clean_url(url: str) -> str:
    """Strip api_key query parameters from URL and canonicalize for caching."""
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered_qs = [(k, v) for k, v in qs if k != "api_key"]
    # Sorting ensures parameter order does not miss cache hits
    filtered_qs.sort()
    new_query = urllib.parse.urlencode(filtered_qs, safe=":,")
    return urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


def get_cache_key(url: str) -> str:
    """Compute sha256 of cleaned URL."""
    cleaned = clean_url(url)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def get_cache_path(url: str) -> Path:
    """Return path in data/cache/<prefix>/<hash>.gz"""
    key = get_cache_key(url)
    sub = key[:2]
    return CACHE_DIR / sub / f"{key}.json.gz"


def read_cache(url: str) -> Optional[dict]:
    """Retrieve cached JSON response if exists, else None."""
    path = get_cache_path(url)
    if not path.is_file():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_cache(url: str, data: Union[dict, list]) -> None:
    """Write JSON data to cache."""
    path = get_cache_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with gzip.open(temp_path, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    temp_path.replace(path)
