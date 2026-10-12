"""Step 10: Build Indian institution registry and compute coauthor_institutes column.

Produces:
- config/indian_inst_registry.csv
- data/review/inst_registry_review.csv
- Updates data/interim/paper_authors_attributed.parquet with coauthor_institutes
"""

import collections
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("10_coauthor_institutes")


def assign_sector_cluster(name: str, inst_type: str) -> str:
    """Classify Indian institution into sector/cluster for network mapping."""
    n = name.upper()
    if "INDIAN INSTITUTE OF TECHNOLOGY" in n or re.search(r"\bIIT\b", n):
        return "IIT"
    if "NATIONAL INSTITUTE OF TECHNOLOGY" in n or re.search(r"\bNIT\b", n):
        return "NIT"
    if "INDIAN INSTITUTE OF INFORMATION TECHNOLOGY" in n or re.search(r"\bIIIT\b", n):
        return "IIIT"
    if "INDIAN INSTITUTE OF SCIENCE EDUCATION AND RESEARCH" in n or re.search(r"\bIISER\b", n):
        return "IISER"
    if "COUNCIL OF SCIENTIFIC AND INDUSTRIAL RESEARCH" in n or re.search(r"\bCSIR\b", n) or "NATIONAL CHEMICAL LABORATORY" in n or "INDIAN INSTITUTE OF CHEMICAL TECHNOLOGY" in n or "CENTRAL ELECTROCHEMICAL" in n:
        return "CSIR"
    if "BHABHA ATOMIC RESEARCH" in n or "TATA INSTITUTE OF FUNDAMENTAL RESEARCH" in n or "TIFR" in n or "BARC" in n or "IGCAR" in n or "RRCAT" in n or "NISER" in n:
        return "DAE"
    if "INDIAN COUNCIL OF AGRICULTURAL RESEARCH" in n or "ICAR" in n or "IARI" in n:
        return "ICAR"
    if "INDIAN COUNCIL OF MEDICAL RESEARCH" in n or "ICMR" in n or "NIV" in n or "NIPER" in n:
        return "ICMR"
    if "DEFENCE RESEARCH AND DEVELOPMENT" in n or "DRDO" in n:
        return "DRDO"
    if "INDIAN SPACE RESEARCH" in n or "ISRO" in n or "VSSC" in n:
        return "ISRO"
    if "UNIVERSITY OF HYDERABAD" in n or "DELHI UNIVERSITY" in n or "JAWAHARLAL NEHRU UNIVERSITY" in n or "BANARAS HINDU UNIVERSITY" in n or "ALIGARH MUSLIM" in n or "CENTRAL UNIVERSITY" in n:
        return "CentralUniv"
    if "PUNE UNIVERSITY" in n or "OSMANIA UNIVERSITY" in n or "ALAGAPPA UNIVERSITY" in n or "MADRAS UNIVERSITY" in n or "CALCUTTA UNIVERSITY" in n or "MUMBAI UNIVERSITY" in n or "STATE UNIVERSITY" in n:
        return "StateUniv"
    if "BIRLA INSTITUTE OF TECHNOLOGY" in n or "MANIPAL" in n or "AMITY" in n or "SRM" in n or "VELLORE INSTITUTE OF TECHNOLOGY" in n or "VIT" in n or "THAPAR" in n or "SHIV NADAR" in n or "ASHOKA" in n:
        return "Private"
    return "Other"


def clean_institution_name(name: str) -> str:
    """Ensure institution name does not contain semicolons and is normalized."""
    if not name or pd.isna(name):
        return ""
    # Semicolons are not allowed inside names because semicolon is our column delimiter
    clean = str(name).replace(";", ",").strip()
    return clean


def run_step_10() -> None:
    logger.info("Starting Step 10: Build Indian institution registry and compute coauthor_institutes...")

    interim_dir = Path("data/interim")
    config_dir = Path("config")
    review_dir = Path("data/review")

    authors_path = interim_dir / "paper_authors_attributed.parquet"
    assert authors_path.exists(), "paper_authors_attributed.parquet not found"

    df_authors = pd.read_parquet(authors_path)

    # 1. Collect all Indian institutions across the corpus
    inst_counts: Dict[str, int] = collections.defaultdict(int)
    inst_meta: Dict[str, Dict[str, Any]] = {}

    for ext_str in df_authors["external_coauthor_insts"].dropna():
        if not ext_str:
            continue
        try:
            for inst in json.loads(ext_str):
                if inst.get("country_code") == "IN":
                    name = clean_institution_name(inst.get("display_name"))
                    iid = inst.get("id")
                    if name and iid:
                        inst_counts[iid] += 1
                        if iid not in inst_meta:
                            inst_meta[iid] = {
                                "openalex_id": iid,
                                "ror": inst.get("ror") or "",
                                "canonical_name": name,
                                "short_name": name.split(",")[0].strip(),
                                "city": "",
                                "type": inst.get("type") or "education",
                                "sector_cluster": assign_sector_cluster(name, inst.get("type") or ""),
                            }
        except Exception:
            pass

    # Add our 3 assigned institutes to registry
    our_insts = [
        ("https://openalex.org/I3125981224", "https://ror.org/057mn3690", "CSIR - National Chemical Laboratory", "CSIR-NCL", "Pune", "CSIR"),
        ("https://openalex.org/I55664587", "https://ror.org/040dky007", "CSIR - Indian Institute of Chemical Technology", "CSIR-IICT", "Hyderabad", "CSIR"),
        ("https://openalex.org/I106349282", "https://ror.org/01qek3q18", "CSIR - Central Electrochemical Research Institute", "CSIR-CECRI", "Karaikudi", "CSIR"),
    ]
    for iid, ror, cname, sname, city, sector in our_insts:
        inst_meta[iid] = {
            "openalex_id": iid,
            "ror": ror,
            "canonical_name": cname,
            "short_name": sname,
            "city": city,
            "type": "government",
            "sector_cluster": sector,
        }

    # Save indian_inst_registry.csv
    registry_df = pd.DataFrame(list(inst_meta.values()))
    registry_path = config_dir / "indian_inst_registry.csv"
    registry_df.to_csv(registry_path, index=False)
    logger.info(f"Saved {len(registry_df)} Indian institutions to {registry_path}")

    # Save top 100 review
    top100_records = []
    for iid, count in sorted(inst_counts.items(), key=lambda x: x[1], reverse=True)[:100]:
        if iid in inst_meta:
            rec = dict(inst_meta[iid])
            rec["coauthorship_frequency"] = count
            top100_records.append(rec)
    df_top100 = pd.DataFrame(top100_records)
    df_top100.to_csv(review_dir / "inst_registry_review.csv", index=False)
    logger.info(f"Saved top 100 review institutions to {review_dir / 'inst_registry_review.csv'}")

    # Build canonical lookup: openalex_id -> canonical_name
    id_to_canonical = {iid: meta["canonical_name"] for iid, meta in inst_meta.items()}

    # 2. Derive coauthor_institutes per row
    # Rules:
    # Semicolon-separated list of canonical Indian institutions of co-authors,
    # excluding the row's own institute.
    # Sorted alphabetically, deduplicated.
    updated_rows: List[Dict[str, Any]] = []

    # Map our internal display names to exclusion strings
    our_own_canonical = {
        "CSIR-NCL": {"CSIR - National Chemical Laboratory", "National Chemical Laboratory", "CSIR-NCL"},
        "CSIR-IICT": {"CSIR - Indian Institute of Chemical Technology", "Indian Institute of Chemical Technology", "CSIR-IICT"},
        "CSIR-CECRI": {"CSIR - Central Electrochemical Research Institute", "Central Electrochemical Research Institute", "CSIR-CECRI"},
    }

    # Group paper co-authorships by work_id
    work_indian_insts: Dict[str, Set[str]] = collections.defaultdict(set)
    for _, row in df_authors.iterrows():
        wid = row["work_id"]
        inst_name = row["institution"]
        # Add internal coauthor institutes (e.g. if NCL and IICT co-authored)
        work_indian_insts[wid].add(inst_name)
        ext_str = row.get("external_coauthor_insts")
        if ext_str and not pd.isna(ext_str):
            try:
                for ext in json.loads(ext_str):
                    if ext.get("country_code") == "IN":
                        cname = id_to_canonical.get(ext.get("id")) or clean_institution_name(ext.get("display_name"))
                        if cname:
                            work_indian_insts[wid].add(cname)
            except Exception:
                pass

    for _, row in df_authors.iterrows():
        rec = row.to_dict()
        wid = row["work_id"]
        own_inst = row["institution"]
        own_exclusions = our_own_canonical.get(own_inst, {own_inst})

        all_insts = work_indian_insts.get(wid, set())
        # Filter out own institute
        filtered = [name for name in all_insts if name not in own_exclusions and name != own_inst]
        # Sort alphabetically
        filtered_sorted = sorted(list(set(filtered)))

        rec["coauthor_institutes"] = ";".join(filtered_sorted)
        updated_rows.append(rec)

    df_updated = pd.DataFrame(updated_rows)
    df_updated.to_parquet(authors_path, index=False)
    logger.info(f"✓ Updated {len(df_updated)} rows with coauthor_institutes in {authors_path}")

    # Inspect sample rows
    print("Sample coauthor_institutes values:")
    sample_coauth = df_updated[df_updated["coauthor_institutes"] != ""]["coauthor_institutes"].head(5)
    for s in sample_coauth:
        print("  -->", s)

    logger.info("✓ Step 10 complete successfully.")


if __name__ == "__main__":
    run_step_10()
