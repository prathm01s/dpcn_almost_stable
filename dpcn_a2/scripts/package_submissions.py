"""Refresh the team archive final_submission/ from data/final, stats/report and dashboard/.

final_submission/ holds the dataset, network files, supporting tables, the report
(24_CSIR.pdf / .pptx), the dashboard as dashboard.zip, MANIFEST.json and CHECKSUMS.sha256.
Run from dpcn_a2/:
    python scripts/package_submissions.py
"""

import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final"
REPORT = ROOT / "stats" / "report"
DASH = ROOT / "dashboard"
DATA_FILES = ["group24_data.csv", "citation_network.csv", "authorship_network.csv", "indian_connections.csv",
              "faculty_master.csv", "group24_data_extended.csv", "indian_linked_works.csv",
              "work_reference_counts.csv", "MANIFEST.json"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def team_archive() -> None:
    out = ROOT / "final_submission"
    out.mkdir(exist_ok=True)
    for f in DATA_FILES:
        if (FINAL / f).exists():
            shutil.copy2(FINAL / f, out / f)
    for f in ("24_CSIR.pdf", "24_CSIR.pptx"):
        shutil.copy2(REPORT / f, out / f)
    zip_path = out / "dashboard.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DASH.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(DASH).as_posix())
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "CHECKSUMS.sha256")
    (out / "CHECKSUMS.sha256").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files),
                                          encoding="utf-8", newline="\n")


if __name__ == "__main__":
    team_archive()
    print("Refreshed final_submission/")
