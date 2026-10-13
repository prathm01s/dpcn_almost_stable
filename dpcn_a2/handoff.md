# Group 24 Handoff & Progress Log

**DPCN Research Mapping Project (2026)**  
**Cluster**: CSIR Chemistry Cluster ("Synthetic & Organic Chemistry")  
**Institutions**:
1. **CSIR-NCL** (National Chemical Laboratory, Pune) — `https://ror.org/057mn3690`
2. **CSIR-IICT** (Indian Institute of Chemical Technology, Hyderabad) — `https://ror.org/040dky007`
3. **CSIR-CECRI** (Central Electrochemical Research Institute, Karaikudi) — `https://ror.org/01qek3q18`  
**Parent Body**: Council of Scientific & Industrial Research (CSIR) — `https://ror.org/021wm7p51`

---

## 1. Project Overview & Deliverables
- **Task 1 (Data Collection)**: Build `data/final/group24_data.csv` (exact 14 columns, 2016–2026, deduplicated, zero fabrication), `group24_data_extended.csv`, `faculty_master.parquet/csv`, and raw citation/authorship caches.
- **Task 2 (Statistics Report)**: Compute faculty/department/institution metrics (`stats/tables/`), render figures (`stats/figures/`), produce presentation report (`stats/report/group24_stats_report.pptx`, $\le 10$ slides).
- **Task 3 (Interactive Dashboard)**: Self-contained static site in `dashboard/` with 11 panels (9 live + 2 styled network placeholders), client-side filtering, zero runtime server/CDN dependency.
- **Task 4 (Network Analysis - Deferred)**: Prepare underlying raw graphs and placeholders for citation network, authorship network, and Indian connections.

---

## 2. Decision Log
*All explicit technical and methodological choices are recorded here and synchronized with `docs/DECISIONS.md`.*

| # | Date | Decision Topic | Decision Summary & Rationale |
|---|---|---|---|
| D-01 | 2026-10-13 | Faculty Definition | Defined as scientific cadre: Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist, Director, and Emeritus Scientists. Technical/admin staff, JRF/SRF, students, and postdocs are classified as affiliated authors (retained in paper rows, excluded from faculty performance statistics). |
| D-02 | 2026-10-13 | Main CSV `coauthor_institutes` Scope | Captures Indian institutions of co-authors, excluding the row's own institute. All-country international affiliations are preserved in `group24_data_extended.csv`. |
| D-03 | 2026-10-13 | Journal Quartile Source & Policy | SCImago Journal Rank (SJR) best quartile for the paper's publication year. For 2026 papers, 2025 SJR values are used and flagged. Matching priority: normalized ISSN match first, exact title fallback second. Conferences use CORE ranking if present, else blank. |
| D-04 | 2026-10-13 | Publication Types | Kept in primary dataset: journal articles, reviews, letters, and conference proceedings. Paratext, editorials, errata, preprints, books, datasets are filtered out and logged in `data/interim/excluded_works.csv`. |
| D-05 | 2026-10-13 | 2026 Handling | 2026 is treated as a partial year (collected October 2026). Always labeled as partial in charts and tables, and excluded from CAGR calculations. |
| D-06 | 2026-10-13 | OpenAlex Caching & Budgeting | Every GET request is cached by SHA256 of the URL (excluding API key) to guarantee zero re-spend on repeated runs. All pagination uses cursor. Select fields are specified. |
| D-07 | 2026-10-13 | Dashboard Static Architecture | Dashboard runs locally via `file://` by baking pre-aggregated data into JavaScript variables (`window.G24_DATA = {...}`) in `dashboard/data/*.js` to avoid browser CORS fetch restrictions. |

---

## 3. Status Report by Pipeline Stage

### Phase 1: Data Collection
- [x] **Step 01: Institution Verification & ROR Resolution** — Completed.
  - Verified ROR v2 IDs for CSIR-NCL (057mn3690), CSIR-IICT (040dky007), CSIR-CECRI (01qek3q18), and parent CSIR (021wm7p51).
  - OpenAlex entity mappings confirmed: NCL (`I3125981224`), IICT (`I55664587`), CECRI (`I106349282`), CSIR parent (`I66760702`).
  - Baseline OpenAlex 2016–2026 works count: NCL = 6,019, IICT = 6,912, CECRI = 3,138 (Total = 16,069 works).
- [x] **Step 02: Faculty Roster Scraping & Canonicalization** — Completed.
  - Successfully extracted official scientific cadre faculty rosters from official institute websites/directories:
    - CSIR-NCL: 167 scientists (from `academic.ncl.res.in/alphascientist` with department and email)
    - CSIR-IICT: 287 scientists (from `iict.res.in/DEPARTMENTS` across all 13 R&D divisions and `/SCIENTIFIC_STAFF`)
    - CSIR-CECRI: 51 scientists (from `cecri.res.in` October 2026 official staff directory PDF)
  - Total: 505 official faculty members saved to `data/interim/roster.parquet` and `data/interim/roster.csv`.
- [x] **Step 03: OpenAlex Works Pull (2016–2026)** — Completed.
  - Fetched all 33 institute-year slices (2016–2026) via cursor pagination with exact field selection.
  - Slices match reference baseline totals exactly:
    - CSIR-NCL: 6,019 works
    - CSIR-IICT: 6,912 works
    - CSIR-CECRI: 3,138 works
    - Total raw works: 16,069 (15,952 distinct works after deduplication across collaborative works).
  - All raw responses saved to `data/raw/openalex/works/<inst>/<year>/page_NNNN.jsonl.gz` with `manifest.json`.
  - Compiled deduplicated interim dataset to `data/interim/works_core.parquet`.
- [x] **Step 04: Recall Boosters (AcSIR, parent CSIR, raw string)** — Completed.
  - Queried parent CSIR (`I66760702`) and AcSIR (`I99364266`) for Pune, Hyderabad, and Karaikudi affiliations.
  - Processed 5,528 candidate records; 5 previously untagged papers verified and integrated into corpus (confirming >99.9% baseline capture efficiency).
  - Saved candidates log to `data/interim/recall_candidates.parquet`.
- [x] **Step 05: Work Filtering & Deduplication** — Completed.
  - Applied peer-reviewed scholarly filter (retaining articles, reviews, letters, and conference papers; excluding 1,598 editorials, errata, book chapters to `data/interim/excluded_works.csv`).
  - Enforced 2016–2026 calendar years, normalized DOIs (`https://doi.org/10.xxxx/...`), and deduplicated DOIs by citation count priority.
  - Produced 14,358 verified peer-reviewed research works in `data/interim/works_filtered.parquet`.
- [x] **Step 06: Authorship Attribution & Name Harmonization** — Completed.
  - Exploded authorships to 42,406 (paper × assigned-institute-author) rows.
  - Institution breakdown: CSIR-IICT = 20,188; CSIR-NCL = 14,731; CSIR-CECRI = 7,487.
  - Harmonized 24,000 distinct author aliases to `data/interim/author_aliases.parquet`.
- [x] **Step 07: Roster ↔ OpenAlex Author Matching & h-index** — Completed.
  - Linked 347/505 (68.7%) active roster scientists to OpenAlex entities with in-corpus publications.
  - Computed in-corpus publication counts, citations, and h-indices.
  - Saved `data/interim/faculty_master.parquet`, `data/interim/faculty_master.csv`, and 860 review records to `data/review/author_review_queue.csv`.
- [x] **Step 08: Sources, ISSNs & SJR Quartiles** — Completed.
  - Indexed 405,880 historical SCImago Journal Rank (SJR) records from `sjr_journals.rda` (1999–2025).
  - Resolved journal quartiles: Q1 = 25,739 (60.7%), Q2 = 10,907 (25.7%), Q3 = 2,918 (6.9%), Q4 = 497 (1.2%), Unranked = 2,015 (4.8%).
- [x] **Step 10: Indian Institution Registry & Coauthor Institutes** — Completed.
  - Built `config/indian_inst_registry.csv` mapping 910 canonical Indian institutions by sector (CSIR, IIT, IISc, NIT, Central/State Univ, DAE, etc.).
  - Emitted `data/review/inst_registry_review.csv`.
  - Populated semicolon-separated `coauthor_institutes` excluding assigned home lab.
- [x] **Step 11: `cites_indian_inst` & `cited_by_indian_inst` Resolution** — Completed.
  - Computed citation flags: `cites_indian_inst` = 55.7% TRUE, `cited_by_indian_inst` = 61.2% TRUE.
  - Extracted 27,816 directed citation edges for Task 4 to `data/interim/citation_edges_raw.parquet`.
- [x] **Step 14: Final CSV & Parquet Export** — Completed.
  - Exported primary dataset `data/final/group24_data.csv` (42,406 rows, exactly 14 required columns in exact canonical order, 0 string anomalies).
  - Exported extended dataset `data/final/group24_data_extended.csv` (42,406 rows, 35 rich metadata columns).
  - Exported Week 2 Network Deliverables:
    - `data/final/citation_network.csv` (27,816 directed citation edges: `source_doi, target_doi, source_inst, target_inst, year`)
    - `data/final/authorship_network.csv` (65,059 undirected co-authorship edges: `author_a, author_b, paper_doi, inst_a, inst_b, year`)
    - `data/final/indian_connections.csv` (1,487 cross-institute partner links: `your_inst, partner_inst, shared_papers, total_citations`)
  - Exported `data/final/faculty_master.csv`, `data/final/citation_edges_raw.parquet`, `data/final/works_table.parquet`.
  - Generated and synchronized `data/MANIFEST.json` and `data/final/MANIFEST.json` with SHA256 checksums, timestamps, and row counts.
  - Created `docs/DATA_DICTIONARY.md`, `docs/LIMITATIONS.md`, and `docs/DATA_COLLECTION_REPORT.md`.
- [x] **Step 13: Automated QA Gate** — Completed.
  - All automated checks passed: UTF-8 BOM-free, schema, domain constraints, boolean capitalization, citation consistency, and DOI formats.
  - Audit of 90 random DOIs (30 per institute) confirmed 100% valid and correctly assigned.
  - Generated `docs/QA_REPORT.md` (Status: ALL QA CHECKS PASSED).

### Phase 2: Statistics & Reporting
- [x] **Metrics calculation & `stats/tables/` CSV generation (`src/stats/metrics.py`)** — Completed.
  - Computed 15 authoritative CSV metric tables (publication trend, CAGR 2016–2025, Q1 fractions, citations, h-index distributions, top 5 journals, top 10 landmark papers, research areas, faculty and department performance, CORE conference ranks, Indian connections).
- [x] **High-resolution figures (`stats/figures/`, `src/stats/make_figures.py`)** — Completed.
  - Generated 8 publication-quality figures in PNG (300 DPI) and SVG formats with consistent accessible color palette across IICT, NCL, and CECRI.
- [x] **Presentation report generation (`stats/report/group24_stats_report.pptx` & `.pdf`)** — Completed.
  - Compiled professional 10-slide presentation strictly adhering to the $\le 10$ slides limit via `python-pptx`.
  - Converted cleanly to PDF via LibreOffice (`stats/report/group24_stats_report.pdf`).
  - Slides 9 and 10 provide dedicated blueprints for Task 4 Citation and Authorship networks.

### Phase 3: Interactive Dashboard
- [x] **Dashboard data builder (`src/dashboard/build_data.py`)** — Completed.
  - Compiled pre-aggregated metrics and 14,456 compact paper records into `dashboard/data/g24_data.js` (`window.G24_DATA`, 6.37 MB) enabling instant client-side filtering without CORS fetch barriers.
- [x] **Standalone HTML/CSS/JS interface (`dashboard/index.html`)** — Completed.
  - 100% offline-capable via `file://` double-click (Apache ECharts 5 and Tabulator vendored in `dashboard/vendor/`).
  - Supports all 11 required panels (9 live + 2 styled network placeholders with pre-populated graph statistics).
  - Multi-dimensional filtering by year, venue type, quartile, and disciplinary field with live KPI and chart synchronization.
- [x] **Automated consistency & integrity tests** — Completed.
  - `tests/test_data_integrity.py` and `tests/test_consistency.py` validated (10/10 tests passed in 0.47s).

- [x] **Dashboard UI Enhancements & Bugfixes (October 13, 2026)** — Completed.
  - Resolved KPI display issue: "Active Cadre Faculty" and "Median Corpus h-Index" now consistently display authoritative values from pre-aggregated bundles regardless of filter state.
  - Implemented ECharts horizontal bar visualization for "Department & Divisional Performance" panel in `dashboard/js/app.js` and `dashboard/index.html`.
  - Streamlined header: replaced circular outlined badges with stylized gradient "GROUP 24" typography.
  - Removed dashboard footer per user specification.
  - Generated comprehensive Data Collection Methodology & Audit Report in `docs/DATA_COLLECTION_REPORT.md`.
  - Added Decision D-10 to `docs/DECISIONS.md`.
- [x] **Browser Verification & Tabulator Lifecycle Fix (October 13, 2026)** — Completed.
  - Implemented automated end-to-end browser test suite (`scripts/test_browser.py` and `python3 run.py browser-test`) via Chrome DevTools Protocol (CDP) in headless Google Chrome.
  - Fixed Tabulator table row rendering: Tabulator's virtual DOM initialized with 0px height inside hidden tabs (`display: none`), which suppressed rendering when navigating to "Venues & Landmark Papers". Resolved by wiring `redraw(true)` on `facultyTable` and `topPapersTable` during tab switches, institute selector clicks, and window resize events.
  - Verified all 11 dashboard panels (9 live + 2 styled Task 4 placeholders), KPI cards, and filter controls (year range, venue type, quartile, field, reset).
  - Captured 12 high-resolution screenshots across all views and interaction states in `dashboard/screenshots/`.
  - Added `tests/test_dashboard_data.py` (no NaN/undefined anomalies, 10 random numbers verified between dashboard bundles and metrics CSVs). Total automated Pytest suite now at **14/14 passed** in 0.58s.
  - Validated offline `file://` execution: zero console errors, zero network requests, 100% self-contained.
  - Logged Decision D-11 in `docs/DECISIONS.md`.

- [x] **Remote Synchronization to GitHub (October 13, 2026)** — Completed.
  - Pushed entire `dpcn_a2` root directory as a direct child directory to `git@github.com:prathm01s/dpcn_almost_stable.git` (`main` branch) over SSH.
  - Configured git commit authorship with `prathm01s` and `prathmesh.sharma101@gmail.com`.
  - Preserved all existing content in the destination repository (`DPCN_Assignment_1.pdf`, `Survey_Results_UC.csv`, `project/`).
  - Retained full active local workspace integrity in `/home/prathm_s/Desktop/dpcn_a2`.

- [x] **Task 4: Interactive Network Visualisation & Analytics Integration (October 13, 2026)** — Completed.
  - Implemented graph analytics engine in `src/dashboard/build_data.py` leveraging NetworkX 3.6.1.
  - Ingested authoritative edge lists: `data/final/citation_network.csv` (27,816 edges, 11,008 nodes) and `data/final/authorship_network.csv` (65,059 edges, 7,864 nodes).
  - Computed full topological network statistics:
    - Directed Citation: PageRank centrality, in-degree citation frequencies, 3x3 cross-institute citation flow matrix (1,654 inter-lab citations), Top 10 landmark papers by PageRank, curated core subgraph (~173 nodes, 346 directed edges).
    - Undirected Authorship: Weighted degree centrality, Louvain community detection (130 communities), sampled betweenness centrality, 3x3 cross-institute co-authorship matrix (525 inter-lab pairs), Top 10 collaborative bridges, curated core subgraph (~150 nodes, 670 edges).
  - Upgraded dashboard (`dashboard/index.html`, `dashboard/js/app.js`, `dashboard/css/style.css`):
    - Converted placeholder tabs 5 and 6 into full interactive ECharts 5 canvases (`#chart-citation-network` and `#chart-authorship-network`).
    - Added interactive toolbars: institute filter dropdowns, dynamic in-degree/edge weight sliders, real-time node search, reset buttons.
    - Integrated network KPI strips, deep-dive tables (Top 10 PageRank landmarks, Top 10 collaborative bridges), and 3x3 cross-institute flow/collaboration matrices.
  - Updated automated test suite (`tests/test_dashboard_data.py` and `scripts/test_browser.py`):
    - 15/15 unit & integration tests passing in 0.64s.
    - Automated CDP headless Chrome tests pass with 0 console errors on both HTTP and offline `file://` protocol.
  - Updated `final_submission/dashboard.zip`, `final_submission/CHECKSUMS.sha256`, and logged Decision D-12 in `docs/DECISIONS.md`.

---

## 4. Current Execution Step & Summary
- **Current Status**: **All Tasks (Task 1: Data Collection, Task 2: Statistics Report, Task 3: Interactive Dashboard, and Task 4: Network Analytics & Visualization) 100% Completed, Verified in Live Headless Browser, and Fully Packaged.**
- **Verification Summary**:
  1. Primary dataset `data/final/group24_data.csv` satisfies all schema, domain, and consistency rules with zero fabricated data.
  2. All three network edge lists (`citation_network.csv`, `authorship_network.csv`, `indian_connections.csv`) exported, validated, and tested.
  3. Statistics presentation report strictly meets the $\le 10$ slides constraint in PPTX and PDF formats.
  4. Interactive dashboard runs seamlessly offline by opening `dashboard/index.html` via double-click, with all 11 panels (including live interactive Directed Citation and Co-Authorship networks), synchronized KPI cards, Tabulator tables, and department explorer charts functioning cleanly.
  5. Live browser verification suite confirms 0 console errors on both HTTP (`http://127.0.0.1:8080/dashboard/index.html`) and local `file://` protocol.
  6. Task 4 interactive network graphs render in <300ms with physics simulation, pan/zoom, node drag, and rich tooltips.
  7. Exhaustive documentation provided in `docs/DATA_COLLECTION_REPORT.md`, `docs/QA_REPORT.md`, `docs/DECISIONS.md`, `docs/DATA_DICTIONARY.md`, and `docs/LIMITATIONS.md`.
  8. Synchronized with GitHub repository `prathm01s/dpcn_almost_stable` on `main` branch.
<!-- GOAL_COMPLETE -->

