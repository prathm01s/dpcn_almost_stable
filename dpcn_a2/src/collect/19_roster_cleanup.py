"""Step 19: Remove non-faculty entries and wrong matches from the faculty roster.

Faculty = scientific cadre (AGENTS.md §5.2; DECISIONS D-01). The IICT staff pages also list
technical staff, whose job title was scraped into the name (e.g. "Dr. X Sr. Technical Officer (3)")
while their designation was recorded as "Scientist". This step:

1. Rule (code): roster entries whose name ends in a technical title (Technical Officer,
   Technical Assistant, Technician, with Sr./Senior/Principal and grade) are not faculty.
   They are removed from faculty_master.csv and listed in data/review/roster_excluded.csv.
2. Manual decisions (config/overrides/roster_overrides.csv, with reason and date):
   - drop_duplicate: remove a second roster entry for a person already listed
   - unmatch: keep the scientist on the roster but drop a wrong OpenAlex author match
3. Dataset rows that pointed to a removed or unmatched entry become affiliated-author rows
   (faculty_id, department, designation cleared). The author name loses the job title; for
   wrong matches it becomes the name printed on the paper (OpenAlex raw_author_name, read from
   Step 17's cached responses, no API cost). The same names are fixed in authorship_network.csv.

Idempotent: a second run finds nothing to change. Run after Step 18 and before Step 15.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

from src.common.http import http_client
from src.common.logging import get_logger
from src.common.openalex import OPENALEX_BASE

logger = get_logger("19_roster_cleanup")

FINAL = Path("data/final")
OVERRIDES = Path("config/overrides/roster_overrides.csv")
REVIEW = Path("data/review/roster_excluded.csv")
TECH_TITLE = re.compile(
    r"\s+(?:(?:Sr|Senior|Principal)\.?\s+)?(?:Technical Officer|Technical Assistant|Technician)(?:\s*\(\d+\))?\s*$",
    re.IGNORECASE,
)
BATCH = 100
SELECT = "id,doi,publication_year,referenced_works,authorships"  # Step 17's query, so responses are cached


def clean_name(name: str) -> str:
    return TECH_TITLE.sub("", name).strip()


def raw_author_names(pairs: Set[Tuple[str, str]], all_ids) -> Dict[Tuple[str, str], str]:
    """(work short id, author short id) -> raw_author_name, from Step 17's cached batch responses."""
    out: Dict[Tuple[str, str], str] = {}
    if not pairs:
        return out
    ids = sorted(all_ids)
    wanted_works = {w for w, _ in pairs}
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        if not wanted_works & set(chunk):
            continue
        data = http_client.get_json(f"{OPENALEX_BASE}/works", params={
            "filter": f"openalex_id:{'|'.join(chunk)}", "per_page": BATCH, "select": SELECT,
        })
        for w in data.get("results", []):
            wid = w["id"].rsplit("/", 1)[-1]
            for a in w.get("authorships") or []:
                aid = ((a.get("author") or {}).get("id") or "").rsplit("/", 1)[-1]
                if (wid, aid) in pairs:
                    out[(wid, aid)] = a.get("raw_author_name") or (a.get("author") or {}).get("display_name") or ""
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def run_step_19() -> None:
    fm = pd.read_csv(FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    ov = pd.read_csv(OVERRIDES, dtype=str, keep_default_na=False) if OVERRIDES.exists() else pd.DataFrame(
        columns=["faculty_id", "action", "reason", "decided_on"])

    tech = fm[fm["full_name"].str.contains(TECH_TITLE)]
    drop_dup = set(ov.loc[ov["action"] == "drop_duplicate", "faculty_id"]) & set(fm["faculty_id"])
    unmatch = set(ov.loc[(ov["action"] == "unmatch"), "faculty_id"]) & set(fm.loc[fm["author_id"] != "", "faculty_id"])
    removed = set(tech["faculty_id"]) | drop_dup
    # OpenAlex profiles that were matched to the wrong scientist: every row on them gets the paper's own name
    wrong_profiles = set(fm.loc[fm["faculty_id"].isin(unmatch), "author_id"]) - {""}
    logger.info(f"Technical staff on roster: {len(tech)}; duplicates: {len(drop_dup)}; wrong matches: {len(unmatch)}")
    if not (removed or unmatch):
        logger.info("Roster already clean; nothing to do.")
        return

    # Review log of removed entries (appended, so earlier runs stay recorded)
    reason_of = dict(zip(ov["faculty_id"], ov["reason"]))
    log = fm[fm["faculty_id"].isin(removed)].copy()
    log["job_title"] = [TECH_TITLE.search(n).group(0).strip() if TECH_TITLE.search(n) else "" for n in log["full_name"]]
    log["reason"] = [f"Not scientific cadre: roster name carries technical title '{t}'" if t else reason_of.get(f, "")
                     for f, t in zip(log["faculty_id"], log["job_title"])]
    log = log[["faculty_id", "inst_key", "full_name", "job_title", "designation", "department", "author_id",
               "n_papers_corpus", "reason"]]
    if REVIEW.exists():
        log = pd.concat([pd.read_csv(REVIEW, dtype=str, keep_default_na=False), log]).drop_duplicates("faculty_id")
    write(log, REVIEW)

    # faculty_master: drop removed entries, clear wrong matches
    fm = fm[~fm["faculty_id"].isin(removed)].copy()
    um = fm["faculty_id"].isin(unmatch)
    fm.loc[um, ["author_id", "match_score"]] = ""
    fm.loc[um, ["h_index_corpus", "n_papers_corpus", "n_citations_corpus"]] = "0"
    fm.loc[um, "match_confidence"] = "unmatched"
    fm.loc[um, "is_matched"] = "False"
    fm.loc[um, "match_evidence"] = [f"Unmatched by override: {reason_of.get(f, '')}" for f in fm.loc[um, "faculty_id"]]
    write(fm, FINAL / "faculty_master.csv")

    # Dataset rows
    main = pd.read_csv(FINAL / "group24_data.csv", dtype=str, keep_default_na=False)
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    assert len(main) == len(ext) and (main["doi"] == ext["doi"]).all() and (main["author"] == ext["author"]).all()

    hit = ext["faculty_id"].isin(removed | unmatch)
    wrong = ext["author_openalex_id"].isin(wrong_profiles) & ext["faculty_id"].isin(removed | unmatch)
    pairs = {(w.rsplit("/", 1)[-1], a.rsplit("/", 1)[-1])
             for w, a in zip(ext.loc[wrong, "work_id"], ext.loc[wrong, "author_openalex_id"])}
    raw = raw_author_names(pairs, {w.rsplit("/", 1)[-1] for w in ext["work_id"]})

    old_names = ext["author"].copy()
    new_names = ext["author"].map(clean_name)
    for idx in ext.index[wrong]:
        key = (ext.at[idx, "work_id"].rsplit("/", 1)[-1], ext.at[idx, "author_openalex_id"].rsplit("/", 1)[-1])
        if raw.get(key):
            new_names.at[idx] = raw[key]
    ext.loc[hit, "author_role"] = "affiliated_author"
    ext.loc[hit, ["faculty_id", "department", "designation"]] = ""
    ext["author"] = new_names
    main["author"] = new_names
    write(main, FINAL / "group24_data.csv")
    write(ext, FINAL / "group24_data_extended.csv")
    renamed = int((old_names != new_names).sum())

    # authorship_network.csv: same renames, per paper
    rename = {(d, o): n for d, o, n in zip(ext["doi"], old_names, new_names) if o != n}
    auth = pd.read_csv(FINAL / "authorship_network.csv", dtype=str, keep_default_na=False)
    for col in ("author_a", "author_b"):
        auth[col] = [rename.get((d, n), clean_name(n)) for d, n in zip(auth["paper_doi"], auth[col])]
    auth = auth[auth["author_a"] != auth["author_b"]].drop_duplicates()
    write(auth, FINAL / "authorship_network.csv")

    for mpath in (Path("data/MANIFEST.json"), FINAL / "MANIFEST.json"):
        m = json.loads(mpath.read_text(encoding="utf-8"))
        for name in ("faculty_master.csv", "authorship_network.csv"):
            m["files"].setdefault(name, {"path": f"data/final/{name}"})
            m["files"][name]["sha256"] = sha256(FINAL / name)
        m["files"]["faculty_master.csv"]["rows"] = len(fm)
        m["files"]["authorship_network.csv"]["rows"] = len(auth)
        m["roster_cleanup"] = {"technical_staff_removed": int(len(tech)), "duplicates_removed": len(drop_dup),
                               "wrong_matches_cleared": len(unmatch), "author_names_cleaned": renamed}
        mpath.write_text(json.dumps(m, indent=2), encoding="utf-8", newline="\n")
    logger.info(f"Roster: {len(fm)} entries ({len(removed)} removed, {len(unmatch)} unmatched); "
                f"{int(hit.sum())} rows now affiliated authors; {renamed} author names cleaned")


if __name__ == "__main__":
    run_step_19()
