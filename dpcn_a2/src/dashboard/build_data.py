"""Step 18: Build static JavaScript data payload for interactive offline dashboard.

Reads authoritative CSV metrics from stats/tables/ and data/final/
Produces dashboard/data/g24_data.js defining window.G24_DATA.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.common.logging import get_logger
from src.stats.networks import (
    authorship_graph, citation_graph, corpus_dois, incorpus_citation_edges, lab_authorship_edges,
)

logger = get_logger("build_dashboard_data")

TABLES_DIR = Path("stats/tables")
OUTPUT_JS = Path("dashboard/data/g24_data.js")

INST_KEY_MAP = {
    "Group 24 Combined": "all",
    "CSIR-IICT": "iict",
    "CSIR-NCL": "ncl",
    "CSIR-CECRI": "cecri",
}


def load_csv(filename: str) -> pd.DataFrame:
    p = TABLES_DIR / filename
    if not p.exists():
        logger.warning(f"{p} does not exist!")
        return pd.DataFrame()
    return pd.read_csv(p, keep_default_na=False)


def ordered_subgraph(G: "nx.Graph", nodes) -> "nx.Graph":
    """Induced subgraph in G's node order (networkx subgraph views iterate in set order,
    which varies with PYTHONHASHSEED and made the dashboard bundle non-reproducible)."""
    keep = set(nodes)
    H = G.__class__()
    H.add_nodes_from((n, G.nodes[n]) for n in G if n in keep)
    H.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if u in keep and v in keep)
    return H


def build_network_payload(df_ext: pd.DataFrame) -> Dict[str, Any]:
    """Compute citation and authorship network analytics for interactive visualization."""
    logger.info("Computing network analytics for dashboard...")

    # 1. CITATION NETWORK: in-corpus edges only (edges to outside Indian papers are raw data)
    df_cite_all = pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
    df_cite = incorpus_citation_edges(df_cite_all, corpus_dois(df_ext))
    G_c, pr, in_deg = citation_graph(df_cite)

    # Build DOI metadata lookup
    doi_info = {}
    for _, r in df_ext.drop_duplicates(subset=["doi"]).iterrows():
        d = r["doi"]
        if d:
            short_t = r["title"][:85] + ("..." if len(r["title"]) > 85 else "")
            doi_info[d] = {
                "title": short_t,
                "full_title": r["title"],
                "journal": r["journal_name"],
                "year": int(r["year"]),
                "inst": r["institution"],
                "inst_key": INST_KEY_MAP.get(r["institution"], "all"),
                "citations": int(r["citations"]),
                "quartile": r["quartile"] or "Unranked",
            }

    # Cross-institute citation flow matrix (source_inst -> target_inst)
    labs = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
    flow_matrix = []
    inter_lab_citations = 0
    for s_lab in labs:
        row = {"source_inst": s_lab, "s_key": INST_KEY_MAP.get(s_lab, "all")}
        for t_lab in labs:
            cnt = int(((df_cite["source_inst"] == s_lab) & (df_cite["target_inst"] == t_lab)).sum())
            row[INST_KEY_MAP.get(t_lab, "all")] = cnt
            if s_lab != t_lab:
                inter_lab_citations += cnt
        flow_matrix.append(row)

    # Top 10 PageRank landmark papers
    top_pr_sorted = sorted(pr.items(), key=lambda x: (-x[1], x[0]))
    top_pr_list = []
    for rank_idx, (doi_item, score) in enumerate(top_pr_sorted[:10], 1):
        meta = doi_info.get(doi_item, {})
        top_pr_list.append({
            "rank": rank_idx,
            "doi": doi_item,
            "score": round(score, 5),
            "in_degree": in_deg.get(doi_item, 0),
            "title": meta.get("title", doi_item),
            "journal": meta.get("journal", ""),
            "year": meta.get("year", ""),
            "inst": meta.get("inst", ""),
            "citations": meta.get("citations", 0),
            "quartile": meta.get("quartile", ""),
        })

    # Curate high-impact citation core subgraph (~160 papers)
    top_c_nodes = sorted(G_c.nodes(), key=lambda n: (in_deg.get(n, 0), pr.get(n, 0), n), reverse=True)[:150]
    cross_cite_edges = df_cite[df_cite["source_inst"] != df_cite["target_inst"]]
    top_cross_sources = cross_cite_edges["source_doi"].value_counts().head(25).index.tolist()
    top_c_nodes_set = set(top_c_nodes).union(set(top_cross_sources))
    sub_c = ordered_subgraph(G_c, top_c_nodes_set)

    c_nodes = []
    category_order = ["iict", "ncl", "cecri"]
    for n in sub_c.nodes():
        meta = doi_info.get(n, {})
        deg_val = in_deg.get(n, 0)
        c_cat = meta.get("inst_key", "all")
        cat_idx = category_order.index(c_cat) if c_cat in category_order else 0
        c_nodes.append({
            "id": n,
            "name": meta.get("title", n[:30] + "..."),
            "full_title": meta.get("full_title", n),
            "journal": meta.get("journal", "Journal"),
            "year": meta.get("year", 2020),
            "inst": meta.get("inst", "CSIR"),
            "category": cat_idx,
            "citations": meta.get("citations", deg_val),
            "in_degree": deg_val,
            "pagerank": round(pr.get(n, 0), 5),
            "symbolSize": max(12, min(42, int(10 + deg_val * 1.4))),
            "value": deg_val,
            "doi": n,
        })

    c_links = []
    for u, v, d in sub_c.edges(data=True):
        c_links.append({
            "source": u,
            "target": v,
            "s_inst": d.get("s_inst", ""),
            "t_inst": d.get("t_inst", ""),
            "is_cross": d.get("s_inst") != d.get("t_inst"),
        })

    # 2. AUTHORSHIP NETWORK: authors of the three labs only (partner co-authors are raw data)
    df_auth = lab_authorship_edges(pd.read_csv("data/final/authorship_network.csv", dtype=str, keep_default_na=False))
    A = authorship_graph(df_auth)
    G_a = A["G"]
    author_inst_map = A["inst_of"]
    deg_a = A["degree"]  # distinct co-authors
    strength_a = A["strength"]  # joint-paper links
    comms = A["communities"]
    author_comm_map = A["comm_of"]
    btw_a = A["betweenness"]

    # Cross-institute collaboration matrix
    collab_matrix = []
    inter_lab_pairs = 0
    for s_lab in labs:
        row = {"inst": s_lab, "inst_key": INST_KEY_MAP.get(s_lab, "all")}
        for t_lab in labs:
            if s_lab == t_lab:
                cnt = int(((df_auth["inst_a"] == s_lab) & (df_auth["inst_b"] == t_lab)).sum())
            else:
                cnt = int((((df_auth["inst_a"] == s_lab) & (df_auth["inst_b"] == t_lab)) |
                           ((df_auth["inst_a"] == t_lab) & (df_auth["inst_b"] == s_lab))).sum())
            row[INST_KEY_MAP.get(t_lab, "all")] = cnt
            if s_lab != t_lab:
                inter_lab_pairs += cnt
        collab_matrix.append(row)

    inter_lab_pairs = inter_lab_pairs // 2

    # Top collaborative bridges
    top_deg_sorted = sorted(deg_a.items(), key=lambda x: (-x[1], -strength_a[x[0]], x[0]))
    top_bridges_list = []
    for rank_idx, (auth_name, degree_val) in enumerate(top_deg_sorted[:10], 1):
        top_bridges_list.append({
            "rank": rank_idx,
            "author": auth_name,
            "collaborators_count": degree_val,
            "joint_paper_links": strength_a[auth_name],
            "betweenness": round(btw_a.get(auth_name, 0), 4),
            "community_id": author_comm_map.get(auth_name, 0),
            "institution": author_inst_map.get(auth_name, ""),
        })

    # Pick top ~160 most collaborative & bridging authors
    top_a_nodes = [a for a, _ in top_deg_sorted[:150]]
    cross_auth_edges = df_auth[df_auth["inst_a"] != df_auth["inst_b"]]
    cross_authors = set(cross_auth_edges["author_a"]).union(set(cross_auth_edges["author_b"]))
    cross_authors_top = sorted(sorted(cross_authors), key=lambda a: deg_a.get(a, 0), reverse=True)[:25]
    top_a_nodes_set = set(top_a_nodes).union(set(cross_authors_top))
    sub_a = ordered_subgraph(G_a, top_a_nodes_set)

    df_fac_meta = pd.read_csv("data/final/faculty_master.csv", keep_default_na=False)
    fac_dept_map = dict(zip(df_fac_meta["full_name"], df_fac_meta["department"]))
    fac_desig_map = dict(zip(df_fac_meta["full_name"], df_fac_meta["designation"]))

    a_nodes = []
    for n in sub_a.nodes():
        inst_n = author_inst_map.get(n, "CSIR")
        d_val = deg_a.get(n, 0)
        a_cat = INST_KEY_MAP.get(inst_n, "all")
        cat_idx = category_order.index(a_cat) if a_cat in category_order else 0
        a_nodes.append({
            "id": n,
            "name": n,
            "inst": inst_n,
            "category": cat_idx,
            "community": author_comm_map.get(n, 0),
            "department": fac_dept_map.get(n, "Scientific Cadre"),
            "designation": fac_desig_map.get(n, "Scientist"),
            "degree": d_val,
            "betweenness": round(btw_a.get(n, 0), 4),
            "symbolSize": max(12, min(42, int(10 + d_val * 0.12))),
            "value": d_val,
        })

    a_links = []
    for u, v, d in sub_a.edges(data=True):
        w = d.get("weight", 1)
        a_links.append({
            "source": u,
            "target": v,
            "weight": w,
            "value": w,
            "is_cross": author_inst_map.get(u) != author_inst_map.get(v),
        })

    logger.info(f"✓ Network analytics complete: Citation sub={len(c_nodes)} nodes, {len(c_links)} edges; Authorship sub={len(a_nodes)} nodes, {len(a_links)} edges")

    return {
        "categories": [
            {"name": "CSIR-IICT", "itemStyle": {"color": "#2b5c8f"}},
            {"name": "CSIR-NCL", "itemStyle": {"color": "#2e7d32"}},
            {"name": "CSIR-CECRI", "itemStyle": {"color": "#d95f02"}},
        ],
        "citation": {
            "stats": {
                "total_edges": len(df_cite),
                "total_nodes": len(set(df_cite["source_doi"]).union(set(df_cite["target_doi"]))),
                "inter_lab_citations": inter_lab_citations,
                "top_pagerank_paper": top_pr_list[0]["title"] if top_pr_list else "",
            },
            "nodes": c_nodes,
            "links": c_links,
            "top_pagerank": top_pr_list,
            "flow_matrix": flow_matrix,
        },
        "authorship": {
            "stats": {
                "total_edges": len(df_auth),
                "total_authors": len(set(df_auth["author_a"]).union(set(df_auth["author_b"]))),
                "communities_count": len(comms),
                "modularity": round(A["modularity"], 4),
                "inter_lab_pairs": inter_lab_pairs,
                "top_collaborator": top_bridges_list[0]["author"] if top_bridges_list else "",
            },
            "nodes": a_nodes,
            "links": a_links,
            "top_bridges": top_bridges_list,
            "collab_matrix": collab_matrix,
        },
    }


def build_impact_ratio_payload() -> Dict[str, Any]:
    """Thresholds and authoritative (unfiltered) IR summary from stats/tables/impact_ratio_summary.csv."""
    from src.stats.impact_ratio import settings

    summ = load_csv("impact_ratio_summary.csv")
    return {
        "thresholds": settings()["thresholds"],
        "percentile": float(summ["percentile"].iloc[0]),
        "percentile_threshold": float(summ["percentile_threshold"].iloc[0]),
        "summary": {INST_KEY_MAP[r["institution"]]: r for r in json.loads(summ.to_json(orient="records"))},
    }


def build_connectivity_payload() -> Dict[str, Any]:
    """Indian connectivity bundle (Sections 7a/7b) keyed by dashboard institute key."""

    def records(df: pd.DataFrame, drop=("institution", "scope")) -> List[Dict[str, Any]]:
        df = df.drop(columns=[c for c in drop if c in df.columns])
        return json.loads(df.to_json(orient="records"))

    def by_inst(df: pd.DataFrame, col: str = "institution") -> Dict[str, List[Dict[str, Any]]]:
        return {INST_KEY_MAP[i]: records(g) for i, g in df.groupby(col) if i in INST_KEY_MAP}

    # Combined row has blank cells; default NA parsing keeps the count columns numeric
    flow = pd.read_csv(TABLES_DIR / "citation_flow_summary.csv").convert_dtypes()
    yearly = load_csv("citation_flow_by_year.csv")
    yearly_all = yearly.groupby("year", as_index=False).sum(numeric_only=True).assign(institution="Group 24 Combined")
    sectors = load_csv("cross_cluster_summary.csv")
    hubs = load_csv("hub_authors.csv")

    return {
        "flow_summary": {INST_KEY_MAP[r["institution"]]: r for r in records(flow, drop=()) if r["institution"] in INST_KEY_MAP},
        "flow_by_year": by_inst(pd.concat([yearly, yearly_all])),
        "top_citing_institutes": by_inst(load_csv("top_citing_indian_institutes.csv")),
        "top_citing_papers": by_inst(load_csv("top_papers_citing_institute.csv")),
        "cross_cluster": by_inst(sectors),
        "hub_authors": by_inst(hubs, col="scope"),
        "topic_jaccard": records(load_csv("topic_jaccard.csv"), drop=()),
        "partner_topic_jaccard": by_inst(load_csv("partner_topic_jaccard.csv")),
    }


def run_build_dashboard_data() -> None:
    logger.info("Starting dashboard data build...")
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)

    df_trend = load_csv("publication_trend.csv")
    df_type = load_csv("publication_trend_type.csv")
    df_quartile = load_csv("quartile_distribution.csv")
    df_cite = load_csv("citation_summary.csv")
    df_h_sum = load_csv("h_index_summary.csv")
    df_h_bins = load_csv("h_index_distribution.csv")
    df_top_j = load_csv("top_journals.csv")
    df_top_p = load_csv("top_cited_papers.csv")
    df_field = load_csv("research_areas_field.csv")
    df_subfield = load_csv("research_areas_subfield.csv")
    df_fac = load_csv("faculty_performance.csv")
    df_dept = load_csv("department_performance.csv")
    df_conf = load_csv("conference_ranks.csv")
    df_conn = load_csv("indian_connections_summary.csv")
    df_partners = load_csv("indian_partner_institutions.csv")

    # Load compact paper rows for instant client-side multi-filter queries
    df_ext = pd.read_csv("data/final/group24_data_extended.csv", keep_default_na=False)
    # Deduplicate to paper level per institution
    df_papers_inst = df_ext.drop_duplicates(subset=["institution", "work_id"])
    refs = pd.read_csv("data/final/work_reference_counts.csv", dtype={"references_count": "Int64"})
    ref_of = {w: (None if pd.isna(n) else int(n)) for w, n in zip(refs["work_id"], refs["references_count"])}

    # Prepare compact records: [work_id, inst_key, year, type, quartile, field, citations, title, journal, doi]
    compact_papers: List[Dict[str, Any]] = []
    for _, r in df_papers_inst.iterrows():
        compact_papers.append({
            "id": r["work_id"],
            "inst": INST_KEY_MAP.get(r["institution"], "other"),
            "yr": int(r["year"]),
            "t": str(r["type"]).lower(),
            "q": str(r["quartile"]),
            "f": str(r["field"]) or "Unclassified",
            "c": int(r["citations"]),
            "ti": str(r["title"]),
            "j": str(r["journal_name"]),
            "doi": str(r["doi"]),
            "r": ref_of.get(r["work_id"]),  # references made (citation impact ratio = c / r)
        })

    logger.info(f"Compiled {len(compact_papers)} compact paper records for client-side filtering")

    payload: Dict[str, Any] = {
        "meta": {
            "group": 24,
            "title": "Mapping Indian Research: CSIR Chemistry Cluster",
            "institutes": ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"],
            "collection_date": "2026-10-13",
            "year_window": [2016, 2026],
            "is_partial_2026": True,
            "total_papers": df_ext["work_id"].nunique(),
            "total_authorship_rows": len(df_ext),
            "total_faculty": len(df_fac),
        },
        "by_institute": {},
        "papers_compact": compact_papers,
        "network": build_network_payload(df_ext),
        "impact_ratio": build_impact_ratio_payload(),
        "connectivity": build_connectivity_payload(),
    }

    # Populate by_institute bundles
    for inst_name, inst_key in INST_KEY_MAP.items():
        # Trend
        sub_trend = df_trend[df_trend["institution"] == inst_name].sort_values("year")
        sub_type = df_type[df_type["institution"] == inst_name].sort_values("year")
        trend_merged = []
        for _, tr in sub_trend.iterrows():
            y = tr["year"]
            ty_row = sub_type[sub_type["year"] == y]
            j_cnt = int(ty_row["journal_papers"].iloc[0]) if len(ty_row) > 0 else 0
            c_cnt = int(ty_row["conference_papers"].iloc[0]) if len(ty_row) > 0 else 0
            trend_merged.append({
                "year": int(y),
                "is_partial": bool(tr["is_partial_year"]),
                "total": int(tr["papers"]),
                "journal": j_cnt,
                "conference": c_cnt,
                "yoy_growth_pct": float(tr["yoy_growth_pct"]) if tr["yoy_growth_pct"] != "" else None,
                "cagr_2016_2025": float(tr["cagr_2016_2025"]),
            })

        # Quartiles
        sub_q_all = df_quartile[(df_quartile["institution"] == inst_name) & (df_quartile["period"] == "2016-2026 Overall")]
        sub_q_years = df_quartile[(df_quartile["institution"] == inst_name) & (df_quartile["period"] != "2016-2026 Overall")].sort_values("year")

        q_overall = {}
        if len(sub_q_all) > 0:
            qr = sub_q_all.iloc[0]
            q_overall = {
                "total_journals": int(qr["total_journals"]),
                "q1": int(qr["q1_count"]),
                "q2": int(qr["q2_count"]),
                "q3": int(qr["q3_count"]),
                "q4": int(qr["q4_count"]),
                "unranked": int(qr["unranked_count"]),
                "q1_fraction_primary_pct": float(qr["q1_fraction_primary_pct"]),
                "q1_fraction_all_pct": float(qr["q1_fraction_all_pct"]),
                "quartile_coverage_pct": float(qr["quartile_coverage_pct"]),
            }

        q_yearly = []
        for _, qr in sub_q_years.iterrows():
            q_yearly.append({
                "year": int(qr["year"]),
                "total_journals": int(qr["total_journals"]),
                "q1": int(qr["q1_count"]),
                "q2": int(qr["q2_count"]),
                "q3": int(qr["q3_count"]),
                "q4": int(qr["q4_count"]),
                "unranked": int(qr["unranked_count"]),
                "q1_fraction_primary_pct": float(qr["q1_fraction_primary_pct"]),
            })

        # Citations
        sub_c_all = df_cite[(df_cite["institution"] == inst_name) & (df_cite["period"] == "2016-2026 Overall")]
        c_summary = {}
        if len(sub_c_all) > 0:
            cr = sub_c_all.iloc[0]
            c_summary = {
                "total_citations": int(cr["total_citations"]),
                "mean_citations": float(cr["mean_citations"]),
                "median_citations": float(cr["median_citations"]),
                "p75_citations": float(cr["p75_citations"]),
                "max_citations": int(cr["max_citations"]),
                "uncited_count": int(cr["uncited_count"]),
                "uncited_share_pct": float(cr["uncited_share_pct"]),
            }

        sub_c_years = df_cite[(df_cite["institution"] == inst_name) & (df_cite["period"] != "2016-2026 Overall")].sort_values("year")
        c_yearly = []
        for _, cr in sub_c_years.iterrows():
            c_yearly.append({
                "year": int(cr["year"]),
                "total_citations": int(cr["total_citations"]),
                "mean_citations": float(cr["mean_citations"]),
                "median_citations": float(cr["median_citations"]),
                "uncited_share_pct": float(cr["uncited_share_pct"]),
            })

        # h-index
        sub_h_sum = df_h_sum[df_h_sum["institution"] == inst_name]
        h_sum = {}
        if len(sub_h_sum) > 0:
            hr = sub_h_sum.iloc[0]
            h_sum = {
                "active_faculty_count": int(hr["active_faculty_count"]),
                "mean_h_index": float(hr["mean_h_index"]),
                "median_h_index": float(hr["median_h_index"]),
                "p25_h_index": float(hr["p25_h_index"]),
                "p75_h_index": float(hr["p75_h_index"]),
                "max_h_index": int(hr["max_h_index"]),
            }

        sub_h_bins = df_h_bins[df_h_bins["institution"] == inst_name]
        h_bins = []
        for _, br in sub_h_bins.iterrows():
            h_bins.append({
                "bin_label": br["bin_label"],
                "faculty_count": int(br["faculty_count"]),
                "share_pct": float(br["share_pct"]),
            })

        # Top Journals
        sub_tj = df_top_j[df_top_j["institution"] == inst_name].sort_values("rank")
        top_journals = []
        for _, jr in sub_tj.iterrows():
            top_journals.append({
                "rank": int(jr["rank"]),
                "journal_name": jr["journal_name"],
                "paper_count": int(jr["paper_count"]),
                "share_pct": float(jr["share_pct"]),
                "total_citations": int(jr["total_citations"]),
                "quartile": jr["quartile"],
                "issn": jr["issn"],
            })

        # Top Cited Papers
        sub_tp = df_top_p[df_top_p["institution"] == inst_name].sort_values("rank")
        top_papers = []
        for _, pr in sub_tp.iterrows():
            top_papers.append({
                "rank": int(pr["rank"]),
                "title": pr["title"],
                "journal_name": pr["journal_name"],
                "year": int(pr["year"]),
                "citations": int(pr["citations"]),
                "doi": pr["doi"],
                "quartile": pr["quartile"],
                "in_corpus_authors": pr["in_corpus_authors"],
            })

        # Research Areas
        sub_fields = df_field[df_field["institution"] == inst_name].sort_values("paper_count", ascending=False)
        fields_list = []
        for _, fr in sub_fields.iterrows():
            fields_list.append({
                "field": fr["field"],
                "paper_count": int(fr["paper_count"]),
                "share_pct": float(fr["share_pct"]),
            })

        sub_sf = df_subfield[df_subfield["institution"] == inst_name].sort_values("paper_count", ascending=False)
        subfields_list = []
        for _, sfr in sub_sf.iterrows():
            subfields_list.append({
                "subfield": sfr["subfield"],
                "paper_count": int(sfr["paper_count"]),
                "share_pct": float(sfr["share_pct"]),
            })

        # Faculty list
        if inst_key == "all":
            sub_fac = df_fac
        else:
            sub_fac = df_fac[df_fac["institution"] == inst_name]
        fac_list = []
        for _, fac in sub_fac.iterrows():
            fac_list.append({
                "faculty_id": fac["faculty_id"],
                "name": fac["name"],
                "institution": fac["institution"],
                "department": fac["department"],
                "designation": fac["designation"],
                "papers": int(fac["papers"]),
                "citations": int(fac["citations"]),
                "mean_citations": float(fac["mean_citations_per_paper"]),
                "q1_papers": int(fac["q1_papers"]),
                "q1_share_pct": float(fac["q1_share_pct"]),
                "top_journal": fac["top_journal"],
                "h_index": int(fac["h_index_corpus"]),
                "active_years": fac["active_years"],
            })

        # Departments
        if inst_key == "all":
            sub_dept = df_dept
        else:
            sub_dept = df_dept[df_dept["institution"] == inst_name]
        dept_list = []
        for _, dr in sub_dept.iterrows():
            dept_list.append({
                "institution": dr["institution"],
                "department": dr["department"],
                "total_faculty": int(dr["total_faculty"]),
                "active_faculty": int(dr["active_faculty"]),
                "papers": int(dr["papers"]),
                "citations": int(dr["citations"]),
                "q1_share_pct": float(dr["q1_share_pct"]),
                "mean_h_index": float(dr["mean_faculty_h_index"]),
                "top_field": dr["top_field"],
            })

        # Conference Ranks
        sub_conf = df_conf[df_conf["institution"] == inst_name]
        conf_data = {}
        if len(sub_conf) > 0:
            cnfr = sub_conf.iloc[0]
            conf_data = {
                "total_conferences": int(cnfr["total_conferences"]),
                "core_a_star": int(cnfr["core_a_star"]),
                "core_a": int(cnfr["core_a"]),
                "core_b": int(cnfr["core_b"]),
                "core_c": int(cnfr["core_c"]),
                "unranked": int(cnfr["unranked"]),
                "note": cnfr["note"],
            }

        # Indian Connections
        sub_conn = df_conn[df_conn["institution"] == inst_name]
        conn_data = {}
        if len(sub_conn) > 0:
            cnr = sub_conn.iloc[0]
            conn_data = {
                "total_papers": int(cnr["total_papers"]),
                "papers_with_indian_coauthors": int(cnr["papers_with_indian_coauthors"]),
                "indian_coauthor_pct": float(cnr["indian_coauthor_pct"]),
                "cites_indian_inst_pct": float(cnr["cites_indian_inst_pct"]),
                "cited_by_indian_inst_pct": float(cnr["cited_by_indian_inst_pct"]),
            }

        sub_part = df_partners[df_partners["institution"] == inst_name].sort_values("rank")
        partners_list = []
        for _, prt in sub_part.iterrows():
            partners_list.append({
                "rank": int(prt["rank"]),
                "partner_institution": prt["partner_institution"],
                "collaborative_papers": int(prt["collaborative_papers"]),
                "share_pct": float(prt["share_pct"]),
            })

        payload["by_institute"][inst_key] = {
            "name": inst_name,
            "trend": trend_merged,
            "quartiles": {
                "overall": q_overall,
                "yearly": q_yearly,
            },
            "citations": {
                "overall": c_summary,
                "yearly": c_yearly,
            },
            "h_index": {
                "summary": h_sum,
                "bins": h_bins,
            },
            "top_journals": top_journals,
            "top_papers": top_papers,
            "research_areas": {
                "fields": fields_list,
                "subfields": subfields_list,
            },
            "faculty": fac_list,
            "departments": dept_list,
            "conference_rank": conf_data,
            "indian_connections": {
                "summary": conn_data,
                "top_partners": partners_list,
            },
        }

    # Write out to dashboard/data/g24_data.js
    js_content = f"window.G24_DATA = {json.dumps(payload, indent=2)};\n"
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    logger.info(f"✓ Saved dashboard payload to {OUTPUT_JS} ({OUTPUT_JS.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    run_build_dashboard_data()
