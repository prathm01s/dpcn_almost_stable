"""Shared building blocks for Group 24 Insights analyses.

Provides distinct paper tables, faculty master access, network builders,
and standard output JSON serialization adhering to the implementation contract.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import networkx as nx
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("insights_common")

SEED = 24
LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
INST_KEY_TO_LAB = {
    "iict": "CSIR-IICT",
    "ncl": "CSIR-NCL",
    "cecri": "CSIR-CECRI",
}

DATA_FINAL = Path("data/final")
INSIGHTS_TABLES_DIR = Path("stats/tables/insights")
INSIGHTS_TABLES_DIR.mkdir(parents=True, exist_ok=True)


def papers() -> pd.DataFrame:
    """Distinct paper-level dataset (one row per work_id in group24_data_extended.csv).
    
    Returns one row per distinct work_id with columns:
    work_id, doi, year, labs, type, journal, quartile, citations, subfield, n_authors
    """
    ext_path = DATA_FINAL / "group24_data_extended.csv"
    if not ext_path.exists():
        raise FileNotFoundError(f"Missing {ext_path}")

    df_ext = pd.read_csv(ext_path, keep_default_na=False)

    # Group institutions and authors per work_id
    grouped = df_ext.groupby("work_id")
    labs_series = grouped["institution"].agg(lambda s: "; ".join(sorted(set(s))))
    n_authors_series = grouped["author"].nunique()

    # Deduplicate to distinct papers
    df_papers = df_ext.drop_duplicates(subset=["work_id"]).copy()
    df_papers["labs"] = df_papers["work_id"].map(labs_series)
    df_papers["n_authors"] = df_papers["work_id"].map(n_authors_series)
    df_papers["journal"] = df_papers["journal_name"]
    df_papers["year"] = pd.to_numeric(df_papers["year"], errors="coerce").fillna(0).astype(int)
    df_papers["citations"] = pd.to_numeric(df_papers["citations"], errors="coerce").fillna(0).astype(int)

    keep_cols = [
        "work_id", "doi", "year", "labs", "type", "journal",
        "quartile", "citations", "subfield", "n_authors"
    ]
    res = df_papers[keep_cols].reset_index(drop=True)
    assert len(res) == df_ext["work_id"].nunique() and res["work_id"].is_unique
    return res


def faculty() -> pd.DataFrame:
    """Roster scientists from faculty_master.csv.
    
    Columns: author_id, name, lab, division, openalex_author_id, is_matched, match_confidence
    """
    fm_path = DATA_FINAL / "faculty_master.csv"
    if not fm_path.exists():
        raise FileNotFoundError(f"Missing {fm_path}")

    df_fm = pd.read_csv(fm_path, keep_default_na=False)
    df_res = pd.DataFrame({
        "author_id": df_fm["faculty_id"],
        "name": df_fm["full_name"],
        "name_norm": df_fm["name_norm"],
        "lab": df_fm["inst_key"].map(INST_KEY_TO_LAB).fillna(df_fm["inst_key"]),
        "division": df_fm["department"],
        "openalex_author_id": df_fm["author_id"],
        "is_matched": df_fm["is_matched"].astype(str).str.lower() == "true",
        "match_confidence": df_fm["match_confidence"],
    })
    return df_res


def ordered_subgraph(G: nx.Graph, nodes) -> nx.Graph:
    """Induced subgraph built in G's insertion order.

    G.subgraph() views iterate in set order, which varies with PYTHONHASHSEED and would change
    sampled betweenness, removal runs and simulations between executions.
    """
    keep = set(nodes)
    H = nx.Graph()
    H.add_nodes_from((n, G.nodes[n]) for n in G if n in keep)
    H.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if u in keep and v in keep)
    return H


def author_key(df: pd.DataFrame) -> pd.Series:
    """One identity per person: the faculty_id of a roster scientist or flagged former member (which
    joins OpenAlex profiles split over one person, D-41), else the OpenAlex author ID, else the name.

    faculty_id is used only on rows with an author ID: Step 07 once gave all ID-less rows one
    FORMER_ id (FORMER_CECRI_0005, 936 different names; cleared by Step 20).
    """
    key = df["author_openalex_id"].where(df["author_openalex_id"] != "", "name:" + df["author"])
    if "faculty_id" in df.columns:
        person = (df["faculty_id"] != "") & (df["author_openalex_id"] != "")
        key = key.where(~person, df["faculty_id"])
    return key


def coauthor_graph(max_authors: int = 30) -> nx.Graph:
    """Undirected co-authorship graph of the three labs' authors, one node per person (author_key).

    Built from group24_data_extended.csv (one row per paper x lab author), so a person with
    several spellings is one node and two people with the same name stay apart. Edge weight =
    joint papers. Papers with > max_authors listed authors (lab authors plus Indian partner
    co-authors in authorship_network.csv) are dropped.
    Node attributes: name (most frequent spelling), lab (roster lab for faculty, else most
    frequent lab), is_faculty (roster scientist), faculty_id.
    Returns the largest connected component (LCC).
    """
    auth_path = DATA_FINAL / "authorship_network.csv"
    ext_path = DATA_FINAL / "group24_data_extended.csv"
    for p in (auth_path, ext_path):
        if not p.exists():
            raise FileNotFoundError(f"Missing {p}")

    df_auth = pd.read_csv(auth_path, keep_default_na=False)
    doi_with_papers = df_auth[df_auth["paper_doi"] != ""]
    doi_authors = (pd.concat([doi_with_papers[["paper_doi", "author_a"]].rename(columns={"author_a": "a"}),
                              doi_with_papers[["paper_doi", "author_b"]].rename(columns={"author_b": "a"})])
                   .groupby("paper_doi")["a"].nunique())
    dropped_dois = set(doi_authors[doi_authors > max_authors].index)

    df_ext = pd.read_csv(ext_path, dtype=str, keep_default_na=False,
                         usecols=["work_id", "doi", "author", "institution", "author_openalex_id", "faculty_id"])
    df_ext["key"] = author_key(df_ext)
    dropped = df_ext["doi"].isin(dropped_dois)
    logger.info(f"Dropped {df_ext.loc[dropped, 'work_id'].nunique()} hyper-authored papers with >{max_authors} authors")
    df_ext = df_ext[~dropped].sort_values(["work_id", "key"], kind="stable")

    def modal(s: pd.Series) -> str:
        return sorted(s.value_counts().items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    name_of = df_ext.groupby("key")["author"].agg(modal)
    lab_of = df_ext.groupby("key")["institution"].agg(modal)
    fac = faculty()
    roster = dict(zip(fac["author_id"], fac["lab"]))
    fid_of = df_ext[df_ext["faculty_id"].isin(roster) & (df_ext["key"] == df_ext["faculty_id"])].groupby("key")["faculty_id"].first()

    G = nx.Graph()
    for _, keys in df_ext.groupby("work_id", sort=True)["key"]:
        authors = sorted(set(keys))
        for i, a in enumerate(authors):
            for b in authors[i + 1:]:
                if G.has_edge(a, b):
                    G[a][b]["weight"] += 1
                else:
                    G.add_edge(a, b, weight=1)

    for node in G.nodes():
        fid = fid_of.get(node)
        G.nodes[node]["name"] = name_of[node]
        G.nodes[node]["lab"] = roster[fid] if fid else lab_of[node]
        G.nodes[node]["is_faculty"] = fid is not None
        G.nodes[node]["faculty_id"] = fid or ""

    logger.info(f"Full co-authorship graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if G.number_of_nodes() == 0:
        return G

    lcc_nodes = max(nx.connected_components(G), key=len)
    LCC = ordered_subgraph(G, lcc_nodes)
    lcc_share = len(lcc_nodes) / G.number_of_nodes() * 100
    logger.info(f"Co-authorship LCC: {LCC.number_of_nodes()} nodes ({lcc_share:.1f}% of graph), {LCC.number_of_edges()} edges")

    return LCC


def citation_graph() -> nx.DiGraph:
    """Directed DiGraph from citation_network.csv (source cites target).
    
    Restricted to in-corpus edges between papers in Group 24 corpus.
    """
    cite_path = DATA_FINAL / "citation_network.csv"
    if not cite_path.exists():
        raise FileNotFoundError(f"Missing {cite_path}")

    df_cite = pd.read_csv(cite_path, keep_default_na=False)
    p_df = papers()
    corpus_dois = set(p_df["doi"]) - {""}

    # Filter to in-corpus edges
    in_corpus = df_cite[
        df_cite["source_doi"].isin(corpus_dois) & df_cite["target_doi"].isin(corpus_dois)
    ].copy()

    # Paper metadata lookup by DOI
    meta_lookup = p_df.drop_duplicates(subset=["doi"]).set_index("doi").to_dict(orient="index")

    G = nx.DiGraph()
    for s_doi, t_doi in in_corpus[["source_doi", "target_doi"]].itertuples(index=False):
        G.add_edge(s_doi, t_doi)

    for node in G.nodes():
        meta = meta_lookup.get(node, {})
        G.nodes[node]["doi"] = node
        G.nodes[node]["journal"] = meta.get("journal", "")
        G.nodes[node]["year"] = meta.get("year", 0)
        G.nodes[node]["lab"] = meta.get("labs", "")
        G.nodes[node]["citations"] = meta.get("citations", 0)
        G.nodes[node]["subfield"] = meta.get("subfield", "")

    logger.info(f"In-corpus citation graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def not_computed(insight_id: str, question: str, reason: str) -> Dict[str, Any]:
    """Contract-conforming placeholder when an input (e.g. an API cache) is missing. Never invents numbers.

    An existing computed result is kept, so running `make insights` on a machine without the cache does not
    wipe results computed elsewhere; it is only stale if the code changed since (rerun with the cache then).
    """
    out_file = INSIGHTS_TABLES_DIR / f"{insight_id}.json"
    if out_file.exists():
        existing = json.loads(out_file.read_text(encoding="utf-8"))
        if existing.get("metrics", {}).get("status") != "not computed":
            logger.warning(f"{insight_id}: {reason}; keeping the previously computed {out_file} "
                           f"(computed_at {existing.get('computed_at')})")
            return existing
    data = {
        "id": insight_id,
        "question": question,
        "headline": f"Not computed – {reason}",
        "metrics": {"status": "not computed", "reason": reason},
        "chart": {"type": "none", "data": {}},
        "method_note": f"Not computed: {reason}",
    }
    save_insight(data)
    return data


def save_insight(data: Dict[str, Any]) -> Path:
    """Save insight JSON matching contract.
    
    Contract keys: id, question, headline, metrics, chart, method_note, computed_at
    """
    req_keys = ["id", "question", "headline", "metrics", "chart", "method_note"]
    for k in req_keys:
        if k not in data:
            raise ValueError(f"Insight missing required contract key '{k}'")

    if "computed_at" not in data or not data["computed_at"]:
        data["computed_at"] = datetime.now(timezone.utc).isoformat()

    out_file = INSIGHTS_TABLES_DIR / f"{data['id']}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"✓ Saved insight: {out_file}")
    return out_file
