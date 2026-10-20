"""Step 16: Remove duplicate rows and invalid edges from the exported data.

Works on data/final/ directly (the data/interim/ caches are not in every
checkout). Run it before Step 15, which recomputes the Indian citation flags
from the cleaned citation_network.csv.

Removes:
- group24_data.csv / group24_data_extended.csv: rows that repeat the same
  (institution, work_id, author). OpenAlex sometimes lists one person twice on a
  paper (e.g. once with an author ID and once without). The row with an
  author_openalex_id is kept. Both files stay row-aligned.
- citation_network.csv: self-loops (source_doi == target_doi, OpenAlex reference
  errors), edges with a blank DOI on either end, and exact duplicate rows.
- authorship_network.csv: exact duplicate rows.

Also refreshes row counts in data/MANIFEST.json and data/final/MANIFEST.json.
"""

import json
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("16_clean_final")

FINAL_DIR = Path("data/final")
MANIFESTS = (Path("data/MANIFEST.json"), FINAL_DIR / "MANIFEST.json")


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(FINAL_DIR / name, dtype=str, keep_default_na=False)


def write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(FINAL_DIR / name, index=False, encoding="utf-8", lineterminator="\n")


def duplicate_author_rows(df_ext: pd.DataFrame) -> pd.Series:
    """True for rows to drop: repeats of (institution, work_id, author), keeping the row with an author ID."""
    order = df_ext["author_openalex_id"].eq("").astype(int)  # rows with an ID sort first
    ranked = df_ext.assign(_o=order, _i=range(len(df_ext))).sort_values(["_o", "_i"], kind="stable")
    drop_idx = ranked[ranked.duplicated(["institution", "work_id", "author"])].index
    return df_ext.index.isin(drop_idx)


def clean_citation_edges(df: pd.DataFrame) -> pd.DataFrame:
    keep = (df["source_doi"] != "") & (df["target_doi"] != "") & (df["source_doi"] != df["target_doi"])
    return df[keep].drop_duplicates()


def refresh_counts(main: pd.DataFrame, ext: pd.DataFrame, cite: pd.DataFrame, auth: pd.DataFrame) -> None:
    for path in MANIFESTS:
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        m["total_rows"] = len(main)
        m["total_distinct_papers"] = int(ext["work_id"].nunique())
        m["rows_by_institution"] = main["institution"].value_counts().to_dict()
        m["files"]["group24_data.csv"]["rows"] = len(main)
        m["files"]["group24_data_extended.csv"]["rows"] = len(ext)
        m["files"]["citation_network.csv"]["rows"] = len(cite)
        m["files"]["authorship_network.csv"]["rows"] = len(auth)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(m, f, indent=2)


def run_step_16() -> None:
    logger.info("Starting Step 16: clean duplicate rows and invalid edges in data/final/...")
    main, ext = read("group24_data.csv"), read("group24_data_extended.csv")
    assert len(main) == len(ext) and (main["doi"] == ext["doi"]).all() and (main["author"] == ext["author"]).all()

    drop = duplicate_author_rows(ext)
    main, ext = main[~drop], ext[~drop]
    logger.info(f"Dropped {int(drop.sum())} duplicate (institution, work, author) rows -> {len(main)} rows")

    cite = read("citation_network.csv")
    cite_clean = clean_citation_edges(cite)
    logger.info(f"Citation network: {len(cite)} -> {len(cite_clean)} edges")

    auth = read("authorship_network.csv")
    auth_clean = auth.drop_duplicates()
    logger.info(f"Authorship network: {len(auth)} -> {len(auth_clean)} edges")

    write(main, "group24_data.csv")
    write(ext, "group24_data_extended.csv")
    write(cite_clean, "citation_network.csv")
    write(auth_clean, "authorship_network.csv")
    refresh_counts(main, ext, cite_clean, auth_clean)
    logger.info("Step 16 complete. Run Step 15 next to recompute the Indian flags and SHA256s.")


if __name__ == "__main__":
    run_step_16()
