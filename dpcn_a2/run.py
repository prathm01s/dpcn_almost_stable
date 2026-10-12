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
        run_build_dashboard_data()
    elif target == "test":
        subprocess.run([sys.executable, "-m", "pytest", "tests/"], check=True)
    elif target == "all":
        run_target("collect")
        run_target("stats")
        run_target("dashboard")
        run_target("test")
    else:
        print(f"Unknown target: {target}")
        print("Available targets: all, collect, stats, dashboard, test")
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_target(target)
