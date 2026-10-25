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

### D-12 (2026-10-13): Task 4 Full Interactive Network Analytics & Visualization Implementation
- **Decision**: 
  1. Built full graph analytics using NetworkX directly on `data/final/citation_network.csv` (27,816 edges, 11,008 nodes) and `data/final/authorship_network.csv` (65,059 edges, 7,864 nodes).
  2. For the Directed Citation Network, computed exact PageRank centrality, in-degree citation frequencies, a 3x3 cross-institute citation flow matrix (1,654 inter-lab citations), top 10 landmark publications by PageRank, and a curated high-impact core subgraph (~173 nodes, 346 directed edges) with directional arrows.
  3. For the Co-Authorship Network, computed weighted degree centrality, Louvain community detection (130 communities), sampled betweenness centrality, a 3x3 cross-institute co-authorship matrix (525 inter-lab pairs), top 10 collaborative bridges, and a curated collaborative core subgraph (~150 nodes, 670 edges) with weighted link widths.
  4. Embedded computed analytics into `dashboard/data/g24_data.js` via `src/dashboard/build_data.py`. Replaced placeholder tabs 5 and 6 in `dashboard/index.html` with interactive ECharts 5 force-directed graph canvases (`#chart-citation-network` and `#chart-authorship-network`), complete with interactive toolbars (institute filters, dynamic degree/weight sliders, real-time node search), KPI summary strips, and deep-dive tables.
- **Rationale**: Direct user request; brings Task 4 network analysis and visualization into the live dashboard ahead of schedule. Curating core subgraphs (~150–175 nodes) ensures high-speed client-side rendering (<300ms) with zero canvas lag while preserving full statistical precision across all 27k+ citation edges and 65k+ authorship edges in the metric cards, ranking tables, and 3x3 flow matrices.


### D-13 (2026-10-20): Indian Citation Flags Measured Only, Heuristics Removed
- **Decision**: `cites_indian_inst` and `cited_by_indian_inst` are now set only from observed in-corpus citation links (`citation_network.csv`): a row for institute X is `TRUE` when the citing/cited corpus paper involves an Indian institution other than X (another assigned lab or an Indian co-author institute). The heuristic completion in Step 11 (any Indian co-author ⇒ cites = TRUE; ≥10 citations ⇒ cited_by = TRUE) was removed, and `src/collect/15_refresh_indian_flags.py` re-applied the rule to `data/final/` because the interim parquet caches are not in this checkout. Only the two flag columns changed (verified byte-identical otherwise); manifest SHA256s were refreshed.
- **Effect**: `cites_indian_inst` 55.7% → 37.4% TRUE (rows), `cited_by_indian_inst` 61.2% → 35.9%. 7,771 and 10,710 rows respectively had been TRUE only through the heuristics. No row became TRUE that was FALSE before.
- **Rationale**: AGENTS.md rule 1 (no fabricated data). The heuristics were assumptions, not observations. Resolving out-of-corpus references and citing works from OpenAlex would raise the flags but was not done (group decision: fix within existing data); the flags are documented as lower bounds in LIMITATIONS.md.

### D-14 (2026-10-20): Sector Classification Fix for the Indian Institution Registry
- **Decision**: Moved `assign_sector_cluster` to `src/common/sectors.py`, matched abbreviations as whole words, and added CSIR/DAE lab-name lists, IISc, central-university names, and `Industry`/`Healthcare`/`Government` from the OpenAlex institution type. Re-labelled `config/indian_inst_registry.csv` (only `sector_cluster` changed).
- **Rationale**: Substring matching made `"NIV"` match inside "UNIVERSITY", so 305 universities (e.g. Savitribai Phule Pune University, Jadavpur University) were labelled `ICMR`; AcSIR, IISc and CSIR labs such as CCMB were `Other`. Correct sectors are needed for the cross-cluster flags.

### D-15 (2026-10-20): Indian Connectivity Analyses (Sections 7a/7b) and Dashboard Tab
- **Decision**:
  1. Fixed `src/stats/metrics.py`: pandas parses `TRUE`/`FALSE` as booleans, so the string comparison counted 0 flagged papers in `indian_connections_summary.csv` (and the dashboard).
  2. Added `src/stats/connectivity.py` (run by `make stats`): citation in/out-flow per institute and per year, impact ratio (in/out), top 10 citing Indian institutes, top 10 most-cited corpus papers citing each institute, cross-cluster links by partner sector (CSIR ↔ IIT, CSIR ↔ DAE, …), Jaccard topic similarity between the three labs and with top partners, and hub authors bridging institutions.
  3. Added an "Indian Connectivity" dashboard tab with these results, and connectivity checks in `scripts/test_browser.py` and `tests/test_connectivity.py`.
  4. Made the dashboard network subgraphs deterministic (`ordered_subgraph`, name tie-breaks); networkx subgraph views iterate in set order, so `g24_data.js` previously changed with `PYTHONHASHSEED`.
- **Scope**: Flows count in-corpus citations only, so they are lower bounds; "All Three" sums per-lab flows.

### D-16 (2026-10-20): Week 1–2 Pre-Submission Cleanup (Duplicates, Invalid Edges, Line Endings)
- **Decision**:
  1. Added `src/collect/16_clean_final.py` (runs after Step 14, before Step 15). It removes 13 rows of `group24_data.csv`/`_extended.csv` that repeated the same (institution, work, author) — OpenAlex listed one person twice on a paper (the row with an `author_openalex_id` is kept); 55 self-loop edges (`source_doi == target_doi`, OpenAlex reference errors) and 7 blank-DOI edges from `citation_network.csv`; 1 exact duplicate row from `authorship_network.csv`.
  2. Re-ran Step 15, so the Indian flags no longer count a paper "citing itself": 35 rows changed, all TRUE → FALSE (21 for `cites_indian_inst`, 35 for `cited_by_indian_inst`) (`cites` 37.4% → 37.3%, `cited_by` 35.9% → 35.8% of rows). Rebuilt `stats/tables/` (metrics + connectivity) and `dashboard/data/g24_data.js`; inter-lab citations 1,654 → 1,653.
  3. Added `.gitattributes` forcing LF for `*.csv/*.json/*.md/*.js/*.yaml/*.sha256`: on Windows checkouts with `core.autocrlf=true`, git had rewritten every CSV with CRLF, so `CHECKSUMS.sha256` and MANIFEST hashes failed. Step 15 now writes LF explicitly.
  4. Added the missing `networkx`, `pyreadr`, `websocket-client` to `requirements.txt`.
- **Effect**: 42,406 → 42,393 rows; citation edges 27,816 → 27,754; authorship edges 65,059 → 65,058. Distinct papers (14,352), `indian_connections.csv`, and paper-level metrics are unchanged. A control run of Step 15 on the uncleaned data reproduced the committed files byte-for-byte before the cleanup was applied.
- **Not changed**: `citation_network.csv` still holds in-corpus edges only (both papers in the NCL/IICT/CECRI corpus); edges to papers of other Indian institutions need out-of-corpus OpenAlex lookups (see D-13, LIMITATIONS.md). The stats report text (`src/stats/make_report.py`) contains hardcoded figures that disagree with `stats/tables/` and must be rewritten from the tables before the Week 3 submission.

### D-17 (2026-10-20): Links With Other Indian Institutions From OpenAlex; Data-Driven Report; Shared Network Module
- **Decision**:
  1. Added `src/collect/17_indian_links_api.py` (runs after Step 16, before Step 15). For each batch of 100 corpus works it queries OpenAlex `openalex_id:` (references, authorships), `cited_by:<ids>,authorships.countries:IN` (Indian papers we cite) and `cites:<ids>,authorships.countries:IN` (Indian papers citing us). 2,395 list calls, est. $0.24, cached in `data/cache/`. Appended 165,240 citation edges between corpus papers and DOI-bearing Indian-affiliated papers outside the corpus (the outside side's inst = its Indian institutions, `;`-joined), and 43,789 co-authorship edges between our authors and co-authors at other Indian institutions. Outside-paper metadata in `data/final/indian_linked_works.csv` (103,673 works).
  2. Step 15 now reads the outside paper's institutions from the edge, so `cites_indian_inst` = 88.9% and `cited_by_indian_inst` = 72.3% of rows (were 37.3% / 35.8% lower bounds). This supersedes the scope note in D-13/D-16.
  3. `src/stats/connectivity.py` flows (Section 7a) include the outside links; the top citing papers now include outside papers.
  4. New `src/stats/networks.py` (Section 6) computes PageRank, in-degree distribution, lab flow matrix, degree / betweenness centrality and Louvain communities on the within-cluster edges only, and writes `stats/tables/network_*.csv`. The dashboard builds its graphs with the same functions. Fixed: dashboard "Collaborators (Degree)" showed weighted degree (joint-paper count) — now distinct co-authors; betweenness previously treated collaboration weight as distance and sampled 100 nodes — now unweighted with 1,000 sampled sources.
  5. Rewrote `src/stats/make_report.py`: every number comes from `stats/tables/` (the old deck had hand-typed figures, e.g. invented "landmark papers", 380,000 citations, Chemistry 68.2%, and stale flag shares). Slides 9–10 now hold the citation and authorship network summaries. PDF is exported with LibreOffice or, on Windows, PowerPoint. `tests/test_networks.py` checks report ↔ tables ↔ dashboard agreement.
- **Effect**: `citation_network.csv` 27,754 → 192,994 rows; `authorship_network.csv` 65,058 → 108,847 rows; in-corpus network figures unchanged.

### D-18 (2026-10-20): Citation Impact Ratio and Impact-Based "Q1" (Instructor Request)
- **Request**: classify papers as Q1 by an impact ratio = citations received ÷ citations made, with a threshold chosen by the group (instructor's examples: 5 or 10).
- **Update (same day)**: the fixed thresholds 5 and 10 were dropped (they select 0.53% and 0.13% of papers — too strict to be a "Q1"); only the 75th-percentile threshold (IR > 0.59, top 25%) is used in the report and dashboard. `impact_ratio.thresholds` in `config/settings.yaml` is now empty and can re-add fixed thresholds if needed.
- **Decision**:
  1. Paper IR = OpenAlex `cited_by_count` (13 Oct) ÷ number of `referenced_works`; institute IR = Σ citations received ÷ Σ references made over the institute's distinct papers. Papers with 0 references in OpenAlex (513) have no IR and are excluded from IR shares (reported).
  2. A paper is "IR-Q1" when IR > T. Thresholds live in `config/settings.yaml` (`impact_ratio.thresholds: [5, 10]`, the instructor's examples) plus `quartile_percentile: 75`, a data-driven threshold (IR > 0.59) that selects the top 25% of papers — the same share a quartile covers — so IR-Q1 can be compared like-for-like with SJR Q1.
  3. Reference counts come from Step 17's cached OpenAlex responses (`src/collect/18_reference_counts.py` → `data/final/work_reference_counts.csv`; 0 API calls). Analysis in `src/stats/impact_ratio.py` → `stats/tables/impact_ratio_*.csv`; report slide 4; dashboard Overview panel "Q1 by Citation Impact Ratio vs Journal Quartile" (threshold selector, follows filters).
- **Result**: institute IR — IICT 0.41, NCL 0.47, CECRI 0.59, all three 0.47. IR > 5: 0.53% of papers; IR > 10: 0.13%; IR > 0.59 (P75): 25.2%. Only 32.9% of papers in SJR-Q1 journals are top-25% by IR, so journal-based and paper-based Q1 differ substantially.
- **How it differs from SJR Q1**: SJR Q1 ranks the journal (venue prestige across all its papers); IR ranks each paper by its own citations relative to how many works it cites. IR favours older papers (more time to be cited) and reviews with many citations.
- Also added the dashboard URL (https://prathm01s.github.io/dpcn_almost_stable/) to report slides 1 and 10.

---

### D-19 (2026-10-25): Hyper-Authored Paper Filtering for Co-authorship Topology
- **Decision**: In `src/stats/insights/common.py`, papers with $> 30$ authors are excluded when constructing the co-authorship graph (dropping 5 hyper-authored consortia papers out of 14,352).
- **Rationale**: Megapapers (e.g., massive international consortia or clinical genome screens with 50+ authors) create artificial cliques of hundreds or thousands of edges. These distort degree distributions, artificially inflate local clustering, and skew rich-club and network fragility evaluations. Dropping papers $>30$ authors preserves 7,508 nodes and 34,693 edges in the Giant Component (95.8% of nodes).

### D-20 (2026-10-25): Citation Maturation Window for Quartile vs Impact (2016–2023)
- **Decision**: In Insight 5 ("Do Q1 papers actually draw more citations?"), analysis is restricted to papers published between 2016 and 2023 (10,212 papers), excluding 2024–2026.
- **Rationale**: Papers published in 2024–2026 have had $\le 2$ years to accrue citations. Evaluating citation percentiles, uncited rates, and high-impact anomalies on immature citation cohorts would confound publication recency with lack of impact.

### D-21 (2026-10-25): Career Abroad Spell Classification Rules for Brain Circulation
- **Decision**: In Insight 9 ("Does international mobility boost impact?"), an author is classified as a "Returnee" if their pre-CSIR career publication record (derived from OpenAlex `/authors` careers) contains $\ge 2$ consecutive years with exclusively or predominantly foreign institutional affiliations. Scientists with exclusively Indian affiliations are "Home-grown". Scientists with ambiguous or missing pre-tenure histories are "Unclassifiable".
- **Rationale**: Distinguishes substantive foreign research training (e.g., overseas PhD or multi-year postdoc) from brief visits, short collaborations, or co-authored papers written while remaining in India. A 30-scientist validation sample is exported to `stats/tables/insights/09_validation_sample.csv`.

### D-22 (2026-10-25): Academic Age $\ge 30$ as a Proxy for Senior Faculty Retirement Exposure
- **Decision**: In Insight 10 ("Succession Risk"), academic career age is measured as $\text{Collection Year (2026)} - \text{Year of First Recorded Publication}$. Faculty with academic age $\ge 30$ years are treated as nearing retirement (within ~5 years). Robustness checks evaluate sensitivity at thresholds 28 and 32.
- **Rationale**: CSIR institute faculty directory pages do not publicly disclose birthdates or exact retirement years. Academic age (time elapsed since first scholarly publication) is the standard bibliometric proxy for chronological age and senior career stage.

### D-23 (2026-10-25): Sampled Betweenness Centrality for Targeted Network Attack Simulation
- **Decision**: In Insight 3 ("Fragility"), betweenness centrality for node removal ranking is computed on the co-authorship LCC using a randomized pivot sampling ($k=1,000$ sources) with fixed seed `SEED=24`.
- **Rationale**: Exact betweenness centrality on a graph of 7,500 nodes and 35,000 edges has $O(V \cdot E)$ complexity (~260 million operations per step). Computing exact betweenness dynamically across hundreds of iterative removal rounds is computationally intractable. A 1,000-source pivot approximation provides $>0.99$ rank correlation while completing in seconds.

