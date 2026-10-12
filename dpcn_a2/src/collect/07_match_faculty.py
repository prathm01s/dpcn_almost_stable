"""Step 07: Match official faculty roster with in-corpus OpenAlex authors, compute h-indices, and tag author roles.

Outputs:
- data/interim/faculty_master.parquet & CSV
- data/review/author_review_queue.csv
- Updates data/interim/paper_authors_attributed.parquet with author_role, faculty_id, department, designation
"""

import collections
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd
import yaml

from src.common.logging import get_logger
from src.common.names import clean_name, match_names

logger = get_logger("07_match_faculty")


def calculate_h_index(citation_counts: List[int]) -> int:
    """Compute h-index for a list of paper citation counts."""
    sorted_cits = sorted(citation_counts, reverse=True)
    h = 0
    for i, c in enumerate(sorted_cits, start=1):
        if c >= i:
            h = i
        else:
            break
    return h


def run_step_07() -> None:
    logger.info("Starting Step 07: Match roster ↔ OpenAlex authors and compute h-indices...")

    interim_dir = Path("data/interim")
    review_dir = Path("data/review")
    review_dir.mkdir(parents=True, exist_ok=True)

    roster_path = interim_dir / "roster.parquet"
    authors_path = interim_dir / "paper_authors_attributed.parquet"
    alias_path = interim_dir / "author_aliases.parquet"

    assert roster_path.exists(), "roster.parquet not found"
    assert authors_path.exists(), "paper_authors_attributed.parquet not found"

    df_roster = pd.read_parquet(roster_path)
    df_authors = pd.read_parquet(authors_path)
    df_alias = pd.read_parquet(alias_path)

    logger.info(f"Loaded {len(df_roster)} roster scientists, {len(df_authors)} authorship rows, {len(df_alias)} author aliases")

    # Group authorship rows by (inst_key, author_id)
    # to compute distinct papers and citations per in-corpus author
    author_works_by_inst: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for _, row in df_authors.iterrows():
        inst_k = row["inst_key"]
        aid = row["author_id"]
        wid = row["work_id"]
        cits = int(row["citations"])
        yr = int(row["year"])

        key = (inst_k, aid)
        if key not in author_works_by_inst:
            author_works_by_inst[key] = {
                "work_ids": set(),
                "citations_map": {},
                "years": set(),
                "author_name": row["author"],
            }
        author_works_by_inst[key]["work_ids"].add(wid)
        author_works_by_inst[key]["citations_map"][wid] = cits
        author_works_by_inst[key]["years"].add(yr)

    # Pre-index candidate in-corpus authors per institute
    corpus_authors_by_inst: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for (inst_k, aid), data in author_works_by_inst.items():
        cits_list = list(data["citations_map"].values())
        h_idx = calculate_h_index(cits_list)
        corpus_authors_by_inst[inst_k].append({
            "author_id": aid,
            "display_name": data["author_name"],
            "name_norm": clean_name(data["author_name"]),
            "n_papers": len(data["work_ids"]),
            "n_citations": sum(cits_list),
            "h_index": h_idx,
            "years": sorted(list(data["years"])),
        })

    # Match each roster scientist against corpus authors in that institute
    faculty_records: List[Dict[str, Any]] = []
    review_queue: List[Dict[str, Any]] = []

    matched_aid_to_faculty: Dict[str, Dict[str, Any]] = {}

    faculty_counter = 1

    for _, r in df_roster.iterrows():
        inst_k = r["inst_key"]
        r_name = r["full_name"]
        r_norm = r["name_norm"]
        dept = r["department"]
        desig = r["designation"]

        candidates = corpus_authors_by_inst.get(inst_k, [])

        best_cand = None
        best_score = 0.0
        multi_matches = []

        r_toks = set(cand_norm.lower() for cand_norm in r_norm.split() if len(cand_norm) > 1)
        r_inits = set(cand_norm[0].lower() for cand_norm in r_norm.split() if cand_norm)

        for cand in candidates:
            c_toks = cand.get("tok_set")
            if c_toks is None:
                cand["tok_set"] = set(t.lower() for t in cand["name_norm"].split() if len(t) > 1)
                cand["init_set"] = set(t[0].lower() for t in cand["name_norm"].split() if t)
                c_toks = cand["tok_set"]

            # Must share at least one significant token
            if r_toks and c_toks and not (r_toks & c_toks):
                continue

            score, init_match = match_names(r_norm, cand["name_norm"])
            if score >= 90 and init_match:
                multi_matches.append((score, cand))
                if score > best_score:
                    best_score = score
                    best_cand = cand

        fid = f"FAC_{inst_k.upper()}_{faculty_counter:04d}"
        faculty_counter += 1

        if best_cand:
            aid = best_cand["author_id"]
            matched_aid_to_faculty[aid] = {
                "faculty_id": fid,
                "full_name": r_name,
                "designation": desig,
                "department": dept,
                "author_role": "faculty",
            }

            faculty_records.append({
                "inst_key": inst_k,
                "faculty_id": fid,
                "full_name": r_name,
                "name_norm": r_norm,
                "designation": desig,
                "department": dept,
                "author_id": aid,
                "h_index_corpus": best_cand["h_index"],
                "n_papers_corpus": best_cand["n_papers"],
                "n_citations_corpus": best_cand["n_citations"],
                "match_confidence": "high" if best_score >= 95 else "medium",
                "match_score": best_score,
                "match_evidence": f"Name score {best_score:.1f}; {best_cand['n_papers']} in-corpus papers",
                "is_matched": True,
            })

            if len(multi_matches) > 1:
                review_queue.append({
                    "inst_key": inst_k,
                    "roster_name": r_name,
                    "matched_id": aid,
                    "matched_name": best_cand["display_name"],
                    "candidate_count": len(multi_matches),
                    "reason": "Multiple candidate matches in corpus",
                })
        else:
            # Unmatched roster scientist (0 papers in window)
            faculty_records.append({
                "inst_key": inst_k,
                "faculty_id": fid,
                "full_name": r_name,
                "name_norm": r_norm,
                "designation": desig,
                "department": dept,
                "author_id": None,
                "h_index_corpus": 0,
                "n_papers_corpus": 0,
                "n_citations_corpus": 0,
                "match_confidence": "unmatched",
                "match_score": 0.0,
                "match_evidence": "No matching papers found in 2016–2026 window",
                "is_matched": False,
            })

    # Identify Probable Former Faculty:
    # Unmatched in-corpus authors with >= 10 papers across >= 3 years
    former_faculty_counter = 1
    for inst_k, cand_list in corpus_authors_by_inst.items():
        for cand in cand_list:
            aid = cand["author_id"]
            if aid not in matched_aid_to_faculty:
                if cand["n_papers"] >= 10 and len(cand["years"]) >= 3:
                    ffid = f"FORMER_{inst_k.upper()}_{former_faculty_counter:04d}"
                    former_faculty_counter += 1
                    matched_aid_to_faculty[aid] = {
                        "faculty_id": ffid,
                        "full_name": cand["display_name"],
                        "designation": "Former Scientist / Senior Researcher",
                        "department": "Chemistry / Chemical Sciences",
                        "author_role": "probable_former_faculty",
                    }
                    review_queue.append({
                        "inst_key": inst_k,
                        "roster_name": "N/A (Former Faculty Heuristic)",
                        "matched_id": aid,
                        "matched_name": cand["display_name"],
                        "candidate_count": 1,
                        "reason": f"Prolific author: {cand['n_papers']} papers across {len(cand['years'])} years",
                    })

    # Save faculty_master
    df_fac = pd.DataFrame(faculty_records)
    df_fac.to_parquet(interim_dir / "faculty_master.parquet", index=False)
    df_fac.to_csv(interim_dir / "faculty_master.csv", index=False)
    logger.info(f"Saved {len(df_fac)} faculty records to {interim_dir / 'faculty_master.parquet'}")

    # Save review queue
    df_rev = pd.DataFrame(review_queue)
    df_rev.to_csv(review_dir / "author_review_queue.csv", index=False)
    logger.info(f"Saved {len(df_rev)} review candidates to {review_dir / 'author_review_queue.csv'}")

    # Report match rate among active roster
    matched_count = df_fac["is_matched"].sum()
    logger.info(f"Roster match summary: {matched_count}/{len(df_fac)} ({matched_count/len(df_fac)*100:.1f}%) roster scientists active in corpus")

    # Update paper_authors_attributed with author_role, faculty_id, department, designation
    updated_rows: List[Dict[str, Any]] = []
    for _, row in df_authors.iterrows():
        rec = row.to_dict()
        aid = row.get("author_id")
        if aid in matched_aid_to_faculty:
            info = matched_aid_to_faculty[aid]
            rec["author_role"] = info["author_role"]
            rec["faculty_id"] = info["faculty_id"]
            rec["department"] = info["department"]
            rec["designation"] = info["designation"]
            if info["author_role"] == "faculty":
                rec["author"] = info["full_name"]
        else:
            rec["author_role"] = "affiliated_author"
            rec["faculty_id"] = ""
            rec["department"] = "Unassigned"
            rec["designation"] = "Affiliated Author / Researcher"

        updated_rows.append(rec)

    df_updated = pd.DataFrame(updated_rows)
    df_updated.to_parquet(authors_path, index=False)
    logger.info(f"✓ Updated {len(df_updated)} rows with author_role and faculty metadata in {authors_path}")
    print(df_updated["author_role"].value_counts())
    logger.info("✓ Step 07 complete successfully.")


if __name__ == "__main__":
    run_step_07()
