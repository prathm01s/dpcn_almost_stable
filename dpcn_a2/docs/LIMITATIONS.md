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
- OpenAlex reference lists can be incomplete; 513 papers with no references recorded are excluded from IR shares.
- The IR-Q1 threshold (0.59) is relative to this corpus (its 75th percentile), not an absolute standard; fixed thresholds such as 5 or 10 would select < 1% of papers.

---

## 5. Non-Obvious Insights (Bibliometric & Network Analyses)

1. **Sleeping Beauties Window & Censoring**:
   - Sleeping beauty detection uses the Ke et al. (2015, *PNAS*) beauty coefficient $B$ on complete years 2016–2025 (2026 is partial), for papers published 2016–2020 with ≥20 citations and ≥10 citations in the peak year. With at most 10 years of history only short sleeps are visible, and B rewards any late peak, so a 'sustained' check (≥50% of the peak rate after the peak) separates real awakenings from 1–2-year spikes.
2. **Career Abroad Spell Inferences (Brain Circulation)**:
   - Returnee classification is inferred from institutional affiliation country codes on pre-CSIR publication records in OpenAlex `/authors` career histories. If an overseas postdoctoral spell produced no indexed publications, or if publisher metadata omitted institutional affiliations, the spell cannot be observed from OpenAlex alone. A 30-scientist sample was exported to `stats/tables/insights/09_validation_sample.csv` for manual validation against laboratory profile pages.
3. **Faculty Retirement & Succession Risk Proxy**:
   - CSIR institute scientific directories do not publish researcher birthdates or retirement dates. Academic age ($\text{Collection Year} - \text{Year of First Recorded Publication}$) serves as a proxy ($\ge 30$ years indicates probable retirement within 5 years). Sensitivity tests at thresholds 28 and 32 years confirmed that divisional risk rankings remain robust across definitions.
4. **COVID-19 Publication Lag & Hardware Dependence**:
   - Journal publications lag the research by months, so 2020 output mostly reflects pre-pandemic work. CSIR-CECRI was 22.3% below its 2016–19 trend in 2020 and 33.9% in 2021, while IICT and NCL were above theirs; the linear trend extrapolates the 2016–19 decline (steep for IICT), so per-lab gaps depend strongly on that trend. No cause is inferred.
5. **Roster cleanup (D-20)**: technical staff listed on the IICT staff pages and three wrong OpenAlex matches were removed from the faculty roster by Step 19 (`config/overrides/roster_overrides.csv`, `data/review/roster_excluded.csv`). The roster is still the website roster as of October 2026: scientists who left earlier are only flagged as probable former faculty, and further matching errors may remain.
6. **Returnee classification is unvalidated** until `true_class` is filled in `stats/tables/insights/09_validation_sample.csv`.
