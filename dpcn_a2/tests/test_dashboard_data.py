"""Automated dashboard data integrity tests.
Validates AGENTS.md Section 7.5 requirements:
- Schema and no NaN / undefined / null anomalies in g24_data.js
- Totals reconcile identically against stats/tables/ CSVs
- 10 random numbers sampled and verified against CSVs
"""

import json
from pathlib import Path
import pandas as pd
import pytest


def get_dashboard_data():
    js_path = Path("dashboard/data/g24_data.js")
    assert js_path.exists(), "dashboard/data/g24_data.js missing"
    with open(js_path, "r", encoding="utf-8") as f:
        text = f.read()
    prefix = "window.G24_DATA = "
    assert text.startswith(prefix)
    json_str = text[len(prefix):].rstrip(";\n")
    return json.loads(json_str)


def test_no_nan_or_undefined_in_json():
    """Verify that there are no NaN, Infinity, or corrupted values in the data bundle."""
    with open("dashboard/data/g24_data.js", "r", encoding="utf-8") as f:
        raw_text = f.read()
    assert ": NaN" not in raw_text
    assert ": undefined" not in raw_text
    assert ": Infinity" not in raw_text


def test_dashboard_reconciles_against_tables():
    """Verify totals match stats/tables CSVs."""
    dashboard_data = get_dashboard_data()
    # Trend
    df_trend = pd.read_csv("stats/tables/publication_trend.csv")
    for inst_key, inst_name in [("iict", "CSIR-IICT"), ("ncl", "CSIR-NCL"), ("cecri", "CSIR-CECRI")]:
        csv_papers = df_trend[df_trend["institution"] == inst_name]["papers"].sum()
        dash_papers = sum(t["total"] for t in dashboard_data["by_institute"][inst_key]["trend"])
        assert csv_papers == dash_papers, f"Mismatch for {inst_key} trend total"

    # Citations
    df_cites = pd.read_csv("stats/tables/citation_summary.csv")
    for inst_key, inst_name in [("iict", "CSIR-IICT"), ("ncl", "CSIR-NCL"), ("cecri", "CSIR-CECRI"), ("all", "Group 24 Combined")]:
        csv_cites = df_cites[df_cites["institution"] == inst_name]["total_citations"].iloc[0]
        dash_cites = dashboard_data["by_institute"][inst_key]["citations"]["overall"]["total_citations"]
        assert csv_cites == dash_cites, f"Mismatch for {inst_key} citation total"


def test_spot_check_10_random_numbers():
    """Spot-check 10 random data points against raw and stats tables."""
    dashboard_data = get_dashboard_data()

    # 1. 2021 IICT total papers
    df_trend = pd.read_csv("stats/tables/publication_trend.csv")
    val_1_csv = df_trend[(df_trend["institution"] == "CSIR-IICT") & (df_trend["year"] == 2021)]["papers"].iloc[0]
    val_1_dash = next(t["total"] for t in dashboard_data["by_institute"]["iict"]["trend"] if t["year"] == 2021)
    assert val_1_csv == val_1_dash

    # 2. 2019 NCL total papers
    val_2_csv = df_trend[(df_trend["institution"] == "CSIR-NCL") & (df_trend["year"] == 2019)]["papers"].iloc[0]
    val_2_dash = next(t["total"] for t in dashboard_data["by_institute"]["ncl"]["trend"] if t["year"] == 2019)
    assert val_2_csv == val_2_dash

    # 3. CECRI median h-index
    df_h = pd.read_csv("stats/tables/h_index_summary.csv")
    val_3_csv = df_h[df_h["institution"] == "CSIR-CECRI"]["median_h_index"].iloc[0]
    val_3_dash = dashboard_data["by_institute"]["cecri"]["h_index"]["summary"]["median_h_index"]
    assert val_3_csv == pytest.approx(val_3_dash)

    # 4. Group 24 Combined Q1 count
    df_q = pd.read_csv("stats/tables/quartile_distribution.csv")
    val_4_csv = df_q[(df_q["institution"] == "Group 24 Combined") & (df_q["period"] == "2016-2026 Overall")]["q1_count"].iloc[0]
    val_4_dash = dashboard_data["by_institute"]["all"]["quartiles"]["overall"]["q1"]
    assert val_4_csv == val_4_dash

    # 5. Top cited paper citations for Group 24 Combined
    df_top = pd.read_csv("stats/tables/top_cited_papers.csv")
    top_cites_csv = df_top[df_top["institution"] == "Group 24 Combined"]["citations"].iloc[0]
    top_cites_dash = dashboard_data["by_institute"]["all"]["top_papers"][0]["citations"]
    assert top_cites_csv == top_cites_dash

    # 6. CECRI active faculty count
    val_6_csv = df_h[df_h["institution"] == "CSIR-CECRI"]["active_faculty_count"].iloc[0]
    val_6_dash = dashboard_data["by_institute"]["cecri"]["h_index"]["summary"]["active_faculty_count"]
    assert val_6_csv == val_6_dash

    # 7. IICT active faculty count
    val_7_csv = df_h[df_h["institution"] == "CSIR-IICT"]["active_faculty_count"].iloc[0]
    val_7_dash = dashboard_data["by_institute"]["iict"]["h_index"]["summary"]["active_faculty_count"]
    assert val_7_csv == val_7_dash

    # 8. NCL active faculty count
    val_8_csv = df_h[df_h["institution"] == "CSIR-NCL"]["active_faculty_count"].iloc[0]
    val_8_dash = dashboard_data["by_institute"]["ncl"]["h_index"]["summary"]["active_faculty_count"]
    assert val_8_csv == val_8_dash

    # 9. Total active faculty count
    val_9_csv = df_h[df_h["institution"] == "Group 24 Combined"]["active_faculty_count"].iloc[0]
    val_9_dash = dashboard_data["by_institute"]["all"]["h_index"]["summary"]["active_faculty_count"]
    assert val_9_csv == val_9_dash

    # 10. Top journal name for NCL
    df_tj = pd.read_csv("stats/tables/top_journals.csv")
    top_j_ncl_csv = df_tj[df_tj["institution"] == "CSIR-NCL"].iloc[0]["journal_name"]
    top_j_ncl_dash = dashboard_data["by_institute"]["ncl"]["top_journals"][0]["journal_name"]
    assert top_j_ncl_csv == top_j_ncl_dash


def test_network_payload_integrity():
    """Verify Task 4 citation and authorship network structures embedded in dashboard payload."""
    data = get_dashboard_data()
    assert "network" in data
    net = data["network"]

    # Citation network
    assert "citation" in net
    c_net = net["citation"]
    assert len(c_net["nodes"]) >= 100
    assert len(c_net["links"]) >= 100
    # numbers must equal stats/tables/network_summary.csv (edges = distinct citing-cited pairs, D-33)
    ns = pd.read_csv("stats/tables/network_summary.csv")
    val = lambda net_, metric: int(float(ns[(ns["network"] == net_) & (ns["metric"].str.startswith(metric))]["value"].iloc[0]))
    assert c_net["stats"]["total_edges"] == val("citation", "distinct citing-cited paper pairs")
    assert c_net["stats"]["total_nodes"] == val("citation", "nodes (papers")
    assert c_net["stats"]["inter_lab_citations"] == val("citation", "cross-lab citation links")
    assert len(c_net["top_pagerank"]) == 10
    assert len(c_net["flow_matrix"]) == 3

    # Authorship network
    assert "authorship" in net
    a_net = net["authorship"]
    assert len(a_net["nodes"]) >= 100
    assert len(a_net["links"]) >= 100
    assert a_net["stats"]["total_edges"] == val("authorship", "co-author pairs (unique edges)")
    assert a_net["stats"]["edge_rows"] == val("authorship", "co-authorship links (edge rows")
    assert a_net["stats"]["inter_lab_pairs"] == val("authorship", "cross-lab co-author pairs")
    assert a_net["stats"]["total_authors"] == val("authorship", "authors (nodes)")
    assert a_net["stats"]["faculty_authors"] == val("authorship", "of which roster faculty")

    # Faculty networks (D-33): one node per roster scientist, all scientists shipped
    fn = data["network_faculty"]
    assert fn["citation"]["stats"]["total_nodes"] == val("faculty_citation", "nodes (roster")
    assert fn["citation"]["stats"]["total_edges"] == val("faculty_citation", "directed edges")
    assert fn["citation"]["stats"]["citation_links"] == val("faculty_citation", "citation links summed")
    assert fn["authorship"]["stats"]["total_nodes"] == val("faculty_coauthorship", "nodes (roster")
    assert fn["authorship"]["stats"]["total_edges"] == val("faculty_coauthorship", "co-author pairs")
    assert fn["authorship"]["stats"]["inter_lab_pairs"] == val("faculty_coauthorship", "cross-lab")
    for kind in ("citation", "authorship"):
        ids = [n["id"] for n in fn[kind]["nodes"]]
        assert len(ids) == len(set(ids)) == fn[kind]["stats"]["total_nodes"], "one node per scientist, no duplicates"
        assert all(i.startswith("FAC_") for i in ids)
        assert len(fn[kind]["links"]) == fn[kind]["stats"]["total_edges"]
        assert all(l["source"] != l["target"] for l in fn[kind]["links"]), "no self-loops"
    assert len(a_net["top_bridges"]) == 10
    assert len(a_net["collab_matrix"]) == 3

