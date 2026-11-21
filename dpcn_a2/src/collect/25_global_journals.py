"""Step 25: journals of every benchmark institution's papers, for Q1 / Q1 & IF > 5 / Q1 & IF > 10 (D-47).

For each institution of the Global Benchmark (data/final/global/peers.csv: the three labs, the foreign twins and the
Indian reference group) and each year 2016-2025, the same papers as Step 23 (sub-units included, articles and reviews,
benchmark subfields) are grouped by journal (group_by=primary_location.source.id, cursor-paged so no journal is cut off).
The journals are then resolved to their ISSNs (/sources, 100 per call). The quartile and impact-factor analogue are
attached in src/stats/global_benchmark.py from the SCImago panel, exactly as for the labs' own papers
(src/stats/journal_if.py): the journal's SJR best quartile and 'Cites / Doc. (2 years)' in the paper's year.

API cost: about 450 group_by pages + 40 source batches (about $0.05); cached in data/cache.

Outputs (data/final/global/)
- journal_by_year.csv  institution_id, year, source_id ('' = no journal), papers
- sources.csv          source_id, display_name, issn_l, issn (';'-joined)
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src.common.http import budget_tracker, http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE

logger = get_logger("25_global_journals")
G = Path("data/final/global")
WORKERS = 6  # AGENTS.md: global concurrency <= 8


def _peers_module():
    import importlib
    return importlib.import_module("src.collect.22_global_peers")


def _short(x):
    return str(x).rstrip("/").rsplit("/", 1)[-1] if x else ""


def journals_one(flt: str) -> list:
    """[(source_id, papers)] for one filter, all groups (cursor paging)."""
    out, cursor = [], "*"
    while cursor:
        d = http_client.get_json(f"{OPENALEX_BASE}/works", params={"filter": flt, "group_by": "primary_location.source.id",
                                                                   "per_page": 200, "cursor": cursor})
        for g in d.get("group_by", []):
            key = _short(g.get("key"))
            out.append(("" if key in ("", "unknown", "null") else key, int(g["count"])))
        cursor = d.get("meta", {}).get("next_cursor")
    return out


def run_step_25() -> None:
    m = _peers_module()
    cfg = m.load_cfg()
    peers = pd.read_csv(G / "peers.csv", dtype=str)
    sc = pd.read_csv(G / "scope_subfields.csv", dtype={"subfield_id": str})
    scope = "primary_topic.subfield.id:" + "|".join(sc.loc[sc["in_scope"], "subfield_id"])
    types = "|".join(cfg["work_types"])
    jobs = [(iid, y) for iid in peers["institution_id"] for y in range(cfg["years"]["start"], cfg["years"]["end"] + 1)]

    def job(j):
        iid, y = j
        flt = f"authorships.institutions.lineage:{iid},publication_year:{y},type:{types},{scope}"
        return [{"institution_id": iid, "year": y, "source_id": s, "papers": n} for s, n in journals_one(flt)]

    rows = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(job, jobs):
            rows += r
    jb = pd.DataFrame(rows).groupby(["institution_id", "year", "source_id"], as_index=False)["papers"].sum()
    jb.sort_values(["institution_id", "year", "source_id"]).to_csv(G / "journal_by_year.csv", index=False)
    logger.info(f"journal_by_year: {len(jb):,} rows, {jb['papers'].sum():,} papers")

    ids = sorted(s for s in jb["source_id"].unique() if s)
    srows = []

    def batch(chunk):
        d = http_client.get_json(f"{OPENALEX_BASE}/sources", params={"filter": "openalex_id:" + "|".join(chunk), "per_page": 100,
                                                                     "select": "id,display_name,issn_l,issn"})
        return [{"source_id": _short(s["id"]), "display_name": s.get("display_name") or "", "issn_l": s.get("issn_l") or "",
                 "issn": ";".join(s.get("issn") or [])} for s in d.get("results", [])]

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(batch, [ids[i:i + 100] for i in range(0, len(ids), 100)]):
            srows += r
    pd.DataFrame(srows).sort_values("source_id").to_csv(G / "sources.csv", index=False)
    logger.info(f"sources: {len(srows):,} of {len(ids):,} resolved ({budget_tracker.network_calls} network calls, "
                f"{budget_tracker.cache_hits} cache hits)")


if __name__ == "__main__":
    run_step_25()
