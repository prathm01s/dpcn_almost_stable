"""Step 17: Add citation and co-authorship links with other Indian institutions.

Earlier steps only kept links inside the NCL/IICT/CECRI corpus, so the Indian
citation flags were lower bounds. This step queries OpenAlex, 100 corpus papers
at a time:

1. our papers:            filter=openalex_id:W1|...      -> referenced_works, authorships
2. Indian papers we cite: filter=cited_by:W1|...,authorships.countries:IN
3. Indian papers citing us: filter=cites:W1|...,authorships.countries:IN

and appends to data/final/:
- citation_network.csv   edges between a corpus paper and an Indian-affiliated paper
                         outside the corpus. The outside paper's side lists its Indian
                         institutions joined by ";" (our labs as CSIR-NCL / CSIR-IICT /
                         CSIR-CECRI). Only edges where both papers have a DOI are kept.
- authorship_network.csv edges between our authors and co-authors whose authorship
                         is at another Indian institution (inst_b lists those institutions).
- indian_linked_works.csv metadata of the outside papers (title, year, citations, institutions).

Step 15 then recomputes cites_indian_inst / cited_by_indian_inst from citation_network.csv.
Re-running is free (responses are cached in data/cache/) and idempotent: rows added by an
earlier run are removed before the new ones are written.
"""

import collections
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

from src.common.http import budget_tracker
from src.common.logging import get_logger
from src.common.openalex import fetch_cursor_pages, OPENALEX_BASE
from src.common.http import http_client

logger = get_logger("17_indian_links_api")

FINAL_DIR = Path("data/final")
LAB_IDS = {
    "I3125981224": "CSIR-NCL",
    "I55664587": "CSIR-IICT",
    "I106349282": "CSIR-CECRI",
}
LABS = set(LAB_IDS.values())
BATCH = 100
WORKERS = 6


def short_id(url: str) -> str:
    return url.rsplit("/", 1)[-1] if url else ""


def norm_doi(doi: str) -> str:
    if not doi:
        return ""
    d = doi.strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/"):
        if d.startswith(p):
            d = d[len(p):]
    return f"https://doi.org/{d}" if d.startswith("10.") else ""


class InstNamer:
    """OpenAlex institution -> name used in our CSVs (registry canonical name, our labs short)."""

    def __init__(self) -> None:
        reg = pd.read_csv("config/indian_inst_registry.csv", dtype=str, keep_default_na=False)
        self.names = {short_id(i): n for i, n in zip(reg["openalex_id"], reg["canonical_name"])}
        self.names.update(LAB_IDS)

    def __call__(self, inst: dict) -> str:
        iid = short_id(inst.get("id") or "")
        name = self.names.get(iid) or (inst.get("display_name") or "")
        return name.replace(";", ",").strip()


def indian_insts(work: dict, namer: InstNamer) -> Set[str]:
    return {
        namer(i)
        for a in work.get("authorships") or []
        for i in a.get("institutions") or []
        if i.get("country_code") == "IN" and namer(i)
    }


def fetch_batch(ids: List[str], our_ids: Set[str], namer: InstNamer) -> dict:
    """Run the three queries for one batch and keep only what later steps need."""
    joined = "|".join(ids)
    out = {"ours": {}, "refs": {}, "citing": {}}

    data = http_client.get_json(f"{OPENALEX_BASE}/works", params={
        "filter": f"openalex_id:{joined}", "per_page": BATCH,
        "select": "id,doi,publication_year,referenced_works,authorships",
    })
    for w in data.get("results", []):
        out["ours"][short_id(w["id"])] = {
            "refs": [short_id(r) for r in w.get("referenced_works") or []],
            "authorships": [
                {
                    "author_id": short_id((a.get("author") or {}).get("id") or ""),
                    "name": (a.get("author") or {}).get("display_name") or a.get("raw_author_name") or "",
                    "lab_ids": [short_id(i.get("id") or "") for i in a.get("institutions") or []
                                if short_id(i.get("id") or "") in LAB_IDS],
                    "indian": sorted({namer(i) for i in a.get("institutions") or []
                                      if i.get("country_code") == "IN" and namer(i)}),
                }
                for a in w.get("authorships") or []
            ],
        }

    for page in fetch_cursor_pages("works", {
        "filter": f"cited_by:{joined},authorships.countries:IN", "per_page": 100,
        "select": "id,doi,title,publication_year,cited_by_count,authorships",
    }):
        for w in page.get("results", []):
            out["refs"][short_id(w["id"])] = meta(w, namer)

    for page in fetch_cursor_pages("works", {
        "filter": f"cites:{joined},authorships.countries:IN", "per_page": 100,
        "select": "id,doi,title,publication_year,cited_by_count,referenced_works,authorships",
    }):
        for w in page.get("results", []):
            m = meta(w, namer)
            m["cites"] = sorted({short_id(r) for r in w.get("referenced_works") or []} & our_ids)
            out["citing"][short_id(w["id"])] = m
    return out


def meta(w: dict, namer: InstNamer) -> dict:
    return {
        "doi": norm_doi(w.get("doi") or ""),
        "title": (w.get("title") or "").replace("\n", " ").strip(),
        "year": w.get("publication_year"),
        "cited_by_count": w.get("cited_by_count") or 0,
        "insts": sorted(indian_insts(w, namer)),
    }


def collect(our_ids: List[str]) -> dict:
    namer = InstNamer()
    our_set = set(our_ids)
    batches = [our_ids[i:i + BATCH] for i in range(0, len(our_ids), BATCH)]
    merged = {"ours": {}, "refs": {}, "citing": {}}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for n, res in enumerate(pool.map(lambda b: fetch_batch(b, our_set, namer), batches), 1):
            merged["ours"].update(res["ours"])
            merged["refs"].update(res["refs"])
            for wid, m in res["citing"].items():
                if wid in merged["citing"]:
                    merged["citing"][wid]["cites"] = sorted(set(merged["citing"][wid]["cites"]) | set(m["cites"]))
                else:
                    merged["citing"][wid] = m
            if n % 10 == 0 or n == len(batches):
                logger.info(f"Batches {n}/{len(batches)} | network calls {budget_tracker.network_calls} "
                            f"| est. spend ${budget_tracker.estimated_spend_usd:.3f}")
    missing = our_set - set(merged["ours"])
    if missing:
        # Works merged or removed in OpenAlex since the 13 Oct pull: their outgoing links are unknown.
        logger.warning(f"{len(missing)} corpus works not returned by OpenAlex, e.g. {sorted(missing)[:3]}")
    return merged


def citation_edges(data: dict, works: pd.DataFrame, corpus_dois: Set[str]) -> Tuple[pd.DataFrame, dict]:
    """Edges between corpus papers and outside Indian-affiliated papers (both with DOI)."""
    labs_of = works.groupby("wid")["institution"].agg(lambda s: sorted(set(s))).to_dict()
    doi_of = works.drop_duplicates("wid").set_index("wid")["doi"].to_dict()
    year_of = works.drop_duplicates("wid").set_index("wid")["year"].to_dict()
    our_ids = set(labs_of)

    def outside(wid: str, m: dict) -> bool:
        return wid not in our_ids and m["doi"] and m["doi"] not in corpus_dois and m["insts"]

    rows, used = [], {}
    for wid, info in data["ours"].items():
        src = doi_of.get(wid, "")
        if not src:
            continue
        for r in info["refs"]:
            m = data["refs"].get(r)
            if m and outside(r, m):
                used[r] = m
                for lab in labs_of[wid]:
                    rows.append((src, m["doi"], lab, ";".join(m["insts"]), int(year_of[wid])))
    for cid, m in data["citing"].items():
        if not outside(cid, m):
            continue
        for wid in m["cites"]:
            tgt = doi_of.get(wid, "")
            if tgt:
                used[cid] = m
                for lab in labs_of[wid]:
                    rows.append((m["doi"], tgt, ";".join(m["insts"]), lab, int(m["year"] or 0)))
    df = pd.DataFrame(rows, columns=["source_doi", "target_doi", "source_inst", "target_inst", "year"])
    df = df[df["source_doi"] != df["target_doi"]].drop_duplicates()
    return df.sort_values(list(df.columns)).reset_index(drop=True), used


def authorship_edges(data: dict, ext: pd.DataFrame) -> pd.DataFrame:
    """Our authors x co-authors whose authorship is at another Indian institution (not our labs)."""
    rows = []
    paper = ext.drop_duplicates("wid").set_index("wid")[["doi", "year"]]
    ours_by_work = ext.drop_duplicates(["wid", "institution", "author"]).groupby("wid")
    for wid, g in ours_by_work:
        info = data["ours"].get(wid)
        if not info:
            continue
        own_ids = set(g["author_openalex_id"].map(short_id)) - {""}
        own_names = set(g["author"])
        external = [a for a in info["authorships"]
                    if not a["lab_ids"] and a["indian"] and a["name"]
                    and a["author_id"] not in own_ids and a["name"] not in own_names]
        if not external:
            continue
        doi, year = paper.at[wid, "doi"], int(paper.at[wid, "year"])
        for r in g.itertuples(index=False):
            for a in external:
                rows.append((r.author, a["name"], doi, r.institution, ";".join(a["indian"]), year))
    df = pd.DataFrame(rows, columns=["author_a", "author_b", "paper_doi", "inst_a", "inst_b", "year"])
    df = df[df["author_a"] != df["author_b"]].drop_duplicates()
    return df.sort_values(list(df.columns)).reset_index(drop=True)


def run_step_17() -> None:
    logger.info("Starting Step 17: links with other Indian institutions (OpenAlex)...")
    ext = pd.read_csv(FINAL_DIR / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    ext["wid"] = ext["work_id"].map(short_id)
    corpus_dois = set(ext["doi"]) - {""}
    our_ids = sorted(set(ext["wid"]))

    data = collect(our_ids)
    logger.info(f"Fetched {len(data['ours'])} corpus works, {len(data['refs'])} Indian references, "
                f"{len(data['citing'])} Indian citing works")

    # Citation network: keep in-corpus rows (both DOIs in corpus), replace outside rows
    cite = pd.read_csv(FINAL_DIR / "citation_network.csv", dtype=str, keep_default_na=False)
    cite_in = cite[cite["source_doi"].isin(corpus_dois) & cite["target_doi"].isin(corpus_dois)]
    new_cite, used = citation_edges(data, ext, corpus_dois)
    new_cite["year"] = new_cite["year"].astype(str)
    out_cite = pd.concat([cite_in, new_cite], ignore_index=True)
    out_cite.to_csv(FINAL_DIR / "citation_network.csv", index=False, encoding="utf-8", lineterminator="\n")
    logger.info(f"citation_network.csv: {len(cite_in)} in-corpus + {len(new_cite)} Indian outside = {len(out_cite)} edges")

    # Authorship network: keep rows between our labs, replace outside rows
    auth = pd.read_csv(FINAL_DIR / "authorship_network.csv", dtype=str, keep_default_na=False)
    auth_in = auth[auth["inst_a"].isin(LABS) & auth["inst_b"].isin(LABS)]
    new_auth = authorship_edges(data, ext)
    new_auth["year"] = new_auth["year"].astype(str)
    out_auth = pd.concat([auth_in, new_auth], ignore_index=True)
    out_auth.to_csv(FINAL_DIR / "authorship_network.csv", index=False, encoding="utf-8", lineterminator="\n")
    logger.info(f"authorship_network.csv: {len(auth_in)} within labs + {len(new_auth)} with Indian partners = {len(out_auth)} edges")

    linked = pd.DataFrame([
        {"work_id": f"https://openalex.org/{w}", "doi": m["doi"], "title": m["title"], "year": m["year"],
         "cited_by_count": m["cited_by_count"], "indian_institutions": ";".join(m["insts"])}
        for w, m in sorted(used.items())
    ])
    linked.to_csv(FINAL_DIR / "indian_linked_works.csv", index=False, encoding="utf-8", lineterminator="\n")

    for path in (Path("data/MANIFEST.json"), FINAL_DIR / "MANIFEST.json"):
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        m["files"]["citation_network.csv"]["rows"] = len(out_cite)
        m["files"]["authorship_network.csv"]["rows"] = len(out_auth)
        m["files"]["indian_linked_works.csv"] = {"path": "data/final/indian_linked_works.csv", "rows": len(linked)}
        m["indian_links_collected_at"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        m["indian_links_query"] = ("OpenAlex /works filter cited_by:<100 ids>,authorships.countries:IN and "
                                   "cites:<100 ids>,authorships.countries:IN (core corpus)")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(m, f, indent=2)
    logger.info(f"Step 17 complete. Network calls: {budget_tracker.network_calls}, "
                f"est. spend ${budget_tracker.estimated_spend_usd:.3f}. Run Step 15 next.")


if __name__ == "__main__":
    run_step_17()
