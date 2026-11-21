# The Global Benchmark, explained simply

*Group 24 · CSIR-NCL, CSIR-IICT, CSIR-CECRI · read this before presenting the Global Benchmark page (`dashboard/global.html`)*

This note explains, in plain words, **what** we built, **why** we built it this way, **how** every choice was made, **what we found**, **how we checked it**, and **what its limits are**. Every number below comes from the tables in `stats/tables/global_*.csv`. Nothing is typed in by hand.

---

## 1. The whole idea in one paragraph

Our three labs (NCL Pune, IICT Hyderabad, CECRI Karaikudi) are government chemistry research labs. The basic dashboard tells us how much they publish and how often they are cited, but a number on its own means little. Is 12% "good"? The Global Benchmark answers that by putting the labs **next to fair comparison partners**:

- a **"twin" lab** in the USA, China, South Korea and Australia for each of our labs. A twin is a government research institute that works on the most similar topics;
- **six leading Indian institutes** (IISc, IIT Bombay, IIT Madras, ICT Mumbai, IACS Kolkata, IISER Pune);
- **fifteen Indian universities**, for the "who learns from whom" question.

All of them are measured the **same way**, on the **same research areas**, over the **same years (2016–2025)**, using **OpenAlex's own world-level citation measures**. Then we ask four questions:

1. How much do they publish, and is it growing?
2. How often are their papers among the world's most cited?
3. Do they work on the same topics?
4. Do they write papers together, and who cites whom?

---

## 2. Why we did it

- In our meeting, the professor suggested comparing our labs with chemistry institutes in India and abroad (China and the USA were mentioned), and showing how the labs are **connected** to them.
- A comparison is only useful if it is **fair**. Comparing NCL with "MIT" or "the whole Chinese Academy of Sciences" would be unfair: different size, different mission, different fields. So most of the work went into **choosing the comparison partners by fixed rules**, not by our opinion.

---

## 3. Key words you will use (plain-language glossary)

| Word | What it means here |
|---|---|
| **OpenAlex** | A free, open database of almost every scholarly paper in the world, with authors, institutions, topics and citations. All our data comes from it. |
| **Subfield** | OpenAlex sorts every paper into one of about 250 research subfields (e.g. "Organic Chemistry", "Catalysis", "Electrical and Electronic Engineering"). |
| **Scope** | The 31 subfields where our three labs publish 90% of their papers. Everyone is measured **only inside this scope**. |
| **Peer / twin** | A foreign government institute chosen by our rules as the closest match to one of our labs. One twin per lab per country, at most. |
| **Indian reference group** | Six top Indian chemistry institutes chosen by the team (not by the rules) as a home-country yardstick. |
| **Top 10% share** | Out of an institution's papers, the percentage that are among the **10% most-cited papers in the world** of the same subfield, same paper type and same year. This is **field-normalised**: a chemistry paper is compared with chemistry papers only, and a 2018 paper with 2018 papers only. The world average is about 10% by definition (exactly **10.83%** in our scope, because of ties). |
| **Top 1% share** | Same idea for the top 1%. |
| **FWCI > 1** | "Field-Weighted Citation Impact" above 1 means the paper got more citations than the world average for its field, type and year. |
| **CAGR** | Average yearly growth rate of paper output between 2016 and 2025. −5% means output shrinks by about 5% each year. |
| **International share** | Percentage of papers that have co-authors from more than one country. |
| **Cosine similarity** | A number from 0 to 1 that says how similar two research profiles are (1 = identical mix of topics, 0 = nothing in common). Explained in §6. |
| **Exchange ratio** | (partner's papers that cite the lab) ÷ (partner's papers that the lab cites). Above 1: the partner uses the lab's work more than the reverse. Below 1: the lab uses the partner's work more. |

---

## 4. Step 1: Which countries, and why

We did **not** pick countries from a hunch. We first looked at **who our labs actually co-author with**, using our own cleaned dataset (2016–2026):

- 3,171 of our 14,208 papers (22.3%) have at least one foreign co-author, spread over **95 countries**.
- The top partners by number of joint papers:

| Rank | Country | Joint papers | NCL | IICT | CECRI | Main partner institutions |
|---|---|---|---|---|---|---|
| 1 | **USA** | 564 | 194 | 244 | 133 | Texas A&M, Purdue, Florida International |
| 2 | **South Korea** | 477 | 119 | 173 | 187 | Jeonbuk National, Yeungnam, Hanyang |
| 3 | **Australia** | 408 | 83 | 265 | 63 | RMIT (272!), CSIRO, Univ. of Sydney |
| 4 | Saudi Arabia | 268 | 65 | 134 | 70 | King Saud University |
| 5 | **China** | 229 | 45 | 109 | 76 | Chinese Academy of Sciences, Hunan Univ. |

*(Joint papers are counted once per paper, so the three lab columns can add up to more than the country total when two of our labs are on the same paper.)*

**Our reasoning for the four countries:**

- **USA and China**: the two world leaders in chemistry research, and the two the professor named. China's share of world papers in our research areas went from 14.0% (2016) to 31.6% (2025).
- **South Korea and Australia**: our 2nd and 3rd largest partners, after the USA. Both also have **CSIR-like government research institutes** (KRICT in Korea, CSIRO in Australia), so a fair "twin" exists there.
- **Why not Saudi Arabia?** It is our 4th partner, but most joint papers are with one university (King Saud), and it has no government chemistry institute comparable to CSIR labs.

The full 95-country table is on the page (section "Which countries the labs work with").

---

## 5. Step 2: Deciding "what research counts" (the scope)

**Problem:** IIT Bombay publishes a lot of civil engineering and computer science; Oak Ridge publishes a lot of nuclear physics. If we count all their papers, we compare apples with oranges.

**Solution:** we took all our labs' papers (2016–2025, articles and reviews), sorted the subfields from most to least used, and kept the subfields that together cover **90%** of our labs' papers. That gives **31 subfields**, for example:

| Subfield | Share of our labs' papers |
|---|---|
| Organic Chemistry | 24.2% |
| Renewable Energy, Sustainability & Environment | 10.9% |
| Materials Chemistry | 9.4% |
| Electrical & Electronic Engineering (mostly batteries/electrochemistry, CECRI) | 7.2% |
| Electronic, Optical & Magnetic Materials | 4.6% |
| … down to Food Science (0.5%) | 90.1% cumulative |

From then on, **every institution, ours included, is measured only on papers in these 31 subfields.** This is why IISc shows "only" 12,516 papers: that is its chemistry-and-materials part, not all of IISc.

Other fixed choices, applied to everyone:

- **Years 2016–2025.** 2026 is left out because it is a partial year (we collected the data in October 2026).
- **Paper types: articles and reviews only.** No conference abstracts, editorials, etc.
- **Sub-units count with their parent.** For example, a paper from a division of DICP counts for DICP. OpenAlex's "lineage" filter does this.

---

## 6. Step 3: How the foreign twins were chosen (the rules)

The same rules run for every country, in code (`src/collect/22_global_peers.py`, settings in `config/global_benchmark.yaml`). Think of it as a funnel.

### Rule 1: Start with the country's 200 biggest players in our scope
Take the 200 institutions in that country with the most papers in the 31 subfields.

### Rule 2: Keep only government research institutes
CSIR labs are **government research institutes**, not universities, companies or hospitals. So we keep only institutions that OpenAlex labels "government" or "facility".

We also drop **umbrella bodies**: organisations that are the *parent* of another candidate (e.g. the whole Chinese Academy of Sciences, the US Department of Energy, CSIRO as a whole). Why: CSIR is compared **lab by lab** (NCL, not "CSIR"), so the other side must also be single labs (DICP, not "the Chinese Academy of Sciences").

### Rule 2b: Hand-checked removals (written down, with reasons)
OpenAlex sometimes labels things "government/facility" that are not stand-alone institutes. We reviewed them by hand and removed **46**, each with a written reason in `config/overrides/global_peer_exclusions.csv`. The types:

- **University-hosted labs**, e.g. China's "State Key Laboratory of Fine Chemicals" sits inside Dalian University of Technology. It is really a university.
- **Multi-university consortia**, e.g. "Collaborative Innovation Center of Chemical Science and Engineering Tianjin" is an affiliation label, not an institute.
- **Shared user facilities** such as synchrotrons (Australian Synchrotron, Pohang Accelerator Laboratory). Their papers are written by visiting users.
- **Ministries, departments, funding agencies**, e.g. US Department of Defense, Australian Research Council, National Research Foundation of Korea.
- **Institute for Basic Science (Korea)**, removed after our data audit (D-40). Most IBS centres are on university campuses (KAIST, POSTECH, UNIST, SNU). That is the same reason the Chinese State Key Labs were removed.

*Why by hand and not automatically?* We tried an automatic "has a university parent" rule. It failed both ways: Argonne lists the University of Chicago (its operator) as a parent, so it would wrongly be dropped; KRICT has no parent at all in OpenAlex. A written list with reasons is more honest, and anyone can check it.

### Rule 3: Not too small
A candidate must have at least **half the in-scope papers of our smallest lab**. CECRI has 2,476, so the floor is 1,238 papers. Of those that pass, the 25 largest go to the next step.

### Rule 4: Pick the most similar one (the "twin"), using cosine similarity

**How similarity works, simply.** For each institution we make a list: how many papers in each subfield. For example (made-up numbers): NCL = [Organic 1000, Materials 500, Catalysis 200, …]. Two lists that "point in the same direction" have similar topic mixes, even if one institution is much bigger. That is what **cosine similarity** measures:

$$\text{similarity}(A,B) = \frac{\sum_s A_s \cdot B_s}{\sqrt{\sum_s A_s^2}\;\sqrt{\sum_s B_s^2}}$$

where $A_s$ is A's number of papers in subfield $s$. The result is between 0 (no topic in common) and 1 (exactly the same mix). Size does not matter, only the mix. A big institute and a small one with the same focus score high.

**How twins are assigned (one per lab, per country).** Within each country:
1. Find the single best lab–candidate pair of all, and fix it.
2. Remove that lab and that candidate, then find the best pair among what is left, and so on.
3. A pair below **0.4** is not accepted. That lab then simply has **no twin** in that country.

This is called greedy one-to-one matching. It stops two of our labs from sharing the same twin.

**Worked example (China):**
- The best pair is Shanghai Institute of Organic Chemistry (SIOC) ↔ **IICT: 0.97**, almost identical profiles, both heavy organic chemistry. Fixed.
- Next best among the rest: Fujian Institute of Research on the Structure of Matter (FJIRSM) ↔ **CECRI: 0.82**. Fixed.
- Then for NCL: Dalian Institute of Chemical Physics (DICP) ↔ **NCL: 0.77**. Fixed.

**Why the floor is 0.4 (and not 0.5).** We first tried 0.5. It left the USA with only one twin, because US national labs (Oak Ridge, Argonne…) publish far more physics than our labs. 0.4 still means "moderate overlap" and gives every country at least two twins. We show this choice openly on the page.

### The funnel, in numbers

| Country | Start (rule 1) | Not in the country* | Not government (rule 2) | Umbrella body | Removed by hand (2b) | Too small (rule 3) | Similarity tested | Twins chosen |
|---|---|---|---|---|---|---|---|---|
| USA | 200 | 29 | 143 | 4 | 11 | 0 | 13 | 2 |
| China | 200 | 13 | 149 | 2 | 18 | 0 | 18 | 3 |
| South Korea | 200 | 50 | 118 | 6 | 6 | 7 | 13 | 2 |
| Australia | 200 | 108 | 67 | 2 | 11 | 8 | 4 | 2 |

*\*"Not in the country": foreign institutions that show up because they co-author many papers with that country's researchers. They are removed first.*

### The final peer list

| Our lab | USA | China | South Korea | Australia |
|---|---|---|---|---|
| **NCL** (Pune) | Oak Ridge National Laboratory (0.48) | Dalian Inst. of Chemical Physics (0.77) | KRICT, Korea Research Inst. of Chemical Technology (0.66) | CSIRO Manufacturing (0.70) |
| **IICT** (Hyderabad) | **No twin**: closest is PNNL (0.25) | Shanghai Inst. of Organic Chemistry (0.97) | **No twin**: KRICT (0.47) is closer to NCL (0.66); next free is KBSI (0.38) | **No twin**: CSIRO Manufacturing (0.54) is closer to NCL (0.70); next free is QIMR Berghofer (0.09) |
| **CECRI** (Karaikudi) | National Laboratory of the Rockies, formerly NREL (0.78) | Fujian Inst. of Research on the Structure of Matter (0.82) | Korea Institute of Energy Research (0.81) | ANSTO, Australian Nuclear Science & Technology Org. (0.61) |

**9 foreign twins in total.** The pattern makes sense:
- **CECRI** (electrochemistry, batteries, energy) gets energy institutes: NREL, KIER, FJIRSM.
- **IICT** (organic synthesis, drugs, agrochemicals) gets SIOC, and **only SIOC: a twin in 1 of 4 countries**. This is a **finding**, not a gap in the data:
  - **USA**: no government lab comes close; the best is Pacific Northwest National Laboratory at 0.25. US national labs work on energy, materials and physics, not organic synthesis.
  - **South Korea and Australia**: one institute in each passes 0.4 for IICT (KRICT 0.47, CSIRO Manufacturing 0.54), but each is *even closer to NCL* (0.66 and 0.70). The rule gives each foreign institute to only one lab, the closer one, so it became NCL's twin. The next free candidates are far below 0.4 (KBSI 0.38, QIMR Berghofer 0.09).
  - **Why**: 37% of IICT's papers are organic chemistry. Its twin SIOC has 64%, and no other foreign twin has more than 8%. Government labs with IICT's organic-chemistry focus exist in China but not in the other three countries.
  - On the page this is the **"Final peer list"** table in section 02: one row per lab, one column per country, the similarity score as a bar with the 0.4 minimum marked, and for every "No twin" cell the closest candidate and why it was not chosen.
- **NCL** (broad: organic, materials, polymers, catalysis) gets broad chemistry institutes: DICP, KRICT, CSIRO Manufacturing, ORNL.

### The Indian reference group (chosen by the team, not by the rules)
IISc Bangalore, IIT Bombay, IIT Madras, ICT Mumbai, IACS Kolkata, IISER Pune. These are leading Indian chemistry institutions. They are mostly universities, so the rules above (government only) would not pick them, but they are the natural home comparison. They are measured with exactly the same scope and queries. The page states clearly that this group was chosen by us.

---

## 7. What we measured, and why it is fair

For **all 18 institutions** (3 labs + 9 twins + 6 Indian), the same OpenAlex queries:

| Measure | How it is computed | Why |
|---|---|---|
| Papers per year (in scope) | count of articles + reviews in the 31 subfields | output size and trend |
| Growth (CAGR 2016→2025) | $(\text{papers}_{2025}/\text{papers}_{2016})^{1/9} - 1$ | is output growing or shrinking? |
| Output index | papers each year ÷ papers in 2016 × 100 | compares trends of big and small institutes on one chart |
| **Top 10% share** | papers flagged by OpenAlex as in the world's top 10% (same subfield, type, year) ÷ all papers | **the main impact measure**; fair across fields and years |
| Top 1% share | same for top 1% | very high-impact work |
| Above world average | share of papers with FWCI > 1 | second impact measure |
| International share | share of papers with authors from >1 country | how international the work is |
| Research profile | share of papers in each subfield | what they work on |
| Co-authored papers | papers with both the lab and the peer as authors | do they work together? |
| Citation flows | peer papers citing the lab's papers, and peer papers the lab cites (both published 2016–2026, joint papers left out) | who learns from whom |

**Why this is fair:**
- **Same rules for everyone.** Our own labs are also measured by the raw OpenAlex query, not our cleaned dataset, so no side gets special treatment.
- **Field-normalised impact.** We do not compare raw citation counts, which are unfair: organic chemistry and batteries have different citation habits, and older papers have had more time. The top-10% flag is computed by OpenAlex against the whole world's papers of the same subfield, type and year.
- **The world reference is measured, not assumed:** 10.83% of the world's papers in our scope are in the top 10% (ties at the cut-off push it slightly above 10%).

---

## 8. What we found

### 8.1 Output and growth (2016 → 2025, in scope)

| Institution | Papers 2016 | Papers 2025 | Growth per year |
|---|---|---|---|
| **CSIR-NCL** | 612 | 406 | **−4.5%** |
| **CSIR-IICT** | 733 | 447 | **−5.3%** |
| **CSIR-CECRI** | 213 | 214 | **+0.1%** (flat) |
| Median foreign twin | | | +1.9% |
| Median Indian reference institute | | | +2.9% |
| e.g. DICP / FJIRSM (China) | 1,072 / 653 | 2,003 / 1,340 | +7.2% / +8.3% |

**In simple words:** NCL and IICT publish fewer papers each year, while the twins and the Indian institutes grow. CECRI is flat.

*Is the decline real?* Yes. We checked NCL against its own Annual Report 2023-24 (467 / 407 / 365 papers for 2021 / 2022 / 2023). Our numbers (459 / 418 / 413) are on the same scale, so the decline is not a data-collection error.

At country level, China's share of the world's papers in these subfields rose from 14.0% to 31.6%, India's from 4.4% to 8.3%, and the USA's fell slightly from 11.8% to 10.0%.

### 8.2 Impact: how often papers are among the world's most cited

| Institution | Top 10% share | Top 1% share | Above world avg (FWCI>1) |
|---|---|---|---|
| **CSIR-CECRI** | **17.3%** | 1.25% | 51.9% |
| **CSIR-NCL** | 12.3% | 1.16% | 40.2% |
| **CSIR-IICT** | 8.9% | 0.56% | 36.7% |
| World (same scope) | 10.8% | 1.09% | – |
| Median Indian reference institute | 12.3% | 0.97% | – |
| Median foreign twin | **24.8%** | 3.5% | – |

**In simple words:**
- **CECRI** is clearly above the world level (17.3% vs 10.8%), and above the Indian institutes.
- **NCL** is above the world level and exactly level with India's best institutes (12.3%).
- **IICT** is a little below the world level (8.9%).
- The **foreign twins are about twice as high** (median 24.8%). For example SIOC (IICT's twin) is at 27.3% and DICP (NCL's twin) at 27.2%.

### 8.3 What they work on (research profiles)
- IICT: 37% organic chemistry. Its twin SIOC: 64% organic chemistry.
- NCL: 22% organic chemistry and 11% materials chemistry, a broad mix like DICP and KRICT.
- CECRI: 27% renewable energy and 18% electrical/electronic engineering (batteries, fuel cells), the same mix as NREL, KIER and FJIRSM.

This confirms that the similarity rule chose sensible twins.

### 8.4 Working together: co-authorship (2016–2025)
- With the **9 foreign twins and other foreign peers**: only **49** joint papers in total, of which just **8** are with the twins themselves.
- With the **6 Indian institutes**: **682** joint papers. The strongest pairs are NCL–IISER Pune (247, both in Pune), NCL–IIT Bombay (88), NCL–IISc (62) and CECRI–IIT Madras (59).

**In simple words:** the labs collaborate a lot inside India, but hardly at all with their closest foreign equivalents. Their big foreign partners (§4) are mostly *universities*, not these government institutes.

### 8.5 Who learns from whom: citation flows
The **exchange ratio** = partner papers citing the lab ÷ partner papers the lab cites. Joint papers are left out, and only papers from 2016–2026 are counted in both directions.

| Partner group | Partner cites lab | Lab cites partner | Ratio | Meaning |
|---|---|---|---|---|
| Foreign peers (all) | 2,946 | 4,461 | **0.66** | labs learn more from them than the reverse |
| USA | 380 | 957 | 0.40 | strongest one-way flow toward the labs |
| China | 2,059 | 2,805 | 0.73 | |
| South Korea | 342 | 412 | 0.83 | close to balanced |
| Australia | 165 | 287 | 0.57 | |
| 6 Indian institutes | 4,309 | 3,129 | **1.38** | Indian institutes use the labs' work more than the reverse |

### 8.6 Knowledge exchange with 15 Indian universities
This part used to be a separate page (the "Academic Bridge"). We merged it here so the two pages cannot contradict each other: it uses exactly the same definition as §8.5. Universities: IISc and 8 IITs (Bombay, Madras, Delhi, Kharagpur, Kanpur, Roorkee, Guwahati, Hyderabad), and 6 state universities (Savitribai Phule Pune, Hyderabad, Osmania, Alagappa, Anna University Chennai, Madras).

| Group | Univ. papers citing the labs | Univ. papers the labs cite | Ratio |
|---|---|---|---|
| IISc + IITs | 6,814 | 4,190 | **1.63** |
| State universities | 3,379 | 1,693 | **2.00** |

All 15 universities have a ratio above 1 (from 1.22 for IISc to 2.62 for Alagappa University). **In simple words:** for Indian universities, our labs are a **source of knowledge**. Universities build on the labs' work more than the labs build on theirs. The closest neighbours are also the closest partners: NCL with Pune University (355 joint papers), IICT with Osmania (258), CECRI with Alagappa (167, both in Karaikudi region).

### 8.7 The overall story (what to tell the professor)
1. **At home, the labs are leaders.** They match or beat India's top institutes on impact (CECRI and NCL), and Indian universities and institutes draw on their work more than the reverse.
2. **Globally, there is a clear gap.** The closest foreign equivalents produce about twice the share of world top-10% papers, are growing while NCL and IICT shrink, and are the ones the labs learn from (ratio 0.66).
3. **The labs hardly collaborate with these equivalents** (8 joint papers with the twins in ten years), which is an obvious opportunity.
4. **CECRI stands out** as the strongest of the three on impact and international collaboration (31% of papers international).

---

## 9. How we checked our own work

| Check | Result |
|---|---|
| Our output vs NCL's own Annual Report 2023-24 | same scale (459/418/413 vs 467/407/365); decline is real |
| Indian-university counts from our dataset vs separate OpenAlex queries (9 lab × university pairs counted both ways) | agree within **4.3%** (e.g. NCL ↔ IISc 421 vs 425 citing papers); an automated test fails if > 10% |
| World baseline | measured (10.83%), not assumed (10%) |
| Citation-flow time window | fixed during the audit (D-40): both directions now count only 2016–2026 papers. Before the fix, "papers the lab cites" included old papers back to 1953, which made every partner look like a source. |
| Every rule decision | stored in config files with reasons; the page shows the funnel, the similarity table and the exclusion list |
| Every sentence on the page | generated from the data file, not typed by hand |
| Automated tests | `tests/test_global_benchmark.py` (rules, twins unique, numbers consistent, home card = tables) and a headless-browser test that opens the page and checks every chart and table |
| Reproducible | all API answers cached; rerunning gives the same numbers without new API cost |

---

## 10. Honest limitations (say these before you are asked)

1. **OpenAlex is not perfect.** Affiliations are sometimes missing or wrong, which affects everyone, but probably Indian government labs more. Our cleaned dataset recovers some missed papers; the benchmark uses the raw query for everyone to stay fair.
2. **"Twins" are the closest available, not perfect copies.** ORNL (0.48) is a much larger, physics-heavy lab, and similarity only looks at *topics*, not budget, staff or mission.
3. **IICT has only one twin** (China). In the USA nothing comes close (0.25). In Korea and Australia the one close institute is closer to NCL and became NCL's twin. Under a different matching rule IICT could share it; we kept one twin per institute so that no two labs are measured against the same comparator.
4. **The Indian group was chosen by us**, not by the rules. We say so on the page.
5. **CSIRO Manufacturing's −8.1% a year** is probably an artefact: OpenAlex credits some papers to "CSIRO" as a whole instead of the division.
6. **ANSTO and ORNL run large user facilities.** Visiting scientists' papers raise their output and international share (ANSTO: 71% international).
7. **China's rise is partly better data.** Country shares divide by all papers, including those without a known country; affiliation coverage has improved over time.
8. **Everyone's top-10% share falls between 2016–20 and 2021–25**, while the world stays at 10.8%. Recent papers have had less time to be cited, and the effect differs between institutions, so compare within the same period.
9. **Citation counts are a proxy for influence**, not for quality, industrial value or patents, which matter a lot for CSIR labs.
10. **2026 is excluded** (partial year).

---

## 11. Questions the professor may ask, with short answers

**Q: Why these four countries?**
A: They are our top 3 co-authoring countries (USA 564, Korea 477, Australia 408 papers), plus China as the world leader the professor named. Korea and Australia also have CSIR-like government institutes.

**Q: Why not compare with MIT or the Chinese Academy of Sciences?**
A: MIT is a university, and CSIR labs are government research labs. CAS is an umbrella of over 100 institutes, and we compare lab with lab. Rule 2 removes both kinds.

**Q: How do you know the twins are really similar?**
A: Cosine similarity of their topic mix in the 31 subfields, a standard measure. SIOC–IICT is 0.97. The research-profile chart on the page shows the same thing visually.

**Q: Why 90% scope, why 200 candidates, why 0.4?**
A: 90% covers almost all our labs' work but leaves out stray one-off topics. 200 is large enough that no relevant government institute is missed (the funnel shows most are removed as non-government anyway). For 0.4 we tried 0.5 first, but it left the USA with one twin, so we chose 0.4 ("moderate overlap") and documented it. All three are one-line settings in `config/global_benchmark.yaml`.

**Q: Isn't removing institutions by hand subjective?**
A: Each of the 46 removals has a written reason in a file anyone can read. All are of a few clear types: university-hosted labs, consortia, synchrotrons, ministries and funding agencies. An automatic rule was tried and gave wrong results (it would remove Argonne).

**Q: Why top-10% share instead of citations per paper?**
A: Raw citations are unfair across fields and years. Top-10% share compares each paper only with papers of the same subfield, type and year worldwide, and it is not distorted by one hugely cited paper.

**Q: Your labs' numbers here differ slightly from the main dashboard. Why?**
A: The main dashboard uses our cleaned dataset (all types, 2016–2026). The benchmark uses the same raw OpenAlex query for every institution (articles and reviews, 2016–2025, 31 subfields), so the comparison is like-for-like.

**Q: What does an exchange ratio of 0.66 mean?**
A: For every 100 papers of the foreign peers that our labs cite, the peers cite our labs in 66 papers. Knowledge flows mostly **to** our labs from them. For Indian universities it is the opposite (1.63–2.00).

**Q: Is NCL's falling output real or a data problem?**
A: Real. It matches NCL's own annual report within a few percent.

**Q: What is the main takeaway?**
A: The labs are national leaders and a knowledge source for Indian universities. But compared with their closest foreign equivalents they publish less high-impact work, are shrinking rather than growing, and hardly collaborate with them.

---

## 12. Where everything is

| What | File |
|---|---|
| The page | `dashboard/global.html` (+ `dashboard/js/global.js`, `dashboard/css/global.css`) |
| All settings (years, scope, rules, countries, Indian group) | `config/global_benchmark.yaml` |
| The 46 hand removals with reasons | `config/overrides/global_peer_exclusions.csv` |
| Peer selection code (rules 1–4) | `src/collect/22_global_peers.py` |
| Benchmark data pull (same queries for all) | `src/collect/23_global_benchmark.py` |
| Tables and calculations | `src/stats/global_benchmark.py` → `stats/tables/global_*.csv` |
| Peer list / funnel / similarity / summary / links / universities | `global_peers.csv`, `global_rule_funnel.csv`, `global_similarity.csv`, `global_summary.csv`, `global_links.csv`, `global_indian_universities.csv` |
| Decisions and their reasons | `docs/DECISIONS.md`: D-35 (design), D-39 (universities merged), D-40 (audit fixes) |
| Tests | `tests/test_global_benchmark.py`, `scripts/test_browser.py` |
| Rebuild everything | `python run.py global` (uses the cache; no new API cost) |

**Reading the charts:** every institution name on the charts has a coloured square and its country after it (e.g. "■ DICP  China"), and a colour key for the countries sits below each chart.

**Page sections, in order:** Overview (one-minute summary) → 01 Countries → 02 Peers and rules → 03 Output and growth → 04 Impact → 05 Research topics → 06 Links (co-authorship and citations) → 07 Indian universities → 08 Method, sources and key terms.
