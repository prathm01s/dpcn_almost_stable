"""Build dashboard/data/g24_global.js for the Global Benchmark page (dashboard/global.html, D-35).

Reads only stats/tables/global_*.csv, data/final/global/scope_subfields.csv,
config/global_benchmark.yaml and config/overrides/global_peer_exclusions.csv; nothing is
recomputed here, so the page shows exactly the numbers in those files.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from src.common.logging import get_logger

logger = get_logger("build_global")
T = Path("stats/tables")
OUT = Path("dashboard/data/g24_global.js")


def _records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))


def run_build_global() -> None:
    if not (T / "global_summary.csv").exists():
        logger.warning("global tables missing; skipping the Global Benchmark payload")
        return
    with open("config/global_benchmark.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open("config/settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    scope = pd.read_csv("data/final/global/scope_subfields.csv")
    ex = pd.read_csv("config/overrides/global_peer_exclusions.csv", dtype=str)
    cr = pd.read_csv(T / "global_country_relations.csv")
    wac = pd.read_csv("data/final/work_author_counts.csv", dtype=str, keep_default_na=False)
    foreign = wac["countries"].str.split(";").apply(lambda xs: any(x and x != "IN" for x in xs))

    payload = {
        "meta": {
            "built": date.today().isoformat(),
            "collection_date": settings.get("collection_date"),
            "years": cfg["years"], "work_types": cfg["work_types"],
            "scope_coverage": cfg["scope_coverage"], "countries": cfg["countries"],
            "candidates": cfg["candidates"], "peers_per_country": cfg["peers_per_country"],
            "min_similarity": cfg["min_similarity"],
            "corpus_papers": int(len(wac)), "foreign_coauthored_papers": int(foreign.sum()),
        },
        "peers": _records(pd.read_csv(T / "global_peers.csv", dtype={"institution_id": str})),
        "summary": _records(pd.read_csv(T / "global_summary.csv", dtype={"institution_id": str})),
        "by_year": _records(pd.read_csv(T / "global_by_year.csv", dtype={"institution_id": str})),
        "countries": _records(pd.read_csv(T / "global_countries.csv", keep_default_na=False)),
        "links": _records(pd.read_csv(T / "global_links.csv", dtype={"institution_id": str})),
        "country_relations": _records(cr),
        "funnel": _records(pd.read_csv(T / "global_rule_funnel.csv")),
        "similarity": _records(pd.read_csv(T / "global_similarity.csv", dtype={"institution_id": str})),
        "profiles": _records(pd.read_csv(T / "global_profiles.csv", dtype={"institution_id": str})),
        "scope": _records(scope[scope["in_scope"]][["subfield", "share_pct", "cum_share_pct"]]),
        "exclusions": _records(ex[["name", "country", "reason"]]),
        "universities": _records(pd.read_csv(T / "global_indian_universities.csv")),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.G24_GLOBAL = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n",
                   encoding="utf-8")
    logger.info(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    write_teaser(payload)


def write_teaser(payload: dict) -> None:
    """Small file for the Global Benchmark card on the home screen (dashboard/index.html)."""
    s = {r["short"]: r for r in payload["summary"]}
    labs = [r for r in payload["summary"] if r["group"] == "CSIR lab"]
    foreign = [r for r in payload["summary"] if r["group"] not in ("CSIR lab", "India")]
    india = [r for r in payload["summary"] if r["group"] == "India"]
    med = lambda xs: float(pd.Series(xs).median()) if xs else None
    links = [r for r in payload["links"] if r["group"] != "India"]
    inn, out = sum(r["peer_papers_citing_lab"] for r in links), sum(r["peer_papers_cited_by_lab"] for r in links)
    teaser = {
        "countries": len(payload["country_relations"]),
        "foreign_share_pct": round(100 * payload["meta"]["foreign_coauthored_papers"] / payload["meta"]["corpus_papers"], 1),
        "benchmark_countries": list(payload["meta"]["countries"].values()),
        "n_foreign_twins": len(foreign), "n_indian": len(india), "n_universities": len({r["university"] for r in payload["universities"]}),
        "top10": {r["short"]: r["top10_pct"] for r in labs},
        "top10_twin_median": med([r["top10_pct"] for r in foreign]),
        "top10_india_median": med([r["top10_pct"] for r in india]),
        "cagr": {r["short"]: r["cagr_pct"] for r in labs},
        "exchange_ratio_foreign": round(inn / out, 2) if out else None,
    }
    path = OUT.parent / "g24_global_teaser.js"
    path.write_text("window.G24_GLOBAL_TEASER = " + json.dumps(teaser, separators=(",", ":"), ensure_ascii=False) + ";\n", encoding="utf-8")
    logger.info(f"Wrote {path}")


if __name__ == "__main__":
    run_build_global()
