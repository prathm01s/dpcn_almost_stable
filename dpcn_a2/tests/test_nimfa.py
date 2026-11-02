"""Unit tests for Discrete-Time Markov Chain (NIMFA) Spreading Simulation Suite."""

import json
from pathlib import Path
import pandas as pd
import pytest

INSIGHTS_DIR = Path("stats/tables/insights")


def test_nimfa_comparison_json_exists_and_valid():
    path = INSIGHTS_DIR / "11_nimfa_vs_si_comparison.json"
    assert path.exists(), f"Missing {path}"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)

    expected_networks = {"full_authorship", "cadre_authorship", "full_citation", "cadre_citation"}
    assert expected_networks.issubset(set(data.keys()))

    for net_key in expected_networks:
        net_info = data[net_key]
        assert "thresholds" in net_info
        assert "fields" in net_info
        assert len(net_info["fields"]) >= 6

        for field_name, f_data in net_info["fields"].items():
            assert "mc_curve" in f_data
            assert "nimfa_curve" in f_data
            assert "mc_t50" in f_data
            assert "nimfa_t50" in f_data

            mc_c = f_data["mc_curve"]
            nimfa_c = f_data["nimfa_curve"]
            assert len(mc_c) == 16
            assert len(nimfa_c) == 16

            # Monotonicity of SI adoption curves
            for t in range(len(mc_c) - 1):
                assert mc_c[t] <= mc_c[t + 1] + 1e-4, f"Non-monotonic MC curve in {net_key} {field_name}"
                assert nimfa_c[t] <= nimfa_c[t + 1] + 1e-4, f"Non-monotonic NIMFA curve in {net_key} {field_name}"

            # Jensen's inequality: NIMFA mean-field should upper bound or match MC in expectation
            assert f_data["mean_jensen_gap"] >= -1.0, f"Significant negative Jensen gap in {net_key} {field_name}"


def test_simulation_grid_csv():
    path = INSIGHTS_DIR / "11_simulation_grid_metrics.csv"
    assert path.exists(), f"Missing {path}"

    df = pd.read_csv(path)
    assert len(df) >= 24
    assert "network" in df.columns
    assert "field" in df.columns
    assert "mc_t50" in df.columns
    assert "nimfa_t50" in df.columns
    assert "beta_c" in df.columns
    assert "beta_c_spectral" in df.columns

    # Verify Cadre Co-Authorship beta_c is around 0.099
    cadre_rows = df[df["network"].str.contains("Cadre Co-Authorship")]
    assert len(cadre_rows) >= 6
    assert (cadre_rows["beta_c"] > 0.08).all()


def test_seed_origin_and_intra_institute_csvs():
    seed_path = INSIGHTS_DIR / "11_seed_origin_comparison.csv"
    assert seed_path.exists(), f"Missing {seed_path}"
    seed_df = pd.read_csv(seed_path)
    assert len(seed_df) >= 6
    assert set(seed_df["seed_origin_institute"].unique()) == {"CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"}

    intra_path = INSIGHTS_DIR / "11_intra_institute_comparison.csv"
    assert intra_path.exists(), f"Missing {intra_path}"
    intra_df = pd.read_csv(intra_path)
    assert len(intra_df) >= 9
    assert set(intra_df["institute"].unique()) == {"CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"}
    assert set(intra_df["subgraph_type"].unique()) == {"full_authorship", "cadre_authorship", "full_citation"}

