"""Output checks for the NIMFA / Monte Carlo spreading suite (s11_nimfa_spreading.py, D-38 names)."""

import json
from pathlib import Path

import pandas as pd

INSIGHTS_DIR = Path("stats/tables/insights")
NETWORKS = {"full_coauthorship", "faculty_coauthorship", "full_citation", "faculty_citation"}


def test_nimfa_comparison_json_exists_and_valid():
    data = json.loads((INSIGHTS_DIR / "11_nimfa_vs_si_comparison.json").read_text(encoding="utf-8"))
    assert NETWORKS.issubset(data)
    steps = data["parameters"]["max_steps"]
    for net_key in NETWORKS:
        net = data[net_key]
        assert "thresholds" in net and len(net["fields"]) >= 6
        for field, f in net["fields"].items():
            mc, nim = f["mc_curve"], f["nimfa_curve"]
            assert len(mc) == len(nim) == steps + 1
            # SI adoption never decreases
            assert all(mc[t] <= mc[t + 1] + 1e-4 for t in range(steps)), (net_key, field)
            assert all(nim[t] <= nim[t + 1] + 1e-4 for t in range(steps)), (net_key, field)
            # mean field does not predict less spreading than the simulation (beyond Monte Carlo noise)
            assert f["min_gap"] >= -1.0, (net_key, field)


def test_simulation_grid_csv():
    df = pd.read_csv(INSIGHTS_DIR / "11_simulation_grid_metrics.csv")
    assert len(df) == 4 * 7
    for col in ("network", "field", "mc_t50", "nimfa_t50", "beta_c_hmf", "beta_c_qmf", "min_gap", "rank_agreement_spearman"):
        assert col in df.columns
    fac = df[df["network"] == "faculty_coauthorship"]
    assert len(fac) == 7 and (fac["beta_c_hmf"] > 0.08).all()
    # undirected networks have the degree formula, directed ones only the spectral one
    assert df[df["network"].str.endswith("citation")]["beta_c_hmf"].isna().all()


def test_seed_origin_and_intra_institute_csvs():
    seed_df = pd.read_csv(INSIGHTS_DIR / "11_seed_origin_comparison.csv")
    assert len(seed_df) == 6
    assert set(seed_df["seed_origin_institute"]) == {"CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"}
    intra_df = pd.read_csv(INSIGHTS_DIR / "11_intra_institute_comparison.csv")
    assert len(intra_df) == 9
    assert set(intra_df["institute"]) == {"CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"}
    assert set(intra_df["subgraph_type"]) == {"full_coauthorship", "faculty_coauthorship", "full_citation"}
