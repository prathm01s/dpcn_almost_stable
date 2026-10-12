"""HTTP client with caching, exponential backoff, rate limiting, and budget tracking."""

import os
import sys
import time
import random
from pathlib import Path
from typing import Any, Dict, Optional, Union
import httpx
from dotenv import load_dotenv

from src.common.cache import clean_url, read_cache, write_cache
from src.common.logging import get_logger

load_dotenv()

logger = get_logger("http")

API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "student@dpcn2026.org").strip()
DEFAULT_USER_AGENT = f"DPCN-ResearchMapping/2026 (mailto:{CONTACT_EMAIL})"


class BudgetTracker:
    def __init__(self, max_spend_usd: float = 0.80):
        self.max_spend_usd = max_spend_usd
        self.total_calls = 0
        self.cache_hits = 0
        self.network_calls = 0
        self.estimated_spend_usd = 0.0
        self.remaining_usd: Optional[float] = None

    def record_cache_hit(self) -> None:
        self.total_calls += 1
        self.cache_hits += 1

    def record_network_call(self, cost_usd: float = 0.0001) -> None:
        self.total_calls += 1
        self.network_calls += 1
        self.estimated_spend_usd += cost_usd

    def update_from_headers(self, headers: httpx.Headers) -> None:
        rem = headers.get("x-ratelimit-remaining-usd")
        if rem is not None:
            try:
                self.remaining_usd = float(rem)
            except ValueError:
                pass


budget_tracker = BudgetTracker()


class HttpClient:
    def __init__(self, timeout: float = 30.0, max_rps: float = 15.0):
        self.timeout = timeout
        self.min_interval = 1.0 / max_rps if max_rps > 0 else 0.05
        self.last_request_time = 0.0
        self.client = httpx.Client(
            timeout=self.timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            follow_redirects=True,
        )

    def _rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        max_retries: int = 6,
    ) -> Dict[str, Any]:
        """Perform GET request with caching, backoff, and budget check."""
        params_dict = dict(params or {})

        # Automatically inject api_key if querying OpenAlex and key is configured
        if "openalex.org" in url and API_KEY and "api_key" not in params_dict:
            params_dict["api_key"] = API_KEY

        # Build full URL string for caching
        req = self.client.build_request("GET", url, params=params_dict)
        full_url = str(req.url)

        if use_cache:
            cached_data = read_cache(full_url)
            if cached_data is not None:
                budget_tracker.record_cache_hit()
                logger.debug(f"Cache hit: {clean_url(full_url)}")
                return cached_data

        # Check budget limits before network call
        if budget_tracker.estimated_spend_usd >= budget_tracker.max_spend_usd:
            logger.warning(
                f"Budget cap reached: spent est ${budget_tracker.estimated_spend_usd:.4f} >= limit ${budget_tracker.max_spend_usd:.2f}. Halting."
            )
            sys.exit(75)

        retries = 0
        backoff = 1.0
        while True:
            self._rate_limit()
            try:
                resp = self.client.send(req)
                budget_tracker.update_from_headers(resp.headers)

                if resp.status_code == 200:
                    data = resp.json()
                    # OpenAlex records cost in payload or header
                    cost = 0.0001
                    if isinstance(data, dict) and "cost_usd" in data:
                        cost = float(data.get("cost_usd", 0.0001))
                    elif "x-ratelimit-cost-usd" in resp.headers:
                        try:
                            cost = float(resp.headers["x-ratelimit-cost-usd"])
                        except ValueError:
                            pass

                    budget_tracker.record_network_call(cost)
                    if use_cache:
                        write_cache(full_url, data)
                    return data

                elif resp.status_code == 429:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Rate limit / 429 exceeded max retries: {clean_url(full_url)}")
                        resp.raise_for_status()

                    # Check if budget exhausted
                    if budget_tracker.remaining_usd is not None and budget_tracker.remaining_usd <= 0.0001:
                        logger.error("OpenAlex daily budget exhausted! Resume after 00:00 UTC.")
                        sys.exit(75)

                    sleep_sec = backoff + random.uniform(0.1, 0.5)
                    logger.warning(f"429 received. Backing off for {sleep_sec:.2f}s (retry {retries}/{max_retries})")
                    time.sleep(sleep_sec)
                    backoff *= 2.0

                elif resp.status_code in [500, 502, 503, 504]:
                    retries += 1
                    if retries > max_retries:
                        resp.raise_for_status()
                    sleep_sec = backoff + random.uniform(0.1, 0.5)
                    logger.warning(f"HTTP {resp.status_code}. Retrying in {sleep_sec:.2f}s (retry {retries}/{max_retries})")
                    time.sleep(sleep_sec)
                    backoff *= 2.0

                else:
                    resp.raise_for_status()

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Request failed after {max_retries} retries: {exc}")
                    raise
                sleep_sec = backoff + random.uniform(0.1, 0.5)
                logger.warning(f"Connection error ({exc}). Retrying in {sleep_sec:.2f}s...")
                time.sleep(sleep_sec)
                backoff *= 2.0


http_client = HttpClient()
