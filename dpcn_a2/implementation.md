# implementation.md: Group 24 "Insights" Features

**Project:** DPCN Research Mapping, Group 24 (CSIR-NCL, CSIR-IICT, CSIR-CECRI, 2016–2026)
**Goal:** Add 10 non-obvious analyses. Each one answers a single question with **one headline sentence + one chart**. Do not add extra metrics, tables or commentary beyond what is specified here.

---

## 0. Ground rules (read first)

1. **Read before writing code (in this order):** `AGENTS.md` (its conventions override this file where they conflict), `handoff.md`, `README.md`, `docs/DATA_DICTIONARY.md`, `docs/DECISIONS.md`, `docs/LIMITATIONS.md`, `Makefile`, `run.py`. Then skim `src/common/`, `src/collect/`, `src/stats/`, `src/dashboard/` to learn the existing loaders, OpenAlex client, config handling and how `dashboard/data/g24_data.js` is generated. **Reuse these; do not write parallel versions.**
   Known data paths (verify):
   - `data/final/group24_data.csv`: paper × assigned-institute-author rows (**not** one row per paper)
   - `data/final/citation_network.csv`, `data/final/authorship_network.csv`, `data/final/citation_edges_raw.parquet`
   - `config/indian_inst_registry.csv` + the faculty roster file in `config/` or `data/`
   - `dashboard/index.html`, `dashboard/js/app.js`, `dashboard/data/g24_data.js`, `dashboard/vendor/echarts.min.js`
   Map the column names in `docs/DATA_DICTIONARY.md` to the fields used below (work id, author id, author name, is-roster-faculty flag, lab, division/department, year, quartile, citations, OpenAlex topic/subfield). If a required field is missing, derive it or stop and report. **Do not guess.**
2. **Never fabricate.** Every number shown must come from code in this repo. If an analysis cannot be computed, write `null` and the dashboard card shows "Not computed – <reason>".
3. **Aggregate at distinct work ID** for any paper-level count or citation sum (row granularity double-counts collaborative papers).
4. **Reproducible:** fixed seed `SEED = 24` for every random step. All OpenAlex API responses cached to `data/cache/openalex/` (JSON per request), so reruns do not hit the API.
5. **OpenAlex etiquette:** use the existing OpenAlex client in `src/collect` or `src/common` if there is one. Read `mailto` from the env var it already uses; otherwise add `OPENALEX_MAILTO` to `.env.example`. Batch IDs batch IDs (`filter=openalex_id:W1|W2|...`, ≤50 per call, `per-page=200`, `select=` only needed fields), sleep 0.1s between calls, retry with backoff on 429/5xx.
6. **Scope:** all stats are about our three labs. Pre-2016 career data (Sections 9–10) is used **only** to classify scientists' career paths, never added to the publication corpus.

### Code layout (fits the existing repo)

```
src/collect/
  fetch_counts_by_year.py      # Part C fetch (Section 7)
  fetch_author_careers.py      # Part D fetch (Sections 9–10)
src/stats/insights/
  __init__.py
  common.py                    # thin layer over src/common: distinct-paper table, graph builders, JSON writer
  s01_friendship_paradox.py
  s02_rich_club.py
  s03_fragility.py
  s04_price_law.py
  s05_quartile_vs_impact.py
  s06_pagerank_vs_citations.py
  s07_sleeping_beauties.py
  s08_covid_shock.py
  s09_brain_circulation.py
  s10_succession_risk.py
  run_all.py                   # runs s01–s10 (skips C/D if caches are missing, marks them null)
src/dashboard/
  build_insights_js.py         # stats/tables/insights/*.json -> dashboard/data/g24_insights.js
                               # (or extend the existing g24_data.js builder, if cleaner)
stats/tables/insights/         # NN_name.json (e.g. 03_fragility.json) + 09_validation_sample.csv
data/cache/openalex/           # raw API cache (add to .gitignore if large)
tests/test_insights.py         # unit tests (see acceptance checks)
```

Module names start with `s01_…` because Python can't import names that begin with a digit. Run each module with `python -m src.stats.insights.s01_friendship_paradox`.

**Entry points:**
- Add Makefile targets: `make insights-fetch` (Parts C+D, network), `make insights` (all stats from cache + rebuild dashboard JS), `make test` (existing target should pick up new tests).
- If `run.py` has a subcommand/stage system, register `insights` there too.

Dependencies: add any missing ones (`networkx scipy pyarrow requests`) to `requirements.txt`. No plotting libs. Charts are rendered in the dashboard with ECharts. If the existing pipeline in `stats/figures/` produces static PNGs for the report, follow that pattern only for the report table in Part F; it needs no figure.

### Output contract (every analysis JSON)

```json
{
  "id": "03_fragility",
  "question": "How many researchers hold the cluster together?",
  "headline": "Removing the top 14 bridge researchers (0.2%) halves the network; random removal needs 1,900.",
  "metrics": { "...": "only the numbers used in the headline + chart" },
  "chart": { "type": "line|bar|scatter|sankey|stacked_bar", "data": { } },
  "method_note": "One sentence: data used + method + key caveat.",
  "computed_at": "ISO timestamp"
}
```

The headline is generated from the metrics by a template string in code, never hand-typed.

### Shared building blocks (`common.py`)

- `papers()`: one row per distinct work: `work_id, doi, year, lab(s), type, journal, quartile, citations, subfield, n_authors`.
- `faculty()`: roster scientists: `author_id, name, lab, division, openalex_author_id`.
- `coauthor_graph(max_authors=30)`: undirected `networkx.Graph` from `authorship_network.csv`:
  - drop papers with `n_authors > max_authors` (hyper-authored papers create artificial cliques); log how many were dropped;
  - collapse multiple rows per pair into one edge with `weight = number of joint papers`;
  - node attrs: `name, lab (or 'external'), is_faculty`;
  - return the **largest connected component (LCC)** and also log its share of nodes.
- `citation_graph()`: directed `DiGraph` from `citation_network.csv` (source cites target).

---

## Part A: Co-authorship network (needs only existing files)

### 1. Friendship paradox
**Question:** Do our researchers' co-authors have more co-authors than they do?

**Method (on co-author LCC):**
- `k_i` = degree; `knn_i` = mean degree of i's neighbours.
- `share_paradox` = % of nodes with `knn_i > k_i`.
- `mean_k` = ⟨k⟩; `mean_neighbour_k` = ⟨k²⟩/⟨k⟩ (expected degree of a random co-author).
- Repeat `share_paradox` for **roster faculty nodes only**.

**Headline:** "X% of researchers have fewer co-authors than their co-authors do. The average researcher has A co-authors, but the average co-author has B."

**Chart:** scatter, x = k, y = knn (both log scale), y = x reference line, faculty points highlighted.

### 2. Rich club
**Question:** Do the most-connected scientists collaborate mainly with each other?

**Method:**
- `nx.rich_club_coefficient(G, normalized=False)` → ρ(k).
- Null: 20 degree-preserving rewired graphs (`nx.double_edge_swap`, `nswap = 10 × E`, `max_tries = 100 × nswap`, seeds `SEED..SEED+19`) → ρ_rand(k); ρ_norm(k) = ρ(k)/mean ρ_rand(k).
- Report at the degree threshold `k*` = 99th-percentile degree (top 1% of nodes): ρ_norm(k*), plus how many of those top-1% nodes are roster faculty and from which labs.
- If rewiring is too slow, use 10 nulls and state that in `method_note`.

**Headline:** "The top 1% most-connected researchers are X× more interconnected than chance (ρ_norm = X). N of them are CSIR faculty."
(If ρ_norm ≈ 1 or < 1, the headline must say there is **no** rich club. Report the true result.)

**Chart:** line, x = k, y = ρ_norm(k), horizontal reference at y = 1.

### 3. Fragility (targeted vs random removal)
**Question:** How many researchers hold the cluster together?

**Method (on co-author LCC, unweighted):**
- Strategies:
  - (a) remove by **betweenness**, computed once (`nx.betweenness_centrality(G, k=1000, seed=SEED)`), highest first;
  - (b) by **degree**;
  - (c) **random**, mean of 20 runs.
- Remove nodes one at a time up to 20% of nodes; after each removal record `LCC_size / original_LCC_size`.
- `n50_<strategy>` = removals needed for LCC to fall below 50%.
- `n_labsplit` = removals under betweenness until **no single component contains roster faculty from all three labs**.
- Record the names + labs of the first 10 removed under betweenness ("keystone researchers").

**Headline:** "Removing the top N bridge researchers (p% of the network) halves the cluster; random removal needs M. Removing just K people disconnects the three labs from each other."

**Chart:** line, x = fraction removed, y = relative LCC size, 3 series (betweenness, degree, random).

---

## Part B: Paper-level stats (needs only existing files)

### 4. Price's law + inequality
**Question:** Is output concentrated in a few scientists?

**Method:**
- Population: roster faculty with ≥1 paper (N active). Per scientist, count distinct papers (whole counting).
- Sort descending, take the top ⌈√N⌉ scientists. `price_share` = |union of their papers| / |union of all faculty papers|. Price's law predicts 50%.
- `top10_share` = same union share for the top 10% of scientists.
- `gini` over per-scientist paper counts.
- Also compute the Gini over per-scientist citations (sum over distinct papers).

**Headline:** "√N = n scientists produce X% of the cluster's papers (Price's law predicts 50%). The top 10% produce Y%; Gini = G (papers), H (citations)."

**Chart:** Lorenz curve (x = cumulative share of scientists, y = cumulative share of papers) with equality diagonal; marker at the √N point.

### 5. Does journal quartile predict impact?
**Question:** Is a Q1 journal a reliable signal of a highly cited paper?

**Method:**
- Journal papers, **years 2016–2023 only** (2024–26 too young to judge); quartile ∈ {Q1, Q2, Q3, Q4}.
- Top-10% flag **within publication year**: citations ≥ 90th percentile of that year's papers.
- Compute:
  - `pct_top10_from_nonQ1` = share of top-10% papers that are Q2–Q4;
  - `pct_Q1_uncited` = share of Q1 papers with 0 citations;
  - `pct_Q2Q3_in_top10` = share of Q2/Q3 papers that reach the top 10%.

**Headline:** "X% of the cluster's top-10% most-cited papers were published outside Q1 journals, while Y% of Q1 papers are still uncited."

**Chart:** 100% stacked bar per quartile: uncited / cited-but-not-top-10% / top-10%.

### 6. Local influence vs global citations
**Question:** Are the papers most influential *inside* our cluster the same as the world's most-cited?

**Method:**
- PageRank on `citation_graph()` (α = 0.85).
- Restrict to corpus papers with in-cluster in-degree ≥ 1.
- Spearman ρ between PageRank and global citation count.
- **Hidden gem** = top 5% by PageRank **and** below the median global citations of its publication year.
- List the top 5 hidden gems by PageRank (title, lab, year, journal, DOI, in-degree, global cites).

**Headline:** "In-cluster influence and global citations correlate only weakly (Spearman ρ = X). N papers are 'hidden gems': top-5% internal influence, below-median global citations."
(Word the strength from ρ: <0.3 weak, 0.3–0.6 moderate, >0.6 strong.)

**Chart:** scatter, x = global citations (log1p), y = PageRank (log), gems highlighted; table of the 5 gems under the chart.

### 8. COVID shock
**Question:** How much output did COVID cost, and did research shift?

**Method:**
1. **Output gap:** per lab and combined, fit a linear trend on annual distinct papers 2016–2019. Project 2020 and 2021. `gap_y` = (actual − predicted)/predicted. Use a trend, not the 2019 level, because output is already declining.
2. **Topic shift:** a paper is COVID-related if its title/abstract/OpenAlex topics match `covid|sars-cov-2|coronavirus|pandemic|antiviral|favipiravir|remdesivir` (case-insensitive). Report the COVID share by lab, 2020–2022, and its peak.
3. **Structural shift:** Jensen–Shannon divergence of the subfield distribution 2018–19 vs 2020–21, compared with the baseline 2016–17 vs 2018–19. Report the ratio.

**Headline:** "Output was X% below trend in 2020 and Y% in 2021. COVID-related work peaked at Z% of <lab>'s papers in <year>; the topic mix shifted R× more than in a normal period."

**Chart:** line per lab: actual papers 2016–2025 + dashed projected trend for 2020–21.

**Caveat for method_note:** publication lag means 2020 papers mostly reflect pre-pandemic work, so the effect should show mainly in 2021.

---

## Part C: Needs an OpenAlex fetch (paper-level)

### 7. Sleeping beauties
**Question:** Which papers were ignored for years and then suddenly took off?

**Fetch:** `counts_by_year` for all corpus works (`select=id,publication_year,counts_by_year`), cached.

**Method (Ke et al., 2015, PNAS):**
- Eligible papers: published 2016–2020, total cites ≥ 20, peak year `t_m ≥ 3` years after publication.
- With `c_t` = citations in year t after publication (t = 0 at the publication year):

  `B = Σ_{t=0}^{t_m} [ ((c_{t_m} − c_0)/t_m · t + c_0 − c_t) / max(1, c_t) ]`

- Awakening year `t_a` = the t ≤ t_m that maximises the distance from c_t to the line joining (0, c_0) and (t_m, c_{t_m}).
- Report the count of papers with B in the top 1%, and the top 5 by B (title, lab, journal, year, DOI, B, awakening year).

**Headline:** "N papers show delayed recognition. The strongest, '<title>' (<lab>, <year>), averaged A citations/yr for T years, then jumped to P/yr from <awakening year>."

**Chart:** line, yearly citations of the top 5 sleeping beauties, awakening year marked.

**Caveat:** the 10-year window only catches short sleeps. Say this in `method_note`.

---

## Part D: Needs an OpenAlex fetch (career histories)

Shared fetch for Sections 9 and 10: for every roster scientist with an OpenAlex author ID, fetch **all** works (any year) with `select=id,publication_year,authorships`. Keep only that author's own authorship entry → `(year, institution_id, institution_name, country_code)`. Cache to `data/cache/openalex/careers/<author_id>.json`.

If roster scientists lack OpenAlex IDs, resolve them by name + lab affiliation, with the match flagged `low_confidence` when it is ambiguous. Exclude low-confidence matches from the stats and report how many were excluded.

### 9. Brain circulation (returnees)
**Question:** How many of our scientists trained in India, worked abroad, and came back, and did time abroad change their research?

**Classification per scientist (from the career timeline):**
- `phd_proxy` = most frequent institution on the first 3 papers.
- `abroad_spell` = ≥2 **consecutive** years in which **all** of their affiliations are non-Indian, with ≥2 papers in the spell. This filters out co-author affiliation errors and short visits.
- Classes:
  - **Returnee**: phd_proxy in India → abroad_spell → current CSIR lab;
  - **Home-grown**: no abroad_spell;
  - **Foreign-trained**: phd_proxy outside India;
  - **Unclassifiable**: <3 papers before joining CSIR.
- Host country = most frequent country in the abroad spell.

**Validation (mandatory):**
- Export `stats/tables/insights/09_validation_sample.csv`: 30 random classified scientists, columns `name, lab, predicted_class, phd_proxy, host_country, profile_url, true_class (blank), notes (blank)`. The team fills `true_class` from CSIR profile pages.
- If the filled file exists, compute and report accuracy. If not, the card shows "validation pending".

**Metrics:**
1. % returnees per lab (of classifiable scientists).
2. Top 5 host countries.
3. **Did it change their research?** For 2016–2026 papers, compare returnees vs home-grown on:
   - (a) citations per paper, adjusted with OLS: `log1p(cites_per_paper) ~ returnee + academic_age + C(lab)`; report the returnee coefficient as a % difference with a 95% CI;
   - (b) share of papers with ≥1 foreign co-author.

**Headline:** "X% of classifiable CSIR scientists are returnees (NCL a%, IICT b%, CECRI c%), mostly via <country1>, <country2>. Returnees' papers draw D% more citations than home-grown peers of similar career age, and E% vs F% of their papers have foreign co-authors."
(Do not claim causation. If the CI includes 0, the headline says "no significant difference".)

**Chart:** Sankey: PhD region (India / abroad) → host country (top 5 + other / none) → lab.

### 10. Succession risk
**Question:** How much of each lab's output depends on scientists close to retirement?

**Method:**
- `academic_age = 2026 − first publication year` (from the career fetch).
- **At-risk** = academic_age ≥ 30. This is a proxy for being within ~5 years of CSIR superannuation at 60, assuming the first paper comes around age 25–27. Run sensitivity with thresholds 28 and 32.
- Using distinct papers 2021–2025 per lab:
  - `share_any` = % of papers with ≥1 at-risk roster author;
  - `share_sole` = % of papers whose **only** roster authors are at-risk, i.e. papers that would have no CSIR faculty author left;
  - the same two measures for citations.
- Division with the highest `share_sole`.
- If the repo has real birth or joining dates, use those instead of the proxy and say so.

**Headline:** "X% of <lab>'s recent papers (Y% of its citations) are led solely by scientists likely to retire within ~5 years. Highest exposure: <division> (Z%)."

**Chart:** grouped bar per lab: `share_sole` papers vs `share_sole` citations, with threshold-28/32 error whiskers.

---

## Part E: Dashboard integration

1. `src/dashboard/build_insights_js.py` writes `dashboard/data/g24_insights.js`:
   `window.G24_INSIGHTS = { "01_friendship_paradox": {...}, ... };`
   (Use a JS global, the same pattern as `g24_data.js`, so the dashboard works from `file://` without fetch.)
2. In `index.html`:
   - add `<script src="data/g24_insights.js"></script>` before `js/app.js`;
   - add the tab button `<button class="tab-btn" data-tab="insights">Insights</button>` before "Data & Exports";
   - add `<div id="tab-insights" class="tab-content">` with a responsive 2-column grid of 10 cards.
3. In `js/app.js`, add `renderInsights()`. Each card shows exactly:
   - **Question** (card title),
   - **Headline** (large text, key numbers bold),
   - **one ECharts chart** built from `chart`,
   - `method_note` in small muted text.
   Nothing else. Reuse existing card/CSS classes and the existing lab colours (IICT `#2b5c8f`, NCL `#2e7d32`, CECRI `#d95f02`).
4. The cards ignore the global year/quartile filters (they are fixed analyses). Add a small "Fixed analysis – filters don't apply" label to the tab.
5. Resize charts on tab show, as the existing tabs do.
6. Take a screenshot of the new tab into `dashboard/screenshots/insights.png`, following the existing screenshot convention.

## Part F: Report integration

The report is capped at 10 slides/5 pages. Add **one** slide/section titled "Ten Non-Obvious Findings": a 2-column table with the question in one column and the headline in the other, auto-generated from the JSONs. Do not add charts to the report; point to the dashboard tab.

---

## Part G: Docs & submission housekeeping

Update the existing docs; do not create new doc files:
- `docs/DECISIONS.md`: one entry per non-obvious choice (max-30-author cutoff, 2016–2023 window for quartile test, abroad-spell rule, academic-age ≥ 30 proxy, approximate betweenness k=1000).
- `docs/LIMITATIONS.md`: OpenAlex author disambiguation, the 10-year sleeping-beauty window, silent postdocs missed by the returnee rule, the retirement proxy, publication lag in the COVID analysis.
- `docs/DATA_DICTIONARY.md`: schema of the insight JSONs + validation CSV.
- `docs/QA_REPORT.md`: append the acceptance-check results below.
- `handoff.md`: what was added, how to run it, what is pending (e.g. validation sample to fill).
- `final_submission/`: copy the updated dashboard + report the same way existing deliverables are copied there (check how it is currently populated, e.g. a Makefile target, and reuse it).

## Implementation order & acceptance checks

| Step | Sections | Network/API? | Done when |
|---|---|---|---|
| 1 | `common.py` | No | Distinct paper count matches dashboard KPI (14,353); LCC size + dropped hyper-author papers logged |
| 2 | 1, 2, 3 | No | 3 JSONs; rich-club nulls seeded; fragility curves reach 20% removal |
| 3 | 4, 5, 6, 8 | No | 4 JSONs; quartile analysis uses 2016–2023 only |
| 4 | 7 | OpenAlex works | Cache populated; B formula unit-tested on a hand-made curve (flat then spike → high B; steady rise → B ≈ 0) |
| 5 | 9, 10 | OpenAlex authors | Career cache populated; validation CSV exported; match-confidence counts reported |
| 6 | Dashboard + report | No | Insights tab renders 10 cards with no console errors; every headline number traceable to a JSON metric |

**Final check:** run `make insights` from a clean clone (with cache present) and confirm it reproduces identical JSONs. Then run `make test` and confirm the tests pass.
