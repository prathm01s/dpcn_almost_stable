"""Master runner for all 10 Group 24 Insights analyses.

Executes s01 to s10 in order, writing each output JSON to stats/tables/insights/.
Runs from local data only: Insights 7, 9 and 10 read the OpenAlex caches written by
`make insights-fetch`; if those are missing they write a "Not computed" JSON instead.
"""

import sys
from pathlib import Path
from src.common.logging import get_logger

logger = get_logger("insights_run_all")


def run_all() -> None:
    logger.info("================================================================================")
    logger.info("Starting Group 24 Insights Pipeline (10 Non-Obvious Analyses)")
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

    # 7. Sleeping Beauties
    from src.stats.insights.s07_sleeping_beauties import run as run_07
    run_07()

    # 8. COVID Shock
    from src.stats.insights.s08_covid_shock import run as run_08
    run_08()

    # 9. Brain Circulation
    from src.stats.insights.s09_brain_circulation import run as run_09
    run_09()

    # 10. Succession Risk
    from src.stats.insights.s10_succession_risk import run as run_10
    run_10()

    logger.info("================================================================================")
    logger.info("✓ Completed all 10 Insights analyses. Outputs saved in stats/tables/insights/")
    logger.info("================================================================================")


if __name__ == "__main__":
    run_all()
