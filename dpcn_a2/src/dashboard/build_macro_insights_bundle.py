"""Bundler for the 5 Macro and Comparative Insight Studies.

Reads JSON tables from stats/tables/macro_insights/ and writes self-contained
JavaScript bundles to dashboard/data/ to guarantee 100% offline file:// compatibility.
"""

import json
from pathlib import Path

SRC_DIR = Path("stats/tables/macro_insights")
DEST_DIR = Path("dashboard/data")
DEST_DIR.mkdir(parents=True, exist_ok=True)

BUNDLES = [
    {
        "src": SRC_DIR / "21_smart_specialization.json",
        "dest": DEST_DIR / "g24_smart_spec.js",
        "var_name": "G24_SMART_SPEC_DATA"
    },
    {
        "src": SRC_DIR / "11_academic_bridge.json",
        "dest": DEST_DIR / "g24_academic_bridge.js",
        "var_name": "G24_ACADEMIC_BRIDGE_DATA"
    },
    {
        "src": SRC_DIR / "51_frugal_innovation.json",
        "dest": DEST_DIR / "g24_frugal_rd.js",
        "var_name": "G24_FRUGAL_RD_DATA"
    },
    {
        "src": SRC_DIR / "52_patents_vs_papers.json",
        "dest": DEST_DIR / "g24_patents_papers.js",
        "var_name": "G24_PATENTS_PAPERS_DATA"
    },
    {
        "src": SRC_DIR / "31_leiden_benchmarks.json",
        "dest": DEST_DIR / "g24_leiden_benchmarks.js",
        "var_name": "G24_LEIDEN_BENCHMARKS_DATA"
    }
]


def bundle_macro_insights():
    print("Bundling Macro Insights data into dashboard/data/...")
    for b in BUNDLES:
        src_path = b["src"]
        dest_path = b["dest"]
        var_name = b["var_name"]
        
        if not src_path.exists():
            raise FileNotFoundError(f"Missing required source artifact: {src_path}")
            
        data = json.loads(src_path.read_text(encoding="utf-8"))
        js_content = f"// Generated for Group 24 Dashboard - 100% Offline Standalone Bundle\nwindow.{var_name} = {json.dumps(data, indent=2)};\n"
        dest_path.write_text(js_content, encoding="utf-8")
        print(f"✓ Created {dest_path} ({len(js_content) // 1024} KB)")

    print("All 5 Macro Insights data bundles created successfully.")


if __name__ == "__main__":
    bundle_macro_insights()
