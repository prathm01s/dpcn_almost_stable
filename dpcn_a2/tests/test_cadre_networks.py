"""Unit tests for Cadre Networks extraction and Data Cleaning Provenance audit."""

import json
from pathlib import Path
import pandas as pd
import pytest

INSIGHTS_DIR = Path("stats/tables/insights")


def test_cadre_networks_summary_csv():
    path = INSIGHTS_DIR / "11_cadre_networks_summary.csv"
    assert path.exists(), f"Missing {path}"

    df = pd.read_csv(path)
    assert len(df) == 4
    assert set(df["network"]) == {
        "Full Co-Authorship",
        "Cadre Co-Authorship",
        "Full Citation",
        "Cadre Faculty Citation"
    }

    # The cadre networks must equal the faculty networks in stats/tables/network_summary.csv (D-33):
    # both are built by src/stats/networks.py with one node per roster scientist.
    ns = pd.read_csv("stats/tables/network_summary.csv")
    val = lambda net, metric: float(ns[(ns["network"] == net) & (ns["metric"] == metric)]["value"].iloc[0])
    row_cadre = df[df["network"] == "Cadre Co-Authorship"].iloc[0]
    assert int(row_cadre["nodes"]) == val("faculty_coauthorship", "scientists with >= 1 faculty co-author")
    assert int(row_cadre["edges"]) == val("faculty_coauthorship", "co-author pairs (unique edges)")
    row_cite = df[df["network"] == "Cadre Faculty Citation"].iloc[0]
    assert int(row_cite["nodes"]) == val("faculty_citation", "scientists citing or cited by another scientist")
    assert int(row_cite["edges"]) == val("faculty_citation", "directed edges (scientist A cites scientist B)")
    # the full networks are computed, not typed in
    row_full = df[df["network"] == "Full Co-Authorship"].iloc[0]
    assert int(row_full["nodes"]) == val("authorship", "largest connected component (authors)")
    row_fc = df[df["network"] == "Full Citation"].iloc[0]
    assert int(row_fc["nodes"]) == val("citation", "nodes (papers with >= 1 in-corpus link)")
    assert int(row_fc["edges"]) == val("citation", "distinct citing-cited paper pairs")


def test_cadre_graph_jsons():
    auth_path = INSIGHTS_DIR / "11_cadre_coauthorship_graph.json"
    cite_path = INSIGHTS_DIR / "11_cadre_citation_graph.json"
    assert auth_path.exists()
    assert cite_path.exists()

    auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
    assert "nodes" in auth_data
    assert "links" in auth_data
    assert "metrics" in auth_data
    assert len(auth_data["nodes"]) > 50

    cite_data = json.loads(cite_path.read_text(encoding="utf-8"))
    assert "nodes" in cite_data
    assert "links" in cite_data
    assert "metrics" in cite_data
    assert len(cite_data["nodes"]) > 50


def test_data_cleaning_audit_json():
    path = INSIGHTS_DIR / "11_data_cleaning_stats.json"
    assert path.exists(), f"Missing {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "funnel" in data
    f = data["funnel"]

    # Exact numbers verification
    assert f["stage_1_raw_scraped"]["total"] == 505
    assert f["stage_2_excluded_technical_and_duplicates"]["total_excluded"] == 123  # + 3 page-text entries (D-40)
    assert f["stage_2_excluded_technical_and_duplicates"]["technical_staff_excluded"] == 119
    assert f["stage_3_clean_roster"]["total"] == 382
    assert f["stage_4_active_cadre_with_papers"]["total"] == 306

    # Breakdown by institute
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-IICT"] == 168
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-NCL"] == 166
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-CECRI"] == 48

    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-IICT"] == 129
    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-NCL"] == 151
    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-CECRI"] == 26
