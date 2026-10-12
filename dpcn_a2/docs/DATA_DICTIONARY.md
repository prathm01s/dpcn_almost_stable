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
| 13 | `cites_indian_inst` | String | `TRUE`, `FALSE` | Uppercase boolean string indicating whether this paper references at least one paper authored by a researcher at an Indian institution. | OpenAlex `referenced_works` institutions lookup |
| 14 | `cited_by_indian_inst` | String | `TRUE`, `FALSE` | Uppercase boolean string indicating whether this paper is cited by at least one paper authored by a researcher at an Indian institution. | OpenAlex `/works?filter=cites:<WID>` institutions lookup |

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

1. **`data/final/faculty_master.csv`**: Comprehensive directory of 505 scientific cadre scientists from official staff directories across NCL, IICT, and CECRI with in-corpus publication counts, citation totals, and career/corpus h-indices.
2. **`data/final/citation_edges_raw.parquet`**: 27,824 directed citation edges `(source_work_id -> target_work_id)` connecting corpus papers with citing/referenced works, partitioned and prepared for Task 4 network analysis.
3. **`data/final/works_table.parquet`**: Deduplicated paper-level dataset (14,357 works) containing full topic hierarchies, biblio details, and open access status.
4. **`config/indian_inst_registry.csv`**: 911 mapped Indian academic and research institutions with canonical display names, ROR IDs, state, city, and research sector classification (CSIR, IIT, IISc, NIT, Central Universities, etc.).
