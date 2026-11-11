# Data audit, 11 November 2026 (D-40, D-41)

This audit checks whether the Global Benchmark (D-35) and the core dataset match real-world scale, fixes what was wrong, and lists the numbers that still look high or low so they can be checked by hand.

**Limits of the audit.** This checkout has no OpenAlex cache and no `.env`, so nothing was re-queried. Every check below uses files in the repository, plus one outside source: NCL's own annual report.

Status codes used in the tables:
- **OK**: verified.
- **FIXED**: was wrong and has been corrected.
- **CHANGED**: the selection changed by a rule.
- **FLAG**: left as it is, but you should look at it.

---

## 1. Is the scale right? (independent check)

**Source:** CSIR-NCL Annual Report 2023-24, "Science Performance Indicators" page, p. 18 (dspace.ncl.res.in, handle 20.500.12252/6390).

| NCL papers | Annual report | Our curated dataset | Benchmark raw query |
|---|---|---|---|
| 2021 | 467 | 461 | 459 |
| 2022 | 407 | 415 | 418 |
| 2023 | 365 | 417 | 413 |

**OK.** Our paper counts match NCL's own counts to within 2% for 2021–22. For 2023 we are 14% higher. Likely reasons, not verified: the report's cut-off date, and papers OpenAlex dates by online publication. The fall in NCL's output is real: the lab reports it too. IICT's fall (−5.3% a year) follows the same pattern. IICT's own publication page loads its data dynamically, so it couldn't be checked here.

**Other scale facts** from the same report (2023-24):
- **Scientific staff:** NCL has 126; our roster lists 166 NCL names (see §4).
- **Students and project staff:** NCL has 1,054 (690 project assistants and 364 research fellows). This is why the all-author network has thousands of nodes: over ten years, three labs of this size produce several thousand student and project-staff authors. The faculty network (306 scientists with papers) is the right comparison with "faculty".
- **Scale across CSIR:** the CSIR annual report for 2022-23 gives 5,846 SCI papers for all of CSIR in 2022. Our three labs had 1,121 papers in 2022, which is 19% of CSIR. That share is plausible for two of CSIR's largest chemistry labs plus CECRI.

---

## 2. The teammate's Global Benchmark claims

| Claim as handed over | Status | Corrected value | How to check |
|---|---|---|---|
| Peer list (twins per country) | **CHANGED** | South Korea: IBS removed. IICT has no Korean twin. | §3 |
| "IICT has no match in the USA or Australia" | **CHANGED** | IICT also has no match in South Korea | `stats/tables/global_peers.csv` |
| 22.3% of papers have a foreign co-author, 95 countries | **OK** | 3,171 / 14,208 | `stats/tables/global_country_relations.csv` |
| USA 564 > South Korea 477 > Australia 408; China 5th (229) | **OK** | | same file |
| NCL −4.5% a year, IICT −5.3% a year, CECRI flat | **OK** | NCL's annual report agrees (§1) | `global_summary.csv` |
| Foreign twins grew a median 1.2% a year | **CHANGED** | 1.9% (9 twins; IBS was −0.2%) | `global_summary.csv` `cagr_pct` |
| Indian peers grew 2.9% a year | **OK** | | |
| China's world share rose from 14% to 32% | **FLAG** | The numbers are right, but the 2016 figure is too low (§5) | `global_countries.csv` |
| CECRI 17.3%, NCL 12.3%, IICT 8.9% in the world's top 10% | **OK** | | `global_summary.csv` `top10_pct` |
| Foreign twins (median) 25.4% in the top 10% | **CHANGED** | 24.8% | |
| Indian peers (median) 12.3% | **OK** | | |
| "The world average is 10%" | **FIXED** | The world's measured share in these subfields is **10.83%** (top 1%: 1.09%) | `stats/tables/global_world_baseline.csv` |
| "Only 54 papers co-authored with the foreign twins" | **FIXED** | 54 was with all 10 foreign *peers*, counting every lab–peer pair. Now 49 with the 9 foreign peers, and **8** with the twins themselves. | `global_links.csv` (`is_twin`) |
| 682 co-authored papers with the Indian peers | **OK** | 247 of them are NCL with IISER Pune (same city) | `global_links.csv` |
| "The twins cite us about a third as often (USA 0.17, India 0.64)" | **FIXED, conclusion weaker** | Foreign **0.66** (USA 0.40, China 0.73, South Korea 0.83, Australia 0.57). Indian peers **1.38**: they cite the labs *more* than the labs cite them. | §3 |
| Indian universities: "the labs draw slightly more on them" (ratios 0.46–1.93) | **FIXED, conclusion reversed** | All 15 universities cite the labs more than the labs cite them: **1.22–2.62** (IISc and IITs 1.63, state universities 2.00) | `global_indian_universities.csv` |

---

## 3. What was wrong and what changed

### 3.1 Citation flows compared two different time windows (the biggest error)

The exchange ratio divides two counts:
- **Peer papers that cite a lab.** These can only be from 2016 or later, because the labs' papers start in 2016.
- **Peer papers a lab cites.** These included papers from any year, back to 1953. About half of them were from before 2016: 50.5% for the foreign peers, 53.4% for the Indian institutes and 50.2% for the 15 universities.

So every partner looked like a net source of knowledge, whoever it was.

**Fix:** both directions now count only partner papers published 2016–2026 (`src/stats/global_benchmark.py`, `_flow_years`).

| Group | Before | After |
|---|---|---|
| Foreign peers | 0.33 | 0.66 |
| USA | 0.17 | 0.40 |
| China | 0.38 | 0.73 |
| South Korea | 0.35 | 0.83 |
| Australia | 0.36 | 0.57 |
| Indian reference group | 0.64 | 1.38 |
| IISc and IITs | 0.46–1.08 | 1.22–2.25 |
| State universities | 0.55–1.46 | 1.25–2.62 |

The page's sentences used to state the direction ("the labs draw on …") as fixed text. They are now worked out from the numbers, on `global.html` and on the home-screen card.

The counts are still not scaled by institution size: a larger partner has more papers both to cite and to be cited.

### 3.2 World baseline

The dashed "world" line and the text used exactly 10% and 1%. OpenAlex counts ties at the threshold, so the world's share in the 31 benchmark subfields is 10.83% and 1.09% (10.6–11.3% depending on the year). The reference line now uses these measured values.

### 3.3 Institute for Basic Science (South Korea) dropped

Rule 2b of the teammate's own rules removes university-hosted labs; that is how the Chinese State Key Laboratories were removed. Most IBS research centres sit on university campuses (KAIST, POSTECH, UNIST, SNU and others). IBS was also IICT's weakest twin: 0.42, just above the 0.4 floor.

The next-best Korean match for IICT, KBSI, scores 0.38, below the floor. So IICT has no Korean twin, and NCL's twin (KRICT) and CECRI's twin (KIER) don't change.

I also listed the National Research Foundation of Korea as a funding agency, like the Australian Research Council, so a future run can't pick it.

**To undo:** delete the IBS line in `config/overrides/global_peer_exclusions.csv`, then run Step 22 with the API.

The change was applied without the API by `python -m src.collect.22_global_peers --offline`. This re-applies rules 2b and 4 from the saved `candidates.csv`, and it refuses to run if a change would need new data.

### 3.4 Core dataset

| Problem | Size | Fix |
|---|---|---|
| Roster entries that were page text: "Last Updated: 07-10-2026", "director.cecri@csir.res.in", "mjkannan.cecri@csir.res.in" | 3 CECRI entries, none with papers | Removed by a new Step 19 rule. Roster 385 → 382; scientists with papers still 306. Listed in `data/review/roster_excluded.csv`. |
| Department recorded as "Contact Number:" (a page label) | 12 NCL scientists; it showed as a department bar in the NCL chart | Department set to blank (unknown) |
| "Probable former faculty" given an invented post: designation "Former Scientist / Senior Researcher", department "Chemistry / Chemical Sciences" | 742 authors, 15,230 rows | Designation blank, department "Unassigned" |
| The AGENTS.md §5.7.6 student exclusion was never applied | 36 authors, 456 rows | Now affiliated authors |

Faculty statistics never used the "former faculty" flag, so these D-40 fixes change no faculty number. The dashboard tables and hover cards no longer show the invented posts.

### 3.5 Designations and split author profiles (D-41)

**Designations were one title too high.** Step 02 called Scientist-F "Chief Scientist" and moved every lower lettered grade up one title. The CSIR recruitment rules put Scientist-E at pay level 13, F at 13A and G at 14. CSIR lab pay lists rank Principal (L-13) < Senior Principal (L-13A) < Chief Scientist (L-14). The correct ladder is C Scientist, D Senior Scientist, E Principal, F Senior Principal, G Chief Scientist. Both scrapers read only the letter, so the 152 IICT and CECRI labels map exactly. They now carry the letter, e.g. "Senior Principal Scientist (Scientist-F)". NCL's page gives no grades.

**Scientists split across OpenAlex profiles.** Step 07 matched each roster scientist to one OpenAlex profile. Papers on that person's other profiles were counted as someone else's, mostly as "probable former faculty". A strict rule finds the splits:
- compatible names: same surname, every full given name of one name appears in the other, and initials agree;
- the same lab;
- never on the same paper;
- at least 3 shared co-authors, and at least 20% of the smaller profile's co-authors.

The result is a reviewed list, `config/overrides/author_profile_merges.csv`: 59 profiles, 32 of them into 26 roster scientists.

| Scientist | Papers before → after | h-index before → after |
|---|---|---|
| B. Sridhar (IICT) | 9 → 329 | 1 → 29 |
| B. Subramanian (CECRI) | 3 → 93 | 3 → 26 |
| Mahesh S. Dharne (NCL) | 11 → 90 | 3 → 23 |
| P. Ragupathy (CECRI) | 4 → 63 | 4 → 24 |
| T.G. Ajithkumar (NCL) | 4 → 62 | 1 → 21 |
| K. Suresh Babu (IICT) | 4 → 56 | 3 → 16 |
| M.S.L. Karuna (IICT) | 11 → 38 | 4 → 15 |
| S. Vasudevan (CECRI) | 4 → 25 | 2 → 13 |

The rule rejects these different people:
- the twins Sidhanath (IICT) and Sheshanath (RMIT) Bhosale, who share 75 papers;
- Rintu vs Rajkumar Banerjee;
- Sumana vs Subrata Kundu;
- Sarthak vs S. Nishant Jain;
- B. Jagan Mohan vs B.V. Subba Reddy.

Lab totals change as follows:
- **Faculty papers:** 6,966 → 7,494 (CECRI 852 → 1,001, IICT 2,719 → 2,991, NCL 3,422 → 3,530).
- **Mean h-index:** IICT 8.12 → 8.57, NCL 9.75 → 10.05, CECRI 11.92 → 14.00.

The Insight 11 networks now make one node per person. The study was re-run, and its headline numbers moved slightly: faculty half-reach takes 12 steps (was 13), the faculty threshold is 0.215 (was 0.30), and an outbreak at 0.2 covers 30% of the faculty network (was 24%).

**Other fixes.**
- Step 20 overwrote its own log of 144 removed duplicate papers whenever a re-run found nothing new. The log was restored, and the step now appends to it.
- Insight 11 had a fixed claim saying "123 technical staff and duplicates". Three of the 123 are page-text entries, so the claim now names them.

---

## 4. Numbers that look high or low (check these yourself)

| Number | Where | Why it looks odd | What I found |
|---|---|---|---|
| **690 "probable former faculty"** (706 before D-41) | `group24_data_extended.csv`, `author_role` | About twice the roster. NCL has 126 scientists, so it can't have lost 216 in ten years. | **PARTLY FIXED.** 32 of these profiles were current roster scientists split by OpenAlex (§3.5), and 27 more were second profiles of one person. The rest only means "≥ 10 papers in ≥ 3 years at the lab, not on today's roster": mostly long-term project staff, postdocs or frequent collaborators. Don't call them "former faculty" in the report. |
| **NCL roster: 166 scientists** vs 126 in the annual report | `faculty_master.csv` | +32% | The NCL page gives no designations (all are recorded as "Scientist"), so I can't separate emeritus or retired scientists from recent recruits. 151 of the 166 have papers. |
| **CECRI roster: 48 entries, only 26 with papers** | `faculty_master.csv` | CECRI is a lab of 100+ scientists | The CECRI pages list unit heads and administrative cells (Mandapam unit, Director's technical cell). Recall for CECRI faculty is low; it is better described as "26 scientists matched". |
| **IICT: 49 Chief Scientists and 32 more "Chief Scientist (Scientist-F)" out of 168** | `faculty_master.csv` | Very top-heavy | **FIXED (§3.5).** Our Step 02 called Scientist-F "Chief Scientist" and moved every lower grade up one title. IICT is now 49 Chief (G), 32 Senior Principal (F), 23 Principal (E), 23 Senior (D), 39 Scientist (C). |
| **CSIRO Manufacturing −8.1% a year** (347 → 159 papers) | `global_summary.csv` | Big drop for a twin | Most likely papers credited to CSIRO as a whole rather than to the business unit. Treat its trend as unreliable (now stated on the page). |
| **ANSTO 70.8% international** | `global_summary.csv` `intl_pct` | Far above everyone else | ANSTO runs user facilities (a neutron source and the Australian Synchrotron), so visiting users' papers carry an ANSTO affiliation. ORNL is similar (39%). |
| **China's world share 14.0% in 2016** | `global_countries.csv` | Too low for chemistry and materials science | The denominator includes OpenAlex papers with no known country, and there are more of those in early years. The rise to 31.6% is partly better affiliation data. |
| **Every top-10% share falls from 2016–20 to 2021–25** (ORNL 27.9 → 17.4, NCL 15.1 → 9.0, DICP 29.7 → 25.5) | `global_summary.csv` `top10_pct_early/late` | All institutions fall at once | The world's share stays at 10.8–10.9%, so citations are shifting towards other institutions (mainly Chinese ones). Compare institutions within a period, not one institution across periods. |
| **NCL top 10%: 21.9% in 2016 → 7.9% in 2025** | `global_by_year.csv` | A steep fall | Real in the data, and steeper than the other Indian institutes'. NCL's annual-report output fell over the same years. |
| **CECRI (17.3%) ahead of NCL and IICT** | `global_summary.csv` | Smallest lab has the highest impact | Plausible: electrochemistry and energy papers are highly cited. CECRI's 2024–25 values are lower (10.0%, 10.7%). |
| **RMIT University: 272 papers, almost all with IICT** | `global_country_relations.csv` | One foreign university dominates Australia | Concentrated in a few authors (Sheshanath V. Bhosale, RMIT; Sidhanath V. Bhosale, IICT). This fits a long-running IICT–RMIT partnership; check the IICT website before quoting it. |
| **King Saud University: 138 papers** (Saudi Arabia ranks 4th) | same | Large for Saudi Arabia | Spread over 197 lab authors; the most frequent is Ahmed Kamal (IICT, not on today's roster). King Saud University has been reported to give adjunct affiliations to foreign researchers, so some of these links may be affiliation-only; worth a sentence of caution. |
| **Nigeria: 113 papers** | same | Unusual partner | Covenant University and others, mainly with IICT and CECRI. Not checked further. |
| **Ahmed Kamal under three OpenAlex profiles** ("Ähmed Kamal" 84 papers, "Ahmed Kamal" 35 + 2) | `group24_data_extended.csv` | One person split in three | **FIXED (§3.5)** for the 84- and 35-paper profiles: 36 shared co-authors, never on the same paper. The 2-paper 2026 profile shares only 2 co-authors, below the rule, so it stays apart. |
| **8 citations from papers dated before 2016** | `citation_network.csv` | Dates look impossible | Only 2 are impossible: a 1970 and a 2008 paper citing 2022–23 papers (OpenAlex metadata; one DOI encodes 2025). The other 6 are 2015 papers citing 2016 papers, which is normal for online-first. Year-wise tables use only 2016–2026, so none are counted. Left as is. |
| **IIT Hyderabad and Alagappa University ratios above 2** | `global_indian_universities.csv` | They cite the labs twice as much as the labs cite them | Possibly younger or smaller departments that draw on CSIR's chemistry; not checked. Alagappa University is in Karaikudi, next to CECRI. |
| **B. Sridhar (IICT) is now the most productive scientist: 329 papers** | `faculty_performance.csv` | Was 9 papers before §3.5 | Real, but read it carefully: he is IICT's X-ray crystallographer, and 260 of the 329 papers list him as a middle author (crystal structures for other groups' syntheses). He ranks first by paper count, not by leadership of the work. |
| **Some scientists are still split** (e.g. Rajesh G. Gonnade vs a 5-paper "Rajesh C. Gonnade" profile) | `faculty_master.csv` | Undercounts | The merge rule needs compatible initials and ≥ 3 shared co-authors, so near-misses stay apart. `python -m src.collect.19_roster_cleanup --propose` writes every candidate to `data/review/author_profile_merge_candidates.csv`; to merge one, add it to `config/overrides/author_profile_merges.csv` and re-run Steps 19–20. |

---

## 5. What I could not verify

- **Peers' raw counts.** I could only check them for plausibility: DICP about 1,700 papers a year, ORNL about 2,900, KRICT about 560, IISc about 2,460 articles and reviews a year. The checkout has no cache, so I couldn't re-run Steps 22 and 23.
- **The early-2016 China share.** A proper share needs a query for papers with a known country, which needs the API.
- **The IICT and CECRI rosters.** I couldn't check them against their annual reports; only NCL's report was used.

---

## 6. How to reproduce and check

```bash
cd dpcn_a2
python -m src.collect.19_roster_cleanup --propose   # list split-profile candidates (data/review/)
python -m src.collect.19_roster_cleanup      # roster artefacts, designations, profile merges; a second run does nothing
python -m src.collect.20_dedupe_papers       # recompute faculty paper counts and h-indices
python -m src.collect.22_global_peers --offline   # re-apply exclusions without the API
python run.py insight11 && python run.py stats && python run.py dashboard
pytest -q                                     # 100 passed, 4 skipped (withdrawn studies)
python scripts/test_browser.py                # all pages, zero console errors
```

Files changed by this audit:
- **Data:** `data/final/faculty_master.csv`, `group24_data.csv`, `group24_data_extended.csv`, `authorship_network.csv`, `global/candidates.csv`, `global/peers.csv`.
- **Configuration:** `config/overrides/global_peer_exclusions.csv`, `config/overrides/author_profile_merges.csv` (new).
- **Code:** `src/collect/02_build_roster.py`, `07_match_faculty.py`, `19_roster_cleanup.py`, `20_dedupe_papers.py`, `src/stats/insights/common.py`, `s11_claims.py`, `s11_data_cleaning_audit.py`, `s11_information_diffusion.py`, `22_global_peers.py`, `src/stats/global_benchmark.py`, `src/dashboard/build_global.py`, `dashboard/js/global.js`, `dashboard/js/app.js`.
- **Outputs:** the tables and payloads they produce.
- **Docs:** D-40 and D-41 in `docs/DECISIONS.md`, `docs/LIMITATIONS.md`, `docs/DATA_DICTIONARY.md`.
