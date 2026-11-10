#!/usr/bin/env python3
"""Unified project runner (equivalent to make targets).

Usage:
  python3 run.py all
  python3 run.py collect
  python3 run.py stats
  python3 run.py dashboard
  python3 run.py global      (global benchmark only)
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
        from src.dashboard.build_global import run_build_global
        run_build_dashboard_data()
        run_build_global()
        build_insights_js()
        run_build_profiles()
        build_suite_js()
    elif target == "insights-fetch":
        from src.collect.fetch_author_careers import main as fetch_careers_main
        fetch_careers_main()
    elif target == "insights":
        from src.stats.insights.run_all import run_all as insights_main
        from src.dashboard.build_insights_js import build_insights_js
        insights_main()
        build_insights_js()
    elif target == "macro-insights":
        # Only Study 1.1 is built: Studies 2.1, 3.1, 5.1 and 5.2 are withdrawn from the dashboard
        # (D-33) because their inputs are hand-entered values without a source file.
        from src.stats.macro_insights.s11_academic_bridge import run_academic_bridge_analysis
        from src.dashboard.build_macro_insights_bundle import bundle_macro_insights
        run_academic_bridge_analysis()
        bundle_macro_insights()
    elif target == "global":
        # Global benchmark only (D-35): peer selection, benchmark data, tables, dashboard payload
        import importlib
        importlib.import_module("src.collect.22_global_peers").run_step_22()
        importlib.import_module("src.collect.23_global_benchmark").run_step_23()
        from src.stats.global_benchmark import run_global_benchmark
        from src.dashboard.build_global import run_build_global
        run_global_benchmark()
        run_build_global()
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
        print("Available targets: all, collect, global, stats, insights, insights-fetch, dashboard, test, browser-test")
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_target(target)

