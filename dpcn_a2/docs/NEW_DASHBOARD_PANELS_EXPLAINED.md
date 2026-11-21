# The four new dashboard panels, explained and checked

Added by commits `1b48319`, `ecb4a22` (D-42, 15 Nov 2026) and `2f599d2` (Section 10, "Advanced Bibliometrics & Specialization Hub"). Checked on 17 Nov 2026 against `data/final/` and `stats/tables/`.

Each panel below has four parts:
- **what it shows**;
- **how it is computed**, with the code and files;
- **how to read it**;
- **what is wrong or misleading**.

Every number in the last part was recomputed from the repository's data. Nothing here needs the OpenAlex API.

## Summary

| Panel | Numbers | Wording | Must fix before presenting |
|---|---|---|---|
| 1. Institutional radar (Section 02) | Correct (one small count error) | Several claims go beyond the data | The "Benchmark Max" values are scaling caps someone chose, not benchmarks. |
| 2. Self-citation dynamics (Section 10) | **Wrong** | The takeaway is not supported | The "citations by others" series includes the labs' own outgoing references. The "Author Scope" button multiplies by an invented 0.38. |
| 3. Faculty productivity vs impact scatter (Section 10) | Correct | Quadrant names overstate | The legend colours clash with the bubble colours. |
| 4. Disciplinary radial profile (Section 10) | **Wrong** | The specialization paragraph is not supported | Side-box numbers are typed into the code. Three of them are IICT's figures shown as the whole cluster. "All Labs" counts every paper twice. 97.5% has no source in the data. |

Two of these break the project rule "never fabricate data" (AGENTS.md):
- the 0.38 factor in panel 2;
- the typed-in numbers in panel 4.

They should be fixed or removed before the dashboard is submitted.

---

## 1. Institutional Comparative Profile (spider / radar chart)

### What it shows

Each lab is a coloured polygon on six axes. The further a corner sits from the centre, the higher the lab scores on that axis. The table to the right gives the raw values.

### How it is computed

The calculation is in `src/stats/metrics.py: compute_institutional_radar`, and its output is `stats/tables/institutional_radar.csv`.

| Axis | Formula | Source file | IICT | NCL | CECRI | Checked |
|---|---|---|---|---|---|---|
| Q1 Journal Ratio | papers in a SCImago Q1 journal ÷ all papers | `phase2_overview.csv` | 51.3% | 64.2% | 70.0% | Yes |
| Internationalization | papers with at least one foreign co-author ÷ all papers | `phase2_overview.csv` (`intl_papers_pct`) | 22.1% | 18.2% | 30.4% | Yes |
| Mean Citations | OpenAlex citation count, averaged over the lab's distinct papers (2016–2026) | `group24_data.csv` | 20.5 | 25.2 | 32.4 | Yes |
| Top-10% Excellence | share of the lab's papers in the world's top 10% for their field and year (OpenAlex `citation_normalized_percentile`) | `global_summary.csv` (Global Benchmark) | 8.9% | 12.3% | 17.3% | Yes |
| Network Centrality | betweenness of the lab in a 63-node co-authorship network: the 3 labs plus their 60 most frequent partner institutions | `phase2_institution_network_nodes.csv` | 0.0786 | 0.0681 | 0.0486 | Yes |
| Industry Linkage | number of papers co-authored with an **Indian** company | `cross_cluster_summary.csv`, sector "Industry" | 53 | 81 | 8 | IICT is 52 distinct papers; 53 counts company–paper pairs |

**How the polygon is drawn.** Each raw value is divided by the "Benchmark Max" column and shown as a percentage of the axis length:
- Q1 ÷ 100%
- International ÷ 40%
- Citations ÷ 40
- Top-10% ÷ 25%
- Betweenness ÷ 0.10
- Industry ÷ 100 papers

### How to read each axis

**Q1 Journal Ratio**
- **Means:** how much of a lab's output goes to journals ranked in the top quarter of their category.
- **Does not mean:** quality of individual papers.
- CECRI publishes in fewer, mostly high-ranked electrochemistry and energy journals.

**Internationalization**
- **Means:** the share of papers with at least one co-author from an institution outside India.
- **Does not mean:** how many countries a lab works with.

**Mean Citations**
- **Means:** raw citations per paper.
- **Does not mean:** a fair comparison across fields. It isn't adjusted for field or paper age, and energy and materials papers collect citations faster than organic synthesis papers.
- Use the Top-10% axis for a fair comparison.

**Top-10% Excellence**
- **Means:** the field- and year-adjusted measure, which makes it the fairest impact axis.
- **Compare with:** the measured world share in the same subjects, which is **10.83%** (`global_world_baseline.csv`). IICT (8.9%) is *below* the world level, NCL (12.3%) slightly above, and CECRI (17.3%) well above.

**Network Centrality**
- **Means:** how often a lab sits on the shortest path between two partner institutions in the labs' own partner network.
- **Does not mean:** a measure of the national network. The 63 nodes are only the three labs and their top 60 partners, and the list includes foreign partners such as RMIT.
- IICT scores exactly the same as AcSIR and the CSIR headquarters (0.0786): all three are linked to all 62 other nodes.

**Industry Linkage**
- **Means:** an absolute count, so bigger labs get more.
- **As a share of output:** NCL 1.52%, IICT 0.85%, CECRI 0.28%. So 98.5–99.7% of each lab's papers have no Indian company partner.
- **Only Indian companies are counted.** A paper with BASF or Shell Global would be counted under "Foreign", not here.

### Problems

1. **"Values calibrated to natural domain benchmarks"** isn't true. The caps (40%, 40 citations, 25%, 0.10, 100 papers) were chosen to make the chart fill nicely; they don't come from any external benchmark. Change the caption to "each axis scaled to a fixed maximum", and rename the column from "Benchmark Max" to "Axis max".
2. **The shape depends on those caps.** With a cap of 50 papers, NCL's industry corner would hit the edge; with 200 it would shrink by half. Don't compare polygon areas.
3. **IICT industry count:** 52 distinct papers, not 53.
4. **Wording in the three "specialization" cards:**
   - "Citation velocity" means citations per year. The axis is citations per paper.
   - "Global citation tailwinds in clean electrochemical energy storage" is an interpretation; nothing in the data measures it.
   - "Anchors the national research network as the primary structural bridging hub" overstates a 63-node partner network in which IICT ties with AcSIR and CSIR headquarters.
   - "Deep pharmaceutical … translation" rests on 52 papers (0.85%). The partners named are right (GVK, Cipla, Dr. Reddy's), but "deep" isn't.
   - For NCL, the partners Reliance (17 papers), TCS (10) and Praj (6) are correct.
5. **CECRI is smaller.** It has 2,870 papers, against 6,123 for IICT and 5,316 for NCL. Shares are fair across labs of different sizes; counts are not.

---

## 2. Self-Citation Dynamics & Knowledge Diffusion

### What it shows

**Five KPI cards:**

| Card | Value |
|---|---|
| Total network citations | 192,418 |
| Self-citations | 37,614 |
| Overall self-citation rate | 19.55% |
| Average per year | 3,420 |
| Per paper | 2.65 |

**Two charts:**
- a stacked bar of "self" against "citations by others" per year;
- the self-citation percentage per year, falling from 30.32% in 2016 to 12.68% in 2026.

### How it is computed

The calculation is in `src/stats/metrics.py: compute_self_citation_summary`, and its output is `stats/tables/self_citation_summary.csv`. The steps:
1. Take every row of `data/final/citation_network.csv` with a year of 2016–2026.
2. Call a row "self" when the citing paper's lab equals the cited paper's lab.
3. Group the rows by the **citing** paper's year.

So "self-citation" here means **institutional** self-citation: an NCL paper citing an NCL paper. It does not mean an author citing their own work.

### What `citation_network.csv` actually contains

The file is not "all citations". It holds three kinds of rows:

| Kind of row | Rows (2016–2026) | In the panel's "All Labs" view |
|---|---|---|
| A lab paper citing another paper of the same lab | 37,614 | "Self" |
| A lab paper citing a paper of another of the three labs | 3,016 | "Citations by others" |
| An **Indian** paper from outside the three labs citing a lab paper | 76,963 | "Citations by others" |
| A lab paper **citing** an outside Indian paper (an outgoing reference) | 74,825 | "Citations by others" ← wrong |

Citations from foreign papers aren't in the file at all. For scale, OpenAlex counts **350,015** citations received by the labs' 14,208 papers.

### Problems

1. **The "All Labs" view counts outgoing references as citations received.** 74,825 of the 154,804 "citations by others" (48%) are the labs citing other people. In 2016, 7,134 of the 7,650 "external" rows go the wrong way.
2. **The two series cover different windows** (the same kind of error that D-40 fixed in the Global Benchmark):
   - "Self" includes 11,222 citations to the labs' own papers from **before** 2016.
   - Outside citations can only point at 2016–2026 papers, because only those were queried.
3. **Only Indian citing papers are counted.** Foreign citations, roughly two-thirds of everything the labs receive, are missing. That inflates the self share.
4. **The falling trend is mostly paper age, not "maturation".** A paper's first citations come mostly from its own group; outsiders arrive later. The panel's "2016" bar can only count citations to papers that are at most a few months old, while a "2025" bar counts citations to papers up to nine years old.
5. **The "Author Scope" button is made up.** It multiplies the institutional self-citation counts by a fixed **0.38** (`dashboard/js/app.js`, `const factor = … 0.38`). No author-level self-citation was computed anywhere. This is invented data and must be removed.
6. **"2.65 self-citations per paper"** divides self-citations, including those to pre-2016 papers, by the number of 2016–2026 papers. It mixes the two windows again.

### The like-for-like numbers

Comparing like with like means counting citations **received** by the labs' 2016–2026 papers, from Indian papers including the labs themselves:

| Lab | Self share of those citations |
|---|---|
| IICT | 29.6% |
| NCL | 22.3% |
| CECRI | 22.2% |
| All three | **25.1%** (of 104,962) |

Against **all** citations OpenAlex records for those papers (350,015), institutional self-citations to 2016+ papers are 26,338, about **7.5%**. That is an ordinary figure for chemistry labs.

The year-by-year like-for-like share still falls, from 62% to 17%. The reason is the age effect in problem 4, not growing outside adoption.

**What the takeaway should say instead:**
> "About a quarter of the citations that the labs' 2016–2026 papers received from Indian papers come from the same lab (7.5% of all their citations). The share falls for later citing years mainly because papers are first cited by their own group and by others later."

---

## 3. Faculty Productivity vs Citation Impact scatter

### What it shows

**The points:**
- One bubble per roster scientist with at least one paper (306).
- **x** = papers at the scientist's roster lab in 2016–2026.
- **y** = total citations to those papers.
- **Bubble size** = h-index.
- **Colour** = lab: blue IICT, green NCL, orange CECRI.

**The quadrants:** the dashed lines are the medians, 17 papers and 192 citations. They split the chart into four groups:

| Quadrant | Rule | Faculty | IICT | NCL | CECRI |
|---|---|---|---|---|---|
| "High-Impact Giants" | ≥ 17 papers and ≥ 192 citations | 141 | 52 | 77 | 12 |
| "High-Efficiency Specialists" | < 17 papers, ≥ 192 citations | 12 | 7 | 4 | 1 |
| "Prolific Contributors" | ≥ 17 papers, < 192 citations | 17 | 10 | 7 | 0 |
| "Emerging Faculty" | < 17 papers, < 192 citations | 136 | 60 | 63 | 13 |

The labelled points are the 8 most cited scientists and the 4 with the most papers.

### How it is computed

`src/stats/metrics.py: compute_faculty_scatter_summary`, built from `stats/tables/faculty_performance.csv`. That table is the one that already feeds the Faculty tab. The medians, counts and outliers are all correct.

### How to read it

**Paper count and citation count move together** (Spearman correlation 0.93). So the four boxes mostly sort people by size:
- About 90% of scientists fall in "both high" or "both low".
- Only 29 are off the diagonal.

**Two corners are worth looking at:**
- The **upper-left** scientists get many citations from few papers.
- The **lower-right** scientists publish a lot but are cited less.

**B. Sridhar (IICT, 329 papers) sits far right.** He is IICT's X-ray crystallographer: 260 of his papers list him as a middle author, providing crystal structures for other groups' syntheses. His count was 9 before D-41 joined his split OpenAlex profiles, and it's real. But his position measures service authorship, not leading research.

**Subrata Kundu (CECRI) is the top bubble,** with 258 papers and 15,782 citations, h = 59.

### Problems

1. **The colours clash.** The bubbles use lab colours, but the quadrant legend uses almost the same colours for quadrants: orange for "Giants", blue for "Specialists", green for "Prolific". A reader will think orange bubbles are "Giants" when they are CECRI. Give the quadrant legend neutral markers, or colour the bubbles by quadrant.
2. **"High-Impact"** here means total citations above the median, not impact per paper.
3. **"Emerging Faculty"** suggests early-career scientists. The group includes anyone with fewer than 17 papers in the window, including senior staff in administrative or service roles. "Below median on both" is accurate.
4. **When you filter to one lab, the dashed lines stay at the all-lab medians.** That's fine, but the caption should say so.

---

## 4. 360° Disciplinary Radial Research Profile

### What it shows

**The radar** spreads the labs' output over nine broad disciplines. A toggle switches to the 27 detailed fields.

**The side box:**
- Chemistry 37.5%, Materials 14.1%, Chemical Engineering 8.2%
- i10-index 1,842
- 88.6% of papers cited
- 25.6 "cites/paper"

**The text** says the cluster puts 97.5% of its research in physical and engineering chemical sciences.

### How it is computed

**The radar:**
- `src/stats/metrics.py: compute_disciplinary_radial_summary` reads `stats/tables/research_areas_field.csv`, which has paper counts per OpenAlex field.
- It maps each field to one of nine "macro disciplines" with a hand-written table.
- `build_disciplinary_radial_payload` in `src/dashboard/build_data.py` turns them into shares.

The fields are OpenAlex's 26 fields plus "Unclassified". They come from Scopus's subject classification. They have nothing to do with QS, so the button label "27 QS/Scopus Fields" is wrong.

**The side box and the 97.5% are not computed at all.** They are typed into `build_data.py` (the `"kpis"` block) and `dashboard/index.html`.

### What the data says

These are the correct shares, from 14,208 distinct papers, each counted once:

| Field (OpenAlex) | Share | The panel says |
|---|---|---|
| Chemistry | 26.9% | 37.5% |
| Engineering | 19.2% | — |
| Materials Science | 18.0% | 14.1% |
| Energy | 10.5% | — |
| Biochemistry, Genetics and Molecular Biology | 7.9% | — |
| Medicine | 5.8% | — |
| Chemical Engineering | 2.1% | 8.2% |

**Broad groups:**

| Group | Share |
|---|---|
| OpenAlex's "Physical Sciences" domain (includes engineering, energy, environment) | 81.8% |
| Life Sciences | 11.9% |
| Health Sciences | 6.0% |
| Social Sciences | 0.3% |

**Other figures:**

| Figure | Data (all three labs) | The panel says |
|---|---|---|
| i10 (papers with ≥ 10 citations) | **7,792** | 1,842 |
| Share of papers cited at least once | **89.7%** | 88.6% |
| Mean citations per paper | **24.6** | 25.6 |

### Problems

1. **Three side-box numbers are IICT's, shown as the cluster's.** Chemistry 37.5%, Materials 14.1% and Engineering 13.1% match IICT alone (37.6%, 14.1%, 13.1%). For the cluster they are 26.9%, 18.0% and 19.2%.
2. **Other numbers match nothing.**
   - "Chemical Engineering 8.2%" (actually 2.1%).
   - "i10-index 1,842" (actually 7,792 for the cluster; 1,894 CECRI, 3,076 IICT, 2,882 NCL).
   - "88.6%" and "25.6": no lab or subset gives these.
3. **97.5% has no source.** The nearest real figure is 81.8% of papers in OpenAlex's Physical Sciences domain. The panel's own nine-group mapping gives 78.4% for "Physical Sciences" plus "Engineering & Technology". Also, "unlike comprehensive universities which disperse funding across 20+ disciplines" compares against something that was never measured.
4. **"All Labs" counts every paper twice.** It adds the three labs' rows *and* the "Group 24 Combined" row of the same table: 28,517 paper counts for 14,208 papers. The shares come out about right only because the combined row equals the sum of the labs. The code should use only the combined row.
5. **Mean citations per paper is not "citation velocity"** (velocity would be per year).
6. **The mapping is partly arbitrary:**
   - "Unclassified" and anything unmapped are put into Physical Sciences.
   - Environmental Science gets its own spoke, although OpenAlex files it under Physical Sciences.
   - Most of the nine spokes are near zero: Arts, Business, Social Sciences and Mathematics together are 0.3%. So the "360°" chart is mostly empty space.

---

## What I recommend

The panels are interesting, but three things should not stay as they are:
- the invented 0.38 author factor;
- the typed-in numbers in the disciplinary side box;
- the reversed self-citation reading.

In order:

1. **Panel 4:**
   - Compute the side box from `group24_data_extended.csv` (cluster: Chemistry 26.9%, Materials 18.0%, Engineering 19.2%; i10 7,792; 89.7% cited; 24.6 per paper).
   - Use only the combined row for "All Labs".
   - Drop or replace the 97.5% sentence (81.8% in OpenAlex's Physical Sciences domain).
   - Rename "QS/Scopus" to "OpenAlex fields".
2. **Panel 2:**
   - Remove "Author Scope".
   - Count only citations **received**, to 2016–2026 papers, in both series.
   - Say that only Indian citing papers are included.
   - Replace the takeaway with the sentence suggested in section 2.
3. **Panel 1:**
   - Rename "Benchmark Max" to "Axis max".
   - Use 52 for IICT's industry papers.
   - Show the world top-10% line (10.83%).
   - Soften the card wording.
4. **Panel 3:**
   - Fix the legend colours.
   - Rename "High-Impact Giants" and "Emerging Faculty" to plain descriptions.
   - Add a note on B. Sridhar's middle-author record.

## How to check these numbers yourself

Run from `dpcn_a2/`:

```bash
python - <<'EOF'
import pandas as pd
e = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
p = e.drop_duplicates("work_id"); c = p["citations"].astype(int)
print("papers", len(p), "i10", (c >= 10).sum(), "cited %", round((c > 0).mean()*100, 1), "mean", round(c.mean(), 1))
print((p["field"].value_counts(normalize=True)*100).round(1).head(8))
print((p["domain"].value_counts(normalize=True)*100).round(1))
for lab, g in p.groupby("institution"):
    print(lab, (g["field"].value_counts(normalize=True)*100).round(1).head(3).to_dict())

net = pd.read_csv("data/final/citation_network.csv", keep_default_na=False)
labs = {"CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"}
out = net[net["source_inst"].isin(labs) & ~net["target_inst"].isin(labs)]
print("outgoing references counted as 'citations by others':", len(out))
EOF
grep -n "0.38" dashboard/js/app.js          # the invented author factor
grep -n "1842\|97.5" src/dashboard/build_data.py dashboard/index.html   # typed-in numbers
```
