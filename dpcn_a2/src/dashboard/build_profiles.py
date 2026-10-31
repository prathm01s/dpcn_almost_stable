"""Build per-scientist profiles for the dashboard's hover cards and profile panel.

One record per roster scientist (data/final/faculty_master.csv), keyed by faculty_id,
written to dashboard/data/g24_profiles.js as window.G24_PROFILES (a JS global, so the
dashboard keeps working from file://). Everything is computed from data/final and
stats/tables; nothing is fetched.

Per scientist: identity and OpenAlex link, headline stats (from faculty_performance.csv),
papers and citations by publication year, research subfields, top journals, most-cited
papers, partner institutes, and in-corpus co-authors (by OpenAlex author ID) with the
co-author links among them for the ego network.
"""

import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("build_profiles")

OUTPUT_JS = Path("dashboard/data/g24_profiles.js")
YEARS = list(range(2016, 2027))
MAX_COLLABORATORS = 30
TOP_TAGS = 8
TOP_JOURNALS = 5
TOP_PAPERS = 6
TOP_PARTNERS = 8
INST_KEY = {"CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri"}


def _split(s: str):
    return [p.strip() for p in s.split(";") if p.strip()]


def build_profiles() -> dict:
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    perf = pd.read_csv("stats/tables/faculty_performance.csv", dtype=str, keep_default_na=False).set_index("faculty_id")
    hubs = pd.read_csv("stats/tables/hub_authors.csv", dtype=str, keep_default_na=False)
    hubs = hubs[hubs["scope"] == "Group 24 Combined"].set_index("author_openalex_id")

    papers = ext.drop_duplicates("work_id").set_index("work_id")
    papers["citations_i"] = papers["citations"].astype(int)
    papers["year_i"] = papers["year"].astype(int)

    # Authors on each work (OpenAlex IDs, our three labs only) and display names
    with_id = ext[ext["author_openalex_id"] != ""]
    work_authors = with_id.groupby("work_id")["author_openalex_id"].agg(lambda s: sorted(set(s)))
    author_name = with_id.groupby("author_openalex_id")["author"].agg(lambda s: s.mode().iloc[0])
    author_lab = with_id.groupby("author_openalex_id")["institution"].agg(lambda s: s.mode().iloc[0])

    matched = fm[(fm["is_matched"] == "True") & (fm["author_id"] != "")]
    fid_by_author = dict(zip(matched["author_id"], matched["faculty_id"]))
    lab_of = {k: v for k, v in zip(fm["faculty_id"], fm["inst_key"].map({v: k for k, v in INST_KEY.items()}))}

    fac_rows = ext[ext["faculty_id"].isin(fm["faculty_id"])]
    works_by_fid = fac_rows.groupby("faculty_id")["work_id"].agg(lambda s: sorted(set(s)))

    # Rank within lab by citations among scientists with papers
    active = perf[perf["papers"].astype(int) > 0].copy()
    active["citations_i"] = active["citations"].astype(int)
    rank_in_lab, lab_size = {}, Counter(active["institution"])
    for lab, g in active.groupby("institution"):
        for r, fid in enumerate(g.sort_values(["citations_i", "name"], ascending=[False, True]).index, 1):
            rank_in_lab[fid] = r

    profiles = {}
    for _, f in fm.iterrows():
        fid = f["faculty_id"]
        p = perf.loc[fid] if fid in perf.index else None
        lab = lab_of.get(fid, "")
        prof = {
            "id": fid,
            "name": f["full_name"],
            "lab": lab,
            "lab_key": INST_KEY.get(lab, "all"),
            "designation": f["designation"],
            "division": f["department"],
            "openalex": f["author_id"],
            "papers": int(p["papers"]) if p is not None else 0,
            "citations": int(p["citations"]) if p is not None else 0,
            "h_index": int(p["h_index_corpus"]) if p is not None and p["h_index_corpus"] else 0,
            "mean_citations": float(p["mean_citations_per_paper"]) if p is not None and p["mean_citations_per_paper"] else 0.0,
            "q1_share_pct": float(p["q1_share_pct"]) if p is not None and p["q1_share_pct"] else 0.0,
            "first_author_papers": int(p["first_author_papers"]) if p is not None and p["first_author_papers"] else 0,
            "corresponding_papers": int(p["corresponding_author_papers"]) if p is not None and p["corresponding_author_papers"] else 0,
            "active_years": p["active_years"] if p is not None else "",
            "rank_in_lab": rank_in_lab.get(fid),
            "lab_active_faculty": lab_size.get(lab, 0),
        }
        works = works_by_fid.get(fid, [])
        if not works:
            profiles[fid] = prof
            continue
        wp = papers.loc[works]

        prof["by_year"] = [
            {"year": y,
             "papers": int((wp["year_i"] == y).sum()),
             "citations": int(wp.loc[wp["year_i"] == y, "citations_i"].sum())}
            for y in YEARS
        ]
        subfields = Counter(s for s in wp["subfield"] if s)
        prof["interests"] = [{"name": k, "papers": v} for k, v in subfields.most_common(TOP_TAGS)]

        journals = []
        for name, g in wp[wp["journal_name"] != ""].groupby("journal_name"):
            q = g["quartile"][g["quartile"] != ""]
            journals.append({"name": name, "papers": len(g), "quartile": q.mode().iloc[0] if len(q) else ""})
        prof["journals"] = sorted(journals, key=lambda j: (-j["papers"], j["name"]))[:TOP_JOURNALS]

        top = wp.sort_values(["citations_i", "year_i"], ascending=[False, False]).head(TOP_PAPERS)
        prof["top_papers"] = [{"title": r["title"], "journal": r["journal_name"], "year": int(r["year_i"]),
                               "citations": int(r["citations_i"]), "doi": r["doi"], "quartile": r["quartile"]}
                              for _, r in top.iterrows()]

        partners = Counter(i for c in wp["coauthor_institutes"] for i in _split(c))
        prof["partners"] = [{"name": k, "papers": v} for k, v in partners.most_common(TOP_PARTNERS)]

        # In-corpus co-authors, by OpenAlex author ID
        me = f["author_id"]
        joint = Counter()
        for w in works:
            for a in work_authors.get(w, []):
                if a != me:
                    joint[a] += 1
        top_collab = sorted(joint, key=lambda a: (-joint[a], author_name[a]))[:MAX_COLLABORATORS]
        prof["n_coauthors"] = len(joint)
        prof["collaborators"] = [{
            "openalex": a,
            "name": author_name[a],
            "lab": author_lab[a],
            "faculty_id": fid_by_author.get(a),
            "joint_papers": joint[a],
        } for a in top_collab]

        # Links among those collaborators: papers of this scientist they co-authored together
        idx = {a: i for i, a in enumerate(top_collab)}
        pair = Counter()
        for w in works:
            present = sorted(idx[a] for a in work_authors.get(w, []) if a in idx)
            for i, j in itertools.combinations(present, 2):
                pair[(i, j)] += 1
        prof["collab_links"] = [[i, j, n] for (i, j), n in sorted(pair.items())]

        if me in hubs.index:
            h = hubs.loc[me]
            prof["hub"] = {"rank": int(h["rank"]), "institutions_bridged": int(h["institutions_bridged"])}
        profiles[fid] = prof

    return profiles


def run_build_profiles() -> Path:
    profiles = build_profiles()
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(profiles, ensure_ascii=False, separators=(",", ":"))
    OUTPUT_JS.write_text(f"window.G24_PROFILES = {payload};\n", encoding="utf-8")
    n_active = sum(1 for p in profiles.values() if p["papers"] > 0)
    logger.info(f"✓ Saved {len(profiles)} profiles ({n_active} with papers) to {OUTPUT_JS} "
                f"({OUTPUT_JS.stat().st_size / 1024:.0f} KB)")
    return OUTPUT_JS


if __name__ == "__main__":
    run_build_profiles()
