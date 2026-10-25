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


def build_insights_js() -> Path:
    logger.info("Compiling insights data payload...")
    insights_data = {}

    json_files = sorted(TABLES_DIR.glob("*.json"))
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
    js_content = f"window.G24_INSIGHTS = {payload_str};\n"

    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    logger.info(f"✓ Saved {OUTPUT_JS} ({len(insights_data)} insights compiled)")
    return OUTPUT_JS


if __name__ == "__main__":
    build_insights_js()
