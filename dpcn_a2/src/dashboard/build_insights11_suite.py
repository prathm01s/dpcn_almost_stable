"""Compile all Insight 11 artifacts (Cadre Networks, Data Cleaning, NIMFA vs SI simulations)
into a self-contained JavaScript bundle dashboard/data/g24_insights11_suite.js.

Ensures the new page works completely offline via file:// protocol.
"""

import json
from pathlib import Path
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("build_insights11_suite")

OUTPUT_JS = Path("dashboard/data/g24_insights11_suite.js")
TABLES_DIR = Path("stats/tables/insights")


def build_suite_js():
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load Data Cleaning Stats
    cleaning_file = TABLES_DIR / "11_data_cleaning_stats.json"
    cleaning_stats = json.loads(cleaning_file.read_text(encoding="utf-8")) if cleaning_file.exists() else {}

    # 2. Load Cadre Networks Summary & Graphs
    summary_file = TABLES_DIR / "11_cadre_networks_summary.csv"
    cadre_summary = pd.read_csv(summary_file).to_dict(orient="records") if summary_file.exists() else []

    auth_graph_file = TABLES_DIR / "11_cadre_coauthorship_graph.json"
    cadre_auth_graph = json.loads(auth_graph_file.read_text(encoding="utf-8")) if auth_graph_file.exists() else {}

    cite_graph_file = TABLES_DIR / "11_cadre_citation_graph.json"
    cadre_cite_graph = json.loads(cite_graph_file.read_text(encoding="utf-8")) if cite_graph_file.exists() else {}

    # 3. Load Simulation Results
    sim_file = TABLES_DIR / "11_nimfa_vs_si_comparison.json"
    simulations = json.loads(sim_file.read_text(encoding="utf-8")) if sim_file.exists() else {}

    grid_file = TABLES_DIR / "11_simulation_grid_metrics.csv"
    sim_grid = pd.read_csv(grid_file).to_dict(orient="records") if grid_file.exists() else []

    bundle = {
        "cleaning": cleaning_stats,
        "cadre_summary": cadre_summary,
        "cadre_coauthorship": cadre_auth_graph,
        "cadre_citation": cadre_cite_graph,
        "simulations": simulations,
        "simulation_grid": sim_grid,
    }

    payload = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))
    OUTPUT_JS.write_text(f"window.G24_INSIGHTS11_SUITE = {payload};\n", encoding="utf-8")
    logger.info(f"✓ Saved Insight 11 Suite JS bundle to {OUTPUT_JS} ({OUTPUT_JS.stat().st_size / 1024:.0f} KB)")
    return OUTPUT_JS


if __name__ == "__main__":
    build_suite_js()
