# Group 24 — Week 1–2 Submission: Dataset + Network Files

**DPCN Course Project 2026** · Instructor: Chittaranjan Hens
**Cluster:** CSIR Labs — Synthetic & Organic Chemistry
**Institutions:** CSIR-NCL (Pune, ROR `057mn3690`) · CSIR-IICT (Hyderabad, ROR `040dky007`) · CSIR-CECRI (Karaikudi, ROR `01qek3q18`)
**Data:** OpenAlex, queried by ROR-verified institution IDs. Papers and citation counts collected 13 October 2026; links with other Indian institutions collected 20 October 2026. **Years:** 2016–2026 (2026 is a partial year).

## Files

| File | Rows | Columns |
|---|---|---|
| `group24_data.csv` | 42,393 | group, institution, author, title, year, type, journal_name, issn, doi, citations, quartile, coauthor_institutes, cites_indian_inst, cited_by_indian_inst |
| `citation_network.csv` | 192,994 | source_doi, target_doi, source_inst, target_inst, year |
| `authorship_network.csv` | 108,847 | author_a, author_b, paper_doi, inst_a, inst_b, year |
| `indian_connections.csv` | 1,487 | your_inst, partner_inst, shared_papers, total_citations |
| `faculty_master.csv` (supporting) | 505 | Faculty list from official institute websites: name, designation, department, OpenAlex author ID, h-index (2016–2026 papers), papers, citations, match confidence |

All files are UTF-8 CSV with LF line endings. `CHECKSUMS.sha256` lists the SHA-256 of each file.

## Coverage

| Institution | Distinct papers | Rows in `group24_data.csv` |
|---|---|---|
| CSIR-IICT | 6,167 | 20,183 |
| CSIR-NCL | 5,404 | 14,726 |
| CSIR-CECRI | 2,885 | 7,484 |
| **All three (distinct papers)** | **14,352** | **42,393** |

Kept: journal articles, reviews, letters and conference papers (14,166 journal + 186 conference papers). Excluded: editorials, errata, preprints, book chapters, datasets.

## How to read `group24_data.csv`

- **One row per (paper × author from one of our three institutes).** A paper with four NCL authors has four rows. Count papers by distinct DOI/title, and never sum `citations` across rows.
- **author:** every author OpenAlex attributes to the institute (faculty, students and project staff). The faculty-only list is in `faculty_master.csv`.
- **citations:** OpenAlex `cited_by_count` on 13 Oct 2026.
- **quartile:** SCImago (SJR) best quartile of the journal in the paper's publication year. 2026 papers use the 2025 SJR values. 63.3% of journal papers with a known quartile are Q1. 5.5% of rows have a blank quartile (journals not in SJR, plus all conference papers).
- **Conference rank:** none of the 186 conference papers appears in the CORE ranking. CORE ranks computer-science venues, and these are chemistry/electrochemistry proceedings. So `quartile` is blank for conferences.
- **coauthor_institutes:** Indian institutions of the paper's co-authors, excluding the row's own institute, separated by `;`. Our other two labs appear as `CSIR-NCL` / `CSIR-IICT` / `CSIR-CECRI`.
- **cites_indian_inst / cited_by_indian_inst:** TRUE when the paper cites (or is cited by) a paper that involves an Indian institution other than the row's own institute. This covers papers inside our corpus and Indian-affiliated papers outside it. TRUE for 88.3% / 73.4% of papers. Every TRUE can be traced to a row of `citation_network.csv`.

## Network files

- **citation_network.csv:** directed edges "source cites target", from OpenAlex `referenced_works`. `year` is the citing paper's year.
  - **27,754 edges** link two papers of our corpus (`source_inst` / `target_inst` = the lab). 1,653 of these cross between our labs.
  - **165,240 edges** link one of our papers with a DOI-bearing paper outside the corpus that has an Indian author institution. On the outside side, the inst column lists that paper's Indian institutions separated by `;`.
  - A paper attributed to two of our labs appears once per lab.
- **authorship_network.csv:** undirected edges between two co-authors of the same paper. `author_a` is always from one of our labs (`inst_a`).
  - **65,058 edges** join two authors of our labs (7,864 authors; 525 edges cross labs).
  - **43,789 edges** join our authors to co-authors at other Indian institutions (`inst_b`).
  - Authors are identified by name. `paper_doi` is blank for the few papers without a DOI.
- **indian_connections.csv:** for each of our labs, every Indian partner institution it co-authored with (899 distinct partners). `shared_papers` is the number of distinct joint papers. `total_citations` is the sum of those papers' citations. Partners include the other two Group 24 labs, AcSIR, and CSIR headquarters as recorded by OpenAlex.

Network analysis (PageRank, centralities, communities) uses only the edges within our three labs. The edges to other Indian institutions are raw data, as the instruction note asks.

## Known limitations

- OpenAlex affiliation and author matching is imperfect. Some papers may be missing or mis-attributed, and an author can be split or merged across profiles.
- Citation links to papers without a DOI are not included. "Indian" is based on OpenAlex institution country codes.
- 2026 is partial, covering data to 13 October 2026.
- No data was shared with or taken from other groups.
