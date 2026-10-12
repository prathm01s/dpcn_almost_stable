"""Step 01: Resolve and verify institutions via ROR v2 API and OpenAlex API.

Produces:
- data/raw/ror/{inst}.json
- data/review/institution_candidates.csv
- data/interim/openalex_yearly_counts.csv
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import yaml

from src.common.http import http_client
from src.common.logging import get_logger

logger = get_logger("01_resolve_institutions")


def run_step_01() -> None:
    logger.info("Starting Step 01: Resolve and verify institutions...")

    with open("config/institutions.yaml", "r", encoding="utf-8") as f:
        inst_config = yaml.safe_load(f)

    ror_raw_dir = Path("data/raw/ror")
    ror_raw_dir.mkdir(parents=True, exist_ok=True)
    interim_dir = Path("data/interim")
    interim_dir.mkdir(parents=True, exist_ok=True)
    review_dir = Path("data/review")
    review_dir.mkdir(parents=True, exist_ok=True)
    yearly_counts_path = interim_dir / "openalex_yearly_counts.csv"
    candidates_path = review_dir / "institution_candidates.csv"

    if yearly_counts_path.exists() and candidates_path.exists():
        logger.info(f"Loaded existing outputs from {yearly_counts_path} and {candidates_path}")
        logger.info("✓ Step 01 complete successfully (re-used existing verification).")
        return

    candidates = []
    yearly_counts = []

    for inst_key, meta in inst_config.items():
        ror_url = meta.get("ror")
        if not ror_url:
            continue

        ror_id = ror_url.split("/")[-1]
        display_name = meta.get("display_name", inst_key)
        expected_city = meta.get("city", "")

        logger.info(f"Verifying {display_name} (ROR: {ror_id})...")

        # 1. ROR v2 API
        ror_api_url = f"https://api.ror.org/v2/organizations/{ror_url}"
        ror_data = http_client.get_json(ror_api_url, use_cache=True)

        with open(ror_raw_dir / f"{inst_key}.json", "w", encoding="utf-8") as f:
            json.dump(ror_data, f, indent=2)

        # Assertions on ROR
        locations = ror_data.get("locations", [])
        assert len(locations) > 0, f"No locations found for {inst_key} in ROR"
        loc_details = locations[0].get("geonames_details", {})
        country_code = loc_details.get("country_code")
        city_name = loc_details.get("name")
        assert country_code == "IN", f"Expected country IN for {inst_key}, got {country_code}"
        if expected_city:
            assert expected_city.lower() in city_name.lower() or city_name.lower() in expected_city.lower(), (
                f"City mismatch for {inst_key}: expected {expected_city}, got {city_name}"
            )

        logger.info(f"✓ ROR verified: {display_name} in {city_name}, {country_code}")

        # 2. OpenAlex Institutions filter by ROR
        oa_inst_url = "https://api.openalex.org/institutions"
        oa_data = http_client.get_json(oa_inst_url, params={"filter": f"ror:{ror_url}"}, use_cache=True)
        results = oa_data.get("results", [])
        assert len(results) > 0, f"No OpenAlex institution found for ROR {ror_url}"

        for r in results:
            cand = {
                "inst_key": inst_key,
                "display_name": display_name,
                "openalex_id": r.get("id"),
                "oa_display_name": r.get("display_name"),
                "country_code": r.get("country_code"),
                "ror": r.get("ror"),
                "works_count": r.get("works_count"),
                "cited_by_count": r.get("cited_by_count"),
                "decision": "accept",
                "reason": "Exact ROR match",
            }
            candidates.append(cand)
            oa_id = r.get("id")

            # 3. Reference yearly counts (2016-2026)
            works_group_url = "https://api.openalex.org/works"
            params = {
                "filter": f"authorships.institutions.id:{oa_id},publication_year:2016-2026",
                "group_by": "publication_year",
            }
            group_data = http_client.get_json(works_group_url, params=params, use_cache=True)
            for item in group_data.get("group_by", []):
                yearly_counts.append({
                    "inst_key": inst_key,
                    "institution": display_name,
                    "openalex_id": oa_id,
                    "year": int(item.get("key")),
                    "count": item.get("count"),
                })

    # Save institution_candidates.csv
    cand_df = pd.DataFrame(candidates)
    cand_df.to_csv(review_dir / "institution_candidates.csv", index=False)
    logger.info(f"Saved {len(cand_df)} candidates to {review_dir / 'institution_candidates.csv'}")

    # Save openalex_yearly_counts.csv
    yearly_df = pd.DataFrame(yearly_counts).sort_values(by=["institution", "year"])
    yearly_df.to_csv(interim_dir / "openalex_yearly_counts.csv", index=False)
    logger.info(f"Saved yearly baseline counts to {interim_dir / 'openalex_yearly_counts.csv'}")

    logger.info("✓ Step 01 complete successfully.")


if __name__ == "__main__":
    run_step_01()
