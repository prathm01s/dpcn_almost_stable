"""Cadre-faculty networks (co-authorship and citation) for CSIR-NCL, CSIR-IICT, CSIR-CECRI.

Nodes are roster scientists (faculty_master.csv), identified by faculty_id and built with the
shared functions in src/stats/networks.py, so these numbers equal the dashboard's faculty
networks and stats/tables/network_summary.csv. Node ids in the JSON are display labels
(the name; the lab is added when two scientists share a name).

Every value in the summary is computed from the graphs (D-33 replaced constants that had been
typed in for the two full networks and for the cadre citation network's clustering,
modularity and beta_c).

Exports:
- stats/tables/insights/11_cadre_networks_summary.csv
- stats/tables/insights/11_cadre_coauthorship_graph.json
- stats/tables/insights/11_cadre_citation_graph.json
"""

import json
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd

from src.common.logging import get_logger
from src.stats.networks import (authorship_graph, citation_graph, corpus_dois, incorpus_citation_edges,
                                lab_authorship_edges, labelled_faculty_graphs, network_metrics)

logger = get_logger("s11_cadre_networks")

SEED = 42
TABLES_DIR = Path("stats/tables/insights")
LAB_COLORS = {"CSIR-IICT": "#2563eb", "CSIR-NCL": "#16a34a", "CSIR-CECRI": "#ea580c"}


def _row(network: str, scope: str, m: dict, kind: str, nodes_key: str = "connected_nodes") -> dict:
    return {"network": network, "scope": scope, "nodes": m[nodes_key], "edges": m["edges"],
            "mean_degree": m["mean_degree"], "density": round(m["density"], 4), "clustering_coef": m["clustering"],
            "modularity": m["modularity"], "beta_c": m["beta_c"], "type": kind}


def extract_cadre_networks():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    cite = incorpus_citation_edges(pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False),
                                   corpus_dois(ext))
    auth = lab_authorship_edges(pd.read_csv("data/final/authorship_network.csv", dtype=str, keep_default_na=False))

    G_auth, G_cite, self_pairs, _ = labelled_faculty_graphs(ext, fm, cite)
    lab = dict(G_auth.nodes(data="lab"))

    # ---- full networks, for the four-network comparison (computed, not typed in)
    A = authorship_graph(auth)
    full_lcc = A["G"].subgraph(max(nx.connected_components(A["G"]), key=len)).copy()
    Gc, _, _ = citation_graph(cite)
    m_full_auth = network_metrics(full_lcc)
    m_full_cite = network_metrics(Gc)
    m_auth, m_cite = network_metrics(G_auth), network_metrics(G_cite)

    summary_rows = [
        _row("Full Co-Authorship", "All lab authors incl. students and project staff (largest component)",
             m_full_auth, "Undirected", "nodes"),
        _row("Cadre Co-Authorship", f"Roster scientists with a faculty co-author (of {m_auth['nodes']} active)",
             m_auth, "Undirected"),
        _row("Full Citation", "Papers with an in-corpus citation link", m_full_cite, "Directed", "nodes"),
        _row("Cadre Faculty Citation", f"Roster scientists citing or cited by another (of {m_cite['nodes']} active)",
             m_cite, "Directed"),
    ]
    pd.DataFrame(summary_rows).to_csv(TABLES_DIR / "11_cadre_networks_summary.csv", index=False)

    # ---- co-authorship graph JSON (connected scientists)
    conn_a = [n for n, d in G_auth.degree() if d > 0]
    Gc_a = G_auth.subgraph(conn_a)
    btw = nx.betweenness_centrality(Gc_a)
    strength = dict(G_auth.degree(weight="weight"))
    collab = defaultdict(int)
    for u, v, w in G_auth.edges(data="weight"):
        collab[tuple(sorted([lab[u], lab[v]]))] += w

    def node(n, extra):
        d = G_auth.nodes[n]
        return {"id": n, "name": n, "lab": d["lab"], "dept": d["department"], "desig": d["designation"],
                "faculty_id": d["faculty_id"], "h_index": d["h_index"], "papers": d["papers"],
                "citations": d["citations"], "itemStyle": {"color": LAB_COLORS.get(d["lab"], "#64748b")}, **extra}

    top_a = sorted(conn_a, key=lambda n: (-strength[n], n))[:180]
    sub_a = G_auth.subgraph(top_a)
    auth_json = {
        "nodes": [node(n, {"degree": G_auth.degree(n), "strength": strength[n], "betweenness": round(btw.get(n, 0), 4)})
                  for n in sub_a.nodes()],
        "links": [{"source": u, "target": v, "weight": w, "value": w} for u, v, w in sub_a.edges(data="weight")],
        "metrics": {
            "total_cadre_faculty": m_auth["nodes"], "connected_faculty": m_auth["connected_nodes"],
            "edges": m_auth["edges"], "density": round(m_auth["density"], 4), "k_mean": m_auth["mean_degree"],
            "beta_c": m_auth["beta_c"], "clustering": m_auth["clustering"], "modularity": m_auth["modularity"],
            "lcc_nodes": m_auth["lcc_nodes"], "shown_nodes": sub_a.number_of_nodes(),
        },
        "collab_matrix": [{"pair": f"{k[0]} ↔ {k[1]}", "joint_papers": v}
                          for k, v in sorted(collab.items(), key=lambda x: (-x[1], x[0]))],
        "top_degree": [{"name": n, "lab": lab[n], "degree": G_auth.degree(n), "strength": strength[n]}
                       for n in sorted(conn_a, key=lambda n: (-G_auth.degree(n), n))[:10]],
        "top_betweenness": [{"name": n, "lab": lab[n], "betweenness": round(btw.get(n, 0), 4)}
                            for n in sorted(conn_a, key=lambda n: (-btw.get(n, 0), n))[:10]],
    }
    (TABLES_DIR / "11_cadre_coauthorship_graph.json").write_text(json.dumps(auth_json, indent=2), encoding="utf-8")

    # ---- citation graph JSON
    conn_c = [n for n, d in G_cite.degree() if d > 0]
    in_w, out_w = dict(G_cite.in_degree(weight="weight")), dict(G_cite.out_degree(weight="weight"))
    pr = nx.pagerank(G_cite, weight="weight") if G_cite.number_of_edges() else {}
    flow = defaultdict(int)
    for u, v, w in G_cite.edges(data="weight"):
        flow[(lab[u], lab[v])] += w
    top_c = sorted(conn_c, key=lambda n: (-(in_w[n] + out_w[n]), n))[:180]
    sub_c = G_cite.subgraph(top_c)
    cite_json = {
        "nodes": [{"id": n, "name": n, "lab": lab[n], "dept": G_cite.nodes[n]["department"],
                   "faculty_id": G_cite.nodes[n]["faculty_id"], "in_degree": in_w[n], "out_degree": out_w[n],
                   "pagerank": round(pr.get(n, 0), 5), "itemStyle": {"color": LAB_COLORS.get(lab[n], "#64748b")}}
                  for n in sub_c.nodes()],
        "links": [{"source": u, "target": v, "weight": w, "value": w} for u, v, w in sub_c.edges(data="weight")],
        "metrics": {
            "total_cadre_faculty": m_cite["nodes"], "connected_faculty": m_cite["connected_nodes"],
            "edges": m_cite["edges"], "citation_links": int(G_cite.size(weight="weight")),
            "self_citation_pairs_excluded": self_pairs,
            "reciprocity": round(nx.reciprocity(G_cite), 3) if G_cite.number_of_edges() else 0.0,
            "density": round(m_cite["density"], 4), "shown_nodes": sub_c.number_of_nodes(),
        },
        "top_cited_faculty": [{"name": n, "lab": lab[n], "in_citations": in_w[n], "pagerank": round(pr.get(n, 0), 4)}
                              for n in sorted(conn_c, key=lambda n: (-in_w[n], n))[:10]],
        "top_citing_faculty": [{"name": n, "lab": lab[n], "out_citations": out_w[n]}
                               for n in sorted(conn_c, key=lambda n: (-out_w[n], n))[:10]],
        "citation_flow_matrix": [{"source_lab": k[0], "target_lab": k[1], "citations": v}
                                 for k, v in sorted(flow.items(), key=lambda x: (-x[1], x[0]))],
    }
    (TABLES_DIR / "11_cadre_citation_graph.json").write_text(json.dumps(cite_json, indent=2), encoding="utf-8")
    logger.info(f"Cadre networks: co-authorship {m_auth['connected_nodes']}/{m_auth['nodes']} scientists, "
                f"{m_auth['edges']} pairs; citation {m_cite['connected_nodes']} scientists, {m_cite['edges']} edges")
    return summary_rows


if __name__ == "__main__":
    extract_cadre_networks()
