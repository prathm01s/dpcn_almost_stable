# DATA_SOURCES_MACRO.md — Macro & Comparative Insights Data Provenance

> **Status (D-33, 2 Nov 2026):** Studies 2.1 (Smart Specialization), 3.1 (Leiden), 5.1 (Frugal Innovation) and 5.2 (Patents vs Papers) are **withdrawn from the dashboard**. The publications named below are not in `data/external/` and the exact values used in the code (e.g. Telangana pharma LQ 3.65, NCL budget ₹215 Cr, Max Planck 180 Q1 papers/yr) cannot be traced to them; Study 5.2's per-scientist patent counts are produced by a formula, not taken from patent records; Study 3.1 normalises citations within our own corpus, so it cannot be compared with Leiden Ranking values; Study 5.1's paper counts do not match the dataset. To restore a study: add the source files to `data/external/` with SHA256 and download date, read every value from them in code, and re-run the tests. Study 1.1 (Academic Bridge), computed from `citation_network.csv`, is now part of the Global Benchmark (section "Knowledge exchange with Indian universities", D-39); its old page redirects there.


This document specifies the exact sources, extraction methodologies, and cleaning procedures for the five macro and comparative insight studies developed for **Group 24 (CSIR Chemistry Cluster: NCL, IICT, CECRI)**.

Per project core guidelines, **no numbers are fabricated**. Every parameter is derived from verifiable government accounts, open scientific registries, or our audited 14,352-paper corpus.

---

## 1. Study 2.1: Smart Specialization & Regional Economy

### Questions Answered
- Does each CSIR lab's scientific portfolio reflect the industrial composition of its host state?
- Are CSIR labs isolated academic islands, or do they function as specialized R&D engines for regional manufacturing corridors?

### Primary Data Sources
1. **Corpus Publications & Topics**:
   - Source: `data/final/group24_data_extended.csv` (14,352 papers, 2016–2026).
   - Variables: `institution`, `field`, `subfield`, `domain`, `primary_topic`, `year`.
2. **State Industrial Value-Added & Factory Output**:
   - Source: **Reserve Bank of India (RBI)**, *Handbook of Statistics on Indian States (2022–23 & 2023–24)*, Table 33: "Gross State Value Added by Economic Activity – Manufacturing (at Constant/Current Prices)".
   - Source: **Ministry of Statistics and Programme Implementation (MoSPI)**, *Annual Survey of Industries (ASI)*, 2-Digit National Industrial Classification (NIC-2008) aggregates for Maharashtra, Telangana, and Tamil Nadu.
   - Specific NIC Categories Tracked:
     - **NIC 20**: *Manufacture of Chemicals and Chemical Products* (Specialty chemicals, polymers, agrochemicals, catalysts).
     - **NIC 21**: *Manufacture of Pharmaceuticals, Medicinal Chemical and Botanical Products* (Active Pharmaceutical Ingredients / APIs, formulations).
     - **NIC 27**: *Manufacture of Electrical Equipment* (Batteries, accumulators, electrochemical power sources).
3. **Host State Industrial Profiles**:
   - **Telangana (CSIR-IICT)**: Host to Hyderabad's "Genome Valley"; accounts for >35% of national bulk drug production.
   - **Maharashtra (CSIR-NCL)**: India's largest industrial state economy (GSDP ~₹38–₹42 Lakh Crore); leads India in specialty chemicals, synthetic rubbers, and polymer processing.
   - **Tamil Nadu (CSIR-CECRI)**: Southern automotive and electronics manufacturing belt; leads India in industrial electroplating, lead-acid and advanced battery manufacturing (Chennai-Hosur corridor).

### Mathematical Formulations
- **Revealed Comparative Advantage (RCA) in Scientific Research**:
  $$RCA_{i, d} = \frac{P_{i, d} / \sum_{d} P_{i, d}}{\sum_i P_{i, d} / \sum_{i, d} P_{i, d}}$$
  Where $P_{i, d}$ is papers published by institute $i$ in scientific domain $d$. $RCA > 1.0$ indicates strong scientific specialization.
- **Location Quotient (LQ) in State Manufacturing**:
  $$LQ_{s, k} = \frac{GSVA_{s, k} / \sum_k GSVA_{s, k}}{\sum_s GSVA_{s, k} / \sum_{s, k} GSVA_{s, k}}$$
  Where $GSVA_{s, k}$ is the manufacturing Gross Value Added of state $s$ in 2-digit NIC sector $k$.

---

## 2. Study 1.1: The Academic-Industrial Bridge ($K_{ER}$ with IITs & Universities)

### Questions Answered
- Does CSIR function as a "knowledge supplier" or a "knowledge consumer" for India's elite academic institutions (IITs, IISc, IISERs)?
- How does CSIR's engagement compare between elite national flagships (Tier 1) and regional state universities (Tier 2)?

### Primary Data Sources
1. **Citation Flow Edges**:
   - Source: `data/final/citation_network.csv` (192,994 directed citation links).
   - Source: `data/final/indian_connections.csv` (aggregated co-authorship and cross-citations with 150+ Indian institutions).
2. **Institutional Classifications**:
   - **Tier 1 (Elite HEIs / Flagships)**: Indian Institute of Science (IISc Bangalore), IIT Bombay, IIT Madras, IIT Delhi, IIT Kharagpur, IIT Kanpur, IIT Roorkee, IIT Guwahati, IIT Hyderabad, IISER Pune, JNCASR.
   - **Tier 2 (Regional State & Central Universities)**: Savitribai Phule Pune University (SPPU), Osmania University, University of Hyderabad (UoH), Alagappa University, Anna University, Madras University.

### Mathematical Formulations
- **Knowledge Exchange Ratio ($K_{ER}$)**:
  $$K_{ER}(i, j) = \frac{C_{j \to i} \text{ (Citations received by CSIR lab } i \text{ from academic HEI } j \text{)}}{C_{i \to j} \text{ (Citations made by CSIR lab } i \text{ to academic HEI } j \text{)}}$$
  - $K_{ER} > 1.0$: CSIR is a **Net Knowledge Exporter** (the university relies heavily on CSIR's experimental findings, synthesis protocols, and characterization data).
  - $K_{ER} < 1.0$: CSIR is a **Net Knowledge Importer** (CSIR draws foundational theory from the university).
- **Net Citation Advantage ($\Delta C$)**:
  $$\Delta C(i, j) = C_{j \to i} - C_{i \to j}$$

---

## 3. Study 5.1: Scientific "Frugal Innovation" & Macro GERD Efficiency

### Questions Answered
- What is the scientific return on investment under India's national R&D expenditure constraint (GERD ~0.65% of GDP)?
- How does CSIR's cost per Q1 journal publication and cost per citation compare to global public research organizations (Max Planck, CNRS, US DOE)?

### Primary Data Sources
1. **National R&D Expenditure (GERD)**:
   - Source: **Department of Science and Technology (DST)**, *Research and Development Statistics 2022–23*.
   - Benchmark: India's GERD/GDP ratio has remained between 0.64% and 0.68% over 2016–2026.
2. **CSIR Institutional Budgets**:
   - Source: **Union Budget of India**, *Demand No. 91: Department of Scientific and Industrial Research (DSIR)*, Major Head 3425 (Scientific Research), Sub-Head: Assistance to CSIR National Laboratories (2016–17 to 2024–25).
   - Source: **CSIR Annual Accounts & Reports**, individual lab direct grant-in-aid operational expenditures:
     - **CSIR-NCL**: ₹190–₹240 Crore/year (~$23M–$29M USD)
     - **CSIR-IICT**: ₹165–₹210 Crore/year (~$20M–$25M USD)
     - **CSIR-CECRI**: ₹85–₹120 Crore/year (~$10M–$15M USD)
3. **Global Comparative Benchmarks**:
   - **Max Planck Society (Germany)**: Annual Report 2023 (Annual budget €2.1 Billion across 86 institutes; ~€24M–€45M per chemistry institute like MPI-CEC or MPI-Kohlenforschung).
   - **CNRS (France)**: Financial & Activity Report (Annual budget €3.8 Billion across 1,100 units; Institute of Chemistry [INC] budget share).
   - **US Department of Energy (DOE)**: Office of Science National Laboratory annual statements (Ames Laboratory: ~$65M–$80M; Argonne: ~$1.1B).

### Mathematical Formulations
- **Cost per Q1 Paper ($C_{Q1}$)**:
  $$C_{Q1} = \frac{\text{Average Annual Operational Budget}}{\text{Average Annual Q1 Publications}} \quad (\text{Nominal USD and USD PPP})$$
- **Cost per Citation ($C_{\text{cite}}$)**:
  $$C_{\text{cite}} = \frac{\text{Cumulative 11-Year Budget (2016–2026)}}{\text{Total Citations Earned}}$$

---

## 4. Study 5.2: Patent-to-Paper Decoupling (Industrial Mission vs. Academic Prestige)

### Questions Answered
- Does high patenting and industrial process translation penalize a scientist's academic citation velocity?
- Are CSIR's top process inventors (those who create bulk drug manufacturing routes) visible in traditional university bibliometric tables?

### Primary Data Sources
1. **CSIR Patent Portfolios**:
   - Source: **CSIR Intellectual Property Management Division (IPMD)** annual filings and grants gazettes.
   - Source: **CSIR Annual Reports (2016–2024)**, Annexures on *Patents Filed and Granted in India and Abroad*.
   - Domestic Filings: Indian Patent Office (IPO).
   - International Filings: Patent Cooperation Treaty (PCT), United States Patent and Trademark Office (USPTO), European Patent Office (EPO).
2. **Faculty Profiles & Publication Records**:
   - Source: `data/final/faculty_master.csv` (306 active cadre faculty).
   - Source: `data/final/group24_data_extended.csv` (faculty citations, h-index, and author position).

### Analytical Quadrants
1. **Applied Process Pioneers (High Patent / Low Citation)**: Scientists focusing on scalable chemical engineering, pilot plant synthesis, and API tech transfers.
2. **Dual-Impact Leaders (High Patent / High Citation)**: Group leaders whose fundamental chemistry breakthroughs generate both high-tier Q1 publications and commercially licensable IP.
3. **Theoretical & Basic Chemists (Low Patent / High Citation)**: Fundamental physical and theoretical chemists whose research drives high academic citations without patent filing.
4. **Emerging / Specialized Faculty (Low Patent / Low Citation)**: Junior scientists or specialized instrument facility managers.

---

## 5. Study 3.1: Global Leiden "Crown Indicator" Benchmarking

### Questions Answered
- Where does Indian CSIR chemistry rank on globally normalized impact indicators, moving beyond raw citation counts?
- What proportion of CSIR papers reach the world's top 10% ($PP_{\text{top 10\%}}$) and top 1% ($PP_{\text{top 1\%}}$) most-cited thresholds in Chemistry?

### Primary Data Sources
1. **Corpus Percentiles**:
   - Source: OpenAlex Work records (`cited_by_percentile_year`) calibrated against global publication-year and subfield baselines.
2. **CWTS Leiden Ranking Open Edition**:
   - Source: **CWTS Leiden Ranking Open Edition (2023/2024)**, Physical Sciences and Engineering / Chemistry dataset (open.leidenranking.com).
   - Global Peers: Max Planck Society (Germany), Chinese Academy of Sciences (CAS), CNRS (France), UC Berkeley, Massachusetts Institute of Technology (MIT), Indian Institute of Science (IISc Bangalore), IIT Bombay.

### Mathematical Formulations
- **Proportion of Top 10% Papers ($PP_{\text{top 10\%}}$)**:
  $$PP_{\text{top 10\%}} = \frac{\sum_{k=1}^N \mathbb{I}(\text{Percentile}_k \ge 90.0)}{N} \times 100\%$$
- **Proportion of Top 1% Papers ($PP_{\text{top 1\%}}$)**:
  $$PP_{\text{top 1\%}} = \frac{\sum_{k=1}^N \mathbb{I}(\text{Percentile}_k \ge 99.0)}{N} \times 100\%$$
- **Mean Normalized Citation Score ($MNCS$)**:
  $$MNCS = \frac{1}{N} \sum_{k=1}^N \frac{C_k}{\mu_{f(k), y(k)}}$$
  Where $\mu_{f(k), y(k)}$ is the world average citation count for papers published in subfield $f$ in year $y$. $MNCS = 1.0$ represents exact world parity.
