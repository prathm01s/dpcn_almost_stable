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

    # Verify Cadre Co-Authorship has 235 connected nodes
    row_cadre = df[df["network"] == "Cadre Co-Authorship"].iloc[0]
    assert int(row_cadre["nodes"]) == 235
    assert int(row_cadre["edges"]) == 579
    assert float(row_cadre["beta_c"]) > 0.08

    # Verify Faculty-to-Faculty citation has 245 nodes and 1,610 edges
    row_cite = df[df["network"] == "Cadre Faculty Citation"].iloc[0]
    assert int(row_cite["nodes"]) == 245
    assert int(row_cite["edges"]) == 1610


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
    assert f["stage_2_excluded_technical_and_duplicates"]["total_excluded"] == 120
    assert f["stage_2_excluded_technical_and_duplicates"]["technical_staff_excluded"] == 119
    assert f["stage_3_clean_roster"]["total"] == 385
    assert f["stage_4_active_cadre_with_papers"]["total"] == 306

    # Breakdown by institute
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-IICT"] == 168
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-NCL"] == 166
    assert f["stage_3_clean_roster"]["by_lab"]["CSIR-CECRI"] == 51

    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-IICT"] == 129
    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-NCL"] == 151
    assert f["stage_4_active_cadre_with_papers"]["by_lab"]["CSIR-CECRI"] == 26
