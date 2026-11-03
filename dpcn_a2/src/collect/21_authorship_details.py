"""Step 21: Full author counts per corpus paper and author lists of the Indian papers citing the labs.

Phase II (instructor's directions, D-34) needs, per paper, the total number of authors (to separate
papers with < 10 and >= 10 authors and flag large-collaboration papers) and all collaborating
institutions; and, for the papers citing the labs, who wrote them (to examine why some
non-governmental institutions cite the labs so often).

Both are in the OpenAlex responses that Step 17 already fetched and cached in data/cache/:
- query 1 (filter=openalex_id:<our ids>, select id,doi,publication_year,referenced_works,authorships)
- query 3 (filter=cites:<our ids>,authorships.countries:IN, select id,doi,title,publication_year,
  cited_by_count,referenced_works,authorships)
This step reads those cached files directly (0 API calls). Re-issuing the queries is not an option:
Step 20 changed the corpus, so the 100-id batches would differ and miss the cache. Like Step 18,
it needs data/cache/ (it is not in every checkout).

OpenAlex list responses carry at most 100 authorships per work; papers with exactly 100 are
marked authors_capped = TRUE (100 or more authors).

Outputs
- data/final/work_author_counts.csv: work_id, n_authors, authors_capped, n_institutions,
  n_countries, countries (";"), institution_ids (";", short OpenAlex ids)
- data/final/citing_works.csv: one row per paper outside the corpus that cites >= 1 corpus paper
  (query 3): work_id, doi, year, cited_by_count, n_authors, author_ids (";"), institution_ids (";"),
  n_references, n_references_to_corpus
- data/final/institutions_seen.csv: every institution on a corpus or citing paper: institution_id,
  display_name, country_code, type (OpenAlex), sector (src/common/sectors.py rules for India;
  "Foreign" otherwise), corpus_papers, citing_papers
"""

import glob
import gzip
import json
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger
from src.common.sectors import assign_sector_cluster

logger = get_logger("21_authorship_details")

FINAL = Path("data/final")
CACHE = Path("data/cache")
CAP = 100


def short(url: str) -> str:
    return (url or "").rsplit("/", 1)[-1]


INSTITUTIONS: dict = {}


def remember_institutions(w: dict) -> None:
    for a in w.get("authorships") or []:
        for i in a.get("institutions") or []:
            iid = short(i.get("id"))
            if iid and iid not in INSTITUTIONS:
                INSTITUTIONS[iid] = {"display_name": (i.get("display_name") or "").replace(";", ","),
                                     "country_code": i.get("country_code") or "", "type": i.get("type") or ""}


def count_ids(col) -> dict:
    c: dict = {}
    for v in col:
        for i in (v or "").split(";"):
            if i:
                c[i] = c.get(i, 0) + 1
    return c


def summarise(w: dict) -> dict:
    remember_institutions(w)
    auths = w.get("authorships") or []
    insts, countries = set(), set()
    for a in auths:
        for i in a.get("institutions") or []:
            if i.get("id"):
                insts.add(short(i["id"]))
            if i.get("country_code"):
                countries.add(i["country_code"])
        for cc in a.get("countries") or []:
            countries.add(cc)
    return {
        "n_authors": len(auths),
        "author_ids": ";".join(sorted({short((a.get("author") or {}).get("id")) for a in auths} - {""})),
        "institution_ids": ";".join(sorted(insts)),
        "countries": ";".join(sorted(countries)),
        "n_institutions": len(insts),
        "n_countries": len(countries),
    }


def run_step_21() -> None:
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False, usecols=["work_id", "doi"])
    corpus = set(ext["work_id"].map(short))
    ours, citing = {}, {}
    files = sorted(glob.glob(str(CACHE / "*" / "*.json.gz")))
    for f in files:
        try:
            d = json.load(gzip.open(f, "rt", encoding="utf-8"))
        except (OSError, ValueError):
            continue
        body = d.get("data", d) if isinstance(d, dict) else d
        for w in (body.get("results") or []) if isinstance(body, dict) else []:
            if "authorships" not in w or not w.get("id"):
                continue
            wid = short(w["id"])
            if wid in corpus:
                s = summarise(w)
                if s["n_authors"] >= ours.get(wid, {}).get("n_authors", -1):
                    ours[wid] = s
            elif "cited_by_count" in w and "referenced_works" in w:  # query 3: Indian papers citing the labs
                refs = [short(r) for r in w.get("referenced_works") or []]
                s = summarise(w)
                citing[wid] = {"work_id": wid, "doi": (w.get("doi") or "").lower(), "year": w.get("publication_year"),
                               "cited_by_count": w.get("cited_by_count"), "n_authors": s["n_authors"],
                               "author_ids": s["author_ids"], "institution_ids": s["institution_ids"],
                               "n_references": len(refs), "n_references_to_corpus": sum(r in corpus for r in refs)}
    missing = corpus - set(ours)
    assert not missing, f"{len(missing)} corpus works have no cached authorships (cache incomplete)"
    out = pd.DataFrame([{"work_id": f"https://openalex.org/{w}", **ours[w]} for w in sorted(ours)])
    out["authors_capped"] = (out["n_authors"] >= CAP).map({True: "TRUE", False: "FALSE"})
    out = out[["work_id", "n_authors", "authors_capped", "n_institutions", "n_countries", "countries", "institution_ids",
               "author_ids"]]
    out.to_csv(FINAL / "work_author_counts.csv", index=False, encoding="utf-8", lineterminator="\n")
    cw = pd.DataFrame(list(citing.values())).sort_values("work_id")
    cw = cw[cw["n_references_to_corpus"] > 0]
    on_ours, on_citing = count_ids(out["institution_ids"]), count_ids(cw["institution_ids"])
    inst = pd.DataFrame([{"institution_id": i, **m,
                          "sector": assign_sector_cluster(m["display_name"], m["type"]) if m["country_code"] == "IN" else "Foreign",
                          "corpus_papers": on_ours.get(i, 0), "citing_papers": on_citing.get(i, 0)}
                         for i, m in sorted(INSTITUTIONS.items()) if i in on_ours or i in on_citing])
    inst.to_csv(FINAL / "institutions_seen.csv", index=False, encoding="utf-8", lineterminator="\n")
    cw.to_csv(FINAL / "citing_works.csv", index=False, encoding="utf-8", lineterminator="\n")
    logger.info(f"Step 21: {len(out):,} corpus papers ({int((out['n_authors'] >= 10).sum()):,} with >= 10 authors, "
                f"{int((out['authors_capped'] == 'TRUE').sum())} capped at {CAP}); {len(cw):,} citing papers; "
                f"{len(files):,} cached files read, 0 API calls")


if __name__ == "__main__":
    run_step_21()
