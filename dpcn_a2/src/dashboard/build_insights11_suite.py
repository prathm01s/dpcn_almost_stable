"""Build dashboard/data/g24_insights11_suite.js for the Insight 11 page (dashboard/insights11.html, D-38).

The page merges the field-diffusion study (part 1, s11_information_diffusion) with the extended study
(part 2, s11_nimfa_spreading; part 3, s11_threshold_check; faculty networks and roster audit) and the
claims checker (part 4, s11_claims). This module only copies their outputs; nothing is recomputed, so
every number on the page is the number in stats/tables/insights/11_*.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("build_insights11_suite")

OUTPUT_JS = Path("dashboard/data/g24_insights11_suite.js")
T = Path("stats/tables/insights")


def _json(name):
    p = T / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _csv(name):
    p = T / name
    return json.loads(pd.read_csv(p).to_json(orient="records")) if p.exists() else []


def build_suite_js() -> Path:
    import yaml
    with open("config/settings.yaml", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
    dif = _json("11_information_diffusion.json")
    nim = _json("11_nimfa_vs_si_comparison.json")
    payload = {
        "meta": {"built": date.today().isoformat(), "collection_date": settings.get("collection_date")},
        "diffusion": {k: dif.get(k) for k in ("question", "headline", "metrics", "method_note", "fields_data")},
        "spreading": nim,
        "grid": _csv("11_simulation_grid_metrics.csv"),
        "threshold": _json("11_threshold_check.json"),
        "cadre_summary": _csv("11_cadre_networks_summary.csv"),
        "faculty_graph": _json("11_cadre_coauthorship_graph.json"),
        "faculty_citation_graph": {k: v for k, v in _json("11_cadre_citation_graph.json").items() if k not in ("nodes", "links")},
        "cleaning": _json("11_data_cleaning_stats.json"),
        "claims": _json("11_claims.json"),
    }
    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JS.write_text("window.G24_I11 = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n",
                         encoding="utf-8")
    logger.info(f"Wrote {OUTPUT_JS} ({OUTPUT_JS.stat().st_size // 1024} KB)")
    return OUTPUT_JS


if __name__ == "__main__":
    build_suite_js()
