"""Master runner for the Group 24 Insights analyses.

Executes s01-s06, s08, s09 and s11 in order, writing each output JSON to stats/tables/insights/.
Sleeping beauties (s07) and Succession risk (s10) were removed after the instructor review (D-37).
Runs from local data only: Insight 9 reads the OpenAlex cache written by `make insights-fetch`;
if it is missing it writes a "Not computed" JSON instead.
"""

import sys
from pathlib import Path
from src.common.logging import get_logger

logger = get_logger("insights_run_all")


def run_insight11() -> None:
    """Insight 11 (D-38), from data/final only: faculty networks and roster audit, part 1 field study,
    part 2 four networks / mean field / labs, part 3 threshold test, part 4 claims, then the page data."""
    from src.stats.insights.s11_cadre_networks import extract_cadre_networks
    from src.stats.insights.s11_data_cleaning_audit import audit_data_cleaning
    from src.stats.insights.s11_information_diffusion import run as run_diffusion
    from src.stats.insights.s11_nimfa_spreading import run_all_simulations
    from src.stats.insights.s11_threshold_check import run_threshold_check
    from src.stats.insights.s11_claims import build_claims
    from src.dashboard.build_insights11_suite import build_suite_js
    extract_cadre_networks()
    audit_data_cleaning()
    run_diffusion()
    run_all_simulations()
    run_threshold_check()
    claims = build_claims()
    build_suite_js()
    if claims["n_passed"] != claims["n_claims"]:
        logger.warning(f"Insight 11: only {claims['n_passed']}/{claims['n_claims']} claims pass; see 11_claims.json")


def run_all() -> None:
    logger.info("================================================================================")
    logger.info("Starting Group 24 Insights Pipeline (9 analyses)")
    logger.info("================================================================================")

    # 1. Friendship Paradox
    from src.stats.insights.s01_friendship_paradox import run as run_01
    run_01()

    # 2. Rich Club
    from src.stats.insights.s02_rich_club import run as run_02
    run_02()

    # 3. Fragility
    from src.stats.insights.s03_fragility import run as run_03
    run_03()

    # 4. Price's Law
    from src.stats.insights.s04_price_law import run as run_04
    run_04()

    # 5. Quartile vs Impact
    from src.stats.insights.s05_quartile_vs_impact import run as run_05
    run_05()

    # 6. PageRank vs Citations
    from src.stats.insights.s06_pagerank_vs_citations import run as run_06
    run_06()

    # 8. COVID Shock
    from src.stats.insights.s08_covid_shock import run as run_08
    run_08()

    # 9. Brain Circulation
    from src.stats.insights.s09_brain_circulation import run as run_09
    run_09()

    # 11. How ideas spread: the full study on its own page (field study, four networks, threshold test, claims)
    run_insight11()

    logger.info("================================================================================")
    logger.info("✓ Completed all 9 Insights analyses. Outputs saved in stats/tables/insights/")
    logger.info("================================================================================")



if __name__ == "__main__":
    run_all()
