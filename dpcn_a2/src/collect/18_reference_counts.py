"""Step 18: Number of references (citations made) per corpus paper.

Needed for the citation impact ratio (src/stats/impact_ratio.py):
    impact ratio = citations received / citations made
                 = cited_by_count / number of works in referenced_works

Re-issues Step 17's first query per batch (filter=openalex_id:<100 ids>) with the
identical parameters, so responses come from data/cache/ at no API cost.

Output: data/final/work_reference_counts.csv  (work_id, references_count)
references_count is blank for works OpenAlex no longer returns.
"""

from pathlib import Path

import pandas as pd

from src.common.http import budget_tracker, http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE

logger = get_logger("18_reference_counts")

FINAL_DIR = Path("data/final")
BATCH = 100
# Must match Step 17's select so the cached responses are reused
SELECT = "id,doi,publication_year,referenced_works,authorships"


def run_step_18() -> None:
    ext = pd.read_csv(FINAL_DIR / "group24_data_extended.csv", dtype=str, keep_default_na=False, usecols=["work_id"])
    ids = sorted({w.rsplit("/", 1)[-1] for w in ext["work_id"]})
    counts = {}
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        data = http_client.get_json(f"{OPENALEX_BASE}/works", params={
            "filter": f"openalex_id:{'|'.join(chunk)}", "per_page": BATCH, "select": SELECT,
        })
        for w in data.get("results", []):
            counts[w["id"].rsplit("/", 1)[-1]] = len(w.get("referenced_works") or [])
    out = pd.DataFrame({
        "work_id": [f"https://openalex.org/{w}" for w in ids],
        "references_count": pd.array([counts.get(w) for w in ids], dtype="Int64"),
    })
    out.to_csv(FINAL_DIR / "work_reference_counts.csv", index=False, encoding="utf-8", lineterminator="\n")
    logger.info(f"Saved reference counts for {out['references_count'].notna().sum()}/{len(out)} works "
                f"({budget_tracker.cache_hits} cache hits, {budget_tracker.network_calls} network calls)")


if __name__ == "__main__":
    run_step_18()
