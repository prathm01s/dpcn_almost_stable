"""Phase II analyses (instructor's directions of 3 Nov 2026; D-34).

Every table is computed from data/final/ (and config/); nothing is typed in.

Definitions
- Journal IF = SCImago "Cites / Doc. (2 years)" of the paper's journal in its quartile year
  (src/stats/journal_if.py). Scopus-based analogue, not Clarivate's JIF.
- n_authors = all authors of the paper in OpenAlex (data/final/work_author_counts.csv, Step 21);
  OpenAlex lists at most 100, so 100 means "100 or more".
- Collaborating institutions = distinct OpenAlex institutions on the papers other than the lab
  itself (for "All three": other than the three labs); all countries.
- Faculty = roster scientists with >= 1 paper; their papers are those at their roster lab
  (src/stats/networks.faculty_papers). Students and project staff stay in all paper statistics;
  they are left out only of the faculty networks.
- Non-governmental citing institutions = Indian institutions in sector Private or Industry
  (src/common/sectors.py rules, corrected by config/overrides/sector_overrides.csv).

Outputs (stats/tables/phase2_*.csv) — see the docstring of each function.
"""

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

import networkx as nx
import numpy as np
import pandas as pd
import yaml

from src.common.logging import get_logger
from src.stats.journal_if import journal_if_lookup
from src.stats.networks import (LAB_OF_KEY, active_faculty, corpus_dois, faculty_citation_graph,
                                faculty_coauthor_graph, faculty_papers, incorpus_citation_edges)

logger = get_logger("stats_phase2")

FINAL = Path("data/final")
TABLES = Path("stats/tables")
LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
ALL = "Group 24 Combined"
PERIODS = [("2016–2018", 2016, 2018), ("2019–2021", 2019, 2021), ("2022–2024", 2022, 2024), ("2025–2026*", 2025, 2026)]
NON_GOV = {"Private", "Industry"}
LARGE = 10      # instructor: papers with fewer than 10 vs 10 or more authors
VERY_LARGE = 30


def split(s: str) -> List[str]:
    return [x for x in (s or "").split(";") if x]


def lab_institution_ids() -> Dict[str, Set[str]]:
    cfg = yaml.safe_load(open("config/institutions.yaml", encoding="utf-8"))
    out = {}
    for key, lab in LAB_OF_KEY.items():
        out[lab] = {i.rsplit("/", 1)[-1] for i in cfg[key]["openalex_institution_ids"]}
    return out


def sector_table() -> pd.DataFrame:
    inst = pd.read_csv(FINAL / "institutions_seen.csv", dtype=str, keep_default_na=False)
    ov = pd.read_csv("config/overrides/sector_overrides.csv", dtype=str, keep_default_na=False)
    inst["sector_rule"] = inst["sector"]
    for r in ov.itertuples():
        m = (inst["country_code"] == "IN") & inst["display_name"].str.contains(r.name_contains, case=False, regex=False)
        inst.loc[m, "sector"] = r.sector
    for c in ("corpus_papers", "citing_papers"):
        inst[c] = inst[c].astype(int)
    return inst.set_index("institution_id")


# ---------------------------------------------------------------------------
def paper_table() -> pd.DataFrame:
    """One row per (institution, paper) with IF, author count, collaborating institutions."""
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    w = ext.drop_duplicates(["institution", "work_id"]).copy()
    jif = journal_if_lookup(ext.drop_duplicates("work_id"))
    wac = pd.read_csv(FINAL / "work_author_counts.csv", dtype=str, keep_default_na=False).set_index("work_id")
    w["jif"] = w["work_id"].map(jif)
    w["n_authors"] = w["work_id"].map(wac["n_authors"]).astype(int)
    w["capped"] = w["work_id"].map(wac["authors_capped"]).eq("TRUE")
    w["inst_ids"] = w["work_id"].map(wac["institution_ids"]).map(lambda s: set(split(s)))
    w["countries"] = w["work_id"].map(wac["countries"]).map(lambda s: set(split(s)))
    w["author_ids"] = w["work_id"].map(wac["author_ids"]).map(lambda s: set(split(s)))
    w["year"] = w["year"].astype(int)
    w["citations"] = w["citations"].astype(int)
    labs = ext.groupby("work_id")["institution"].agg(lambda s: "; ".join(sorted(set(s))))
    w["labs"] = w["work_id"].map(labs)
    return w


def groups(p: pd.DataFrame):
    for lab in LABS:
        yield lab, p[p["institution"] == lab]
    yield ALL, p.drop_duplicates("work_id")


def overview_row(g: pd.DataFrame, own: Set[str], inst: pd.DataFrame) -> Dict:
    q1 = g["quartile"] == "Q1"
    partners = set().union(*g["inst_ids"]) - own if len(g) else set()
    indian = {i for i in partners if i in inst.index and inst.at[i, "country_code"] == "IN"}
    countries = set().union(*g["countries"]) - {"IN"} if len(g) else set()
    return {
        "papers": len(g),
        "q1_papers": int(q1.sum()),
        "q1_if_gt5": int((q1 & (g["jif"] > 5)).sum()),
        "q1_if_gt10": int((q1 & (g["jif"] > 10)).sum()),
        "papers_with_if": int(g["jif"].notna().sum()),
        "papers_lt10_authors": int((g["n_authors"] < LARGE).sum()),
        "papers_ge10_authors": int((g["n_authors"] >= LARGE).sum()),
        "papers_ge30_authors": int((g["n_authors"] >= VERY_LARGE).sum()),
        "papers_100plus_authors": int(g["capped"].sum()),
        "mean_authors": round(float(g["n_authors"].mean()), 2) if len(g) else None,
        "collab_institutions": len(partners),
        "collab_institutions_indian": len(indian),
        "collab_institutions_foreign": len(partners) - len(indian),
        "collab_countries": len(countries),
        "intl_papers_pct": round(float(g["countries"].map(lambda c: bool(c - {"IN"})).mean() * 100), 2) if len(g) else None,
    }


def overview(p, labids, inst, fm) -> None:
    """phase2_overview.csv (per lab + combined) and phase2_overview_by_year.csv."""
    af = active_faculty(fm)
    rows, yrows = [], []
    for name, g in groups(p):
        own = labids[name] if name in labids else set().union(*labids.values())
        nf = int((af["lab"] == name).sum()) if name in LABS else len(af)
        rows.append({"institution": name, "active_faculty": nf, **overview_row(g, own, inst)})
        for y in range(2016, 2027):
            yrows.append({"institution": name, "year": y, **overview_row(g[g["year"] == y], own, inst)})
    pd.DataFrame(rows).to_csv(TABLES / "phase2_overview.csv", index=False)
    pd.DataFrame(yrows).to_csv(TABLES / "phase2_overview_by_year.csv", index=False)


# ---------------------------------------------------------------------------
def faculty_comparison(p, labids, fm, ext, FA, FC) -> pd.DataFrame:
    """phase2_faculty_comparison.csv: one row per active scientist; ranks and flags.

    Flags: 'large-collaboration papers' when >= 1 paper has >= 30 authors or >= 50% of the
    scientist's citations come from papers with >= 10 authors; 'profile also has papers at another
    lab' when the scientist's OpenAlex profile carries rows credited to another lab (those rows are
    not counted: the scientist moved labs, or two people share one profile)."""
    af = active_faculty(fm).set_index("faculty_id")
    fp = faculty_papers(ext, fm)
    by_lab = {lab: p[p["institution"] == lab].set_index("work_id") for lab in LABS}
    other_lab = ext[ext["faculty_id"].isin(af.index)].merge(af[["lab"]], left_on="faculty_id", right_index=True)
    other_lab = other_lab[other_lab["institution"] != other_lab["lab"]].groupby("faculty_id")["work_id"].nunique()
    in_w = dict(FC.in_degree(weight="weight"))
    rows = []
    for fid, g in fp.groupby("faculty_id"):
        lab = af.at[fid, "lab"]
        pp = by_lab[lab].loc[g["work_id"]]
        q1 = pp["quartile"] == "Q1"
        cites = pp["citations"]
        big = pp["n_authors"] >= LARGE
        partners = set().union(*pp["inst_ids"]) - labids[lab]
        share_big = float(cites[big].sum() / cites.sum() * 100) if cites.sum() else 0.0
        flags = []
        if (pp["n_authors"] >= VERY_LARGE).any() or share_big >= 50:
            flags.append("large-collaboration papers")
        if fid in other_lab.index:
            flags.append(f"{int(other_lab[fid])} paper(s) under the same profile at another lab (moved labs or merged "
                         f"profile; not counted)")
        rows.append({
            "faculty_id": fid, "name": af.at[fid, "full_name"], "institution": lab,
            "department": af.at[fid, "department"], "designation": af.at[fid, "designation"],
            "papers": len(pp), "q1_papers": int(q1.sum()), "q1_if_gt5": int((q1 & (pp["jif"] > 5)).sum()),
            "q1_if_gt10": int((q1 & (pp["jif"] > 10)).sum()), "citations": int(cites.sum()),
            "h_index": int(af.at[fid, "h_index_corpus"]),
            "faculty_coauthors": FA.degree(fid) if fid in FA else 0,
            "shared_papers_with_faculty": FA.degree(fid, weight="weight") if fid in FA else 0,
            "cited_by_faculty": in_w.get(fid, 0),
            "collab_institutions": len(partners),
            "intl_papers": int(pp["countries"].map(lambda c: bool(c - {"IN"})).sum()),
            "papers_ge10_authors": int(big.sum()), "max_authors": int(pp["n_authors"].max()),
            "citations_from_ge10_pct": round(share_big, 1),
            "flags": "; ".join(flags),
        })
    df = pd.DataFrame(rows)
    df["rank_productivity"] = df["papers"].rank(ascending=False, method="min").astype(int)
    df["rank_connectivity"] = df["faculty_coauthors"].rank(ascending=False, method="min").astype(int)
    df["rank_collab_institutions"] = df["collab_institutions"].rank(ascending=False, method="min").astype(int)
    df = df.sort_values(["rank_productivity", "faculty_id"])
    df.to_csv(TABLES / "phase2_faculty_comparison.csv", index=False)
    return df


def top_papers_by_if(p) -> None:
    """phase2_top30_by_if.csv (per lab + combined) and phase2_frequent_journals.csv (top 20)."""
    rows, jrows = [], []
    for name, g in groups(p):
        t = g[g["jif"].notna()].sort_values(["jif", "citations", "work_id"], ascending=[False, False, True]).head(30)
        for i, r in enumerate(t.itertuples(), 1):
            rows.append({"institution": name, "rank": i, "title": r.title, "journal_name": r.journal_name, "year": r.year,
                         "journal_if": r.jif, "quartile": r.quartile, "citations": r.citations, "labs": r.labs,
                         "n_authors": r.n_authors, "doi": r.doi})
        j = g[g["journal_name"] != ""].groupby("journal_name").agg(
            papers=("work_id", "size"), citations=("citations", "sum"), journal_if=("jif", "median"),
            quartile=("quartile", lambda s: s[s != ""].mode().iloc[0] if (s != "").any() else ""))
        j = j.sort_values(["papers", "citations"], ascending=False).head(20).reset_index()
        for i, r in enumerate(j.itertuples(), 1):
            jrows.append({"institution": name, "rank": i, "journal_name": r.journal_name, "papers": r.papers,
                          "share_pct": round(r.papers / len(g) * 100, 2), "journal_if": None if pd.isna(r.journal_if) else round(r.journal_if, 2),
                          "quartile": r.quartile, "citations": int(r.citations)})
    pd.DataFrame(rows).to_csv(TABLES / "phase2_top30_by_if.csv", index=False)
    pd.DataFrame(jrows).to_csv(TABLES / "phase2_frequent_journals.csv", index=False)


def faculty_top10_by_if(p, ext, fm) -> None:
    """phase2_faculty_top10_by_if.csv: each scientist's 10 papers in the highest-IF journals."""
    fp = faculty_papers(ext, fm)
    af = active_faculty(fm).set_index("faculty_id")
    by_lab = {lab: p[p["institution"] == lab].set_index("work_id") for lab in LABS}
    rows = []
    for fid, g in fp.groupby("faculty_id"):
        pp = by_lab[af.at[fid, "lab"]].loc[g["work_id"]].reset_index()
        pp = pp.sort_values(["jif", "citations", "work_id"], ascending=[False, False, True], na_position="last").head(10)
        for i, r in enumerate(pp.itertuples(), 1):
            rows.append({"faculty_id": fid, "rank": i, "title": r.title, "journal_name": r.journal_name, "year": r.year,
                         "journal_if": r.jif, "quartile": r.quartile, "citations": r.citations, "doi": r.doi})
    pd.DataFrame(rows).to_csv(TABLES / "phase2_faculty_top10_by_if.csv", index=False)


def large_author_papers(p) -> None:
    """phase2_large_author_papers.csv: papers with >= 30 authors (flagged; mostly consortium or
    multi-centre work whose citations do not reflect one lab's contribution)."""
    g = p.drop_duplicates("work_id")
    big = g[g["n_authors"] >= VERY_LARGE].sort_values(["n_authors", "citations"], ascending=False)
    big[["work_id", "title", "journal_name", "year", "labs", "n_authors", "capped", "citations", "doi"]].rename(
        columns={"capped": "authors_100_or_more"}).to_csv(TABLES / "phase2_large_author_papers.csv", index=False)


# ---------------------------------------------------------------------------
def institution_network(p, labids, inst) -> None:
    """phase2_institution_network_{nodes,edges}.csv: institutions that co-author the labs' papers.
    Nodes = the 3 labs + the 60 most frequent partner institutions; edge = both on >= 1 paper."""
    g = p.drop_duplicates("work_id")
    lab_ids = set().union(*labids.values())
    freq = Counter(i for s in g["inst_ids"] for i in s if i not in lab_ids)
    keep = lab_ids | {i for i, _ in freq.most_common(60)}
    G = nx.Graph()
    for s in g["inst_ids"]:
        ids = sorted(i for i in s if i in keep)
        for a in ids:
            G.add_node(a)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                G.add_edge(a, b, weight=G[a][b]["weight"] + 1 if G.has_edge(a, b) else 1)
    btw = nx.betweenness_centrality(G, weight=None)
    name_of_lab = {i: lab for lab, s in labids.items() for i in s}
    nodes = []
    for n in G.nodes:
        meta = inst.loc[n] if n in inst.index else None
        nodes.append({"institution_id": n, "name": name_of_lab.get(n, meta["display_name"] if meta is not None else n),
                      "country_code": meta["country_code"] if meta is not None else "IN",
                      "sector": "Assigned lab" if n in name_of_lab else (meta["sector"] if meta is not None else ""),
                      "papers_with_labs": int(sum(n in s for s in g["inst_ids"])), "degree": G.degree(n),
                      "betweenness": round(btw[n], 4)})
    pd.DataFrame(nodes).sort_values("papers_with_labs", ascending=False).to_csv(TABLES / "phase2_institution_network_nodes.csv", index=False)
    pd.DataFrame([{"source": a, "target": b, "papers": d["weight"]} for a, b, d in G.edges(data=True)]).sort_values(
        "papers", ascending=False).to_csv(TABLES / "phase2_institution_network_edges.csv", index=False)


def temporal(p, labids, inst, ext, fm) -> None:
    """phase2_temporal.csv: how output, collaboration and the faculty networks change by period."""
    fp = faculty_papers(ext, fm)
    year_of = dict(zip(p["work_id"], p["year"]))
    cite = incorpus_citation_edges(pd.read_csv(FINAL / "citation_network.csv", dtype=str, keep_default_na=False), corpus_dois(ext))
    lab_ids = set().union(*labids.values())
    rows = []
    for label, y0, y1 in PERIODS:
        g = p.drop_duplicates("work_id")
        g = g[(g["year"] >= y0) & (g["year"] <= y1)]
        fpp = fp[fp["work_id"].map(year_of).between(y0, y1)]
        FA = faculty_coauthor_graph(fpp, fm)
        FA.remove_nodes_from([n for n, d in list(FA.degree()) if d == 0])
        ce = cite[cite["year"].astype(int).between(y0, y1)]
        FC, _ = faculty_citation_graph(fp, ce, fm)  # citing paper in the period, cited paper any year
        FC.remove_nodes_from([n for n, d in list(FC.degree()) if d == 0])
        lab = dict(FA.nodes(data="lab"))
        partners = set().union(*g["inst_ids"]) - lab_ids if len(g) else set()
        lcc = max((len(c) for c in nx.connected_components(FA)), default=0)
        rows.append({
            "period": label, "papers": len(g), "mean_authors": round(float(g["n_authors"].mean()), 2),
            "papers_ge10_authors_pct": round(float((g["n_authors"] >= LARGE).mean() * 100), 2),
            "intl_papers_pct": round(float(g["countries"].map(lambda c: bool(c - {"IN"})).mean() * 100), 2),
            "collab_institutions": len(partners),
            "active_faculty": int(fpp["faculty_id"].nunique()),
            "faculty_coauthor_pairs": FA.number_of_edges(),
            "cross_lab_pairs": sum(1 for u, v in FA.edges if lab[u] != lab[v]),
            "faculty_network_density": round(nx.density(FA), 4) if FA.number_of_nodes() > 1 else 0.0,
            "largest_group_scientists": lcc,
            "faculty_citation_links": FC.number_of_edges(),
            "faculty_citations": int(FC.size(weight="weight")),
        })
    pd.DataFrame(rows).to_csv(TABLES / "phase2_temporal.csv", index=False)


# ---------------------------------------------------------------------------
def citing_institutions(inst, ext) -> None:
    """Who cites the labs, by sector, and why some non-governmental institutions cite so much.

    phase2_citing_sectors.csv: citing papers per sector (a paper with two sectors counts for each)
    phase2_citing_sectors_by_year.csv
    phase2_citing_institutions_diagnostics.csv: for the 25 Indian institutions with most citing
      papers, plus benchmark rows, the indicators below.

    Indicators (citing papers = Indian papers outside the corpus that cite >= 1 corpus paper):
    - refs_to_corpus_per_paper: corpus papers cited per citing paper
    - stacking_pct: share of citing papers that cite >= 5 corpus papers at once
    - shared_author_pct: share of citing papers that share >= 1 author with a corpus paper they cite
      (the citing authors cite their own earlier work with the labs)
    - lab_coauthor_pct: share of citing papers with an author who also appears on corpus papers
    - top_author_pct: share of the institution's citing papers that include its single most
      frequent author (concentration on one person)
    - recent_pct: share published 2023-2026
    """
    cw = pd.read_csv(FINAL / "citing_works.csv", dtype=str, keep_default_na=False)
    for c in ("year", "n_references", "n_references_to_corpus", "cited_by_count", "n_authors"):
        cw[c] = pd.to_numeric(cw[c], errors="coerce")
    cw["insts"] = cw["institution_ids"].map(split)
    cw["authors"] = cw["author_ids"].map(lambda s: set(split(s)))
    # authors of each cited corpus paper, via the citation edges (doi -> doi)
    wac = pd.read_csv(FINAL / "work_author_counts.csv", dtype=str, keep_default_na=False)
    doi_of = ext.drop_duplicates("work_id").set_index("work_id")["doi"]
    corpus_authors = {doi_of[w]: set(split(a)) for w, a in zip(wac["work_id"], wac["author_ids"]) if doi_of.get(w)}
    lab_people = set().union(*corpus_authors.values())
    cite = pd.read_csv(FINAL / "citation_network.csv", dtype=str, keep_default_na=False, usecols=["source_doi", "target_doi"])
    cite = cite[cite["target_doi"].isin(corpus_authors) & ~cite["source_doi"].isin(corpus_authors)].drop_duplicates()
    cited_by = cite.groupby("source_doi")["target_doi"].agg(list)
    cw["cited"] = cw["doi"].map(cited_by)
    cw["shared_author"] = [bool(a & set().union(*(corpus_authors.get(t, set()) for t in ts))) if isinstance(ts, list) else False
                           for a, ts in zip(cw["authors"], cw["cited"])]
    cw["lab_coauthor"] = cw["authors"].map(lambda a: bool(a & lab_people))
    sector_of = inst["sector"].to_dict()
    country_of = inst["country_code"].to_dict()
    cw["sectors"] = cw["insts"].map(lambda ids: {sector_of.get(i, "") for i in ids if country_of.get(i) == "IN"} - {""})

    rows = []
    for sec in sorted({s for ss in cw["sectors"] for s in ss}):
        g = cw[cw["sectors"].map(lambda ss: sec in ss)]
        rows.append({"sector": sec, "non_governmental": sec in NON_GOV, "citing_papers": len(g),
                     "citations_to_corpus": int(g["n_references_to_corpus"].sum())})
    sec = pd.DataFrame(rows).sort_values("citing_papers", ascending=False)
    sec["share_of_indian_citing_pct"] = (sec["citing_papers"] / cw["sectors"].map(bool).sum() * 100).round(2)
    sec.to_csv(TABLES / "phase2_citing_sectors.csv", index=False)
    yrows = []
    for y in range(2016, 2027):
        gy = cw[cw["year"] == y]
        n = int(gy["sectors"].map(bool).sum())
        ng = int(gy["sectors"].map(lambda ss: bool(ss & NON_GOV)).sum())
        yrows.append({"year": y, "indian_citing_papers": n, "non_governmental_citing_papers": ng,
                      "non_governmental_pct": round(ng / n * 100, 2) if n else None})
    pd.DataFrame(yrows).to_csv(TABLES / "phase2_citing_sectors_by_year.csv", index=False)

    def indicators(g: pd.DataFrame) -> Dict:
        top = Counter(a for s in g["authors"] for a in s).most_common(1)
        return {
            "citing_papers": len(g), "citations_to_corpus": int(g["n_references_to_corpus"].sum()),
            "refs_to_corpus_per_paper": round(float(g["n_references_to_corpus"].mean()), 2),
            "stacking_pct": round(float((g["n_references_to_corpus"] >= 5).mean() * 100), 2),
            "shared_author_pct": round(float(g["shared_author"].mean() * 100), 2),
            "lab_coauthor_pct": round(float(g["lab_coauthor"].mean() * 100), 2),
            "top_author_pct": round(top[0][1] / len(g) * 100, 2) if top else 0.0,
            "recent_pct": round(float((g["year"] >= 2023).mean() * 100), 2),
            "median_references": float(g["n_references"].median()),
            "median_citing_paper_citations": float(g["cited_by_count"].median()),
        }

    per_inst = defaultdict(list)
    for idx, ids in zip(cw.index, cw["insts"]):
        for i in set(ids):
            if country_of.get(i) == "IN":
                per_inst[i].append(idx)
    top = sorted(per_inst, key=lambda i: (-len(per_inst[i]), i))[:25]
    drows = [{"institution": inst.at[i, "display_name"], "sector": sector_of.get(i, ""),
              "non_governmental": sector_of.get(i, "") in NON_GOV, **indicators(cw.loc[per_inst[i]])} for i in top]
    bench = {
        "Benchmark: IITs, IISc, IISERs": cw["sectors"].map(lambda ss: bool(ss & {"IIT", "IISc", "IISER"})),
        "Benchmark: all government and public institutions": cw["sectors"].map(lambda ss: bool(ss) and not ss & NON_GOV),
        "Benchmark: all non-governmental (Private, Industry)": cw["sectors"].map(lambda ss: bool(ss & NON_GOV)),
        "Benchmark: all Indian citing papers": cw["sectors"].map(bool),
    }
    for label, m in bench.items():
        drows.append({"institution": label, "sector": "benchmark", "non_governmental": "", **indicators(cw[m])})
    pd.DataFrame(drows).to_csv(TABLES / "phase2_citing_institutions_diagnostics.csv", index=False)


def data_checks(ext, fm, p) -> None:
    """phase2_data_checks.csv: author-name and affiliation checks with their counts and handling."""
    af = active_faculty(fm)
    dup_names = af[af["full_name"].duplicated(keep=False)]
    lab_rows = ext[ext["author_openalex_id"] != ""]
    multi_id = lab_rows.groupby("author")["author_openalex_id"].nunique()
    other_lab = ext[ext["faculty_id"].isin(af["faculty_id"])].merge(af[["faculty_id", "lab"]], on="faculty_id")
    other_lab = other_lab[other_lab["institution"] != other_lab["lab"]]
    g = p.drop_duplicates("work_id")
    dups = pd.read_csv("data/review/duplicate_papers_removed.csv", dtype=str, keep_default_na=False)
    rows = [
        ("Two different scientists with the same name", len(dup_names) // 2 if len(dup_names) else 0,
         "; ".join(f"{r.full_name} ({r.lab})" for r in dup_names.itertuples()),
         "Kept as separate people (one faculty_id each) in all faculty tables and networks"),
        ("Lab author names that stand for > 1 OpenAlex author", int((multi_id > 1).sum()), "",
         "Faculty analyses use faculty_id, not names; the all-author network is labelled 'by name'"),
        ("Scientists whose OpenAlex profile also has papers at another lab", int(other_lab["faculty_id"].nunique()),
         f"{other_lab['work_id'].nunique()} papers", "Not counted for the scientist (possible merged profile)"),
        ("Author rows without an OpenAlex author ID", int((ext["author_openalex_id"] == "").sum()), "",
         "Kept in paper statistics; never counted as faculty"),
        ("Papers with >= 30 authors", int((g["n_authors"] >= VERY_LARGE).sum()), "", "Flagged (phase2_large_author_papers.csv)"),
        ("Papers listed with 100 authors (100 or more)", int(g["capped"].sum()), "", "Flagged; OpenAlex lists at most 100"),
        ("Duplicate or non-research records removed (Step 20)", len(dups), dups["reason"].value_counts().to_dict(),
         "Removed or merged into the kept record (data/review/duplicate_papers_removed.csv)"),
    ]
    pd.DataFrame(rows, columns=["check", "count", "detail", "handling"]).to_csv(TABLES / "phase2_data_checks.csv", index=False)


def run_phase2() -> None:
    logger.info("Phase II tables...")
    TABLES.mkdir(parents=True, exist_ok=True)
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv(FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    labids = lab_institution_ids()
    inst = sector_table()
    p = paper_table()
    fp = faculty_papers(ext, fm)
    cite = incorpus_citation_edges(pd.read_csv(FINAL / "citation_network.csv", dtype=str, keep_default_na=False), corpus_dois(ext))
    FA = faculty_coauthor_graph(fp, fm)
    FC, _ = faculty_citation_graph(fp, cite, fm)
    overview(p, labids, inst, fm)
    faculty_comparison(p, labids, fm, ext, FA, FC)
    top_papers_by_if(p)
    faculty_top10_by_if(p, ext, fm)
    large_author_papers(p)
    institution_network(p, labids, inst)
    temporal(p, labids, inst, ext, fm)
    citing_institutions(inst, ext)
    data_checks(ext, fm, p)
    logger.info("✓ Phase II tables written (stats/tables/phase2_*.csv)")


if __name__ == "__main__":
    run_phase2()
