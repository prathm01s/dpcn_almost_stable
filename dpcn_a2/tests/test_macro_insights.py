"""Unit tests for the 5 Macro & Comparative Insight Studies (Group 24)."""

import json
from pathlib import Path
import pytest

DATA_DIR = Path("stats/tables/macro_insights")
JS_DIR = Path("dashboard/data")


def test_smart_specialization_data():
    json_path = DATA_DIR / "21_smart_specialization.json"
    assert json_path.exists(), f"Missing {json_path}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "state_economic_data" in data
    assert "matched_synergies" in data
    assert len(data["matched_synergies"]) == 3
    
    # Assert RCA and LQ mathematical bounds
    for row in data["matched_synergies"]:
        assert row["lab_rca"] > 0, "RCA must be strictly positive"
        assert row["state_lq"] > 0, "Location Quotient must be strictly positive"
        assert row["paper_share_pct"] > 0, "Paper share must be strictly positive"

    # Specific scientific assertions
    iict_row = [r for r in data["matched_synergies"] if r["institution"] == "CSIR-IICT"][0]
    cecri_row = [r for r in data["matched_synergies"] if r["institution"] == "CSIR-CECRI"][0]
    ncl_row = [r for r in data["matched_synergies"] if r["institution"] == "CSIR-NCL"][0]
    
    assert iict_row["state_lq"] > 3.0, "Telangana pharma LQ should exceed 3.0"
    assert cecri_row["lab_rca"] > 2.0, "CECRI electrochemistry RCA should exceed 2.0"
    assert ncl_row["state_lq"] > 1.2, "Maharashtra chemical LQ should exceed 1.2"


def test_academic_bridge_data():
    json_path = DATA_DIR / "11_academic_bridge.json"
    assert json_path.exists(), f"Missing {json_path}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "institutions_evaluated" in data
    assert len(data["institutions_evaluated"]) >= 12
    
    for item in data["institutions_evaluated"]:
        assert item["ker"] >= 0, "KER must be non-negative"
        assert item["c_in_received_from_hei"] >= 0
        assert item["c_out_sent_to_hei"] >= 0
        assert item["exchange_role"] in ["Net Knowledge Exporter", "Net Knowledge Importer"]

    # Verify key role relationships
    by_name = {item["academic_institution"]: item for item in data["institutions_evaluated"]}
    assert by_name["IIT Hyderabad"]["ker"] > 1.5, "IIT Hyderabad should be net exporter from CSIR"
    assert by_name["IISc Bangalore"]["ker"] < 0.6, "IISc should be net importer to CSIR"
    assert by_name["Alagappa University"]["ker"] > 1.2, "Alagappa Univ should be net exporter from CSIR"


def test_frugal_innovation_data():
    json_path = DATA_DIR / "51_frugal_innovation.json"
    assert json_path.exists(), f"Missing {json_path}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "global_benchmarks" in data
    benchmarks = {b["organization"]: b for b in data["global_benchmarks"]}
    
    csir = benchmarks["CSIR Chemistry Cluster (Group 24)"]
    max_planck = benchmarks["Max Planck Society (MPI Chemistry/Energy)"]
    us_doe = benchmarks["US DOE Ames National Laboratory"]
    
    # Capital efficiency multiplier assertions
    assert csir["cost_per_q1_nominal_usd"] < max_planck["cost_per_q1_nominal_usd"] / 3
    assert csir["cost_per_q1_nominal_usd"] < us_doe["cost_per_q1_nominal_usd"] / 5
    assert csir["gerd_gdp_pct"] == 0.65
    assert csir["cost_per_citation_usd"] < 25.0


def test_patents_vs_papers_data():
    json_path = DATA_DIR / "52_patents_vs_papers.json"
    assert json_path.exists(), f"Missing {json_path}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "lab_patent_totals" in data
    assert "quadrant_distribution" in data
    assert "faculty_scatter" in data
    assert len(data["faculty_scatter"]) >= 250
    
    # Assert all 4 quadrants populated
    quads = {q["quadrant"]: q["faculty_count"] for q in data["quadrant_distribution"]}
    assert len(quads) == 4
    for q_name, count in quads.items():
        assert count > 20, f"Quadrant {q_name} must have substantive representation"

    for f in data["faculty_scatter"]:
        assert f["patents_total"] == f["patents_domestic"] + f["patents_foreign"]


def test_leiden_benchmarks_data():
    json_path = DATA_DIR / "31_leiden_benchmarks.json"
    assert json_path.exists(), f"Missing {json_path}"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    
    assert "cluster_consolidated" in data
    cluster = data["cluster_consolidated"]
    
    assert cluster["pp_top10_pct"] > 10.0, "CSIR top 10% share should exceed world baseline (10%)"
    assert cluster["pp_top1_pct"] > 1.0, "CSIR top 1% share should exceed world baseline (1%)"
    assert 0.90 <= cluster["mncs"] <= 1.15, "CSIR MNCS should be near world average parity (1.0)"
    
    # Assert lab results
    for lab in data["lab_results"]:
        assert lab["pp_top10_pct"] > 12.0
        assert lab["total_papers_evaluated"] > 2000


def test_js_bundles_offline_ready():
    bundle_files = [
        ("g24_smart_spec.js", "window.G24_SMART_SPEC_DATA"),
        ("g24_academic_bridge.js", "window.G24_ACADEMIC_BRIDGE_DATA"),
        ("g24_frugal_rd.js", "window.G24_FRUGAL_RD_DATA"),
        ("g24_patents_papers.js", "window.G24_PATENTS_PAPERS_DATA"),
        ("g24_leiden_benchmarks.js", "window.G24_LEIDEN_BENCHMARKS_DATA")
    ]
    for filename, window_var in bundle_files:
        path = JS_DIR / filename
        assert path.exists(), f"Missing JS bundle {path}"
        content = path.read_text(encoding="utf-8")
        assert len(content) > 1000, f"Bundle {filename} too small"
        assert window_var in content, f"Bundle {filename} does not set {window_var}"
