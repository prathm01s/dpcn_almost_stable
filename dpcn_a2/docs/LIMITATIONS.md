# Data Quality Disclosures & Methodological Limitations

> **Course:** DPCN 2026 | **Instructor:** Chittaranjan Hens  
> **Group 24:** CSIR-NCL, CSIR-IICT, CSIR-CECRI (Synthetic & Organic Chemistry Cluster)  
> **Date of Collection:** 13 October 2026  

---

## 1. Coverage & Temporal Window

1. **Partial Year 2026**:
   - Data collection was executed in mid-October 2026. Therefore, publication and citation counts for calendar year 2026 represent a **partial year (~9.5 months)**.
   - Any multi-year trend analysis or Compound Annual Growth Rate (CAGR) calculations must either normalize 2026 or truncate the full-year evaluation window to 2016–2025.
   - Citations for recent works (2025–2026) are naturally lower due to citation latency (the time required for peer review and indexing of citing works).

2. **Peer-Reviewed Scope**:
   - In accordance with academic bibliometric standards and assignment guidelines (Step 05), non-peer-reviewed items such as editorial material, author corrections, errata, front/back matter, and book chapters were filtered out (1,598 items excluded across all three institutes).
   - This ensures metrics accurately reflect original research articles and peer-reviewed review articles.

---

## 2. Venue Classification & Quartiles

1. **SCImago Journal Rank (SJR) vs. JCR**:
   - Journal quartiles are derived from the historical **SCImago Journal Rank (SJR)** database (1999–2025), which is openly verifiable and derived from Elsevier's Scopus index.
   - Journal Citation Reports (JCR / Impact Factor) is proprietary to Clarivate Analytics and requires commercial subscription access. While SJR and JCR quartiles correlate heavily (>85% agreement), differences can occur in borderline category assignments.
   - For 2026 publications, quartiles were assigned using the most recent available SJR snapshot (2024/2025 release) because 2026 SJR scores are calculated retrospectively in mid-2027.

2. **Conference Rankings (CORE)**:
   - The CORE ranking portal is designed primarily for Computer Science conferences (A*, A, B, C).
   - In chemical sciences and electrochemical engineering, conferences typically do not participate in CORE ranking systems. As expected, over 98% of conference proceedings in our domain are unranked in CORE. This is a domain characteristic, not missing data.

---

## 3. Author Disambiguation & Faculty Identification

1. **Faculty vs. Affiliated Researchers**:
   - The official staff directories of CSIR-NCL, CSIR-IICT, and CSIR-CECRI list **scientific cadre personnel** (Scientist, Senior Scientist, Principal Scientist, Senior Principal Scientist, Chief Scientist, and Directors).
   - Junior Research Fellows (JRF), Senior Research Fellows (SRF), Ph.D. students (AcSIR), postdocs, and project staff author a substantial proportion of laboratory publications. In our dataset, each row represents an author-paper pair; affiliated non-cadre authors are retained with `author_role = affiliated_author`, while cadre scientists are linked via `faculty_id`.
   - Scientists who retired or moved institutions prior to October 2026 are categorized as `probable_former_faculty`.

2. **Name Ambiguities in Indian Naming Conventions**:
   - Indian academic author strings frequently use varied initial orders (e.g. `S. Sivaram` vs `Sivaram Swaminathan`, or `Babu, K.` vs `K. Babu`).
   - Disambiguation utilized phonetic and token-sorted fuzzy matching alongside OpenAlex canonical author IDs (`author_id`) and institutional co-occurrence to minimize both split-identity and merged-identity errors.

---

## 4. Citation Metrics & Network Limitations

1. **Citation Truncation and Time Window**:
   - Citation metrics (`citations` / `cited_by_count`) reflect lifetime citations accrued up to the date of data extraction (October 2026).
   - They are not field-normalized (e.g., fractional citation counting or RCR). Chemical synthesis papers typically accrue citations over longer cycles (3–5 years) compared to rapid biomedical literature.

2. **Cross-Institute and Indian Connections**:
   - Flags `cites_indian_inst` and `cited_by_indian_inst` use in-corpus links plus links to/from Indian-affiliated papers outside the corpus (OpenAlex `cited_by:` / `cites:` with `authorships.countries:IN`, queried 20 Oct 2026, core corpus). Only papers with a DOI are kept in `citation_network.csv` and counted. "Indian" relies on OpenAlex institution country codes; authorships without an institution ID are not counted. The citing-paper pull is one week newer than the 13 Oct `citations` column, so 23 papers show slightly more Indian citing papers than their `citations` value. Two citing papers carry impossible publication years in OpenAlex (1970, 2008) and are kept as recorded.
   - Partner sectors (IIT, CSIR, DAE, …) in `cross_cluster_*.csv` are assigned from institution names (`src/common/sectors.py`); institutions matching no rule are labelled `Other`, and `StateUniv` covers state and other non-central universities.
   - Topic Jaccard with partner institutions uses the topics of the partner's joint papers within our corpus, not the partner's full output, which was not collected.
   - OpenAlex references coverage is approximately 95% complete for Crossref-indexed publications. Unindexed citations from local or regional non-DOI venues are not captured.

3. **No Summation Across Rows**:
   - Because the required CSV dataset is structured at the **paper × assigned-institute author** level, summing the `citations` column directly over the file will result in multiple counting for co-authored papers. Analysis must always aggregate at the distinct `work_id` or paper level.

## Network analysis

- Authors in `authorship_network.csv` are identified by name (as the instruction note's columns require), so two people with the same name are merged into one node.
- Betweenness centrality is estimated from 1,000 sampled source nodes (seed 42); exact values may differ slightly. Louvain communities use seed 42.
- AcSIR (the degree-granting academy for CSIR students) and CSIR headquarters appear as partner institutions when OpenAlex lists them; they are kept as recorded.
- One corpus paper (W4380288032) is no longer returned by OpenAlex (merged or removed after 13 Oct); its outgoing links to outside papers are missing.

## Citation impact ratio

- Citations (13 Oct 2026) accumulate over time while references are fixed, so IR rises with paper age; IR-Q1 papers concentrate in 2016–2021. No age or field normalisation is applied.
- OpenAlex reference lists can be incomplete; 451 papers with no references recorded are excluded from IR shares. Short lists inflate IR: of the 73 papers with IR > 5, 16 have fewer than 10 references in OpenAlex (e.g. a 2017 review listed with 2 references, IR 287); they are flagged in `impact_ratio_high_papers.csv` and on the dashboard.
- The IR-Q1 threshold (0.60) is relative to this corpus (its 75th percentile), not an absolute standard. The fixed thresholds IR > 5 and IR > 10 select 0.53% and 0.13% of papers.

---

## 5. Non-Obvious Insights (Bibliometric & Network Analyses)

1. **Career Abroad Spell Inferences (Brain Circulation)**:
   - Returnee classification is inferred from institutional affiliation country codes on pre-CSIR publication records in OpenAlex `/authors` career histories. If an overseas postdoctoral spell produced no indexed publications, or if publisher metadata omitted institutional affiliations, the spell cannot be observed from OpenAlex alone. A 30-scientist sample was exported to `stats/tables/insights/09_validation_sample.csv` for manual validation against laboratory profile pages.
2. **COVID-19 Publication Lag & Hardware Dependence**:
   - Journal publications lag the research by months, so 2020 output mostly reflects pre-pandemic work. CSIR-CECRI was 22.3% below its 2016–19 trend in 2020 and 33.9% in 2021, while IICT and NCL were above theirs; the linear trend extrapolates the 2016–19 decline (steep for IICT), so per-lab gaps depend strongly on that trend. No cause is inferred.
3. **Roster cleanup (D-25)**: technical staff listed on the IICT staff pages and three wrong OpenAlex matches were removed from the faculty roster by Step 19 (`config/overrides/roster_overrides.csv`, `data/review/roster_excluded.csv`). The roster is still the website roster as of October 2026: scientists who left earlier are only flagged as probable former faculty, and further matching errors may remain.
4. **Returnee classification is unvalidated** until `true_class` is filled in `stats/tables/insights/09_validation_sample.csv`.
5. **Insight co-author graph vs Task 4 network**: Insights 1–3 and 11 use a co-author graph keyed by OpenAlex author ID (7,752 researchers in the LCC); the Task 4 authorship network in the report and dashboard is keyed by name. Their node counts and centralities therefore differ slightly.
6. **Rows without an author ID**: the 1,579 dataset rows without an OpenAlex author ID all carry `faculty_id = FORMER_CECRI_0005` (936 different names), an artefact of the probable-former-faculty step. These rows are not roster faculty and do not affect faculty statistics, but `FORMER_CECRI_0005` should not be read as one person.
7. **Insight 11 is a stylised model**: β0 = 0.20 per step is chosen, not estimated, and the networks merge 2016–2026 into one static network. SI spreading has no threshold (any β > 0 eventually reaches the connected network); the structural thresholds reported (⟨k⟩/⟨k²⟩, 1/λmax) apply to spreading with recovery, and the measured SIR threshold is 1.5–2.6× the configuration-model formula because the networks are clustered (D-38). The comparison between networks, fields, conditions and labs is the result, not the absolute speed.


## Global benchmark (D-35)
- Peers are the most similar government institutes by research mix, not identical organisations; US national labs publish much more physics and materials science, so their similarity to the CSIR labs is lower and no US or Australian institute is close enough to CSIR-IICT.
- Rule 2b (stand-alone institutes) and the similarity floor 0.4 are judgment calls; every exclusion is listed with its reason.
- All benchmark numbers come from raw OpenAlex queries (affiliation-based, whole counting). OpenAlex affiliation quality varies between institutes; a unit that was renamed or split can show an artificial drop (e.g. CSIRO Manufacturing's output falls by more than half between 2016 and 2025).
- Top 10% / top 1% shares for the most recent years are less settled because recent papers have had little time to be cited.
- Citation flows use the labs' curated papers (2016–2026) but count any peer paper, so they are not restricted to the scope; papers co-authored by the lab and the peer are left out of the flows.
