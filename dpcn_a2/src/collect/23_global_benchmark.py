"""Step 23: benchmark data for the peers chosen in Step 22 (D-35).

Every institution (our three labs, the foreign twins and the Indian reference group) is measured
with the same OpenAlex queries: papers of the institution and its sub-units
(authorships.institutions.lineage), 2016-2025, articles and reviews, in the benchmark scope
(the subfields in data/final/global/scope_subfields.csv). Our labs' numbers here therefore come
from the raw OpenAlex query, not from the curated dataset used elsewhere on the site.

Field-normalised impact uses OpenAlex's own world baselines:
- top 10% / top 1%: citation_normalized_percentile.is_in_top_10_percent / _1_percent (the paper is
  among the most cited 10% / 1% of works of the same subfield, type and year worldwide)
- above world average: fwci > 1 (field-weighted citation impact; 1 = world average)
International co-authorship: countries_distinct_count > 1.

Links between each CSIR lab and each peer:
- co-authored papers (all fields), by year
- citation flows, using the lab's papers in our curated dataset (data/final/group24_data_extended.csv)
  in batches of 100: peer papers citing them (filter cites:) and peer papers they cite
  (filter cited_by:), restricted to the peers with authorships.institutions.lineage. Each peer
  paper is counted once per lab and direction; papers co-authored with the lab itself are marked.

API cost: ~150 group_by calls + ~900 paged list calls (~$0.10), cached in data/cache.

Outputs (data/final/global/)
- bench_by_year.csv    institution_id, year, papers_all, papers_scope, top10, top1, above_world, intl
- country_by_year.csv  country_code (IN, US, CN, KR, AU, WORLD), year, papers_scope, top10, top1
- collab_by_year.csv   lab, institution_id, year, papers
- citation_flows.csv   lab, institution_id, direction (peer_cites_lab | lab_cites_peer), work_id,
                       year (of the peer paper), coauthored_with_lab
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger
from src.common.openalex import fetch_cursor_pages

logger = get_logger("23_global_benchmark")
G = Path("data/final/global")


def _peers_module():
    import importlib
    return importlib.import_module("src.collect.22_global_peers")


WORKERS = 6  # parallel batches (AGENTS.md: global concurrency <= 8)


def _peer_papers(flt: str) -> dict:
    """{work_id: (year, lineage ids of all its institutions)} for every page of one filter."""
    out = {}
    for page in fetch_cursor_pages("works", {"filter": flt, "per_page": 100, "select": "id,publication_year,authorships"}):
        for w in page.get("results", []):
            lin = {x.rstrip("/").rsplit("/", 1)[-1] for a in w.get("authorships") or [] for inst in a.get("institutions") or []
                   for x in (inst.get("lineage") or [inst.get("id")]) if x}
            out[w["id"].rsplit("/", 1)[-1]] = (w.get("publication_year"), lin)
    return out


def by_year(m, flt: str) -> dict:
    return {int(r["key"]): int(r["count"]) for r in m.group_by(flt, "publication_year")}


def run_step_23() -> None:
    m = _peers_module()
    cfg = m.load_cfg()
    base = m.base_filter(cfg)
    peers = pd.read_csv(G / "peers.csv", dtype=str)
    sc = pd.read_csv(G / "scope_subfields.csv", dtype={"subfield_id": str})
    scope = "primary_topic.subfield.id:" + "|".join(sc.loc[sc["in_scope"], "subfield_id"])
    years = range(cfg["years"]["start"], cfg["years"]["end"] + 1)

    metrics = {
        "papers_all": "",
        "papers_scope": f",{scope}",
        "top10": f",{scope},citation_normalized_percentile.is_in_top_10_percent:true",
        "top1": f",{scope},citation_normalized_percentile.is_in_top_1_percent:true",
        "above_world": f",{scope},fwci:>1",
        "intl": f",{scope},countries_distinct_count:>1",
    }
    rows = []
    for iid in peers["institution_id"]:
        got = {k: by_year(m, f"authorships.institutions.lineage:{iid},{base}{v}") for k, v in metrics.items()}
        for y in years:
            rows.append({"institution_id": iid, "year": y, **{k: got[k].get(y, 0) for k in metrics}})
    pd.DataFrame(rows).to_csv(G / "bench_by_year.csv", index=False)
    logger.info(f"bench_by_year: {len(peers)} institutions")

    rows = []
    for cc in ["IN", *cfg["countries"].keys(), "WORLD"]:
        cf = "" if cc == "WORLD" else f"authorships.countries:{cc},"
        got = {k: by_year(m, f"{cf}{base}{metrics[k]}") for k in ["papers_scope", "top10", "top1"]}
        for y in years:
            rows.append({"country_code": cc, "year": y, **{k: got[k].get(y, 0) for k in got}})
    pd.DataFrame(rows).to_csv(G / "country_by_year.csv", index=False)

    labs = peers[peers["group"] == "CSIR lab"]
    others = peers[peers["group"] != "CSIR lab"]
    rows = []
    for _, lab in labs.iterrows():
        for iid in others["institution_id"]:
            got = by_year(m, f"authorships.institutions.lineage:{lab['institution_id']},authorships.institutions.lineage:{iid},{base}")
            rows += [{"lab": lab["name"], "institution_id": iid, "year": y, "papers": got.get(y, 0)} for y in years]
    pd.DataFrame(rows).to_csv(G / "collab_by_year.csv", index=False)
    logger.info("collab_by_year done")

    # Citation flows between each lab's curated papers and the peers
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False,
                      usecols=["work_id", "institution"])
    peer_ids = others["institution_id"].tolist()
    peer_set = set(peer_ids)
    rows = []
    for _, lab in labs.iterrows():
        lab_id = lab["institution_id"]
        works = sorted({m.short(w) for w in ext.loc[ext["institution"] == lab["name"], "work_id"]})
        for direction, key in [("peer_cites_lab", "cites"), ("lab_cites_peer", "cited_by")]:
            filters = [f"{key}:{'|'.join(works[i:i + 100])},authorships.institutions.lineage:{'|'.join(peer_ids)}"
                       for i in range(0, len(works), 100)]
            seen = {}
            # batches run in parallel (each pages through its own cursor); results are merged in batch order
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                for found in pool.map(_peer_papers, filters):
                    seen.update(found)
            for wid, (yr, lin) in seen.items():
                for iid in lin & peer_set:
                    rows.append({"lab": lab["name"], "institution_id": iid, "direction": direction, "work_id": wid,
                                 "year": yr, "coauthored_with_lab": lab_id in lin})
            logger.info(f"{lab['name']} {direction}: {len(seen)} peer papers")
    pd.DataFrame(rows).to_csv(G / "citation_flows.csv", index=False)


if __name__ == "__main__":
    run_step_23()
