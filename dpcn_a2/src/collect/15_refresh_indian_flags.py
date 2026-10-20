"""Step 15: Recompute cites_indian_inst / cited_by_indian_inst on the exported data.

Applies the Step 11 rule to data/final/ directly, for checkouts where the
data/interim/ parquet caches are not available. Earlier exports filled the flags
with heuristics (any Indian co-author => cites; >= 10 citations => cited by);
this step replaces them with values measured from data/final/citation_network.csv
only, then refreshes the SHA256 entries in the manifests.

Rule (per paper x assigned-institute row, institute X):
- cites_indian_inst: the paper cites >= 1 corpus paper whose institutions (assigned
  labs + Indian co-author institutes) include an Indian institution other than X
- cited_by_indian_inst: the paper is cited by >= 1 corpus paper whose institutions
  include an Indian institution other than X

Outputs (rewritten in place):
- data/final/group24_data.csv
- data/final/group24_data_extended.csv
- data/MANIFEST.json, data/final/MANIFEST.json (sha256 + flag rule note)
"""

import collections
import hashlib
import json
from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("15_refresh_indian_flags")

FINAL_DIR = Path("data/final")
FLAG_RULE = (
    "Measured on in-corpus citation links only (citation_network.csv); "
    "no heuristic completion."
)


def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def work_institutions(df_ext: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """Return doi -> work_id and work_id -> {assigned labs + Indian co-author institutes}."""
    doi_to_work: Dict[str, str] = {}
    insts: Dict[str, Set[str]] = collections.defaultdict(set)
    for wid, doi, inst, coauth in df_ext[["work_id", "doi", "institution", "coauthor_institutes"]].itertuples(index=False):
        if doi:
            doi_to_work[doi] = wid
        insts[wid].add(inst)
        for p in coauth.split(";"):
            if p.strip():
                insts[wid].add(p.strip())
    return doi_to_work, insts


def compute_flags(df_ext: pd.DataFrame, df_cite: pd.DataFrame) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    """Return the (work_id, institution) keys whose cites / cited_by flag is TRUE."""
    doi_to_work, insts = work_institutions(df_ext)
    cites: Set[Tuple[str, str]] = set()
    cited_by: Set[Tuple[str, str]] = set()
    unmapped = 0

    for src_doi, tgt_doi, s_inst, t_inst in df_cite[["source_doi", "target_doi", "source_inst", "target_inst"]].itertuples(index=False):
        src, tgt = doi_to_work.get(src_doi), doi_to_work.get(tgt_doi)
        if src is None or tgt is None:
            unmapped += 1
            continue
        if any(i != s_inst for i in insts[tgt]):
            cites.add((src, s_inst))
        if any(i != t_inst for i in insts[src]):
            cited_by.add((tgt, t_inst))

    logger.info(f"{len(df_cite) - unmapped} citation edges used; {unmapped} skipped (missing DOI)")
    return cites, cited_by


def apply_flags(df: pd.DataFrame, work_ids: pd.Series, cites: Set, cited_by: Set) -> pd.DataFrame:
    keys = list(zip(work_ids, df["institution"]))
    df = df.copy()
    df["cites_indian_inst"] = ["TRUE" if k in cites else "FALSE" for k in keys]
    df["cited_by_indian_inst"] = ["TRUE" if k in cited_by else "FALSE" for k in keys]
    return df


def refresh_manifest(manifest_path: Path, updated: Dict[str, Path]) -> None:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    for name, path in updated.items():
        manifest["files"][name]["sha256"] = compute_file_sha256(path)
    manifest["indian_flag_rule"] = FLAG_RULE
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def run_step_15() -> None:
    logger.info("Starting Step 15: Recompute Indian citation flags from exported edges...")
    main_path = FINAL_DIR / "group24_data.csv"
    ext_path = FINAL_DIR / "group24_data_extended.csv"

    # Read everything as strings so untouched columns are written back byte-identical.
    df_main = pd.read_csv(main_path, dtype=str, keep_default_na=False)
    df_ext = pd.read_csv(ext_path, dtype=str, keep_default_na=False)
    df_cite = pd.read_csv(FINAL_DIR / "citation_network.csv", dtype=str, keep_default_na=False)
    assert len(df_main) == len(df_ext), "primary and extended datasets must be row-aligned"
    assert (df_main["doi"] == df_ext["doi"]).all() and (df_main["institution"] == df_ext["institution"]).all()

    cites, cited_by = compute_flags(df_ext, df_cite)
    df_ext = apply_flags(df_ext, df_ext["work_id"], cites, cited_by)
    df_main = apply_flags(df_main, df_ext["work_id"], cites, cited_by)

    df_main.to_csv(main_path, index=False, encoding="utf-8")
    df_ext.to_csv(ext_path, index=False, encoding="utf-8")

    updated = {"group24_data.csv": main_path, "group24_data_extended.csv": ext_path}
    for manifest_path in (Path("data/MANIFEST.json"), FINAL_DIR / "MANIFEST.json"):
        refresh_manifest(manifest_path, updated)

    for col in ("cites_indian_inst", "cited_by_indian_inst"):
        share = (df_main[col] == "TRUE").mean() * 100
        logger.info(f"{col}: {share:.1f}% of rows TRUE")
    logger.info("✓ Step 15 complete successfully.")


if __name__ == "__main__":
    run_step_15()
