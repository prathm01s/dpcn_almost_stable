"""Indian connectivity metrics (instruction note Sections 7a and 7b).

Citation flow (7a) is measured on data/final/citation_network.csv: in-corpus edges
(both papers in the CSIR-NCL / CSIR-IICT / CSIR-CECRI corpus) plus edges to and from
DOI-bearing Indian-affiliated papers outside the corpus (Step 17). A citation counts
as coming from (or going to) another Indian institution when the citing (cited) paper
involves an Indian institution other than the institute in question. Institutions of
a corpus paper = assigned labs + coauthor_institutes; of an outside paper = the
";"-separated list in the edge's inst column. Metadata of outside papers comes from
data/final/indian_linked_works.csv.

Connectivity map (7b) uses data/final/indian_connections.csv and the sector
labels in config/indian_inst_registry.csv.

Outputs (stats/tables/):
- citation_flow_summary.csv        in/out flow and impact ratio per institute
- citation_flow_by_year.csv        year-wise flow (by citing-paper year)
- top_citing_indian_institutes.csv top 10 Indian institutes citing each institute
- top_papers_citing_institute.csv  top 10 most-cited corpus papers citing each institute
- cross_cluster_links.csv          every partner link with sector and cross-cluster flag
- cross_cluster_summary.csv        partners / shared papers per partner sector
- topic_jaccard.csv                Jaccard topic similarity between the three institutes
- partner_topic_jaccard.csv        Jaccard topic similarity, institute vs top partners
- hub_authors.csv                  authors bridging the most institutions
"""

import collections
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd

from src.common.logging import get_logger
from src.common.sectors import assign_sector_cluster

logger = get_logger("stats_connectivity")

INSTITUTES = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
COMBINED = "Group 24 Combined"
HOME_SECTOR = "CSIR"
TABLES_DIR = Path("stats/tables")


def _split(s: str) -> List[str]:
    return [p.strip() for p in s.split(";") if p.strip()]


def _load():
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    df_cite = pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
    df_conn = pd.read_csv("data/final/indian_connections.csv", keep_default_na=False)
    registry = pd.read_csv("config/indian_inst_registry.csv", dtype=str, keep_default_na=False)
    linked_path = Path("data/final/indian_linked_works.csv")
    linked = (pd.read_csv(linked_path, dtype=str, keep_default_na=False) if linked_path.exists()
              else pd.DataFrame(columns=["work_id", "doi", "title", "year", "cited_by_count", "indian_institutions"]))
    return df_ext, df_cite, df_conn, registry, linked


def _paper_table(df_ext: pd.DataFrame) -> pd.DataFrame:
    """One row per work: doi, title, year, citations, assigned labs, all Indian institutions."""
    rows = {}
    for r in df_ext.itertuples(index=False):
        p = rows.setdefault(r.work_id, {
            "work_id": r.work_id, "doi": r.doi, "title": r.title, "year": int(r.year),
            "citations": int(r.citations), "journal_name": r.journal_name,
            "labs": set(), "insts": set(),
        })
        p["labs"].add(r.institution)
        p["insts"].add(r.institution)
        p["insts"].update(_split(r.coauthor_institutes))
    return pd.DataFrame(rows.values())


def _paper_meta(papers: pd.DataFrame, linked: pd.DataFrame) -> pd.DataFrame:
    """DOI -> title/journal/year/citations/institutions for corpus and outside papers."""
    corpus = papers[papers["doi"] != ""].drop_duplicates("doi").set_index("doi")
    corpus = corpus[["title", "journal_name", "year", "citations", "insts"]].assign(in_corpus=True)
    out = linked[(linked["doi"] != "") & ~linked["doi"].isin(corpus.index)].drop_duplicates("doi")
    out = pd.DataFrame({
        "title": out["title"].values,
        "journal_name": "",
        "year": pd.to_numeric(out["year"], errors="coerce").fillna(0).astype(int).values,
        "citations": pd.to_numeric(out["cited_by_count"], errors="coerce").fillna(0).astype(int).values,
        "insts": [set(_split(i)) for i in out["indian_institutions"]],
        "in_corpus": False,
    }, index=out["doi"].values)
    return pd.concat([corpus, out])


def _flow_edges(df_cite: pd.DataFrame, papers: pd.DataFrame) -> pd.DataFrame:
    """Citation edges with citing/cited institutions and in/out Indian flags.

    in_indian:  the cited paper is ours (target_inst is a lab) and the citing paper involves
                an Indian institution other than target_inst.
    out_indian: the citing paper is ours and the cited paper involves another Indian institution.
    """
    by_doi = papers[papers["doi"] != ""].drop_duplicates("doi").set_index("doi")
    e = df_cite.copy()
    e["year"] = pd.to_numeric(e["year"]).astype(int)
    e["src_in"] = e["source_doi"].isin(by_doi.index)
    e["tgt_in"] = e["target_doi"].isin(by_doi.index)
    e = e[e["src_in"] | e["tgt_in"]].copy()
    e["src_insts"] = [by_doi.at[d, "insts"] if i else set(_split(x))
                      for d, i, x in zip(e["source_doi"], e["src_in"], e["source_inst"])]
    e["tgt_insts"] = [by_doi.at[d, "insts"] if i else set(_split(x))
                      for d, i, x in zip(e["target_doi"], e["tgt_in"], e["target_inst"])]
    e["in_indian"] = e["tgt_in"] & pd.Series(
        [any(i != t for i in s) for s, t in zip(e["src_insts"], e["target_inst"])], index=e.index)
    e["out_indian"] = e["src_in"] & pd.Series(
        [any(i != s for i in t) for t, s in zip(e["tgt_insts"], e["source_inst"])], index=e.index)
    e["cross_lab"] = e["src_in"] & e["tgt_in"] & (e["source_inst"] != e["target_inst"])
    e["outside"] = ~(e["src_in"] & e["tgt_in"])
    return e


def citation_flow(edges: pd.DataFrame, meta: pd.DataFrame) -> None:
    summary, yearly, top_inst, top_papers = [], [], [], []

    for inst in INSTITUTES:
        inn = edges[edges["tgt_in"] & (edges["target_inst"] == inst) & edges["in_indian"]]
        out = edges[edges["src_in"] & (edges["source_inst"] == inst) & edges["out_indian"]]
        in_lab = edges[(edges["target_inst"] == inst) & edges["cross_lab"]]
        out_lab = edges[(edges["source_inst"] == inst) & edges["cross_lab"]]
        summary.append({
            "institution": inst,
            "in_citations_indian": len(inn),
            "out_citations_indian": len(out),
            "impact_ratio_indian": round(len(inn) / len(out), 3) if len(out) else None,
            "in_citations_other_assigned_labs": len(in_lab),
            "out_citations_other_assigned_labs": len(out_lab),
            "impact_ratio_other_assigned_labs": round(len(in_lab) / len(out_lab), 3) if len(out_lab) else None,
            "distinct_citing_institutions": len(set().union(*inn["src_insts"]) - {inst}) if len(inn) else 0,
            "in_citations_from_outside_corpus": int(inn["outside"].sum()),
            "out_citations_to_outside_corpus": int(out["outside"].sum()),
        })

        for y in range(2016, 2027):
            yearly.append({
                "institution": inst,
                "year": y,
                "in_citations_indian": int((inn["year"] == y).sum()),
                "out_citations_indian": int((out["year"] == y).sum()),
                "in_citations_other_assigned_labs": int((in_lab["year"] == y).sum()),
                "out_citations_other_assigned_labs": int((out_lab["year"] == y).sum()),
            })

        # Top citing institutions: distinct citing papers per institution
        citing_works: Dict[str, Set[str]] = collections.defaultdict(set)
        citing_edges: collections.Counter = collections.Counter()
        for w, insts in zip(inn["source_doi"], inn["src_insts"]):
            for i in insts - {inst}:
                citing_works[i].add(w)
                citing_edges[i] += 1
        ranked = sorted(citing_works, key=lambda i: (-len(citing_works[i]), -citing_edges[i], i))[:10]
        for rank, i in enumerate(ranked, 1):
            top_inst.append({
                "institution": inst, "rank": rank, "citing_institution": i,
                "citing_papers": len(citing_works[i]), "citations": citing_edges[i],
            })

        # Most-cited papers (corpus or outside) citing this institute from another Indian institution
        works = meta.loc[sorted(set(inn["source_doi"]))].sort_values(["citations", "title"], ascending=[False, True]).head(10)
        for rank, (doi, p) in enumerate(works.iterrows(), 1):
            top_papers.append({
                "institution": inst, "rank": rank, "title": p["title"], "journal_name": p["journal_name"],
                "year": p["year"], "citations": p["citations"], "doi": doi,
                "citing_institutions": "; ".join(sorted(p["insts"] - {inst})),
            })

    # Combined: citing papers involving an Indian institution outside the three labs,
    # counted once per (citing, cited) paper pair.
    labs = set(INSTITUTES)
    pairs = edges[edges["tgt_in"]].drop_duplicates(["source_doi", "target_doi"])
    pairs = pairs[[bool(s - labs) for s in pairs["src_insts"]]]
    citing_works = collections.defaultdict(set)
    citing_edges = collections.Counter()
    for w, insts in zip(pairs["source_doi"], pairs["src_insts"]):
        for i in insts - labs:
            citing_works[i].add(w)
            citing_edges[i] += 1
    ranked = sorted(citing_works, key=lambda i: (-len(citing_works[i]), -citing_edges[i], i))[:10]
    for rank, i in enumerate(ranked, 1):
        top_inst.append({
            "institution": COMBINED, "rank": rank, "citing_institution": i,
            "citing_papers": len(citing_works[i]), "citations": citing_edges[i],
        })
    works = meta.loc[sorted(set(pairs["source_doi"]))].sort_values(["citations", "title"], ascending=[False, True]).head(10)
    for rank, (doi, p) in enumerate(works.iterrows(), 1):
        top_papers.append({
            "institution": COMBINED, "rank": rank, "title": p["title"], "journal_name": p["journal_name"],
            "year": p["year"], "citations": p["citations"], "doi": doi,
            "citing_institutions": "; ".join(sorted(p["insts"] - labs)),
        })

    total_in = sum(r["in_citations_indian"] for r in summary)
    total_out = sum(r["out_citations_indian"] for r in summary)
    summary.append({
        "institution": COMBINED,
        "in_citations_indian": total_in,
        "out_citations_indian": total_out,
        "impact_ratio_indian": round(total_in / total_out, 3) if total_out else None,
        # Flows between the three labs are internal to the cluster, so not meaningful combined
        "in_citations_other_assigned_labs": None,
        "out_citations_other_assigned_labs": None,
        "impact_ratio_other_assigned_labs": None,
        "distinct_citing_institutions": None,
        "in_citations_from_outside_corpus": sum(r["in_citations_from_outside_corpus"] for r in summary),
        "out_citations_to_outside_corpus": sum(r["out_citations_to_outside_corpus"] for r in summary),
    })

    df_summary = pd.DataFrame(summary)
    count_cols = [c for c in df_summary.columns if c.startswith(("in_", "out_", "distinct_"))]
    df_summary[count_cols] = df_summary[count_cols].astype("Int64")
    df_summary.to_csv(TABLES_DIR / "citation_flow_summary.csv", index=False)
    pd.DataFrame(yearly).to_csv(TABLES_DIR / "citation_flow_by_year.csv", index=False)
    pd.DataFrame(top_inst).to_csv(TABLES_DIR / "top_citing_indian_institutes.csv", index=False)
    pd.DataFrame(top_papers).to_csv(TABLES_DIR / "top_papers_citing_institute.csv", index=False)


def cross_cluster(df_conn: pd.DataFrame, registry: pd.DataFrame) -> None:
    sector_of = dict(zip(registry["canonical_name"], registry["sector_cluster"]))
    links = df_conn.copy()
    links["partner_sector"] = [sector_of.get(p) or assign_sector_cluster(p) for p in links["partner_inst"]]
    links["link_type"] = HOME_SECTOR + " <-> " + links["partner_sector"]
    links["is_cross_cluster"] = (links["partner_sector"] != HOME_SECTOR).map({True: "TRUE", False: "FALSE"})
    links = links.sort_values(["your_inst", "shared_papers"], ascending=[True, False])
    links.to_csv(TABLES_DIR / "cross_cluster_links.csv", index=False)

    rows = []
    for inst in INSTITUTES + [COMBINED]:
        sub = links if inst == COMBINED else links[links["your_inst"] == inst]
        for sector, g in sub.groupby("partner_sector"):
            rows.append({
                "institution": inst,
                "partner_sector": sector,
                "link_type": f"{HOME_SECTOR} <-> {sector}",
                "is_cross_cluster": "TRUE" if sector != HOME_SECTOR else "FALSE",
                "partner_institutions": g["partner_inst"].nunique(),
                "shared_papers": int(g["shared_papers"].sum()),
                "total_citations": int(g["total_citations"].sum()),
            })
    df = pd.DataFrame(rows).sort_values(["institution", "shared_papers"], ascending=[True, False])
    df.to_csv(TABLES_DIR / "cross_cluster_summary.csv", index=False)


def _jaccard(a: Set[str], b: Set[str]) -> float:
    return round(len(a & b) / len(a | b), 4) if a | b else 0.0


def topic_similarity(df_ext: pd.DataFrame, df_conn: pd.DataFrame) -> None:
    papers = df_ext.drop_duplicates(["institution", "work_id"])
    levels = {"subfield": "subfield", "topic": "primary_topic"}

    rows = []
    for level, col in levels.items():
        topics = {i: set(papers.loc[papers["institution"] == i, col]) - {""} for i in INSTITUTES}
        for a, b in combinations(INSTITUTES, 2):
            rows.append({
                "institution_a": a, "institution_b": b, "level": level,
                "topics_a": len(topics[a]), "topics_b": len(topics[b]),
                "shared_topics": len(topics[a] & topics[b]),
                "jaccard": _jaccard(topics[a], topics[b]),
            })
    pd.DataFrame(rows).to_csv(TABLES_DIR / "topic_jaccard.csv", index=False)

    # Partner topic profile = topics of all corpus papers co-authored with that partner.
    # Partners' own full publication lists are not collected, so this is the topic
    # footprint of the partnership as seen from the cluster corpus.
    partner_topics: Dict[str, Set[str]] = collections.defaultdict(set)
    for coauth, topic in zip(df_ext["coauthor_institutes"], df_ext["primary_topic"]):
        if topic:
            for p in _split(coauth):
                partner_topics[p].add(topic)

    rows = []
    for inst in INSTITUTES:
        inst_topics = set(papers.loc[papers["institution"] == inst, "primary_topic"]) - {""}
        top = df_conn[df_conn["your_inst"] == inst].nlargest(10, "shared_papers")
        for rank, p in enumerate(top.itertuples(index=False), 1):
            pt = partner_topics.get(p.partner_inst, set())
            rows.append({
                "institution": inst, "rank": rank, "partner_institution": p.partner_inst,
                "shared_papers": p.shared_papers, "institute_topics": len(inst_topics),
                "partner_topics_in_corpus": len(pt), "shared_topics": len(inst_topics & pt),
                "jaccard": _jaccard(inst_topics, pt),
            })
    pd.DataFrame(rows).to_csv(TABLES_DIR / "partner_topic_jaccard.csv", index=False)


def hub_authors(df_ext: pd.DataFrame, top_n: int = 25) -> None:
    """Authors whose papers connect the most distinct institutions."""
    ext = df_ext[df_ext["author_openalex_id"] != ""]
    labs_of_work = df_ext.groupby("work_id")["institution"].agg(set)

    rows = []
    for aid, g in ext.groupby("author_openalex_id"):
        home = g["institution"].mode().iloc[0]
        partners = set().union(*(set(_split(c)) for c in g["coauthor_institutes"]))
        other_labs = set().union(*(labs_of_work[w] for w in g["work_id"].unique())) - set(g["institution"])
        rows.append({
            "author": g["author"].mode().iloc[0],
            "author_openalex_id": aid,
            "home_institution": home,
            "author_role": g["author_role"].mode().iloc[0],
            "department": g["department"].mode().iloc[0],
            "papers": g["work_id"].nunique(),
            "partner_institutions": len(partners),
            "other_assigned_labs": len(other_labs),
            "institutions_bridged": len(partners) + len(other_labs),
            "cross_institution_papers": int((g["coauthor_institutes"] != "").groupby(g["work_id"]).any().sum()),
            "top_partners": "; ".join(
                p for p, _ in collections.Counter(
                    p for c in g["coauthor_institutes"] for p in _split(c)
                ).most_common(5)
            ),
        })
    df = pd.DataFrame(rows).sort_values(["institutions_bridged", "cross_institution_papers"], ascending=False)
    out = pd.concat([df.head(top_n).assign(scope=COMBINED)] + [
        df[df["home_institution"] == i].head(10).assign(scope=i) for i in INSTITUTES
    ])
    out.insert(0, "rank", out.groupby("scope").cumcount() + 1)
    out = out[["scope", "rank"] + [c for c in out.columns if c not in ("scope", "rank")]]
    out.to_csv(TABLES_DIR / "hub_authors.csv", index=False)


def run_connectivity_metrics() -> None:
    logger.info("Computing Indian connectivity metrics (Sections 7a/7b)...")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df_ext, df_cite, df_conn, registry, linked = _load()

    papers = _paper_table(df_ext)
    edges = _flow_edges(df_cite, papers)
    citation_flow(edges, _paper_meta(papers, linked))
    cross_cluster(df_conn, registry)
    topic_similarity(df_ext, df_conn)
    hub_authors(df_ext)
    logger.info("✓ Saved 9 connectivity tables to stats/tables/")


if __name__ == "__main__":
    run_connectivity_metrics()
