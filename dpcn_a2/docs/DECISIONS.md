# DECISIONS.md — Group 24 Architectural and Methodological Decisions

All architectural, methodological, and data harmonization decisions made during the project are documented here with dates and rationales.

---

### D-01 (2026-10-13): Definition of "Faculty" vs "Affiliated Authors"
- **Decision**: Faculty is strictly defined as scientific cadre staff from official institute rosters (Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist, Director, Distinguished/Emeritus Scientists). Technical/administrative staff, students (PhD, JRF, SRF), project assistants, and visiting researchers are categorized as `affiliated_author`.
- **Rationale**: The assignment mandates faculty-level metrics (h-index distribution, top faculty performance table). Students and temporary staff have high turnover and would distort institutional faculty-level distributions. Affiliated authors are still retained as rows in `group24_data.csv` to ensure complete paper coverage.

### D-02 (2026-10-13): Definition and Scope of `coauthor_institutes`
- **Decision**: In `group24_data.csv`, `coauthor_institutes` contains a semicolon-separated, alphabetically sorted list of canonical names of Indian institutions for all co-authors, excluding the row's own institution. All-country/international affiliations are preserved in `group24_data_extended.csv`.
- **Rationale**: The specification states `coauthor_institutes` is explicitly for Indian connections ("Semicolon-separated list of co-author institutions (for Indian connections)"). Keeping only Indian institutions in the primary column directly satisfies the Indian network mapping requirement while avoiding cluttered strings.

### D-03 (2026-10-13): Journal Quartile Source and Policy
- **Decision**: SCImago Journal Rank (SJR) best quartile for the paper's publication year is used. For 2026 publications (as SJR updates in June of the following year), the latest available SJR year (2025) is used and flagged. Matching priority is normalized ISSN (without hyphens) first, and clean exact title matching as fallback. CORE conference rankings (A*, A, B, C) are applied to conference proceedings.
- **Rationale**: SJR is open access and Scopus-derived, whereas JCR is paywalled. Best quartile across subject areas represents standard bibliometric practice.

### D-04 (2026-10-13): Inclusion and Typing of Work Types
- **Decision**: The primary dataset retains peer-reviewed scholarly outputs: journal articles, reviews, letters, and conference proceedings. Paratext, editorials, errata, preprints, books, datasets, and dissertations are excluded from `group24_data.csv` and logged in `data/interim/excluded_works.csv`.
- **Rationale**: Consistent with research mapping guidelines across academic clusters to ensure comparable citation and output statistics.

### D-05 (2026-10-13): Handling of 2026 Publications
- **Decision**: 2026 publications (up to collection date October 2026) are included but flagged as `is_partial_year = true`. In all charts, tables, and reports, 2026 is explicitly denoted as "2026 (partial)". It is excluded from CAGR trends (2016–2025 CAGR is reported).
- **Rationale**: Prevents misinterpreting mid-year collection volume as an apparent decline in research productivity.

### D-06 (2026-10-13): Caching and OpenAlex Budget Management
- **Decision**: Every HTTP GET request is cached to disk using the SHA-256 hash of the URL with API keys and authentication tokens stripped. Paging strictly uses OpenAlex cursor tokens. Slices are split by institution and publication year. Field selection (`select=`) is enforced.
- **Rationale**: Ensures the pipeline is idempotent, resumable across runs without burning budget, and respects rate limits.

### D-07 (2026-10-13): Interactive Dashboard Offline Architecture
- **Decision**: The interactive dashboard is built as a static site that can run locally via `file://` by directly double-clicking `dashboard/index.html`. Pre-aggregated and compact paper data is emitted into JavaScript files (`window.G24_DATA = {...}`) rather than `.json` fetch calls, with all third-party libraries (Apache ECharts 5, Tabulator) vendored locally.
- **Rationale**: Modern web browsers block `fetch()` on `file://` protocol due to CORS security policies. Embedding data in script tags ensures zero runtime failures in class presentations or offline evaluations.

### D-08 (2026-10-13): Statistics Presentation Report Hard Constraint (<= 10 Slides)
- **Decision**: The report presentation (`stats/report/group24_stats_report.pptx` and `.pdf`) is strictly budgeted to exactly 10 slides. Slides 1–8 cover executive summary, publication trends, journal quartiles, citation dynamics, faculty excellence, research domains, top venues/landmarks, and departmental performance. Slides 9–10 are reserved for Task 4 Citation and Authorship Network architecture blueprints.
- **Rationale**: The assignment guidelines stipulate a strict maximum length of $\le 10$ slides or $\le 5$ pages. Exceeding this limit incurs penalties.

### D-09 (2026-10-13): Preservation of Task 4 Graph Assets During Phase 1
- **Decision**: While full network topological calculations (Louvain community detection, PageRank) are deferred to Task 4, all raw citation edges (`citation_edges_raw.parquet`, 27,816 edges), canonical Indian institution mapping (`indian_inst_registry.csv`, 910 institutions), and co-authorship relationships were fully resolved and persisted during Phase 1.
- **Rationale**: Guarantees that when Task 4 is executed, zero additional OpenAlex API calls or budget will be required, and network graphs can be derived instantaneously from disk.

### D-10 (2026-10-13): Dashboard UI Refinements & Department Explorer Visualization
- **Decision**: 
  1. Fixed the KPI summary strip so that "Active Cadre Faculty" and "Median Corpus h-Index" are always sourced from pre-aggregated institutional bundles and never fall back to "-" during client-side filtering.
  2. Implemented an interactive ECharts horizontal bar visualization for "Department & Divisional Performance" driven by `stats/tables/department_performance.csv`, displaying publication volume, citation counts, Q1 share, active faculty, and top research field on hover.
  3. Replaced top-right pill badges with a single stylized gradient "GROUP 24" typography element and removed the redundant dashboard footer for a cleaner, modern interface.
- **Rationale**: Direct user request; ensures critical institutional faculty benchmarks remain visible regardless of filter state and provides immediate insight into division-level strengths across CSIR-NCL, CSIR-IICT, and CSIR-CECRI.

### D-11 (2026-10-13): Tabulator Table Lifecycle Synchronization & Automated Browser CDP Test Suite
- **Decision**: 
  1. Updated `dashboard/js/app.js` to explicitly invoke `redraw(true)` on `facultyTable` and `topPapersTable` whenever tabs switch, institute selections change, or the window resizes.
  2. Implemented an automated end-to-end browser testing suite (`scripts/test_browser.py`, `python3 run.py browser-test`, and `tests/test_dashboard_data.py`) leveraging the Chrome DevTools Protocol (CDP) in headless Google Chrome.
- **Rationale**: Tabulator's virtual DOM renderer initializes with a calculated viewport height of 0px when constructed inside a hidden container (`display: none`), which previously prevented row rendering when switching to the "Venues & Landmark Papers" tab. Explicitly triggering `redraw(true)` on tab activation ensures all rows and columns render immediately with zero visual clipping. The automated CDP test suite verifies all 11 panels, filters, and offline `file://` execution with zero console errors.
