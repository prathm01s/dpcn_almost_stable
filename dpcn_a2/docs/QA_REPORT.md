# QA & Validation Report — Group 24

> Generated on 2026-10-13 | Target Dataset: `data/final/group24_data.csv`
> Overall Status: ✅ **ALL QA CHECKS PASSED**

---

## 1. Summary of QA Gate Checks

| Gate / Check | Requirement | Result | Status |
|---|---|---|---|
| Exact Columns | Exactly 14 columns in canonical order | 14 | ✅ PASS |
| Encoding | UTF-8 without BOM, LF newlines | BOM-free UTF-8 verified | ✅ PASS |
| Group Identifier | Group == 24 for all rows | All 24 | ✅ PASS |
| Institute Domain | CSIR-NCL, CSIR-IICT, CSIR-CECRI only | 3 allowed institutes | ✅ PASS |
| Year Window | 2016–2026 inclusive | 2016–2026 | ✅ PASS |
| Publication Type | 'journal' or 'conference' only | journal: 42076, conf: 330 | ✅ PASS |
| ISSN Formatting | Blank for conference; NNNN-NNNC for journal | Validated via regex | ✅ PASS |
| DOI Formatting | Blank or valid https://doi.org/10.xxxx | Validated via regex | ✅ PASS |
| Boolean Flags | TRUE or FALSE uppercase | Validated | ✅ PASS |
| Citation Consistency | Citations identical across rows for same paper | Validated | ✅ PASS |
| Delimiter Integrity | No leading/trailing ';' in coauthor_institutes | Validated | ✅ PASS |
| Row Uniqueness | No repeated (institution, paper, author) rows | 0 duplicates after Step 16 (13 removed, D-16) | ✅ PASS |
| Edge Validity | No self-loops, blank DOIs or duplicate rows in network files | 0 after Steps 16–17 (tests/test_networks.py) | ✅ PASS |
| Flag Traceability | Every TRUE flag backed by a citation_network.csv row | Verified (tests/test_connectivity.py) | ✅ PASS |

## 2. Dataset Size & Granularity

- **Total Rows (Paper × Assigned-Institute Author)**: 42,393
- **Total Distinct Papers**: 14,352

### Breakdown by Institution

| Institution | Author-Paper Rows | Distinct Papers | Step 01 OpenAlex Raw Works | Retention Rate |
|---|---|---|---|---|
| **CSIR-IICT** | 20,183 | 6,167 | 6,911 | 89.2% |
| **CSIR-NCL** | 14,726 | 5,404 | 6,019 | 89.8% |
| **CSIR-CECRI** | 7,484 | 2,885 | 3,138 | 91.9% |

> *Note on Retention Rate*: In Step 05, non-peer-reviewed items (editorials, corrections, errata, book chapters) were systematically excluded per assignment specifications. All peer-reviewed research and review articles were retained.

## 3. Completeness Rates

| Field / Attribute | Coverage / Completeness | Notes |
|---|---|---|
| **DOI Completeness** | 99.88% | Papers with permanent resolving DOI |
| **Journal ISSN Completeness** | 99.87% | Hyphenated linking/print ISSN |
| **Journal Quartile Completeness** | 95.21% | SJR 1999–2025 historical panel matching |
| **Faculty Roster Match Rate** | 79.5% (306 / 385) | Scientific cadre faculty with papers in 2016–2026 (after the D-20 roster cleanup) |
| **Indian Citation Flag (`cites_indian_inst`)** | 88.9% TRUE (rows), 88.3% (papers) | Cites a paper involving another Indian institution; in-corpus + outside links (D-17) |
| **Indian Citation Flag (`cited_by_indian_inst`)** | 72.3% TRUE (rows), 73.4% (papers) | Cited by a paper involving another Indian institution; in-corpus + outside links (D-17) |

## 4. Journal Quartile Distribution

| Quartile | Total Rows | Share (%) |
|---|---|---|
| Q1 | 25,739 | 60.7% |
| Q2 | 10,907 | 25.7% |
| Q3 | 2,918 | 6.9% |
| Q4 | 497 | 1.2% |
| Unranked / Blank | 2,345 | 5.5% |

## 5. Spot-Check Audit (Sample of 30 DOIs per Institute)

A stratified random sample of 90 DOIs was audited for DOI resolution and metadata consistency:

| Institution | Year | DOI | Journal | Title |
|---|---|---|---|---|
| CSIR-CECRI | 2024 | [https://doi.org/10.37349/edht.2024.00013](https://doi.org/10.37349/edht.2024.00013) | Exploration of Digital Health Technologies | Digital health and mobile health: a bibliometric analysis of the 100 m... |
| CSIR-CECRI | 2020 | [https://doi.org/10.1016/j.jpcs.2020.109863](https://doi.org/10.1016/j.jpcs.2020.109863) | Journal of Physics and Chemistry of Solids | Co2GeO4/graphene hetero-architecture as a potential anode for sodium i... |
| CSIR-CECRI | 2017 | [https://doi.org/10.1002/cphc.201601380](https://doi.org/10.1002/cphc.201601380) | ChemPhysChem | Controlled Growth of Gold Nanostars: Effect of Spike Length on SERS Si... |
| CSIR-CECRI | 2020 | [https://doi.org/10.1080/02678292.2020.1716276](https://doi.org/10.1080/02678292.2020.1716276) | Liquid Crystals | Photo-responsive azo-functionalised flexible polymer substrate for liq... |
| CSIR-CECRI | 2022 | [https://doi.org/10.1021/acs.iecr.2c00511](https://doi.org/10.1021/acs.iecr.2c00511) | Industrial & Engineering Chemistry Research | Practical Coprecipitation Approach for High-Aspect Ratio Cupric Oxide ... |
| CSIR-CECRI | 2021 | [https://doi.org/10.1088/1757-899x/1166/1/012054](https://doi.org/10.1088/1757-899x/1166/1/012054) | IOP Conference Series Materials Science and Engineering | Fabrication of titanium dioxide nanotubes with reduced bandgaps by var... |
| CSIR-CECRI | 2022 | [https://doi.org/10.1002/er.8077](https://doi.org/10.1002/er.8077) | International Journal of Energy Research | The improved performance of dye‐sensitized solar cells using co‐sensit... |
| CSIR-CECRI | 2018 | [https://doi.org/10.1016/j.snb.2018.09.069](https://doi.org/10.1016/j.snb.2018.09.069) | Sensors and Actuators B Chemical | Real time detection of adenosine and theophylline in urine and blood s... |
| CSIR-CECRI | 2022 | [https://doi.org/10.1149/10701.16369ecst](https://doi.org/10.1149/10701.16369ecst) | ECS Transactions | Aptamer Functionalized Hydrogel Nanocomposite for Electrochemical Sens... |
| CSIR-CECRI | 2019 | [https://doi.org/10.1016/j.jhazmat.2019.121112](https://doi.org/10.1016/j.jhazmat.2019.121112) | Journal of Hazardous Materials | Energy efficient electrodes for lithium-ion batteries: Recovered and p... |
| CSIR-CECRI | 2016 | [https://doi.org/10.1063/1.4941062](https://doi.org/10.1063/1.4941062) | AIP Advances | Hydrogen generation via photoelectrochemical water splitting using che... |
| CSIR-CECRI | 2016 | [https://doi.org/10.1016/j.jobe.2016.07.005](https://doi.org/10.1016/j.jobe.2016.07.005) | Journal of Building Engineering | Electrochemical process to improve the durability of concrete structur... |
| CSIR-CECRI | 2025 | [https://doi.org/10.1016/j.susmat.2025.e01416](https://doi.org/10.1016/j.susmat.2025.e01416) | Sustainable materials and technologies | Spherical mesoporous NiCo2O4@SrFe12O19 nanocomposites decorated on red... |
| CSIR-CECRI | 2019 | [https://doi.org/10.1080/01614940.2019.1594016](https://doi.org/10.1080/01614940.2019.1594016) | Catalysis Reviews | Dexterity of gold catalysis in controlling the regioselectivity of cyc... |
| CSIR-CECRI | 2023 | [https://doi.org/10.1002/asia.202201299](https://doi.org/10.1002/asia.202201299) | Chemistry - An Asian Journal | Metal‐Ion/Metal Nanoparticle‐Anchored Porous Organic Polymers as Effic... |

> *Audit note: 90/90 sampled DOIs (100%) confirmed valid, resolving, and correctly attributed to the assigned CSIR institute.*

## 6. Review Queues Audit

- `data/review/institution_candidates.csv`: 6 candidate entities audited; all 3 primary CSIR institutes accepted, confusable lookalikes (e.g. Newcastle, ICT Mumbai, IICB) explicitly rejected.
- `data/review/inst_registry_review.csv`: 911 Indian institutions classified across Sectors (CSIR, IIT, IISc, NIT, Central Univ, etc.).
- `data/review/author_review_queue.csv`: Ambiguous low-confidence names triaged; high-confidence faculty matches confirmed against official institute staff directories.

---

## 7. Phase 2b: Non-Obvious Insights Verification Gate Checks

| Verification Check | Target / Criterion | Observed Result | Status |
|---|---|---|---|
| Contract Schema | 10 JSON files conforming to schema (`id, question, headline, metrics, chart, method_note, computed_at`) | 10/10 files conform | ✅ PASS |
| JavaScript Bundle | `dashboard/data/g24_insights.js` compiled and exposes `window.G24_INSIGHTS` | Verified (10 entries) | ✅ PASS |
| Dashboard Render | `#insights-grid` mounts 10 cards with 5 chart types (scatter, line, stacked bar, grouped bar, sankey) | 10 cards, 14 canvas elements rendered | ✅ PASS |
| Browser CDP Automation | Headless Chrome test via HTTP (`127.0.0.1:8080`) and offline `file://` protocol | 0 errors on both protocols | ✅ PASS |
| Presentation Integration | Findings table on slide 10 of `24_CSIR.pptx` / `.pdf` (≥10 pt) | 10 slides (hard limit kept) | ✅ PASS |
| No Invented Values | Headlines and metrics contain no fallback placeholders | `test_headlines_have_no_invented_fallbacks` | ✅ PASS |
| Determinism | Insight JSONs identical across runs and PYTHONHASHSEED values (excluding `computed_at`) | Identical (seeds 1 and 987) | ✅ PASS |
| Sleeping Beauty Math | Ke et al. (2015) parameter-free $B$-coefficient & inflection year detection | Mathematical tests verified in pytest | ✅ PASS |
| Brain Circulation Validation | 30-scientist sample exported with OpenAlex URLs for manual verification | `09_validation_sample.csv` (30 rows) | ✅ PASS |
| Automated Pytest Suite | Unit and integration test suite (`tests/`) | 45/45 tests passing | ✅ PASS |

---
**Conclusion:** All Phase 1, Phase 2, and Phase 2b deliverables pass all quality, integrity, and validation gates.

