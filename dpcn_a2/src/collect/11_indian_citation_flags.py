"""Step 11: Compute cites_indian_inst and cited_by_indian_inst flags, and export raw citation edges for Task 4.

Flags (measured on in-corpus citation links only, i.e. both papers belong to the
CSIR-NCL / CSIR-IICT / CSIR-CECRI corpus):
- cites_indian_inst: TRUE iff paper cites >= 1 corpus paper involving an Indian institution
  other than the row's own institute (another assigned lab or an Indian co-author institute)
- cited_by_indian_inst: TRUE iff paper is cited by >= 1 corpus paper involving an Indian
  institution other than the row's own institute

Outputs:
- data/interim/citation_edges_raw.parquet (directed edges for Task 4)
- Updates data/interim/paper_authors_attributed.parquet with cites_indian_inst, cited_by_indian_inst
"""

import collections
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("11_indian_citation_flags")


def run_step_11() -> None:
    logger.info("Starting Step 11: Compute Indian citation flags and citation edges...")

    interim_dir = Path("data/interim")
    works_path = interim_dir / "works_filtered.parquet"
    authors_path = interim_dir / "paper_authors_attributed.parquet"

    assert works_path.exists(), "works_filtered.parquet not found"
    assert authors_path.exists(), "paper_authors_attributed.parquet not found"

    df_works = pd.read_parquet(works_path)
    df_auth = pd.read_parquet(authors_path)

    logger.info(f"Loaded {len(df_works)} works and {len(df_auth)} author rows")

    # Build work lookup: work_id -> doi, year, title, cited_by_count
    work_info: Dict[str, Dict[str, Any]] = {}
    for _, w in df_works.iterrows():
        work_info[w["work_id"]] = {
            "doi": w.get("doi") or "",
            "year": int(w.get("publication_year")),
            "title": w.get("title") or "",
            "cited_by_count": int(w.get("cited_by_count") or 0),
        }

    # Build mapping from work_id to all institutions involved (own assigned labs + coauthor Indian institutes)
    work_all_indian_insts: Dict[str, Set[str]] = collections.defaultdict(set)
    work_assigned_insts: Dict[str, Set[str]] = collections.defaultdict(set)

    for wid, group in df_auth.groupby("work_id"):
        assigned = set(group["institution"])
        work_assigned_insts[wid] = assigned
        work_all_indian_insts[wid].update(assigned)

        for coauth in group["coauthor_institutes"].dropna():
            if coauth:
                for inst in str(coauth).split(";"):
                    if inst.strip():
                        work_all_indian_insts[wid].add(inst.strip())

    # Build paper references mapping
    work_references: Dict[str, Set[str]] = {}
    for _, w in df_works.iterrows():
        wid = w["work_id"]
        refs_str = w.get("referenced_works")
        if refs_str and not pd.isna(refs_str):
            try:
                work_references[wid] = set(json.loads(refs_str))
            except Exception:
                work_references[wid] = set()
        else:
            work_references[wid] = set()

    # Track in-corpus directed citation edges: citing_work -> cited_work
    citation_edges: List[Dict[str, Any]] = []

    cites_indian_flag: Dict[Tuple[str, str], bool] = collections.defaultdict(bool)
    cited_by_indian_flag: Dict[Tuple[str, str], bool] = collections.defaultdict(bool)

    corpus_work_ids = set(work_info.keys())

    for citing_id, refs in work_references.items():
        citing_insts = work_assigned_insts.get(citing_id, set())
        citing_info = work_info.get(citing_id, {})
        citing_doi = citing_info.get("doi", "")
        citing_year = citing_info.get("year", 0)

        # Check references that are in our corpus
        internal_refs = refs.intersection(corpus_work_ids)

        for cited_id in internal_refs:
            cited_insts = work_assigned_insts.get(cited_id, set())
            cited_all_ind = work_all_indian_insts.get(cited_id, set())
            cited_info = work_info.get(cited_id, {})
            cited_doi = cited_info.get("doi", "")

            for s_inst in citing_insts:
                for t_inst in cited_insts:
                    is_cross = s_inst != t_inst
                    citation_edges.append({
                        "source_work_id": citing_id,
                        "target_work_id": cited_id,
                        "source_doi": citing_doi,
                        "target_doi": cited_doi,
                        "source_inst": s_inst,
                        "target_inst": t_inst,
                        "year": citing_year,
                        "is_cross_inst": is_cross,
                    })

                    # If cited paper has Indian institutions other than s_inst
                    if any(i != s_inst for i in cited_all_ind):
                        cites_indian_flag[(citing_id, s_inst)] = True

                    # If citing paper has Indian institutions other than t_inst
                    citing_all_ind = work_all_indian_insts.get(citing_id, set())
                    if any(i != t_inst for i in citing_all_ind):
                        cited_by_indian_flag[(cited_id, t_inst)] = True

    # Save citation_edges_raw.parquet for Task 4
    df_edges = pd.DataFrame(citation_edges)
    edges_path = interim_dir / "citation_edges_raw.parquet"
    df_edges.to_parquet(edges_path, index=False)
    logger.info(f"Saved {len(df_edges)} raw citation edges to {edges_path}")

    # Flags come only from observed in-corpus citation links. OpenAlex reference
    # lists of out-of-corpus works are not collected, so a paper whose Indian
    # citations all involve papers outside the cluster corpus is left FALSE.
    updated_authors: List[Dict[str, Any]] = []

    for _, row in df_auth.iterrows():
        rec = row.to_dict()
        wid = row["work_id"]
        inst = row["institution"]

        cites_flag = cites_indian_flag.get((wid, inst), False)
        cited_flag = cited_by_indian_flag.get((wid, inst), False)

        rec["cites_indian_inst"] = "TRUE" if cites_flag else "FALSE"
        rec["cited_by_indian_inst"] = "TRUE" if cited_flag else "FALSE"
        updated_authors.append(rec)

    df_authors_updated = pd.DataFrame(updated_authors)
    df_authors_updated.to_parquet(authors_path, index=False)
    logger.info(f"✓ Updated {len(df_authors_updated)} author rows with citation flags in {authors_path}")

    print("Flag distributions:")
    print("cites_indian_inst:")
    print(df_authors_updated["cites_indian_inst"].value_counts(normalize=True))
    print("cited_by_indian_inst:")
    print(df_authors_updated["cited_by_indian_inst"].value_counts(normalize=True))

    logger.info("✓ Step 11 complete successfully.")


if __name__ == "__main__":
    run_step_11()
