"""Write SOURCES.md: every external source the Group 24 data comes from.

The narrative sections are fixed text; the journal and conference appendix is generated
from data/final/group24_data_extended.csv so it always matches the dataset.

Usage: python3 scripts/make_sources_md.py   (run from dpcn_a2/)
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

OUT = Path("SOURCES.md")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md(text: str) -> str:
    return str(text).replace("|", "\\|").strip()


def venue_table(papers: pd.DataFrame) -> str:
    rows = []
    named = papers[papers["journal_name"] != ""]
    for (name, source_id), g in named.groupby(["journal_name", "source_id"]):
        issn = next((i for i in g["issn"] if i), "")
        rows.append((name, issn, source_id.replace("https://openalex.org/", ""), len(g)))
    rows.sort(key=lambda r: (-r[3], r[0].lower()))
    lines = ["| Venue | ISSN | OpenAlex source | Papers |", "|---|---|---|---:|"]
    lines += [f"| {md(n)} | {i} | [{s}](https://openalex.org/{s}) | {c} |" for n, i, s, c in rows]
    return "\n".join(lines)


def main() -> None:
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    papers = ext.drop_duplicates("work_id")
    manifest = json.loads(Path("data/MANIFEST.json").read_text())
    journals = papers[papers["type"] == "journal"]
    confs = papers[papers["type"] == "conference"]
    # A venue = (name, OpenAlex source); a few names map to two sources
    n_journals = len(journals.loc[journals["journal_name"] != "", ["journal_name", "source_id"]].drop_duplicates())
    n_confs = len(confs.loc[confs["journal_name"] != "", ["journal_name", "source_id"]].drop_duplicates())
    unnamed_j = int((journals["journal_name"] == "").sum())
    unnamed_c = int((confs["journal_name"] == "").sum())
    match = papers.loc[papers["type"] == "journal", "quartile_match_method"].value_counts().to_dict()
    sjr_hash = sha256(Path("data/external/sjr_journals.rda"))

    text = f"""# Data Sources — Group 24

**DPCN Research Mapping Project 2026** · CSIR-NCL (Pune), CSIR-IICT (Hyderabad), CSIR-CECRI (Karaikudi) · publications 2016–2026

This file lists every source the Group 24 dataset, statistics report and dashboard were built from.
All {len(papers):,} papers, their DOIs, citation counts, authors, affiliations and research topics come from **OpenAlex**.
The faculty roster comes from the three institutes' **official websites**, and journal quartiles from **SCImago Journal Rank**.
No data was taken from other groups.

## 1. Summary

| Source | What we took from it | Accessed |
|---|---|---|
| [OpenAlex](https://openalex.org) (API `https://api.openalex.org`) | Papers 2016–2026, DOIs, citation counts, authors and affiliations, journals/conferences, topics, references and citing works, author career histories | {manifest['collection_date']} (corpus); {manifest['indian_links_collected_at'][:10]} (links with other Indian institutions); October 2026 (Insights fetches) |
| [ROR](https://ror.org) (Research Organization Registry, API v2) | Persistent identifiers of the three labs and CSIR, used to find their OpenAlex IDs; RORs of partner institutions | {manifest['collection_date']} |
| Institute websites (NCL, IICT, CECRI) | Faculty roster: names, designations, departments/divisions | October 2026 |
| [SCImago Journal Rank](https://www.scimagojr.com), via the [`sjrdata`](https://github.com/ikashnitsky/sjrdata) package | Journal best quartile (Q1–Q4) per year | October 2026 |
| [CORE conference rankings](https://portal.core.edu.au/conf-ranks/) | Not imported: conference papers are left unranked (see §6) | — |

## 2. OpenAlex (primary source)

OpenAlex is an open catalogue of scholarly works (data released under CC0). We queried its REST API through our own
client (`src/common/openalex.py`): cursor paging, `select=` to fetch only the needed fields, and every response cached
so re-runs make no new calls. Default corpus (`core`).

**Institution IDs**

| Lab | OpenAlex | ROR |
|---|---|---|
| CSIR-NCL | [I3125981224](https://openalex.org/I3125981224) | [057mn3690](https://ror.org/057mn3690) |
| CSIR-IICT | [I55664587](https://openalex.org/I55664587) | [040dky007](https://ror.org/040dky007) |
| CSIR-CECRI | [I106349282](https://openalex.org/I106349282) | [01qek3q18](https://ror.org/01qek3q18) |
| CSIR (parent, recall check only) | [I66760702](https://openalex.org/I66760702) | [021wm7p51](https://ror.org/021wm7p51) |

**Queries**

| Purpose | Endpoint and filter | Pipeline step |
|---|---|---|
| Resolve each lab's OpenAlex entity from its ROR | `/institutions?filter=ror:<ROR>` | `src/collect/01_resolve_institutions.py` |
| Yearly reference counts per lab | `/works?filter=authorships.institutions.id:<ID>,publication_year:2016-2026&group_by=publication_year` | 01 |
| All works per lab and year, 2016–2026 | `/works?filter=authorships.institutions.id:<ID>,publication_year:<year>` | `03_pull_works.py` |
| Papers tagged only with the CSIR parent whose affiliation text names a lab | `/works?filter=authorships.institutions.id:I66760702,raw_affiliation_strings.search:<lab name>` | `04_recall_boosters.py` |
| References and authorships of our papers | `/works?filter=openalex_id:W1\\|…\\|W100` | `17_indian_links_api.py`, `18_reference_counts.py` |
| Indian-affiliated papers our papers cite | `/works?filter=cited_by:W1\\|…,authorships.countries:IN` | 17 |
| Indian-affiliated papers citing our papers | `/works?filter=cites:W1\\|…,authorships.countries:IN` | 17 |
| Yearly citations of candidate "sleeping beauties" (Insight 7) | `/works?filter=openalex_id:…&select=id,publication_year,counts_by_year` | `fetch_counts_by_year.py` |
| Full career histories of roster scientists (Insights 9–10) | `/works?filter=authorships.author.id:<A…>` | `fetch_author_careers.py` |

**Fields used**: work ID, DOI, title, publication year, type, `cited_by_count` (the `citations` column), authorships
(author IDs and names, institutions with ROR and country, raw affiliation strings), primary location (journal or
conference source, ISSN), primary topic (topic, subfield, field, domain), `referenced_works`, `counts_by_year`.

## 3. Institute websites (faculty roster)

Scientific-cadre faculty (Scientist to Chief Scientist and Director) were taken from each lab's official staff
listing, then matched to OpenAlex author IDs (`02_build_roster.py`, `07_match_faculty.py`, `19_roster_cleanup.py`).

| Lab | Page | Taken |
|---|---|---|
| CSIR-NCL | [academic.ncl.res.in/alphascientist](http://academic.ncl.res.in/alphascientist) | Scientist list with division |
| CSIR-IICT | [iict.res.in/DEPARTMENTS](https://www.iict.res.in/DEPARTMENTS), [iict.res.in/SCIENTIFIC_STAFF](https://www.iict.res.in/SCIENTIFIC_STAFF) | Scientists by R&D department |
| CSIR-CECRI | [Staff Directory PDF](https://www.cecri.res.in/Portals/0/rti/Staff_Directory.pdf) (cecri.res.in, RTI section) | Scientists and divisions, extracted with `pdftotext` |

Manual roster corrections (duplicate listings, wrong author matches) are listed with reasons and dates in
`config/overrides/roster_overrides.csv`; excluded non-faculty entries are in `data/review/roster_excluded.csv`.

## 4. Journal quartiles — SCImago Journal Rank (SJR)

- **Data**: `sjr_journals.rda` from the [`sjrdata`](https://github.com/ikashnitsky/sjrdata) R package v1.0.25
  (I. Kashnitsky), which redistributes SCImago's yearly journal rankings from [scimagojr.com](https://www.scimagojr.com)
  (SCImago, based on Scopus data). Stored as `data/external/sjr_journals.rda`, SHA-256 `{sjr_hash}`
  (identical to the file in the package's GitHub repository).
- **Use**: a paper's `quartile` is the journal's SJR *best quartile* in the paper's publication year, matched on ISSN
  (`08_resolve_quartiles.py`). 2026 papers use the 2025 ranking; a journal missing in that year takes the nearest year
  within ±2. Of {len(journals):,} journal papers: {match.get('issn', 0):,} matched by ISSN, {match.get('nearest_year', 0):,} by
  nearest year, {match.get('none', 0):,} unranked.
- `data/external/scimagojr_2023.csv` (the 2023 export downloaded from scimagojr.com) is kept for reference but not
  used by the pipeline.

## 5. Indian institutions

Co-author and citing/cited institutions are OpenAlex institution records with country code `IN`, identified by
their ROR IDs. `config/indian_inst_registry.csv` lists them with a sector label (IIT, NIT, CSIR, DAE, university, …)
assigned from the institution name by `src/common/sectors.py`.

## 6. Conference ranks — CORE

The assignment asks for CORE ranks (A*/A/B/C) for conference papers. CORE ranks mainly computer-science venues, and
no CORE rankings file was imported, so the `quartile` column is blank for all {len(confs)} conference papers
(Appendix B lists their venues).

## 7. Sources not used

Scopus, Web of Science / JCR quartiles, Google Scholar, IRINS/VIDWAN and Crossref were not used as data sources.
DOIs are as recorded by OpenAlex.

## Appendix A — Journals ({n_journals:,})

Every journal in which at least one of the {len(papers):,} papers appeared, with the number of distinct papers.
Names, ISSNs and source IDs are from OpenAlex.{f" {unnamed_j} journal papers have no venue name in OpenAlex." if unnamed_j else ""}

{venue_table(journals)}

## Appendix B — Conferences and proceedings ({n_confs})

{f"{unnamed_c} conference papers have no venue name in OpenAlex." if unnamed_c else ""}

{venue_table(confs)}
"""
    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB): {n_journals} journals, {n_confs} conferences")


if __name__ == "__main__":
    main()
