# Group 24 — Week 3 Submission: Statistics Report + Interactive Dashboard

**DPCN Course Project 2026** · Instructor: Chittaranjan Hens
**Cluster:** CSIR Labs — Synthetic & Organic Chemistry · CSIR-NCL (Pune), CSIR-IICT (Hyderabad), CSIR-CECRI (Karaikudi)
**Live dashboard:** https://prathm01s.github.io/dpcn_almost_stable/
**Data:** OpenAlex, 2016 – 13 Oct 2026 (2026 partial). The dataset and network files were submitted in Week 1–2 and are included again here so the dashboard's download buttons work.

## Contents

| Path | What it is |
|---|---|
| `Group24_CSIR.pdf` | Statistics report, 10 slides (PDF) |
| `Group24_CSIR.pptx` | Same report, editable PowerPoint |
| `dashboard/index.html` | Interactive dashboard. **Double-click to open**; it works offline with no server or internet. |
| `data/final/`, `data/MANIFEST.json` | Dataset and network CSVs that the dashboard's "Data & Exports" tab links to |
| `stats/report/` | Copy of the report that the dashboard links to |
| `CHECKSUMS.sha256` | SHA-256 of every file |

## Statistics report (10 slides)

| Slide | Content |
|---|---|
| 1 | Title, scope and headline numbers |
| 2 | Data coverage and method; limitations |
| 3 | Publication trend 2016–2026 per institute; growth (CAGR 2016→2025) |
| 4 | Journal quartile distribution and Q1 fraction per institution; **Q1 by citation impact ratio** (citations received ÷ citations made; IR-Q1 = top 25% of papers, IR > 0.59) compared with SJR Q1 |
| 5 | Faculty h-index distribution; top faculty |
| 6 | Top 5 journals for each institution |
| 7 | Top 10 most-cited papers; citation summary |
| 8 | Research-area breakdown; department performance |
| 9 | **Citation network summary:** PageRank top 10, in-degree distribution, citation flow with other Indian institutions |
| 10 | **Authorship network summary:** degree and betweenness centrality, Louvain communities, Indian partners |

Every number in the report is generated from the project's statistics tables, which also feed the dashboard, so the two agree. An automated test checks this.

## Dashboard panels

| Required panel | Where in the dashboard |
|---|---|
| Publication trend chart | Overview & Trends → Panel 1 |
| Faculty list (name, department, h-index, total papers) | Faculty & Divisions → Panel 2 & 4 |
| Journal quartile distribution | Overview & Trends → Panel 3; impact-ratio Q1 panel below it |
| Faculty performance table (sortable) | Faculty & Divisions → Panel 2 & 4 |
| Top journals | Venues & Landmark Papers → Panel 5 |
| h-index distribution | Faculty & Divisions → Panel 6 |
| Research area breakdown | Thematic Domains → Panel 7 (plus subfields) |
| Most-cited papers (top 10) | Venues & Landmark Papers → Panel 8 |
| Conference rank (CORE) | Venues & Landmark Papers → Panel 9 (none of the 186 conference papers is CORE-ranked; CORE covers computer-science venues) |
| Citation network visualisation (directed) | Directed Citation Network → Panel 10, with PageRank table and 3 × 3 lab flow matrix |
| Authorship network visualisation (undirected) | Co-Authorship Network → Panel 11, with centrality table and 3 × 3 lab matrix |

Extras:

- **Indian Connectivity tab:** year-wise citation flow, top citing Indian institutes, partner sectors (CSIR ↔ IIT, etc.), topic Jaccard similarity, and hub authors.
- **Data & Exports tab:** definitions and downloads.
- **Filters:** the institute selector (each lab, all three, compare) and the year, type, quartile and field filters apply across panels.

## Notes

- **Units:** papers are counted once per institute; "All three" counts distinct papers. h-index is computed from 2016–2026 papers in the corpus.
- **Network scope:** network analysis is restricted to the three labs. Links to other Indian institutions are raw data (Week 1–2 files) and drive the Indian Connectivity tab.
