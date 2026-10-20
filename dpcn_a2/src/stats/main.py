"""Pipeline runner for Phase 2: Statistics and Reporting.

Executes:
1. src.stats.metrics -> computes all tables in stats/tables/
   src.stats.connectivity -> Indian citation flow & connectivity tables (Sections 7a/7b)
2. src.stats.make_figures -> generates 8 publication figures in stats/figures/
3. src.stats.make_report -> compiles PowerPoint report (<=10 slides) and PDF in stats/report/
"""

from src.stats.metrics import run_metrics_computation
from src.stats.connectivity import run_connectivity_metrics
from src.stats.make_figures import run_figure_generation
from src.stats.make_report import run_report_generation
from src.common.logging import get_logger

logger = get_logger("stats_main")


def main() -> None:
    logger.info("=== Starting Phase 2: Statistics & Reporting Pipeline ===")
    run_metrics_computation()
    run_connectivity_metrics()
    run_figure_generation()
    run_report_generation()
    logger.info("=== Phase 2 Completed Successfully! ===")


if __name__ == "__main__":
    main()
