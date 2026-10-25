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
| **01** | `friendship_paradox` | Do our researchers' co-authors have more co-authors than they do? | **93.2% of researchers have fewer co-authors than their co-authors do.** The average researcher has 9.2 co-authors, but their average co-author has 31.1. (Even among faculty, 54.4% experience the paradox). | Log-log scatter plot ($k$ vs $k_{nn}$) with $y=x$ equality line |
| **02** | `rich_club` | Do top scientists collaborate primarily among themselves? | **No rich-club effect exists ($\rho_{norm} = 0.76 \le 0.95$).** Highly connected scientists collaborate with students and external networks rather than forming an insular clique. | Normalized curve $\rho_{norm}(k)$ with null envelope and threshold line at 1.0 |
| **03** | `fragility` | How fragile is the cluster's collaborative network? | **Halving the giant component requires removing 872 bridge researchers (11.6%)** targeted by betweenness, vs 3,279 by random attrition. Removing 608 bridges disconnects the 3 labs completely. | Percolation attack curves ($S/N$ vs removed nodes) |
| **04** | `price_law` | Is output concentrated in a few scientists? | **$\lceil\sqrt{N}\rceil = 19$ scientists produce 36.2% of papers** (Price's law predicts 50%). The top 10% produce 50.3%; Gini coefficient is 0.63 for papers and 0.75 for citations. | Lorenz curves (papers & citations) with $\sqrt{N}$ point and 50% line |
| **05** | `quartile_vs_impact` | Do Q1 papers actually draw more citations? | **11.3% of the cluster's top-10% cited papers were published outside Q1** (in Q2/Q3/Q4), while 1.4% of Q1 papers have zero citations after 3+ years. | Grouped boxplots & scatter overlay of citations by SJR quartile |
| **06** | `pagerank_vs_citations` | Which papers are disproportionately influential within the cluster? | **Spearman $\rho = 0.405$ reveals moderate divergence between raw citations and internal PageRank.** Identified 82 "hidden gem" foundation papers. | Scatter plot (Rank PR vs Rank Citations) with highlighted outliers |
| **07** | `sleeping_beauties` | Which papers were ignored for years and then took off? | **Identified 15 top-1% Sleeping Beauties (Ke et al., 2015 $B$-coefficient).** Top paper slept 5 years with $\le 2$ citations/yr before surging to 65 citations/yr. | Multi-line timeline showing awakenings and sleep durations |
| **08** | `covid_shock` | How did COVID-19 alter productivity and research topics? | **CSIR-CECRI output dropped 22.3% below trend in 2020 and 33.9% in 2021** (hardware lab dependence). COVID-related synthesis peaked at 5.5% at IICT in 2021. | Multi-line trend with counterfactual baseline & JSD topic shift |
| **09** | `brain_circulation` | Does international mobility boost citation impact? | **8.3% of faculty are verified returnees** (NCL 13.2%, IICT 4.0%, CECRI 0.0%). Returnees show no significant citation advantage ($p = 0.80$) but maintain 1.8× higher foreign co-authorship. | Sankey career flow + regression boxplot |
| **10** | `succession_risk` | How exposed are research areas to impending retirements? | **IICT has 20.0% of recent output and 23.3% of citations led solely by senior faculty** ($\ge 30$ yrs academic age). Highest exposure: Energy & Environmental Engg. (69.3%). | Stacked bar chart of paper share by division by faculty career cohort |

---

## 3. Data Lineage and Offline Infrastructure

### 3.1 Source Data Assets
- `data/final/group24_data_extended.csv`: 42,393 author-paper rows covering 14,352 distinct peer-reviewed works (2016–2026).
- `data/final/faculty_master.csv`: 505 scientific cadre staff across CSIR-NCL, CSIR-IICT, and CSIR-CECRI.
- `data/final/citation_network.csv` & `authorship_network.csv`: Resolved within-cluster and Indian network edges.
- `data/cache/openalex/counts_by_year.json`: Cached yearly citation histories for 3,614 eligible papers (2016–2020 with $\ge 20$ citations) from OpenAlex.
- `data/cache/openalex/careers/*.json`: Cached full career publication histories for all 344 active faculty from OpenAlex `/authors`.
- `data/cache/openalex/foreign_coauthors.json`: Pre-computed foreign co-authorship fractions for all active faculty.

### 3.2 Output Artifacts
- `stats/tables/insights/*.json`: 10 independent JSON files complying with the common contract schema.
- `stats/tables/insights/09_validation_sample.csv`: Stratified validation sample of 30 scientists across all 3 labs with OpenAlex profile URLs for human evaluation.
- `dashboard/data/g24_insights.js`: Pre-compiled browser bundle exposing `window.G24_INSIGHTS`.
- `stats/report/Group24_CSIR.pptx` & `.pdf`: Official slide deck with Slide 11 ("10 Key Structural & Network Findings") presenting a formatted two-column summary table.

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
- **Predicted Distribution**:
  - `Home-grown`: 13 scientists (e.g. Dr. Asha S.K., Dr. Sailaja Krishnamurty, Dr. K. Radhakrishnan).
  - `Returnee`: 4 scientists (e.g. Dr. Avijit Jana, Dr. Sreekumar Kurungot with foreign spells in US/DE/JP).
  - `Unclassifiable`: 13 scientists (pre-CSIR history incomplete or without indexed foreign affiliations).
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
# Generates stats/report/Group24_CSIR.pptx (11 slides) and .pdf
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
