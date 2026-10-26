# Group 24: Phase 2b Insights Handoff & Implementation Manual

**Course:** Data-driven Policy & Complex Networks (DPCN 2026)  
**Cluster:** CSIR Chemistry (CSIR-NCL, CSIR-IICT, CSIR-CECRI)  
**Date:** October 2026  
**Status:** ✅ **Complete, Tested, and Production-Ready**

---

## 1. Executive Summary

This handoff documents the complete implementation of the **10 Non-Obvious Insights** specified in `implementation.md`. These analyses uncover structural, demographic, topological, and historical phenomena within the CSIR Chemistry Cluster that standard bibliometric metrics (e.g. publication counts, raw citations, or h-index) conceal.

Every insight adheres strictly to the required contract: **one direct question**, **one quantitative headline**, **key summary metrics**, and **one interactive Apache ECharts visualization**. All analyses are backed by verifiable data in `stats/tables/insights/*.json`, bundled into `dashboard/data/g24_insights.js`, displayed in the interactive dashboard's **Insights** tab, integrated as an 11th slide in the official presentation, and covered by automated unit and browser tests.

---

## 2. Summary of the 10 Non-Obvious Insights

| # | Slug | Core Question | Quantitative Headline Finding | Chart Type |
|---|---|---|---|---|
| **01** | `friendship_paradox` | Do our researchers' co-authors have more co-authors than they do? | 93.2% of researchers have fewer co-authors than their co-authors do. The average researcher has 9.2 co-authors, but the average co-author has 31.1. | Scatter |
| **02** | `rich_club` | Do the most-connected scientists collaborate mainly with each other? | The top 1% most-connected researchers show no rich-club effect and are less interconnected than chance (ρ_norm = 0.75). 39 of 78 are CSIR faculty. | Line chart |
| **03** | `fragility` | How many researchers hold the cluster together? | Removing the top 841 bridge researchers (11.2% of the network) halves the cluster; random removal needs 3,282. Removing 644 of them separates the three labs' faculty into different components. | Line chart |
| **04** | `price_law` | Is output concentrated in a few scientists? | √N = 18 scientists produce 35.8% of the cluster's papers (Price's law predicts 50%). The top 10% produce 48.2%; Gini = 0.61 (papers), 0.74 (citations). | Line chart |
| **05** | `quartile_vs_impact` | Is a Q1 journal a reliable signal of a highly cited paper? | 11.3% of the cluster's top-10% most-cited papers were published outside Q1 journals, while 1.4% of Q1 papers are still uncited. | 100% stacked bar |
| **06** | `pagerank_vs_citations` | Are the papers most influential inside our cluster the same as the world's most-cited? | In-cluster influence and global citations correlate only moderately (Spearman ρ = 0.40). 43 papers are 'hidden gems': top-5% internal influence, below-median global citations. | Scatter |
| **07** | `sleeping_beauties` | Which papers were ignored for years and then suddenly took off? | 2 of the 7 strongest candidates (top 1% of 602 papers by Ke's B) show sustained delayed recognition. The strongest, 'Funnel shaped molecules containing benzo/pyrido[1,2,5]thiadiazole f…' (IICT, 2016), drew 1.4 citations/yr for 5 years, then 4.7/yr from 2021. | Line chart |
| **08** | `covid_shock` | How much output did COVID cost, and did research shift? | Output was 1.8% above the 2016–19 trend in 2020 and 12.7% above in 2021. COVID-related work peaked at 5.5% of CSIR-IICT's papers in 2021; the topic mix shifted about as much as in a normal period (JSD ratio 1.05). | Line chart |
| **09** | `brain_circulation` | How many of our scientists trained in India, worked abroad, and came back, and did time abroad change their research? | 17.0% of classifiable CSIR scientists are returnees (NCL 17.7% (n=141), IICT 17.0% (n=106), CECRI 11.1% (n=18)); their abroad spell was most often in the US (25 of 45). Their papers' citations do not differ significantly from home-grown peers of similar career age (+8%, 95% CI -20% to +46%); 20.6% of returnees' papers vs 16.9% of home-grown scientists' papers have a foreign co-author. | Sankey diagram |
| **10** | `succession_risk` | How much of each lab's output depends on scientists close to retirement? | In CECRI, 46.3% of recent papers (48.6% of their citations) have only roster authors likely to retire within ~5 years (IICT 20.8%, NCL 11.5%). Highest exposure: Electrochemical Process Engineering, CECRI (74.6% of 193 papers). | Grouped bar |

---

## 3. Data Lineage and Offline Infrastructure

### 3.1 Source Data Assets
- `data/final/group24_data_extended.csv`: 42,393 author-paper rows covering 14,352 distinct peer-reviewed works (2016–2026).
- `data/final/faculty_master.csv`: 385 scientific cadre staff across CSIR-NCL, CSIR-IICT, and CSIR-CECRI (after the D-20 roster cleanup).
- `data/final/citation_network.csv` & `authorship_network.csv`: Resolved within-cluster and Indian network edges.
- `data/cache/openalex/counts_by_year.json`: Cached yearly citation histories for 3,614 eligible papers (2016–2020 with $\ge 20$ citations) from OpenAlex.
- `data/cache/openalex/careers/*.json`: Cached full career publication histories of the matched faculty (OpenAlex works by author ID).
- `data/cache/openalex/foreign_coauthors.json`: Pre-computed foreign co-authorship fractions for all active faculty.

### 3.2 Output Artifacts
- `stats/tables/insights/*.json`: 10 independent JSON files complying with the common contract schema.
- `stats/tables/insights/09_validation_sample.csv`: Stratified validation sample of 30 scientists across all 3 labs with OpenAlex profile URLs for human evaluation.
- `dashboard/data/g24_insights.js`: Pre-compiled browser bundle exposing `window.G24_INSIGHTS`.
- `stats/report/24_CSIR.pptx` & `.pdf`: Official slide deck with Slide 10 ("10 Key Structural & Network Findings") presenting a formatted two-column summary table.

---

## 4. Dashboard Implementation

The interactive dashboard at `dashboard/index.html` features a dedicated **Insights** tab:
1. **Interactive Cards Grid**: 10 distinct metric cards rendered dynamically from `window.G24_INSIGHTS`.
2. **Dynamic Chart Rendering**: Handled via `renderInsights()` in `dashboard/js/app.js` using Apache ECharts 5 (scatter plots, line curves, grouped/stacked bars, and sankey diagrams).
3. **Number Bolding & Typography**: Automatically emphasizes metrics and percentages in headlines for high visual readability.
4. **100% Offline Capability**: Runs seamlessly via the local `file://` protocol without requiring local web servers or external CDNs.
5. **Headless Chrome Verification**: Validated via automated Chrome DevTools Protocol (`scripts/test_browser.py`) with zero console errors.

---

## 5. Human Validation Sample Status

In accordance with Insight 9 ("Brain Circulation"), a random stratified sample of 30 scientists was exported to `stats/tables/insights/09_validation_sample.csv`:
- **Columns**: `name`, `lab`, `predicted_class`, `phd_proxy`, `host_country`, `profile_url`, `true_class`, `notes`.
- **Predicted Distribution** (seed 24, regenerated 26 Oct 2026): Foreign-trained: 3, Home-grown: 16, Returnee: 8, Unclassifiable: 3.
- **Audit Ready**: Evaluators can open the provided OpenAlex URLs in column 6 to inspect full career publications and confirm postdoctoral affiliations.

---

## 6. Execution Commands & Verification Guide

### Recompute All Insights
```bash
# Recompute all 10 insights and regenerate dashboard/data/g24_insights.js
make insights
# Or via Python runner:
python3 run.py insights
```

### Rebuild Official Presentation Report
```bash
# Generates stats/report/24_CSIR.pptx (10 slides) and .pdf
python3 -m src.stats.make_report
```

### Run Automated Unit and Integration Tests
```bash
# Runs full pytest suite (42 tests, 100% passing)
python3 -m pytest tests/
```

### Run End-to-End Browser Automation Test
```bash
# Runs headless Chrome CDP test on both HTTP (127.0.0.1:8080) and file:// protocol
python3 run.py browser-test
```

### Re-package Submission Bundles
```bash
# Syncs submission_week1-2/, submission_week3/, and final_submission/
python3 scripts/package_submissions.py
```

---

## 7. Review fixes (26 Oct 2026)

A review of the insights code found and fixed these issues (details in `docs/DECISIONS.md` D-19):
- **Report length**: the report had 11 slides and the ≤10 test had been relaxed to ≤15. Slide 1 now merges the title with data & method, the findings table is slide 10 at ≥10 pt, and the test is back to ≤10.
- **Invented fallbacks removed**: host countries "US/Germany", random-removal "3280", rich-club default 1.0, and "N/A" in headlines.
- **Career fetch** (`src/collect/fetch_author_careers.py`) now uses the project's OpenAlex client (API key, cache, retries, cursor paging, no 1,000-work cap); errors stop the run instead of caching partial careers. Foreign co-author flags come from Step 18 (cached data), and papers without data are excluded instead of counted as "no".
- **Sleeping beauties**: complete years only (2016–2025), peak year ≥10 citations, and a check whether the awakening is sustained; most top candidates were short spikes.
- **Insight 10** no longer hard-codes CSIR-IICT; it reports the most exposed lab. **Insight 6** uses each year's median over all corpus papers. **Insight 2** evaluates ρ on the same top-1% set it counts.
- **Determinism**: ties in host/PhD country and the co-author LCC node order no longer depend on Python's hash seed (outputs identical across PYTHONHASHSEED values).
- **Dashboard**: year-axis line charts (Insights 7, 8) now plot; axis titles no longer clipped; legends on one line; Sankey shows classifiable scientists only.

Pending: fill `true_class` in `stats/tables/insights/09_validation_sample.csv` (30 scientists) to report classification accuracy.
Roster issues seen during the review were fixed afterwards by Step 19 (D-20): 119 IICT technical-staff entries removed from the faculty roster, Dr. D. Srinivasa Reddy kept once (IICT), and three wrong OpenAlex matches cleared. Faculty with papers: 347 → 306.
