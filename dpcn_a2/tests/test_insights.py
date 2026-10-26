"""Unit and integration tests for the Group 24 Insights analyses (s01-s10).

Covers:
1. Schema and contract compliance of all 10 insight JSON files.
2. Mathematical verification of Ke et al. (2015) Sleeping Beauty B-coefficient.
3. Gini coefficient and Price's Law calculations.
4. Friendship paradox network invariants.
5. Brain circulation validation sample structure.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

INSIGHTS_DIR = Path("stats/tables/insights")
INSIGHT_IDS = [
    "01_friendship_paradox",
    "02_rich_club",
    "03_fragility",
    "04_price_law",
    "05_quartile_vs_impact",
    "06_pagerank_vs_citations",
    "07_sleeping_beauties",
    "08_covid_shock",
    "09_brain_circulation",
    "10_succession_risk",
]

REQUIRED_KEYS = {
    "id",
    "question",
    "headline",
    "metrics",
    "chart",
    "method_note",
    "computed_at",
}


def test_all_insight_files_exist_and_conform_to_schema():
    """Verify each of the 10 insight JSON files exists and has all required contract fields."""
    for insight_id in INSIGHT_IDS:
        filepath = INSIGHTS_DIR / f"{insight_id}.json"
        assert filepath.exists(), f"Missing insight file: {filepath}"
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{insight_id} missing required keys: {missing}"

        assert isinstance(data["metrics"], dict)
        assert len(data["metrics"]) > 0, f"{insight_id} metrics cannot be empty"

        assert isinstance(data["chart"], dict)
        assert "type" in data["chart"]
        assert "data" in data["chart"]

        assert len(data["headline"]) > 10
        assert len(data["method_note"]) > 10


def test_sleeping_beauty_ke_formula():
    """Verify Ke et al. (2015) B-coefficient calculation on synthetic citation curves."""
    from src.stats.insights.s07_sleeping_beauties import compute_sleeping_beauty

    # Case 1: Early peak (within 2 years) -> filtered out per definition
    early_cites = {2016: 50, 2017: 40, 2018: 10, 2019: 5, 2020: 2}
    res_early = compute_sleeping_beauty(2016, early_cites)
    assert res_early == {}, "Early peak papers should not be classified as sleeping beauties"

    # Case 2: Classic Sleeping Beauty: flat/low citations for years, then large spike
    sb_cites = {
        2016: 1,
        2017: 0,
        2018: 1,
        2019: 0,
        2020: 2,
        2021: 45,
        2022: 70,
        2023: 30,
        2024: 15,
        2025: 10,
        2026: 5,
    }
    res_sb = compute_sleeping_beauty(2016, sb_cites)
    assert res_sb != {}, "Clear sleeping beauty pattern should be detected"
    assert res_sb["B"] > 5.0
    assert res_sb["awakening_year"] in [2020, 2021, 2022]
    assert res_sb["avg_post"] > res_sb["avg_pre"]



def test_gini_and_price_law():
    """Verify Gini calculation and Price's square-root law implementation."""
    from src.stats.insights.s04_price_law import gini

    # Perfect equality
    equal_vals = np.array([10.0, 10.0, 10.0, 10.0, 10.0])
    assert abs(gini(equal_vals)) < 1e-6

    # Extreme inequality: 1 person has everything
    unequal_vals = np.array([0.0, 0.0, 0.0, 0.0, 100.0])
    # For N=5, (5-1)/5 = 0.8
    assert abs(gini(unequal_vals) - 0.8) < 1e-5

    # Check Price's law insight values
    p4_path = INSIGHTS_DIR / "04_price_law.json"
    with open(p4_path) as f:
        p4 = json.load(f)
    m = p4["metrics"]
    assert m["N_active_faculty"] == 344
    assert m["n_sqrt"] == 19  # ceil(sqrt(344)) = 19
    assert m["gini_papers"] > 0.5
    assert m["gini_citations"] > m["gini_papers"]


def test_friendship_paradox_results():
    """Check friendship paradox metrics have expected relations."""
    p1_path = INSIGHTS_DIR / "01_friendship_paradox.json"
    with open(p1_path) as f:
        p1 = json.load(f)
    m = p1["metrics"]
    assert m["share_paradox"] > 90.0
    assert m["mean_neighbour_k"] > m["mean_k"]


def test_brain_circulation_validation_sample():
    """Verify the 30-scientist validation sample CSV was exported properly."""
    sample_csv = INSIGHTS_DIR / "09_validation_sample.csv"
    assert sample_csv.exists()
    df = pd.read_csv(sample_csv)
    assert len(df) == 30
    req_cols = {"name", "lab", "predicted_class", "phd_proxy", "host_country", "profile_url"}
    assert req_cols.issubset(df.columns)
    assert df["predicted_class"].isin(["Home-grown", "Returnee", "Foreign-trained", "Unclassifiable"]).all()


def test_headlines_have_no_invented_fallbacks():
    """Headlines must not contain placeholder values that are not in the metrics."""
    for f in Path("stats/tables/insights").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert "N/A" not in d["headline"], f.name
        assert "Not computed" not in d["headline"], f"{f.name}: run make insights-fetch before make insights"


def test_rich_club_uses_top_set_threshold():
    d = json.loads(Path("stats/tables/insights/02_rich_club.json").read_text(encoding="utf-8"))
    assert d["metrics"]["rho_norm_at_k_star"] is not None


def test_sleeping_beauty_ignores_partial_year_and_tiny_peaks():
    from src.stats.insights.s07_sleeping_beauties import compute_sleeping_beauty
    # Peak of 5 citations: too small to count, however late it comes
    assert compute_sleeping_beauty(2016, {2016: 0, 2017: 0, 2018: 0, 2019: 0, 2020: 5, 2021: 5, 2022: 5, 2023: 5}) == {}
    # A big 2026 (partial-year) value must not become the peak
    res = compute_sleeping_beauty(2016, {2016: 5, 2017: 6, 2018: 8, 2019: 9, 2020: 12, 2021: 14, 2026: 90})
    assert res == {} or res["peak_year"] <= 2025
