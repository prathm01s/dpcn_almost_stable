"""Step 20: Remove duplicate papers and non-research items from the exported data.

OpenAlex lists some papers more than once and some items that are not research papers.
Found in the 2016-2026 corpus (D-33):

1. Angewandte Chemie German edition: Wiley publishes every Angewandte paper twice, in the
   International Edition (10.1002/anie.X) and the German edition (10.1002/ange.X). The
   German-edition record is merged into its International Edition twin.
2. Versions of one paper: eLife reviewed-preprint versions (10.7554/elife.N.1, .2, ...) and
   JoVE video DOIs (10.3791/N-v) are merged into one record per paper.
3. Same paper twice in one journal: same normalised title, same year and same journal
   (OpenAlex duplicate records) are merged into one.
4. Repository copies (Zenodo, institutional repositories): not journal or conference papers
   (AGENTS.md 5.5). Merged into the journal version when one exists with the same title,
   otherwise removed.
5. Non-research items: retraction notices, corrections/errata, cover pictures, prefaces and
   editorials (AGENTS.md 5.5 excludes errata and paratext). Removed.

"Merged" = the duplicate's author rows are re-pointed to the kept record (so no lab author
is lost), then (institution, work, author) repeats are dropped. In the kept record the
citation count stays the kept record's own OpenAlex count; the counts are not summed.
Citation and authorship edges are re-pointed the same way; self-loops and repeats are dropped.

Also fixes the "probable former faculty" flag on author rows without an OpenAlex author ID:
Step 07 grouped all ID-less authors as one prolific person (FORMER_CECRI_0005, 936 names).

Then recomputes the files derived from the rows: faculty_master.csv paper/citation/h-index
counts (papers at the scientist's roster lab, as in Step 07) and indian_connections.csv.

Works on data/final/ and runs after the API steps (17, 18) so that their cached request
batches are unchanged; Step 15 runs next and recomputes the Indian citation flags.
Every removed or merged paper is listed in data/review/duplicate_papers_removed.csv.
"""

import json
import re
from pathlib import Path
from typing import Dict

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("20_dedupe_papers")

FINAL = Path("data/final")
REVIEW = Path("data/review")
MANIFESTS = (Path("data/MANIFEST.json"), FINAL / "MANIFEST.json")

# Paper-level columns copied from the kept record onto re-pointed author rows
PAPER_COLS_MAIN = ["title", "year", "type", "journal_name", "issn", "doi", "citations", "quartile",
                   "coauthor_institutes", "cites_indian_inst", "cited_by_indian_inst"]
PAPER_COLS_EXT = ["work_id", "source_id", "source_type", "issn_l", "quartile_year_used", "quartile_match_method",
                  "field", "subfield", "domain", "primary_topic", "is_retracted", "is_partial_year", "collected_at"]

NON_RESEARCH = re.compile(
    r"^\s*(retraction(\s+(note|notice))?(\s+to)?\b"
    r"|correction(\s+to)?\s*[:“\"‘']"
    r"|corrigendum\b|erratum\b|addendum\s*[:“\"]|expression of concern\b"
    r"|cover (picture|image|feature|art)\b|(front|back|inside( front| back)?) cover\b"
    r"|(innen|rück)?titelbild\b"
    r"|preface\s*$|editorial\s*$|foreword\s*$|guest editorial\b)",
    re.IGNORECASE)
REPOSITORY = re.compile(r"zenodo|repository|figshare|arxiv|chemrxiv|biorxiv|medrxiv|research square|ssrn|preprints\.org",
                        re.IGNORECASE)
# DOIs minted by repositories (Zenodo, Figshare, arXiv); other DOIs on repository records belong to journals
REPOSITORY_DOI = re.compile(r"doi\.org/10\.(5281|6084|48550)/", re.IGNORECASE)


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(FINAL / name, dtype=str, keep_default_na=False)


def write(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")


def title_key(t: str) -> str:
    return re.sub(r"[\W_]+", "", t.lower())


def find_duplicates(papers: pd.DataFrame) -> pd.DataFrame:
    """One row per removed paper: work_id, doi, reason, kept_work_id ('' = removed without a twin)."""
    p = papers.copy()
    p["tk"] = p["title"].map(title_key)
    p["cit"] = p["citations"].astype(int)
    by_doi = dict(zip(p["doi"], p["work_id"]))
    out: Dict[str, dict] = {}

    def drop(row, reason, kept=""):
        if row.work_id not in out and row.work_id != kept:
            out[row.work_id] = {"work_id": row.work_id, "doi": row.doi, "title": row.title, "year": row.year,
                                "journal_name": row.journal_name, "citations": row.citations,
                                "reason": reason, "kept_work_id": kept}

    # 5. non-research items
    for r in p[p["title"].str.match(NON_RESEARCH)].itertuples():
        drop(r, "non-research item (retraction notice / correction / cover / preface / editorial)")
    # 1. Angewandte German edition -> International Edition
    for r in p[p["doi"].str.contains("/ange.", regex=False)].itertuples():
        twin = by_doi.get(r.doi.replace("/ange.", "/anie.", 1))
        if twin:
            drop(r, "Angewandte Chemie German edition of an International Edition paper", twin)
    # 2. versions of one DOI (eLife .N versions, JoVE -v video)
    p["base_doi"] = (p["doi"].str.replace(r"(10\.7554/elife\.\d+)\.\d+$", r"\1", regex=True)
                             .str.replace(r"(10\.3791/\d+)-v$", r"\1", regex=True))
    for _, g in p[p["doi"] != ""].groupby("base_doi"):
        if len(g) > 1:
            keep = g.sort_values(["cit", "doi"], ascending=[False, True]).iloc[0]
            for r in g.itertuples():
                drop(r, "another version (DOI) of the same paper", keep.work_id)
    live = p[~p["work_id"].isin(out)]
    # 4. repository records: merged into a journal twin with the same title; otherwise removed when
    #    the record has no DOI or a repository DOI. Repository records carrying a journal's DOI are
    #    journal papers that OpenAlex filed under a repository, and stay.
    repo = live["journal_name"].str.contains(REPOSITORY) | live["source_type"].eq("repository")
    journal_by_title = live[~repo].groupby("tk")["work_id"].first()
    for r in live[repo].itertuples():
        twin = journal_by_title.get(r.tk, "")
        if twin or r.doi == "" or REPOSITORY_DOI.search(r.doi):
            drop(r, "repository copy, not a journal or conference paper", twin)
    live = p[~p["work_id"].isin(out)]
    # 3. same title, year and journal (titles of >= 25 characters, to skip generic ones)
    cand = live[live["tk"].str.len() >= 25]
    for _, g in cand.groupby(["tk", "year", "journal_name"]):
        if len(g) > 1:
            keep = g.sort_values(["cit", "work_id"], ascending=[False, True]).iloc[0]
            for r in g.itertuples():
                drop(r, "duplicate record of the same paper in the same journal", keep.work_id)
    # follow chains: a kept record that is itself removed passes its own target on
    for rec in out.values():
        k, seen = rec["kept_work_id"], set()
        while k in out and k not in seen:
            seen.add(k)
            k = out[k]["kept_work_id"]
        rec["kept_work_id"] = "" if k in out else k
    return pd.DataFrame(list(out.values()), columns=["work_id", "doi", "title", "year", "journal_name", "citations",
                                                     "reason", "kept_work_id"])


def h_index(cites) -> int:
    c = sorted(cites, reverse=True)
    return sum(1 for i, x in enumerate(c, 1) if x >= i)


def run_step_20() -> None:
    logger.info("Starting Step 20: remove duplicate papers and non-research items...")
    main, ext = read("group24_data.csv"), read("group24_data_extended.csv")
    assert len(main) == len(ext) and (main["doi"] == ext["doi"]).all() and (main["author"] == ext["author"]).all()
    df = pd.concat([main, ext[[c for c in ext.columns if c not in main.columns]]], axis=1)

    papers = df.drop_duplicates("work_id")
    dups = find_duplicates(papers)
    REVIEW.mkdir(parents=True, exist_ok=True)
    log = REVIEW / "duplicate_papers_removed.csv"
    # appended, so a re-run (which finds nothing new) keeps the record of earlier removals
    if log.exists():
        dups_log = pd.concat([pd.read_csv(log, dtype=str, keep_default_na=False), dups.astype(str)])
        dups_log = dups_log.drop_duplicates("work_id", keep="last")
    else:
        dups_log = dups
    write(dups_log, log)
    logger.info(f"{len(dups)} papers removed or merged: {dups['reason'].value_counts().to_dict()}")

    # ---- re-point author rows of merged papers to the kept record, drop removed papers
    kept_of = dict(zip(dups["work_id"], dups["kept_work_id"]))
    rec = papers.set_index("work_id")
    rows = df[~df["work_id"].isin(kept_of) | df["work_id"].map(kept_of).ne("")].copy()
    moved = rows["work_id"].isin(kept_of)
    # coauthor_institutes excludes the row's own lab, so it is taken per (paper, lab)
    co_by = df.drop_duplicates(["work_id", "institution"]).set_index(["work_id", "institution"])["coauthor_institutes"]
    kept_ids = rows.loc[moved, "work_id"].map(kept_of)
    for col in PAPER_COLS_MAIN + PAPER_COLS_EXT:
        if col in ("work_id", "coauthor_institutes"):
            continue
        rows.loc[moved, col] = kept_ids.map(rec[col]).values
    keys = list(zip(kept_ids, rows.loc[moved, "institution"]))
    own = rows.loc[moved, "coauthor_institutes"].tolist()
    rows.loc[moved, "coauthor_institutes"] = [co_by.get(k, o) for k, o in zip(keys, own)]
    rows.loc[moved, "work_id"] = rows.loc[moved, "work_id"].map(kept_of)
    # keep the kept record's own rows first, then drop (institution, work, author) repeats
    rows = rows.assign(_m=moved.astype(int), _i=range(len(rows))).sort_values(["_m", "_i"], kind="stable")
    rows = rows.drop_duplicates(["institution", "work_id", "author"]).sort_values("_i").drop(columns=["_m", "_i"])
    logger.info(f"Author rows: {len(df)} -> {len(rows)}")

    # ---- probable-former-faculty flag on rows without an OpenAlex author ID
    bad = rows["faculty_id"].str.startswith("FORMER_") & rows["author_openalex_id"].eq("")
    rows.loc[bad, ["faculty_id", "designation", "department"]] = ""
    rows.loc[bad, "author_role"] = "affiliated_author"
    logger.info(f"Cleared the former-faculty flag on {int(bad.sum())} rows without an author ID")

    main_out = rows[list(main.columns)]
    ext_out = rows[list(ext.columns)]

    # ---- citation and authorship edges
    doi_map = {d: rec.at[k, "doi"] for w, k in kept_of.items() if k for d in [rec.at[w, "doi"]] if d}
    removed_dois = {rec.at[w, "doi"] for w, k in kept_of.items() if not k and rec.at[w, "doi"]}
    cite = read("citation_network.csv")
    n0 = len(cite)
    cite = cite[~cite["source_doi"].isin(removed_dois) & ~cite["target_doi"].isin(removed_dois)].copy()
    cite["source_doi"] = cite["source_doi"].replace(doi_map)
    cite["target_doi"] = cite["target_doi"].replace(doi_map)
    cite = cite[cite["source_doi"] != cite["target_doi"]].drop_duplicates()
    logger.info(f"citation_network.csv: {n0} -> {len(cite)} edges")

    auth = read("authorship_network.csv")
    n0 = len(auth)
    auth = auth[~auth["paper_doi"].isin(removed_dois)].copy()
    auth["paper_doi"] = auth["paper_doi"].replace(doi_map)
    auth = auth[auth["author_a"] != auth["author_b"]].drop_duplicates()
    logger.info(f"authorship_network.csv: {n0} -> {len(auth)} edges")

    # ---- faculty_master counts: papers at the scientist's roster lab (Step 07 definition)
    fm = read("faculty_master.csv")
    lab_of = {"ncl": "CSIR-NCL", "iict": "CSIR-IICT", "cecri": "CSIR-CECRI"}
    fr = ext_out[ext_out["faculty_id"].isin(set(fm["faculty_id"]))].merge(
        fm[["faculty_id", "inst_key"]], on="faculty_id")
    fr = fr[fr["institution"] == fr["inst_key"].map(lab_of)].drop_duplicates(["faculty_id", "work_id"])
    cit = fr["work_id"].map(dict(zip(ext_out["work_id"], ext_out["citations"].astype(int))))
    agg = fr.assign(c=cit).groupby("faculty_id")["c"].agg(["size", "sum", lambda s: h_index(s.tolist())])
    agg.columns = ["n", "c", "h"]
    changed = 0
    for col, src in (("n_papers_corpus", "n"), ("n_citations_corpus", "c"), ("h_index_corpus", "h")):
        new = fm["faculty_id"].map(agg[src]).fillna(0).astype(int).astype(str)
        changed += int((new != fm[col]).sum())
        fm[col] = new
    logger.info(f"faculty_master.csv: {changed} count values updated")

    # ---- indian_connections.csv (Step 14 definition)
    pu = main_out.assign(work_id=ext_out["work_id"].values)[["institution", "work_id", "citations", "coauthor_institutes"]]
    pu = pu.drop_duplicates(["institution", "work_id"])
    recs = [(r.institution, p, int(r.citations)) for r in pu.itertuples()
            for p in sorted({x.strip() for x in r.coauthor_institutes.split(";") if x.strip()})]
    conn = (pd.DataFrame(recs, columns=["your_inst", "partner_inst", "c"])
            .groupby(["your_inst", "partner_inst"]).agg(shared_papers=("c", "count"), total_citations=("c", "sum"))
            .reset_index().sort_values(["your_inst", "shared_papers"], ascending=[True, False]))

    write(main_out, FINAL / "group24_data.csv")
    write(ext_out, FINAL / "group24_data_extended.csv")
    write(cite, FINAL / "citation_network.csv")
    write(auth, FINAL / "authorship_network.csv")
    write(fm, FINAL / "faculty_master.csv")
    write(conn, FINAL / "indian_connections.csv")

    for path in MANIFESTS:
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        m["total_rows"] = len(main_out)
        m["total_distinct_papers"] = int(ext_out["work_id"].nunique())
        m["rows_by_institution"] = main_out["institution"].value_counts().to_dict()
        for name, d in (("group24_data.csv", main_out), ("group24_data_extended.csv", ext_out),
                        ("citation_network.csv", cite), ("authorship_network.csv", auth),
                        ("faculty_master.csv", fm), ("indian_connections.csv", conn)):
            if name in m.get("files", {}):
                m["files"][name]["rows"] = len(d)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(m, f, indent=2)
    logger.info(f"Step 20 complete: {ext_out['work_id'].nunique()} distinct papers. Run Step 15 next.")


if __name__ == "__main__":
    run_step_20()
