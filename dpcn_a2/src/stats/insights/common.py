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
    """Distinct paper-level dataset (14,352 works).
    
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
    assert len(res) == 14352, f"Expected 14,352 distinct papers, got {len(res)}"
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


def coauthor_graph(max_authors: int = 30) -> nx.Graph:
    """Undirected networkx.Graph from authorship_network.csv.
    
    Drops hyper-authored papers (authors > max_authors).
    Attaches node attributes: name, lab, is_faculty.
    Returns Largest Connected Component (LCC).
    """
    auth_path = DATA_FINAL / "authorship_network.csv"
    if not auth_path.exists():
        raise FileNotFoundError(f"Missing {auth_path}")

    df_auth = pd.read_csv(auth_path, keep_default_na=False)
    # Identify and drop hyper-authored papers (across entire authorship network)
    doi_with_papers = df_auth[df_auth["paper_doi"] != ""]
    doi_authors = doi_with_papers.groupby("paper_doi").apply(
        lambda g: len(set(g["author_a"]).union(set(g["author_b"])))
    )
    dropped_dois = set(doi_authors[doi_authors > max_authors].index)
    logger.info(f"Dropped {len(dropped_dois)} hyper-authored papers with >{max_authors} authors")

    # Filter to within-cluster rows
    df_lab = df_auth[df_auth["inst_a"].isin(LABS) & df_auth["inst_b"].isin(LABS)].copy()
    df_filtered = df_lab[~df_lab["paper_doi"].isin(dropped_dois)].copy()

    # Load faculty definitions for attribute tagging
    df_fac = faculty()
    matched_fac = df_fac[df_fac["is_matched"]]
    faculty_names = set(matched_fac["name"]).union(set(matched_fac["name_norm"]))
    
    # Also load from group24_data_extended
    ext_path = DATA_FINAL / "group24_data_extended.csv"
    if ext_path.exists():
        df_ext = pd.read_csv(ext_path, usecols=["author", "author_role"], keep_default_na=False)
        ext_fac = set(df_ext[df_ext["author_role"] == "faculty"]["author"])
        faculty_names = faculty_names.union(ext_fac)

    # Build Graph
    G = nx.Graph()
    inst_of: Dict[str, str] = {}

    for a, b, ia, ib in df_filtered[["author_a", "author_b", "inst_a", "inst_b"]].itertuples(index=False):
        inst_of.setdefault(a, ia)
        inst_of.setdefault(b, ib)
        if G.has_edge(a, b):
            G[a][b]["weight"] += 1
        else:
            G.add_edge(a, b, weight=1)

    # Attach node attributes
    for node in G.nodes():
        G.nodes[node]["name"] = node
        G.nodes[node]["lab"] = inst_of.get(node, "external")
        G.nodes[node]["is_faculty"] = node in faculty_names

    logger.info(f"Full co-authorship graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if G.number_of_nodes() == 0:
        return G

    # Extract LCC
    lcc_nodes = max(nx.connected_components(G), key=len)
    # Build the LCC in G's insertion order: subgraph views can iterate in set order, which varies with
    # PYTHONHASHSEED and would change sampled betweenness and random-removal runs between executions
    LCC = nx.Graph()
    LCC.add_nodes_from((n, G.nodes[n]) for n in G if n in lcc_nodes)
    LCC.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if u in lcc_nodes)
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
    """Contract-conforming placeholder when an input (e.g. an API cache) is missing. Never invents numbers."""
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
