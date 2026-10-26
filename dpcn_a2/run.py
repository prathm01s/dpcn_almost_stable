#!/usr/bin/env python3
"""Unified project runner (equivalent to make targets).

Usage:
  python3 run.py all
  python3 run.py collect
  python3 run.py stats
  python3 run.py dashboard
  python3 run.py test
"""

import sys
import subprocess


def run_target(target: str) -> None:
    if target == "collect":
        from src.collect.main import main as collect_main
        collect_main()
    elif target == "stats":
        from src.stats.main import main as stats_main
        stats_main()
    elif target == "dashboard":
        from src.dashboard.build_data import run_build_dashboard_data
        from src.dashboard.build_insights_js import build_insights_js
        run_build_dashboard_data()
        build_insights_js()
    elif target == "insights-fetch":
        from src.collect.fetch_counts_by_year import main as fetch_counts_main
        from src.collect.fetch_author_careers import main as fetch_careers_main
        fetch_counts_main()
        fetch_careers_main()
    elif target == "insights":
        from src.stats.insights.run_all import run_all as insights_main
        from src.dashboard.build_insights_js import build_insights_js
        insights_main()
        build_insights_js()
    elif target == "test":
        subprocess.run([sys.executable, "-m", "pytest", "tests/"], check=True)
    elif target == "browser-test":
        from scripts.test_browser import run_tests
        run_tests()
    elif target == "all":
        run_target("collect")
        run_target("insights")  # before stats: the report quotes the insight headlines
        run_target("stats")
        run_target("dashboard")
        run_target("test")
    else:
        print(f"Unknown target: {target}")
        print("Available targets: all, collect, stats, insights, insights-fetch, dashboard, test, browser-test")
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_target(target)

