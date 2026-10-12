"""Automated consistency checks ensuring metrics tables, report, and dashboard agree."""

import json
from pathlib import Path
import pandas as pd
import pytest


def test_metric_tables_exist():
    required_tables = [
        "publication_trend.csv",
        "publication_trend_type.csv",
        "quartile_distribution.csv",
        "citation_summary.csv",
        "h_index_summary.csv",
        "h_index_distribution.csv",
        "top_journals.csv",
        "top_cited_papers.csv",
        "research_areas_field.csv",
        "faculty_performance.csv",
        "department_performance.csv",
        "conference_ranks.csv",
        "indian_connections_summary.csv",
    ]
    for table_name in required_tables:
        p = Path("stats/tables") / table_name
        assert p.exists(), f"Required metrics table {table_name} missing"


def test_dashboard_json_consistency():
    js_path = Path("dashboard/data/g24_data.js")
    assert js_path.exists(), "g24_data.js missing"

    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()

    prefix = "window.G24_DATA = "
    assert content.startswith(prefix)
    json_str = content[len(prefix):].rstrip(";\n")
    data = json.loads(json_str)

    # Check structure
    assert data["meta"]["group"] == 24
    assert "by_institute" in data
    assert set(data["by_institute"].keys()) == {"all", "iict", "ncl", "cecri"}

    # Compare IICT total papers between publication_trend.csv and dashboard
    df_trend = pd.read_csv("stats/tables/publication_trend.csv")
    iict_trend_sum = df_trend[df_trend["institution"] == "CSIR-IICT"]["papers"].sum()
    dashboard_iict_sum = sum(t["total"] for t in data["by_institute"]["iict"]["trend"])
    assert iict_trend_sum == dashboard_iict_sum

    # Compare NCL total papers
    ncl_trend_sum = df_trend[df_trend["institution"] == "CSIR-NCL"]["papers"].sum()
    dashboard_ncl_sum = sum(t["total"] for t in data["by_institute"]["ncl"]["trend"])
    assert ncl_trend_sum == dashboard_ncl_sum

    # Compare CECRI total papers
    cecri_trend_sum = df_trend[df_trend["institution"] == "CSIR-CECRI"]["papers"].sum()
    dashboard_cecri_sum = sum(t["total"] for t in data["by_institute"]["cecri"]["trend"])
    assert cecri_trend_sum == dashboard_cecri_sum

    # Compare Q1 fraction
    df_q = pd.read_csv("stats/tables/quartile_distribution.csv")
    q_all = df_q[(df_q["institution"] == "Group 24 Combined") & (df_q["period"] == "2016-2026 Overall")].iloc[0]
    dash_q1_pct = data["by_institute"]["all"]["quartiles"]["overall"]["q1_fraction_primary_pct"]
    assert float(q_all["q1_fraction_primary_pct"]) == pytest.approx(dash_q1_pct, 0.01)


def test_report_artifacts_exist():
    assert Path("stats/report/group24_stats_report.pptx").exists()
    assert Path("stats/report/group24_stats_report.pdf").exists()
    for i in range(1, 9):
        assert Path(f"stats/figures/fig{i}_*.png") or any(Path("stats/figures").glob(f"fig{i}_*.png"))
