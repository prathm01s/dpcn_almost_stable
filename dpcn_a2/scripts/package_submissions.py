"""Build the submission bundles from data/final, stats/report and dashboard/.

  submission_week1-2/  + group24_week1-2_submission.zip   dataset + network files
  submission_week3/    + group24_week3_submission.zip     report + dashboard
  final_submission/                                        everything (team archive)

The README.md files inside submission_week1-2/ and submission_week3/ are written by
hand and kept; everything else in those folders is replaced. Run from dpcn_a2/:
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
WEEK12_FILES = ["group24_data.csv", "citation_network.csv", "authorship_network.csv",
                "indian_connections.csv", "faculty_master.csv"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def reset(folder: Path) -> None:
    """Empty a bundle folder but keep its hand-written README.md."""
    folder.mkdir(exist_ok=True)
    for p in folder.iterdir():
        if p.name == "README.md":
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()


def checksums(folder: Path) -> None:
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.name != "CHECKSUMS.sha256")
    lines = [f"{sha256(p)}  {p.relative_to(folder).as_posix()}" for p in files]
    (folder / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def zip_dir(folder: Path, zip_path: Path, arc_root: str) -> None:
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, f"{arc_root}/{p.relative_to(folder).as_posix()}")


def copy_dashboard(dest: Path) -> None:
    shutil.copytree(DASH, dest, ignore=shutil.ignore_patterns("screenshots"))


def week12() -> None:
    out = ROOT / "submission_week1-2"
    reset(out)
    for f in WEEK12_FILES:
        shutil.copy2(FINAL / f, out / f)
    checksums(out)
    zip_dir(out, ROOT / "group24_week1-2_submission.zip", "group24_week1-2")


def week3() -> None:
    out = ROOT / "submission_week3"
    reset(out)
    for f in ("group24_stats_report.pdf", "group24_stats_report.pptx"):
        shutil.copy2(REPORT / f, out / f)
    copy_dashboard(out / "dashboard")
    # Files the dashboard's download buttons link to (../data/final, ../stats/report)
    (out / "data" / "final").mkdir(parents=True)
    for f in ("group24_data.csv", "citation_network.csv", "authorship_network.csv", "indian_connections.csv"):
        shutil.copy2(FINAL / f, out / "data" / "final" / f)
    shutil.copy2(ROOT / "data" / "MANIFEST.json", out / "data" / "MANIFEST.json")
    (out / "stats" / "report").mkdir(parents=True)
    for f in ("group24_stats_report.pdf", "group24_stats_report.pptx"):
        shutil.copy2(REPORT / f, out / "stats" / "report" / f)
    checksums(out)
    zip_dir(out, ROOT / "group24_week3_submission.zip", "group24_week3")


def team_archive() -> None:
    out = ROOT / "final_submission"
    for f in WEEK12_FILES + ["group24_data_extended.csv", "indian_linked_works.csv", "MANIFEST.json"]:
        if (FINAL / f).exists():
            shutil.copy2(FINAL / f, out / f)
    for f in ("group24_stats_report.pdf", "group24_stats_report.pptx"):
        shutil.copy2(REPORT / f, out / f)
    zip_path = out / "dashboard.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DASH.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(DASH).as_posix())
    files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "CHECKSUMS.sha256")
    (out / "CHECKSUMS.sha256").write_text("".join(f"{sha256(p)}  {p.name}\n" for p in files), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    week12()
    week3()
    team_archive()
    print("Built submission_week1-2/, submission_week3/, final_submission/ and the two zips")
