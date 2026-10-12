Instructor: **Chittaranjan Hens** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

# **DPCN Research Mapping Project** 

Instruction Note for All Groups  ·  2026 

|Instructor|Issued|Groups|Institutions|
|---|---|---|---|
|**Chittaranjan Hens**|**Academic Year 2026**|**30 Independent Groups**|**43+ Covered**|



## **1.  Overview** 

This course project maps the research output of **43+ Indian institutions** spanning IITs, IIITs, NITs, Central Universities, IISERs, CSIR labs, and DAE institutes over **2016–2026** . Each of the **30 independent groups** is responsible for four deliverables: a raw dataset, a statistics report, an interactive dashboard, and network analysis files. 

<mark>⚠</mark> **<mark>Key Rule:</mark>** <mark>All groups work fully independently. No data sharing between groups. The professor collects every output at the end. If two or three groups wish to collaborate, please inform the instructor</mark> **<mark>immediately</mark>** <mark>.</mark> 

## **2.  Four Core Tasks** 

**1.  Data Collection:** Fetch all faculty publications (2016–2026) for your 2–3 assigned institutions using OpenAlex, IRINS, or Scopus. Export to CSV with the column structure specified in Section 5. 

**2.  Statistics Report:** Analyse the dataset and compute key metrics at faculty, department, and institution level (publication trend, Q1 fraction, h-index distribution, top journals, citation counts, etc.). 

**3.  Interactive Dashboard:** Build and submit an interactive dashboard that displays all results for your assigned institutions. Required panels are listed in Section 4. 

**4.  Network Analysis:** Build and submit citation and authorship network files for your assigned institutions. Details in Section 6. 

**<mark>New in 2026:</mark>** <mark>Citation Networks and Authorship Networks are now required deliverables (Week 2). See Sections 6 and 7 for full specifications.</mark> 

## **3.  Group Assignments** 

Each group is assigned 2–3 institutions from the same cluster (see the PPT). 

|**Groups**|**Cluster**|**Institutions Covered**|
|---|---|---|
|**Groups 1–4**|**Old & large IITs**|IIT Bombay, Madras, Delhi, Kanpur, Kharagpur, Roorkee, Guwahati, Hyderabad|
|**Groups 5–8**|**Newer IITs (3–4 per group)**|IIT Gandhinagar, Jodhpur, Patna, BHU Varanasi, Indore, Mandi, Bhubaneswar,<br>Tirupati, Jammu, Goa, Palakkad, Dharwad, Bhilai|
|**Groups 9–11**|**IIITs**|IIIT Hyderabad, Delhi, Allahabad, Bangalore, Gwalior, Jabalpur, Pune,<br>Kancheepuram|
|**Groups 12–15**|**NITs**|NIT Trichy, Surathkal, Warangal, Rourkela, Calicut, Kurukshetra, Durgapur,<br>Bhopal, Jamshedpur, Silchar|



_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 1 _of_ 6 

Instructor: **Chittaranjan** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

**Hens** 

|**Groups 16–17**|**Central Universities**|JNU, Hyderabad Central, University of Delhi, BHU, Jadavpur, Jamia Millia Islamia|
|---|---|---|
|**Groups 18–20**|**IISc · TIFR · IISERs**|IISc, TIFR Mumbai, IISER Pune, Kolkata, Bhopal, Mohali, Thiruvananthapuram|
|**Groups 21–23**|**Premier Science Institutes**|ISI (all campuses), IMSc, CMI, HRI, NCBS, SNBose, Bose Institute, SINP|
|**Groups 24–26**|**CSIR Chemistry & Physics**<br>**Labs**|NCL, IICT, CECRI, CFTRI, NIIST, NML, NPL, CSIO, CGCRI|
|**Groups 27–28**|**CSIR Engineering Labs**|CMERI, CRRI, CIMFR, CBRI, CEERI, SERC, AMPRI, CDRI|
|**Groups 29–30**|**CSIR Biology · DAE**<br>**Institutes**|CCMB, IGIB, IMTECH, BARC, IGCAR, RRCAT, NISER|



**Newer IITs:** Cross-check institute website for faculty who joined before 2018 — OpenAlex coverage may be thin. **<mark>ISI / IMSc / HRI (Groups 21–23):</mark>** <mark>Use the ROR ID directly (e.g. ror.org/01an7q238 for ISI) to avoid wrong-institution matches.</mark> 

## **4.  Dashboard — Required Panels** 

Your interactive dashboard must include at least these panels for each assigned institution: 

- **Publication trend chart:** Line or bar chart — papers per year, 2016–2026 

- **Faculty list:** Name, department, h-index, total papers 

- **Journal quartile distribution:** Stacked or pie chart — Q1 / Q2 / Q3 / Q4 share 

- **Faculty performance table:** Sortable — papers, citations, top journal, h-index 

- **Top journals:** Top 5 journals per institution by paper count 

- **h-index distribution:** Histogram of faculty h-index values 

- **Research area breakdown:** Publication share by domain / field 

- **Most-cited papers:** Top 10 — title, journal, year, citation count, DOI 

- **Conference rank (where applicable):** CORE A* / A / B / C breakdown 

- **Citation network visualisation:** Interactive directed graph — nodes = papers, edges = citations (NEW) 

- **Authorship network visualisation:** Interactive undirected graph — nodes = authors, edges = co-authorship (NEW) 

## **5.  Dataset — CSV Column Structure** 

Submit one CSV file per group, named **groupN_data.csv** (e.g. group12_data.csv). The file must include all of the following columns: 

|**Column Name**||**Description**|
|---|---|---|
|**group**|Your group number||
|**institution**|Assigned institution name||
|**author**|Faculty / author full name||
|**title**|Paper / article title||
|**year**|Publication year (2016–2026)||
|**type**|journal  or  conference||
|**journal_name**|Journal or conference name||



_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 2 _of_ 6 

Instructor: **Chittaranjan** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

**Hens** 

|**issn**<br>ISSN (journals only)|
|---|
|**doi**<br>DOI URL|
|**citations**<br>Citation count at collection date|
|**quartile**<br>Q1 / Q2 / Q3 / Q4 or CORE A*/A/B/C|
|**coauthor_institutes**<br>Semicolon-separated list of co-author institutions (for Indian connections)|
|**cites_indian_inst**<br>TRUE if paper cites a paper from another Indian institution|
|**cited_by_indian_inst**<br>TRUE ifpaper is cited byanother Indian institution|
|**Indian connection note:**The three new columns (coauthor_institutes, cites_indian_inst, cited_by_indian_inst)<br>capture cross-institute links in your raw data. Your_statistical analysis_must remain within your assigned institutions<br>only.|



## **6.  Citation Networks & Authorship Networks  (Task 4)** 

Every group must now build and submit two network files alongside the main dataset. Both are due in Week 2. 

### **6a.  Citation Network** 

A directed graph where each node is a paper and each edge means "paper A cites paper B". Build it from your dataset's DOIs and citation data. 

- **Extract paper-cites-paper pairs from OpenAlex (referenced_works field) or Scopus** 

- **Compute in-degree per paper:** = cited-by count within your institution's corpus 

- **Compute PageRank:** to find the most influential papers in your cluster 

- **Map citation flow:** into and out of your assigned institutions from/to other Indian institutes 

- **Identify cross-institute citation edges:** flag them in your raw CSV (cites_indian_inst column) 

- **Export as edge-list CSV:** columns: source_doi, target_doi, source_inst, target_inst, year 

- **Visualise:** directed network graph using Gephi, NetworkX, or D3.js 

### **6b.  Authorship Network** 

An undirected graph where each node is a faculty member and each edge means "these two people co-authored a paper". Extract from your paper data. 

- **Extract co-author pairs from every paper in your dataset** 

- **Build an undirected graph:** nodes = authors, edges = co-authorship events 

- **Compute degree centrality:** = most collaborative faculty at your institutions 

- **Compute betweenness centrality:** = faculty who bridge otherwise disconnected groups 

- **Apply community detection:** Louvain or Leiden algorithm to find collaboration clusters 

- **Flag cross-institution edges:** these are the Indian inter-institute connections 

- **Export as edge-list CSV:** columns: author_a, author_b, paper_doi, inst_a, inst_b, year 

- **Visualise:** collaboration clusters using Gephi or NetworkX 

## **7.  Indian Connectivity: Citation Flow & Raw Data** 

_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 3 _of_ 6 

Instructor: **Chittaranjan Hens** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

This section captures how your institutions are embedded in the broader Indian research network — who cites you, who you cite, and who your faculty collaborate with. 

### **7a.  Citation Flow** 

- **Count citations received from other Indian institutes (in-flow)** 

- **Count citations given to other Indian institutes (out-flow)** 

- **Identify the top 10 Indian institutes citing your institution's work** 

- **Compute citation impact ratio:** In-cites / Out-cites per institution 

- **Produce a year-wise citation flow chart (2016–2026)** 

### **7b.  Connectivity Map** 

- **List every Indian institution your faculty co-author with** 

- **Rank partner institutions by number of shared papers** 

- **Show co-authorship strength:** number of joint papers per partner institution 

- **Flag cross-cluster links:** IIT ↔ CSIR, IIT ↔ IISER, CSIR ↔ DAE, etc. 

- **Compute Jaccard similarity of research topics between your institutes and partners** 

### **7c.  Network Files to Submit** 

Submit these three additional files with your Week 2 dataset delivery: 

|**Filename**|**Required Columns**|**Description**|
|---|---|---|
|**citation_network.csv**|source_doi, target_doi, source_inst, target_inst,<br>year|Directed edges — paper A cites paper B|
|**authorship_network.csv**|author_a, author_b, paper_doi, inst_a, inst_b,<br>year|Undirected co-authorship edges|
|**indian_connections.csv**|your_inst, partner_inst, shared_papers,<br>total_citations|Aggregated cross-institute links|



**<mark>Scope reminder:</mark>** <mark>Build and analyse networks WITHIN your assigned institutions. Include cross-institute edges in the raw files only. Do not merge your data with another group's data.</mark> 

## **8.  Statistics Report** 

Submit a short report — **maximum 10 slides or 5 pages** — covering your assigned institutions at faculty, department, and institution level. It must address: 

- **Publication trend (2016–2026):** total and per-year breakdown 

- **Q1 fraction per institution:** percentage of papers in Q1 journals 

- **h-index distribution of faculty** 

- **Top 5 journals for each institution** 

- **Most-cited papers (top 10)** 

- **Research area breakdown** 

- **Citation network summary:** PageRank top-10, in-degree distribution, cross-institute flow (NEW) 

- **Authorship network summary:** degree & betweenness centrality, community structure (NEW) 

_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 4 _of_ 6 

Instructor: **Chittaranjan Hens** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

## **9.  Recommended Tools & Sources** 

- **OpenAlex:** Primary source for publications & cited_by data (API: openalex.org) 

- **IRINS:** Indian Research Information Network — useful for institutional coverage 

- **Scopus:** Secondary source for quartile and citation data 

- **ROR IDs:** Use institution ROR IDs for accurate OpenAlex queries (esp. ISI, TIFR, CSIR) 

- **Scimago / JCR:** Journal quartile (Q1–Q4) lookup 

- **CORE Portal:** Conference rank (A* / A / B / C) 

- **NetworkX (Python):** Build, analyse, and export citation & authorship networks 

- **Gephi:** Desktop network visualisation and community detection (Louvain) 

- **D3.js / Cytoscape.js:** Interactive network visualisation for the dashboard 

## **10.  Submission Timeline** 

|**Deadline**|**Deliverable**|**Details**|
|---|---|---|
|**Week1-2**|**📁  Dataset + Network**<br>**Files**|groupN_data.csv + citation_network.csv +<br>authorship_network.csv + indian_connections.csv|
|**Week 3**|**📁  Report + 📁  Dashboard**|Statistics report (≤10 slides / ≤5 pages) + interactive<br>dashboard including network visualisations|



## **11.  Submission Checklist** 

Before submitting, verify each item: 

- ☐groupN_data.csv named correctly and contains all required columns including three new network columns 

- ☐Data covers years 2016 to 2026 only 

- ☐All assigned institutions are included in the dataset 

- ☐citation_network.csv submitted (source_doi, target_doi, source_inst, target_inst, year) 

- ☐authorship_network.csv submitted (author_a, author_b, paper_doi, inst_a, inst_b, year) 

- ☐indian_connections.csv submitted (your_inst, partner_inst, shared_papers, total_citations) 

- ☐Statistics report does not exceed 10 slides or 5 pages (use dahborad) 

☐Report covers all required metrics + citation & authorship network summaries 

- ☐Dashboard includes network visualisation panels (citation graph + co-authorship graph) 

- ☐All deliverables submitted to the professor — no sharing with other groups 

- ☐If collaborating with another group — instructor has been notified in advance 

Questions? Contact the instructor — **Chittaranjan Hens** — through the course communication channel. 

_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 5 _of_ 6 

Instructor: **Chittaranjan Hens** 

**DPCN Course Project 2026** ·  Research Mapping across Indian Institutions 

_All group outputs go directly to the professor. No inter-group data sharing is required or permitted._ 

_DPCN Course · 2026 · Instructor: Chittaranjan Hens  ·  Page_ 6 _of_ 6 

