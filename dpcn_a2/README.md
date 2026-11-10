# DPCN Research Mapping Project 2026 — Group 24
### CSIR Chemistry Cluster ("Synthetic & Organic Chemistry")
**Instructor**: Chittaranjan Hens · **Course**: DPCN 2026 · **Collection Date**: 13 October 2026

---

## 1. Executive Summary & Scope

**Group 24** is assigned the premier CSIR Chemistry cluster comprising three leading national research laboratories:

| Institute | Full Name | Location | ROR ID | OpenAlex ID |
|---|---|---|---|---|
| **CSIR-NCL** | CSIR – National Chemical Laboratory | Pune, Maharashtra | `057mn3690` | `I3125981224` |
| **CSIR-IICT** | CSIR – Indian Institute of Chemical Technology | Hyderabad, Telangana | `040dky007` | `I55664587` |
| **CSIR-CECRI** | CSIR – Central Electrochemical Research Institute | Karaikudi, Tamil Nadu | `01qek3q18` | `I106349282` |

Parent Body: **Council of Scientific & Industrial Research (CSIR)** — ROR `021wm7p51` (`I66760702`).

### Dataset Highlights (2016–2026)
- **14,208 Distinct Peer-Reviewed Publications** (filtered for original research & reviews; errata, retraction notices, cover pictures, prefaces and duplicate records of the same paper removed, D-33).
- **41,989 Attributed Authorship Records** (paper × assigned-institute author).
- **63.3% Global Q1 Journal Share** (SCImago SJR 1999–2025 historical panel).
- **385 Scientific Cadre Faculty** on the official institute rosters (505 scraped; 119 IICT technical-staff entries and 1 duplicate removed, D-25); 306 have papers in 2016–2026.
- **192,426 Directed Citation Edges** in `citation_network.csv`: 27,582 within the corpus (27,099 distinct paper pairs; a pair whose citing paper belongs to two labs has one row per lab) + 164,844 with Indian-affiliated papers outside it (D-16, D-17, D-33).
- **Faculty networks** (D-33): one node per roster scientist — 306 scientists; 553 co-author pairs and 1,534 directed citation links between them. The paper-level citation network (10,931 papers) and the all-author co-authorship network (7,853 authors, of whom 283 are roster faculty and the rest students, postdocs and staff) are kept as secondary views.
- **Zero Data Fabrication**: 100% of publications, citations, and DOIs originate from verified OpenAlex and Crossref records.

---

**Live dashboard:** https://dpcnsite.vercel.app/ (Vercel, deployed from `dashboard/` with `vercel --prod`)

## 2. Repository Layout & Deliverables

```
group24/
├── data/
│   ├── final/
│   │   ├── group24_data.csv            # Task 1 Primary Dataset (exact 14 required columns)
│   │   ├── group24_data_extended.csv   # Rich dataset with 35 metadata & thematic fields
│   │   ├── faculty_master.csv          # 385 scientific cadre faculty with corpus h-indices
│   │   ├── citation_edges_raw.parquet  # 27,816 directed citation edges for Task 4
│   │   └── works_table.parquet         # Deduplicated work-level parquet
│   └── MANIFEST.json                   # Cryptographic SHA256 checksums, metadata, and timestamps
├── stats/
│   ├── report/
│   │   ├── 24_CSIR.pdf    # Task 2 Presentation Report (PDF format, <= 10 slides)
│   │   └── 24_CSIR.pptx   # Task 2 PowerPoint Presentation (10 slides)
│   ├── figures/                        # 8 publication-quality figures (300 DPI PNG + SVG)
│   └── tables/                         # 24 metric CSV tables (incl. Indian connectivity, Sections 7a/7b)
├── dashboard/                          # Task 3 Interactive Standalone Dashboard
│   ├── index.html                      # Double-click offline dashboard (no server needed)
│   ├── css/style.css                   # Custom responsive styling
│   ├── js/app.js                       # Client-side filtering & ECharts controller
│   ├── data/g24_data.js                # Pre-aggregated data payload (window.G24_DATA)
│   └── vendor/                         # Vendored offline dependencies (ECharts 5, Tabulator)
├── config/
│   ├── institutions.yaml               # Verified ROR and OpenAlex entity configurations
│   └── indian_inst_registry.csv        # 910 canonical Indian institutions classified by sector
├── docs/
│   ├── QA_REPORT.md                    # Step 13 QA verification report (100% PASS)
│   ├── DATA_DICTIONARY.md              # Comprehensive definitions of all data columns
│   ├── DECISIONS.md                    # Methodological log of all architectural decisions
│   └── LIMITATIONS.md                  # Scientific limitations and disclosures
├── src/                                # Modular, reproducible Python pipeline
│   ├── collect/                        # Steps 01 to 14 (data extraction, curation, QA, export)
│   ├── stats/                          # Metrics, high-res figures, PowerPoint builder
│   ├── dashboard/                      # Dashboard data compilation
│   └── common/                         # HTTP cache, name tokenizers, ISSN normalizers
├── tests/                              # Automated test suite (Pytest)
├── run.py                              # CLI runner (all, collect, stats, dashboard, test)
├── Makefile                            # Standard POSIX make target interface
└── requirements.txt                    # Pinned Python dependencies
```

---

## 3. Quick Start & Execution

### 3.1 Setup Environment
Install dependencies:
```bash
pip install -r requirements.txt
```

### 3.2 Run Complete Pipeline
Execute the full collection, statistics, and dashboard pipeline:
```bash
python3 run.py all
# Or if make is installed:
make all
```

Individual pipeline targets:
- `python3 run.py collect`: Runs Phase 1 data collection, filtering, quartile mapping, and QA validation.
- `python3 run.py stats`: Calculates metric tables, generates 300 DPI figures, and compiles the 10-slide PPTX & PDF reports.
- `python3 run.py dashboard`: Compiles the compact data payload into `dashboard/data/g24_data.js`.
- `python3 run.py test`: Runs all Pytest unit, integrity, and consistency tests.
- `python3 run.py insight11`: Insight 11 only (how ideas spread: field study, four networks, threshold test, claims and the page data for `dashboard/insights11.html`; no API calls).
- `python3 run.py global`: Global benchmark only (peer selection, benchmark data, tables and `dashboard/data/g24_global.js`); see 3.4.

### 3.3 Opening the Interactive Dashboard (Task 3)
The dashboard is **100% self-contained and offline-capable**:
1. Navigate to the `dashboard/` directory.
2. Double-click `index.html` to open directly in any modern browser (Chrome, Firefox, Safari, Edge) via `file://`.
3. No web server, Node.js, or internet connection is required.

### 3.4 Global Benchmark (lead work, D-35)
`dashboard/global.html`, opened from the highlighted **Global Benchmark** button on the home screen, compares
CSIR-NCL, CSIR-IICT and CSIR-CECRI with their closest government-lab "twins" in the USA, China, South Korea
and Australia and with six Indian reference institutes, and lists every country the labs co-author with.
- Peer rules: `config/global_benchmark.yaml`; hand-reviewed exclusions: `config/overrides/global_peer_exclusions.csv`.
- Data: `src/collect/22_global_peers.py` (peer selection) and `23_global_benchmark.py` (OpenAlex output,
  field-normalised impact, co-authorship and citation flows), cached in `data/cache/`; raw files in `data/final/global/`.
- Tables: `src/stats/global_benchmark.py` → `stats/tables/global_*.csv`; payload: `src/dashboard/build_global.py`.
- Rebuild: `python run.py global` (re-runs from the cache at zero API cost).

---

## 4. Primary Dataset Specification (`group24_data.csv`)

The primary dataset strictly adheres to the 14 mandatory columns in exact canonical order:

| # | Column | Description | Format / Sample |
|---|---|---|---|
| 1 | `group` | Group assignment identifier | `24` |
| 2 | `institution` | Canonical institute | `CSIR-NCL`, `CSIR-IICT`, `CSIR-CECRI` |
| 3 | `author` | Harmonized author name | `Sivaram Swaminathan` |
| 4 | `title` | Publication title | Text |
| 5 | `year` | Publication year | `2016`–`2026` (2026 is partial) |
| 6 | `type` | Venue type | `journal` or `conference` |
| 7 | `journal_name` | Source display name | `ACS Applied Materials & Interfaces` |
| 8 | `issn` | Hyphenated ISSN | `1944-8244` (blank for conferences) |
| 9 | `doi` | Canonical resolving DOI | `https://doi.org/10.1021/acsami...` |
| 10 | `citations` | Total OpenAlex citations | Integer $\ge 0$ |
| 11 | `quartile` | SCImago SJR quartile | `Q1`, `Q2`, `Q3`, `Q4`, or blank |
| 12 | `coauthor_institutes` | Semicolon-delimited Indian partners | `IIT Bombay; IISc Bangalore` |
| 13 | `cites_indian_inst` | References other Indian labs | `TRUE` / `FALSE` |
| 14 | `cited_by_indian_inst` | Cited by other Indian labs | `TRUE` / `FALSE` |

*Note on Granularity:* Structured at **paper × assigned-institute author** level. Never sum `citations` across rows without paper deduplication.

---

## 5. Validation & Quality Assurance (QA)

Run automated QA, schema verification, and consistency tests:
```bash
python3 run.py test
```
**Results (14/14 Passed):**
- Schema & Column Order: Exact 14 columns, UTF-8 BOM-free, LF newlines.
- Domain Integrity: Group 24 constant, valid institutes, years 2016–2026, valid quartiles.
- Citations Consistency: Identical citation count across multiple authors of the same paper.
- 90 Random Spot-Checked DOIs (30 per lab): 100% verified against Crossref / OpenAlex.
- 10 Random Dashboard Numbers: Verified 100% identical between dashboard bundles and raw metrics tables.
- Full details documented in [`docs/QA_REPORT.md`](docs/QA_REPORT.md).

Run headless browser end-to-end verification suite:
```bash
python3 run.py browser-test
```
- Tests all 11 dashboard panels, institute toggles, filters, and Tabulator tables via Chrome DevTools Protocol (CDP).
- Verifies offline `file://` protocol execution with zero console errors.
- Captures screenshots in `dashboard/screenshots/`.

---

## 6. Deferred Task 4 Assets Prepared

While Task 4 network analysis (PageRank, Louvain community detection, interactive network canvas) is deferred, all necessary underlying data graphs have been extracted and persisted:
- **`data/final/citation_edges_raw.parquet`**: 27,816 directed citation edges.
- **`config/indian_inst_registry.csv`**: 910 categorized Indian partner institutions.
- **Interactive Dashboard**: Features dedicated styled placeholder panels for Citation Network (Panel 10) and Authorship Network (Panel 11).
- **Report**: Slides 9 and 10 contain detailed architectural blueprints and metrics previews for the network modules.
