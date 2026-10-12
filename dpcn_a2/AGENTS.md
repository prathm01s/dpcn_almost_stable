# AGENTS.md — DPCN Research Mapping Project · Group 24

> Operating manual for the AI agent. Read this whole file before doing anything. Re-read the relevant phase before starting it.
> Instructor: Chittaranjan Hens · Course: DPCN 2026 · Collection date for this project: **October 2026** (record the exact date in `data/MANIFEST.json`).

---

## 0. Mission, scope and ground rules

**Group 24** is assigned the **CSIR Chemistry cluster ("Synthetic & Organic Chemistry")**:

| Short | Full name | City | ROR ID (verify, see §4) |
|---|---|---|---|
| **NCL** | CSIR – National Chemical Laboratory | Pune, Maharashtra | `https://ror.org/057mn3690` |
| **IICT** | CSIR – Indian Institute of Chemical Technology | Hyderabad, Telangana | `https://ror.org/040dky007` |
| **CECRI** | CSIR – Central Electrochemical Research Institute | Karaikudi, Tamil Nadu | `https://ror.org/01qek3q18` |

Parent body of all three: Council of Scientific & Industrial Research (CSIR), ROR `https://ror.org/021wm7p51`.

### What we are building NOW (Phase 1–3)
1. **Task 1 — Dataset**: `group24_data.csv` with every paper (2016–2026) by faculty/authors of the three institutes.
2. **Task 2 — Statistics report**: ≤10 slides or ≤5 pages.
3. **Task 3 — Interactive dashboard**.

### What we are NOT building yet (Task 4, deferred)
Citation-network and authorship-network analysis/visualisation (PageRank, centralities, Louvain, network CSV exports, D3/Cytoscape graphs). **BUT**: the dataset columns `coauthor_institutes`, `cites_indian_inst`, `cited_by_indian_inst` are part of Task 1 and ARE required now. Also, during collection, **persist the raw material the networks will need later** (referenced_works edges, per-paper author lists with institutions, citing-work metadata) — see §9. The dashboard must reserve two clearly-marked placeholder tabs for the two network panels.

### Non-negotiable rules
1. **Never fabricate data.** No invented papers, DOIs, quartiles, h-indices, faculty names, or numbers in prose. If something cannot be obtained, leave it blank/`NA`, log it, and report the gap. Every number shown in the report/dashboard must be traceable to a file in `data/`.
2. **Years 2016–2026 only** (publication_year between 2016 and 2026 inclusive). 2026 is a *partial year* (data collected in Oct 2026) — always label it so.
3. **Analysis stays within our three institutes.** Cross-institute (Indian) links appear only as raw-data columns and, optionally, a small preview panel. Do **not** pull or merge any other group's data.
4. **Group-independent**: no use of other groups' outputs.
5. **Secrets**: the OpenAlex API key lives in `.env` (`OPENALEX_API_KEY`). Never print, log, commit, or write it into any cached URL/manifest. Strip `api_key=` from every logged URL.
6. **Resumable & idempotent**: every stage reads from/writes to disk caches; re-running must not re-spend API budget for already-cached requests.
7. **Reproducible**: one command per phase (`make collect`, `make stats`, `make dashboard`, `make all`). Seeds fixed. Package versions pinned in `requirements.txt`.
8. **When blocked or ambiguous**, do the safest reasonable thing, document it in `docs/DECISIONS.md`, and continue; escalate only items in §13 or genuine blockers (e.g., API key missing, budget exhausted).
9. **Verify before relying on memory.** OpenAlex's API changed substantially in 2026 (see §3). If any endpoint, filter, or field behaves differently from this file, trust the live docs (`https://help.openalex.org`, machine index `https://help.openalex.org/llms.txt`) and the live API responses, and record the discrepancy in `docs/DECISIONS.md`.

---

## 1. Assignment digest (authoritative requirements from the two source documents)

### 1.1 Deliverables and deadlines
| When | Deliverable |
|---|---|
| Week 1–2 | `group24_data.csv` (+ `citation_network.csv`, `authorship_network.csv`, `indian_connections.csv` — the three network files belong to deferred Task 4 but plan for them) |
| Week 3 | Statistics report (≤10 slides / ≤5 pages) + interactive dashboard (with network visualisation panels — to be completed in Task 4) |

### 1.2 Required CSV: `group24_data.csv` — EXACT columns, in this order
| # | Column | Rule for us |
|---|---|---|
| 1 | `group` | always `24` |
| 2 | `institution` | one of exactly: `CSIR-NCL`, `CSIR-IICT`, `CSIR-CECRI` (see §4 for display names) |
| 3 | `author` | full name of the author (faculty/author) on that row |
| 4 | `title` | paper title |
| 5 | `year` | publication year, integer 2016–2026 |
| 6 | `type` | `journal` or `conference` (lowercase) |
| 7 | `journal_name` | journal or conference (source) display name |
| 8 | `issn` | ISSN (journals only; hyphenated `NNNN-NNNC`; prefer print/linking ISSN; blank for conferences) |
| 9 | `doi` | DOI as URL `https://doi.org/10.xxxx/...` (lowercase DOI); blank if none |
| 10 | `citations` | citation count at collection date (OpenAlex `cited_by_count`) |
| 11 | `quartile` | `Q1`/`Q2`/`Q3`/`Q4` for journals; `CORE A*`/`CORE A`/`CORE B`/`CORE C` for conferences; blank if unknown |
| 12 | `coauthor_institutes` | semicolon-separated list of co-author institutions (Indian connections — see §5.10 for our exact definition) |
| 13 | `cites_indian_inst` | `TRUE`/`FALSE` — paper cites a paper from another Indian institution |
| 14 | `cited_by_indian_inst` | `TRUE`/`FALSE` — paper is cited by a paper from another Indian institution |

**Row granularity: one row per (paper × author-of-assigned-institute).** A paper with 4 NCL authors yields 4 rows. Therefore **never sum the `citations` column across rows** — always deduplicate to paper level first (§6.2).

Extra columns are NOT allowed in `group24_data.csv` (the spec says the file "must include" these columns; keep it clean). All extra fields go to `group24_data_extended.csv` (same rows, same order, plus extra columns — see §5.14).

### 1.3 Dashboard — required panels (per institution)
1. Publication trend chart (papers/year, 2016–2026)
2. Faculty list (name, department, h-index, total papers)
3. Journal quartile distribution (stacked or pie; Q1/Q2/Q3/Q4)
4. Faculty performance table (sortable: papers, citations, top journal, h-index)
5. Top 5 journals by paper count
6. h-index distribution histogram
7. Research-area breakdown (publication share by domain/field)
8. Top 10 most-cited papers (title, journal, year, citations, DOI)
9. Conference rank breakdown CORE A*/A/B/C ("where applicable")
10. Citation network visualisation (directed; **Task 4 — placeholder now**)
11. Authorship network visualisation (undirected; **Task 4 — placeholder now**)

### 1.4 Statistics report — required content (≤10 slides or ≤5 pages)
Faculty-, department-, and institution-level: publication trend (total + per year); Q1 fraction per institution; h-index distribution; top-5 journals per institution; top-10 most-cited papers; research-area breakdown; citation-network summary and authorship-network summary (**Task 4 — reserve space**).

### 1.5 Hints from the documents that matter to us
- Sources suggested: OpenAlex (primary), IRINS, Scopus (secondary, quartile/citations), ROR IDs (for accurate OpenAlex queries — "esp. ISI, TIFR, CSIR"), Scimago/JCR (quartile), CORE (conference rank).
- The instructor encourages **cross-checking institute websites for faculty lists** (stressed for newer IITs and small institutes; same logic applies to us).
- Checklist: file named correctly, all columns present, 2016–2026 only, all assigned institutions included, report within length, dashboard includes network panels, nothing shared with other groups.

---

## 2. Repository layout (create exactly this)

```
group24/
├── AGENTS.md
├── README.md                     # human quick-start (how to run, how to open dashboard)
├── Makefile                      # collect / stats / dashboard / all / test / clean-cache
├── requirements.txt              # pinned
├── .env.example                  # OPENALEX_API_KEY=, CONTACT_EMAIL=
├── .gitignore                    # .env, data/raw/**, data/cache/**
├── config/
│   ├── institutions.yaml         # registry (§4) — single source of truth
│   ├── indian_inst_registry.csv  # Indian institution canonical names + sector/cluster (built in §5.10)
│   └── settings.yaml             # years, thresholds, budget caps
├── src/
│   ├── common/ (http.py, cache.py, logging.py, openalex.py, names.py, issn.py)
│   ├── collect/ (01_resolve_institutions.py … 12_export.py)
│   ├── stats/   (metrics.py, make_tables.py, make_figures.py, make_report.py)
│   └── dashboard/ (build_data.py, + web/ assets)
├── data/
│   ├── raw/        # untouched API responses (JSONL, gzip) — gitignored
│   ├── cache/      # per-request cache (hash of URL sans key) — gitignored
│   ├── interim/    # roster, matches, work/authorship/source tables (parquet + SQLite)
│   ├── external/   # scimago_*.csv, core_*.csv (downloaded, with SHA256 + date)
│   ├── review/     # manual-review queues (CSV) — humans resolve these
│   ├── final/      # group24_data.csv, group24_data_extended.csv, + deferred network files
│   └── MANIFEST.json   # collection date, API versions, counts, file hashes
├── stats/
│   ├── tables/     # every CSV behind every chart/number
│   ├── figures/    # PNG (300 dpi) + SVG
│   └── report/     # group24_stats_report.pptx (+ .pdf)
├── dashboard/      # self-contained static site (open index.html by double-click)
│   ├── index.html, css/, js/, vendor/, data/*.js
├── docs/
│   ├── DECISIONS.md   # every judgment call, with date + rationale
│   ├── DATA_DICTIONARY.md
│   ├── QA_REPORT.md   # generated by validation stage
│   └── LIMITATIONS.md
├── logs/
└── tests/
```

---

## 3. Environment, API access and budget (READ CAREFULLY — this changed in 2026)

**Facts verified from OpenAlex's own docs (Oct 2026):**
- Base URL `https://api.openalex.org`. A **free API key is effectively mandatory** (create an account at openalex.org → copy key from `openalex.org/settings/api`). Send as `?api_key=KEY` or `Authorization: Bearer KEY`. Without a key the budget is ~$0.10/day; with a free key **$1/day**.
- Usage-based pricing: singleton lookups (`/works/W123`) free; **list/filter calls ≈ $0.0001 each**; `search=` calls ≈ $0.001 each; PDF downloads $0.01. Limit: 100 requests/second max; HTTP **429** when over budget or rate.
- Check budget any time: `GET /rate-limit?api_key=KEY`. Daily budget resets at midnight UTC.
- `per_page` max **100**. `OR` values per filter max **100** (`a|b|c`). Basic paging cap 10,000 results → **always use cursor paging** (`cursor=*`, then `meta.next_cursor`) for anything big, and slice queries by year/institution.
- Use `select=` to fetch only needed fields (cheaper, faster).
- Default corpus = curated core. `corpus=all` adds the ~193M-work expansion corpus (`is_xpac` flag). **Default for us: core only**; run one comparison query with `corpus=all` per institution and log the delta in `docs/DECISIONS.md` (do not silently include expansion works).
- **Never filter by names; resolve to IDs first** (names are ambiguous).
- OpenAlex has an MCP server (`https://mcp.openalex.org/mcp`) — optional; plain HTTP via our own client is the canonical path for reproducibility.

**Implementation requirements for `src/common/http.py`:**
- Single `requests`/`httpx` session, `User-Agent` including `CONTACT_EMAIL`, timeout 30 s.
- Exponential backoff with jitter on 429/5xx (max 6 tries). On 429 with budget exhausted (check `/rate-limit`), **stop gracefully**, write a checkpoint, print "budget exhausted; resume after 00:00 UTC", exit code 75.
- Cache every GET by `sha256(url_without_api_key)`; cache hits cost nothing.
- Global concurrency ≤ 8; sleep to stay ≤ 20 req/s.
- A `BudgetTracker` that reads `/rate-limit` at start and every 500 calls; hard stop at a configurable `max_spend_usd_per_run` (default 0.80).
- **Budget estimate** (verify by measuring): ~15–25k papers across the three institutes → works pull ≈ 250 list calls (cents). The expensive parts are §5.11 (citing/cited resolution; est. $0.5–$2 total). Plan to spread it over 2–3 days or ask the owner (§13) to top up credits. Do not ask the owner to spend money without a measured estimate.

**Python stack** (pin versions): `httpx` or `requests`, `tenacity`, `pandas`, `pyarrow`, `duckdb` or `sqlite3`, `rapidfuzz`, `unidecode`, `beautifulsoup4`, `lxml`, `playwright` (only if a roster page needs JS), `pyyaml`, `python-dotenv`, `tqdm`, `numpy`, `scipy`, `matplotlib`, `plotly` (+`kaleido`), `python-pptx`, `pytest`. (Later, Task 4: `networkx`, `python-louvain`/`leidenalg`.)

---

## 4. Institution registry (`config/institutions.yaml`)

Seed values below came from ROR/website lookups. **Phase 1 step 1 must re-verify every ID against the live APIs** (`https://api.ror.org/v2/organizations/<ror>` and OpenAlex `/institutions?filter=ror:<ror>`) and abort if any name/location mismatch.

| Key | Display name (use in CSV `institution`) | ROR | Official site | Notes |
|---|---|---|---|---|
| `ncl` | CSIR-NCL | 057mn3690 | ncl.res.in, ncl-india.org | Pune; est. 1950; ROR record lists CSIR as parent; also hosts National Collection of Industrial Microorganisms (NCIM); library/IR at `library.ncl.res.in` (IR@NCL) |
| `iict` | CSIR-IICT | 040dky007 | iict.res.in, iictindia.org | Hyderabad (Tarnaka/Uppal Road); formerly Regional Research Laboratory (RRL-H) until 1 Apr 1989 |
| `cecri` | CSIR-CECRI | 01qek3q18 | cecri.res.in | Karaikudi, TN; extension centres Chennai & Mandapam; ROR acronym `CSIR-CECRI` |

For each institute, `institutions.yaml` must also hold:
- `openalex_institution_ids`: list (there may be **more than one OpenAlex entity** for the same ROR/organisation, e.g., name variants or CSIR-prefixed duplicates — find all via `GET /institutions?filter=ror:<ROR>` and `GET /institutions?search=<name variants>` then *only keep those whose `ror` matches or whose geography/name clearly matches*; log rejected candidates with reason).
- `name_variants` (for raw-affiliation recall, §5.4): e.g., NCL → "National Chemical Laboratory", "CSIR-NCL", "CSIR National Chemical Laboratory", "NCL Pune", "Dr. Homi Bhabha Road", "NCL Innovation Park"; IICT → "Indian Institute of Chemical Technology", "CSIR-IICT", "Regional Research Laboratory Hyderabad" (older), "Tarnaka", "Uppal Road"; CECRI → "Central Electrochemical Research Institute", "CSIR-CECRI", "Karaikudi".
- `confusable_entities_to_exclude` — **look-alikes that must NOT leak in**: Newcastle University ("NCL"), UK National Chemical Laboratory (historic), Institute of Chemical Technology Mumbai (ICT), **CSIR-Indian Institute of Chemical Biology (IICB, Kolkata)**, CSIR-CSMCRI (Bhavnagar), CSIR-CLRI, CSIR-CFTRI (that's Group 25), CSIR-NIIST/NML (Group 25), CSIR-NPL/CSIO/CGCRI (Group 26). Our rows must only carry our three institutes' affiliation IDs.
- `roster_urls` (see §5.2) and `department_list` (scraped, not assumed).
- `cluster: "CSIR"` and `sector`-style tags used later for cross-cluster flags.

---

## 5. PHASE 1 — DATA COLLECTION (Task 1)

Goal: a trustworthy, well-documented paper×author table for CSIR-NCL, CSIR-IICT, CSIR-CECRI, 2016–2026, plus an *interim relational store* used by stats, dashboard, and later networks.

### 5.0 Data-source strategy (why each source, what it provides)

| Need | Primary source | Fallback / cross-check |
|---|---|---|
| Papers, DOIs, citations, authorships, affiliations, topics, referenced_works | **OpenAlex** `/works` (filter by institution ID) | Crossref (DOI sanity), Scopus (only if the group has institutional access), IRINS if the lab has an instance |
| Faculty roster + department | **Official institute websites** (scientific-staff directories, division pages) | IRINS/VIDWAN profiles (`vidwan.inflibnet.ac.in`), annual reports, CSIR directory pages |
| Author-level h-index, works_count, ORCID | **OpenAlex `/authors`** (`summary_stats.h_index`) | Computed in-corpus h-index (we also compute this ourselves) |
| Journal ISSN / source type | OpenAlex `/sources` | Crossref journal API |
| Journal quartile Q1–Q4 | **SCImago Journal Rank (SJR) yearly files** (free; Scopus-derived) | JCR is paywalled — do **not** scrape it; only use if a group member can legitimately export it (record as separate column) |
| Conference rank | **CORE portal** rankings (A*/A/B/C) | none |
| Indian institution identification | OpenAlex `institutions.country_code == "IN"` + ROR | Our curated `indian_inst_registry.csv` |
| Research area | OpenAlex `primary_topic` → `subfield` → `field` → `domain` | — |
| Validation | Institute publication pages (e.g., IICT's `iict.res.in/ALL_PUBLICATIONS` lists papers by year, 2011–2024 at time of research), IR@NCL, annual reports, SCImago SIR output counts, IRINS counts | Random DOI spot-checks via Crossref |

Notes:
- **IRINS** (INFLIBNET) is per-institution (`<inst>.irins.org`) and only covers institutions that adopted it. Probe `ncl`, `iict`, `cecri` instances (and VIDWAN); if present, use as a *cross-check* of faculty lists/publication counts, not as primary. If absent, document and move on.
- **Scopus** requires an Elsevier API key (institutional entitlement). Treat as optional; never block on it.
- **CORE** is a *computer-science* conference-rank list. Chemistry/electrochemistry/materials conference papers will mostly be unranked → the CORE panel will be sparse or empty. That is expected: implement a graceful "Not applicable — N conference papers, M with a CORE rank" state. Do not fabricate ranks.

### 5.1 Step 01 — Resolve and verify institutions
1. Read `config/institutions.yaml`. For each ROR: call ROR v2 API; assert name, country=IN, city match; save JSON to `data/raw/ror/`.
2. For each ROR: `GET /institutions?filter=ror:https://ror.org/<id>` → collect OpenAlex institution IDs, `display_name`, `country_code`, `lineage`, `works_count`, `counts_by_year`. Also search by name variants and list *all* plausible entities; mark each `accept`/`reject` with reason in `data/review/institution_candidates.csv`.
3. Sanity: `GET /works?filter=authorships.institutions.id:<ID>,publication_year:2016-2026&group_by=publication_year` → yearly counts per institute; save as `data/interim/openalex_yearly_counts.csv`. These become the **reference totals** for recall checks (§5.13).
4. Also record the CSIR **parent** entity ID. Some works are affiliated only to the parent "Council of Scientific and Industrial Research" because the affiliation string was generic (e.g., "CSIR, Pune") — used in §5.4.

### 5.2 Step 02 — Faculty roster from official websites (the "faculty list")
**Definition we adopt (document in DECISIONS.md):** *Faculty* = scientific cadre staff: Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist (+ Director, Emeritus/Distinguished scientists if listed, flagged). Technical/administrative/auxiliary staff are excluded. Ph.D. students, JRF/SRF, Research Associates, project staff, visiting scholars are **not faculty** (they still appear as authors — see §5.6).

Scrape each institute's staff pages (respect `robots.txt`, throttle ≥1 s, identify with a descriptive User-Agent, cache HTML in `data/raw/roster/<inst>/<date>/`):
- **IICT**: `iict.res.in` → People → *Scientific Staff* (e.g. `/SCIENTIFIC_STAFF`), also `DEPT_SEARCH` / `DESIGNATION_SEARCH` pages. Observed designations: Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist. Observed R&D departments (re-verify): Analytical & Structural Chemistry; Applied Biology; Catalysis & Fine Chemicals; Energy & Environmental Engineering; Fluoro-Agrochemicals; Oils, Lipid Science & Technology; Natural Products & Medicinal Chemistry; Organic Synthesis & Process Chemistry; Chemical Engineering & Process Technology; Polymers & Functional Materials.
- **NCL**: `ncl.res.in` (also `ncl-india.org`) → People / Scientists / Divisions. Divisions to expect (verify live): Organic Chemistry; Physical & Materials Chemistry; Polymer Science & Engineering; Catalysis & Inorganic Chemistry; Chemical Engineering & Process Development; Biochemical Sciences; plus support/facility units (e.g., Central NMR Facility, NCIM). NCL's library site (`library.ncl.res.in`) lists thesis-by-division and can help map division names.
- **CECRI**: `cecri.res.in` → staff/telephone directory/people pages (a staff telephone directory download exists on the contact page) and division/research-area pages. Known focus areas (use to sanity-check division names): corrosion science & engineering, electrochemical materials science, functional materials & nanoscale electrochemistry, electrochemical power sources, electrochemical pollution control, electrodics & electrocatalysis, electrometallurgy, industrial metal finishing, computer networking & instrumentation.
- If a page needs JavaScript, use `playwright`. If a page is a PDF/DOC (directories), parse it. If a site blocks scraping or is unreachable, record in `LIMITATIONS.md` and fall back to IRINS/VIDWAN/annual-report lists, else fall back to the "probable faculty" heuristic (§5.7).

Output `data/interim/roster.parquet` + CSV with columns:
`inst_key, full_name, name_norm, designation, department, email_domain_only(optional), profile_url, scraped_at, source_url, status` (`current`). Keep raw name strings (with titles like "Dr.", "Sri", "Smt") and a cleaned version (strip titles/punctuation, `unidecode`, collapse initials). Expect roughly low-hundreds of scientists per lab (NCL and IICT larger than CECRI) — if your counts are wildly different, investigate before proceeding.

### 5.3 Step 03 — Pull all works per institute (OpenAlex)
For each institute and each publication year 2016…2026 (slice by year to stay well under limits):
```
GET /works?filter=authorships.institutions.id:<ID1>|<ID2>,publication_year:<Y>
          &select=<fields below>&per_page=100&cursor=*&api_key=…
```
Required `select` fields: `id, doi, title, display_name, publication_year, publication_date, type, language, is_retracted, is_paratext, cited_by_count, counts_by_year, authorships, primary_location, best_oa_location, biblio, primary_topic, topics, referenced_works, referenced_works_count, ids`. (Confirm exact field names against the live Work object; field availability changed across versions. `authorships` should carry per-author `author.id/display_name/orcid`, `institutions[]` with `id/display_name/ror/country_code/type`, `raw_affiliation_strings`, `countries`, `author_position`, `is_corresponding`.)
- Save raw pages to `data/raw/openalex/works/<inst>/<year>/page_NNNN.jsonl.gz` and write `data/raw/openalex/works/manifest.json` (query, count reported by `meta.count`, count fetched, timestamp).
- **Assert** fetched == `meta.count` for each slice; otherwise re-run that slice.
- Include 2026 up to the collection date; mark `is_partial_year=true` for 2026 in the interim store.
- Run once per institute with `corpus=all` into a *separate* raw folder and log counts to compare with core (don't merge).

### 5.4 Step 04 — Recall booster (find papers OpenAlex mis-tagged)
OpenAlex affiliation matching on Indian government labs is imperfect. Do **all** of the following, each producing candidate works kept in `data/interim/recall_candidates.parquet`, which are **added to the corpus only if validated**:
1. **Parent-entity works**: works whose authorship carries the CSIR parent entity but whose `raw_affiliation_strings` contain one of our `name_variants` for that institute (regex, case-insensitive, accent-folded) and which are not already captured.
2. **Raw-string search** (verify the exact filter name in docs, e.g. `raw_affiliation_strings.search` / `authorships.raw_affiliation_strings.search`): query each distinctive variant with `publication_year:2016-2026`, page via cursor. Keep a hit only if (a) the matching string actually names our institute, (b) it doesn't match any `confusable_entities_to_exclude`, and (c) the authorship has no conflicting different-institute ID for that same string.
3. **AcSIR dual affiliations**: many CSIR doctoral students list both CSIR-lab and "Academy of Scientific and Innovative Research (AcSIR)". Ensure those papers are captured when the lab string is present even if only AcSIR was tagged.
4. **Roster-driven recall**: for every roster-matched OpenAlex author (§5.7), pull *their* works 2016–2026 (`authorships.author.id:<A…>`) and keep works where the authorship-level affiliation (ID or raw string) indicates our institute **during that period**. Authors moving between institutes must not drag in papers from a different institution.
5. **Reporting**: write `docs/QA_REPORT.md` section "Recall": per institute, #works from ID filter, #added by each booster, #rejected with top rejection reasons. Rule of thumb: if boosters add >15% to any institute, revisit step 03 filters and investigate before finalising.

### 5.5 Step 05 — Work-level filtering and typing
Include works where:
- `publication_year` 2016–2026; not `is_retracted` unless flagged (keep retracted in the data with a flag in the extended file; exclude from statistics? **Decision: keep, flag, and exclude from headline stats only if retracted — document**); not paratext.
- Type rule — primary dataset keeps **peer-reviewed research outputs**: OpenAlex `type` in {`article`, `review`, `letter`, and conference papers (`article` with source type `conference`, or `proceedings-article`-like types per live vocabulary)}. Excluded types (editorial, erratum, paratext, dataset, preprint-only, book chapters, dissertations, grants, etc.) go to `data/interim/excluded_works.csv` with reason and are summarised in QA. Re-check the live `/data/work-types` vocabulary.
- `type` column in CSV: `conference` if `primary_location.source.type == "conference"` (or the work type indicates proceedings); otherwise `journal` if source type is `journal`. Works whose primary source is a repository/ebook platform/other: try the first location whose source type is `journal`/`conference`; if none, exclude (log).
- **Deduplicate**: one `work_id` once; merge records sharing the same DOI (lowercased) — keep the one with higher `cited_by_count` and the journal-published version over the preprint.
- DOI normalisation: lowercase, strip `https://doi.org/`, re-prefix with `https://doi.org/`; validate with regex `^10\.\d{4,9}/\S+$`. Keep works without DOI (blank in CSV) but give them a stable `work_id` in the extended file.

### 5.6 Step 06 — Authorship explosion and institution attribution
For each work, for each authorship:
- Attribute the authorship to our institute X if any of its `institutions[]` IDs ∈ X's accepted IDs, **or** a validated raw-string match from §5.4.
- A single authorship may map to **more than one** of our institutes (rare joint appointments) → produce one row per institute and flag `multi_inst_authorship=true`.
- Authors not attributed to any of our institutes are *co-authors* (feed §5.10), not CSV rows.
- Row author name: use OpenAlex `author.display_name`, but **harmonise to a canonical name per author ID** (most frequent display name; if matched to roster use the roster's cleaned full name). Save alias lists in `data/interim/author_aliases.parquet`.
- Mark each row's `author_role`: `faculty` (roster-matched) | `probable_former_faculty` (§5.7) | `affiliated_author` (students, project staff, others).

### 5.7 Step 07 — Match roster ↔ OpenAlex authors, h-index, disambiguation
1. For each roster scientist, find candidate OpenAlex author IDs **among authors actually seen in our corpus** (not by global name search — that's how wrong people get matched): normalise names → exact match → fuzzy (`rapidfuzz`, token-set ratio ≥ 92 AND initials-consistent) → manual-review queue for 85–92 or multiple candidates. Handle Indian-name pitfalls: initials-first vs surname-first, single-name persons, "Kumar/Singh/Rao" collisions, transliteration variants, "Dr./Prof./Sri/Smt" prefixes, middle-name initials.
2. Resolve ambiguity with evidence: shared co-authors, same department-consistent topics, ORCID, institutional-affiliation timeline. A match needs ≥2 pieces of evidence beyond name when the name is common.
3. **Split/merged profiles**: OpenAlex sometimes splits one person into several author IDs or merges two people. For every roster scientist, allow a **set** of author IDs (`author_ids`), union their works, and flag suspicious profiles (e.g., profile `works_count` hugely above in-corpus count with topics unrelated to chemistry) in `data/review/author_merge_review.csv`.
4. Fetch each matched author entity (`/authors/<id>`, free singleton calls): `display_name, orcid, works_count, cited_by_count, summary_stats.h_index, summary_stats.i10_index, last_known_institutions`. Store as `h_index_openalex` (career-wide).
5. Also compute **in-corpus h-index** (`h_index_corpus`): h such that h papers (2016–2026, deduped, in our corpus) have ≥h citations. Keep both; document that they differ (career vs 2016–2026 window).
6. **Probable former faculty** (not on today's roster, but clearly senior staff earlier in the window): authors with ≥10 papers across ≥3 distinct years attributed to the institute and not roster-matched, excluding first-author-only student patterns (high share of `author_position=first` and ≤5-year active span) → flag `probable_former_faculty`; put in a review queue; the human decides.
7. Produce `data/interim/faculty_master.parquet`: `inst_key, faculty_id (internal), full_name, designation, department, author_ids[], orcid, h_index_openalex, h_index_corpus, n_papers_corpus, n_citations_corpus, match_confidence, match_evidence`.
8. Quality bar: ≥90% of roster scientists **who have ≥1 paper in the window** matched with high confidence; report the unmatched list.

### 5.8 Step 08 — Journals: ISSN and quartile
1. Collect distinct `source` IDs; batch-fetch `/sources` (`filter=openalex_id:S1|S2|...`, 100 at a time): `display_name, issn_l, issn[], type, host_organization_name, is_in_doaj, is_core`.
2. Download **SCImago Journal Rank** yearly CSVs (free, `https://www.scimagojr.com/journalrank.php?year=<Y>&type=j&out=xls`; semicolon-separated; contains `Sourceid, Title, Type, Issn, SJR, SJR Best Quartile, H index, ... Categories, Areas`). Store in `data/external/scimago_<year>.csv` with SHA256 and download date in `MANIFEST.json`. If the site blocks automated downloads, use the community mirror of the full panel (`Michael-E-Rose/SCImagoJournalRankIndicators`, `all.csv`, on GitHub) and **record that substitution**; if neither works, escalate (§13).
3. **Join rule (document as "quartile policy")**:
   - Normalise ISSNs (SJR lists ISSNs *without hyphen*, comma-separated; OpenAlex uses hyphens). Match on any ISSN of the OpenAlex source ∩ any ISSN of the SJR record.
   - Quartile = SJR **best quartile for the paper's publication year**. For 2026 papers (no 2026 SJR yet — SJR updates in June for the previous year) use the latest available year (2025) and flag `quartile_year_used`.
   - If the journal is missing that year but present in neighbouring years, use the nearest year within ±2 and flag.
   - Fallback: exact normalised-title match (lowercase, strip punctuation/"the"/"&"→"and") only if unique; flag `quartile_match_method` ∈ {`issn`,`title`,`nearest_year`,`none`}.
   - Unmatched → blank `quartile`; dashboard shows "Unranked / not in SJR".
   - Be explicit in the report: *SJR "best quartile" is across all subject categories of the journal and is Scopus-based; JCR quartiles may differ.* (Optional extension: SJR also gives per-category quartiles; if time permits add `quartile_in_primary_category` in the extended file.)
4. **Conferences**: CORE rankings from `portal.core.edu.au/conf-ranks/` (export CSV if available; record edition, e.g., ICORE20xx, and download date). Match by normalised conference name/acronym with conservative fuzzy matching; exact/unique matches only; otherwise blank. Output `quartile` as `CORE A*`/`CORE A`/`CORE B`/`CORE C`.
5. Save `data/interim/source_table.parquet`.

### 5.9 Step 09 — Citations
- `citations` = `cited_by_count` from the works pull. Record the collection timestamp (`MANIFEST.json: collected_at`). Citation counts drift daily; never mix pulls from different dates for the same paper (if re-pulling, re-pull all).
- Also store `counts_by_year` (citations per year) for later year-wise citation-flow charts.
- Do **not** compute or substitute our own citation counts for the CSV column.

### 5.10 Step 10 — `coauthor_institutes` and the Indian institution registry
1. Build `config/indian_inst_registry.csv` from all institution entities seen in our corpus with `country_code=="IN"`: `openalex_id, ror, canonical_name, short_name, city, type (education/government/facility/…), sector_cluster` (derive using ROR types + name rules: `IIT`, `NIT`, `IIIT`, `IISER`, `CentralUniv`, `StateUniv`, `CSIR`, `DAE`, `ICAR`, `ICMR`, `DRDO`, `ISRO`, `Private`, `Other`). Merge duplicates via ROR; hand-review the top 100 by frequency (`data/review/inst_registry_review.csv`). This registry is what makes the cross-cluster flags (IIT↔CSIR etc.) possible later.
2. **Our definition of `coauthor_institutes` (main CSV)**: for the row's paper, the semicolon-separated, alphabetically sorted, de-duplicated **canonical names of Indian institutions of all co-authors, excluding the row's own institute** (but *including* our other two institutes if they co-authored). International and unidentifiable affiliations are excluded from the main column. In `group24_data_extended.csv` add `coauthor_institutes_all` (all countries) and `coauthor_countries`. *(If the instructor prefers all-country lists, swap — see §13.)*
3. Co-author institutions come from the authorships' `institutions[]` (IDs → registry canonical names). Authors without any institution ID contribute nothing (don't guess from free text, except validated name-variant matches for our own institutes).
4. Use `;` as separator with no surrounding spaces inside the value; names must not contain `;` (replace with `,`).

### 5.11 Step 11 — `cites_indian_inst` and `cited_by_indian_inst`
**Definitions (document verbatim in DATA_DICTIONARY.md):** For a row for institute X and paper P:
- `cites_indian_inst = TRUE` iff P's reference list contains ≥1 paper that has ≥1 authorship affiliated with an **Indian institution other than X** (country code IN). Self-citation to X's own papers does not count; citing a paper from our other two institutes **does** count.
- `cited_by_indian_inst = TRUE` iff ≥1 paper that cites P has ≥1 authorship affiliated with an Indian institution other than X.
- Values `TRUE`/`FALSE` only (uppercase). If metadata is missing for *all* references (OpenAlex has no references for the work) set `FALSE` and set `cites_data_status=no_references` in the extended file — never leave blank in the main file.

**Efficient algorithm (do not call per-paper endpoints in a loop):**
1. *Outgoing (cites):* `referenced_works` IDs are already in the works pull. Build the set of unique referenced work IDs; batch-resolve their authorship institutions with `GET /works?filter=openalex_id:W1|…|W100&select=id,authorships.institutions&per_page=100` (100 per call). Cache everything (parquet `referenced_work_institutions`). Typical volume: ~10⁵–10⁶ unique IDs → ~10³–10⁴ calls; measure on the first institute and extrapolate before running the rest; use the budget tracker; resume across days.
   - Optimisation: IDs already in our corpus need no lookup.
2. *Incoming (cited by):* for batches of up to 100 of our work IDs: `GET /works?filter=cites:W1|…|W100,authorships.countries:IN&select=id,publication_year,referenced_works,authorships.institutions&per_page=100&cursor=*`. (Verify filter names `cites` and `authorships.countries` or `authorships.institutions.country_code` in the live docs.) For each citing work, intersect its `referenced_works` with our batch to attribute edges `(citing → our paper)`. Persist **all** edges (`data/interim/citation_edges_raw.parquet`: `citing_id, cited_id, citing_year, citing_inst_ids[], citing_inst_country[]`) — this is the seed for Task 4.
   - A batch must be paged to completion (cursor until null). If any batch is incomplete, mark papers in it `cited_by_data_status=incomplete` and retry.
3. Compute flags per (paper, institute) applying the "Indian institution other than X" rule using the registry.
4. Sanity checks: (a) fraction of papers with `cites_indian_inst=TRUE` should be plausible (expect a clear majority for chemistry labs; if <20% or ~100% investigate); (b) count of incoming edges per paper ≤ `cited_by_count` (OpenAlex), and for papers with large `cited_by_count` the Indian-filtered count is smaller.

### 5.12 Step 12 — Research area fields
From each work's `primary_topic`: `topic_id/name`, `subfield`, `field`, `domain`. Store also the top-3 `topics` (with scores) in the extended file. Dashboard/report "research area" uses **field** (primary) with **subfield** drill-down. Expect Chemistry, Materials Science, Chemical Engineering, Biochemistry/Genetics & Molecular Biology, Energy, Environmental Science, Pharmacology etc. Works without a topic → "Unclassified" (report share).

### 5.13 Step 13 — Validation & QA (hard gate; produce `docs/QA_REPORT.md`)
Automated checks (fail the pipeline on any ✗):
- Schema: exact 14 columns/order in main CSV; no extra columns; UTF-8 (with BOM-free), `\n` newlines, RFC-4180 quoting; no embedded raw newlines in fields.
- Domain checks: `group==24`; `institution` ∈ 3 allowed values; `year` ∈ [2016,2026]; `type` ∈ {journal, conference}; `citations` int ≥0; `quartile` ∈ allowed set or blank; `issn` regex or blank (and blank for conferences); `doi` regex or blank; booleans uppercase; `coauthor_institutes` no leading/trailing `;`.
- Uniqueness: no duplicate (`institution`, `doi`/`work_id`, canonical author) rows.
- Consistency: every paper appears under ≥1 of our institutes; per-paper `citations` identical across its rows.
- Coverage: per institute × year counts vs OpenAlex `group_by` reference totals (§5.1) → explain every deviation >5% (due to type filters etc.).
- Completeness rates (report, don't hide): % papers with DOI, ISSN, quartile, topic; % authors with institution IDs; % roster scientists matched.
Manual/semi-automated validation (log results):
- **Random spot-check**: 30 random DOIs per institute checked against Crossref (title, year, journal) → match rate ≥ 98%.
- **Cross-check totals** against independent sources where available: IICT's own publication listing by year, IR@NCL / annual reports, SCImago SIR or institutional counts, IRINS/Scopus if accessible. Large discrepancies are expected (different scope) — report ratios, don't "fix" data to match.
- **Eyeball top-20 most-cited and top-20 most-prolific authors** per institute for plausibility (e.g., a "faculty" with 400 papers/yr is a merged profile).
- **Wrong-institution leakage test**: sample 50 papers per institute where the only evidence is a raw-string match; verify by reading affiliation strings.
- Review queues in `data/review/` must be either resolved or explicitly marked "accepted as-is" with a count in QA_REPORT.

### 5.14 Step 14 — Export
Write to `data/final/`:
- `group24_data.csv` — 14 required columns exactly.
- `group24_data_extended.csv` — same rows/order **plus**: `work_id, author_openalex_id, faculty_id, author_role, department, designation, is_corresponding, author_position, h_index_openalex, h_index_corpus, source_id, source_type, issn_l, quartile_year_used, quartile_match_method, field, subfield, domain, primary_topic, topics_top3, coauthor_institutes_all, coauthor_countries, n_authors, is_open_access, is_retracted, is_partial_year, multi_inst_authorship, cites_data_status, cited_by_data_status, collected_at`.
- `faculty_master.csv`, `works_table.parquet`, `authorships_table.parquet`, `sources_table.parquet`, `citation_edges_raw.parquet` (seed for Task 4), `interim SQLite/duckdb db`.
- `data/MANIFEST.json`: collection date, OpenAlex corpus mode, query manifests, counts per stage, file SHA256s, package versions, git commit.
- `docs/DATA_DICTIONARY.md` (every column: definition, source, derivation, known limitations) and `docs/LIMITATIONS.md`.

**Phase 1 exit criteria:** all QA gates green; `make collect` re-runs from cache with zero API spend; row counts per institute and year printed in QA_REPORT.

---

## 6. PHASE 2 — STATISTICS (Task 2)

Input: `data/interim` tables (preferred) or the final CSV. All numbers computed in `src/stats/metrics.py`, written as CSVs into `stats/tables/`, then consumed by figures, the report, **and** the dashboard (so all three always agree).

### 6.1 Units and levels
- **Paper level** = distinct `work_id` (never count author rows as papers).
- **Institution level**: papers with ≥1 attributed authorship at X (whole counting). A paper co-authored across two of our institutes counts once for each in the institutional views, and **once** in the "Group 24 combined" view (state this in every combined table's footnote).
- **Department level**: papers where ≥1 roster faculty member of department D is an author (department from website roster). Papers can count in several departments. Authors with no known department are excluded from department stats ("Unassigned" reported separately).
- **Faculty level**: papers where the faculty member is an author (using `author_ids` union).
- Years: calendar `publication_year`; always show 2026 as "2026 (partial, to 13 Oct)" — set the date to the actual collection date; never compare 2026 to full years without that note, and add an annualised-run-rate line only as a clearly labelled estimate (optional).

### 6.2 Required metrics (exact definitions)
| Metric | Definition / procedure |
|---|---|
| **Publication trend** | `n_papers[inst, year]`, totals, CAGR 2016→2025 (exclude partial 2026), YoY %, journal vs conference split |
| **Q1 fraction** | `Q1 papers / journal papers with known quartile` (**primary**); also report `Q1 / all journal papers` and the coverage `% with known quartile`. Per institute, per year, combined. Also full Q1–Q4 + Unranked distribution |
| **Citations** | total, mean, median, max, % uncited, field-normalisation **not** claimed (say so); citations per paper by year of publication (older papers have had longer to accrue). Use `cited_by_count` at collection date |
| **h-index distribution** | across *roster faculty with ≥1 paper in the window*; show both `h_index_openalex` (career) and `h_index_corpus` (2016–2026); histogram bins of width 5 (adjustable), plus mean/median/quartiles/max; list faculty with missing h-index |
| **Top 5 journals** | by distinct-paper count per institute (tie → higher total citations); include share %, quartile, ISSN |
| **Top 10 most-cited papers** | by `cited_by_count` per institute (+combined): title, journal, year, citations, DOI, institute(s), the in-corpus authors |
| **Research areas** | paper share by OpenAlex `field` (primary_topic) per institute; subfield drill-down; domain-level summary; "Unclassified" share |
| **Faculty performance** | per faculty: papers, citations (sum over distinct papers), mean citations/paper, Q1 papers, Q1 %, top journal (mode), h-index (both), first/corresponding-author counts, active years, department |
| **Department performance** | per department: faculty count (roster), papers, citations, Q1 %, mean h-index, top field |
| **Conference rank** | counts by CORE A*/A/B/C/unranked among conference papers; if N is tiny, say "n = X" and avoid percentages |
| **Indian-connection preview (optional, low priority)** | % papers with ≥1 Indian co-author institute; top 10 Indian partner institutes by shared papers (from `coauthor_institutes`); % `cites_indian_inst`, % `cited_by_indian_inst`. Label as raw-data preview — full analysis belongs to Task 4 |

Handle ties, missing data, and small samples explicitly; never silently drop rows — report N for every statistic.

### 6.3 Data-quality & limitation disclosures (must appear in the report, brief)
OpenAlex author disambiguation and affiliation errors; SJR best-quartile vs JCR; 2026 partial year and 2026 quartile fallback; career vs window h-index; faculty = current roster (former staff only flagged); CORE list is CS-centric; citation counts as of collection date; non-faculty authors (students/project staff) are *not* in faculty statistics.

### 6.4 Figures (matplotlib/plotly → PNG 300 dpi + SVG; colour-blind-safe palette; consistent institute colours across report and dashboard)
Publication trend (grouped bars + line for total), Q1–Q4 stacked bars per institute (100% and absolute), h-index histogram (small multiples per institute), top-journals horizontal bars, research-area treemap or horizontal bars, citations-per-paper-by-year, faculty scatter (papers vs citations, size=h-index), department bar chart. Every figure has a title with N, axis units, source note ("OpenAlex, collected <date>; quartiles: SJR <years>").

### 6.5 Report (≤10 slides — hard limit; build with `python-pptx`, export PDF if LibreOffice is available)
| Slide | Content |
|---|---|
| 1 | Title, group 24, three institutes, data scope (2016–Oct 2026), sources, collection date |
| 2 | Data coverage & quality (counts, completeness, method, limitations in 4 bullets) |
| 3 | Publication trend 2016–2026 (all three + combined) with 3 key takeaways |
| 4 | Journal quartiles: Q1 fraction per institute (+ unranked share) |
| 5 | Faculty: h-index distributions + top faculty table |
| 6 | Top 5 journals per institute |
| 7 | Top 10 most-cited papers (compact table; combined or per institute with small font — keep legible ≥10 pt) |
| 8 | Research-area & department breakdown |
| 9 | **[Reserved — Task 4]** Citation-network summary (PageRank top-10, in-degree distribution, cross-institute flow). For now: placeholder slide with "to be completed", **or** the Indian-connection preview |
| 10 | **[Reserved — Task 4]** Authorship-network summary (degree/betweenness, communities); for now: key conclusions & next steps |

Rules: every claim backed by a number; takeaways phrased as observations, not speculation; no unreferenced superlatives; consistent colours; speaker notes list the source table file for each chart. The same facts must match the dashboard exactly (automated test `tests/test_consistency.py` compares report tables ↔ dashboard JSON).

**Phase 2 exit criteria:** all CSVs in `stats/tables/`; figures generated; report ≤10 slides rendered and visually checked (convert to images and inspect for overflow/overlap); consistency test passes.

---

## 7. PHASE 3 — INTERACTIVE DASHBOARD (Task 3)

### 7.1 Architecture and constraints
- **Static, self-contained site** in `dashboard/` — no backend, no CDN dependencies at runtime (vendor all JS/CSS into `dashboard/vendor/`) so it works offline and can be shown in class by double-clicking `index.html`. Also deployable to GitHub Pages.
- **Opening via `file://`** blocks `fetch()` of local JSON in most browsers → the build step emits data as JS files (`window.G24_DATA = {...}`) loaded with `<script>` tags, not as `.json` fetches. Keep total payload ≲ 15 MB (pre-aggregate; don't ship the full authorship table unless needed). If the table is large, ship paper-level data compressed in a compact columnar format and lazy-load per institute.
- Libraries (vendored): **Apache ECharts 5** (charts), **Tabulator** (sortable/filterable/virtual tables) — or Plotly.js + DataTables if preferred; plain ES modules/vanilla JS (no build tools required to *run*). Reserve **Cytoscape.js** slot for Task 4.
- `src/dashboard/build_data.py` reads `stats/tables/*` (never recomputes metrics differently) and writes `dashboard/data/*.js`. `make dashboard` rebuilds everything deterministically.

### 7.2 Layout and UX
- Header: project title, group 24, collection date, data-source note, "2026 is partial" badge.
- **Institution selector**: tabs/segmented control — `CSIR-NCL | CSIR-IICT | CSIR-CECRI | All three (combined, distinct papers) | Compare`. Every panel respects the selection. "Compare" shows the three side by side for trend, Q1 share, h-index medians.
- Global filters (apply to all panels): year range slider (2016–2026), type (journal/conference), quartile, department, research field. Show active-filter chips and a Reset button. Filters must update KPIs, charts, and tables consistently, with counts of papers shown.
- KPI strip: papers, journal papers, Q1 %, total citations, mean citations/paper, faculty count (with ≥1 paper), median h-index.
- Responsive (≥1024 px primary; usable on tablet/phone), keyboard-accessible, high-contrast palette, colour-blind safe, ARIA labels on charts, tooltips with exact numbers, dark/light theme optional. Loading states and "no data for selection" states everywhere. Downloadable CSV for each table and PNG for each chart (ECharts `saveAsImage`).

### 7.3 Panels (map 1:1 to the assignment; all must exist)
| # | Panel | Specification |
|---|---|---|
| 1 | Publication trend | Bar (papers/yr) + optional line (cumulative or citations); 2016–2026; 2026 hatched/labelled partial; per-institute series in Compare mode; tooltip with journal/conference split |
| 2 | Faculty list | Searchable table: name, designation, **department**, h-index (toggle career/2016–26 window), total papers (2016–26), link to profile if public; chip for `probable former` (toggle to include) |
| 3 | Journal quartile distribution | Stacked bar by year **and** a pie/donut for the selection; include "Unranked" category visibly; tooltip shows counts and %; footnote on SJR method |
| 4 | Faculty performance table | Sortable/filterable: papers, citations, mean cit./paper, Q1 papers, Q1 %, top journal, h-index, department; sticky header; column visibility toggle; row click → faculty drawer with their yearly trend, top 5 papers, top journals |
| 5 | Top journals | Top 5 horizontal bars (with option to expand to top 15), paper count, quartile badge, ISSN |
| 6 | h-index distribution | Histogram of faculty h-index; switch career vs window; marker lines for mean/median; bin-width control |
| 7 | Research area breakdown | Donut/treemap by field; click a field → subfield breakdown and filters other panels; "Unclassified" shown |
| 8 | Most-cited papers | Top 10 table: title, journal, year, citations, DOI (clickable link), institute, quartile; selection-aware |
| 9 | Conference rank | CORE A*/A/B/C/unranked chart with N; when N is small or zero show an explanatory empty state ("conference output is minimal for chemistry labs; CORE ranks CS venues") — never blank/broken |
| 10 | Citation network | **Placeholder tab** "Task 4 — pending", already styled, with the data hook (`G24_DATA.network.citation`) and layout area sized for a Cytoscape.js canvas |
| 11 | Authorship network | **Placeholder tab**, same |
| + | Department explorer | Bar/table of departments (papers, citations, Q1 %, faculty) with drill into faculty |
| + | Indian connections preview (optional) | Top Indian partner institutes (from `coauthor_institutes`), % cites/cited-by Indian — clearly labelled preview |
| + | Data & methods | Definitions, sources, collection date, limitations, links to downloadable CSVs |

### 7.4 Data contract (`dashboard/data/`)
Pre-aggregated, keyed by `inst` ∈ {`ncl`,`iict`,`cecri`,`all`}:
`meta` (collection date, partial-year note, counts), `trend[year]`, `quartile[year][Q1..Q4,Unranked]`, `journals_top[]`, `faculty[]` (id, name, dept, designation, h_career, h_window, papers, citations, q1, topJournal, years[]), `hist_h[]`, `fields[]`, `subfields[]`, `top_cited[]`, `conference_rank{}`, `papers[]` (compact paper-level rows to support client-side filtering: id, inst bitmask, year, type, quartile, field, dept bitmask, citations, journalId, doi), `journals{}` lookup, `network` (empty stubs). Version-stamp the payload and print it in the footer.
The client-side filters recompute aggregates from `papers[]` (so filters genuinely work) — pre-aggregated tables are used for the unfiltered default view and for **testing equality** with the report.

### 7.5 Quality gates for the dashboard
- Automated: `tests/test_dashboard_data.py` (schema, no NaN/undefined, totals equal report tables); headless-browser smoke test (Playwright): loads `index.html` from `file://`, switches each institution, applies a filter, asserts panel DOM/chart instances exist and no console errors.
- Visual check: take screenshots of each tab/state (desktop + 1024 px + mobile) and inspect for clipping, overlapping labels, unreadable tick labels, empty charts.
- Performance: first paint < 3 s on a laptop; filter updates < 300 ms.
- Accuracy: pick 10 random numbers on the dashboard and verify against the CSV by hand (script prints them).
- Accessibility pass (contrast, keyboard focus, alt/aria text).
- README explains: how to open, how to rebuild, how to deploy to GitHub Pages, data refresh procedure.

**Phase 3 exit criteria:** all 11 panels present (9 live + 2 clearly-labelled placeholders), filters work, tests pass, offline-capable, README written.

---

## 8. Execution order and checkpoints

1. `make setup` (venv, deps, `.env` check, registry verification).
2. Phase 1 steps 01→14 (stop at each step's assertion on failure).
3. **Checkpoint A (human):** review `QA_REPORT.md`, `data/review/*` queues, `DECISIONS.md` (see §13).
4. Phase 2 (`make stats`) → **Checkpoint B (human):** review figures/tables and the report draft.
5. Phase 3 (`make dashboard`) → **Checkpoint C (human):** demo walkthrough.
6. Final packaging: `final_submission/` containing `group24_data.csv`, (network files when Task 4 done), report PDF/PPTX, dashboard folder zipped. Do not include `.env`, raw caches, or API keys.

At the end of each phase, append a dated entry to `docs/DECISIONS.md` and update `MANIFEST.json`.

---

## 9. Deferred Task 4 — what to preserve now so it is cheap later
- `citation_edges_raw.parquet` (outgoing edges from `referenced_works` among all works; incoming edges from citing-work pulls) with source/target work IDs, DOIs, institution IDs, years.
- Authorship tables with author IDs, institution IDs/countries, positions — enough to derive `authorship_network.csv` (`author_a, author_b, paper_doi, inst_a, inst_b, year`).
- `indian_inst_registry.csv` with sector/cluster tags (needed for the cross-cluster flags IIT↔CSIR etc.).
- Topic assignments per paper (for Jaccard similarity of research topics).
- Dashboard placeholders and `network` data stubs; report slides 9–10 reserved.
- Required later files (spec): `citation_network.csv` (source_doi, target_doi, source_inst, target_inst, year), `authorship_network.csv` (author_a, author_b, paper_doi, inst_a, inst_b, year), `indian_connections.csv` (your_inst, partner_inst, shared_papers, total_citations). Do not build these now unless asked.

---

## 10. Risk register and known pitfalls (check each deliberately)

| Risk | Mitigation |
|---|---|
| OpenAlex under-covers/misattributes CSIR affiliations (generic "CSIR" strings, multiple entities, AcSIR dual affiliation) | §5.4 recall boosters; parent-entity check; QA recall report |
| Look-alike institutions leaking in (Newcastle "NCL", IICB vs IICT, ICT Mumbai, other CSIR labs) | `confusable_entities_to_exclude`; ROR-only matching; leakage test |
| Name collisions in faculty↔author matching (common Indian names) | Match only among authors seen in our corpus; ≥2 evidence pieces; review queue |
| Split/merged OpenAlex author profiles distort h-index | `author_ids` sets; merge-review file; compute in-corpus h-index too |
| Faculty roster websites change/block scraping/are JS-rendered | Cache HTML, use Playwright, fall back to IRINS/VIDWAN/annual reports; document |
| Summing citations over author rows (double counting) | Paper-level dedupe everywhere; unit tests |
| 2026 partial year misread as decline | Label everywhere; exclude from CAGR |
| SJR quartile ≠ JCR; 2026 quartile unavailable; ISSN mismatch | Quartile policy §5.8, match-method flags, coverage reported |
| CORE ranks are CS-only → empty conference panel | Graceful empty state, N shown |
| API budget exhaustion/rate limits (usage-based pricing since Feb 2026) | Cache, `select=`, batch 100 IDs, budget tracker, resume across days |
| OpenAlex field/filter names drift | Check live docs; contract tests that fail loudly on unexpected response shape |
| Mixed-date data pulls | Single `collected_at`; re-pull everything if refreshing |
| Silent row drops / inconsistent counts across report vs dashboard | Count reconciliation tables; consistency tests |
| Retractions / paratext / errata inflating counts | Type filters + flags |
| Large datasets making dashboard slow | Pre-aggregation, compact payloads, lazy loading |
| Privacy/ethics | Only public bibliographic/staff-directory data; no emails/phone numbers stored beyond what is necessary; respect robots.txt and ToS; attribute data sources in the dashboard footer |

---

## 11. Acceptance checklist (maps to the instructor's submission checklist)

- [ ] `group24_data.csv` exists, **exactly** the 14 required columns in order; no extras
- [ ] Years only 2016–2026; all three institutes present; `group` = 24
- [ ] Paper-level dedupe verified; per-paper citation consistency verified
- [ ] `quartile` and `type` rules applied; CORE for conferences only
- [ ] `coauthor_institutes`, `cites_indian_inst`, `cited_by_indian_inst` populated per definitions
- [ ] QA_REPORT.md all green; review queues resolved or accepted; LIMITATIONS.md written
- [ ] Statistics report ≤10 slides, covers all required metrics; slides 9–10 reserved for network summaries
- [ ] Dashboard: all required panels (network panels as labelled placeholders until Task 4), filters work, offline-capable
- [ ] Report numbers == dashboard numbers (automated test)
- [ ] No API keys or other groups' data in the submission package
- [ ] README and DATA_DICTIONARY complete; `make all` reproduces everything from cache

---

## 12. Agent working protocol

- Work in small, verifiable steps; after each step run its assertions/tests and print a short summary (counts, coverage, anomalies).
- Log to `logs/<stage>_<timestamp>.log`; never log secrets.
- Prefer deterministic code over manual edits; any manual correction must live in a versioned file (`config/overrides/*.csv`) with reason and date, and be applied by code.
- Write unit tests for: DOI/ISSN/name normalisation, ISSN↔SJR matching, quartile policy, h-index calculation, Indian-institution flagging rule, paper-level dedupe, partial-year handling.
- Use `git` with frequent small commits; never commit `.env`, caches, or raw data.
- When uncertain whether something is a requirement or a judgment call, check §1 (authoritative) and §13; document the choice.
- Final response of each phase: what was produced (file paths), key numbers, known gaps, items needing human decision.

---

## 13. Decisions to confirm with the group/instructor (defaults chosen — change here if told otherwise)

1. **Faculty definition**: scientific cadre from official rosters; students/project staff appear as `affiliated_author` rows but are excluded from faculty stats. *(Alternative: include all affiliated authors as "faculty".)*
2. **Main-CSV `coauthor_institutes`**: Indian institutions only (excluding own institute); all-country list in the extended file. *(Alternative: all countries in the main column.)*
3. **h-index default in dashboard/report**: OpenAlex career h-index, with 2016–2026 in-corpus h-index shown alongside.
4. **Quartile source**: SJR best quartile of the publication year (2025 values for 2026 papers); JCR not used unless someone has legitimate access.
5. **Work types kept**: journal articles, reviews, letters, conference papers; everything else excluded and logged.
6. **API spend**: free daily budget with spreading over days; ask the owner before spending credits.
7. **Retracted works**: kept in the data (flagged), excluded from headline statistics.
8. **Scopus/IRINS**: used only as cross-checks if accessible.
9. **Combined view**: "All three" counts distinct papers once.
10. **Collaboration**: the instructor encourages inter-group collaboration — if Group 25/26 (other CSIR chemistry/physics labs) want to collaborate, inform the instructor first; until then, no data exchange.

---

## Appendix A — Query templates (verify syntax against live docs before use)

```
# resolve institution
GET /institutions?filter=ror:https://ror.org/057mn3690&api_key=…
# yearly counts for recall reference
GET /works?filter=authorships.institutions.id:I…,publication_year:2016-2026&group_by=publication_year
# works for one institute-year (cursor paging)
GET /works?filter=authorships.institutions.id:I…,publication_year:2021&per_page=100&cursor=*&select=id,doi,title,publication_year,type,cited_by_count,counts_by_year,authorships,primary_location,primary_topic,topics,referenced_works,biblio
# works by author
GET /works?filter=authorships.author.id:A…,publication_year:2016-2026
# batch resolve sources / works / authors
GET /sources?filter=openalex_id:S1|S2|…&per_page=100
GET /works?filter=openalex_id:W1|W2|…&select=id,authorships&per_page=100
GET /authors?filter=openalex_id:A1|A2|…&select=id,display_name,orcid,works_count,cited_by_count,summary_stats
# incoming citations from Indian-affiliated works for a batch of our papers
GET /works?filter=cites:W1|…|W100,authorships.countries:IN&per_page=100&cursor=*&select=id,publication_year,referenced_works,authorships
# budget
GET /rate-limit?api_key=…
```

## Appendix B — Normalisation helpers (implement + unit-test)

- **DOI**: `doi.strip().lower()`, remove `https?://(dx\.)?doi\.org/`, validate regex, re-prefix `https://doi.org/`.
- **ISSN**: uppercase, remove spaces; display `NNNN-NNNC`; SJR form = without hyphen; validate checksum optionally.
- **Journal title key**: lowercase → `unidecode` → replace `&`→`and` → strip punctuation → drop leading "the" → collapse spaces.
- **Person name key**: strip titles (`Dr|Prof|Sri|Shri|Smt|Mr|Mrs|Ms`), `unidecode`, lowercase, remove dots/commas, split tokens; build keys `surname+initials`, `full tokens sorted`; treat single letters as initials.
- **Institution canonicalisation**: ROR → registry canonical name; strip "CSIR-" duplicates only through the registry (never by regex alone).

## Appendix C — Minimal `settings.yaml`

```yaml
years: {start: 2016, end: 2026}
collection_date: null            # filled automatically at run start (UTC date)
openalex: {per_page: 100, corpus: core, max_spend_usd_per_run: 0.80, max_rps: 20, concurrency: 8}
roster: {min_delay_s: 1.0, respect_robots: true}
matching: {fuzzy_threshold_auto: 92, fuzzy_threshold_review: 85}
former_faculty_heuristic: {min_papers: 10, min_distinct_years: 3}
stats: {hist_bin_width: 5, partial_year_note: "2026 is partial (data to collection date)"}
```
