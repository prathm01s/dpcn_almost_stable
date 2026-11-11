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
3. Rule (code, D-40): roster entries that are not people (page text scraped as a name: an e-mail
   address, a URL, "Last Updated: <date>", or any digit) are removed like technical staff.
   Departments that are page labels ("Contact Number:") become unknown ("").
4. Rule (code, D-40): "probable former faculty" (Step 07 flag) is a review flag, not a post: the
   designation and department are cleared, and the AGENTS.md 5.7.6 student pattern (at least half
   of the author's papers at the lab as first author, active at most 5 years) becomes an
   affiliated author.
5. Dataset rows that pointed to a removed or unmatched entry become affiliated-author rows
   (faculty_id, department, designation cleared). The author name loses the job title; for
   wrong matches it becomes the name printed on the paper (OpenAlex raw_author_name, read from
   Step 17's cached responses, no API cost). The same names are fixed in authorship_network.csv.

6. Rule (code, D-41): CSIR grade titles. Step 02 had called Scientist-F "Chief Scientist" and moved
   every lower lettered grade up one title; the labels are mapped to the CSIR ladder
   (C Scientist, D Senior, E Principal, F Senior Principal, G Chief Scientist).
7. Reviewed list (config/overrides/author_profile_merges.csv, D-41): OpenAlex split some scientists
   over several author profiles. Rows of a listed profile at the scientist's lab take the scientist's
   identity (or, for a probable former faculty member, the larger profile's flag). Candidates come
   from `python -m src.collect.19_roster_cleanup --propose` (compatible names, same lab, no shared
   paper, >= 3 shared co-authors); Step 20 then recomputes the paper counts and h-indices.

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
NOT_A_PERSON = re.compile(r"@|https?://|www\.|last updated|\d", re.IGNORECASE)
DEPT_ARTEFACT = re.compile(r"^\s*(contact(\s+number)?|phone|tel(ephone)?|e-?mail|fax)\s*:?\s*$", re.IGNORECASE)
STUDENT_MAX_SPAN = 5          # years active at the lab
STUDENT_MIN_FIRST_SHARE = 0.5  # share of the author's lab papers as first author
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


def former_faculty_fixes(ext: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Masks of rows flagged probable_former_faculty: (student pattern -> affiliated author, invented post to clear)."""
    flag = ext["author_role"] == "probable_former_faculty"
    # per person (faculty_id): merged split profiles (D-41) share one FORMER_ id
    rows = ext[flag].drop_duplicates(["institution", "faculty_id", "work_id"])
    g = rows.groupby(["institution", "faculty_id"]).agg(
        y0=("year", lambda s: int(min(s))), y1=("year", lambda s: int(max(s))),
        first=("author_position", lambda s: (s == "first").mean()))
    student = g[(g["y1"] - g["y0"] + 1 <= STUDENT_MAX_SPAN) & (g["first"] >= STUDENT_MIN_FIRST_SHARE)].index
    key = pd.MultiIndex.from_frame(ext[["institution", "faculty_id"]])
    to_affiliated = flag & key.isin(student)
    invented = flag & ~to_affiliated & ((ext["designation"] != "") | (ext["department"] != "Unassigned"))
    return pd.Series(to_affiliated, index=ext.index), invented


# ---- Split OpenAlex profiles (D-41) -------------------------------------------------------------
# OpenAlex sometimes splits one scientist over several author profiles. Step 07 matched each roster
# scientist to one profile, so the papers on the others were counted as someone else's (mostly as
# "probable former faculty"). The merges are a reviewed list (MERGES); propose_profile_merges()
# lists candidates under a strict rule: compatible names, the same lab, never on the same paper,
# and shared co-authors.
MERGES = Path("config/overrides/author_profile_merges.csv")
MERGE_MIN_SHARED = 3          # co-authors the two profiles share
MERGE_MIN_SHARE = 0.2         # ... as a share of the smaller profile's co-authors
TITLES = {"dr", "prof", "mr", "mrs", "ms", "smt", "shri", "sri"}
LAB_NAME = {"ncl": "CSIR-NCL", "iict": "CSIR-IICT", "cecri": "CSIR-CECRI"}

# CSIR grades (CSIR recruitment rules: Scientist-E L-13, F L-13A, G L-14). Step 02 had shifted every
# lettered grade below G up by one title; this maps its labels to the correct ones (D-41).
DESIGNATION_FIX = {
    "Chief Scientist (Scientist-F)": "Senior Principal Scientist (Scientist-F)",
    "Senior Principal Scientist": "Principal Scientist (Scientist-E)",
    "Principal Scientist": "Senior Scientist (Scientist-D)",
    "Senior Scientist": "Scientist (Scientist-C)",
}


def name_tokens(name: str) -> list:
    import unicodedata
    s = unicodedata.normalize("NFKD", clean_name(name)).encode("ascii", "ignore").decode().lower()
    toks = re.sub(r"[^a-z]+", " ", s).split()
    while toks and toks[0] in TITLES:
        toks = toks[1:]
    return toks


def names_compatible(a: str, b: str) -> bool:
    """Same surname; every full given name of one name appears in the other; initials agree in order."""
    ta, tb = name_tokens(a), name_tokens(b)
    if len(ta) < 2 or len(tb) < 2 or ta[-1] != tb[-1]:
        return False
    fa, fb = {t for t in ta if len(t) > 1}, {t for t in tb if len(t) > 1}
    if (fa - fb) and (fb - fa):
        return False
    short, long_ = sorted((ta[:-1], tb[:-1]), key=len)
    if not short[0][0] == long_[0][0]:
        return False
    j = 0
    for t in short:
        while j < len(long_) and not (t == long_[j] or (len(t) == 1 and long_[j].startswith(t))
                                      or (len(long_[j]) == 1 and t.startswith(long_[j]))):
            j += 1
        if j == len(long_):
            return False
        j += 1
    return True


def propose_profile_merges() -> pd.DataFrame:
    """Candidate merges: an unmatched profile at a roster scientist's lab (or a second profile of a
    probable former faculty member) with a compatible name, no shared paper, and shared co-authors."""
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv(FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    ext = ext[ext["author_openalex_id"] != ""]
    works = ext.groupby("author_openalex_id")["work_id"].agg(set)
    authors_of = ext.groupby("work_id")["author_openalex_id"].agg(set)
    co = {a: set().union(*(authors_of[w] for w in ws)) - {a} for a, ws in works.items()}
    prof = (ext.groupby(["institution", "author_openalex_id"])
            .agg(name=("author", lambda s: s.mode().iloc[0]), role=("author_role", "first"),
                 fid=("faculty_id", "first"), n=("work_id", "nunique")).reset_index())
    keeps = []  # (lab, kept faculty_id, kept name, kept profiles)
    for r in fm[fm["author_id"] != ""].itertuples():
        keeps.append((LAB_NAME[r.inst_key], r.faculty_id, r.full_name, {r.author_id}))
    for r in prof[prof["role"] == "probable_former_faculty"].itertuples():
        keeps.append((r.institution, r.fid, r.name, {r.author_openalex_id}))
    rows = []
    for lab, fid, name, kept in keeps:
        kw = set().union(*(works[a] for a in kept))
        kc = set().union(*(co[a] for a in kept)) - kept
        cand = prof[(prof["institution"] == lab) & (prof["role"] != "faculty") & ~prof["author_openalex_id"].isin(kept)
                    & (prof["fid"] != fid)]  # not a profile already joined to this person
        for c in cand.itertuples():
            if fid.startswith("FORMER_") and (c.role == "probable_former_faculty" and c.n > prof.loc[
                    prof["author_openalex_id"].isin(kept), "n"].max()):
                continue  # the larger profile keeps; its own pass absorbs the smaller one
            if not names_compatible(name, c.name):
                continue
            a = c.author_openalex_id
            shared = len(kc & co[a])
            share = shared / max(1, min(len(kc), len(co[a])))
            rows.append({"keep_faculty_id": fid, "lab": lab, "keep_name": name, "merge_author_id": a,
                         "merge_name": c.name, "merge_role": c.role, "merge_papers": c.n,
                         "shared_papers": len(kw & works[a]), "shared_coauthors": shared,
                         "coauthor_share": round(share, 2)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    ok = (out["shared_papers"] == 0) & (out["shared_coauthors"] >= MERGE_MIN_SHARED) & (out["coauthor_share"] >= MERGE_MIN_SHARE)
    out["passes_rule"] = ok
    # a profile that fits two people is ambiguous: never merged
    n_fit = out[ok].groupby("merge_author_id")["keep_faculty_id"].nunique()
    out["ambiguous"] = out["merge_author_id"].map(n_fit).fillna(0).gt(1)
    return out.sort_values(["passes_rule", "shared_coauthors"], ascending=False)


def resolve_profile_merges(cand: pd.DataFrame, decided_on: str) -> pd.DataFrame:
    """Profiles joined by passing pairs form one person. The group goes to its roster scientist
    (skipped if it touches two), else to its largest probable-former-faculty profile."""
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv(FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    prof_of_fid = {f: a for f, a in zip(fm["faculty_id"], fm["author_id"]) if a}
    former = ext[ext["faculty_id"].str.startswith("FORMER_")].drop_duplicates("faculty_id")
    prof_of_fid.update(zip(former["faculty_id"], former["author_openalex_id"]))
    parent: Dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ok = cand[cand["passes_rule"]] if not cand.empty else cand
    for r in ok.itertuples():
        parent[find(prof_of_fid[r.keep_faculty_id])] = find(r.merge_author_id)
    roster_of = {a: f for f, a in zip(fm["faculty_id"], fm["author_id"]) if a}
    papers = ext.groupby("author_openalex_id")["work_id"].nunique()
    groups: Dict[str, list] = {}
    for x in list(parent):
        groups.setdefault(find(x), []).append(x)
    out = []
    for members in groups.values():
        fac = sorted({roster_of[a] for a in members if a in roster_of})
        if len(fac) > 1:
            logger.warning(f"Profiles {members} fit {fac}: not merged")
            continue
        if fac:
            keep_fid, keep_prof = fac[0], prof_of_fid[fac[0]]
        else:
            keep_prof = max(members, key=lambda a: papers.get(a, 0))
            keep_fid = next((f for f, a in prof_of_fid.items() if a == keep_prof and f.startswith("FORMER_")), "")
            if not keep_fid:
                continue
        for a in sorted(set(members) - {keep_prof}):
            ev = ok[(ok["merge_author_id"] == a) | (ok["keep_faculty_id"].map(prof_of_fid) == a)].iloc[0]
            out.append({"keep_faculty_id": keep_fid, "lab": ev["lab"], "merge_author_id": a,
                        "merge_name": ev["merge_name"] if ev["merge_author_id"] == a else ev["keep_name"],
                        "merge_papers": int(papers.get(a, 0)),
                        "evidence": f"compatible name; {ev['shared_papers']} shared papers; "
                                    f"{ev['shared_coauthors']} shared co-authors ({ev['coauthor_share']:.0%})",
                        "decided_on": decided_on})
    cols = ["keep_faculty_id", "lab", "merge_author_id", "merge_name", "merge_papers", "evidence", "decided_on"]
    return pd.DataFrame(out, columns=cols).sort_values(["lab", "keep_faculty_id", "merge_author_id"])


def apply_profile_merges(ext: pd.DataFrame, fm: pd.DataFrame) -> pd.Series:
    """Rows of each listed profile at the kept scientist's lab take that scientist's identity. Returns the mask."""
    if not MERGES.exists():
        return pd.Series(False, index=ext.index)
    mg = pd.read_csv(MERGES, dtype=str, keep_default_na=False)
    fac = fm.set_index("faculty_id")
    hit = pd.Series(False, index=ext.index)
    for r in mg.itertuples():
        m = (ext["author_openalex_id"] == r.merge_author_id) & (ext["institution"] == r.lab) & (ext["faculty_id"] != r.keep_faculty_id)
        if not m.any():
            continue
        if r.keep_faculty_id in fac.index:  # roster scientist
            f = fac.loc[r.keep_faculty_id]
            ext.loc[m, ["author_role", "faculty_id", "department", "designation", "author"]] = [
                "faculty", r.keep_faculty_id, f["department"], f["designation"], f["full_name"]]
        else:  # second profile of a probable former faculty member
            k = ext[ext["faculty_id"] == r.keep_faculty_id].iloc[0]
            ext.loc[m, ["author_role", "faculty_id", "department", "designation", "author"]] = [
                k["author_role"], r.keep_faculty_id, k["department"], k["designation"], k["author"]]
        hit |= m
    return hit


def run_step_19() -> None:
    fm = pd.read_csv(FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    ov = pd.read_csv(OVERRIDES, dtype=str, keep_default_na=False) if OVERRIDES.exists() else pd.DataFrame(
        columns=["faculty_id", "action", "reason", "decided_on"])

    tech = fm[fm["full_name"].str.contains(TECH_TITLE)]
    not_person = fm[fm["full_name"].str.contains(NOT_A_PERSON)]
    bad_dept = fm["department"].str.match(DEPT_ARTEFACT)
    drop_dup = set(ov.loc[ov["action"] == "drop_duplicate", "faculty_id"]) & set(fm["faculty_id"])
    unmatch = set(ov.loc[(ov["action"] == "unmatch"), "faculty_id"]) & set(fm.loc[fm["author_id"] != "", "faculty_id"])
    removed = set(tech["faculty_id"]) | set(not_person["faculty_id"]) | drop_dup
    # OpenAlex profiles that were matched to the wrong scientist: every row on them gets the paper's own name
    wrong_profiles = set(fm.loc[fm["faculty_id"].isin(unmatch), "author_id"]) - {""}
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    old_names = ext["author"].copy()
    # D-41: CSIR grade titles, then split OpenAlex profiles (before the former-faculty rules below)
    desig_fixed = fm["designation"].isin(DESIGNATION_FIX)
    fm["designation"] = fm["designation"].replace(DESIGNATION_FIX)
    ext["designation"] = ext["designation"].replace(DESIGNATION_FIX)
    merged = apply_profile_merges(ext, fm)
    to_affiliated, invented = former_faculty_fixes(ext)
    bad_dept_ids = set(fm.loc[bad_dept, "faculty_id"])
    logger.info(f"Technical staff on roster: {len(tech)}; not a person: {len(not_person)}; duplicates: {len(drop_dup)}; "
                f"wrong matches: {len(unmatch)}; page-label departments: {len(bad_dept_ids)}; "
                f"former-faculty rows: {int(to_affiliated.sum())} student pattern, {int(invented.sum())} invented post; "
                f"designations corrected: {int(desig_fixed.sum())}; rows from merged profiles: {int(merged.sum())}")
    if not (removed or unmatch or bad_dept_ids or to_affiliated.any() or invented.any()
            or desig_fixed.any() or merged.any()):
        logger.info("Roster already clean; nothing to do.")
        return

    # Review log of removed entries (appended, so earlier runs stay recorded)
    reason_of = dict(zip(ov["faculty_id"], ov["reason"]))
    log = fm[fm["faculty_id"].isin(removed)].copy()
    log["job_title"] = [TECH_TITLE.search(n).group(0).strip() if TECH_TITLE.search(n) else "" for n in log["full_name"]]
    np_ids = set(not_person["faculty_id"])
    log["reason"] = [f"Not scientific cadre: roster name carries technical title '{t}'" if t else
                     "Not a person: roster page text scraped as a name (D-40)" if f in np_ids else reason_of.get(f, "")
                     for f, t in zip(log["faculty_id"], log["job_title"])]
    log = log[["faculty_id", "inst_key", "full_name", "job_title", "designation", "department", "author_id",
               "n_papers_corpus", "reason"]]
    if REVIEW.exists():
        log = pd.concat([pd.read_csv(REVIEW, dtype=str, keep_default_na=False), log]).drop_duplicates("faculty_id")
    write(log, REVIEW)

    # faculty_master: drop removed entries, clear wrong matches
    fm.loc[bad_dept, "department"] = ""
    fm = fm[~fm["faculty_id"].isin(removed)].copy()
    um = fm["faculty_id"].isin(unmatch)
    fm.loc[um, ["author_id", "match_score"]] = ""
    fm.loc[um, ["h_index_corpus", "n_papers_corpus", "n_citations_corpus"]] = "0"
    fm.loc[um, "match_confidence"] = "unmatched"
    fm.loc[um, "is_matched"] = "False"
    fm.loc[um, "match_evidence"] = [f"Unmatched by override: {reason_of.get(f, '')}" for f in fm.loc[um, "faculty_id"]]
    if MERGES.exists():
        mg = pd.read_csv(MERGES, dtype=str, keep_default_na=False)
        extra = mg.groupby("keep_faculty_id")["merge_author_id"].agg(lambda s: ", ".join(a.rsplit("/", 1)[-1] for a in s))
        for i in fm.index[fm["faculty_id"].isin(extra.index)]:
            note = f"; also OpenAlex {extra[fm.at[i, 'faculty_id']]} (split profiles, D-41)"
            if "D-41" not in fm.at[i, "match_evidence"]:
                fm.at[i, "match_evidence"] += note
    write(fm, FINAL / "faculty_master.csv")

    # Dataset rows
    main = pd.read_csv(FINAL / "group24_data.csv", dtype=str, keep_default_na=False)
    assert len(main) == len(ext) and (main["doi"] == ext["doi"]).all() and (main["author"] == old_names).all()

    hit = ext["faculty_id"].isin(removed | unmatch)
    wrong = ext["author_openalex_id"].isin(wrong_profiles) & ext["faculty_id"].isin(removed | unmatch)
    pairs = {(w.rsplit("/", 1)[-1], a.rsplit("/", 1)[-1])
             for w, a in zip(ext.loc[wrong, "work_id"], ext.loc[wrong, "author_openalex_id"])}
    raw = raw_author_names(pairs, {w.rsplit("/", 1)[-1] for w in ext["work_id"]})

    new_names = ext["author"].map(clean_name)
    for idx in ext.index[wrong]:
        key = (ext.at[idx, "work_id"].rsplit("/", 1)[-1], ext.at[idx, "author_openalex_id"].rsplit("/", 1)[-1])
        if raw.get(key):
            new_names.at[idx] = raw[key]
    ext.loc[hit, "author_role"] = "affiliated_author"
    ext.loc[hit, ["faculty_id", "department", "designation"]] = ""
    ext.loc[ext["faculty_id"].isin(bad_dept_ids), "department"] = ""
    ext.loc[to_affiliated, "author_role"] = "affiliated_author"
    ext.loc[to_affiliated, "faculty_id"] = ""
    ext.loc[to_affiliated | invented, "designation"] = ""
    ext.loc[to_affiliated | invented, "department"] = "Unassigned"
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
        prev = m.get("roster_cleanup", {})
        m["roster_cleanup"] = {"technical_staff_removed": int(len(tech)) or prev.get("technical_staff_removed", 0),
                               "not_a_person_removed": len(not_person) or prev.get("not_a_person_removed", 0),
                               "duplicates_removed": len(drop_dup) or prev.get("duplicates_removed", 0),
                               "wrong_matches_cleared": len(unmatch) or prev.get("wrong_matches_cleared", 0),
                               "page_label_departments_cleared": len(bad_dept_ids) or prev.get("page_label_departments_cleared", 0),
                               "former_faculty_student_pattern": int(to_affiliated.sum()) or prev.get("former_faculty_student_pattern", 0),
                               "author_names_cleaned": renamed or prev.get("author_names_cleaned", 0),
                               "designations_corrected": int(desig_fixed.sum()) or prev.get("designations_corrected", 0),
                               "rows_from_merged_profiles": int(merged.sum()) or prev.get("rows_from_merged_profiles", 0)}
        mpath.write_text(json.dumps(m, indent=2), encoding="utf-8", newline="\n")
    logger.info(f"Roster: {len(fm)} entries ({len(removed)} removed, {len(unmatch)} unmatched); "
                f"{int(hit.sum())} rows now affiliated authors; {renamed} author names cleaned")


if __name__ == "__main__":
    import sys
    if "--propose" in sys.argv:
        c = propose_profile_merges()
        out = Path("data/review/author_profile_merge_candidates.csv")
        write(c, out)
        write(resolve_profile_merges(c, pd.Timestamp.today().strftime("%Y-%m-%d")),
              Path("data/review/author_profile_merges_proposed.csv"))
        logger.info(f"{int(c['passes_rule'].sum())} pairs pass the rule; review, then copy to {MERGES}")
    else:
        run_step_19()
