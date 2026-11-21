"""Step 24: the full reference list of every corpus paper (D-44).

Needed by the real-citation test of the idea-spreading study (src/stats/insights/s11_real_diffusion.py):
each paper a lab paper cites is an "idea", and a person adopts it in the year of their first lab paper citing it.

Re-issues Step 18's query per batch of 100 papers (filter=openalex_id:<ids>, same select), so the responses
come from data/cache/ at no API cost once cached. referenced_works is part of the work record and does not
drift like citation counts; the pull date is logged in docs/DECISIONS.md (D-44).

Output: data/final/work_references.csv.gz
  work_id             OpenAlex ID of the corpus paper (W...)
  referenced_work_id  OpenAlex ID of a work it cites (W...)
One row per (paper, reference); papers without references have no row.
"""

from pathlib import Path

import pandas as pd

from src.common.http import budget_tracker, http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE

logger = get_logger("24_work_references")

FINAL_DIR = Path("data/final")
OUT = FINAL_DIR / "work_references.csv.gz"
BATCH = 100
SELECT = "id,doi,publication_year,referenced_works,authorships"  # identical to Step 18, so its cached responses are reused


def run_step_24() -> Path:
    ext = pd.read_csv(FINAL_DIR / "group24_data_extended.csv", dtype=str, keep_default_na=False, usecols=["work_id"])
    ids = sorted({w.rsplit("/", 1)[-1] for w in ext["work_id"]})
    rows, seen = [], set()
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        data = http_client.get_json(f"{OPENALEX_BASE}/works", params={
            "filter": f"openalex_id:{'|'.join(chunk)}", "per_page": BATCH, "select": SELECT,
        })
        for w in data.get("results", []):
            wid = w["id"].rsplit("/", 1)[-1]
            seen.add(wid)
            for r in dict.fromkeys(w.get("referenced_works") or []):
                rows.append((wid, r.rsplit("/", 1)[-1]))
    out = pd.DataFrame(rows, columns=["work_id", "referenced_work_id"]).sort_values(["work_id", "referenced_work_id"])
    out.to_csv(OUT, index=False, encoding="utf-8", lineterminator="\n", compression={"method": "gzip", "mtime": 0})
    logger.info(f"Saved {len(out):,} references of {out['work_id'].nunique():,} papers ({len(seen):,} of {len(ids):,} returned) "
                f"to {OUT} ({budget_tracker.cache_hits} cache hits, {budget_tracker.network_calls} network calls)")
    return OUT


if __name__ == "__main__":
    run_step_24()
