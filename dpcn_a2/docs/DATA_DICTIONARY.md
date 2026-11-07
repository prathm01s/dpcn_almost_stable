# Data Dictionary — Group 24 Research Mapping Dataset

> **Collection Date:** 13 October 2026  
> **Course:** DPCN 2026 | **Instructor:** Chittaranjan Hens  
> **Assigned Cluster:** CSIR Chemistry ("Synthetic & Organic Chemistry")  
> **Institutions:** CSIR-NCL, CSIR-IICT, CSIR-CECRI  
> **Temporal Window:** 2016–2026 (inclusive; 2026 partial up to collection date)  
> **Granularity:** One row per **(paper × assigned-institute author)**

---

## 1. Primary Dataset: `data/final/group24_data.csv`

The primary submission dataset contains **exactly 14 columns** in the prescribed order with no auxiliary columns.

| # | Column Name | Type | Allowed Values / Format | Description & Derivation | Primary Source |
|---|---|---|---|---|---|
| 1 | `group` | Integer | `24` | Group assignment number. Constant across all records. | Assignment spec |
| 2 | `institution` | String | `CSIR-NCL`, `CSIR-IICT`, `CSIR-CECRI` | Canonical identifier of the assigned CSIR institute for which this row's authorship is recorded. | ROR / OpenAlex |
| 3 | `author` | String | UTF-8 text (e.g. `Sivaram Swaminathan`) | Full name of the author affiliated with the assigned institute on this paper. Academic titles removed; accents unidecoded. | OpenAlex `authorships[].author.display_name` |
| 4 | `title` | String | Text | Cleaned title of the publication (newlines and trailing punctuation stripped). | OpenAlex `title` / `display_name` |
| 5 | `year` | Integer | `2016`–`2026` | Calendar year of publication. Note: 2026 represents a partial year (Jan 1 – Oct 13, 2026). | OpenAlex `publication_year` |
| 6 | `type` | String | `journal`, `conference` | Type of peer-reviewed venue. Lowercase string. Editorials, errata, and book chapters were excluded in curation. | OpenAlex `type` |
| 7 | `journal_name` | String | Text | Full display name of the journal or conference proceedings. | OpenAlex `primary_location.source.display_name` |
| 8 | `issn` | String | `NNNN-NNNC` or blank | Hyphenated standard International Standard Serial Number (prefer linking ISSN-L or print ISSN). Strictly blank for conference proceedings. | OpenAlex `primary_location.source.issn_l` / ISSN list |
| 9 | `doi` | String | `https://doi.org/10.xxxx/...` or blank | Canonical resolving DOI URL in lowercase prefix format. Blank if no DOI was assigned. | OpenAlex `doi` |
| 10 | `citations` | Integer | $\ge 0$ | Total number of citing publications recorded in OpenAlex as of collection date. **Caution:** Never sum across rows without deduplicating by paper first. | OpenAlex `cited_by_count` |
| 11 | `quartile` | String | `Q1`, `Q2`, `Q3`, `Q4`, `CORE A*`, `CORE A`, `CORE B`, `CORE C`, or blank | Journal quartile or conference rank. Resolved against historical SCImago Journal Rank (SJR) panel (1999–2025) using ISSN and year matching; fallback to closest available year for 2026. Blank if unranked. | SCImago Journal Rank (1999–2025) / CORE |
| 12 | `coauthor_institutes` | String | Semicolon-delimited list or blank | Semicolon-separated list of canonical Indian partner institutions affiliated with co-authors on the paper, excluding the paper's own assigned institution. Formatted as `Inst A; Inst B`. Blank if no external Indian co-authors. | OpenAlex `authorships[].institutions` cross-referenced with `indian_inst_registry.csv` |
| 13 | `cites_indian_inst` | String | `TRUE`, `FALSE` | `TRUE` iff the paper cites at least one paper involving an Indian institution other than the row's institute: another assigned lab, an Indian co-author institute of a corpus paper, or an Indian institution of a DOI-bearing paper outside the corpus (OpenAlex, Step 17, 20 Oct 2026). Every TRUE is backed by a row of `citation_network.csv`. |
| 14 | `cited_by_indian_inst` | String | `TRUE`, `FALSE` | `TRUE` iff at least one paper involving an Indian institution other than the row's institute cites this paper (corpus papers, plus DOI-bearing Indian-affiliated citing papers outside the corpus found via OpenAlex `cites:` on 20 Oct 2026). Every TRUE is backed by a row of `citation_network.csv`. |

---

## 2. Extended Dataset: `data/final/group24_data_extended.csv`

The extended dataset retains the identical row order and row count as `group24_data.csv`, appending rich metadata fields for downstream analysis, dashboarding, and network construction.

| Column Name | Type | Description |
|---|---|---|
| *(1–14)* | *Same as above* | Identical 14 primary fields from `group24_data.csv`. |
| `work_id` | String | OpenAlex work ID (e.g. `https://openalex.org/W2108183120`). |
| `author_openalex_id` | String | OpenAlex author entity ID (e.g. `https://openalex.org/A5102958597`). |
| `faculty_id` | String | Internal roster identifier (e.g. `FAC_NCL_0001`) if matched to an active scientific cadre roster member; blank otherwise. |
| `author_role` | String | Inferred author role: `faculty` (active scientific staff matched to institute directory), `probable_former_faculty` (high output, unlisted in current directory), or `affiliated_author` (student, postdoc, or visiting scholar). |
| `department` | String | Department or scientific division from the official faculty directory. |
| `designation` | String | Official cadre rank (e.g., Scientist, Senior Scientist, Principal Scientist, Chief Scientist, Director). |
| `is_corresponding` | Boolean | True if OpenAlex indicates corresponding author status. |
| `author_position` | String | Position in the author list: `first`, `middle`, or `last`. |
| `source_id` | String | OpenAlex source/venue identifier (e.g. `https://openalex.org/S1983995261`). |
| `source_type` | String | Venue category: `journal`, `conference`, `repository`. |
| `issn_l` | String | Linking ISSN (unhyphenated or hyphenated canonical form). |
| `quartile_year_used` | Integer | SJR publication year utilized for quartile lookup (e.g. `2024` fallback for `2026` papers). |
| `quartile_match_method` | String | Method used to resolve quartile: `issn_year`, `issn_latest`, `title_exact`, or blank. |
| `field` | String | OpenAlex primary topic field (e.g. `Chemistry`, `Materials Science`, `Chemical Engineering`). |
| `subfield` | String | OpenAlex primary topic subfield (e.g. `Organic Chemistry`, `Electrochemistry`, `Catalysis`). |
| `domain` | String | OpenAlex primary topic domain (e.g. `Physical Sciences`, `Life Sciences`). |
| `primary_topic` | String | Granular topic name (e.g. `Transition-Metal-Catalyzed Asymmetric Synthesis`). |
| `is_retracted` | Boolean | True if flagged as retracted by OpenAlex/Crossref. |
| `is_partial_year` | Boolean | True for papers published in calendar year 2026. |
| `multi_inst_authorship` | Boolean | True if the paper has co-authors affiliated with multiple assigned CSIR institutes (e.g. NCL + IICT). |
| `collected_at` | String | ISO 8601 UTC timestamp of data collection. |

---

## 3. Auxiliary Data Deliverables

1. **`data/final/faculty_master.csv`**: Comprehensive directory of 385 scientific cadre scientists from official staff directories across NCL, IICT, and CECRI with in-corpus publication counts, citation totals, and career/corpus h-indices.
2. **`data/final/citation_edges_raw.parquet`**: 27,824 directed citation edges `(source_work_id -> target_work_id)` connecting corpus papers with citing/referenced works, partitioned and prepared for Task 4 network analysis.
3. **`data/final/works_table.parquet`**: Deduplicated paper-level dataset (14,357 works) containing full topic hierarchies, biblio details, and open access status.
4. **`config/indian_inst_registry.csv`**: 911 mapped Indian academic and research institutions with canonical display names, ROR IDs, state, city, and research sector classification (CSIR, IIT, IISc, NIT, Central Universities, etc.).


## Network files (Week 1–2 deliverables)

| File | Columns | Content |
|---|---|---|
| `citation_network.csv` | source_doi, target_doi, source_inst, target_inst, year | Directed "source cites target". (a) In-corpus edges: both papers in the NCL/IICT/CECRI corpus, inst = assigned lab. (b) Edges between a corpus paper and a DOI-bearing Indian-affiliated paper outside the corpus; the outside side's inst is its Indian institutions joined by `;` (our labs written CSIR-NCL / CSIR-IICT / CSIR-CECRI). `year` = citing paper's publication year. A corpus paper attributed to two labs appears once per lab. |
| `authorship_network.csv` | author_a, author_b, paper_doi, inst_a, inst_b, year | Undirected co-authorship. `author_a` is always an author of an assigned lab (`inst_a`). Rows with `inst_b` an assigned lab are within the cluster; other rows link to a co-author whose authorship is at another Indian institution (`inst_b`, `;`-joined if several). `paper_doi` blank for papers without DOI. |
| `indian_connections.csv` | your_inst, partner_inst, shared_papers, total_citations | Per assigned lab and Indian partner institution: distinct co-authored papers and the sum of their citations. Partners include the other two labs. |
| `indian_linked_works.csv` (supporting) | work_id, doi, title, year, cited_by_count, indian_institutions | Metadata of the outside papers used in `citation_network.csv`. |

Network analysis (PageRank, Louvain, centralities) uses only the within-cluster rows; the rows to outside Indian papers/authors are raw data, as the instruction note requires.

## Journal impact factor analogue (dashboard)

| Field | Definition |
|---|---|
| `jif` (dashboard `papers_compact`) | SCImago "Cites / Doc. (2 years)" of the paper's journal in its quartile year (`quartile_year_used`), matched on `issn` / `issn_l`, then cleaned journal title. Scopus-based; **not** Clarivate JIF. `null` when there is no SCImago match (822 of 14,208 papers). Used by the dashboard's "Journal IF" filter. |

## Citation impact ratio

| File / field | Definition |
|---|---|
| `data/final/work_reference_counts.csv` | `work_id`, `references_count` = number of works in the paper's OpenAlex `referenced_works` (citations made); `has_foreign_coauthor` = TRUE if any authorship institution has a country code other than IN (used by Insight 9). Blank for the one work OpenAlex no longer returns. |
| Paper impact ratio (IR) | `citations` ÷ `references_count`; undefined when `references_count` = 0 |
| IR-Q1 | IR > 0.60, the 75th percentile of paper IR over all papers (`config/settings.yaml` → `impact_ratio.quartile_percentile`), i.e. the top 25% of papers |
| IR > 5, IR > 10 | Fixed thresholds asked for by the instructor (`impact_ratio.thresholds`). `ir_gt_5_refs_ge_10` / `ir_gt_10_refs_ge_10` count the papers above the threshold whose OpenAlex reference list has ≥ 10 entries (`reliable_min_references`); `stats/tables/impact_ratio_high_papers.csv` lists every paper with IR > 5 and flags those with < 10 references (`few_references`), whose IR is likely overstated by an incomplete reference list |
| Institute impact ratio | Σ citations ÷ Σ references over the institute's distinct papers with ≥ 1 reference |
| `stats/tables/impact_ratio_summary.csv` | per institute + combined: IR, IR-Q1 counts/shares per threshold, SJR Q1 share |
| `stats/tables/impact_ratio_by_year.csv`, `impact_ratio_vs_sjr.csv`, `impact_ratio_top_papers.csv` | breakdowns by year, by SJR quartile, and the top 10 papers by IR |

---

## 4. Non-Obvious Insights (Bibliometric & Advanced Network Analytics)

### 4.1 JSON Deliverables (`stats/tables/insights/*.json`)
All 10 analyses conform strictly to the following common JSON contract schema:
- `id` (String): Unique identifier (e.g. `01_friendship_paradox`, `07_sleeping_beauties`).
- `question` (String): Plain-language guiding inquiry.
- `headline` (String): One-sentence punchline summarizing the core finding with quantitative numbers.
- `metrics` (Object): Key quantitative summary scalars used in headline and text.
- `chart` (Object): Self-contained ECharts configuration object:
  - `type` (String): ECharts type (`scatter`, `line`, `bar`, `sankey`).
  - `data` (Object): Coordinates, series arrays, axis formats, and visual mark lines.
- `method_note` (String): Detailed methodological citation and formulation notes.
- `computed_at` (String): UTC ISO 8601 generation timestamp.

### 4.2 List of Insight Deliverables
1. `01_friendship_paradox.json`: Co-authorship degree vs neighbor average degree ($k$ vs $k_{nn}$).
2. `02_rich_club.json`: Normalized rich-club coefficient $\rho_{norm}(k)$ against 20 degree-preserving rewired nulls.
3. `03_fragility.json`: Targeted attack (betweenness & degree) vs random node percolation curves.
4. `04_price_law.json`: Output inequality, Gini coefficients, and $\sqrt{N}$ productivity curve.
5. `05_quartile_vs_impact.json`: Citation distributions by SJR quartile, top-decile outliers, and uncitedness.
6. `06_pagerank_vs_citations.json`: Global raw citation count vs internal directed PageRank ranking.
7. `07_sleeping_beauties.json`: Ke et al. (2015) beauty coefficient $B$, awakening trajectories, and asleep durations.
8. `08_covid_shock.json`: Observed vs counterfactual output trajectories, topic shifts, and COVID synthesis shares.
9. `09_brain_circulation.json`: Impact comparisons (citations, foreign co-authors) of returnee vs home-grown faculty.
10. `10_succession_risk.json`: Senior-led research exposure shares across scientific divisions.
11. `11_information_diffusion.json`: Susceptible-Infected (SI) epidemic spreading simulation of novel methodologies and reagents across 6 disciplinary fields, comparing topic-modulated transmission vs domain-restricted subgraphs, with super-spreaders and blockers.

### 4.3 Validation & Spreading Model Deliverables
- `stats/tables/insights/09_validation_sample.csv`: Stratified validation sample of 30 scientists across the 3 labs:
  - `name`: Scientist full name from official directory.
  - `lab`: Assigned CSIR institute (`CSIR-NCL`, `CSIR-IICT`, `CSIR-CECRI`).
  - `predicted_class`: Algorithmic mobility class (`Home-grown`, `Returnee`, `Foreign-trained`, `Unclassifiable`).
  - `phd_proxy`: Inferred institution of first publication.
  - `host_country`: Inferred primary foreign host country during postdoctoral spell.
  - `profile_url`: OpenAlex author profile link for manual verification.
  - `true_class`, `notes`: Blank fields reserved for independent human evaluator audit.
- `stats/tables/insights/11_field_diffusion_metrics.csv`: Comparative epidemic threshold and diffusion metrics across fields:
  - `field`, `short_label`: Disciplinary field name and UI button label.
  - `active_researchers`: Authors in cluster with $\ge 1$ paper in field.
  - `subgraph_lcc_nodes`, `subgraph_edges`: Topology size of induced giant component.
  - `mean_degree`: Average degree $\langle k \rangle$ within the domain subgraph.
  - `beta_c_theoretical`: Degree-moment epidemic threshold $\beta_c = \frac{\langle k \rangle}{\langle k^2 \rangle}$.
  - `beta_c_spectral`: Adjacency spectral threshold $\frac{1}{\lambda_{\max}(A)}$.
  - `cond_a_infield_t50`, `cond_a_final_reach_pct`: In-field diffusion speed and reach under topic-modulated transmission. T50 = median over the field's seeds of each seed's median step to 50% adoption; blank when the typical seed does not reach 50% within 15 steps.
  - `cond_a_spillover_pct`: Cross-disciplinary leakage percentage into researchers outside the domain.
  - `cond_b_t50_steps`: Steps to reach 50% adoption under domain subgraph uniform transmission (same median definition; blank = not reached).
- `stats/tables/insights/11_super_spreaders_blockers.csv`: Seed rankings for spreading efficiency:
  - `field`: Target disciplinary field.
  - `condition`: Simulation mode (`Topic-Modulated (Full Net)` or `Domain Subgraph`).
  - `role`: `Super-Spreader` or `Super-Blocker`.
  - `rank`: Top rank (1 to 5).
  - `author`, `faculty_id`, `lab`, `degree`, `field_share_pct`: Author name, roster faculty ID, institutional affiliation, network degree, and disciplinary focus share.
  - `t50_steps`: Median step (over 50 runs) at which 50% of the field has adopted when starting from this author; blank when the median run does not get there within 15 steps.
  - `p_reach50`: Share of the 50 runs that reach 50% adoption within 15 steps.
  - `reach_t3_pct`: Early adoption traction (% reached by step $t=3$).
  - `final_reach_pct`: Asymptotic adoption reach (% reached by step $t=15$).

## Phase II files (D-34)

| File | Content |
|---|---|
| `data/final/work_author_counts.csv` | Per corpus paper: `n_authors` (all authors in OpenAlex, max 100), `authors_capped` (TRUE = 100 or more), `n_institutions`, `n_countries`, `countries`, `institution_ids`, `author_ids` (short OpenAlex ids). Step 21, from cached OpenAlex responses. |
| `data/final/citing_works.csv` | Indian papers outside the corpus citing >= 1 corpus paper: `work_id`, `doi`, `year`, `cited_by_count`, `n_authors`, `author_ids`, `institution_ids`, `n_references`, `n_references_to_corpus`. |
| `data/final/institutions_seen.csv` | Every institution on a corpus or citing paper: OpenAlex `display_name`, `country_code`, `type`, `sector` (Indian name rules; "Foreign" otherwise), `corpus_papers`, `citing_papers`. Sector corrections: `config/overrides/sector_overrides.csv`. |
| `stats/tables/phase2_overview*.csv` | Per lab / year: faculty, papers, Q1 papers, Q1 in IF > 5 and IF > 10 journals, papers with < 10 / >= 10 / >= 30 / 100+ authors, collaborating institutions (Indian / foreign), countries, international papers %. |
| `stats/tables/phase2_faculty_comparison.csv` | Per scientist: papers, Q1 (IF > 5, IF > 10), citations, h, faculty co-authors, collaborating institutions, international papers, >= 10-author papers, max authors, % citations from >= 10-author papers, flags, ranks. |
| `stats/tables/phase2_top30_by_if.csv`, `phase2_frequent_journals.csv`, `phase2_faculty_top10_by_if.csv` | Top 30 papers by journal IF (ties: citations), top 20 journals by papers (median IF), each scientist's top 10 papers by journal IF. |
| `stats/tables/phase2_large_author_papers.csv` | Papers with >= 30 authors (flagged). |
| `stats/tables/phase2_institution_network_*.csv` | Institutional co-authorship network: the 3 labs + 60 most frequent partners; edge weight = shared papers. |
| `stats/tables/phase2_temporal.csv` | Per period: papers, mean authors, % >= 10 authors, % international, collaborating institutions, active faculty, faculty co-author pairs (cross-lab), density, largest group, faculty citation links. |
| `stats/tables/phase2_citing_*.csv` | Citing papers by sector and year; diagnostics per citing institution (shared author %, lab co-author %, >= 5 lab papers cited %, top-author %, 2023–26 %, median references, median citations) with benchmark rows. |
| `stats/tables/phase2_data_checks.csv` | Name and affiliation checks with counts and handling. |


## Global benchmark files (D-35)

Rules: `config/global_benchmark.yaml`; hand-reviewed rule-2b exclusions: `config/overrides/global_peer_exclusions.csv` (`institution_id, name, country, reason, date`). Built by `python run.py global` (Steps 22–23, then `src/stats/global_benchmark.py` and `src/dashboard/build_global.py`). Shown on `dashboard/global.html`.

**Raw benchmark data (`data/final/global/`)**

| File | Columns | Notes |
|---|---|---|
| `scope_subfields.csv` | subfield_id, subfield, lab_papers, share_pct, cum_share_pct, in_scope | OpenAlex primary-topic subfields of the three labs' papers 2016–2025 (articles, reviews); `in_scope` = the subfields making up 90% |
| `candidates.csv` | country, country_code, institution_id, name, type, city, ror, in_scope_papers, rejected_because, sim_CSIR-NCL, sim_CSIR-IICT, sim_CSIR-CECRI, selected_twin_of | Every institution in each country's pool (rule 1) with the rule it failed, or its similarity to each lab |
| `peers.csv` | group, country, institution_id, name, type, city, twin_of, similarity, in_scope_papers | The 3 labs, the foreign twins and the Indian reference group (for Indian peers `twin_of` = most similar lab) |
| `subfield_profiles.csv` | institution_id, subfield_id, subfield, papers | All papers 2016–2025 by subfield (the similarity input) |
| `bench_by_year.csv` | institution_id, year, papers_all, papers_scope, top10, top1, above_world, intl | `top10`/`top1`: OpenAlex `citation_normalized_percentile.is_in_top_10_percent` / `_1_percent`; `above_world`: `fwci > 1`; `intl`: `countries_distinct_count > 1`; all except `papers_all` in scope |
| `country_by_year.csv` | country_code (IN, US, CN, KR, AU, WORLD), year, papers_scope, top10, top1 | Papers with ≥ 1 author in the country (whole counting) |
| `collab_by_year.csv` | lab, institution_id, year, papers | Papers with both the lab and the peer (all fields) |
| `citation_flows.csv` | lab, institution_id, direction, work_id, year, coauthored_with_lab | One row per peer paper and lab: `peer_cites_lab` = the peer paper cites ≥ 1 of the lab's curated papers; `lab_cites_peer` = it is cited by ≥ 1 of them. `year` = year of the peer paper |

**Tables (`stats/tables/global_*.csv`)**

| File | Content |
|---|---|
| `global_peers.csv` | peers.csv plus a short display name |
| `global_summary.csv` | per institution 2016–2025: papers_all, papers_scope, scope_share_pct, papers_2016, papers_2025, cagr_pct, top10_pct, top1_pct, above_world_pct, intl_pct, top10_pct_early (2016–20), top10_pct_late (2021–25) |
| `global_by_year.csv` | per institution and year: papers_scope, index_2016 (2016 = 100), top10_pct, intl_pct |
| `global_countries.csv` | per country and year: papers_scope, world_share_pct, top10_pct, top1_pct |
| `global_links.csv` | per lab and peer: coauthored_papers, peer_papers_citing_lab, peer_papers_cited_by_lab (both excluding papers co-authored with the lab), exchange_ratio = citing ÷ cited_by, is_twin |
| `global_country_relations.csv` | every foreign country on the labs' curated papers 2016–2026: rank, papers, share_of_foreign_coauthored_pct, papers per lab, papers 2016–20 and 2021–26, partner_institutions, top_partners |
| `global_rule_funnel.csv` | per country: pool size and institutions removed by each rule |
| `global_similarity.csv` | every institution that reached the similarity test |
| `global_profiles.csv` | share of each institution's papers in the 12 largest scope subfields |
