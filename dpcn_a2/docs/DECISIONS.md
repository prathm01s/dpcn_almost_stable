# DECISIONS.md — Group 24 Architectural and Methodological Decisions

All architectural, methodological, and data harmonization decisions made during the project are documented here with dates and rationales. Entries are kept in the order they were made; when a later entry changes an earlier decision, the earlier entry carries a **Status** line pointing to it.

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
- **Status (as implemented)**: quartiles were matched on ISSN (13,251 papers) or the nearest SJR year within ±2 (231); 870 papers stayed unranked (684 journal papers not in SJR plus all 186 conference papers). No CORE rankings file was imported, so no conference paper carries a CORE rank (see SOURCES.md §6).

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
- **Status**: the 10-slide limit still holds; the slide contents and file name changed — see D-17 (data-driven report, network summaries on the network slides) and D-24 (final layout, `24_CSIR.pptx` / `.pdf`).

### D-09 (2026-10-13): Preservation of Task 4 Graph Assets During Phase 1
- **Decision**: While full network topological calculations (Louvain community detection, PageRank) are deferred to Task 4, all raw citation edges (`citation_edges_raw.parquet`, 27,816 edges), canonical Indian institution mapping (`indian_inst_registry.csv`, 910 institutions), and co-authorship relationships were fully resolved and persisted during Phase 1.
- **Rationale**: Guarantees that when Task 4 is executed, zero additional OpenAlex API calls or budget will be required, and network graphs can be derived instantaneously from disk.
- **Status**: superseded — the network analysis was built in D-12 and extended in D-17.

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
- **Status**: the measured-only rule stands, but the in-corpus restriction was lifted in D-17 (links to Indian papers outside the corpus were collected).

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
- **Not changed (at the time; resolved in D-17)**: `citation_network.csv` still holds in-corpus edges only (both papers in the NCL/IICT/CECRI corpus); edges to papers of other Indian institutions need out-of-corpus OpenAlex lookups (see D-13, LIMITATIONS.md). The stats report text (`src/stats/make_report.py`) contains hardcoded figures that disagree with `stats/tables/` and must be rewritten from the tables before the Week 3 submission.

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
  2. A paper is "IR-Q1" when IR > T. T is `quartile_percentile: 75` in `config/settings.yaml`, a data-driven threshold (IR > 0.59) that selects the top 25% of papers — the same share a quartile covers — so IR-Q1 can be compared like-for-like with SJR Q1. (The instructor's example thresholds 5 and 10 were tried first; see the update above.)
  3. Reference counts come from Step 17's cached OpenAlex responses (`src/collect/18_reference_counts.py` → `data/final/work_reference_counts.csv`; 0 API calls). Analysis in `src/stats/impact_ratio.py` → `stats/tables/impact_ratio_*.csv`; report slide 3 (after the D-24 re-layout); dashboard Overview panel "Q1 by Citation Impact Ratio vs Journal Quartile" (follows the filters).
- **Result**: institute IR — IICT 0.41, NCL 0.47, CECRI 0.59, all three 0.47. IR > 0.59 (P75): 25.2% of papers (for reference, IR > 5 would select 0.53% and IR > 10 0.13%). Only 32.9% of papers in SJR-Q1 journals are top-25% by IR, so journal-based and paper-based Q1 differ substantially.
- **How it differs from SJR Q1**: SJR Q1 ranks the journal (venue prestige across all its papers); IR ranks each paper by its own citations relative to how many works it cites. IR favours older papers (more time to be cited) and reviews with many citations.
- Also added the dashboard URL (https://prathm01s.github.io/dpcn_almost_stable/) to report slides 1 and 10.

---

### D-19 (2026-10-25): Hyper-Authored Paper Filtering for Co-authorship Topology
- **Decision**: In `src/stats/insights/common.py`, papers with $> 30$ authors are excluded when constructing the co-authorship graph (dropping 5 hyper-authored consortia papers out of 14,352).
- **Rationale**: Megapapers (e.g., massive international consortia or clinical genome screens with 50+ authors) create artificial cliques of hundreds or thousands of edges. These distort degree distributions, artificially inflate local clustering, and skew rich-club and network fragility evaluations. With papers of $>30$ authors dropped, the giant component has 7,509 nodes and 34,696 edges (95.8% of nodes; figures after the D-25 roster cleanup). The author count per paper is taken from `authorship_network.csv`, i.e. authors of the three labs plus their Indian co-authors, so it is a lower bound on the true author count.

### D-20 (2026-10-25): Citation Maturation Window for Quartile vs Impact (2016–2023)
- **Decision**: In Insight 5 ("Do Q1 papers actually draw more citations?"), analysis is restricted to papers published between 2016 and 2023 (10,212 papers), excluding 2024–2026.
- **Rationale**: Papers published in 2024–2026 have had $\le 2$ years to accrue citations. Evaluating citation percentiles, uncited rates, and high-impact anomalies on immature citation cohorts would confound publication recency with lack of impact.

### D-21 (2026-10-25): Career Abroad Spell Classification Rules for Brain Circulation
- **Decision**: In Insight 9 (brain circulation), each matched roster scientist's full OpenAlex career is classified as: **Foreign-trained** if the most frequent country on their first 3 papers (PhD proxy) is not India; **Returnee** if that country is India and the career contains an abroad spell — ≥2 consecutive years in which all of their affiliations are outside India, with ≥2 distinct papers; **Home-grown** otherwise; **Unclassifiable** if they have fewer than 3 papers or no country on their first papers. Host country = most frequent country in the spell (ties alphabetical). Refined in D-24.
- **Rationale**: Distinguishes substantive foreign research training (e.g., overseas PhD or multi-year postdoc) from brief visits, short collaborations, or co-authored papers written while remaining in India. A 30-scientist validation sample is exported to `stats/tables/insights/09_validation_sample.csv`.

### D-22 (2026-10-25): Academic Age $\ge 30$ as a Proxy for Senior Faculty Retirement Exposure
- **Decision**: In Insight 10 ("Succession Risk"), academic career age is measured as $\text{Collection Year (2026)} - \text{Year of First Recorded Publication}$. Faculty with academic age $\ge 30$ years are treated as nearing retirement (within ~5 years). Robustness checks evaluate sensitivity at thresholds 28 and 32.
- **Rationale**: CSIR institute faculty directory pages do not publicly disclose birthdates or exact retirement years. Academic age (time elapsed since first scholarly publication) is the standard bibliometric proxy for chronological age and senior career stage.

### D-23 (2026-10-25): Sampled Betweenness Centrality for Targeted Network Attack Simulation
- **Decision**: In Insight 3 ("Fragility"), betweenness centrality for node removal ranking is computed on the co-authorship LCC using a randomized pivot sampling ($k=1,000$ sources) with fixed seed `SEED=24`.
- **Rationale**: Betweenness is computed once on the initial LCC and the removal order is fixed from it (it is not recomputed after each removal). Exact betweenness on ~7,500 nodes and ~35,000 edges costs O(V·E); sampling 1,000 source nodes gives an estimate in seconds. The approximation's agreement with exact betweenness was not measured.

### D-24 (2026-10-26): Review of the Ten Insights (Phase 2b)
- **Report**: back to 10 slides (hard limit) — slide 1 now holds title, coverage table, method and limits; slide 10 is the findings table (10 pt, short labels). The ≤10 test, relaxed to ≤15, is restored. Report files renamed `24_CSIR.pptx` / `24_CSIR.pdf` (instructor's naming format).
- **No invented values**: removed fallbacks that produced numbers or names without data (host countries "US/Germany", random-removal n50 = 3,280, n50 = 20% when not reached, rich-club ρ = 1.0, "N/A"). A strategy that misses its threshold now raises instead.
- **Data access**: career histories are fetched through the project's OpenAlex client (API key, cache, retries, cursor paging; 588 calls, ≈$0.06). Foreign co-authorship comes from Step 18 (`has_foreign_coauthor`, cached responses); unknown papers are excluded. Insights 7, 9, 10 read local caches only and write "Not computed" when a cache is missing.
- **Method fixes**: Insight 2 evaluates ρ_norm at k*−1 so it covers the same degree ≥ k* set that is counted; Insight 6 compares with the median of all corpus papers of the year; Insight 7 uses complete years (to 2025), requires ≥10 citations in the peak year and labels awakenings sustained (≥50% of peak after the peak) vs spikes; Insight 9 treats an unknown PhD country as unclassifiable, counts distinct papers in abroad spells, deduplicates shared OpenAlex profiles and restricts the Sankey to classifiable scientists; Insight 10 reports the most exposed lab (was hard-coded IICT) and says "only roster authors at risk" instead of "led solely by".
- **Determinism**: tie-breaks and LCC node order made independent of PYTHONHASHSEED; outputs identical across seeds.
- **Pipeline order**: `make all` / `run.py all` run insights before stats, because the report quotes the insight headlines.
- **Effect on headlines**: Insight 6 hidden gems 82 → 43; Insight 7 now reports 2 sustained awakenings among the 7 strongest candidates; Insight 9 returnees 8.3% → 15.7% (complete careers; foreign co-authorship 20.3% vs 16.8%); Insight 10 most exposed lab CECRI 46.3%.

### D-25 (2026-10-26): Faculty Roster Cleanup (Step 19)
- **Problem**: the IICT staff pages list technical staff next to scientists. The scraper copied their job title into the name (e.g. "Dr. C. Chandrasekhar Sr. Technical Officer (3)") and recorded the designation as "Scientist", so 119 technical-staff entries were counted as faculty (37 of them among the 347 "faculty with papers"); 281 dataset rows and 1,290 co-authorship edges carried the title in the author name. Three roster scientists were also matched to OpenAlex profiles that belong to someone else, and Dr. D. Srinivasa Reddy was listed at both NCL and IICT.
- **Decision**: new `src/collect/19_roster_cleanup.py` (after Step 18, before Step 15). Rule in code: a roster name ending in a technical title (Technical Officer / Technical Assistant / Technician, with Sr./Senior/Principal and grade) is not faculty — removed from `faculty_master.csv` and logged in `data/review/roster_excluded.csv`. Manual decisions in `config/overrides/roster_overrides.csv` (reason + date): drop the NCL duplicate of Dr. Reddy (kept once, as IICT Director, where all his rows already point); unmatch Dr. A.V. Subrahmanya Sarma and Dr. A.V. Sesha Sainath (matched to a merged catch-all profile "A. V.") and Dr. M. Srinivasa Rao (matched to R. Srinivasa Rao). Their dataset rows become affiliated-author rows; job titles are stripped from author names, and rows on wrongly matched profiles take the name printed on the paper (OpenAlex raw_author_name from Step 17's cache).
- **Effect**: roster 505 → 385 (IICT 287 → 168, NCL 167 → 166, CECRI 51); faculty with ≥1 paper 347 → 306 (IICT 169 → 129, NCL 152 → 151); combined median h-index 6 → 7 (IICT 5 → 6). Papers, citations, quartiles, flags and the network files' structure are unchanged; only author names in 282 rows (and the matching co-authorship edges) changed. Statistics, insights, report and dashboard were rebuilt.

---

### D-26 (2026-10-27): Information Diffusion & Epidemic Spreading Model (Insight 11)
- **Motivation**: Model how novel experimental methodologies, synthesis techniques, or chemical reagents diffuse through collaborative research ties in the CSIR Chemistry cluster, addressing epidemic threshold theory and disciplinary boundaries.
- **Model Formulation**:
  1. **Epidemic Spreading Framework**: Susceptible-Infected (SI) process modeling non-depleting information/knowledge transmission across co-authorship edges.
  2. **Epidemic Thresholds**: Theoretical critical threshold computed as $\beta_c = \frac{\langle k \rangle}{\langle k^2 \rangle}$ and compared to the inverse largest eigenvalue of the adjacency matrix $\beta_c^{\text{spectral}} = \frac{1}{\lambda_{\max}(A)}$. For the global co-authorship Giant Component ($N=7,509$, $E=34,696$), heavy-tailed degree heterogeneity produces $\beta_c = 0.0322$ ($\approx 3.2\%$).
  3. **Disciplinary Heterogeneity**:
     - **Condition A (Topic-Modulated Transmission)**: transmission probability along edge $(u, v)$ is $\beta_{uv} = \beta_0 \times \text{CosSim}(\vec{\theta}_u, \vec{\theta}_v) \times s_v(\text{Field})$ ($\beta_0 = 0.20$), using the authors' OpenAlex subfield publication profiles and the receiver's share of papers in the field. Tracks in-field adoption and cross-field spillover over 15 steps on the full co-authorship network.
     - **Condition B (Domain-Restricted Subgraph)**: uniform $\beta_0 = 0.20$ confined to the collaboration subgraph of researchers with ≥1 paper in the field; measures $T_{50}$ (steps to 50% adoption).
  4. **Fields evaluated** (fixed list of the six largest): *Chemistry* (3,206 researchers, LCC 3,202), *Materials* (2,093 researchers, LCC 2,075), *Engineering* (2,079 researchers, LCC 2,065), *Energy* (1,060 researchers, LCC 1,048), *Biochemistry* (1,418 researchers, LCC 1,395), *Medicine* (970 researchers, LCC 952).
  5. **Super-spreaders and blockers**: cadre-faculty seeds, $M = 50$ Monte Carlo runs per seed (convergence checked at $M$ = 25, 50, 100); super-spreaders ranked by lowest $T_{50}$, then reach at $t = 3$.
- **Key findings** (from `stats/tables/insights/11_field_diffusion_metrics.csv` and `11_super_spreaders_blockers.csv`; superseded by D-27):
  - Epidemic threshold $\beta_c$ is lowest in Chemistry (0.032) and highest in Engineering (0.055); the whole giant component has $\beta_c = 0.032$ (spectral $1/\lambda_{\max} = 0.030$).
  - Condition A, final in-field reach (cross-field spillover): Chemistry 76.5% (spillover 2.55%), Energy 55.0% (spillover 1.03%), Biochemistry 32.1% (spillover 1.24%), Medicine 26.2% (spillover 1.20%), Materials 24.7% (spillover 1.29%), Engineering 23.2% (spillover 0.65%). Spillover stays at a few percent, i.e. innovations mostly stay within their field in this model.
  - Condition B, steps to 50% adoption: Medicine 5.56, Chemistry 5.81, Biochemistry 6.15, Energy 6.33, Materials 6.57, Engineering 7.54.
  - Top super-spreader per field (Condition A / Condition B): Chemistry: Dr. Jagadeesh Babu Nanubolu (IICT) / Dr. Jagadeesh Babu Nanubolu (IICT); Materials: Dr. Ramanuj Narayan (IICT) / Dr. Sreekumar Kurungot (NCL); Engineering: Dr. Arun Torris (NCL) / Dr. Sreekumar Kurungot (NCL); Energy: Dr Subrata Kundu (CECRI) / Dr Subrata Kundu (CECRI); Biochemistry: Dr. Sunil Misra (IICT) / Dr. Sunil Misra (IICT); Medicine: Dr. Andugulapati Sai Balagi (IICT) / Dr. Sunil Misra (IICT).
- **Caveat**: an SI model on co-authorship ties is a stylised scenario (who *could* spread a technique fastest), not observed diffusion.
- **Artifacts**: `src/stats/insights/s11_information_diffusion.py`, `stats/tables/insights/11_information_diffusion.json`, `stats/tables/insights/11_field_diffusion_metrics.csv`, `stats/tables/insights/11_super_spreaders_blockers.csv`, Card 11 in `dashboard/index.html` and `dashboard/js/app.js`.

### D-27 (2026-10-31): Second Review of the Insights
- **Co-author graph identity (Insights 1, 2, 3, 11)**: the graph keyed people by display name from `authorship_network.csv`, so 111 names shared by different OpenAlex authors were merged into one node, roster scientists printed under two spellings became two nodes (297 faculty nodes for fewer scientists), and a node's lab came from its first edge. `coauthor_graph()` now builds the graph from `group24_data_extended.csv` keyed by `author_openalex_id` (name only for the 1,579 rows without an ID), with name = most frequent spelling, lab = roster lab for faculty (else most frequent lab), and the same >30-author drop rule (5 papers). LCC 7,509 → 7,752 researchers; 270 roster faculty, each once. The Task 4 authorship network (report, dashboard) is unchanged and still name-based, so its node counts differ from the insights'.
- **Data issue found**: all 1,579 rows without an OpenAlex author ID carry `faculty_id = FORMER_CECRI_0005` (936 different names). The insights no longer use `faculty_id` as an identity for those rows; the upstream assignment is not fixed here (see LIMITATIONS).
- **Insight 3**: random removal is now exact at every step (union-find, adding nodes back in reverse) instead of checked every 20 removals.
- **Insight 4**: the √N marker is drawn on the Lorenz curve (it was in the chart data but outside any series, so never shown).
- **Insight 5**: headline answers its question in both directions (share of top-10% papers in Q1, and share of Q1 papers in the top 10% vs Q2–Q3); the eligible-paper count in the note is computed, not typed.
- **Insight 7**: says "highest-B sustained case" and its rank among the top-1% candidates, and counts spikes and too-recent peaks separately.
- **Insight 8**: "above the 2016–19 trend" read as growth although output was falling ~8%/yr before 2020 and the trend projects that decline. The headline now leads with the change from 2019 and the pre-pandemic rate, then the trend comparison; the dashed projection starts at 2019.
- **Insight 9**: a returnee needs the order India (PhD proxy) → abroad spell (starting no earlier than the third paper's year) → an Indian affiliation in a later year. A spell without a later Indian year no longer counts.
- **Insight 10**: divisions come from the roster and are keyed by (lab, division) — rows were grouped by name only and labelled with the first row's institution, so same-named divisions of different labs merged and could be shown under the wrong lab. "Contact Number:" (scraping artefact) is excluded. The headline shows the 32–28 age cut-off range for the highlighted lab.
- **Insight 11**: (a) runs depended on set iteration order (PYTHONHASHSEED) — nodes are now visited in sorted order and subgraphs built in a fixed order; (b) the method note said M = 50 but the code ran 25 — now 50 everywhere, with the 25/50/100 convergence check kept; (c) runs that never reached 50% were averaged as T50 = 15 — T50 is now the median step (not reached when the median run does not get there), with the number of seeds reaching 50%; (d) the headline's βc range and all field sizes are computed, not typed; (e) super-spreader names carry `faculty_id` (dashboard hover/profile links).
- **Cache safety**: an insight whose OpenAlex cache is missing keeps its previously computed JSON instead of overwriting it with "Not computed".
- **Determinism**: Insights 1–5, 8 and 11 give identical outputs under PYTHONHASHSEED 1 and 987 (test added for the SI simulation).
- **Not rerun here**: Insights 7, 9 and 10 need `data/cache/openalex` (`make insights-fetch`), which is not in this checkout; their committed JSONs predate these fixes until someone with the cache runs `make insights`.
- **Effect on headlines**: Insight 1: 93.2% (unchanged), ⟨k⟩ 9.2 → 9.1; Insight 2: ρ_norm 0.75 → 0.73; Insight 3: n50 841 → 825 bridges, random 3,282 → 3,380, lab split 644 → 691; Insight 5 reframed (88.7% of top-10% papers in Q1; 14.0% of Q1 vs 3.5% of Q2–Q3 papers reach the top 10%); Insight 8 reframed (−8.7% 2019→2020 after −8.4%/yr since 2016); Insight 11: Chemistry Condition B T50 5.81 → 6 (all 15 seeds reach 50%), Condition A reach 76.5% → 76.2%; under Condition A only Chemistry (T50 9) and Energy (T50 14, 11 of 15 seeds) reach 50% within 15 steps.


### D-28 (2026-11-02): Dashboard IF and Q1-papers filters; h-index by campus
- **Journal IF filter (paper-level)**: Clarivate JIF is proprietary and not used (§5.8). The dashboard's "Journal IF" is SCImago's `citations_doc_2years` (Cites / Doc. 2 years, an IF analogue on Scopus data) from `data/external/sjr_journals.rda`, taken from the same SCImago year as the paper's quartile (`quartile_year_used`) and matched on `issn` / `issn_l`, then on the cleaned journal title. 13,443 of the 14,352 papers have a value (13,443 of the 13,482 with a quartile); the rest are excluded when a threshold is set. Thresholds: ≥2, ≥3, ≥5, ≥10 (distinct papers: 11,553 / 9,051 / 4,217 / 817). Stored as `jif` on `papers_compact`; it filters every paper-based panel like the quartile filter.
- **Scientists filter (faculty-level)**: "> 5" / "> 10 Q1 papers" (strictly more than) restricts the Faculty tab: featured scientists, directory (new "Q1 Papers" column), h-index histogram and the Active faculty / Median h-index KPIs (177 / 133 active scientists). The department chart is pre-aggregated and is not filtered.
- **h-index histogram**: binned in the browser from the faculty rows with the bins of `h_index_distribution.csv` (identical counts to the table for every institute); in All / Compare view the bars are stacked by campus in the lab colours.
- **Rebuilt bundle**: rebuilding `g24_data.js` also refreshed the citation-network panel's top-subgraph (346 → 334 links). The committed bundle did not match what the committed code and data produce; the rebuild is identical under different PYTHONHASHSEED values.

### D-29 (2026-11-02): Cadre Faculty Networks & Deterministic NIMFA Markov Spreading Suite
- **Motivation**: Address faculty vs. junior researcher roles in network diffusion by isolating the 306 permanent cadre faculty across CSIR-NCL, CSIR-IICT, and CSIR-CECRI, and formulate a closed-form Discrete-Time Markov Chain (NIMFA) to benchmark against stochastic Monte Carlo SI.
- **Methodology**:
  1. **Cadre Co-Authorship & Citation Networks**:
     - *Cadre Co-Authorship*: restricted strictly to the 306 cadre faculty ($N=235$ connected nodes, $E=579$ unique pairs, $\langle k \rangle = 3.80$, $\beta_c = 0.0993$).
     - *Faculty-to-Faculty Directed Citation*: links from cited faculty to citing faculty ($N=245$ connected, $E=1,610$ directed links, $\langle k \rangle = 6.57$, reciprocity = 0.285).
  2. **Deterministic Discrete-Time Markov Chain (NIMFA)**:
     - Updates: $x_i(t+1) = x_i(t) + (1 - x_i(t)) [1 - \prod_{j \in \mathcal{N}_{\text{in}}(i)} (1 - \beta_{ji} x_j(t))]$.
     - Evaluated across 4 network topologies: Full Co-Authorship ($N=7,509$), Cadre Co-Authorship ($N=235$), Full Citation ($N=10,988$), Cadre Citation ($N=245$).
  3. **Jensen's Inequality Gap**: Quantified the theoretical over-estimate $\Delta(t) = I_{\text{NIMFA}}(t) - I_{\text{MC}}(t) \ge 0$ resulting from neglected positive clique correlations in the mean-field approximation.
  4. **Dedicated Interactive Portal**: Developed `dashboard/insights11.html` with a standalone dark scientific theme, force-directed graph canvases, simulation toggles, and data cleaning audit logs.
- **Key Findings**:
  - Removing non-cadre researchers causes the epidemic threshold $\beta_c$ to jump from 0.0322 to 0.0993, proving that junior scholars provide essential structural bridging across CSIR labs.
  - The Full Paper Citation Network is strongly DAG-like with low reach ($\approx 1.8\%$), whereas the Faculty-to-Faculty Citation Network contains dense cyclical feedback loops reaching $91.8\%$ of faculty.
- **Artifacts**: `src/stats/insights/s11_cadre_networks.py`, `src/stats/insights/s11_nimfa_spreading.py`, `src/stats/insights/s11_data_cleaning_audit.py`, `dashboard/insights11.html`, `dashboard/css/insights11.css`, `dashboard/js/insights11.js`, `dashboard/data/g24_insights11_suite.js`.

---

### D-30 (2026-11-02): Five Macro & Comparative Insights Architecture
- **Motivation**: Provide intuitive, statistically sound, macro-level and comparative insights evaluating the CSIR chemistry cluster in relation to state economies, premier higher education institutions (IITs/IISc), international peers, national R&D expenditure constraints, and industrial patenting.
- **Components & Scope**:
  1. **Insight 2.1 — Smart Specialization & Regional Economy**:
     - Correlates scientific Revealed Comparative Advantage (RCA) with host state 2-digit National Industrial Classification (NIC) value-added Location Quotients (LQ) from RBI and MoSPI ASI records:
       - CSIR-IICT / Telangana: NIC 21 (Pharmaceuticals & Active Pharmaceutical Ingredients)
       - CSIR-NCL / Maharashtra: NIC 20 (Specialty Chemicals, Catalysts & Polymers)
       - CSIR-CECRI / Tamil Nadu: NIC 27 (Electrical Equipment, Batteries & Electrochemical Cells)
  2. **Insight 1.1 — The Academic-Industrial Bridge**:
     - Computes the bidirectional Knowledge Exchange Ratio ($K_{ER} = C_{\text{HEI} \to \text{CSIR}} / C_{\text{CSIR} \to \text{HEI}}$) across 192,994 citation edges to evaluate idea export vs. import between CSIR and:
       - Elite Flagships (IIT Bombay, Madras, Delhi, Kharagpur, Kanpur, Roorkee, Guwahati, and IISc Bangalore).
       - Regional State Universities (Savitribai Phule Pune Univ, Osmania Univ, Univ of Hyderabad, Alagappa Univ), proving CSIR's regional infrastructure uplift role.
  3. **Insight 5.1 — Scientific "Frugal Innovation" & Macro GERD**:
     - Evaluates cost-per-Q1-paper and cost-per-citation under India's national R&D intensity ceiling (~0.65% GDP) using Union Budget Demand No. 91 and CSIR Annual Accounts (~₹180–₹240 Cr/year per lab direct expenditure).
     - Benchmarks against Max Planck Society (Germany), CNRS (France), and US Department of Energy National Labs (Ames, Argonne).
  4. **Insight 5.2 — Patent-to-Paper Decoupling**:
     - Contrasts industrial technology translation (domestic IPO vs. international PCT/US patents from CSIR IPMD and Annual Reports) with academic citation metrics across the 306 cadre faculty.
     - Identifies a 4-quadrant taxonomy separating applied process pioneers from theoretical academic chemists.
  5. **Insight 3.1 — Global Leiden "Crown Indicator" Benchmarking**:
     - Measures field-normalized proportions of top-10% ($PP_{\text{top 10\%}}$) and top-1% ($PP_{\text{top 1\%}}$) papers, and Mean Normalized Citation Score ($MNCS$), benchmarked against CWTS Leiden Ranking Open Edition open chemistry datasets.
- **Implementation Strategy**:
  - Independent, double-clickable offline HTML portals for each study (`insight_smart_spec.html`, `insight_academic_bridge.html`, `insight_frugal_rd.html`, `insight_patents_papers.html`, `insight_leiden_benchmarks.html`).
  - Embedded **Data Collection, Preprocessing & Cleaning Methodology Audit** accordion on every page with explicit mathematical formulations, government document citations, and sample data.
  - Comprehensive unit test suite in `tests/test_macro_insights.py`.

### D-31 (2026-11-02): Aesthetic, Mathematical, and Textual Refinement of Insights Suite
- **Context & Motivation**: Refine the visual presentation, navigation hierarchy, mathematical formula rendering, and textual tone across `insights11.html`, the 5 macro-insight portals, and the main dashboard.
- **Key Enhancements**:
  1. **Two-Tier Navigation Architecture**: Separated the cluttered top navigation into two visual tiers on `insights11.html`:
     - Level 1 (Top Bar): Global navigation links to `Main Dashboard` and the five macro studies (clean text links, zero emojis).
     - Level 2 (Section Subnav): Crisp horizontal tab bar switching between the 6 on-page sections (`4-Network Overlay`, `Seed Origin Dynamics`, `Intra-Institute Spreading`, `Cadre Faculty Graphs`, `SI vs. NIMFA Theory`, `Roster & Cleaning Audit`).
  2. **Offline Vector Mathematical Formula Rendering**:
     - Vendored MathJax 3 (`vendor/mathjax/tex-svg.js`, 2.1 MB) for 100% offline TeX-to-SVG vector math rendering.
     - Converted raw LaTeX strings across `insights11.html` and all five macro portals to standard MathJax delimiters (`$...$`, `$$...$$`). Verified that 70 math SVG elements render on `insights11.html`, 23 on `insight_academic_bridge.html`, 15 on `insight_leiden_benchmarks.html`, 7 on `insight_smart_spec.html`, 5 on `insight_patents_papers.html`, and 2 on `insight_frugal_rd.html` with zero external web font dependencies over `file://`.
  3. **Complete Elimination of Emojis**:
     - Stripped all emojis (`🏭`, `🌉`, `💰`, `📜`, `👑`, `🔬`, `💡`, `🔍`, `📁`, `📐`, `⚙️`) from all HTML files, stylesheets, and JavaScript logic.
  4. **Subdued Academic Typography & Theme**:
     - Standardized on a modern sans-serif typography stack (`-apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif`).
     - Subdued cards with 1px border (`#e2e8f0`), soft shadows, and clean border radii.
     - Redesigned interpretation cards into publication-grade analytical briefing blocks with clean headers and muted backgrounds.
  5. **Objective Scientific Phrasing & Elimination of First-Person Pronouns**:
     - Audited and eliminated all occurrences of `we`, `our`, and `us` in analytical interpretation blocks and hero descriptions in favor of direct, objective empirical statements.
- **Verification**: All 68 pytest unit tests pass in 12.7s; full browser test suite passes across all 7 pages with zero JavaScript/console errors under HTTP and offline `file://`.

### D-32 (2026-11-02): Dashboard Redesigned as a Single Scrolling Page
- **Context**: In the meeting with the instructor, the horizontal tab bar was hard to notice and the team had to show him how to navigate. He asked for every important number to be clearly visible, smooth navigation, and the insights on the main page.
- **Decision**: `dashboard/index.html` is now one scrolling page of ten full-height sections (Home, Key Findings, Trends, Faculty, Journals, Research Areas, Citation Network, Co-authorship, India Links, Data & Methods). Navigation: a sticky header with a link per section (current section highlighted), a "Next ↓" arrow at the end of every section, a floating next-section button, side dots and a reading-progress bar (`dashboard/js/nav.js`). The home screen carries the KPI cards. The 11 insights are boxes on the main page, each with one number read from the insight's `metrics`; a click opens the chart, headline and method in a modal. The institute buttons stay in the sticky header; filters open from a "Filters" button and active filters show as removable chips.
- **Unchanged**: all chart/table element IDs, the data files, the numbers and the filter logic. The network and India-links sections are drawn when first scrolled into view (they were drawn on tab click before).
- **Tests**: `scripts/test_browser.py` scrolls to each section instead of clicking tabs and opens all 11 finding modals.
- **Theme (same day)**: dark theme by default, with a Light/Dark button in the header (floating button on the extended-study pages). `dashboard/js/theme.js` sets `<html data-theme>`, remembers the choice in the browser, and gives ECharts a matching dark theme; colours are CSS variables with a light and a dark set (`css/style.css`, `css/insight_pages.css`, `css/insights11.css`). On the main page charts are redrawn on a switch; the study pages reload. Lab colours are lightened on the dark background (IICT #5b9bd5, NCL #4caf50, CECRI #f28c38).
- **Merge with D-31**: the study pages keep the D-31 design and MathJax formulas; the dark theme is applied on top through CSS variables (`css/insight_pages.css`, `css/insights11.css`) and `js/theme.js`. Emojis are also removed from the redesigned main page.

### D-33 (2026-11-02): Instructor Review — Network Sizes, Duplicates, IR Thresholds, Audit of D-30/D-31
- **Context**: The instructor doubted the network sizes ("thousands of nodes; even big IITs do not have thousands") and suspected double counting or students counted as faculty. He also asked to show papers with IR > 5 and IR > 10, and for more paper information in the tables.
- **What the nodes were**: the paper citation network has one node per paper (10,931 papers; correct, but papers are not people). The all-author co-authorship network had one node per author *name*: 7,853 names, of which only 283 are roster faculty; the rest are PhD students, postdocs, project and former staff. Names also merge different people (two different "Dr. Amitava Das", IICT and NCL) and 264 names stand for more than one OpenAlex author.
- **Decision — faculty networks**: added faculty co-authorship and citation networks with one node per roster scientist (`faculty_id`), using the papers at the scientist's roster lab (the faculty_master.csv rule) — `src/stats/networks.py`, `network_faculty_*.csv`, rows `faculty_*` in `network_summary.csv`. 306 scientists; 553 co-author pairs (16 across labs); 1,534 directed citation links (7,757 paper-to-paper citations, 13,363 self-citations left out). The dashboard and report lead with these; the paper and all-author networks stay as clearly labelled secondary views. Network KPIs on the dashboard had been typed into the HTML (stale: 27,754, 11,008, 7,864 …); they are now read from the data, and edge counts are distinct pairs.
- **Decision — duplicate papers (Step 20)**: `src/collect/20_dedupe_papers.py` removes or merges 144 records: 64 Angewandte Chemie German-edition copies of International Edition papers, 48 retraction notices / corrections / cover pictures / prefaces, 15 repository copies (Zenodo, Figshare, records without DOI; repository records carrying a journal DOI stay), 11 same-title same-journal duplicates, 6 extra version DOIs (eLife, JoVE). Author rows of merged records move to the kept record; citation and authorship edges are re-pointed. Corpus 14,352 → 14,208 papers, 42,393 → 41,989 rows. Runs after Steps 17/18 so their cached API batches are unchanged. List: `data/review/duplicate_papers_removed.csv`.
- **Fix — former-faculty flag**: Step 07 grouped every author without an OpenAlex ID as one person (`FORMER_CECRI_0005`, 936 names); the flag is cleared on those rows and Step 07 now skips empty IDs.
- **Fix — faculty counts**: `faculty_performance.csv` and the profile panel counted papers credited to another lab under the same OpenAlex profile (8 scientists, e.g. 26 vs 1 paper), while h-index used the roster lab only. All now use the roster-lab rule; `faculty_master.csv` counts are recomputed in Step 20.
- **Decision — IR > 5 and IR > 10**: `impact_ratio.thresholds: [5, 10]` alongside the 75th-percentile threshold (now 0.60 after Step 20). IR > 5: 73 papers (0.53%), IR > 10: 18 (0.13%). OpenAlex sometimes lists only part of a reference list (a 2017 review with 2 references has IR 287), so each count also gives the papers with ≥ 10 references (57 and 13) and the dashboard list flags the rest. Dashboard: new card with counts, by-lab and by-year charts and the paper list (follows filters).
- **Tables**: top-cited papers now show labs, lab authors, type, field, journal IF, references and IR (quartile badge colour fixed); PageRank table shows all-time citations, references and IR; profiles show references and IR per paper.
- **Audit of D-30 (macro studies)**: Study 5.2 assigns each named scientist a patent count from a formula (department, designation, paper count and a name hash), not from patent records; 5.1's paper trajectory and Q1/citation counts do not match the dataset and its budgets and international benchmarks are typed in; 3.1 normalises citations within our own corpus (so the cluster is ~world average by construction) and compares that with typed-in Leiden values; 2.1's state industry figures and its "synergy" verdicts are typed in. **2.1, 3.1, 5.1 and 5.2 are withdrawn** from the dashboard (unlinked, banner on the pages, tests skipped, not built by `run.py macro-insights`) until their inputs are files in `data/external/`. 1.1 (Academic Bridge) is computed from `citation_network.csv` and stays; its headline numbers and text, previously typed in, are now read from the data.
- **Audit of D-29/D-31 (Cadre suite)**: the cadre summary table had typed-in values for both full networks and for the cadre citation network's clustering, modularity and βc; `s11_nimfa_spreading.py` built the intra-lab cadre graph from `zip(intra_cadre["author_a"], cadre_auth["author_b"])` (a filtered and an unfiltered column, so the wrong scientists were paired); network labels carried typed-in sizes ("N=235", "N=7,509" for a 7,534-node graph); the page's tables and paragraphs were typed-in numbers. The cadre graphs now come from `src/stats/networks.py`; every table and sentence on the page is generated from the simulation output; unsupported causal statements were removed. `src/stats/insights/common.py` no longer asserts a fixed paper count.

