# DPCN Research Mapping Project 2026 — Group 24 Final Submission Package
### CSIR Chemistry Cluster ("Synthetic & Organic Chemistry")
**Instructor**: Chittaranjan Hens · **Course**: DPCN 2026 · **Collection Date**: 13 October 2026  
**Institutions Covered**: CSIR-NCL (Pune), CSIR-IICT (Hyderabad), CSIR-CECRI (Karaikudi)

---

## 1. Package Inventory & Verification

This directory contains the complete, authoritative submission deliverables for **Group 24**:

| Deliverable File | Size | Description |
|---|---|---|
| `group24_data.csv` | ~12 MB | **Task 1 Primary Dataset**: 42,406 rows, exactly 14 required columns in canonical order. Deduplicated, 2016–2026, UTF-8 BOM-free, zero data fabrication. |
| `group24_data_extended.csv` | ~26 MB | **Extended Dataset**: Same rows with 35 rich metadata columns including OpenAlex IDs, topics, OA status, and all-country affiliations. |
| `citation_network.csv` | 2.9 MB | **Task 4 Citation Network Edge List**: 27,816 directed citation edges (`source_doi, target_doi, source_inst, target_inst, year`). |
| `authorship_network.csv` | 6.5 MB | **Task 4 Co-Authorship Network Edge List**: 65,059 undirected collaboration edges (`author_a, author_b, paper_doi, inst_a, inst_b, year`). |
| `indian_connections.csv` | 74 KB | **Task 4 Indian Partner Connectivity**: 1,487 aggregated cross-institute collaboration links (`your_inst, partner_inst, shared_papers, total_citations`). |
| `faculty_master.csv` | 101 KB | **Cadre Faculty Roster**: 505 verified scientific cadre personnel with OpenAlex career and 2016–2026 in-corpus h-indices. |
| `group24_stats_report.pdf` | 1.9 MB | **Task 2 Statistics Report (PDF)**: Strictly $\le 10$ slides conforming to assignment length limit. |
| `group24_stats_report.pptx` | 2.0 MB | **Task 2 Presentation Slides (PPTX)**: Editable 10-slide PowerPoint presentation with vector charts. |
| `dashboard.zip` | 3.9 MB | **Task 3 Standalone Interactive Dashboard**: Self-contained offline web application (unzip and open `index.html` directly via double-click), including citation/co-authorship network tabs and the Indian Connectivity tab (citation flow, cross-cluster links, topic Jaccard, hub authors). |
| `MANIFEST.json` | 2.1 KB | Cryptographic run manifest with collection timestamp, counts, and metadata. |
| `CHECKSUMS.sha256` | 868 B | SHA-256 cryptographic checksums for all files in this bundle. |

---

## 2. Integrity Verification
To verify the cryptographic integrity of all submission artifacts:
```bash
sha256sum -c CHECKSUMS.sha256
```

---

## 3. How to Open the Interactive Dashboard
1. Unzip `dashboard.zip` if inspecting outside the repository:
   ```bash
   unzip dashboard.zip -d dashboard_standalone
   ```
2. Double-click `dashboard_standalone/index.html` (or `dashboard/index.html` in the repository root) to open in any web browser.
3. The dashboard executes **100% offline** via `file://` protocol with zero external server or CDN dependencies.
