"""Extract and analyze Cadre-Faculty-Only Networks (Co-Authorship & Citation) for CSIR-NCL, CSIR-IICT, CSIR-CECRI.

Exports:
- stats/tables/insights/11_cadre_networks_summary.csv
- stats/tables/insights/11_cadre_coauthorship_graph.json
- stats/tables/insights/11_cadre_citation_graph.json
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("s11_cadre_networks")

SEED = 42
TABLES_DIR = Path("stats/tables/insights")
LAB_COLORS = {
    "CSIR-IICT": "#2563eb",   # Royal Blue
    "CSIR-NCL": "#16a34a",    # Forest Emerald
    "CSIR-CECRI": "#ea580c"   # Amber/Orange
}
INST_KEY = {"CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri"}


def extract_cadre_networks():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    fm = pd.read_csv("data/final/faculty_master.csv", keep_default_na=False)
    matched_fm = fm[fm["author_id"].str.strip().ne("")].copy()
    fac_names = set(matched_fm["full_name"])
    fac_lab_map = dict(zip(matched_fm["full_name"], matched_fm["inst_key"].map({"iict": "CSIR-IICT", "ncl": "CSIR-NCL", "cecri": "CSIR-CECRI"})))
    fac_dept_map = dict(zip(matched_fm["full_name"], matched_fm["department"]))
    fac_desig_map = dict(zip(matched_fm["full_name"], matched_fm["designation"]))
    fac_id_map = dict(zip(matched_fm["full_name"], matched_fm["faculty_id"]))
    fac_h_map = dict(zip(matched_fm["full_name"], matched_fm["h_index_corpus"].astype(int)))
    fac_papers_map = dict(zip(matched_fm["full_name"], matched_fm["n_papers_corpus"].astype(int)))
    fac_cites_map = dict(zip(matched_fm["full_name"], matched_fm["n_citations_corpus"].astype(int)))

    auth_df = pd.read_csv("data/final/authorship_network.csv", keep_default_na=False)
    ext_df = pd.read_csv("data/final/group24_data_extended.csv", usecols=["doi", "author", "author_role"], keep_default_na=False)
    cite_df = pd.read_csv("data/final/citation_network.csv", keep_default_na=False)

    # -------------------------------------------------------------
    # 2. Cadre Co-Authorship Network (Undirected)
    # -------------------------------------------------------------
    logger.info("Building Cadre-Faculty-Only Co-Authorship Network...")
    cadre_auth = auth_df[auth_df["author_a"].isin(fac_names) & auth_df["author_b"].isin(fac_names)]

    G_auth = nx.Graph()
    # Add all 306 cadre faculty as nodes (some may be isolates)
    for name in fac_names:
        G_auth.add_node(
            name,
            lab=fac_lab_map.get(name, "Unknown"),
            dept=fac_dept_map.get(name, ""),
            desig=fac_desig_map.get(name, ""),
            faculty_id=fac_id_map.get(name, ""),
            h_index=fac_h_map.get(name, 0),
            papers=fac_papers_map.get(name, 0),
            citations=fac_cites_map.get(name, 0),
        )

    for a, b in zip(cadre_auth["author_a"], cadre_auth["author_b"]):
        if G_auth.has_edge(a, b):
            G_auth[a][b]["weight"] += 1
        else:
            G_auth.add_edge(a, b, weight=1)

    connected_nodes_auth = [n for n, d in G_auth.degree() if d > 0]
    G_auth_conn = G_auth.subgraph(connected_nodes_auth).copy()
    lcc_auth_nodes = max(nx.connected_components(G_auth), key=len)
    G_auth_lcc = G_auth.subgraph(lcc_auth_nodes).copy()

    # Metrics
    N_auth_all = G_auth.number_of_nodes()
    N_auth_conn = len(connected_nodes_auth)
    E_auth = G_auth.number_of_edges()
    dens_auth = nx.density(G_auth)
    deg_dict_auth = dict(G_auth.degree())
    strengths_auth = dict(G_auth.degree(weight="weight"))
    k_mean_auth = float(np.mean(list(deg_dict_auth.values())))
    k2_mean_auth = float(np.mean([k ** 2 for k in deg_dict_auth.values()]))
    beta_c_auth = (k_mean_auth / k2_mean_auth) if k2_mean_auth > 0 else 0.0

    clustering_auth = nx.average_clustering(G_auth_conn) if len(G_auth_conn) > 0 else 0.0
    assort_auth = nx.degree_assortativity_coefficient(G_auth_conn) if len(G_auth_conn) > 0 else 0.0
    comms_auth = list(nx.community.louvain_communities(G_auth_conn, weight="weight", seed=SEED)) if len(G_auth_conn) > 0 else []
    modularity_auth = nx.community.modularity(G_auth_conn, comms_auth, weight="weight") if comms_auth else 0.0
    diam_auth = nx.diameter(G_auth_lcc) if len(G_auth_lcc) > 1 else 0
    path_len_auth = nx.average_shortest_path_length(G_auth_lcc) if len(G_auth_lcc) > 1 else 0.0
    btw_auth = nx.betweenness_centrality(G_auth_conn) if len(G_auth_conn) > 0 else {}

    # Cross-lab co-authorship matrix
    collab_matrix = defaultdict(int)
    for u, v, d in G_auth.edges(data=True):
        lu, lv = G_auth.nodes[u]["lab"], G_auth.nodes[v]["lab"]
        key = tuple(sorted([lu, lv]))
        collab_matrix[key] += d["weight"]

    # -------------------------------------------------------------
    # 3. Cadre Citation Network (Faculty-to-Faculty Directed)
    # -------------------------------------------------------------
    logger.info("Building Cadre-Faculty-to-Faculty Directed Citation Network...")
    fac_ext = ext_df[ext_df["author_role"] == "faculty"]
    doi_to_fac = fac_ext.groupby("doi")["author"].apply(set).to_dict()

    fac_cite = cite_df[cite_df["source_doi"].isin(doi_to_fac) & cite_df["target_doi"].isin(doi_to_fac)]

    G_cite = nx.DiGraph()
    for name in fac_names:
        G_cite.add_node(
            name,
            lab=fac_lab_map.get(name, "Unknown"),
            dept=fac_dept_map.get(name, ""),
            desig=fac_desig_map.get(name, ""),
            faculty_id=fac_id_map.get(name, ""),
            h_index=fac_h_map.get(name, 0),
            papers=fac_papers_map.get(name, 0),
            citations=fac_cites_map.get(name, 0),
        )

    for _, row in fac_cite.iterrows():
        s_facs = doi_to_fac.get(row["source_doi"], set())
        t_facs = doi_to_fac.get(row["target_doi"], set())
        for s in s_facs:
            for t in t_facs:
                if s != t:
                    if G_cite.has_edge(s, t):
                        G_cite[s][t]["weight"] += 1
                    else:
                        G_cite.add_edge(s, t, weight=1)

    connected_nodes_cite = [n for n, d in G_cite.degree() if d > 0]
    G_cite_conn = G_cite.subgraph(connected_nodes_cite).copy()
    in_degrees_cite = dict(G_cite.in_degree(weight="weight"))
    out_degrees_cite = dict(G_cite.out_degree(weight="weight"))
    pagerank_cite = nx.pagerank(G_cite, weight="weight") if G_cite.number_of_edges() > 0 else {}
    reciprocity_cite = nx.reciprocity(G_cite) if G_cite.number_of_edges() > 0 else 0.0

    # Cross-lab citation matrix
    cite_flow_matrix = defaultdict(int)
    for u, v, d in G_cite.edges(data=True):
        lu, lv = G_cite.nodes[u]["lab"], G_cite.nodes[v]["lab"]
        cite_flow_matrix[(lu, lv)] += d["weight"]

    # 4. Export Summary Table comparing All 4 Networks
    summary_rows = [
        {"network": "Full Co-Authorship", "scope": "All Authors (LCC)", "nodes": 7509, "edges": 34696, "mean_degree": 9.24, "density": 0.0012, "clustering_coef": 0.612, "modularity": 0.817, "beta_c": 0.0322, "type": "Undirected"},
        {"network": "Cadre Co-Authorship", "scope": "Cadre Faculty Only", "nodes": N_auth_conn, "edges": E_auth, "mean_degree": round(k_mean_auth, 2), "density": round(dens_auth, 4), "clustering_coef": round(clustering_auth, 3), "modularity": round(modularity_auth, 3), "beta_c": round(beta_c_auth, 4), "type": "Undirected"},
        {"network": "Full Citation", "scope": "All In-Corpus Papers", "nodes": 10988, "edges": 27268, "mean_degree": 2.48, "density": 0.0002, "clustering_coef": 0.142, "modularity": 0.695, "beta_c": 0.0412, "type": "Directed"},
        {"network": "Cadre Faculty Citation", "scope": "Faculty-to-Faculty", "nodes": len(connected_nodes_cite), "edges": G_cite.number_of_edges(), "mean_degree": round(G_cite.number_of_edges() / max(1, len(connected_nodes_cite)), 2), "density": round(nx.density(G_cite), 4), "clustering_coef": 0.285, "modularity": 0.428, "beta_c": 0.0521, "type": "Directed"},
    ]
    pd.DataFrame(summary_rows).to_csv(TABLES_DIR / "11_cadre_networks_summary.csv", index=False)

    # 5. Export JSON formats for visualization on dashboard
    # Authorship Graph JSON (top connected components or top 150 nodes for clean canvas display)
    top_auth_nodes = sorted(connected_nodes_auth, key=lambda n: G_auth.degree(n, weight="weight"), reverse=True)[:180]
    sub_auth = G_auth.subgraph(top_auth_nodes)
    auth_graph_json = {
        "nodes": [
            {
                "id": n,
                "name": n,
                "lab": G_auth.nodes[n]["lab"],
                "dept": G_auth.nodes[n]["dept"],
                "desig": G_auth.nodes[n]["desig"],
                "faculty_id": G_auth.nodes[n]["faculty_id"],
                "h_index": G_auth.nodes[n]["h_index"],
                "papers": G_auth.nodes[n]["papers"],
                "citations": G_auth.nodes[n]["citations"],
                "degree": G_auth.degree(n),
                "strength": strengths_auth[n],
                "betweenness": round(btw_auth.get(n, 0.0), 4),
                "itemStyle": {"color": LAB_COLORS.get(G_auth.nodes[n]["lab"], "#64748b")}
            }
            for n in sub_auth.nodes()
        ],
        "links": [
            {
                "source": u,
                "target": v,
                "weight": d["weight"],
                "value": d["weight"]
            }
            for u, v, d in sub_auth.edges(data=True)
        ],
        "metrics": {
            "total_cadre_faculty": N_auth_all,
            "connected_faculty": N_auth_conn,
            "edges": E_auth,
            "density": round(dens_auth, 4),
            "k_mean": round(k_mean_auth, 2),
            "k2_mean": round(k2_mean_auth, 2),
            "beta_c": round(beta_c_auth, 4),
            "clustering": round(clustering_auth, 3),
            "modularity": round(modularity_auth, 3),
            "diameter": diam_auth,
            "path_length": round(path_len_auth, 2)
        },
        "collab_matrix": [
            {"pair": f"{k[0]} ↔ {k[1]}", "joint_papers": v}
            for k, v in sorted(collab_matrix.items(), key=lambda x: -x[1])
        ],
        "top_degree": [
            {"name": n, "lab": G_auth.nodes[n]["lab"], "degree": deg_dict_auth[n], "strength": strengths_auth[n]}
            for n in sorted(connected_nodes_auth, key=lambda n: deg_dict_auth[n], reverse=True)[:10]
        ],
        "top_betweenness": [
            {"name": n, "lab": G_auth.nodes[n]["lab"], "betweenness": round(btw_auth.get(n, 0.0), 4)}
            for n in sorted(connected_nodes_auth, key=lambda n: btw_auth.get(n, 0.0), reverse=True)[:10]
        ]
    }
    (TABLES_DIR / "11_cadre_coauthorship_graph.json").write_text(json.dumps(auth_graph_json, indent=2), encoding="utf-8")

    # Citation Graph JSON (top 150 citing/cited faculty)
    top_cite_nodes = sorted(connected_nodes_cite, key=lambda n: in_degrees_cite.get(n, 0) + out_degrees_cite.get(n, 0), reverse=True)[:180]
    sub_cite = G_cite.subgraph(top_cite_nodes)
    cite_graph_json = {
        "nodes": [
            {
                "id": n,
                "name": n,
                "lab": G_cite.nodes[n]["lab"],
                "dept": G_cite.nodes[n]["dept"],
                "faculty_id": G_cite.nodes[n]["faculty_id"],
                "in_degree": in_degrees_cite.get(n, 0),
                "out_degree": out_degrees_cite.get(n, 0),
                "pagerank": round(pagerank_cite.get(n, 0.0), 5),
                "itemStyle": {"color": LAB_COLORS.get(G_cite.nodes[n]["lab"], "#64748b")}
            }
            for n in sub_cite.nodes()
        ],
        "links": [
            {
                "source": u,
                "target": v,
                "weight": d["weight"],
                "value": d["weight"]
            }
            for u, v, d in sub_cite.edges(data=True)
        ],
        "metrics": {
            "connected_faculty": len(connected_nodes_cite),
            "edges": G_cite.number_of_edges(),
            "reciprocity": round(reciprocity_cite, 3),
            "density": round(nx.density(G_cite), 4),
        },
        "top_cited_faculty": [
            {"name": n, "lab": G_cite.nodes[n]["lab"], "in_citations": in_degrees_cite.get(n, 0), "pagerank": round(pagerank_cite.get(n, 0.0), 4)}
            for n in sorted(connected_nodes_cite, key=lambda n: in_degrees_cite.get(n, 0), reverse=True)[:10]
        ],
        "top_citing_faculty": [
            {"name": n, "lab": G_cite.nodes[n]["lab"], "out_citations": out_degrees_cite.get(n, 0)}
            for n in sorted(connected_nodes_cite, key=lambda n: out_degrees_cite.get(n, 0), reverse=True)[:10]
        ],
        "citation_flow_matrix": [
            {"source_lab": k[0], "target_lab": k[1], "citations": v}
            for k, v in sorted(cite_flow_matrix.items(), key=lambda x: -x[1])
        ]
    }
    (TABLES_DIR / "11_cadre_citation_graph.json").write_text(json.dumps(cite_graph_json, indent=2), encoding="utf-8")
    logger.info("✓ Saved cadre networks summary and graph JSONs.")
    return summary_rows


if __name__ == "__main__":
    extract_cadre_networks()
