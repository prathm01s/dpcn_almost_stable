"""Citation and authorship network analysis (Task 4, instruction note Section 6).

Analysis stays within the assigned institutions, as the note requires:
- citation network: edges of data/final/citation_network.csv whose two papers are both
  in the NCL/IICT/CECRI corpus (edges to outside Indian papers are raw data only)
- authorship network: edges of data/final/authorship_network.csv between two authors of
  the three labs (edges to Indian partner co-authors are raw data only)

The dashboard (src/dashboard/build_data.py) builds its graphs with the same functions, so
report and dashboard numbers agree.

Outputs (stats/tables/):
- network_summary.csv                    headline metrics of both networks
- network_citation_pagerank_top10.csv    most influential papers by PageRank
- network_citation_indegree_distribution.csv  corpus papers by in-corpus in-degree
- network_citation_flow_matrix.csv       citations between the three labs
- network_authorship_top_degree.csv      most collaborative authors (degree centrality)
- network_authorship_top_betweenness.csv authors bridging clusters (betweenness)
- network_authorship_communities.csv     largest Louvain communities
- network_authorship_collab_matrix.csv   co-authorship links between the three labs
"""

import collections
from pathlib import Path
from typing import Dict, List, Set, Tuple

import networkx as nx
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("stats_networks")

LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
TABLES_DIR = Path("stats/tables")
SEED = 42
BETWEENNESS_SAMPLE = 1000  # source nodes sampled for betweenness (exact is O(nm))


def corpus_dois(df_ext: pd.DataFrame) -> Set[str]:
    return set(df_ext["doi"]) - {""}


def incorpus_citation_edges(df_cite: pd.DataFrame, dois: Set[str]) -> pd.DataFrame:
    """Edges whose citing and cited papers are both in the corpus."""
    return df_cite[df_cite["source_doi"].isin(dois) & df_cite["target_doi"].isin(dois)].reset_index(drop=True)


def lab_authorship_edges(df_auth: pd.DataFrame) -> pd.DataFrame:
    """Co-authorship edges between two authors of the assigned labs."""
    return df_auth[df_auth["inst_a"].isin(LABS) & df_auth["inst_b"].isin(LABS)].reset_index(drop=True)


def citation_graph(edges: pd.DataFrame) -> Tuple[nx.DiGraph, Dict[str, float], Dict[str, int]]:
    G = nx.DiGraph()
    for s, t, si, ti, y in edges[["source_doi", "target_doi", "source_inst", "target_inst", "year"]].itertuples(index=False):
        G.add_edge(s, t, s_inst=si, t_inst=ti, yr=int(y))
    pr = nx.pagerank(G, max_iter=100)
    return G, pr, dict(G.in_degree())


def authorship_graph(edges: pd.DataFrame):
    """Undirected weighted graph (weight = number of joint papers) plus centralities.

    degree       = distinct co-authors; degree_centrality = degree / (n - 1)
    strength     = joint-paper links (weighted degree)
    betweenness  = unweighted shortest paths, estimated from BETWEENNESS_SAMPLE sources
    communities  = Louvain on joint-paper weights
    """
    G = nx.Graph()
    inst_of: Dict[str, str] = {}
    for a, b, ia, ib in edges[["author_a", "author_b", "inst_a", "inst_b"]].itertuples(index=False):
        inst_of.setdefault(a, ia)
        inst_of.setdefault(b, ib)
        if G.has_edge(a, b):
            G[a][b]["weight"] += 1
        else:
            G.add_edge(a, b, weight=1)
    degree = dict(G.degree())
    strength = dict(G.degree(weight="weight"))
    dc = nx.degree_centrality(G)
    comms = nx.community.louvain_communities(G, weight="weight", seed=SEED)
    comms = sorted(comms, key=lambda c: (-len(c), min(c)))
    comm_of = {n: i for i, c in enumerate(comms) for n in c}
    k = min(BETWEENNESS_SAMPLE, G.number_of_nodes())
    btw = nx.betweenness_centrality(G, k=k, seed=SEED)
    return {
        "G": G, "inst_of": inst_of, "degree": degree, "strength": strength, "degree_centrality": dc,
        "communities": comms, "comm_of": comm_of, "betweenness": btw,
        "modularity": nx.community.modularity(G, comms, weight="weight"),
    }


def _paper_lookup(df_ext: pd.DataFrame) -> pd.DataFrame:
    p = df_ext[df_ext["doi"] != ""].copy()
    labs = p.groupby("doi")["institution"].agg(lambda s: "; ".join(sorted(set(s))))
    p = p.drop_duplicates("doi").set_index("doi")
    p["labs"] = labs
    return p


def run_network_metrics() -> None:
    logger.info("Computing citation and authorship network metrics...")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    df_cite = pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
    df_auth = pd.read_csv("data/final/authorship_network.csv", dtype=str, keep_default_na=False)
    dois = corpus_dois(df_ext)
    papers = _paper_lookup(df_ext)

    # ---- Citation network
    ce = incorpus_citation_edges(df_cite, dois)
    Gc, pr, indeg = citation_graph(ce)
    pairs = ce.drop_duplicates(["source_doi", "target_doi"])

    top = sorted(pr.items(), key=lambda x: (-x[1], x[0]))[:10]
    pd.DataFrame([{
        "rank": r, "doi": d, "title": papers.at[d, "title"], "journal_name": papers.at[d, "journal_name"],
        "year": int(papers.at[d, "year"]), "institutions": papers.at[d, "labs"],
        "in_degree_corpus": indeg.get(d, 0), "citations_openalex": int(papers.at[d, "citations"]),
        "pagerank": round(s, 6),
    } for r, (d, s) in enumerate(top, 1)]).to_csv(TABLES_DIR / "network_citation_pagerank_top10.csv", index=False)

    all_indeg = pd.Series({d: indeg.get(d, 0) for d in sorted(dois)})
    bins = [(0, 0, "0"), (1, 1, "1"), (2, 2, "2"), (3, 5, "3-5"), (6, 10, "6-10"), (11, 20, "11-20"), (21, 10**9, "21+")]
    pd.DataFrame([{
        "in_degree_bin": label, "papers": int(((all_indeg >= lo) & (all_indeg <= hi)).sum()),
        "share_pct": round(((all_indeg >= lo) & (all_indeg <= hi)).mean() * 100, 2),
    } for lo, hi, label in bins]).to_csv(TABLES_DIR / "network_citation_indegree_distribution.csv", index=False)

    flow = [{"source_inst": s, **{t: int(((ce["source_inst"] == s) & (ce["target_inst"] == t)).sum()) for t in LABS}}
            for s in LABS]
    pd.DataFrame(flow).to_csv(TABLES_DIR / "network_citation_flow_matrix.csv", index=False)

    # ---- Authorship network
    ae = lab_authorship_edges(df_auth)
    A = authorship_graph(ae)
    G = A["G"]

    def author_rows(order: List[str]) -> pd.DataFrame:
        return pd.DataFrame([{
            "rank": r, "author": a, "institution": A["inst_of"][a], "degree": A["degree"][a],
            "degree_centrality": round(A["degree_centrality"][a], 5), "joint_paper_links": A["strength"][a],
            "betweenness": round(A["betweenness"][a], 5), "community": A["comm_of"][a] + 1,
        } for r, a in enumerate(order, 1)])

    by_degree = sorted(G.nodes, key=lambda a: (-A["degree"][a], -A["strength"][a], a))[:10]
    by_btw = sorted(G.nodes, key=lambda a: (-A["betweenness"][a], a))[:10]
    author_rows(by_degree).to_csv(TABLES_DIR / "network_authorship_top_degree.csv", index=False)
    author_rows(by_btw).to_csv(TABLES_DIR / "network_authorship_top_betweenness.csv", index=False)

    rows = []
    for i, c in enumerate(A["communities"][:15], 1):
        insts = collections.Counter(A["inst_of"][n] for n in c)
        lead = sorted(c, key=lambda a: (-A["degree"][a], a))[:3]
        rows.append({
            "community": i, "authors": len(c), "share_pct": round(len(c) / G.number_of_nodes() * 100, 2),
            **{f"authors_{k.split('-')[1].lower()}": insts.get(k, 0) for k in LABS},
            "dominant_institution": insts.most_common(1)[0][0], "multi_lab": "TRUE" if len(insts) > 1 else "FALSE",
            "top_authors": "; ".join(lead),
        })
    pd.DataFrame(rows).to_csv(TABLES_DIR / "network_authorship_communities.csv", index=False)

    collab = []
    for s in LABS:
        row = {"institution": s}
        for t in LABS:
            m = ((ae["inst_a"] == s) & (ae["inst_b"] == t)) | ((ae["inst_a"] == t) & (ae["inst_b"] == s))
            row[t] = int(m.sum())
        collab.append(row)
    pd.DataFrame(collab).to_csv(TABLES_DIR / "network_authorship_collab_matrix.csv", index=False)

    comp = max(nx.connected_components(G), key=len)
    wcc = max(nx.weakly_connected_components(Gc), key=len)
    summary = [
        ("citation", "edges (citation links, per lab attribution)", len(ce)),
        ("citation", "distinct citing-cited paper pairs", len(pairs)),
        ("citation", "nodes (papers with >= 1 in-corpus link)", Gc.number_of_nodes()),
        ("citation", "corpus papers with DOI", len(dois)),
        ("citation", "papers cited >= 1 time within corpus", int((all_indeg > 0).sum())),
        ("citation", "mean in-degree (corpus papers)", round(all_indeg.mean(), 3)),
        ("citation", "max in-degree", int(all_indeg.max())),
        ("citation", "cross-lab citation links", int((ce["source_inst"] != ce["target_inst"]).sum())),
        ("citation", "largest weakly connected component (papers)", len(wcc)),
        ("citation", "citation links to/from outside Indian papers (raw data only)", len(df_cite) - len(ce)),
        ("authorship", "authors (nodes)", G.number_of_nodes()),
        ("authorship", "co-author pairs (unique edges)", G.number_of_edges()),
        ("authorship", "co-authorship links (edge rows, one per paper)", len(ae)),
        ("authorship", "mean degree (distinct co-authors)", round(sum(A["degree"].values()) / G.number_of_nodes(), 2)),
        ("authorship", "density", round(nx.density(G), 6)),
        ("authorship", "Louvain communities", len(A["communities"])),
        ("authorship", "communities with >= 10 authors", sum(len(c) >= 10 for c in A["communities"])),
        ("authorship", "modularity", round(A["modularity"], 4)),
        ("authorship", "largest connected component (authors)", len(comp)),
        ("authorship", "largest component share pct", round(len(comp) / G.number_of_nodes() * 100, 2)),
        ("authorship", "cross-lab co-author pairs (edge rows)", int((ae["inst_a"] != ae["inst_b"]).sum())),
        ("authorship", "edges to Indian partner co-authors (raw data only)", len(df_auth) - len(ae)),
        ("authorship", "betweenness sample size (source nodes)", min(BETWEENNESS_SAMPLE, G.number_of_nodes())),
    ]
    df_sum = pd.DataFrame({
        "network": [r[0] for r in summary],
        "metric": [r[1] for r in summary],
        "value": pd.Series([r[2] for r in summary], dtype=object),  # keep ints as ints
    })
    df_sum.to_csv(TABLES_DIR / "network_summary.csv", index=False)
    logger.info(f"✓ Networks: citation {Gc.number_of_nodes()} nodes / {len(pairs)} pairs; "
                f"authorship {G.number_of_nodes()} authors / {G.number_of_edges()} pairs, {len(A['communities'])} communities")


if __name__ == "__main__":
    run_network_metrics()
