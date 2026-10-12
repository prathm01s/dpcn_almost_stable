"""Step 02: Build official scientific cadre faculty roster for NCL, IICT, and CECRI.

Extracts:
1. CSIR-NCL: from http://academic.ncl.res.in/alphascientist
2. CSIR-IICT: from https://www.iict.res.in/DEPARTMENTS & /SCIENTIFIC_STAFF
3. CSIR-CECRI: from Staff_Directory.pdf (extracted via pdftotext)

Output:
- data/interim/roster.parquet
- data/interim/roster.csv
"""

import datetime
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List
from bs4 import BeautifulSoup
import pandas as pd

from src.common.logging import get_logger
from src.common.names import clean_name

logger = get_logger("02_build_roster")

SCRAPED_AT = datetime.datetime.now(datetime.timezone.utc).isoformat()

CADRE_DESIGNATIONS = [
    "SCIENTIST",
    "SENIOR SCIENTIST",
    "PRINCIPAL SCIENTIST",
    "SENIOR PRINCIPAL SCIENTIST",
    "CHIEF SCIENTIST",
    "DIRECTOR",
    "DISTINGUISHED SCIENTIST",
    "OUTSTANDING SCIENTIST",
    "EMERITUS SCIENTIST",
    "SCIENTIST-C",
    "SCIENTIST-D",
    "SCIENTIST-E",
    "SCIENTIST-F",
    "SCIENTIST-G",
    "SCIENTIST - C",
    "SCIENTIST - D",
    "SCIENTIST - E",
    "SCIENTIST - F",
    "SCIENTIST - G",
]


def is_scientific_cadre(desig: str) -> bool:
    """Check if designation belongs to CSIR scientific staff."""
    d_up = desig.upper()
    if any(k in d_up for k in ["TECHNICAL OFFICER", "TECHNICIAN", "ASSISTANT", "CLERK", "TRANSLATOR", "SECTION OFFICER", "CONTROLLER"]):
        return False
    return any(cadre in d_up for cadre in CADRE_DESIGNATIONS)


def normalize_csir_designation(desig: str) -> str:
    """Normalize grade designations to canonical CSIR names."""
    d = desig.strip()
    d_up = d.upper()
    if "DIRECTOR" in d_up and "ASSISTANT" not in d_up:
        return "Director"
    if "EMERITUS" in d_up:
        return "Emeritus Scientist"
    if "DISTINGUISHED" in d_up:
        return "Distinguished Scientist"
    if "OUTSTANDING" in d_up:
        return "Outstanding Scientist"
    if "SCIENTIST-G" in d_up or "SCIENTIST - G" in d_up or "SCIENTIST – G" in d_up:
        return "Chief Scientist (Scientist-G)"
    if "SCIENTIST-F" in d_up or "SCIENTIST - F" in d_up or "SCIENTIST – F" in d_up:
        return "Chief Scientist (Scientist-F)"
    if "SCIENTIST-E" in d_up or "SCIENTIST - E" in d_up or "SCIENTIST – E" in d_up or "SR. PRINCIPAL SCIENTIST" in d_up:
        return "Senior Principal Scientist"
    if "SCIENTIST-D" in d_up or "SCIENTIST - D" in d_up or "SCIENTIST – D" in d_up or "PRINCIPAL SCIENTIST" in d_up:
        return "Principal Scientist"
    if "SCIENTIST-C" in d_up or "SCIENTIST - C" in d_up or "SCIENTIST – C" in d_up or "SENIOR SCIENTIST" in d_up:
        return "Senior Scientist"
    if "SCIENTIST" in d_up:
        return "Scientist"
    return d


def scrape_ncl() -> List[Dict[str, Any]]:
    """Scrape NCL roster from alphascientist.html."""
    logger.info("Scraping CSIR-NCL roster...")
    roster: List[Dict[str, Any]] = []
    html_path = Path("data/raw/roster/ncl/alphascientist.html")
    if not html_path.exists():
        url = "http://academic.ncl.res.in/alphascientist"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(html_path, "wb") as f:
                f.write(content)

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/profile/" in href:
            text = a.get_text(" | ", strip=True)
            # Example text: Dr. Akkattu T. Biju | Dr. Akkattu T. Biju | Unit: | Organic Chemistry Division | Contact Number: | 2441 | Email: | at.biju[at]ncl.res.in
            parts = [p.strip() for p in text.split("|") if p.strip()]
            full_name = parts[0] if parts else ""
            if not full_name or full_name in seen:
                continue
            seen.add(full_name)

            dept = ""
            for i, p in enumerate(parts):
                if "Unit:" in p and i + 1 < len(parts):
                    dept = parts[i + 1]
                    break
                elif "Unit:" in p:
                    dept = p.replace("Unit:", "").strip()

            email_domain = "ncl.res.in"
            clean_n = clean_name(full_name)

            roster.append({
                "inst_key": "ncl",
                "full_name": full_name,
                "name_norm": clean_n,
                "designation": "Scientist",  # Default scientific cadre
                "department": dept or "Chemistry / Chemical Engineering",
                "email_domain_only": email_domain,
                "profile_url": href,
                "scraped_at": SCRAPED_AT,
                "source_url": "http://academic.ncl.res.in/alphascientist",
                "status": "current",
            })

    logger.info(f"✓ CSIR-NCL: collected {len(roster)} scientists")
    return roster


def scrape_iict() -> List[Dict[str, Any]]:
    """Scrape IICT roster by querying DEPARTMENTS forms and SCIENTIFIC_STAFF."""
    logger.info("Scraping CSIR-IICT roster...")
    roster: List[Dict[str, Any]] = []
    seen = {}

    dept_inputs = [
        ("deptName1", "Dept. of Analytical & Structural Chemistry"),
        ("deptName2", "Applied Biology"),
        ("deptName3", "Catalysis & Fine Chemicals"),
        ("deptName4", "Dept. of Oils, Lipid Science & Technology"),
        ("deptName5", "Dept. of Energy & Environmental Engg."),
        ("deptName6", "Fluoro-Agrochemicals"),
        ("deptName7", "Dept. of Natural Products & Medicinal Chemistry"),
        ("deptName8", "Organic Synthesis & Process Chemistry"),
        ("deptName9", "Chemical Engg. & Process Technology (CE & PT)"),
        ("deptName99", "Polymers & Functional Materials"),
        ("deptName11", "Business Development & Research Management (BDRM)"),
        ("deptName12", "Centre for I.T. Services"),
        ("deptName13", "Knowledge and Information Management"),
    ]

    for key, dept_title in dept_inputs:
        url = "https://www.iict.res.in/DEPARTMENTS"
        try:
            data = urllib.parse.urlencode({key: dept_title}).encode()
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")
                for item in soup.find_all(class_="itemde"):
                    txt = item.get_text(" ", strip=True)
                    # Extract name and designation
                    # Example: Dr. B. SridharScientist-G
                    m = re.match(r"^(.*?)(Scientist-[A-Z]|Scientist - [A-Z]|Director|Distinguished Scientist|Outstanding Scientist)$", txt, re.IGNORECASE)
                    if m:
                        name, desig = m.group(1).strip(), m.group(2).strip()
                    else:
                        name, desig = txt, "Scientist"

                    if is_scientific_cadre(desig):
                        norm_d = normalize_csir_designation(desig)
                        clean_n = clean_name(name)
                        if clean_n not in seen:
                            rec = {
                                "inst_key": "iict",
                                "full_name": name,
                                "name_norm": clean_n,
                                "designation": norm_d,
                                "department": dept_title.replace("Dept. of ", "").strip(),
                                "email_domain_only": "iict.res.in",
                                "profile_url": "https://www.iict.res.in/SCIENTIFIC_STAFF",
                                "scraped_at": SCRAPED_AT,
                                "source_url": "https://www.iict.res.in/DEPARTMENTS",
                                "status": "current",
                            }
                            seen[clean_n] = rec
                            roster.append(rec)
        except Exception as e:
            logger.warning(f"Error fetching IICT {dept_title}: {e}")

    # Fallback to general SCIENTIFIC_STAFF page for any additional scientists
    staff_path = Path("data/raw/roster/iict/scientific_staff.html")
    if staff_path.exists():
        with open(staff_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for c in soup.find_all(class_="cardstall"):
            h2s = c.find_all(class_="card-titlestudall")
            if len(h2s) >= 2:
                name = h2s[0].get_text(strip=True)
                desig = h2s[1].get_text(strip=True)
                if is_scientific_cadre(desig):
                    clean_n = clean_name(name)
                    if clean_n not in seen:
                        norm_d = normalize_csir_designation(desig)
                        rec = {
                            "inst_key": "iict",
                            "full_name": name,
                            "name_norm": clean_n,
                            "designation": norm_d,
                            "department": "Chemical Sciences / Technology",
                            "email_domain_only": "iict.res.in",
                            "profile_url": "https://www.iict.res.in/SCIENTIFIC_STAFF",
                            "scraped_at": SCRAPED_AT,
                            "source_url": "https://www.iict.res.in/SCIENTIFIC_STAFF",
                            "status": "current",
                        }
                        seen[clean_n] = rec
                        roster.append(rec)

    logger.info(f"✓ CSIR-IICT: collected {len(roster)} scientists")
    return roster


def scrape_cecri() -> List[Dict[str, Any]]:
    """Parse CECRI roster from Staff_Directory.txt."""
    logger.info("Scraping CSIR-CECRI roster...")
    roster: List[Dict[str, Any]] = []
    txt_path = Path("data/raw/roster/cecri/Staff_Directory.txt")
    assert txt_path.exists(), "Staff_Directory.txt does not exist"

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    lines = [l.strip() for l in text.split("\n")]
    current_division = "General Electrochemistry"
    i = 0
    seen = set()

    while i < len(lines):
        line = lines[i]
        # Check if line indicates division header (uppercase with brackets or known divisions)
        if any(h in line for h in [
            "CORROSION AND MATERIALS PROTECTION",
            "ELECTROCHEMICAL POWER SOURCES",
            "ELECTROPLATING AND ELECTROMETALLURGY",
            "ELECTRODICS AND ELECTROCATALYSIS",
            "ELECTROCHEMICAL PROCESS ENGINEERING",
            "ELECTRO-ORGANIC & MATERIALS ELECTROCHEMISTRY",
            "CENTRAL INSTRUMENTATION FACILITY",
            "DIRECTOR’S TECHNICAL CELL",
            "DIRECTOR OFFICE",
            "CECRI CHENNAI UNIT",
            "CECRI MANDAPAM UNIT",
        ]):
            current_division = line.split("(")[0].strip()

        # Check if line has a scientist designation
        if any(line.upper().startswith(c) for c in [
            "SCIENTIST", "DIRECTOR", "EMERITUS SCIENTIST"
        ]):
            desig_line = line
            if is_scientific_cadre(desig_line):
                # The name typically appears 1 or 2 lines above
                name_line = ""
                for back in range(1, 4):
                    cand = lines[i - back]
                    if cand and not any(cand.upper().startswith(c) for c in ["SCIENTIST", "DIVISION", "PAGE", "SI NO"]):
                        name_line = cand
                        break

                if name_line:
                    clean_n = clean_name(name_line)
                    if clean_n and clean_n not in seen and len(clean_n.split()) >= 2:
                        seen.add(clean_n)
                        norm_d = normalize_csir_designation(desig_line)
                        roster.append({
                            "inst_key": "cecri",
                            "full_name": name_line,
                            "name_norm": clean_n,
                            "designation": norm_d,
                            "department": current_division,
                            "email_domain_only": "cecri.res.in",
                            "profile_url": "https://www.cecri.res.in",
                            "scraped_at": SCRAPED_AT,
                            "source_url": "https://www.cecri.res.in/Portals/0/rti/Staff_Directory.pdf",
                            "status": "current",
                        })
        i += 1

    logger.info(f"✓ CSIR-CECRI: collected {len(roster)} scientists")
    return roster


def run_step_02() -> None:
    logger.info("Starting Step 02: Build official scientific faculty roster...")
    interim_dir = Path("data/interim")
    interim_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = interim_dir / "roster.parquet"
    csv_path = interim_dir / "roster.csv"

    if parquet_path.exists() and csv_path.exists():
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded existing roster ({len(df)} faculty members) from {parquet_path}")
        logger.info("✓ Step 02 complete successfully (re-used existing roster).")
        return

    all_roster: List[Dict[str, Any]] = []

    all_roster.extend(scrape_ncl())
    all_roster.extend(scrape_iict())
    all_roster.extend(scrape_cecri())

    df = pd.DataFrame(all_roster)
    logger.info(f"Total roster size: {len(df)} faculty members across all 3 institutes")
    print(df["inst_key"].value_counts())

    interim_dir = Path("data/interim")
    interim_dir.mkdir(parents=True, exist_ok=True)

    csv_path = interim_dir / "roster.csv"
    parquet_path = interim_dir / "roster.parquet"

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    logger.info(f"Saved roster to {csv_path} and {parquet_path}")
    logger.info("✓ Step 02 complete successfully.")


if __name__ == "__main__":
    run_step_02()
