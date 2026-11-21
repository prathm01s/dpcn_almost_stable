"""Automated verification suite for Insight 11 Conclusions (Section 08) and Data/Methodology (Section 09).

Verifies every quantitative claim, conclusion takeaway, metric chip, and navigation target
against the authoritative JSON/CSV files in stats/tables/insights/11_*.
"""

import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

T = Path("stats/tables/insights")


def _load_json(name):
    p = T / name
    assert p.exists(), f"Missing required data table: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def _load_payload():
    path = Path("dashboard/data/g24_insights11_suite.js")
    assert path.exists(), f"Payload file missing: {path}"
    text = path.read_text(encoding="utf-8")
    prefix = "window.G24_I11 = "
    assert text.startswith(prefix)
    return json.loads(text[len(prefix):].rstrip().rstrip(";"))


# ---------------------------------------------------------------- Takeaway 1: Student Multiplier
def test_takeaway_1_student_multiplier():
    """Verify Student Multiplier numbers: nodes, T50, final reach, percolation threshold & outbreak."""
    nim = _load_json("11_nimfa_vs_si_comparison.json")
    thr = _load_json("11_threshold_check.json")["networks"]
    
    full_nodes = nim["full_coauthorship"]["nodes"]
    fac_nodes = nim["faculty_coauthorship"]["nodes"]
    assert full_nodes == 7678, f"Full coauthorship nodes mismatch: {full_nodes}"
    assert fac_nodes == 238, f"Faculty coauthorship nodes mismatch: {fac_nodes}"
    
    full_comb = nim["full_coauthorship"]["fields"]["Combined"]
    fac_comb = nim["faculty_coauthorship"]["fields"]["Combined"]
    
    assert full_comb["mc_t50"] == 9.0, f"Full coauthorship T50 expected 9.0, got {full_comb['mc_t50']}"
    assert fac_comb["mc_t50"] == 12.0, f"Faculty coauthorship T50 expected 12.0, got {fac_comb['mc_t50']}"
    assert full_comb["mc_final_reach"] == 88.88, f"Full final reach expected 88.88, got {full_comb['mc_final_reach']}"
    assert fac_comb["mc_final_reach"] == 64.52, f"Faculty final reach expected 64.52, got {fac_comb['mc_final_reach']}"
    
    # Percolation at T=0.2
    sf = thr["full_coauthorship"]
    sk = thr["faculty_coauthorship"]
    s_full_02 = float(np.interp(0.2, sf["T_grid"], sf["S"]))
    s_fac_02 = float(np.interp(0.2, sk["T_grid"], sk["S"]))
    assert round(s_full_02, 3) == 0.588
    assert round(s_fac_02, 3) == 0.297
    assert sf["T_peak_simulated"] == 0.06
    assert sk["T_peak_simulated"] == 0.215


# ---------------------------------------------------------------- Takeaway 2: Disciplinary Silos
def test_takeaway_2_disciplinary_silos():
    """Verify Disciplinary Silos numbers: in-field reach, outside spillover, and ratio."""
    dif = _load_json("11_information_diffusion.json")
    ch = dif["fields_data"]["Chemistry"]["condition_a"]
    
    in_reach = ch["adoption_curve"][-1]
    spillover = ch["spillover_curve"][-1]
    
    assert in_reach == 76.59, f"Chemistry in-reach expected 76.59, got {in_reach}"
    assert spillover == 2.46, f"Chemistry spillover expected 2.46, got {spillover}"
    
    ratio = in_reach / spillover
    assert ratio > 31.0, f"Expected ratio > 31x, got {ratio:.2f}"


# ---------------------------------------------------------------- Takeaway 3: The Clustering Reality
def test_takeaway_3_clustering_reality():
    """Verify Clustering Reality numbers: all 8 networks formula ratio, clustering coefficients."""
    thr = _load_json("11_threshold_check.json")["networks"]
    ratios = {k: v["peak_over_theory"] for k, v in thr.items()}
    
    assert len(ratios) == 8, f"Expected 8 networks, got {len(ratios)}"
    for net, r in ratios.items():
        assert r > 1.5, f"Expected ratio > 1.5 for {net}, got {r}"
    assert min(ratios.values()) == 1.54, f"Min ratio expected 1.54, got {min(ratios.values())}"
    assert max(ratios.values()) == 2.32, f"Max ratio expected 2.32, got {max(ratios.values())}"
    
    assert thr["full_coauthorship"]["clustering"] == 0.7
    assert thr["faculty_coauthorship"]["clustering"] == 0.317


# ---------------------------------------------------------------- Takeaway 4: Institutional Velocity
def test_takeaway_4_institutional_velocity():
    """Verify Institutional Velocity: step 3 reach for IICT, NCL, CECRI in MC and NIMFA."""
    nim = _load_json("11_nimfa_vs_si_comparison.json")
    so = nim["seed_origins"]["faculty_coauthorship"]
    
    iict_mc3 = so["iict"]["mc_curve"][3]
    ncl_mc3 = so["ncl"]["mc_curve"][3]
    cecri_mc3 = so["cecri"]["mc_curve"][3]
    
    assert iict_mc3 == 5.98, f"IICT MC step 3 expected 5.98, got {iict_mc3}"
    assert ncl_mc3 == 4.92, f"NCL MC step 3 expected 4.92, got {ncl_mc3}"
    assert cecri_mc3 == 1.23, f"CECRI MC step 3 expected 1.23, got {cecri_mc3}"
    
    assert iict_mc3 > ncl_mc3 > cecri_mc3, "Expected order IICT > NCL > CECRI"
    
    iict_nim3 = so["iict"]["nimfa_curve"][3]
    ncl_nim3 = so["ncl"]["nimfa_curve"][3]
    cecri_nim3 = so["cecri"]["nimfa_curve"][3]
    assert iict_nim3 > ncl_nim3 > cecri_nim3, "Expected NIMFA order IICT > NCL > CECRI"
    
    assert so["iict"]["mc_t50"] == 12.0
    assert so["ncl"]["mc_t50"] == 12.0
    assert so["cecri"]["mc_t50"] is None


# ---------------------------------------------------------------- Takeaway 5: NIMFA Validity & Bounds
def test_takeaway_5_nimfa_validity():
    """Verify NIMFA validity: upper bound min/max gap across 28 runs, Spearman rho, citation reach."""
    grid = pd.read_csv(T / "11_simulation_grid_metrics.csv")
    assert len(grid) == 28, f"Expected 28 runs in grid, got {len(grid)}"
    
    min_gap = float(grid["min_gap"].min())
    max_gap = float(grid["max_gap"].max())
    assert min_gap == -0.26, f"Min gap expected -0.26, got {min_gap}"
    assert max_gap == 12.49, f"Max gap expected 12.49, got {max_gap}"
    
    rhos = grid["rank_agreement_spearman"].dropna().tolist()
    assert min(rhos) >= 0.90, f"Min rho expected >= 0.90, got {min(rhos)}"
    assert max(rhos) <= 1.00, f"Max rho expected <= 1.00, got {max(rhos)}"
    assert round(float(np.median(rhos)), 2) == 0.97
    
    nim = _load_json("11_nimfa_vs_si_comparison.json")
    pc = nim["full_citation"]
    assert pc["fields"]["Combined"]["mc_final_reach"] == 1.68
    assert pc["nodes_in_cycles"] == 22


# ---------------------------------------------------------------- All Claims Verification
def test_claims_payload_integrity():
    """Verify that every claim in 11_claims.json (C1-C11 model, C12-C15 real-citation test, D-44) is present, passed and formatted."""
    cl = _load_json("11_claims.json")
    assert cl["n_claims"] == 15
    assert cl["n_passed"] == 15

    c_ids = [c["id"] for c in cl["claims"]]
    assert c_ids == [f"C{i}" for i in range(1, 16)]
    for c in cl["claims"]:
        assert c["passed"] is True, f"Claim {c['id']} did not pass"
        assert c["claim"], f"Claim {c['id']} missing text"
        assert c["source"], f"Claim {c['id']} missing source"
        assert c["value"] is not None, f"Claim {c['id']} missing value payload"


# ---------------------------------------------------------------- DOM & Navigation Structure
def test_insights11_html_navigation_and_section_structure():
    """Verify HTML nav links, section IDs, and sequence 00 through 10 in insights11.html."""
    html_path = Path("dashboard/insights11.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8")
    
    # Check topnav links
    expected_nav_links = [
        "#i-top", "#i-findings", "#i-data", "#i-model", "#i-threshold",
        "#i-fields", "#i-networks", "#i-meanfield", "#i-labs", "#i-real",
        "#i-conclusions", "#i-proof"
    ]
    for target in expected_nav_links:
        assert f'href="{target}"' in content, f"Nav link {target} missing in insights11.html"
        section_id = target.lstrip("#")
        assert f'id="{section_id}"' in content, f"Target section id='{section_id}' missing in insights11.html"
    
    # Check section numbers 00 through 10
    for i in range(11):
        expected_badge = f'<span class="section-num">{i:02d}</span> / 10'
        assert expected_badge in content, f"Missing section badge '{expected_badge}' in insights11.html"
