"""Compile all insights JSON files into a static JavaScript bundle for offline execution.

Reads stats/tables/insights/*.json and writes dashboard/data/g24_insights.js
defining window.G24_INSIGHTS for the file:// dashboard.
"""

import json
from pathlib import Path
from src.common.logging import get_logger

logger = get_logger("build_insights_js")

TABLES_DIR = Path("stats/tables/insights")
OUTPUT_JS = Path("dashboard/data/g24_insights.js")


def insight11_teaser() -> dict:
    """Numbers for the Insight 11 card on the home screen, copied from the Insight 11 outputs."""
    try:
        nim = json.loads((TABLES_DIR / "11_nimfa_vs_si_comparison.json").read_text(encoding="utf-8"))
        cl = json.loads((TABLES_DIR / "11_claims.json").read_text(encoding="utf-8"))
        dif = json.loads((TABLES_DIR / "11_information_diffusion.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    full, fac = nim["full_coauthorship"]["fields"]["Combined"], nim["faculty_coauthorship"]["fields"]["Combined"]
    chem = dif["fields_data"]["Chemistry"]["condition_a"]
    return {"full_curve": full["mc_curve"], "faculty_curve": fac["mc_curve"], "t50_full": full["mc_t50"],
            "t50_faculty": fac["mc_t50"], "n_full": nim["full_coauthorship"]["nodes"],
            "n_faculty": nim["faculty_coauthorship"]["nodes"], "spillover": chem["spillover_curve"][-1],
            "claims_passed": cl["n_passed"], "claims_total": cl["n_claims"]}


def build_insights_js() -> Path:
    logger.info("Compiling insights data payload...")
    insights_data = {}

    # Insight 11 has its own page (insights11.html, its own data file); the main page only needs a teaser
    json_files = [jf for jf in sorted(TABLES_DIR.glob("*.json")) if not jf.stem.startswith("11_")]
    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                d = json.load(f)
                insight_id = d.get("id", jf.stem)
                insights_data[insight_id] = d
        except Exception as exc:
            logger.warning(f"Error reading {jf}: {exc}")

    OUTPUT_JS.parent.mkdir(parents=True, exist_ok=True)
    payload_str = json.dumps(insights_data, separators=(",", ":"))
    teaser = json.dumps(insight11_teaser(), separators=(",", ":"))
    js_content = f"window.G24_INSIGHTS = {payload_str};\nwindow.G24_I11_TEASER = {teaser};\n"

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    logger.info(f"✓ Saved {OUTPUT_JS} ({len(insights_data)} insights compiled)")
    return OUTPUT_JS


if __name__ == "__main__":
    build_insights_js()
