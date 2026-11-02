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
        from src.dashboard.build_profiles import run_build_profiles
        from src.dashboard.build_insights11_suite import build_suite_js
        run_build_dashboard_data()
        build_insights_js()
        run_build_profiles()
        build_suite_js()
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
    elif target == "macro-insights":
        from src.stats.macro_insights.s21_smart_specialization import run_smart_specialization_analysis
        from src.stats.macro_insights.s11_academic_bridge import run_academic_bridge_analysis
        from src.stats.macro_insights.s51_frugal_innovation import run_frugal_innovation_analysis
        from src.stats.macro_insights.s52_patents_vs_papers import run_patents_vs_papers_analysis
        from src.stats.macro_insights.s31_leiden_benchmarks import run_leiden_benchmarks_analysis
        from src.dashboard.build_macro_insights_bundle import bundle_macro_insights
        run_smart_specialization_analysis()
        run_academic_bridge_analysis()
        run_frugal_innovation_analysis()
        run_patents_vs_papers_analysis()
        run_leiden_benchmarks_analysis()
        bundle_macro_insights()
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

