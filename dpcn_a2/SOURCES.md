# Data Sources — Group 24

**DPCN Research Mapping Project 2026** · CSIR-NCL (Pune), CSIR-IICT (Hyderabad), CSIR-CECRI (Karaikudi) · publications 2016–2026

This file lists every source the Group 24 dataset, statistics report and dashboard were built from.
All 14,352 papers, their DOIs, citation counts, authors, affiliations and research topics come from **OpenAlex**.
The faculty roster comes from the three institutes' **official websites**, and journal quartiles from **SCImago Journal Rank**.
No data was taken from other groups.

## 1. Summary

| Source | What we took from it | Accessed |
|---|---|---|
| [OpenAlex](https://openalex.org) (API `https://api.openalex.org`) | Papers 2016–2026, DOIs, citation counts, authors and affiliations, journals/conferences, topics, references and citing works, author career histories | 2026-10-13 (corpus); 2026-10-20 (links with other Indian institutions); October 2026 (Insights fetches) |
| [ROR](https://ror.org) (Research Organization Registry, API v2) | Persistent identifiers of the three labs and CSIR, used to find their OpenAlex IDs; RORs of partner institutions | 2026-10-13 |
| Institute websites (NCL, IICT, CECRI) | Faculty roster: names, designations, departments/divisions | October 2026 |
| [SCImago Journal Rank](https://www.scimagojr.com), via the [`sjrdata`](https://github.com/ikashnitsky/sjrdata) package | Journal best quartile (Q1–Q4) per year | October 2026 |
| [CORE conference rankings](https://portal.core.edu.au/conf-ranks/) | Not imported: conference papers are left unranked (see §6) | — |

## 2. OpenAlex (primary source)

OpenAlex is an open catalogue of scholarly works (data released under CC0). We queried its REST API through our own
client (`src/common/openalex.py`): cursor paging, `select=` to fetch only the needed fields, and every response cached
so re-runs make no new calls. Default corpus (`core`).

**Institution IDs**

| Lab | OpenAlex | ROR |
|---|---|---|
| CSIR-NCL | [I3125981224](https://openalex.org/I3125981224) | [057mn3690](https://ror.org/057mn3690) |
| CSIR-IICT | [I55664587](https://openalex.org/I55664587) | [040dky007](https://ror.org/040dky007) |
| CSIR-CECRI | [I106349282](https://openalex.org/I106349282) | [01qek3q18](https://ror.org/01qek3q18) |
| CSIR (parent, recall check only) | [I66760702](https://openalex.org/I66760702) | [021wm7p51](https://ror.org/021wm7p51) |

**Queries**

| Purpose | Endpoint and filter | Pipeline step |
|---|---|---|
| Resolve each lab's OpenAlex entity from its ROR | `/institutions?filter=ror:<ROR>` | `src/collect/01_resolve_institutions.py` |
| Yearly reference counts per lab | `/works?filter=authorships.institutions.id:<ID>,publication_year:2016-2026&group_by=publication_year` | 01 |
| All works per lab and year, 2016–2026 | `/works?filter=authorships.institutions.id:<ID>,publication_year:<year>` | `03_pull_works.py` |
| Papers tagged only with the CSIR parent whose affiliation text names a lab | `/works?filter=authorships.institutions.id:I66760702,raw_affiliation_strings.search:<lab name>` | `04_recall_boosters.py` |
| References and authorships of our papers | `/works?filter=openalex_id:W1\|…\|W100` | `17_indian_links_api.py`, `18_reference_counts.py` |
| Indian-affiliated papers our papers cite | `/works?filter=cited_by:W1\|…,authorships.countries:IN` | 17 |
| Indian-affiliated papers citing our papers | `/works?filter=cites:W1\|…,authorships.countries:IN` | 17 |
| Yearly citations of candidate "sleeping beauties" (Insight 7) | `/works?filter=openalex_id:…&select=id,publication_year,counts_by_year` | `fetch_counts_by_year.py` |
| Full career histories of roster scientists (Insights 9–10) | `/works?filter=authorships.author.id:<A…>` | `fetch_author_careers.py` |

**Fields used**: work ID, DOI, title, publication year, type, `cited_by_count` (the `citations` column), authorships
(author IDs and names, institutions with ROR and country, raw affiliation strings), primary location (journal or
conference source, ISSN), primary topic (topic, subfield, field, domain), `referenced_works`, `counts_by_year`.

## 3. Institute websites (faculty roster)

Scientific-cadre faculty (Scientist to Chief Scientist and Director) were taken from each lab's official staff
listing, then matched to OpenAlex author IDs (`02_build_roster.py`, `07_match_faculty.py`, `19_roster_cleanup.py`).

| Lab | Page | Taken |
|---|---|---|
| CSIR-NCL | [academic.ncl.res.in/alphascientist](http://academic.ncl.res.in/alphascientist) | Scientist list with division |
| CSIR-IICT | [iict.res.in/DEPARTMENTS](https://www.iict.res.in/DEPARTMENTS), [iict.res.in/SCIENTIFIC_STAFF](https://www.iict.res.in/SCIENTIFIC_STAFF) | Scientists by R&D department |
| CSIR-CECRI | [Staff Directory PDF](https://www.cecri.res.in/Portals/0/rti/Staff_Directory.pdf) (cecri.res.in, RTI section) | Scientists and divisions, extracted with `pdftotext` |

Manual roster corrections (duplicate listings, wrong author matches) are listed with reasons and dates in
`config/overrides/roster_overrides.csv`; excluded non-faculty entries are in `data/review/roster_excluded.csv`.

## 4. Journal quartiles — SCImago Journal Rank (SJR)

- **Data**: `sjr_journals.rda` from the [`sjrdata`](https://github.com/ikashnitsky/sjrdata) R package v1.0.25
  (I. Kashnitsky), which redistributes SCImago's yearly journal rankings from [scimagojr.com](https://www.scimagojr.com)
  (SCImago, based on Scopus data). Stored as `data/external/sjr_journals.rda`, SHA-256 `b70669804d0532b6ed7d009ae74fb9a68a11b549410bb591cbccbc8fe7d8ad72`
  (identical to the file in the package's GitHub repository).
- **Use**: a paper's `quartile` is the journal's SJR *best quartile* in the paper's publication year, matched on ISSN
  (`08_resolve_quartiles.py`). 2026 papers use the 2025 ranking; a journal missing in that year takes the nearest year
  within ±2. Of 14,166 journal papers: 13,251 matched by ISSN, 231 by
  nearest year, 684 unranked.
- `data/external/scimagojr_2023.csv` (the 2023 export downloaded from scimagojr.com) is kept for reference but not
  used by the pipeline.

## 5. Indian institutions

Co-author and citing/cited institutions are OpenAlex institution records with country code `IN`, identified by
their ROR IDs. `config/indian_inst_registry.csv` lists them with a sector label (IIT, NIT, CSIR, DAE, university, …)
assigned from the institution name by `src/common/sectors.py`.

## 6. Conference ranks — CORE

The assignment asks for CORE ranks (A*/A/B/C) for conference papers. CORE ranks mainly computer-science venues, and
no CORE rankings file was imported, so the `quartile` column is blank for all 186 conference papers
(Appendix B lists their venues).

## 7. Sources not used

Scopus, Web of Science / JCR quartiles, Google Scholar, IRINS/VIDWAN and Crossref were not used as data sources.
DOIs are as recorded by OpenAlex.

## Appendix A — Journals (1,892)

Every journal in which at least one of the 14,352 papers appeared, with the number of distinct papers.
Names, ISSNs and source IDs are from OpenAlex. 17 journal papers have no venue name in OpenAlex.

| Venue | ISSN | OpenAlex source | Papers |
|---|---|---|---:|
| ChemistrySelect | 2365-6549 | [S4210221416](https://openalex.org/S4210221416) | 443 |
| New Journal of Chemistry | 0398-9836 | [S36793815](https://openalex.org/S36793815) | 270 |
| RSC Advances | 2046-2069 | [S2481244646](https://openalex.org/S2481244646) | 245 |
| Chemical Communications | 1359-7345 | [S152760256](https://openalex.org/S152760256) | 239 |
| Organic & Biomolecular Chemistry | 1477-0520 | [S179810352](https://openalex.org/S179810352) | 225 |
| The Journal of Organic Chemistry | 0022-3263 | [S205050996](https://openalex.org/S205050996) | 225 |
| Organic Letters | 1523-7052 | [S201989124](https://openalex.org/S201989124) | 195 |
| ACS Omega | 2470-1343 | [S4210239500](https://openalex.org/S4210239500) | 178 |
| ChemInform | 0009-2975 | [S41354064](https://openalex.org/S41354064) | 176 |
| Tetrahedron Letters | 0040-4039 | [S133942674](https://openalex.org/S133942674) | 166 |
| ACS Applied Materials & Interfaces | 1944-8244 | [S164001016](https://openalex.org/S164001016) | 160 |
| European Journal of Organic Chemistry | 1099-0690 | [S21317199](https://openalex.org/S21317199) | 148 |
| The Journal of Physical Chemistry C | 1932-7447 | [S95739953](https://openalex.org/S95739953) | 129 |
| International Journal of Hydrogen Energy | 0360-3199 | [S48860480](https://openalex.org/S48860480) | 124 |
| Journal of Materials Chemistry A | 2050-7488 | [S2764437742](https://openalex.org/S2764437742) | 119 |
| ACS Applied Energy Materials | 2574-0962 | [S4210188958](https://openalex.org/S4210188958) | 116 |
| Chemistry - An Asian Journal | 1861-471X | [S188582317](https://openalex.org/S188582317) | 110 |
| Journal of Molecular Structure | 0022-2860 | [S203479135](https://openalex.org/S203479135) | 108 |
| Bioresource Technology | 0960-8524 | [S21442059](https://openalex.org/S21442059) | 100 |
| Scientific Reports | 2045-2322 | [S196734849](https://openalex.org/S196734849) | 100 |
| Chemical Engineering Journal | 1385-8947 | [S149937609](https://openalex.org/S149937609) | 99 |
| Electrochimica Acta | 0013-4686 | [S198339081](https://openalex.org/S198339081) | 97 |
| Bioorganic & Medicinal Chemistry Letters | 0960-894X | [S30970080](https://openalex.org/S30970080) | 92 |
| Physical Chemistry Chemical Physics | 1463-9076 | [S181332294](https://openalex.org/S181332294) | 90 |
| Inorganic Chemistry | 0020-1669 | [S171072222](https://openalex.org/S171072222) | 87 |
| ACS Sustainable Chemistry & Engineering | 2168-0485 | [S2502047864](https://openalex.org/S2502047864) | 86 |
| International Journal of Biological Macromolecules | 0141-8130 | [S83853393](https://openalex.org/S83853393) | 84 |
| Energy & Fuels | 0887-0624 | [S186935893](https://openalex.org/S186935893) | 83 |
| Applied Surface Science | 0169-4332 | [S42323631](https://openalex.org/S42323631) | 82 |
| Journal of Alloys and Compounds | 0925-8388 | [S67716761](https://openalex.org/S67716761) | 79 |
| Small | 1613-6810 | [S94619837](https://openalex.org/S94619837) | 79 |
| ACS Applied Nano Materials | 2574-0970 | [S4210191493](https://openalex.org/S4210191493) | 74 |
| Asian Journal of Organic Chemistry | 2193-5807 | [S2491942749](https://openalex.org/S2491942749) | 71 |
| Chemistry - A European Journal | 0947-6539 | [S68911691](https://openalex.org/S68911691) | 70 |
| Nanoscale | 2040-3364 | [S23181512](https://openalex.org/S23181512) | 70 |
| Journal of Materials Science Materials in Electronics | 0957-4522 | [S189509794](https://openalex.org/S189509794) | 69 |
| European Journal of Medicinal Chemistry | 0223-5234 | [S4210169613](https://openalex.org/S4210169613) | 68 |
| Synthesis | 0039-7881 | [S197964166](https://openalex.org/S197964166) | 68 |
| Dalton Transactions | 1477-9226 | [S166159787](https://openalex.org/S166159787) | 67 |
| Sustainable Energy & Fuels | 2398-4902 | [S2764650158](https://openalex.org/S2764650158) | 66 |
| Advanced Synthesis & Catalysis | 1615-4150 | [S36069537](https://openalex.org/S36069537) | 65 |
| Angewandte Chemie | 0044-8249 | [S4210200754](https://openalex.org/S4210200754) | 65 |
| Angewandte Chemie International Edition | 1433-7851 | [S67393510](https://openalex.org/S67393510) | 65 |
| Industrial & Engineering Chemistry Research | 0888-5885 | [S202680183](https://openalex.org/S202680183) | 65 |
| Synthetic Communications | 0039-7911 | [S114976158](https://openalex.org/S114976158) | 64 |
| Catalysis Letters | 1011-372X | [S7359802](https://openalex.org/S7359802) | 63 |
| Catalysis Science & Technology | 2044-4753 | [S2482773761](https://openalex.org/S2482773761) | 61 |
| Crystal Growth & Design | 1528-7483 | [S16561315](https://openalex.org/S16561315) | 60 |
| CrystEngComm | 1466-8033 | [S95865439](https://openalex.org/S95865439) | 60 |
| Journal of Chemical Sciences | 0253-4134 | [S185986200](https://openalex.org/S185986200) | 60 |
| Journal of The Electrochemical Society | 0013-4651 | [S138759888](https://openalex.org/S138759888) | 60 |
| Tetrahedron | 0040-4020 | [S205754296](https://openalex.org/S205754296) | 60 |
| Bioorganic Chemistry | 0045-2068 | [S165482960](https://openalex.org/S165482960) | 59 |
| Langmuir | 0743-7463 | [S75741262](https://openalex.org/S75741262) | 59 |
| Journal of Energy Storage | 2352-152X | [S2764865925](https://openalex.org/S2764865925) | 58 |
| The Journal of Physical Chemistry B | 1520-5207 | [S185621672](https://openalex.org/S185621672) | 58 |
| Journal of environmental chemical engineering | 2213-2929 | [S2764859491](https://openalex.org/S2764859491) | 56 |
| ChemCatChem | 1867-3880 | [S206633562](https://openalex.org/S206633562) | 55 |
| Materials Letters | 0167-577X | [S55626769](https://openalex.org/S55626769) | 53 |
| Green Chemistry | 1463-9262 | [S55009144](https://openalex.org/S55009144) | 51 |
| Materials Chemistry and Physics | 0254-0584 | [S5707928](https://openalex.org/S5707928) | 51 |
| ACS Catalysis | 2155-5435 | [S37391459](https://openalex.org/S37391459) | 49 |
| ChemElectroChem | 2196-0216 | [S4210214564](https://openalex.org/S4210214564) | 49 |
| Ceramics International | 0272-8842 | [S106928643](https://openalex.org/S106928643) | 48 |
| Synlett | 0936-5214 | [S80698544](https://openalex.org/S80698544) | 48 |
| Journal of Applied Polymer Science | 0021-8995 | [S200764475](https://openalex.org/S200764475) | 46 |
| Journal of Power Sources | 0378-7753 | [S177147899](https://openalex.org/S177147899) | 46 |
| Molecular Catalysis | 2468-8231 | [S2764968843](https://openalex.org/S2764968843) | 44 |
| Chemical Science | 2041-6520 | [S184645833](https://openalex.org/S184645833) | 43 |
| ACS Applied Bio Materials | 2576-6422 | [S4210214000](https://openalex.org/S4210214000) | 42 |
| Journal of Materials Chemistry C | 2050-7526 | [S2500738039](https://openalex.org/S2500738039) | 41 |
| Acta Crystallographica Section A Foundations and Advances | 2053-2733 | [S4393918093](https://openalex.org/S4393918093) | 39 |
| Biomass Conversion and Biorefinery | 2190-6815 | [S2764923638](https://openalex.org/S2764923638) | 38 |
| Catalysis Communications | 1566-7367 | [S48346357](https://openalex.org/S48346357) | 38 |
| Materials Today Proceedings | 2214-7853 | [S2898407351](https://openalex.org/S2898407351) | 38 |
| Research on Chemical Intermediates | 0922-6168 | [S89199708](https://openalex.org/S89199708) | 37 |
| Journal of Colloid and Interface Science | 0021-9797 | [S204609040](https://openalex.org/S204609040) | 36 |
| Journal of Biomolecular Structure and Dynamics | 0739-1102 | [S178711970](https://openalex.org/S178711970) | 34 |
| Journal of Electroanalytical Chemistry | 1572-6657 | [S143604795](https://openalex.org/S143604795) | 34 |
| Environmental Science and Pollution Research | 0944-1344 | [S87561820](https://openalex.org/S87561820) | 33 |
| Journal of Heterocyclic Chemistry | 0022-152X | [S46134040](https://openalex.org/S46134040) | 32 |
| Journal of the American Chemical Society | 0002-7863 | [S111155417](https://openalex.org/S111155417) | 32 |
| Natural Product Research | 1478-6419 | [S205999849](https://openalex.org/S205999849) | 32 |
| ACS Applied Polymer Materials | 2637-6105 | [S4210221646](https://openalex.org/S4210221646) | 31 |
| Journal of Photochemistry and Photobiology A Chemistry | 1010-6030 | [S102276873](https://openalex.org/S102276873) | 31 |
| Materials Advances | 2633-5409 | [S4210182508](https://openalex.org/S4210182508) | 31 |
| Journal of Molecular Liquids | 0167-7322 | [S189140625](https://openalex.org/S189140625) | 30 |
| Materials Research Express | 2053-1591 | [S4210216311](https://openalex.org/S4210216311) | 30 |
| Medicinal Chemistry Research | 1054-2523 | [S36909932](https://openalex.org/S36909932) | 30 |
| Sensors and Actuators B Chemical | 0925-4005 | [S98455728](https://openalex.org/S98455728) | 30 |
| Solar Energy | 0038-092X | [S5745031](https://openalex.org/S5745031) | 30 |
| Advanced Sustainable Systems | 2366-7486 | [S4210217307](https://openalex.org/S4210217307) | 28 |
| Asian Journal of Chemistry | 0970-7077 | [S194824834](https://openalex.org/S194824834) | 28 |
| Journal of Nanoscience and Nanotechnology | 1533-4880 | [S133947007](https://openalex.org/S133947007) | 28 |
| Applied Catalysis A General | 0926-860X | [S84179801](https://openalex.org/S84179801) | 27 |
| Catalysis Today | 0920-5861 | [S117279562](https://openalex.org/S117279562) | 27 |
| Journal of Cleaner Production | 0959-6526 | [S58516903](https://openalex.org/S58516903) | 27 |
| Journal of Materials Chemistry B | 2050-750X | [S2479884170](https://openalex.org/S2479884170) | 27 |
| Materials Science and Engineering C | 0928-4931 | [S43139658](https://openalex.org/S43139658) | 27 |
| Progress in Organic Coatings | 0300-9440 | [S41155759](https://openalex.org/S41155759) | 27 |
| The Journal of Chemical Physics | 0021-9606 | [S77047749](https://openalex.org/S77047749) | 27 |
| ARKIVOC | 1551-7004 | [S116969037](https://openalex.org/S116969037) | 26 |
| ChemMedChem | 1860-7179 | [S136164820](https://openalex.org/S136164820) | 26 |
| Industrial Crops and Products | 0926-6690 | [S178362034](https://openalex.org/S178362034) | 26 |
| Rapid Communications in Mass Spectrometry | 0951-4198 | [S89689683](https://openalex.org/S89689683) | 26 |
| The Chemical Record | 1527-8999 | [S134994606](https://openalex.org/S134994606) | 26 |
| Chemosphere | 0045-6535 | [S203465130](https://openalex.org/S203465130) | 25 |
| Energy Technology | 2194-4288 | [S2765059294](https://openalex.org/S2765059294) | 25 |
| Inorganic Chemistry Communications | 1387-7003 | [S166634186](https://openalex.org/S166634186) | 25 |
| Ionics | 0947-7047 | [S137979523](https://openalex.org/S137979523) | 25 |
| Organic Chemistry Frontiers | 2052-4110 | [S2764884854](https://openalex.org/S2764884854) | 25 |
| Bulletin of Materials Science | 0250-4707 | [S99612230](https://openalex.org/S99612230) | 24 |
| Carbon | 0008-6223 | [S188605413](https://openalex.org/S188605413) | 24 |
| Microchemical Journal | 0026-265X | [S151030190](https://openalex.org/S151030190) | 24 |
| Organometallics | 0276-7333 | [S4924609](https://openalex.org/S4924609) | 24 |
| Colloids and Surfaces A Physicochemical and Engineering Aspects | 0927-7757 | [S94313546](https://openalex.org/S94313546) | 23 |
| Fuel | 0016-2361 | [S164770093](https://openalex.org/S164770093) | 23 |
| Molecular Diversity | 1381-1991 | [S105791650](https://openalex.org/S105791650) | 23 |
| Molecules | 1420-3049 | [S108911230](https://openalex.org/S108911230) | 23 |
| The Science of The Total Environment | 0048-9697 | [S86852077](https://openalex.org/S86852077) | 23 |
| Applied Catalysis B: Environmental | 0926-3373 | [S134307298](https://openalex.org/S134307298) | 22 |
| ChemPhysChem | 1439-4235 | [S169445072](https://openalex.org/S169445072) | 22 |
| Journal of Solid State Electrochemistry | 1432-8488 | [S25422132](https://openalex.org/S25422132) | 22 |
| Microporous and Mesoporous Materials | 1387-1811 | [S52195378](https://openalex.org/S52195378) | 22 |
| Organic Process Research & Development | 1083-6160 | [S107255770](https://openalex.org/S107255770) | 22 |
| Process Safety and Environmental Protection | 0263-8762 | [S166351637](https://openalex.org/S166351637) | 22 |
| 3 Biotech | 2190-572X | [S4210190239](https://openalex.org/S4210190239) | 21 |
| ChemPlusChem | 2192-6506 | [S163199293](https://openalex.org/S163199293) | 21 |
| ChemSusChem | 1864-5631 | [S193447295](https://openalex.org/S193447295) | 21 |
| Journal of the Indian Chemical Society | 0019-4522 | [S2765077160](https://openalex.org/S2765077160) | 21 |
| Materials Chemistry Frontiers | 2052-1537 | [S2765048856](https://openalex.org/S2765048856) | 21 |
| Reaction Chemistry & Engineering | 2058-9883 | [S2764466794](https://openalex.org/S2764466794) | 21 |
| Renewable Energy | 0960-1481 | [S815301](https://openalex.org/S815301) | 21 |
| SN Applied Sciences | 2523-3963 | [S4210234597](https://openalex.org/S4210234597) | 21 |
| The Journal of Physical Chemistry Letters | 1948-7185 | [S123480357](https://openalex.org/S123480357) | 21 |
| Batteries & Supercaps | 2566-6223 | [S4210241147](https://openalex.org/S4210241147) | 20 |
| Bioorganic & Medicinal Chemistry | 0968-0896 | [S10422866](https://openalex.org/S10422866) | 20 |
| Chemistry of Materials | 0897-4756 | [S66104727](https://openalex.org/S66104727) | 20 |
| Colloids and Surfaces B Biointerfaces | 0927-7765 | [S22793308](https://openalex.org/S22793308) | 20 |
| Journal of Chemical & Engineering Data | 0021-9568 | [S204459408](https://openalex.org/S204459408) | 20 |
| Journal of Industrial and Engineering Chemistry | 1226-086X | [S145420111](https://openalex.org/S145420111) | 20 |
| Journal of Natural Products | 0163-3864 | [S166799026](https://openalex.org/S166799026) | 20 |
| Letters in Organic Chemistry | 1570-1786 | [S55953343](https://openalex.org/S55953343) | 20 |
| Materials Research Bulletin | 0025-5408 | [S138530117](https://openalex.org/S138530117) | 20 |
| Materials Science and Engineering B | 0921-5107 | [S4210190818](https://openalex.org/S4210190818) | 20 |
| ACS Chemical Neuroscience | 1948-7193 | [S180465690](https://openalex.org/S180465690) | 19 |
| Dyes and Pigments | 0143-7208 | [S137084839](https://openalex.org/S137084839) | 19 |
| European Polymer Journal | 0014-3057 | [S135472351](https://openalex.org/S135472351) | 19 |
| Journal of Hazardous Materials | 0304-3894 | [S145089992](https://openalex.org/S145089992) | 19 |
| Journal of Macromolecular Science Part A | 1060-1325 | [S4210184698](https://openalex.org/S4210184698) | 19 |
| Journal of Polymer Science Part A Polymer Chemistry | 0887-624X | [S92465984](https://openalex.org/S92465984) | 19 |
| Chemical Data Collections | 2405-8300 | [S2898359974](https://openalex.org/S2898359974) | 18 |
| Current Science | 0011-3891 | [S29607422](https://openalex.org/S29607422) | 18 |
| Current Topics in Medicinal Chemistry | 1568-0266 | [S107732428](https://openalex.org/S107732428) | 18 |
| ECS Meeting Abstracts | 1091-8213 | [S4210168594](https://openalex.org/S4210168594) | 18 |
| Heliyon | 2405-8440 | [S2898612692](https://openalex.org/S2898612692) | 18 |
| Molecular Pharmaceutics | 1543-8384 | [S204562082](https://openalex.org/S204562082) | 18 |
| Nanoscale Advances | 2516-0230 | [S4210240921](https://openalex.org/S4210240921) | 18 |
| PLoS ONE | 1932-6203 | [S202381698](https://openalex.org/S202381698) | 18 |
| Results in Chemistry | 2211-7156 | [S4210212333](https://openalex.org/S4210212333) | 18 |
| Biochemistry | 0006-2960 | [S104038378](https://openalex.org/S104038378) | 17 |
| Indian Journal of Chemistry | 0019-5103 | [S4387282313](https://openalex.org/S4387282313) | 17 |
| Journal of Magnetism and Magnetic Materials | 0304-8853 | [S3649266](https://openalex.org/S3649266) | 17 |
| Journal of Materials Science | 0022-2461 | [S26125866](https://openalex.org/S26125866) | 17 |
| Journal of Pharmaceutical and Biomedical Analysis | 0731-7085 | [S174893293](https://openalex.org/S174893293) | 17 |
| Materials Today Chemistry | 2468-5194 | [S2898120712](https://openalex.org/S2898120712) | 17 |
| MedChemComm | 2040-2503 | [S191926780](https://openalex.org/S191926780) | 17 |
| Polymer | 0032-3861 | [S186054908](https://openalex.org/S186054908) | 17 |
| Surfaces and Interfaces | 2468-0230 | [S2764987357](https://openalex.org/S2764987357) | 17 |
| SynOpen | 2509-9396 | [S4210211857](https://openalex.org/S4210211857) | 17 |
| Applied Physics A | 0947-8396 | [S52123058](https://openalex.org/S52123058) | 16 |
| Biocatalysis and Agricultural Biotechnology | 1878-8181 | [S2764378920](https://openalex.org/S2764378920) | 16 |
| Biochemical and Biophysical Research Communications | 0006-291X | [S151589183](https://openalex.org/S151589183) | 16 |
| Biomass and Bioenergy | 0961-9534 | [S171918450](https://openalex.org/S171918450) | 16 |
| Carbohydrate Research | 0008-6215 | [S34126442](https://openalex.org/S34126442) | 16 |
| Emergent Materials | 2522-5731 | [S4210216082](https://openalex.org/S4210216082) | 16 |
| Journal of CO2 Utilization | 2212-9820 | [S4210172371](https://openalex.org/S4210172371) | 16 |
| Journal of Medicinal Chemistry | 0022-2623 | [S162030435](https://openalex.org/S162030435) | 16 |
| Microchimica Acta | 0026-3672 | [S12065667](https://openalex.org/S12065667) | 16 |
| Nanomedicine | 1743-5889 | [S4210216406](https://openalex.org/S4210216406) | 16 |
| Nature Communications | 2041-1723 | [S64187185](https://openalex.org/S64187185) | 16 |
| Polymers for Advanced Technologies | 1042-7147 | [S40708307](https://openalex.org/S40708307) | 16 |
| Process Biochemistry | 0032-9592 | [S173499201](https://openalex.org/S173499201) | 16 |
| Separation and Purification Technology | 1383-5866 | [S69753523](https://openalex.org/S69753523) | 16 |
| ACS Applied Engineering Materials | 2771-9545 | [S4387282792](https://openalex.org/S4387282792) | 15 |
| Advanced Functional Materials | 1616-301X | [S135204980](https://openalex.org/S135204980) | 15 |
| Biomaterials Science | 2047-4830 | [S2494179437](https://openalex.org/S2494179437) | 15 |
| Catalysts | 2073-4344 | [S2738539744](https://openalex.org/S2738539744) | 15 |
| Chemical Physics Letters | 0009-2614 | [S44567922](https://openalex.org/S44567922) | 15 |
| Coordination Chemistry Reviews | 0010-8545 | [S117186765](https://openalex.org/S117186765) | 15 |
| European Journal of Inorganic Chemistry | 1099-0682 | [S16435181](https://openalex.org/S16435181) | 15 |
| Indian Chemical Engineer | 0019-4506 | [S43990833](https://openalex.org/S43990833) | 15 |
| Journal of Drug Delivery Science and Technology | 1773-2247 | [S97205441](https://openalex.org/S97205441) | 15 |
| Journal of Physics and Chemistry of Solids | 0022-3697 | [S171512606](https://openalex.org/S171512606) | 15 |
| Journal of Porphyrins and Phthalocyanines | 1088-4246 | [S56437793](https://openalex.org/S56437793) | 15 |
| Soft Matter | 1744-683X | [S6377669](https://openalex.org/S6377669) | 15 |
| Biochemical Engineering Journal | 1369-703X | [S168210271](https://openalex.org/S168210271) | 14 |
| Biosensors and Bioelectronics | 0956-5663 | [S156181945](https://openalex.org/S156181945) | 14 |
| Energy Storage | 2578-4862 | [S4210199075](https://openalex.org/S4210199075) | 14 |
| Journal of Membrane Science | 0376-7388 | [S119469986](https://openalex.org/S119469986) | 14 |
| Journal of Organometallic Chemistry | 0022-328X | [S108008259](https://openalex.org/S108008259) | 14 |
| Journal of Water Process Engineering | 2214-7144 | [S2764434589](https://openalex.org/S2764434589) | 14 |
| Life Sciences | 0024-3205 | [S175775512](https://openalex.org/S175775512) | 14 |
| ACS Applied Electronic Materials | 2637-6113 | [S4210217399](https://openalex.org/S4210217399) | 13 |
| Acta Crystallographica Section E Crystallographic Communications | 2056-9890 | [S2739106167](https://openalex.org/S2739106167) | 13 |
| Advanced Materials | 0935-9648 | [S99352657](https://openalex.org/S99352657) | 13 |
| Advanced Materials Interfaces | 2196-7350 | [S2764385675](https://openalex.org/S2764385675) | 13 |
| Analytical Methods | 1759-9660 | [S170358085](https://openalex.org/S170358085) | 13 |
| Chemical Engineering and Processing - Process Intensification | 0255-2701 | [S94212472](https://openalex.org/S94212472) | 13 |
| Chemical Engineering Science | 0009-2509 | [S33892871](https://openalex.org/S33892871) | 13 |
| ChemNanoMat | 2199-692X | [S4210190284](https://openalex.org/S4210190284) | 13 |
| ChemPhotoChem | 2367-0932 | [S4210205840](https://openalex.org/S4210205840) | 13 |
| Electroanalysis | 1040-0397 | [S79832926](https://openalex.org/S79832926) | 13 |
| Energy Advances | 2753-1457 | [S4210221295](https://openalex.org/S4210221295) | 13 |
| Journal of Flow Chemistry | 2062-249X | [S2500698275](https://openalex.org/S2500698275) | 13 |
| Journal of Porous Materials | 1380-2224 | [S19938693](https://openalex.org/S19938693) | 13 |
| Journal of Proteomics | 1874-3919 | [S100014387](https://openalex.org/S100014387) | 13 |
| Materials Today Communications | 2352-4928 | [S2765035490](https://openalex.org/S2765035490) | 13 |
| Polymer International | 0959-8103 | [S162033819](https://openalex.org/S162033819) | 13 |
| Renewable and Sustainable Energy Reviews | 1364-0321 | [S68497187](https://openalex.org/S68497187) | 13 |
| Waste and Biomass Valorization | 1877-2641 | [S31817463](https://openalex.org/S31817463) | 13 |
| ACS Biomaterials Science & Engineering | 2373-9878 | [S2764739176](https://openalex.org/S2764739176) | 12 |
| Arabian Journal of Chemistry | 1878-5352 | [S2357026](https://openalex.org/S2357026) | 12 |
| Archiv der Pharmazie | 0365-6233 | [S174911965](https://openalex.org/S174911965) | 12 |
| Beilstein Journal of Organic Chemistry | 1860-5397 | [S13215905](https://openalex.org/S13215905) | 12 |
| Bioresource Technology Reports | 2589-014X | [S2898243299](https://openalex.org/S2898243299) | 12 |
| Carbohydrate Polymers | 0144-8617 | [S64311837](https://openalex.org/S64311837) | 12 |
| Catalysis in Green Chemistry and Engineering | 2572-9896 | [S4210178110](https://openalex.org/S4210178110) | 12 |
| Chemistry and Physics of Lipids | 0009-3084 | [S99078529](https://openalex.org/S99078529) | 12 |
| Desalination and Water Treatment | 1944-3986 | [S124203677](https://openalex.org/S124203677) | 12 |
| International Journal of Energy Research | 0363-907X | [S32776067](https://openalex.org/S32776067) | 12 |
| Journal of Cluster Science | 1040-7278 | [S107691304](https://openalex.org/S107691304) | 12 |
| Journal of Fluorescence | 1053-0509 | [S98273654](https://openalex.org/S98273654) | 12 |
| Journal of Mass Spectrometry | 1076-5174 | [S37349105](https://openalex.org/S37349105) | 12 |
| Journal of Polymer Research | 1022-9760 | [S103518591](https://openalex.org/S103518591) | 12 |
| Macromolecules | 0024-9297 | [S177196338](https://openalex.org/S177196338) | 12 |
| Materials Science in Semiconductor Processing | 1369-8001 | [S82126420](https://openalex.org/S82126420) | 12 |
| Natural Product Communications | 1555-9475 | [S124250138](https://openalex.org/S124250138) | 12 |
| Polymer Engineering and Science | 0032-3888 | [S114499311](https://openalex.org/S114499311) | 12 |
| Russian Journal of General Chemistry | 1070-3632 | [S95954025](https://openalex.org/S95954025) | 12 |
| Separation Science Plus | 2573-1815 | [S4210212791](https://openalex.org/S4210212791) | 12 |
| Biomedical Materials | 1748-6041 | [S110088896](https://openalex.org/S110088896) | 11 |
| Chemical Biology & Drug Design | 1747-0277 | [S123587420](https://openalex.org/S123587420) | 11 |
| Chemistry & Biodiversity | 1612-1872 | [S206700086](https://openalex.org/S206700086) | 11 |
| European Journal of Mass Spectrometry | 1356-1049 | [S4210216295](https://openalex.org/S4210216295) | 11 |
| Food Chemistry | 0308-8146 | [S98026630](https://openalex.org/S98026630) | 11 |
| Frontiers in Chemistry | 2296-2646 | [S2764970645](https://openalex.org/S2764970645) | 11 |
| Journal of Catalysis | 0021-9517 | [S1959426](https://openalex.org/S1959426) | 11 |
| Journal of Photochemistry and Photobiology B Biology | 1011-1344 | [S148303206](https://openalex.org/S148303206) | 11 |
| Journal of Saudi Chemical Society | 1319-6103 | [S77754710](https://openalex.org/S77754710) | 11 |
| Optical Materials | 0925-3467 | [S199247034](https://openalex.org/S199247034) | 11 |
| Surface and Coatings Technology | 0257-8972 | [S76010543](https://openalex.org/S76010543) | 11 |
| Tetrahedron Asymmetry | 0957-4166 | [S88152556](https://openalex.org/S88152556) | 11 |
| Analytical and Bioanalytical Chemistry | 1618-2642 | [S18188872](https://openalex.org/S18188872) | 10 |
| Anti-Cancer Agents in Medicinal Chemistry | 1568-0118 | [S159246083](https://openalex.org/S159246083) | 10 |
| Applied Biochemistry and Biotechnology | 0273-2289 | [S153285774](https://openalex.org/S153285774) | 10 |
| Applied Materials Today | 2352-9407 | [S2764609219](https://openalex.org/S2764609219) | 10 |
| Applied Microbiology and Biotechnology | 0175-7598 | [S70979998](https://openalex.org/S70979998) | 10 |
| Applied Organometallic Chemistry | 0268-2605 | [S134627157](https://openalex.org/S134627157) | 10 |
| Cellular Signalling | 0898-6568 | [S113768434](https://openalex.org/S113768434) | 10 |
| Chemical Engineering & Technology | 0930-7516 | [S154487680](https://openalex.org/S154487680) | 10 |
| Chemical Papers | 0366-6352 | [S201842594](https://openalex.org/S201842594) | 10 |
| eLife | 2050-084X | [S1336409049](https://openalex.org/S1336409049) | 10 |
| Environmental Progress & Sustainable Energy | 1944-7442 | [S4210214890](https://openalex.org/S4210214890) | 10 |
| Helvetica Chimica Acta | 0018-019X | [S181847678](https://openalex.org/S181847678) | 10 |
| Journal of Environmental Management | 0301-4797 | [S44455300](https://openalex.org/S44455300) | 10 |
| Journal of Physics D Applied Physics | 0022-3727 | [S111927887](https://openalex.org/S111927887) | 10 |
| Journal of the Taiwan Institute of Chemical Engineers | 1876-1070 | [S156280905](https://openalex.org/S156280905) | 10 |
| Macromolecular Chemistry and Physics | 1022-1352 | [S124744586](https://openalex.org/S124744586) | 10 |
| Monatshefte für Chemie - Chemical Monthly | 0026-9247 | [S98631280](https://openalex.org/S98631280) | 10 |
| Nano-Structures & Nano-Objects | 2352-507X | [S2764574320](https://openalex.org/S2764574320) | 10 |
| Photochemical & Photobiological Sciences | 1474-905X | [S65504228](https://openalex.org/S65504228) | 10 |
| Polycyclic aromatic compounds | 1026-7743 | [S178924077](https://openalex.org/S178924077) | 10 |
| Polyhedron | 0277-5387 | [S171616156](https://openalex.org/S171616156) | 10 |
| Results in Engineering | 2590-1230 | [S4210226253](https://openalex.org/S4210226253) | 10 |
| RSC Medicinal Chemistry | 2632-8682 | [S4210227295](https://openalex.org/S4210227295) | 10 |
| The Journal of Membrane Biology | 0022-2631 | [S967762373](https://openalex.org/S967762373) | 10 |
| World Journal of Microbiology and Biotechnology | 0959-3993 | [S55229178](https://openalex.org/S55229178) | 10 |
| Advanced Energy Materials | 1614-6832 | [S2502627819](https://openalex.org/S2502627819) | 9 |
| Biochimica et Biophysica Acta (BBA) - General Subjects | 0304-4165 | [S4210238601](https://openalex.org/S4210238601) | 9 |
| Biophysical Journal | 0006-3495 | [S98085912](https://openalex.org/S98085912) | 9 |
| Data in Brief | 2352-3409 | [S2481029507](https://openalex.org/S2481029507) | 9 |
| Drug Development Research | 0272-4391 | [S26306840](https://openalex.org/S26306840) | 9 |
| FEBS Journal | 1742-464X | [S37672443](https://openalex.org/S37672443) | 9 |
| Inorganica Chimica Acta | 0020-1693 | [S112227793](https://openalex.org/S112227793) | 9 |
| International Immunopharmacology | 1567-5769 | [S158377717](https://openalex.org/S158377717) | 9 |
| International Journal of Chemical Kinetics | 0538-8066 | [S207430280](https://openalex.org/S207430280) | 9 |
| Letters in Drug Design & Discovery | 1570-1808 | [S106940122](https://openalex.org/S106940122) | 9 |
| Materials Science for Energy Technologies | 2589-2991 | [S2898569932](https://openalex.org/S2898569932) | 9 |
| Nanomaterials | 2079-4991 | [S2764646681](https://openalex.org/S2764646681) | 9 |
| Nucleic Acids Research | 0305-1048 | [S134668137](https://openalex.org/S134668137) | 9 |
| Polymer Bulletin | 0170-0839 | [S111277402](https://openalex.org/S111277402) | 9 |
| Small Methods | 2366-9608 | [S4210232622](https://openalex.org/S4210232622) | 9 |
| The Journal of Physical Chemistry A | 1089-5639 | [S146709414](https://openalex.org/S146709414) | 9 |
| ACS Medicinal Chemistry Letters | 1948-5875 | [S191852912](https://openalex.org/S191852912) | 8 |
| ACS Pharmacology & Translational Science | 2575-9108 | [S4210207642](https://openalex.org/S4210207642) | 8 |
| Applied Petrochemical Research | 2190-5525 | [S2764713139](https://openalex.org/S2764713139) | 8 |
| Applied Surface Science Advances | 2666-5239 | [S4210213426](https://openalex.org/S4210213426) | 8 |
| Archives of Microbiology | 0003-9276 | [S111869560](https://openalex.org/S111869560) | 8 |
| Biomaterials Advances | 2772-9508 | [S4210239156](https://openalex.org/S4210239156) | 8 |
| Biomedicine & Pharmacotherapy | 0753-3322 | [S15111687](https://openalex.org/S15111687) | 8 |
| BioNanoScience | 2191-1630 | [S4210168380](https://openalex.org/S4210168380) | 8 |
| Biophysical Chemistry | 0301-4622 | [S63395545](https://openalex.org/S63395545) | 8 |
| Catalysis Reviews | 0161-4940 | [S72781473](https://openalex.org/S72781473) | 8 |
| ChemBioChem | 1439-4227 | [S154285657](https://openalex.org/S154285657) | 8 |
| Communications Chemistry | 2399-3669 | [S4210191625](https://openalex.org/S4210191625) | 8 |
| Computational and Theoretical Chemistry | 2210-271X | [S137947318](https://openalex.org/S137947318) | 8 |
| Environmental Research | 0013-9351 | [S173943867](https://openalex.org/S173943867) | 8 |
| Frontiers in Microbiology | 1664-302X | [S2484704948](https://openalex.org/S2484704948) | 8 |
| Future Medicinal Chemistry | 1756-8919 | [S122867665](https://openalex.org/S122867665) | 8 |
| International Journal of Environmental Science and Technology | 1735-1472 | [S85680945](https://openalex.org/S85680945) | 8 |
| Journal of Applied Electrochemistry | 0021-891X | [S111985066](https://openalex.org/S111985066) | 8 |
| Journal of Applied Physics | 0021-8979 | [S187991544](https://openalex.org/S187991544) | 8 |
| Journal of Asian Natural Products Research | 1028-6020 | [S201142877](https://openalex.org/S201142877) | 8 |
| Journal of Proteins and Proteomics | 0975-8151 | [S2764942636](https://openalex.org/S2764942636) | 8 |
| Materials Today Energy | 2468-6069 | [S2898308537](https://openalex.org/S2898308537) | 8 |
| Molecular BioSystems | 1742-2051 | [S169293703](https://openalex.org/S169293703) | 8 |
| Pharmacognosy Magazine | 0973-1296 | [S40318847](https://openalex.org/S40318847) | 8 |
| Proteins Structure Function and Bioinformatics | 0887-3585 | [S121161810](https://openalex.org/S121161810) | 8 |
| Solid State Sciences | 1293-2558 | [S40206742](https://openalex.org/S40206742) | 8 |
| Sustainable Chemistry and Pharmacy | 2352-5541 | [S2898513339](https://openalex.org/S2898513339) | 8 |
| The Canadian Journal of Chemical Engineering | 0008-4034 | [S83557516](https://openalex.org/S83557516) | 8 |
| Ultrasonics Sonochemistry | 1350-4177 | [S130447213](https://openalex.org/S130447213) | 8 |
| Vacuum | 0042-207X | [S86481247](https://openalex.org/S86481247) | 8 |
| Advanced Powder Technology | 0921-8831 | [S9304834](https://openalex.org/S9304834) | 7 |
| Advanced Science | 2198-3844 | [S2737737698](https://openalex.org/S2737737698) | 7 |
| Advances in Colloid and Interface Science | 0001-8686 | [S28247071](https://openalex.org/S28247071) | 7 |
| Analytical Chemistry | 0003-2700 | [S191963794](https://openalex.org/S191963794) | 7 |
| Biochimica et Biophysica Acta (BBA) - Molecular Cell Research | 0167-4889 | [S4210226410](https://openalex.org/S4210226410) | 7 |
| Biochimica et Biophysica Acta (BBA) - Proteins and Proteomics | 1570-9639 | [S4210222880](https://openalex.org/S4210222880) | 7 |
| Bioconjugate Chemistry | 1043-1802 | [S155115410](https://openalex.org/S155115410) | 7 |
| Bioelectrochemistry | 1567-5394 | [S99498898](https://openalex.org/S99498898) | 7 |
| Cellulose | 0969-0239 | [S130536152](https://openalex.org/S130536152) | 7 |
| Clean Technologies and Environmental Policy | 1618-954X | [S101593883](https://openalex.org/S101593883) | 7 |
| Current Environmental Engineering | 2212-7178 | [S4210181111](https://openalex.org/S4210181111) | 7 |
| Current Organic Synthesis | 1570-1794 | [S107400764](https://openalex.org/S107400764) | 7 |
| Diamond and Related Materials | 0925-9635 | [S124577123](https://openalex.org/S124577123) | 7 |
| Energy & Environmental Science | 1754-5692 | [S117082959](https://openalex.org/S117082959) | 7 |
| Fitoterapia | 0367-326X | [S44811770](https://openalex.org/S44811770) | 7 |
| FlatChem | 2452-2627 | [S2898578437](https://openalex.org/S2898578437) | 7 |
| Free Radical Biology and Medicine | 0891-5849 | [S128018148](https://openalex.org/S128018148) | 7 |
| Frontiers in Pharmacology | 1663-9812 | [S132108250](https://openalex.org/S132108250) | 7 |
| IEEE Sensors Journal | 1530-437X | [S189694085](https://openalex.org/S189694085) | 7 |
| International Journal of Nanomedicine | 1176-9114 | [S101287785](https://openalex.org/S101287785) | 7 |
| International Journal of Pharmaceutics | 0378-5173 | [S131016564](https://openalex.org/S131016564) | 7 |
| iScience | 2589-0042 | [S2898358376](https://openalex.org/S2898358376) | 7 |
| IUCrJ | 2052-2525 | [S2737064587](https://openalex.org/S2737064587) | 7 |
| Journal of Biological Chemistry | 0021-9258 | [S140251998](https://openalex.org/S140251998) | 7 |
| Journal of ISAS | 2583-5459 | [S4387288564](https://openalex.org/S4387288564) | 7 |
| Journal of Macromolecular Science Part B | 0022-2348 | [S118630506](https://openalex.org/S118630506) | 7 |
| Journal of materials research/Pratt's guide to venture capital sources | 0884-1616 | [S19730638](https://openalex.org/S19730638) | 7 |
| Journal of Polymers and the Environment | 1064-7546 | [S193665811](https://openalex.org/S193665811) | 7 |
| Journal of Sol-Gel Science and Technology | 0928-0707 | [S146449914](https://openalex.org/S146449914) | 7 |
| Microbial Pathogenesis | 0882-4010 | [S113190374](https://openalex.org/S113190374) | 7 |
| Next Materials | 2949-8228 | [S4387287712](https://openalex.org/S4387287712) | 7 |
| Optik | 0030-4026 | [S201441698](https://openalex.org/S201441698) | 7 |
| physica status solidi (a) | 0031-8965 | [S4210228582](https://openalex.org/S4210228582) | 7 |
| Physical review. B./Physical review. B | 2469-9950 | [S4210237713](https://openalex.org/S4210237713) | 7 |
| Phytomedicine | 0944-7113 | [S180051340](https://openalex.org/S180051340) | 7 |
| Polymer Chemistry | 1759-9954 | [S187215728](https://openalex.org/S187215728) | 7 |
| Reactive and Functional Polymers | 1381-5148 | [S205957783](https://openalex.org/S205957783) | 7 |
| RSC Sustainability | 2753-8125 | [S4387281083](https://openalex.org/S4387281083) | 7 |
| Russian Journal of Organic Chemistry | 0022-3271 | [S73388172](https://openalex.org/S73388172) | 7 |
| Spectrochimica Acta Part A Molecular and Biomolecular Spectroscopy | 1386-1425 | [S96873385](https://openalex.org/S96873385) | 7 |
| Topics in Catalysis | 1022-5528 | [S176313377](https://openalex.org/S176313377) | 7 |
| ACS Materials Letters | 2639-4979 | [S4210213087](https://openalex.org/S4210213087) | 6 |
| ACS Nano | 1936-0851 | [S145476921](https://openalex.org/S145476921) | 6 |
| ACS Sustainable Resource Management | 2837-1445 | [S4389158299](https://openalex.org/S4389158299) | 6 |
| Advanced Optical Materials | 2195-1071 | [S108229257](https://openalex.org/S108229257) | 6 |
| AMB Express | 2191-0855 | [S129630946](https://openalex.org/S129630946) | 6 |
| Biocatalysis and Biotransformation | 1024-2422 | [S946611601](https://openalex.org/S946611601) | 6 |
| Biochimica et Biophysica Acta (BBA) - Molecular Basis of Disease | 0925-4439 | [S4210173099](https://openalex.org/S4210173099) | 6 |
| Biotechnology Progress | 1520-6033 | [S186451451](https://openalex.org/S186451451) | 6 |
| Catalysis Surveys from Asia | 1571-1013 | [S50978397](https://openalex.org/S50978397) | 6 |
| Chemical Engineering Communications | 0098-6445 | [S140963590](https://openalex.org/S140963590) | 6 |
| Chemical Research in Toxicology | 0893-228X | [S152840809](https://openalex.org/S152840809) | 6 |
| Chemico-Biological Interactions | 0009-2797 | [S34460812](https://openalex.org/S34460812) | 6 |
| Composites Part B Engineering | 1359-8368 | [S112674977](https://openalex.org/S112674977) | 6 |
| Computational Biology and Chemistry | 1476-9271 | [S104924063](https://openalex.org/S104924063) | 6 |
| Computers & Chemical Engineering | 0098-1354 | [S150671403](https://openalex.org/S150671403) | 6 |
| Computers in Biology and Medicine | 0010-4825 | [S44278595](https://openalex.org/S44278595) | 6 |
| Construction and Building Materials | 0950-0618 | [S29980478](https://openalex.org/S29980478) | 6 |
| CORROSION | 0010-9312 | [S149373597](https://openalex.org/S149373597) | 6 |
| Current Microbiology | 0343-8651 | [S2248630](https://openalex.org/S2248630) | 6 |
| Current Organic Chemistry | 1385-2728 | [S88154163](https://openalex.org/S88154163) | 6 |
| Cytotherapy | 1465-3249 | [S36838616](https://openalex.org/S36838616) | 6 |
| Energy | 0360-5442 | [S2497375143](https://openalex.org/S2497375143) | 6 |
| Gene Reports | 2452-0144 | [S2765063225](https://openalex.org/S2765063225) | 6 |
| Grasas y Aceites | 0017-3495 | [S193671726](https://openalex.org/S193671726) | 6 |
| Indian Journal of Microbiology | 0046-8991 | [S73816448](https://openalex.org/S73816448) | 6 |
| International Microbiology | 1139-6709 | [S146978284](https://openalex.org/S146978284) | 6 |
| Journal of AOAC International | 1060-3271 | [S103486911](https://openalex.org/S103486911) | 6 |
| Journal of Ayurveda and Integrative Medicine | 0975-9476 | [S24510010](https://openalex.org/S24510010) | 6 |
| Journal of Carbohydrate Chemistry | 0732-8303 | [S207432870](https://openalex.org/S207432870) | 6 |
| Journal of Electronic Materials | 0361-5235 | [S127985767](https://openalex.org/S127985767) | 6 |
| Journal of Energy Chemistry | 2095-4956 | [S2500128275](https://openalex.org/S2500128275) | 6 |
| Journal of Inorganic and Organometallic Polymers and Materials | 1053-0495 | [S22507861](https://openalex.org/S22507861) | 6 |
| Journal of Molecular Catalysis A Chemical | 1381-1169 | [S52459750](https://openalex.org/S52459750) | 6 |
| Journal of Separation Science | 1615-9306 | [S45406943](https://openalex.org/S45406943) | 6 |
| Journal of Solution Chemistry | 0095-9782 | [S121410566](https://openalex.org/S121410566) | 6 |
| Molecular Biology Reports | 0301-4851 | [S197962172](https://openalex.org/S197962172) | 6 |
| NeuroMolecular Medicine | 1535-1084 | [S45104802](https://openalex.org/S45104802) | 6 |
| Organic Electronics | 1566-1199 | [S99846442](https://openalex.org/S99846442) | 6 |
| Photochemistry and Photobiology | 0031-8655 | [S61245073](https://openalex.org/S61245073) | 6 |
| Physica B Condensed Matter | 0921-4526 | [S34296711](https://openalex.org/S34296711) | 6 |
| Physics of Fluids | 1070-6631 | [S22862804](https://openalex.org/S22862804) | 6 |
| Phytochemistry | 0031-9422 | [S88226677](https://openalex.org/S88226677) | 6 |
| Polymers | 2073-4360 | [S123288148](https://openalex.org/S123288148) | 6 |
| Proceedings of the National Academy of Sciences | 0027-8424 | [S125754415](https://openalex.org/S125754415) | 6 |
| Resonance | 0971-8044 | [S4210208472](https://openalex.org/S4210208472) | 6 |
| Sensors and Actuators A Physical | 0924-4247 | [S16945967](https://openalex.org/S16945967) | 6 |
| Separation Science and Technology | 0149-6395 | [S197355279](https://openalex.org/S197355279) | 6 |
| Solar Energy Materials and Solar Cells | 0927-0248 | [S166040772](https://openalex.org/S166040772) | 6 |
| Solar RRL | 2367-198X | [S4210176222](https://openalex.org/S4210176222) | 6 |
| Solid State Ionics | 0167-2738 | [S101472891](https://openalex.org/S101472891) | 6 |
| Synthetic Metals | 0379-6779 | [S171076697](https://openalex.org/S171076697) | 6 |
| Transactions of the Indian Institute of Metals | 0972-2815 | [S4210202889](https://openalex.org/S4210202889) | 6 |
| Zenodo (CERN European Organization for Nuclear Research) |  | [S4306400562](https://openalex.org/S4306400562) | 6 |
| AAPS PharmSciTech | 1530-9932 | [S1234972](https://openalex.org/S1234972) | 5 |
| Acta Crystallographica Section B Structural Science Crystal Engineering and Materials | 2052-5192 | [S4210168249](https://openalex.org/S4210168249) | 5 |
| Acta Crystallographica Section C Structural Chemistry | 2053-2296 | [S4393918092](https://openalex.org/S4393918092) | 5 |
| Advanced Materials Technologies | 2365-709X | [S2765038284](https://openalex.org/S2765038284) | 5 |
| AIP Advances | 2158-3226 | [S189917590](https://openalex.org/S189917590) | 5 |
| Analytical Chemistry Letters | 2229-7928 | [S2764633598](https://openalex.org/S2764633598) | 5 |
| Arabian Journal for Science and Engineering | 1319-8025 | [S4210185304](https://openalex.org/S4210185304) | 5 |
| Biochemical Pharmacology | 0006-2952 | [S185534594](https://openalex.org/S185534594) | 5 |
| Biomacromolecules | 1525-7797 | [S11629336](https://openalex.org/S11629336) | 5 |
| Biomedical Chromatography | 0269-3879 | [S123979729](https://openalex.org/S123979729) | 5 |
| Bioprocess and Biosystems Engineering | 1615-7591 | [S137312515](https://openalex.org/S137312515) | 5 |
| Cell Communication and Signaling | 1478-811X | [S138104925](https://openalex.org/S138104925) | 5 |
| Chemical Physics Impact | 2667-0224 | [S4210212133](https://openalex.org/S4210212133) | 5 |
| Chirality | 0899-0042 | [S67976470](https://openalex.org/S67976470) | 5 |
| Chromatographia | 0009-5893 | [S6712347](https://openalex.org/S6712347) | 5 |
| Colloid & Polymer Science | 0303-402X | [S100444939](https://openalex.org/S100444939) | 5 |
| Comptes Rendus Chimie | 1631-0748 | [S176166730](https://openalex.org/S176166730) | 5 |
| Current Catalysis | 2211-5447 | [S4210184777](https://openalex.org/S4210184777) | 5 |
| European Journal of Lipid Science and Technology | 1438-7697 | [S106501229](https://openalex.org/S106501229) | 5 |
| European Journal of Pharmacology | 0014-2999 | [S187816532](https://openalex.org/S187816532) | 5 |
| Food Research International | 0963-9969 | [S38919146](https://openalex.org/S38919146) | 5 |
| Frontiers in Immunology | 1664-3224 | [S2595292759](https://openalex.org/S2595292759) | 5 |
| Gene | 0378-1119 | [S75702506](https://openalex.org/S75702506) | 5 |
| Green Chemistry Letters and Reviews | 1751-7192 | [S197698500](https://openalex.org/S197698500) | 5 |
| Heterocyclic Communications | 0793-0283 | [S68667125](https://openalex.org/S68667125) | 5 |
| High Performance Polymers | 0954-0083 | [S165151903](https://openalex.org/S165151903) | 5 |
| Inorganic Chemistry Frontiers | 2052-1545 | [S2764402489](https://openalex.org/S2764402489) | 5 |
| International Journal of Molecular Sciences | 1422-0067 | [S10623703](https://openalex.org/S10623703) | 5 |
| INTERNATIONAL JOURNAL OF SYSTEMATIC AND EVOLUTIONARY MICROBIOLOGY | 1466-5026 | [S102181007](https://openalex.org/S102181007) | 5 |
| Journal of Agricultural and Food Chemistry | 0021-8561 | [S134644764](https://openalex.org/S134644764) | 5 |
| Journal of Applied Microbiology | 1364-5072 | [S39794811](https://openalex.org/S39794811) | 5 |
| Journal of Applied Toxicology | 0260-437X | [S81851855](https://openalex.org/S81851855) | 5 |
| Journal of Biosciences | 0250-5991 | [S65171370](https://openalex.org/S65171370) | 5 |
| Journal of Biotechnology | 0168-1656 | [S182099265](https://openalex.org/S182099265) | 5 |
| Journal of Food Science and Technology | 0022-1155 | [S4210169910](https://openalex.org/S4210169910) | 5 |
| Journal of King Saud University - Science | 1018-3647 | [S163784168](https://openalex.org/S163784168) | 5 |
| Journal of Materials Engineering and Performance | 1059-9495 | [S70681891](https://openalex.org/S70681891) | 5 |
| Journal of Molecular Graphics and Modelling | 1093-3263 | [S76694907](https://openalex.org/S76694907) | 5 |
| Journal of Molecular Modeling | 0948-5023 | [S113170167](https://openalex.org/S113170167) | 5 |
| Journal of Plant Growth Regulation | 0721-7595 | [S129665955](https://openalex.org/S129665955) | 5 |
| Journal of Solid State Chemistry | 0022-4596 | [S168898714](https://openalex.org/S168898714) | 5 |
| Journal of Surfactants and Detergents | 1097-3958 | [S91430365](https://openalex.org/S91430365) | 5 |
| Journal of the American Oil Chemists Society | 0003-021X | [S38637062](https://openalex.org/S38637062) | 5 |
| Journal of the Iranian Chemical Society | 1735-207X | [S165434857](https://openalex.org/S165434857) | 5 |
| Journal of Thermal Analysis and Calorimetry | 1388-6150 | [S58867329](https://openalex.org/S58867329) | 5 |
| Liquid Crystals | 0267-8292 | [S15647332](https://openalex.org/S15647332) | 5 |
| Materials | 1996-1944 | [S18714766](https://openalex.org/S18714766) | 5 |
| Materials Today Sustainability | 2589-2347 | [S4210183045](https://openalex.org/S4210183045) | 5 |
| Microbiological Research | 0944-5013 | [S106450229](https://openalex.org/S106450229) | 5 |
| Mini-Reviews in Medicinal Chemistry | 1389-5575 | [S162475533](https://openalex.org/S162475533) | 5 |
| Molecular and Cellular Biochemistry | 0300-8177 | [S11742566](https://openalex.org/S11742566) | 5 |
| Molecular Physics | 0026-8976 | [S204809294](https://openalex.org/S204809294) | 5 |
| Nano Energy | 2211-2855 | [S2497301991](https://openalex.org/S2497301991) | 5 |
| Nanotechnology | 0957-4484 | [S206811868](https://openalex.org/S206811868) | 5 |
| Naunyn-Schmiedeberg s Archives of Pharmacology | 0028-1298 | [S159534381](https://openalex.org/S159534381) | 5 |
| Physical Review A | 0556-2791 | [S164566984](https://openalex.org/S164566984) | 5 |
| Physiology and Molecular Biology of Plants | 0971-5894 | [S197197320](https://openalex.org/S197197320) | 5 |
| Russian Journal of Bioorganic Chemistry | 1068-1620 | [S68845364](https://openalex.org/S68845364) | 5 |
| The Analyst | 0003-2654 | [S105746325](https://openalex.org/S105746325) | 5 |
| Trends in biotechnology | 0167-7799 | [S147849156](https://openalex.org/S147849156) | 5 |
| Accounts of Chemical Research | 0001-4842 | [S145378405](https://openalex.org/S145378405) | 4 |
| ACS Combinatorial Science | 2156-8944 | [S977305210](https://openalex.org/S977305210) | 4 |
| Acta Physiologiae Plantarum | 0137-5881 | [S194146006](https://openalex.org/S194146006) | 4 |
| Advanced Healthcare Materials | 2192-2640 | [S2500736452](https://openalex.org/S2500736452) | 4 |
| Advanced Therapeutics | 2366-3987 | [S4210200121](https://openalex.org/S4210200121) | 4 |
| Analytica Chimica Acta | 0003-2670 | [S192559872](https://openalex.org/S192559872) | 4 |
| APOPTOSIS | 1360-8185 | [S120502300](https://openalex.org/S120502300) | 4 |
| Applied Energy | 0306-2619 | [S109565702](https://openalex.org/S109565702) | 4 |
| Applied Nanoscience | 2190-5509 | [S2764818521](https://openalex.org/S2764818521) | 4 |
| Applied Sciences | 2076-3417 | [S4210205812](https://openalex.org/S4210205812) | 4 |
| Archives of Biochemistry and Biophysics | 0003-9861 | [S153476765](https://openalex.org/S153476765) | 4 |
| Biochemistry and Biophysics Reports | 2405-5808 | [S2764640729](https://openalex.org/S2764640729) | 4 |
| Biomarkers | 1354-750X | [S7166883](https://openalex.org/S7166883) | 4 |
| Biotechnology Letters | 0141-5492 | [S113993733](https://openalex.org/S113993733) | 4 |
| Cellular and Molecular Neurobiology | 0272-4340 | [S33948212](https://openalex.org/S33948212) | 4 |
| Chemical Physics | 0301-0104 | [S190037396](https://openalex.org/S190037396) | 4 |
| Chemical Product and Process Modeling | 1934-2659 | [S56901069](https://openalex.org/S56901069) | 4 |
| ChemistryOpen | 2191-1363 | [S2488117985](https://openalex.org/S2488117985) | 4 |
| Clinical Epidemiology and Global Health | 2213-3984 | [S2764432518](https://openalex.org/S2764432518) | 4 |
| Current Applied Physics | 1567-1739 | [S159232998](https://openalex.org/S159232998) | 4 |
| Current Bioactive Compounds | 1573-4072 | [S197782650](https://openalex.org/S197782650) | 4 |
| DOAJ (DOAJ: Directory of Open Access Journals) |  | [S4306401280](https://openalex.org/S4306401280) | 4 |
| Energies | 1996-1073 | [S198098182](https://openalex.org/S198098182) | 4 |
| Energy Reports | 2352-4847 | [S2898434319](https://openalex.org/S2898434319) | 4 |
| Environmental Chemistry Letters | 1610-3653 | [S88719806](https://openalex.org/S88719806) | 4 |
| Environmental Pollution | 0269-7491 | [S201530359](https://openalex.org/S201530359) | 4 |
| Environmental Technology & Innovation | 2352-1864 | [S2764865870](https://openalex.org/S2764865870) | 4 |
| European Journal of Nutrition & Food Safety | 2347-5641 | [S4210215897](https://openalex.org/S4210215897) | 4 |
| European Journal of Pharmaceutical Sciences | 0928-0987 | [S119477091](https://openalex.org/S119477091) | 4 |
| Food Analytical Methods | 1936-9751 | [S190445914](https://openalex.org/S190445914) | 4 |
| Food Science & Nutrition | 2048-7177 | [S2764587058](https://openalex.org/S2764587058) | 4 |
| Frontiers in Oncology | 2234-943X | [S2596394214](https://openalex.org/S2596394214) | 4 |
| Indian Journal of Chemical Technology | 0971-457X | [S127420649](https://openalex.org/S127420649) | 4 |
| Indian Journal of Pharmaceutical Sciences | 0250-474X | [S87963693](https://openalex.org/S87963693) | 4 |
| Indian Journal of Physics | 0019-5480 | [S195338471](https://openalex.org/S195338471) | 4 |
| Inflammation Research | 1023-3830 | [S55943811](https://openalex.org/S55943811) | 4 |
| International Journal of Polymeric Materials | 0091-4037 | [S176437474](https://openalex.org/S176437474) | 4 |
| IOSR Journal of Mechanical and Civil Engineering | 2278-1684 | [S2764381940](https://openalex.org/S2764381940) | 4 |
| Iranian Polymer Journal | 1026-1265 | [S32218721](https://openalex.org/S32218721) | 4 |
| Journal of Cellular Physiology | 0021-9541 | [S43643205](https://openalex.org/S43643205) | 4 |
| Journal of Chemical Technology & Biotechnology | 0142-0356 | [S112095004](https://openalex.org/S112095004) | 4 |
| Journal of Chromatography A | 0021-9673 | [S176136234](https://openalex.org/S176136234) | 4 |
| Journal of Chromatography B | 1570-0232 | [S103248676](https://openalex.org/S103248676) | 4 |
| Journal of Coatings Technology and Research | 1547-0091 | [S4210172278](https://openalex.org/S4210172278) | 4 |
| Journal of Energy and Environmental Sustainability | 2455-2259 | [S4210181181](https://openalex.org/S4210181181) | 4 |
| Journal of Nanoparticle Research | 1388-0764 | [S194298869](https://openalex.org/S194298869) | 4 |
| Journal of Photochemistry and Photobiology | 2666-4690 | [S4210219111](https://openalex.org/S4210219111) | 4 |
| Journal of the mechanical behavior of biomedical materials/Journal of mechanical behavior of biomedical materials | 1751-6161 | [S100249163](https://openalex.org/S100249163) | 4 |
| Journal of Vector Borne Diseases | 0972-9062 | [S158746746](https://openalex.org/S158746746) | 4 |
| LWT | 0023-6438 | [S26760650](https://openalex.org/S26760650) | 4 |
| Magnetic Resonance in Chemistry | 0749-1581 | [S112856106](https://openalex.org/S112856106) | 4 |
| Microbiology Resource Announcements | 2576-098X | [S4210232526](https://openalex.org/S4210232526) | 4 |
| Molecular Carcinogenesis | 0899-1987 | [S133439003](https://openalex.org/S133439003) | 4 |
| Neuroscience | 0306-4522 | [S30122339](https://openalex.org/S30122339) | 4 |
| Next research. | 3050-4759 | [S4404663819](https://openalex.org/S4404663819) | 4 |
| Particle & Particle Systems Characterization | 0934-0866 | [S2437199](https://openalex.org/S2437199) | 4 |
| Physica E Low-dimensional Systems and Nanostructures | 1386-9477 | [S23074404](https://openalex.org/S23074404) | 4 |
| Physical Sciences Reviews | 2365-6581 | [S2764778717](https://openalex.org/S2764778717) | 4 |
| Phytochemistry Letters | 1874-3900 | [S127984601](https://openalex.org/S127984601) | 4 |
| Phytomedicine Plus | 2667-0313 | [S4210212705](https://openalex.org/S4210212705) | 4 |
| PLANT PHYSIOLOGY | 0032-0889 | [S42294715](https://openalex.org/S42294715) | 4 |
| Plant Physiology and Biochemistry | 0981-9428 | [S115455909](https://openalex.org/S115455909) | 4 |
| Planta | 0032-0935 | [S193523036](https://openalex.org/S193523036) | 4 |
| Probiotics and Antimicrobial Proteins | 1867-1306 | [S163406742](https://openalex.org/S163406742) | 4 |
| Revista de Fomento Social | 0370-0046 | [S4210226164](https://openalex.org/S4210226164) | 4 |
| Royal Society Open Science | 2054-5703 | [S2737558550](https://openalex.org/S2737558550) | 4 |
| Sadhana | 0256-2499 | [S91650206](https://openalex.org/S91650206) | 4 |
| SAR and QSAR in environmental research | 1026-776X | [S56681374](https://openalex.org/S56681374) | 4 |
| Steroids | 0039-128X | [S70286497](https://openalex.org/S70286497) | 4 |
| Surface Engineering | 0267-0844 | [S2016056](https://openalex.org/S2016056) | 4 |
| Surface Science | 0039-6028 | [S137865625](https://openalex.org/S137865625) | 4 |
| Sustainable Chemistry for Climate Action | 2772-8269 | [S4220651145](https://openalex.org/S4220651145) | 4 |
| Sustainable materials and technologies | 2214-9929 | [S2898501196](https://openalex.org/S2898501196) | 4 |
| The International Journal of Biochemistry & Cell Biology | 1357-2725 | [S183320690](https://openalex.org/S183320690) | 4 |
| The Protein Journal | 1572-3887 | [S201049572](https://openalex.org/S201049572) | 4 |
| Thin Solid Films | 0040-6090 | [S84339699](https://openalex.org/S84339699) | 4 |
| Water Air & Soil Pollution | 0049-6979 | [S156652029](https://openalex.org/S156652029) | 4 |
| ACS Applied Optical Materials | 2771-9855 | [S4387282954](https://openalex.org/S4387282954) | 3 |
| ACS Energy Letters | 2380-8195 | [S2764414965](https://openalex.org/S2764414965) | 3 |
| ACS ES&T Water | 2690-0637 | [S4210201235](https://openalex.org/S4210201235) | 3 |
| ACS Macro Letters | 2161-1653 | [S75495113](https://openalex.org/S75495113) | 3 |
| ACS Materials Au | 2694-2461 | [S4210204497](https://openalex.org/S4210204497) | 3 |
| ACS Sensors | 2379-3694 | [S2764631046](https://openalex.org/S2764631046) | 3 |
| Acta Materialia | 1359-6454 | [S64016596](https://openalex.org/S64016596) | 3 |
| Advanced Composites and Hybrid Materials | 2522-0128 | [S4210207107](https://openalex.org/S4210207107) | 3 |
| Advanced Electronic Materials | 2199-160X | [S2765003236](https://openalex.org/S2765003236) | 3 |
| Advanced Journal of Chemistry-Section A | 2645-5676 | [S4210178004](https://openalex.org/S4210178004) | 3 |
| Advances in Microbiology | 2165-3402 | [S4210205325](https://openalex.org/S4210205325) | 3 |
| AIChE Journal | 0001-1541 | [S147177414](https://openalex.org/S147177414) | 3 |
| AIMS Materials Science | 2372-0468 | [S4210234426](https://openalex.org/S4210234426) | 3 |
| Algal Research | 2211-9264 | [S2502055758](https://openalex.org/S2502055758) | 3 |
| Annals of Phytomedicine An International Journal | 2278-9839 | [S4210235516](https://openalex.org/S4210235516) | 3 |
| Antioxidants and Redox Signaling | 1523-0864 | [S88052261](https://openalex.org/S88052261) | 3 |
| Applied Clay Science | 0169-1317 | [S37411791](https://openalex.org/S37411791) | 3 |
| Applied Physics Letters | 0003-6951 | [S105243760](https://openalex.org/S105243760) | 3 |
| Asia-Pacific Journal of Chemical Engineering | 1932-2135 | [S196825396](https://openalex.org/S196825396) | 3 |
| Beilstein Journal of Nanotechnology | 2190-4286 | [S2504426957](https://openalex.org/S2504426957) | 3 |
| Biochimica et Biophysica Acta (BBA) - Biomembranes | 0005-2736 | [S4210187475](https://openalex.org/S4210187475) | 3 |
| BIOINFOLET - A Quarterly Journal of Life Sciences | 0973-1431 | [S2764452741](https://openalex.org/S2764452741) | 3 |
| Biomedical Physics & Engineering Express | 2057-1976 | [S2764445381](https://openalex.org/S2764445381) | 3 |
| Biopolymers | 0006-3525 | [S56808608](https://openalex.org/S56808608) | 3 |
| Biosensors | 2079-6374 | [S150925516](https://openalex.org/S150925516) | 3 |
| Biosensors and Bioelectronics X | 2590-1370 | [S4210214496](https://openalex.org/S4210214496) | 3 |
| Biotechnology Reports | 2215-017X | [S2764596916](https://openalex.org/S2764596916) | 3 |
| BMC Plant Biology | 1471-2229 | [S6444338](https://openalex.org/S6444338) | 3 |
| Brazilian Archives of Biology and Technology | 1516-8913 | [S175992573](https://openalex.org/S175992573) | 3 |
| Bulletin of the Korean Chemical Society | 0253-2964 | [S77209346](https://openalex.org/S77209346) | 3 |
| Carbohydrate Polymer Technologies and Applications | 2666-8939 | [S4210218043](https://openalex.org/S4210218043) | 3 |
| Characterization and Application of Nanomaterials | 2578-1995 | [S4210210482](https://openalex.org/S4210210482) | 3 |
| Chem | 2451-9294 | [S2898106599](https://openalex.org/S2898106599) | 3 |
| Chemical Reviews | 0009-2665 | [S41143188](https://openalex.org/S41143188) | 3 |
| Chemistry of Heterocyclic Compounds | 0009-3122 | [S110436767](https://openalex.org/S110436767) | 3 |
| Chemosensors | 2227-9040 | [S4210174123](https://openalex.org/S4210174123) | 3 |
| Clinica Chimica Acta | 0009-8981 | [S207549998](https://openalex.org/S207549998) | 3 |
| Clinical Proteomics | 1542-6416 | [S103738789](https://openalex.org/S103738789) | 3 |
| Corrosion Reviews | 0334-6005 | [S98033523](https://openalex.org/S98033523) | 3 |
| Corrosion Science | 0010-938X | [S96167972](https://openalex.org/S96167972) | 3 |
| Critical Reviews in Analytical Chemistry | 1040-8347 | [S93754354](https://openalex.org/S93754354) | 3 |
| Current Green Chemistry | 2213-3461 | [S4210188678](https://openalex.org/S4210188678) | 3 |
| Current Opinion in Green and Sustainable Chemistry | 2452-2236 | [S4210195801](https://openalex.org/S4210195801) | 3 |
| Drug Development and Industrial Pharmacy | 0363-9045 | [S162444473](https://openalex.org/S162444473) | 3 |
| Drying Technology | 0737-3937 | [S196498761](https://openalex.org/S196498761) | 3 |
| Ecotoxicology and Environmental Safety | 0147-6513 | [S13733787](https://openalex.org/S13733787) | 3 |
| ECS Journal of Solid State Science and Technology | 2162-8769 | [S2493531148](https://openalex.org/S2493531148) | 3 |
| Electrocatalysis | 1868-2529 | [S65231264](https://openalex.org/S65231264) | 3 |
| Emission Control Science and Technology | 2199-3629 | [S4210217539](https://openalex.org/S4210217539) | 3 |
| Energy Sources Part A Recovery Utilization and Environmental Effects | 1556-7036 | [S4210188153](https://openalex.org/S4210188153) | 3 |
| Environmental Science Advances | 2754-7000 | [S4210211247](https://openalex.org/S4210211247) | 3 |
| Environmental Science Water Research & Technology | 2053-1400 | [S4210190644](https://openalex.org/S4210190644) | 3 |
| Environmental Technology | 0959-3330 | [S37011080](https://openalex.org/S37011080) | 3 |
| Faraday Discussions | 1359-6640 | [S193234216](https://openalex.org/S193234216) | 3 |
| Food & Function | 2042-6496 | [S2483688756](https://openalex.org/S2483688756) | 3 |
| Food Bioscience | 2212-4292 | [S2764726840](https://openalex.org/S2764726840) | 3 |
| Free Radical Research | 1029-2470 | [S23349031](https://openalex.org/S23349031) | 3 |
| Frontiers in Bioengineering and Biotechnology | 2296-4185 | [S2595131146](https://openalex.org/S2595131146) | 3 |
| Fuel Cells | 1615-6846 | [S176175666](https://openalex.org/S176175666) | 3 |
| Gels | 2310-2861 | [S2737559645](https://openalex.org/S2737559645) | 3 |
| Green Materials | 2049-1220 | [S2764379853](https://openalex.org/S2764379853) | 3 |
| IET Nanobiotechnology | 1751-8741 | [S97987397](https://openalex.org/S97987397) | 3 |
| IJPAR JOURNAL | 2320-2831 | [S4387291778](https://openalex.org/S4387291778) | 3 |
| Inflammation | 0360-3997 | [S127393932](https://openalex.org/S127393932) | 3 |
| Inflammopharmacology | 0925-4692 | [S77466329](https://openalex.org/S77466329) | 3 |
| Insect Biochemistry and Molecular Biology | 0965-1748 | [S130917594](https://openalex.org/S130917594) | 3 |
| Insect Molecular Biology | 0962-1075 | [S137961447](https://openalex.org/S137961447) | 3 |
| International Journal of Chemical Reactor Engineering | 1542-6580 | [S61095757](https://openalex.org/S61095757) | 3 |
| International Journal of Current Microbiology and Applied Sciences | 2319-7692 | [S2765017008](https://openalex.org/S2765017008) | 3 |
| International Journal of Data Analytics | 2644-1705 | [S4210195268](https://openalex.org/S4210195268) | 3 |
| International Journal of Electrochemical Science | 1452-3981 | [S48583931](https://openalex.org/S48583931) | 3 |
| International Journal of Intelligent Systems and Applications in Engineering | 2147-6799 | [S2764360368](https://openalex.org/S2764360368) | 3 |
| International Journal of Quantum Chemistry | 0020-7608 | [S167203149](https://openalex.org/S167203149) | 3 |
| International Journal of Tropical Insect Science | 1742-7584 | [S6691161](https://openalex.org/S6691161) | 3 |
| International Polymer Processing | 0930-777X | [S1200972](https://openalex.org/S1200972) | 3 |
| JACS Au | 2691-3704 | [S4210207119](https://openalex.org/S4210207119) | 3 |
| JOM | 0148-6608 | [S116826539](https://openalex.org/S116826539) | 3 |
| Journal of Alzheimer s Disease | 1387-2877 | [S25155249](https://openalex.org/S25155249) | 3 |
| Journal of Applied Biology & Biotechnology | 2347-212X | [S4210205073](https://openalex.org/S4210205073) | 3 |
| Journal of Asia-Pacific Entomology | 1226-8615 | [S49593656](https://openalex.org/S49593656) | 3 |
| Journal of Cellular Biochemistry | 0730-2312 | [S53807158](https://openalex.org/S53807158) | 3 |
| Journal of Computational Chemistry | 0192-8651 | [S21117631](https://openalex.org/S21117631) | 3 |
| Journal of Coordination Chemistry | 0095-8972 | [S161439912](https://openalex.org/S161439912) | 3 |
| Journal of Ethnopharmacology | 0378-8741 | [S29564236](https://openalex.org/S29564236) | 3 |
| Journal of Experimental Botany | 0022-0957 | [S32610980](https://openalex.org/S32610980) | 3 |
| Journal of Inorganic Biochemistry | 0162-0134 | [S155362585](https://openalex.org/S155362585) | 3 |
| Journal of Marine Science and Application | 1671-9433 | [S2357814](https://openalex.org/S2357814) | 3 |
| Journal of Materials Research and Technology | 2214-0697 | [S2765010971](https://openalex.org/S2765010971) | 3 |
| Journal of Materials Science Materials in Engineering | 3004-8958 | [S5407042866](https://openalex.org/S5407042866) | 3 |
| Journal of Medical Microbiology | 0022-2615 | [S154078021](https://openalex.org/S154078021) | 3 |
| Journal of Neuroinflammation | 1742-2094 | [S199572710](https://openalex.org/S199572710) | 3 |
| Journal of Non-Crystalline Solids | 0022-3093 | [S59020844](https://openalex.org/S59020844) | 3 |
| Journal of Plastic Film & Sheeting | 1530-8014 | [S112475225](https://openalex.org/S112475225) | 3 |
| Journal of Proteome Research | 1535-3893 | [S74367812](https://openalex.org/S74367812) | 3 |
| Journal of Structural Biology | 1047-8477 | [S89954039](https://openalex.org/S89954039) | 3 |
| Journal of Superconductivity and Novel Magnetism | 1557-1939 | [S89963981](https://openalex.org/S89963981) | 3 |
| Journal of Visualized Experiments | 1940-087X | [S199738284](https://openalex.org/S199738284) | 3 |
| Letters in Applied Microbiology | 0266-8254 | [S171033905](https://openalex.org/S171033905) | 3 |
| Macromolecular Bioscience | 1616-5187 | [S182383103](https://openalex.org/S182383103) | 3 |
| Materials Circular Economy | 2524-8146 | [S4210179475](https://openalex.org/S4210179475) | 3 |
| Materials Horizons | 2051-6347 | [S2764386229](https://openalex.org/S2764386229) | 3 |
| Medical Mycology | 0268-1218 | [S93288122](https://openalex.org/S93288122) | 3 |
| Metabolomics | 1573-3882 | [S82228219](https://openalex.org/S82228219) | 3 |
| Micromachines | 2072-666X | [S96702057](https://openalex.org/S96702057) | 3 |
| Mini-Reviews in Organic Chemistry | 1570-193X | [S67666162](https://openalex.org/S67666162) | 3 |
| Molecular Neurobiology | 0893-7648 | [S194681035](https://openalex.org/S194681035) | 3 |
| MRS Communications | 2159-6859 | [S2486144580](https://openalex.org/S2486144580) | 3 |
| Nano Research | 1998-0000 | [S173461644](https://openalex.org/S173461644) | 3 |
| Nanomedicine Nanotechnology Biology and Medicine | 1549-9634 | [S80729884](https://openalex.org/S80729884) | 3 |
| New Phytologist | 0028-646X | [S58631098](https://openalex.org/S58631098) | 3 |
| Next Energy | 2949-821X | [S4387287365](https://openalex.org/S4387287365) | 3 |
| Optics & Laser Technology | 0030-3992 | [S112574528](https://openalex.org/S112574528) | 3 |
| Oxford Open Materials Science | 2633-6979 | [S4210237507](https://openalex.org/S4210237507) | 3 |
| Pathogens | 2076-0817 | [S4210239906](https://openalex.org/S4210239906) | 3 |
| Petroleum Chemistry | 0028-2421 | [S181504447](https://openalex.org/S181504447) | 3 |
| Pharmaceuticals | 1424-8247 | [S16322639](https://openalex.org/S16322639) | 3 |
| Physical Review Letters | 0031-9007 | [S24807848](https://openalex.org/S24807848) | 3 |
| Physical review. E | 2470-0045 | [S4210235286](https://openalex.org/S4210235286) | 3 |
| Phytochemistry Reviews | 1568-7767 | [S125094086](https://openalex.org/S125094086) | 3 |
| Plant Biotechnology Journal | 1467-7644 | [S36510773](https://openalex.org/S36510773) | 3 |
| Plant Science | 0168-9452 | [S167743172](https://openalex.org/S167743172) | 3 |
| PLoS Biology | 1544-9173 | [S154343897](https://openalex.org/S154343897) | 3 |
| PLoS neglected tropical diseases | 1935-2727 | [S46544255](https://openalex.org/S46544255) | 3 |
| Powder Technology | 0032-5910 | [S122730748](https://openalex.org/S122730748) | 3 |
| Proceedings of the Indian National Science Academy | 2454-9983 | [S4210183255](https://openalex.org/S4210183255) | 3 |
| Progress in Additive Manufacturing | 2363-9512 | [S4210206835](https://openalex.org/S4210206835) | 3 |
| RASAYAN Journal of Chemistry | 0974-1496 | [S4210208286](https://openalex.org/S4210208286) | 3 |
| Recent Patents on Biotechnology | 1872-2083 | [S165193634](https://openalex.org/S165193634) | 3 |
| Regulatory Toxicology and Pharmacology | 0273-2300 | [S87719511](https://openalex.org/S87719511) | 3 |
| RSC Applied Polymers | 2755-371X | [S4387288668](https://openalex.org/S4387288668) | 3 |
| Saudi Journal of Biological Sciences | 1319-562X | [S32679471](https://openalex.org/S32679471) | 3 |
| Sensors | 1424-8220 | [S101949793](https://openalex.org/S101949793) | 3 |
| Sensors & Diagnostics | 2635-0998 | [S4210227332](https://openalex.org/S4210227332) | 3 |
| Superlattices and Microstructures | 0749-6036 | [S107898947](https://openalex.org/S107898947) | 3 |
| Sustainable Energy Technologies and Assessments | 2213-1388 | [S2764877105](https://openalex.org/S2764877105) | 3 |
| Systematic and Applied Microbiology | 0723-2020 | [S111458355](https://openalex.org/S111458355) | 3 |
| Tetrahedron Chem | 2666-951X | [S4210215647](https://openalex.org/S4210215647) | 3 |
| Tetrahedron Green Chem | 2773-2231 | [S4387285664](https://openalex.org/S4387285664) | 3 |
| The Journal of Chemical Thermodynamics | 0021-9614 | [S173979593](https://openalex.org/S173979593) | 3 |
| The Journal of Nutritional Biochemistry | 0955-2863 | [S548917](https://openalex.org/S548917) | 3 |
| Theoretical Chemistry Accounts | 1432-2234 | [S81945236](https://openalex.org/S81945236) | 3 |
| TrAC Trends in Analytical Chemistry | 0165-9936 | [S64920681](https://openalex.org/S64920681) | 3 |
| Transactions of the IMF | 0020-2967 | [S56956632](https://openalex.org/S56956632) | 3 |
| Vaccines | 2076-393X | [S4210226234](https://openalex.org/S4210226234) | 3 |
| ACS Agricultural Science & Technology | 2692-1952 | [S4210201395](https://openalex.org/S4210201395) | 2 |
| ACS Central Science | 2374-7943 | [S2765035057](https://openalex.org/S2765035057) | 2 |
| ACS Chemical Biology | 1554-8929 | [S118914585](https://openalex.org/S118914585) | 2 |
| ACS Engineering Au | 2694-2488 | [S4210186819](https://openalex.org/S4210186819) | 2 |
| ACS Infectious Diseases | 2373-8227 | [S2764646616](https://openalex.org/S2764646616) | 2 |
| ACS Polymers Au | 2694-2453 | [S4210227641](https://openalex.org/S4210227641) | 2 |
| Acta Scientiarum Biological Sciences | 1679-9283 | [S29120868](https://openalex.org/S29120868) | 2 |
| Acta Tropica | 0001-706X | [S190456265](https://openalex.org/S190456265) | 2 |
| Advanced Device Materials | 2055-0308 | [S4210180513](https://openalex.org/S4210180513) | 2 |
| Advanced Engineering Materials | 1438-1656 | [S156255550](https://openalex.org/S156255550) | 2 |
| Advanced Science Letters | 1936-6612 | [S73201230](https://openalex.org/S73201230) | 2 |
| Advances in Materials and Processing Technologies | 2374-068X | [S2764787537](https://openalex.org/S2764787537) | 2 |
| Advances in Materials Science and Engineering | 1687-8434 | [S155241436](https://openalex.org/S155241436) | 2 |
| Advances in Natural Sciences Nanoscience and Nanotechnology | 2043-6254 | [S29959626](https://openalex.org/S29959626) | 2 |
| African Journal of Biomedical Research | 1119-5096 | [S33826441](https://openalex.org/S33826441) | 2 |
| Analytical Letters | 0003-2719 | [S152476886](https://openalex.org/S152476886) | 2 |
| Analytical Science Advances | 2628-5452 | [S4210193490](https://openalex.org/S4210193490) | 2 |
| Analytical Sciences | 0910-6340 | [S91156679](https://openalex.org/S91156679) | 2 |
| Annals of Indian Academy of Neurology | 0972-2327 | [S8818485](https://openalex.org/S8818485) | 2 |
| Applied Water Science | 2190-5487 | [S2764931087](https://openalex.org/S2764931087) | 2 |
| Archives of Insect Biochemistry and Physiology | 0739-4462 | [S14369749](https://openalex.org/S14369749) | 2 |
| Artificial Cells Nanomedicine and Biotechnology | 2169-1401 | [S2489428960](https://openalex.org/S2489428960) | 2 |
| Asian Journal of Civil Engineering | 1563-0854 | [S4210200020](https://openalex.org/S4210200020) | 2 |
| Asian Journal of Organic & Medicinal Chemistry | 2456-8937 | [S4210232305](https://openalex.org/S4210232305) | 2 |
| Asian Journal of Pharmaceutical and Clinical Research | 0974-2441 | [S2764968390](https://openalex.org/S2764968390) | 2 |
| Autoimmunity Reviews | 1568-9972 | [S12874817](https://openalex.org/S12874817) | 2 |
| Beni-Suef University Journal of Basic and Applied Sciences | 2314-8535 | [S2764610058](https://openalex.org/S2764610058) | 2 |
| Bioactive Carbohydrates and Dietary Fibre | 2212-6198 | [S2764675440](https://openalex.org/S2764675440) | 2 |
| BioEnergy Research | 1939-1234 | [S53942123](https://openalex.org/S53942123) | 2 |
| Bioinformatics | 1367-4803 | [S52395412](https://openalex.org/S52395412) | 2 |
| Bioinspired Biomimetic and Nanobiomaterials | 2045-9858 | [S2764799808](https://openalex.org/S2764799808) | 2 |
| Biointerphases | 1559-4106 | [S68168660](https://openalex.org/S68168660) | 2 |
| Biologia | 0006-3088 | [S4210191406](https://openalex.org/S4210191406) | 2 |
| Biomedicines | 2227-9059 | [S2737005842](https://openalex.org/S2737005842) | 2 |
| Biotechnology Advances | 0734-9750 | [S160877137](https://openalex.org/S160877137) | 2 |
| Biotechnology and Bioprocess Engineering | 1226-8372 | [S72791832](https://openalex.org/S72791832) | 2 |
| Biotechnology Journal | 1860-6768 | [S31411064](https://openalex.org/S31411064) | 2 |
| BMC Cancer | 1471-2407 | [S192926780](https://openalex.org/S192926780) | 2 |
| BMC Research Notes | 1756-0500 | [S100014455](https://openalex.org/S100014455) | 2 |
| Brazilian Journal of Microbiology | 1517-8382 | [S70014682](https://openalex.org/S70014682) | 2 |
| Bulletin of the Chemical Society of Japan | 0009-2673 | [S95305481](https://openalex.org/S95305481) | 2 |
| Canadian Journal of Physiology and Pharmacology | 0008-4212 | [S82722058](https://openalex.org/S82722058) | 2 |
| Carbon letters | 1976-4251 | [S2765060811](https://openalex.org/S2765060811) | 2 |
| Carbon Resources Conversion | 2588-9133 | [S2898119963](https://openalex.org/S2898119963) | 2 |
| Carbon Trends | 2667-0569 | [S4210240045](https://openalex.org/S4210240045) | 2 |
| Cell & Bioscience | 2045-3701 | [S14303005](https://openalex.org/S14303005) | 2 |
| Cell Biochemistry and Function | 0263-6484 | [S960618578](https://openalex.org/S960618578) | 2 |
| Cell Reports Physical Science | 2666-3864 | [S4210216867](https://openalex.org/S4210216867) | 2 |
| Cellular and Molecular Life Sciences | 1420-682X | [S60362788](https://openalex.org/S60362788) | 2 |
| Cellular Physiology and Biochemistry | 1015-8987 | [S161399637](https://openalex.org/S161399637) | 2 |
| Cement and Concrete Composites | 0958-9465 | [S123887920](https://openalex.org/S123887920) | 2 |
| ChemBioEng Reviews | 2196-9744 | [S4210181929](https://openalex.org/S4210181929) | 2 |
| Chemical Engineering Journal Advances | 2666-8211 | [S4210233595](https://openalex.org/S4210233595) | 2 |
| Chemical Society Reviews | 0306-0012 | [S316438](https://openalex.org/S316438) | 2 |
| Chemistry & Chemical Technology | 1996-4196 | [S2764418452](https://openalex.org/S2764418452) | 2 |
| Chemistry of Natural Compounds | 0009-3130 | [S55509983](https://openalex.org/S55509983) | 2 |
| CHINESE JOURNAL OF CATALYSIS (CHINESE VERSION) | 0253-9837 | [S165997068](https://openalex.org/S165997068) | 2 |
| Coatings | 2079-6412 | [S4210205742](https://openalex.org/S4210205742) | 2 |
| Composites Science and Technology | 0266-3538 | [S52442148](https://openalex.org/S52442148) | 2 |
| Critical Reviews in Biotechnology | 0738-8551 | [S28635856](https://openalex.org/S28635856) | 2 |
| Crystal Research and Technology | 0232-1300 | [S85849776](https://openalex.org/S85849776) | 2 |
| Crystals | 2073-4352 | [S4210196485](https://openalex.org/S4210196485) | 2 |
| Current Biotechnology | 2211-5501 | [S2765022663](https://openalex.org/S2765022663) | 2 |
| Current Computer - Aided Drug Design | 1573-4099 | [S130157898](https://openalex.org/S130157898) | 2 |
| Current Indian Science | 2210-299X | [S4387279252](https://openalex.org/S4387279252) | 2 |
| Current Medicinal Chemistry | 0929-8673 | [S33159018](https://openalex.org/S33159018) | 2 |
| Current Microwave Chemistry | 2213-3356 | [S4210186394](https://openalex.org/S4210186394) | 2 |
| Current Nanomaterials | 2405-4615 | [S4210188953](https://openalex.org/S4210188953) | 2 |
| Current Nanoscience | 1573-4137 | [S199030710](https://openalex.org/S199030710) | 2 |
| Current Neuropharmacology | 1570-159X | [S85221069](https://openalex.org/S85221069) | 2 |
| Current Research in Translational Medicine | 2452-3186 | [S2898475623](https://openalex.org/S2898475623) | 2 |
| Current Trends in Biotechnology and Pharmacy | 0973-8916 | [S35776942](https://openalex.org/S35776942) | 2 |
| Cytoskeleton | 1949-3584 | [S4210203183](https://openalex.org/S4210203183) | 2 |
| Cytotechnology | 0920-9069 | [S78433294](https://openalex.org/S78433294) | 2 |
| Drug and Chemical Toxicology | 0148-0545 | [S17820993](https://openalex.org/S17820993) | 2 |
| Drug Delivery and Translational Research | 2190-393X | [S2764352022](https://openalex.org/S2764352022) | 2 |
| EES Catalysis | 2753-801X | [S4387281025](https://openalex.org/S4387281025) | 2 |
| Electrochemical Science Advances | 2698-5977 | [S4210224418](https://openalex.org/S4210224418) | 2 |
| Electrochemistry Communications | 1388-2481 | [S1342386](https://openalex.org/S1342386) | 2 |
| Energy Conversion and Management | 0196-8904 | [S105637730](https://openalex.org/S105637730) | 2 |
| Energy storage materials | 2405-8289 | [S2764728150](https://openalex.org/S2764728150) | 2 |
| Engineered Science | 2576-988X | [S4210220775](https://openalex.org/S4210220775) | 2 |
| Engineering in Life Sciences | 1618-0240 | [S39716790](https://openalex.org/S39716790) | 2 |
| Environmental Engineering and Management Journal | 1582-9596 | [S169219760](https://openalex.org/S169219760) | 2 |
| Environmental Monitoring and Assessment | 0167-6369 | [S11732831](https://openalex.org/S11732831) | 2 |
| Environmental Science Nano | 2051-8153 | [S2764968653](https://openalex.org/S2764968653) | 2 |
| Enzyme and Microbial Technology | 0141-0229 | [S4210230422](https://openalex.org/S4210230422) | 2 |
| Epidemiology and Infection | 0950-2688 | [S61175029](https://openalex.org/S61175029) | 2 |
| European Journal of Cell Biology | 0171-9335 | [S170067410](https://openalex.org/S170067410) | 2 |
| European Journal of Pharmaceutics and Biopharmaceutics | 0939-6411 | [S122302516](https://openalex.org/S122302516) | 2 |
| Expert Opinion on Therapeutic Patents | 1354-3776 | [S3784663](https://openalex.org/S3784663) | 2 |
| Exploration of Digital Health Technologies | 2996-9409 | [S5407042611](https://openalex.org/S5407042611) | 2 |
| FEBS Letters | 0014-5793 | [S104830714](https://openalex.org/S104830714) | 2 |
| FEMS Microbiology Letters | 0378-1097 | [S34954451](https://openalex.org/S34954451) | 2 |
| FEMS Yeast Research | 1567-1356 | [S58380981](https://openalex.org/S58380981) | 2 |
| Figshare |  | [S4377196282](https://openalex.org/S4377196282) | 2 |
| Food and Bioprocess Technology | 1935-5130 | [S181365921](https://openalex.org/S181365921) | 2 |
| Food and Bioproducts Processing | 0960-3085 | [S115749436](https://openalex.org/S115749436) | 2 |
| Food and Chemical Toxicology | 0278-6915 | [S84231135](https://openalex.org/S84231135) | 2 |
| Food Chemistry Advances | 2772-753X | [S4210225726](https://openalex.org/S4210225726) | 2 |
| Frontiers in Behavioral Neuroscience | 1662-5153 | [S76576941](https://openalex.org/S76576941) | 2 |
| Frontiers in Cellular and Infection Microbiology | 2235-2988 | [S2506667490](https://openalex.org/S2506667490) | 2 |
| Frontiers in Energy Research | 2296-598X | [S2595193159](https://openalex.org/S2595193159) | 2 |
| Frontiers in Genetics | 1664-8021 | [S2597340651](https://openalex.org/S2597340651) | 2 |
| Frontiers in Molecular Biosciences | 2296-889X | [S2595797843](https://openalex.org/S2595797843) | 2 |
| Frontiers in Molecular Neuroscience | 1662-5099 | [S39538987](https://openalex.org/S39538987) | 2 |
| Frontiers in Plant Science | 1664-462X | [S2493613807](https://openalex.org/S2493613807) | 2 |
| Functional & Integrative Genomics | 1438-793X | [S205083708](https://openalex.org/S205083708) | 2 |
| Functional Materials Letters | 1793-6047 | [S67457907](https://openalex.org/S67457907) | 2 |
| Future Science OA | 2056-5623 | [S2739054207](https://openalex.org/S2739054207) | 2 |
| Future Virology | 1746-0794 | [S204562989](https://openalex.org/S204562989) | 2 |
| Genome Announcements | 2169-8287 | [S2756006110](https://openalex.org/S2756006110) | 2 |
| Genome Research | 1088-9051 | [S43092948](https://openalex.org/S43092948) | 2 |
| Genomics | 0888-7543 | [S146035217](https://openalex.org/S146035217) | 2 |
| Genomics Data | 2213-5960 | [S2764425287](https://openalex.org/S2764425287) | 2 |
| Geological Journal | 0072-1050 | [S128421901](https://openalex.org/S128421901) | 2 |
| Geoscience Frontiers | 1674-9871 | [S2764860519](https://openalex.org/S2764860519) | 2 |
| Glycobiology | 0959-6658 | [S188363740](https://openalex.org/S188363740) | 2 |
| HAL (Le Centre pour la Communication Scientifique Directe) |  | [S4306402512](https://openalex.org/S4306402512) | 2 |
| Handbook of CH‐Functionalization |  | [S4363605295](https://openalex.org/S4363605295) | 2 |
| HEXAPODA | 0973-8592 | [S5406942292](https://openalex.org/S5406942292) | 2 |
| High Temperature Materials and Processes | 0334-6455 | [S12653085](https://openalex.org/S12653085) | 2 |
| Hydrometallurgy | 0304-386X | [S143946080](https://openalex.org/S143946080) | 2 |
| IEEE Access | 2169-3536 | [S2485537415](https://openalex.org/S2485537415) | 2 |
| IEEE Magnetics Letters | 1949-307X | [S115902931](https://openalex.org/S115902931) | 2 |
| IETE Journal of Research | 0377-2063 | [S158263287](https://openalex.org/S158263287) | 2 |
| In Silico Pharmacology | 2193-9616 | [S4210215659](https://openalex.org/S4210215659) | 2 |
| Indian Journal of Pharmaceutical Education and Research | 0019-5464 | [S30130650](https://openalex.org/S30130650) | 2 |
| Indian Phytopathology | 0367-973X | [S2764768694](https://openalex.org/S2764768694) | 2 |
| Informatics in Medicine Unlocked | 2352-9148 | [S2898224164](https://openalex.org/S2898224164) | 2 |
| Innovative Infrastructure Solutions | 2364-4176 | [S2764568522](https://openalex.org/S2764568522) | 2 |
| Inorganic and Nano-Metal Chemistry | 2470-1556 | [S2764517779](https://openalex.org/S2764517779) | 2 |
| Inorganics | 2304-6740 | [S2737417813](https://openalex.org/S2737417813) | 2 |
| Intermetallics | 0966-9795 | [S38855548](https://openalex.org/S38855548) | 2 |
| International Journal of Applied Ceramic Technology | 1546-542X | [S75568645](https://openalex.org/S75568645) | 2 |
| International Journal of Big Data and Analytics in Healthcare | 2379-7371 | [S4210234792](https://openalex.org/S4210234792) | 2 |
| International Journal of Chemical Engineering | 1687-806X | [S100353606](https://openalex.org/S100353606) | 2 |
| International Journal of Current Research and Review | 0975-5241 | [S2765045337](https://openalex.org/S2765045337) | 2 |
| International Journal of Environmental & Analytical Chemistry | 0306-7319 | [S203371744](https://openalex.org/S203371744) | 2 |
| International Journal of Food Microbiology | 0168-1605 | [S132626406](https://openalex.org/S132626406) | 2 |
| International Journal of Mass Spectrometry | 1387-3806 | [S108264783](https://openalex.org/S108264783) | 2 |
| International Journal of Nanoscience | 0219-581X | [S204978898](https://openalex.org/S204978898) | 2 |
| International Journal of Peptide Research and Therapeutics | 1573-3149 | [S197593595](https://openalex.org/S197593595) | 2 |
| International Journal of Pharmaceutical Investigation | 2230-9713 | [S2764462242](https://openalex.org/S2764462242) | 2 |
| International Journal of Pharmacy and Pharmaceutical Sciences | 0975-1491 | [S2764469077](https://openalex.org/S2764469077) | 2 |
| International Journal of Plastics Technology | 0972-656X | [S204261765](https://openalex.org/S204261765) | 2 |
| International Journal of Polymer Analysis and Characterization | 1023-666X | [S145318752](https://openalex.org/S145318752) | 2 |
| INTERNATIONAL JOURNAL OF RESEARCH AND ANALYTICAL REVIEWS | 2348-1269 | [S4210170903](https://openalex.org/S4210170903) | 2 |
| International Journal of Structural Integrity | 1757-9864 | [S189853587](https://openalex.org/S189853587) | 2 |
| International Journal of Surgery | 1743-9159 | [S67965910](https://openalex.org/S67965910) | 2 |
| Journal of Alzheimer s Disease Reports | 2542-4823 | [S4210202104](https://openalex.org/S4210202104) | 2 |
| Journal of Analytical Chemistry | 0021-8766 | [S3394804](https://openalex.org/S3394804) | 2 |
| Journal of Applied Pharmaceutical Science | 2231-3354 | [S2764844132](https://openalex.org/S2764844132) | 2 |
| Journal of Ayurveda and Holistic Medicine | 2321-1563 | [S4404662803](https://openalex.org/S4404662803) | 2 |
| Journal of Bacteriology & Mycology Open Access | 2469-2786 | [S2764655194](https://openalex.org/S2764655194) | 2 |
| Journal of Basic Microbiology | 0233-111X | [S169733112](https://openalex.org/S169733112) | 2 |
| Journal of Biomaterials Applications | 0885-3282 | [S89326922](https://openalex.org/S89326922) | 2 |
| Journal of Biomedical Materials Research Part B Applied Biomaterials | 1552-4973 | [S198061209](https://openalex.org/S198061209) | 2 |
| Journal of Bionic Engineering | 1672-6529 | [S33108253](https://openalex.org/S33108253) | 2 |
| Journal of Catalyst & Catalysis | 2349-4344 | [S4210231494](https://openalex.org/S4210231494) | 2 |
| Journal of Cell Communication and Signaling | 1873-9601 | [S40198776](https://openalex.org/S40198776) | 2 |
| Journal of Chemical Information and Modeling | 1549-9596 | [S167262187](https://openalex.org/S167262187) | 2 |
| Journal of Chemical Theory and Computation | 1549-9618 | [S189701308](https://openalex.org/S189701308) | 2 |
| Journal of Clinical Oncology | 0732-183X | [S15137598](https://openalex.org/S15137598) | 2 |
| Journal of Commercial Biotechnology | 1462-8732 | [S20248291](https://openalex.org/S20248291) | 2 |
| Journal of Composites Science | 2504-477X | [S4210181540](https://openalex.org/S4210181540) | 2 |
| Journal of Crystal Growth | 0022-0248 | [S10719676](https://openalex.org/S10719676) | 2 |
| Journal of Drug Research in Ayurvedic Sciences | 2279-0357 | [S4210215219](https://openalex.org/S4210215219) | 2 |
| Journal of drug targeting | 1026-7158 | [S100629371](https://openalex.org/S100629371) | 2 |
| Journal of Entomology and Zoology Studies | 2320-7078 | [S2764557943](https://openalex.org/S2764557943) | 2 |
| Journal of Experimental Nanoscience | 1745-8080 | [S94307637](https://openalex.org/S94307637) | 2 |
| Journal of Fluorine Chemistry | 0022-1139 | [S81947917](https://openalex.org/S81947917) | 2 |
| Journal of Food Biochemistry | 0145-8884 | [S53703007](https://openalex.org/S53703007) | 2 |
| Journal of Food Science | 0022-1147 | [S23579880](https://openalex.org/S23579880) | 2 |
| Journal of Green Chemistry and Chemical Engineering | 2831-4158 | [S4387280964](https://openalex.org/S4387280964) | 2 |
| Journal of Hazardous Toxic and Radioactive Waste | 2153-5493 | [S2765043744](https://openalex.org/S2765043744) | 2 |
| Journal of Infection and Public Health | 1876-0341 | [S53706017](https://openalex.org/S53706017) | 2 |
| Journal of Insect Behavior | 0892-7553 | [S142362986](https://openalex.org/S142362986) | 2 |
| Journal of Luminescence | 0022-2313 | [S188673600](https://openalex.org/S188673600) | 2 |
| Journal of Magnetic Resonance Open | 2666-4410 | [S4210238029](https://openalex.org/S4210238029) | 2 |
| Journal of Materials Science Materials in Medicine | 0957-4530 | [S166781098](https://openalex.org/S166781098) | 2 |
| Journal of Microbiological Methods | 0167-7012 | [S24124513](https://openalex.org/S24124513) | 2 |
| Journal of Mining and Metallurgy Section B Metallurgy | 1450-5339 | [S19980739](https://openalex.org/S19980739) | 2 |
| Journal of Molecular Evolution | 0022-2844 | [S144184862](https://openalex.org/S144184862) | 2 |
| Journal of Molecular Histology | 1567-2379 | [S172113453](https://openalex.org/S172113453) | 2 |
| Journal of Molecular Medicine | 0946-2716 | [S114689480](https://openalex.org/S114689480) | 2 |
| Journal of Molecular Neuroscience | 0895-8696 | [S133939727](https://openalex.org/S133939727) | 2 |
| Journal of Nanoscience and Technology | 2455-0191 | [S4210187103](https://openalex.org/S4210187103) | 2 |
| Journal of nanostructure in chemistry | 2008-9244 | [S2764590048](https://openalex.org/S2764590048) | 2 |
| Journal of Natural Products and Natural Products Synthesis | 2770-8284 | [S4387280962](https://openalex.org/S4387280962) | 2 |
| Journal of Oilseeds Research | 0970-2776 | [S2764605448](https://openalex.org/S2764605448) | 2 |
| Journal of Oleo Science | 1341-8327 | [S48379306](https://openalex.org/S48379306) | 2 |
| Journal of Parasitic Diseases | 0971-7196 | [S63436312](https://openalex.org/S63436312) | 2 |
| Journal of Pest Science | 0003-6307 | [S34015784](https://openalex.org/S34015784) | 2 |
| Journal of Pharmaceutical Analysis | 2095-1779 | [S2765050281](https://openalex.org/S2765050281) | 2 |
| Journal of Pharmaceutical Sciences | 0022-3549 | [S130661733](https://openalex.org/S130661733) | 2 |
| Journal of Physics Energy | 2515-7655 | [S4210231992](https://openalex.org/S4210231992) | 2 |
| Journal of Planar Chromatography – Modern TLC | 0933-4173 | [S4210230864](https://openalex.org/S4210230864) | 2 |
| Journal of Plant Diseases and Protection | 1861-3829 | [S158730009](https://openalex.org/S158730009) | 2 |
| Journal of Polymer Science | 2642-4150 | [S4210188590](https://openalex.org/S4210188590) | 2 |
| Journal of Pure and Applied Microbiology | 0973-7510 | [S2476582842](https://openalex.org/S2476582842) | 2 |
| Journal of Raman Spectroscopy | 0377-0486 | [S4206644](https://openalex.org/S4206644) | 2 |
| Journal of Rare Earths | 1002-0721 | [S139187495](https://openalex.org/S139187495) | 2 |
| Journal of Rheology | 0097-0360 | [S32106766](https://openalex.org/S32106766) | 2 |
| Journal of Statistical Mechanics Theory and Experiment | 1742-5468 | [S167943036](https://openalex.org/S167943036) | 2 |
| Journal of Sulfur Chemistry | 1741-5993 | [S99315931](https://openalex.org/S99315931) | 2 |
| Journal of Synchrotron Radiation | 0909-0495 | [S114484406](https://openalex.org/S114484406) | 2 |
| Journal of Taibah University for Science | 1658-3655 | [S2764979341](https://openalex.org/S2764979341) | 2 |
| Journal of the American Ceramic Society | 0002-7820 | [S53162366](https://openalex.org/S53162366) | 2 |
| Journal of the Chinese Chemical Society | 0009-4536 | [S5649782](https://openalex.org/S5649782) | 2 |
| Journal of the Energy Institute | 0144-2600 | [S178232084](https://openalex.org/S178232084) | 2 |
| Journal of the Indian Institute of Science | 0019-4964 | [S2765044025](https://openalex.org/S2765044025) | 2 |
| Journal of The Institution of Engineers (India) Series A | 2250-2149 | [S4210201576](https://openalex.org/S4210201576) | 2 |
| Journal of the Science of Food and Agriculture | 0022-5142 | [S206298197](https://openalex.org/S206298197) | 2 |
| Journal of Trace Elements and Minerals | 2773-0506 | [S4220651556](https://openalex.org/S4220651556) | 2 |
| Journal of Vacuum Science & Technology B Nanotechnology and Microelectronics Materials Processing Measurement and Phenomena | 2166-2746 | [S4210235835](https://openalex.org/S4210235835) | 2 |
| Kinetics and Catalysis | 0023-1584 | [S205357056](https://openalex.org/S205357056) | 2 |
| Korean Journal of Chemical Engineering | 0256-1115 | [S197055754](https://openalex.org/S197055754) | 2 |
| Life Sciences in Space Research | 2214-5524 | [S2764866528](https://openalex.org/S2764866528) | 2 |
| Liver International | 0106-9543 | [S206392846](https://openalex.org/S206392846) | 2 |
| Macromolecular Research | 1225-5947 | [S194131194](https://openalex.org/S194131194) | 2 |
| Macromolecular Symposia | 1022-1360 | [S7773033](https://openalex.org/S7773033) | 2 |
| Macromolecular Theory and Simulations | 1022-1344 | [S118639958](https://openalex.org/S118639958) | 2 |
| Marine Pollution Bulletin | 0025-326X | [S101229256](https://openalex.org/S101229256) | 2 |
| Material Science Research India | 0973-3469 | [S4210192902](https://openalex.org/S4210192902) | 2 |
| Materials & Design | 0264-1275 | [S8792693](https://openalex.org/S8792693) | 2 |
| Materials for Renewable and Sustainable Energy | 2194-1459 | [S4210198319](https://openalex.org/S4210198319) | 2 |
| Materials Research | 1516-1439 | [S204369084](https://openalex.org/S204369084) | 2 |
| Materials Science and Engineering A | 0921-5093 | [S154732359](https://openalex.org/S154732359) | 2 |
| Materials Science-Poland | 0137-1339 | [S4210195564](https://openalex.org/S4210195564) | 2 |
| Materials Technology | 1066-7857 | [S198128313](https://openalex.org/S198128313) | 2 |
| Matter | 2590-2385 | [S4210178557](https://openalex.org/S4210178557) | 2 |
| Medical Hypotheses | 0306-9877 | [S27514295](https://openalex.org/S27514295) | 2 |
| Medicinal Research Reviews | 0198-6325 | [S22382660](https://openalex.org/S22382660) | 2 |
| Membranes | 2077-0375 | [S4210225467](https://openalex.org/S4210225467) | 2 |
| Metabolic Engineering | 1096-7176 | [S173328182](https://openalex.org/S173328182) | 2 |
| MethodsX | 2215-0161 | [S2898269294](https://openalex.org/S2898269294) | 2 |
| Microorganisms | 2076-2607 | [S4210222090](https://openalex.org/S4210222090) | 2 |
| Mitochondrion | 1567-7249 | [S140584875](https://openalex.org/S140584875) | 2 |
| Modern Concepts in Material Science | 2692-5397 | [S4210216783](https://openalex.org/S4210216783) | 2 |
| Molecular & Cellular Proteomics | 1535-9476 | [S104550190](https://openalex.org/S104550190) | 2 |
| Molecular Biomedicine | 2662-8651 | [S4210227457](https://openalex.org/S4210227457) | 2 |
| Molecular Biotechnology | 1073-6085 | [S31191957](https://openalex.org/S31191957) | 2 |
| Molecular Genetics and Genomics | 1617-4615 | [S129324922](https://openalex.org/S129324922) | 2 |
| Molecular Informatics | 1868-1743 | [S150938958](https://openalex.org/S150938958) | 2 |
| Molecular Omics | 2515-4184 | [S4210236495](https://openalex.org/S4210236495) | 2 |
| Molecular Systems Design & Engineering | 2058-9689 | [S4210223080](https://openalex.org/S4210223080) | 2 |
| mSphere | 2379-5042 | [S4210207018](https://openalex.org/S4210207018) | 2 |
| Mutagenesis | 0267-8357 | [S101337917](https://openalex.org/S101337917) | 2 |
| Mutation Research/Genetic Toxicology and Environmental Mutagenesis | 1383-5718 | [S29775604](https://openalex.org/S29775604) | 2 |
| Nano Letters | 1530-6984 | [S143846845](https://openalex.org/S143846845) | 2 |
| Nanoscale Horizons | 2055-6756 | [S4210181981](https://openalex.org/S4210181981) | 2 |
| Nanotechnology Reviews | 2191-9089 | [S4210182563](https://openalex.org/S4210182563) | 2 |
| Nanotoxicology | 1743-5390 | [S193535841](https://openalex.org/S193535841) | 2 |
| National Academy Science Letters | 0250-541X | [S1017267059](https://openalex.org/S1017267059) | 2 |
| Nature Plants | 2055-026X | [S2764671299](https://openalex.org/S2764671299) | 2 |
| Neural Regeneration Research | 1673-5374 | [S80372421](https://openalex.org/S80372421) | 2 |
| Neurochemical Research | 0364-3190 | [S174790897](https://openalex.org/S174790897) | 2 |
| Neuropsychiatry | 1758-2008 | [S4210211137](https://openalex.org/S4210211137) | 2 |
| Neuropsychopharmacology | 0893-133X | [S175030738](https://openalex.org/S175030738) | 2 |
| npj Clean Water | 2059-7037 | [S4210171286](https://openalex.org/S4210171286) | 2 |
| npj Emerging Contaminants | 3059-3719 | [S5407047685](https://openalex.org/S5407047685) | 2 |
| Oncogene | 0950-9232 | [S128439998](https://openalex.org/S128439998) | 2 |
| Oncotarget | 1949-2553 | [S126644158](https://openalex.org/S126644158) | 2 |
| Open Journal of Biological Sciences | 2640-7795 | [S4210176647](https://openalex.org/S4210176647) | 2 |
| Organic Preparations and Procedures International | 0030-4948 | [S4210169069](https://openalex.org/S4210169069) | 2 |
| Oriental Journal Of Chemistry | 0970-020X | [S2764376875](https://openalex.org/S2764376875) | 2 |
| Particuology | 1674-2001 | [S62602987](https://openalex.org/S62602987) | 2 |
| PeerJ | 2167-8359 | [S1983995261](https://openalex.org/S1983995261) | 2 |
| Pest Management Science | 1526-498X | [S31777576](https://openalex.org/S31777576) | 2 |
| Pesticide Biochemistry and Physiology | 0048-3575 | [S9324707](https://openalex.org/S9324707) | 2 |
| Pharmaceutical Patent Analyst | 2046-8954 | [S2764428516](https://openalex.org/S2764428516) | 2 |
| Phosphorus, sulfur, and silicon and the related elements | 1026-7719 | [S70121411](https://openalex.org/S70121411) | 2 |
| Physica Scripta | 0031-8949 | [S59012888](https://openalex.org/S59012888) | 2 |
| Physical Biology | 1478-3967 | [S728652](https://openalex.org/S728652) | 2 |
| Physical Review Materials | 2475-9953 | [S2786256796](https://openalex.org/S2786256796) | 2 |
| Physics and Chemistry of Liquids | 0031-9104 | [S47516686](https://openalex.org/S47516686) | 2 |
| Physiological and Molecular Plant Pathology | 0885-5765 | [S54634327](https://openalex.org/S54634327) | 2 |
| Physiology & Behavior | 0031-9384 | [S167407068](https://openalex.org/S167407068) | 2 |
| Plant Cell Reports | 0721-7714 | [S196783408](https://openalex.org/S196783408) | 2 |
| Plant Cell Tissue and Organ Culture (PCTOC) | 0167-6857 | [S32261165](https://openalex.org/S32261165) | 2 |
| Plant Molecular Biology | 0167-4412 | [S189846775](https://openalex.org/S189846775) | 2 |
| Planta Medica International Open | 2509-6656 | [S4210179725](https://openalex.org/S4210179725) | 2 |
| PLoS Computational Biology | 1553-734X | [S86033158](https://openalex.org/S86033158) | 2 |
| Polymer Composites | 0272-8397 | [S156806727](https://openalex.org/S156806727) | 2 |
| Polymer Degradation and Stability | 0141-3910 | [S10124807](https://openalex.org/S10124807) | 2 |
| Polymer Science Series A | 0965-545X | [S2764435883](https://openalex.org/S2764435883) | 2 |
| Postharvest Biology and Technology | 0925-5214 | [S70397842](https://openalex.org/S70397842) | 2 |
| Preparative Biochemistry & Biotechnology | 1082-6068 | [S113958752](https://openalex.org/S113958752) | 2 |
| Proceedings of the Institution of Mechanical Engineers Part E Journal of Process Mechanical Engineering | 0954-4089 | [S4210186341](https://openalex.org/S4210186341) | 2 |
| Proceedings of the National Academy of Sciences India Section B Biological Sciences | 0369-8211 | [S4210190533](https://openalex.org/S4210190533) | 2 |
| Process Safety Progress | 1066-8527 | [S139295051](https://openalex.org/S139295051) | 2 |
| Processes | 2227-9717 | [S4210201879](https://openalex.org/S4210201879) | 2 |
| Progress in Polymer Science | 0079-6700 | [S119685760](https://openalex.org/S119685760) | 2 |
| Progress in Solid State Chemistry | 0079-6786 | [S185988428](https://openalex.org/S185988428) | 2 |
| Protein and Peptide Letters | 0929-8665 | [S3577691](https://openalex.org/S3577691) | 2 |
| Protein Expression and Purification | 1046-5928 | [S9184782](https://openalex.org/S9184782) | 2 |
| PROTEOMICS | 1615-9853 | [S182655450](https://openalex.org/S182655450) | 2 |
| PROTOPLASMA | 0033-183X | [S201230245](https://openalex.org/S201230245) | 2 |
| Reaction Kinetics Mechanisms and Catalysis | 1878-5190 | [S167175129](https://openalex.org/S167175129) | 2 |
| Reactions | 2624-781X | [S4210207985](https://openalex.org/S4210207985) | 2 |
| Research Journal of Life Sciences Bioinformatics Pharmaceutical and Chemical Sciences | 2454-6348 | [S4210222942](https://openalex.org/S4210222942) | 2 |
| Results in Surfaces and Interfaces | 2666-8459 | [S4210207554](https://openalex.org/S4210207554) | 2 |
| Rheologica Acta | 0035-4511 | [S24603639](https://openalex.org/S24603639) | 2 |
| RSC Mechanochemistry | 2976-8683 | [S4387292599](https://openalex.org/S4387292599) | 2 |
| RSC Pharmaceutics | 2976-8713 | [S4387292600](https://openalex.org/S4387292600) | 2 |
| Russian Chemical Bulletin | 1063-5211 | [S114185612](https://openalex.org/S114185612) | 2 |
| Science Diplomacy | 2456-5318 | [S7407089474](https://openalex.org/S7407089474) | 2 |
| Scientia Pharmaceutica | 0036-8709 | [S70157725](https://openalex.org/S70157725) | 2 |
| Silicon | 1876-990X | [S52783196](https://openalex.org/S52783196) | 2 |
| Small GTPases | 2154-1248 | [S34533772](https://openalex.org/S34533772) | 2 |
| Small Science | 2688-4046 | [S4210233464](https://openalex.org/S4210233464) | 2 |
| Solid State Communications | 0038-1098 | [S82088436](https://openalex.org/S82088436) | 2 |
| Spectroscopy Letters | 0038-7010 | [S37186612](https://openalex.org/S37186612) | 2 |
| Supramolecular chemistry | 1026-7816 | [S87016647](https://openalex.org/S87016647) | 2 |
| Sustainable Food Technology | 2753-8095 | [S4387281084](https://openalex.org/S4387281084) | 2 |
| Systems Microbiology and Biomanufacturing | 2662-7655 | [S4210175094](https://openalex.org/S4210175094) | 2 |
| The FASEB Journal | 0892-6638 | [S25293849](https://openalex.org/S25293849) | 2 |
| The Journal of Antibiotics | 0021-8820 | [S154771817](https://openalex.org/S154771817) | 2 |
| The Journal of Infectious Diseases | 0022-1899 | [S54542293](https://openalex.org/S54542293) | 2 |
| The Lancet Regional Health - Southeast Asia | 2772-3682 | [S4393919553](https://openalex.org/S4393919553) | 2 |
| The Nucleus | 0029-568X | [S4210187714](https://openalex.org/S4210187714) | 2 |
| The Physics of Metals and Metallography | 0031-918X | [S178376305](https://openalex.org/S178376305) | 2 |
| The Plant Journal | 0960-7412 | [S67862205](https://openalex.org/S67862205) | 2 |
| The Prostate | 0270-4137 | [S197000376](https://openalex.org/S197000376) | 2 |
| Toxicology Reports | 2214-7500 | [S2764757124](https://openalex.org/S2764757124) | 2 |
| Transactions of Nonferrous Metals Society of China | 1003-6326 | [S4210194876](https://openalex.org/S4210194876) | 2 |
| Trends in Parasitology | 1471-4922 | [S182404557](https://openalex.org/S182404557) | 2 |
| Tribology in Industry | 0354-8996 | [S4210209753](https://openalex.org/S4210209753) | 2 |
| Tumor Biology | 1010-4283 | [S12644804](https://openalex.org/S12644804) | 2 |
| UTTAR PRADESH JOURNAL OF ZOOLOGY | 0256-971X | [S2764565682](https://openalex.org/S2764565682) | 2 |
| Water Practice & Technology | 1751-231X | [S137656717](https://openalex.org/S137656717) | 2 |
| Water Research | 0043-1354 | [S52566953](https://openalex.org/S52566953) | 2 |
| Water Science & Technology | 0273-1223 | [S53450646](https://openalex.org/S53450646) | 2 |
| Wiley Interdisciplinary Reviews Energy and Environment | 2041-8396 | [S2764570418](https://openalex.org/S2764570418) | 2 |
| World Patent Information | 0172-2190 | [S84022812](https://openalex.org/S84022812) | 2 |
| Access Microbiology | 2516-8290 | [S4210207429](https://openalex.org/S4210207429) | 1 |
| ACS Food Science & Technology | 2692-1944 | [S4210220491](https://openalex.org/S4210220491) | 1 |
| ACS Physical Chemistry Au | 2694-2445 | [S4210221318](https://openalex.org/S4210221318) | 1 |
| ACS Synthetic Biology | 2161-5063 | [S54167817](https://openalex.org/S54167817) | 1 |
| Acta chimica slovenica | 1318-0207 | [S93081443](https://openalex.org/S93081443) | 1 |
| Acta Parasitologica | 1230-2821 | [S120551135](https://openalex.org/S120551135) | 1 |
| Acta Scientific Agriculture | 2581-365X | [S4210183895](https://openalex.org/S4210183895) | 1 |
| Advanced Biology | 2701-0198 | [S4210178898](https://openalex.org/S4210178898) | 1 |
| Advanced Biosystems | 2366-7478 | [S4210205839](https://openalex.org/S4210205839) | 1 |
| Advanced engineering forum | 2234-9898 | [S4210181239](https://openalex.org/S4210181239) | 1 |
| Advanced Fiber Materials | 2524-7921 | [S4210182575](https://openalex.org/S4210182575) | 1 |
| Advanced Industrial and Engineering Polymer Research | 2542-5048 | [S4210184591](https://openalex.org/S4210184591) | 1 |
| Advanced Materials Letters | 0976-3961 | [S2764820603](https://openalex.org/S2764820603) | 1 |
| Advanced Materials Proceedings | 2002-441X | [S4210171283](https://openalex.org/S4210171283) | 1 |
| Advanced NanoBiomed Research | 2699-9307 | [S4210232512](https://openalex.org/S4210232512) | 1 |
| Advanced Photonics Research | 2699-9293 | [S4210188503](https://openalex.org/S4210188503) | 1 |
| Advanced Physics Research | 2751-1200 | [S4387284235](https://openalex.org/S4387284235) | 1 |
| Advances in Applied Research | 0974-3839 | [S2765042416](https://openalex.org/S2765042416) | 1 |
| Advances in concrete construction | 2287-5301 | [S4306500781](https://openalex.org/S4306500781) | 1 |
| Advances in Nanoparticles | 2169-0510 | [S2765039529](https://openalex.org/S2765039529) | 1 |
| Advances in Pharmacological and Pharmaceutical Sciences | 2633-4690 | [S4210179656](https://openalex.org/S4210179656) | 1 |
| African Journal of Traditional Complementary and Alternative Medicines | 0189-6016 | [S23922572](https://openalex.org/S23922572) | 1 |
| Agri Gene | 2352-2151 | [S2898388394](https://openalex.org/S2898388394) | 1 |
| Agricultural Research Journal | 2395-1435 | [S2764983918](https://openalex.org/S2764983918) | 1 |
| Agricultural Science Digest - A Research Journal | 0253-150X | [S2764562560](https://openalex.org/S2764562560) | 1 |
| Agropedology | 0971-1570 | [S4210230082](https://openalex.org/S4210230082) | 1 |
| AIMS Microbiology | 2471-1888 | [S4210236775](https://openalex.org/S4210236775) | 1 |
| Alzheimer s Research & Therapy | 1758-9193 | [S140755874](https://openalex.org/S140755874) | 1 |
| American Journal of Analytical Chemistry | 2156-8251 | [S2764655704](https://openalex.org/S2764655704) | 1 |
| American Journal of Medicinal Chemistry | 2733-2519 | [S4210234696](https://openalex.org/S4210234696) | 1 |
| American Journal of Obstetrics & Gynecology MFM | 2589-9333 | [S4210238021](https://openalex.org/S4210238021) | 1 |
| American Journal of PharmTech Research | 2249-3387 | [S4210195008](https://openalex.org/S4210195008) | 1 |
| American Journal of Tropical Medicine and Hygiene | 0002-9637 | [S100045985](https://openalex.org/S100045985) | 1 |
| Analysis & Sensing | 2629-2742 | [S4210189799](https://openalex.org/S4210189799) | 1 |
| Ancient Science of Life | 0257-7941 | [S2736520405](https://openalex.org/S2736520405) | 1 |
| Angiogenesis | 0969-6970 | [S143701222](https://openalex.org/S143701222) | 1 |
| Animal nutrition | 2405-6383 | [S2764806997](https://openalex.org/S2764806997) | 1 |
| Annales de Toxicologie Analytique | 0768-598X | [S2898414893](https://openalex.org/S2898414893) | 1 |
| Annals of Agricultural Science Cairo | 0570-1783 | [S2764619822](https://openalex.org/S2764619822) | 1 |
| Annals of Medicine and Surgery | 2049-0801 | [S4210226177](https://openalex.org/S4210226177) | 1 |
| Annals of Neurosciences | 0972-7531 | [S22816821](https://openalex.org/S22816821) | 1 |
| Annals of the Entomological Society of America | 0013-8746 | [S79992667](https://openalex.org/S79992667) | 1 |
| Anti-Infective Agents | 1568-0126 | [S4210177725](https://openalex.org/S4210177725) | 1 |
| Antibiotics | 2079-6382 | [S2736332253](https://openalex.org/S2736332253) | 1 |
| Antimicrobial Agents and Chemotherapy | 0066-4804 | [S47215897](https://openalex.org/S47215897) | 1 |
| Antiviral Research | 0166-3542 | [S137372404](https://openalex.org/S137372404) | 1 |
| Antonie van Leeuwenhoek | 0003-6072 | [S192712274](https://openalex.org/S192712274) | 1 |
| ANVESHAK-International Journal of Management | 2278-8913 | [S4210176566](https://openalex.org/S4210176566) | 1 |
| Apmis | 0903-4641 | [S135377718](https://openalex.org/S135377718) | 1 |
| Applied Biological Chemistry | 0368-2897 | [S2764370109](https://openalex.org/S2764370109) | 1 |
| Applied Catalysis O Open | 2950-6484 | [S4394906757](https://openalex.org/S4394906757) | 1 |
| Applied Ecology and Environmental Research | 1589-1623 | [S87697115](https://openalex.org/S87697115) | 1 |
| Applied Food Research | 2772-5022 | [S4210228229](https://openalex.org/S4210228229) | 1 |
| Applied Mathematical Modelling | 0307-904X | [S153281200](https://openalex.org/S153281200) | 1 |
| Applied Radiation and Isotopes | 0969-8043 | [S185347286](https://openalex.org/S185347286) | 1 |
| Applied Thermal Engineering | 1359-4311 | [S129676613](https://openalex.org/S129676613) | 1 |
| AQUA - Water Infrastructure Ecosystems and Society | 0003-7214 | [S4210228842](https://openalex.org/S4210228842) | 1 |
| Aquatic Toxicology | 0166-445X | [S183233548](https://openalex.org/S183233548) | 1 |
| Archives of Metallurgy and Materials | 0860-7052 | [S20440071](https://openalex.org/S20440071) | 1 |
| Archives of Preventive Medicine | 2640-7868 | [S4210167765](https://openalex.org/S4210167765) | 1 |
| Archives of Virology | 0003-9012 | [S57491091](https://openalex.org/S57491091) | 1 |
| Arthropod-Plant Interactions | 1872-8847 | [S61151778](https://openalex.org/S61151778) | 1 |
| Asia-Pacific Journal of Molecular Biology and Biotechnology | 0128-7451 | [S176091581](https://openalex.org/S176091581) | 1 |
| Asian Food Science Journal | 2581-7752 | [S4210202726](https://openalex.org/S4210202726) | 1 |
| Asian Journal of Natural Product Biochemistry | 2775-4189 | [S4210195230](https://openalex.org/S4210195230) | 1 |
| Asian Journal of Pharmacy and Pharmacology | 2455-2674 | [S4210223218](https://openalex.org/S4210223218) | 1 |
| Asian Journal of Research in Chemistry | 0974-4150 | [S2765004438](https://openalex.org/S2765004438) | 1 |
| Asian Journal of Research in Social Sciences and Humanities | 2249-7315 | [S2764474527](https://openalex.org/S2764474527) | 1 |
| Asian Journal of Water Environment and Pollution | 0972-9860 | [S2764409165](https://openalex.org/S2764409165) | 1 |
| Asian Plant Research Journal | 2581-9992 | [S4210172451](https://openalex.org/S4210172451) | 1 |
| ASN NEURO | 1759-0914 | [S119308939](https://openalex.org/S119308939) | 1 |
| Atherosclerosis | 0021-9150 | [S206830620](https://openalex.org/S206830620) | 1 |
| Atmospheric Environment | 1352-2310 | [S4210198353](https://openalex.org/S4210198353) | 1 |
| Austin Journal of Analytical and Pharmaceutical Chemistry | 2381-8913 | [S4210190184](https://openalex.org/S4210190184) | 1 |
| Australian Journal of Chemistry | 0004-9425 | [S91238560](https://openalex.org/S91238560) | 1 |
| Autophagy Reports | 2769-4127 | [S4387278989](https://openalex.org/S4387278989) | 1 |
| Basic & Clinical Pharmacology & Toxicology | 1742-7835 | [S44074210](https://openalex.org/S44074210) | 1 |
| Batteries | 2313-0105 | [S2737090608](https://openalex.org/S2737090608) | 1 |
| Battery energy | 2768-1688 | [S4210239249](https://openalex.org/S4210239249) | 1 |
| Behavioural Brain Research | 0166-4328 | [S81474683](https://openalex.org/S81474683) | 1 |
| Berichte aus der medizinischen Informatik und Bioinformatik/Journal of integrative bioinformatics | 1432-4385 | [S4393917359](https://openalex.org/S4393917359) | 1 |
| Biochemical Genetics | 0006-2928 | [S8388595](https://openalex.org/S8388595) | 1 |
| Biochemical Journal | 0264-6021 | [S44425019](https://openalex.org/S44425019) | 1 |
| Biochemistry & Analytical Biochemistry | 2161-1009 | [S2764889690](https://openalex.org/S2764889690) | 1 |
| Biochimica et Biophysica Acta (BBA) - Bioenergetics | 0005-2728 | [S4210237460](https://openalex.org/S4210237460) | 1 |
| Biochimica et Biophysica Acta (BBA) - Gene Regulatory Mechanisms | 1874-9399 | [S4210203689](https://openalex.org/S4210203689) | 1 |
| Biochimica et Biophysica Acta (BBA) - Molecular and Cell Biology of Lipids | 1388-1981 | [S4210172276](https://openalex.org/S4210172276) | 1 |
| Biochimie | 0037-9042 | [S75247133](https://openalex.org/S75247133) | 1 |
| Bioengineering | 2306-5354 | [S4210179121](https://openalex.org/S4210179121) | 1 |
| Bioengineering & Translational Medicine | 2380-6761 | [S4210212656](https://openalex.org/S4210212656) | 1 |
| Biofouling | 0892-7014 | [S56828788](https://openalex.org/S56828788) | 1 |
| Biofuel Research Journal | 2292-8782 | [S4210226539](https://openalex.org/S4210226539) | 1 |
| Biofuels | 1759-7269 | [S4210186136](https://openalex.org/S4210186136) | 1 |
| Biogerontology | 1389-5729 | [S85312528](https://openalex.org/S85312528) | 1 |
| Bioinformation | 0973-2063 | [S2755911950](https://openalex.org/S2755911950) | 1 |
| Bioinorganic Chemistry and Applications | 1565-3633 | [S113299162](https://openalex.org/S113299162) | 1 |
| Biological Trace Element Research | 0163-4984 | [S45954700](https://openalex.org/S45954700) | 1 |
| Biology | 2079-7737 | [S153489431](https://openalex.org/S153489431) | 1 |
| Biology Methods and Protocols | 2396-8923 | [S2735234984](https://openalex.org/S2735234984) | 1 |
| Biology of the Cell | 0248-4900 | [S91329243](https://openalex.org/S91329243) | 1 |
| Biomedical and Therapeutics Letters | 2394-2274 | [S5406996696](https://openalex.org/S5406996696) | 1 |
| Biomedical Optics Express | 2156-7085 | [S104118869](https://openalex.org/S104118869) | 1 |
| Biomedical Research - India | 0970-938X | [S4210176780](https://openalex.org/S4210176780) | 1 |
| Biomedical Signal Processing and Control | 1746-8094 | [S8427965](https://openalex.org/S8427965) | 1 |
| BioMetals | 0966-0844 | [S64351449](https://openalex.org/S64351449) | 1 |
| Biomicrofluidics | 1932-1058 | [S173107507](https://openalex.org/S173107507) | 1 |
| Biomolecular NMR Assignments | 1874-270X | [S8355228](https://openalex.org/S8355228) | 1 |
| Biomolecules | 2218-273X | [S4210236520](https://openalex.org/S4210236520) | 1 |
| Bioresources and Bioprocessing | 2197-4365 | [S2736711265](https://openalex.org/S2736711265) | 1 |
| Biosystems | 0303-2647 | [S99347777](https://openalex.org/S99347777) | 1 |
| BioTechniques | 0736-6205 | [S79990748](https://openalex.org/S79990748) | 1 |
| Biotechnology and Applied Biochemistry | 0885-4513 | [S34872747](https://openalex.org/S34872747) | 1 |
| Biotechnology for Biofuels | 1754-6834 | [S137860580](https://openalex.org/S137860580) | 1 |
| BMC Biology | 1741-7007 | [S25903957](https://openalex.org/S25903957) | 1 |
| BMC Chemistry | 2661-801X | [S4210224244](https://openalex.org/S4210224244) | 1 |
| BMC Complementary Medicine and Therapies | 2662-7671 | [S4210199159](https://openalex.org/S4210199159) | 1 |
| BMC Systems Biology | 1752-0509 | [S92363890](https://openalex.org/S92363890) | 1 |
| BMJ Innovations | 2055-642X | [S4210179384](https://openalex.org/S4210179384) | 1 |
| BMJ Open | 2044-6055 | [S79054089](https://openalex.org/S79054089) | 1 |
| BMJ Open Sport & Exercise Medicine | 2055-7647 | [S2764939095](https://openalex.org/S2764939095) | 1 |
| Brain Network Disorders | 3050-6239 | [S5407047429](https://openalex.org/S5407047429) | 1 |
| Brain Research | 0006-8993 | [S96638545](https://openalex.org/S96638545) | 1 |
| Brain Research Bulletin | 0361-9230 | [S8119441](https://openalex.org/S8119441) | 1 |
| Brain Sciences | 2076-3425 | [S122317144](https://openalex.org/S122317144) | 1 |
| Brazilian Journal of Pharmaceutical Sciences | 1984-8250 | [S120884445](https://openalex.org/S120884445) | 1 |
| Bulletin of Atmospheric Science and Technology | 2662-1495 | [S4210201357](https://openalex.org/S4210201357) | 1 |
| BULLETIN OF CHEMICAL REACTION ENGINEERING AND CATALYSIS | 1978-2993 | [S2738450280](https://openalex.org/S2738450280) | 1 |
| C – Journal of Carbon Research | 2311-5629 | [S4210233808](https://openalex.org/S4210233808) | 1 |
| Calphad | 0364-5916 | [S179640588](https://openalex.org/S179640588) | 1 |
| Cancer Chemotherapy and Pharmacology | 0344-5704 | [S117498271](https://openalex.org/S117498271) | 1 |
| Cancer Letters | 0304-3835 | [S106234763](https://openalex.org/S106234763) | 1 |
| Cancer Nanotechnology | 1868-6958 | [S22207501](https://openalex.org/S22207501) | 1 |
| Cancer Reports | 2573-8348 | [S4210241191](https://openalex.org/S4210241191) | 1 |
| Cancers | 2072-6694 | [S168415115](https://openalex.org/S168415115) | 1 |
| Carcinogenesis | 0143-3334 | [S184620562](https://openalex.org/S184620562) | 1 |
| Cardiovascular Diabetology | 1475-2840 | [S12095120](https://openalex.org/S12095120) | 1 |
| Cardiovascular Toxicology | 1530-7905 | [S181810612](https://openalex.org/S181810612) | 1 |
| Case Studies in Chemical and Environmental Engineering | 2666-0164 | [S4210239778](https://openalex.org/S4210239778) | 1 |
| Catalysis for Sustainable Energy | 2084-6819 | [S2737188263](https://openalex.org/S2737188263) | 1 |
| Catalysis Structure & Reactivity | 2055-074X | [S4210175124](https://openalex.org/S4210175124) | 1 |
| Cell Adhesion & Migration | 1933-6918 | [S179222606](https://openalex.org/S179222606) | 1 |
| Cell Biology and Toxicology | 0742-2091 | [S31257671](https://openalex.org/S31257671) | 1 |
| Cell Biology International | 1065-6995 | [S7325069](https://openalex.org/S7325069) | 1 |
| Cell Biomaterials | 3050-5623 | [S5407047401](https://openalex.org/S5407047401) | 1 |
| Cell Death and Disease | 2041-4889 | [S185208586](https://openalex.org/S185208586) | 1 |
| Cell Proliferation | 0960-7722 | [S86484535](https://openalex.org/S86484535) | 1 |
| Cells | 2073-4409 | [S2736626452](https://openalex.org/S2736626452) | 1 |
| Cellular and Molecular Immunology | 1672-7681 | [S19143454](https://openalex.org/S19143454) | 1 |
| Cellular Polymers | 0262-4893 | [S163681099](https://openalex.org/S163681099) | 1 |
| Cereal Chemistry | 0009-0352 | [S4210216257](https://openalex.org/S4210216257) | 1 |
| Chemical and Biological Technologies in Agriculture | 2196-5641 | [S2737334311](https://openalex.org/S2737334311) | 1 |
| Chemical and Pharmaceutical Bulletin | 0009-2363 | [S3861430](https://openalex.org/S3861430) | 1 |
| Chemical and Process Engineering New Frontiers | 0208-6425 | [S951764588](https://openalex.org/S951764588) | 1 |
| Chemical Engineering Journal Green and Sustainable | 3051-0031 | [S5407053083](https://openalex.org/S5407053083) | 1 |
| Chemistry - Methods | 2628-9725 | [S4210208565](https://openalex.org/S4210208565) | 1 |
| Chemistry Africa | 2522-5758 | [S4210187402](https://openalex.org/S4210187402) | 1 |
| Chemistry Letters | 0366-7022 | [S90825563](https://openalex.org/S90825563) | 1 |
| Chemistry of Inorganic Materials | 2949-7469 | [S4387288100](https://openalex.org/S4387288100) | 1 |
| Chinese Chemical Letters | 1001-8417 | [S167919573](https://openalex.org/S167919573) | 1 |
| Chinese Journal of Chemical Engineering | 1004-9541 | [S78268018](https://openalex.org/S78268018) | 1 |
| Chinese Journal of Physics | 0577-9073 | [S169735585](https://openalex.org/S169735585) | 1 |
| Chronicle of Diabetes Research and Practice | 2773-1316 | [S4210186777](https://openalex.org/S4210186777) | 1 |
| Civil Engineering and Architecture | 2332-1091 | [S4210186571](https://openalex.org/S4210186571) | 1 |
| CLEAN - Soil Air Water | 1863-0650 | [S19224985](https://openalex.org/S19224985) | 1 |
| Cleaner Engineering and Technology | 2666-7908 | [S4210217486](https://openalex.org/S4210217486) | 1 |
| Clinical and Experimental Medicine | 1591-8890 | [S1255940](https://openalex.org/S1255940) | 1 |
| Clinical and Translational Gastroenterology | 2155-384X | [S2764670792](https://openalex.org/S2764670792) | 1 |
| Cogent Chemistry | 2331-2009 | [S2736746179](https://openalex.org/S2736746179) | 1 |
| Cogent Food & Agriculture | 2331-1932 | [S2764637833](https://openalex.org/S2764637833) | 1 |
| Combinatorial Chemistry & High Throughput Screening | 1386-2073 | [S50933791](https://openalex.org/S50933791) | 1 |
| Communications Biology | 2399-3642 | [S4210225776](https://openalex.org/S4210225776) | 1 |
| Communicative & Integrative Biology | 1942-0889 | [S197152527](https://openalex.org/S197152527) | 1 |
| Comparative Biochemistry and Physiology Part D Genomics and Proteomics | 1744-117X | [S2898390257](https://openalex.org/S2898390257) | 1 |
| Composites Part C Open Access | 2666-6820 | [S4210186814](https://openalex.org/S4210186814) | 1 |
| Computational and Structural Biotechnology Journal | 2001-0370 | [S2764539591](https://openalex.org/S2764539591) | 1 |
| Computational Materials Science | 0927-0256 | [S26018076](https://openalex.org/S26018076) | 1 |
| Computers & Fluids | 0045-7930 | [S195914795](https://openalex.org/S195914795) | 1 |
| Conservation Physiology | 2051-1434 | [S2734435911](https://openalex.org/S2734435911) | 1 |
| Corrosion and Materials Degradation | 2624-5558 | [S4210191110](https://openalex.org/S4210191110) | 1 |
| Corrosion Engineering Science and Technology The International Journal of Corrosion Processes and Corrosion Control | 1478-422X | [S38341973](https://openalex.org/S38341973) | 1 |
| CPT Pharmacometrics & Systems Pharmacology | 2163-8306 | [S4210231731](https://openalex.org/S4210231731) | 1 |
| Critical Reviews in Environmental Science and Technology | 1064-3389 | [S207935976](https://openalex.org/S207935976) | 1 |
| Croatica Chemica Acta | 0011-1643 | [S36275936](https://openalex.org/S36275936) | 1 |
| Current Analytical Chemistry | 1573-4110 | [S110262396](https://openalex.org/S110262396) | 1 |
| Current Biochemical Engineering | 2212-7119 | [S4210188378](https://openalex.org/S4210188378) | 1 |
| Current Drug Targets | 1389-4501 | [S140884253](https://openalex.org/S140884253) | 1 |
| Current Eye Research | 0271-3683 | [S74941265](https://openalex.org/S74941265) | 1 |
| Current Gene Therapy | 1566-5232 | [S31345238](https://openalex.org/S31345238) | 1 |
| Current Metabolomics | 2213-235X | [S4210176110](https://openalex.org/S4210176110) | 1 |
| Current Opinion in Biomedical Engineering | 2468-4511 | [S2898133657](https://openalex.org/S2898133657) | 1 |
| Current Opinion in Colloid & Interface Science | 1359-0294 | [S974056801](https://openalex.org/S974056801) | 1 |
| Current Opinion in Insect Science | 2214-5745 | [S2764908915](https://openalex.org/S2764908915) | 1 |
| Current Opinion in Structural Biology | 0959-440X | [S175155502](https://openalex.org/S175155502) | 1 |
| Current Protein and Peptide Science | 1389-2037 | [S67737920](https://openalex.org/S67737920) | 1 |
| Current Protocols | 2691-1299 | [S4210206398](https://openalex.org/S4210206398) | 1 |
| Current Psychiatry Research and Reviews | 2666-0822 | [S4210198242](https://openalex.org/S4210198242) | 1 |
| Current Smart Materials | 2405-4658 | [S4210192835](https://openalex.org/S4210192835) | 1 |
| Current Trends in Analytical and Bioanalytical Chemistry | 2642-4266 | [S4210200804](https://openalex.org/S4210200804) | 1 |
| Cytokine | 1043-4666 | [S70396342](https://openalex.org/S70396342) | 1 |
| Designed Monomers & Polymers | 1385-772X | [S20456899](https://openalex.org/S20456899) | 1 |
| Detritus | 2611-4127 | [S4210170762](https://openalex.org/S4210170762) | 1 |
| Diabetes | 0012-1797 | [S129060628](https://openalex.org/S129060628) | 1 |
| Diagnostic Pathology | 1746-1596 | [S124750060](https://openalex.org/S124750060) | 1 |
| Diagnostics | 2075-4418 | [S4210172076](https://openalex.org/S4210172076) | 1 |
| Digital twins and applications. | 2995-2182 | [S4404664149](https://openalex.org/S4404664149) | 1 |
| Discover Agriculture | 2731-9598 | [S4387290765](https://openalex.org/S4387290765) | 1 |
| Discover Applied Sciences | 3004-9261 | [S5407042868](https://openalex.org/S5407042868) | 1 |
| Discover Chemical Engineering | 2730-7700 | [S4210190490](https://openalex.org/S4210190490) | 1 |
| Discover Chemistry. | 3005-1193 | [S4404664029](https://openalex.org/S4404664029) | 1 |
| Discover Electrochemistry. | 3005-1215 | [S4404669874](https://openalex.org/S4404669874) | 1 |
| Discover Food | 2731-4286 | [S4210181059](https://openalex.org/S4210181059) | 1 |
| Discover Life | 2948-2976 | [S4394906702](https://openalex.org/S4394906702) | 1 |
| Discover Plants. | 3005-1207 | [S4404533546](https://openalex.org/S4404533546) | 1 |
| Discover Sustainability | 2662-9984 | [S4210179043](https://openalex.org/S4210179043) | 1 |
| Drug Delivery | 1071-7544 | [S70174254](https://openalex.org/S70174254) | 1 |
| Drug Design Development and Therapy | 1177-8881 | [S2496126384](https://openalex.org/S2496126384) | 1 |
| Drug Development and Therapeutics | 2394-2002 | [S4210223880](https://openalex.org/S4210223880) | 1 |
| Drug Research | 2194-9379 | [S4210226141](https://openalex.org/S4210226141) | 1 |
| Drug Testing and Analysis | 1942-7603 | [S36361591](https://openalex.org/S36361591) | 1 |
| Ecological Indicators | 1470-160X | [S194154261](https://openalex.org/S194154261) | 1 |
| Ecological Informatics | 1574-9541 | [S195809937](https://openalex.org/S195809937) | 1 |
| ECS Sensors Plus | 2754-2726 | [S4220651082](https://openalex.org/S4220651082) | 1 |
| EES batteries. | 3033-4071 | [S4404663996](https://openalex.org/S4404663996) | 1 |
| EES solar. | 3033-4063 | [S4404675514](https://openalex.org/S4404675514) | 1 |
| Egyptian Journal of Biological Pest Control | 1110-1768 | [S130435576](https://openalex.org/S130435576) | 1 |
| Egyptian Journal of Chemistry | 0449-2285 | [S4210174320](https://openalex.org/S4210174320) | 1 |
| Egyptian Journal of Petroleum | 1110-0621 | [S2764783832](https://openalex.org/S2764783832) | 1 |
| Electrochem | 2673-3293 | [S4210231854](https://openalex.org/S4210231854) | 1 |
| Electronic Materials Letters | 1738-8090 | [S177378842](https://openalex.org/S177378842) | 1 |
| Emerging Microbes & Infections | 2222-1751 | [S2764760790](https://openalex.org/S2764760790) | 1 |
| Energy & environment materials | 2575-0348 | [S4210219471](https://openalex.org/S4210219471) | 1 |
| Energy Conversion and Management X | 2590-1745 | [S4210191901](https://openalex.org/S4210191901) | 1 |
| Energy Harvesting and Systems | 2329-8766 | [S4210192938](https://openalex.org/S4210192938) | 1 |
| Energy Science & Engineering | 2050-0505 | [S2737327489](https://openalex.org/S2737327489) | 1 |
| Engineering Failure Analysis | 1350-6307 | [S152303250](https://openalex.org/S152303250) | 1 |
| Engineering Reports | 2577-8196 | [S4210199257](https://openalex.org/S4210199257) | 1 |
| Engineering Solid Mechanics | 2291-8744 | [S2764366466](https://openalex.org/S2764366466) | 1 |
| Entomologia Experimentalis et Applicata | 0013-8703 | [S26596028](https://openalex.org/S26596028) | 1 |
| Entomological Research | 1738-2297 | [S106623195](https://openalex.org/S106623195) | 1 |
| Environment & Health | 2833-8278 | [S4387289850](https://openalex.org/S4387289850) | 1 |
| Environment Development and Sustainability | 1387-585X | [S155209994](https://openalex.org/S155209994) | 1 |
| Environment International | 0160-4120 | [S143381477](https://openalex.org/S143381477) | 1 |
| Environmental chemistry and safety | 2097-5740 | [S5406978647](https://openalex.org/S5406978647) | 1 |
| Environmental Engineering Science | 1092-8758 | [S1905899](https://openalex.org/S1905899) | 1 |
| Environmental Nanotechnology Monitoring & Management | 2215-1532 | [S2764626169](https://openalex.org/S2764626169) | 1 |
| Environmental Processes | 2198-7491 | [S2764608354](https://openalex.org/S2764608354) | 1 |
| Environmental Quality Management | 1088-1913 | [S9831443](https://openalex.org/S9831443) | 1 |
| Environmental Science & Technology | 0013-936X | [S13479253](https://openalex.org/S13479253) | 1 |
| Environmental Toxicology | 1520-4081 | [S172436580](https://openalex.org/S172436580) | 1 |
| Environmental Toxicology and Pharmacology | 1382-6689 | [S108944336](https://openalex.org/S108944336) | 1 |
| ES chemistry and sustainability. | 3065-1689 | [S4404675369](https://openalex.org/S4404675369) | 1 |
| ES General | 2836-399X | [S4387288243](https://openalex.org/S4387288243) | 1 |
| European Food Research and Technology | 0373-0174 | [S169454776](https://openalex.org/S169454776) | 1 |
| European Journal of Chemistry | 2153-2249 | [S97250276](https://openalex.org/S97250276) | 1 |
| European Journal of Environmental and Civil engineering | 1964-8189 | [S105391359](https://openalex.org/S105391359) | 1 |
| European Journal of Medicinal Chemistry Reports | 2772-4174 | [S4210220500](https://openalex.org/S4210220500) | 1 |
| European Journal of Prosthodontics | 2347-4610 | [S4210169372](https://openalex.org/S4210169372) | 1 |
| European Journal of Sustainable Development Research | 2542-4742 | [S4210213041](https://openalex.org/S4210213041) | 1 |
| Everyman s Science | 0531-495X | [S5406936577](https://openalex.org/S5406936577) | 1 |
| Evidence-based Complementary and Alternative Medicine | 1741-427X | [S15444899](https://openalex.org/S15444899) | 1 |
| Evolutionary Bioinformatics | 1176-9343 | [S187114417](https://openalex.org/S187114417) | 1 |
| EXCLI journal | 1611-2156 | [S39273986](https://openalex.org/S39273986) | 1 |
| Experimental Heat Transfer | 0891-6152 | [S25352102](https://openalex.org/S25352102) | 1 |
| Experimental Parasitology | 0014-4894 | [S102868315](https://openalex.org/S102868315) | 1 |
| Expert Opinion on Drug Discovery | 1746-0441 | [S142541038](https://openalex.org/S142541038) | 1 |
| Expert Review of Proteomics | 1478-9450 | [S96346590](https://openalex.org/S96346590) | 1 |
| Exploration of Medicine | 2692-3106 | [S4210192963](https://openalex.org/S4210192963) | 1 |
| Exploration of Neuroprotective Therapy | 2769-6510 | [S4390573728](https://openalex.org/S4390573728) | 1 |
| Fibres and Textiles in Eastern Europe | 1230-3666 | [S5858206](https://openalex.org/S5858206) | 1 |
| Flavour and Fragrance Journal | 0882-5734 | [S83413509](https://openalex.org/S83413509) | 1 |
| Flow Measurement and Instrumentation | 0955-5986 | [S46058507](https://openalex.org/S46058507) | 1 |
| Fluid Dynamics Research | 0169-5983 | [S98158633](https://openalex.org/S98158633) | 1 |
| Fluid Phase Equilibria | 0378-3812 | [S34870678](https://openalex.org/S34870678) | 1 |
| Food Additives & Contaminants Part A | 1944-0049 | [S4210190642](https://openalex.org/S4210190642) | 1 |
| Food and Environmental Virology | 1867-0334 | [S13638121](https://openalex.org/S13638121) | 1 |
| Food biomacromolecules. | 2996-2757 | [S4404660971](https://openalex.org/S4404660971) | 1 |
| Food Control | 0956-7135 | [S119525064](https://openalex.org/S119525064) | 1 |
| Food Packaging and Shelf Life | 2214-2894 | [S2764480744](https://openalex.org/S2764480744) | 1 |
| Food Research | 2550-2166 | [S4210236404](https://openalex.org/S4210236404) | 1 |
| Food Science & Nutrition Technology | 2574-2701 | [S4210172627](https://openalex.org/S4210172627) | 1 |
| Food Science and Human Wellness | 2097-0765 | [S2764902628](https://openalex.org/S2764902628) | 1 |
| Forensic Toxicology | 1860-8965 | [S17753527](https://openalex.org/S17753527) | 1 |
| Franklin Open | 2773-1863 | [S4387281167](https://openalex.org/S4387281167) | 1 |
| Frontiers in Aging Neuroscience | 1663-4365 | [S118428158](https://openalex.org/S118428158) | 1 |
| Frontiers in Bioscience-Landmark | 2768-6698 | [S4210236708](https://openalex.org/S4210236708) | 1 |
| Frontiers in Cell and Developmental Biology | 2296-634X | [S2596924766](https://openalex.org/S2596924766) | 1 |
| Frontiers in Cellular Neuroscience | 1662-5102 | [S36653316](https://openalex.org/S36653316) | 1 |
| Frontiers in Environmental Science | 2296-665X | [S2596204836](https://openalex.org/S2596204836) | 1 |
| Frontiers in Insect Science | 2673-8600 | [S4210210584](https://openalex.org/S4210210584) | 1 |
| Frontiers in Nanotechnology | 2673-3013 | [S4210212819](https://openalex.org/S4210212819) | 1 |
| Frontiers in Neuroscience | 1662-453X | [S115201632](https://openalex.org/S115201632) | 1 |
| Frontiers in Systems Biology | 2674-0702 | [S4386621871](https://openalex.org/S4386621871) | 1 |
| Frontiers of Chemical Science and Engineering | 1673-7369 | [S4210176808](https://openalex.org/S4210176808) | 1 |
| Frontiers of Materials Science | 2095-025X | [S2764754586](https://openalex.org/S2764754586) | 1 |
| Fuel Processing Technology | 0378-3820 | [S112051168](https://openalex.org/S112051168) | 1 |
| Fundamental and Clinical Pharmacology | 0767-3981 | [S35226884](https://openalex.org/S35226884) | 1 |
| Future Microbiology | 1746-0913 | [S129524704](https://openalex.org/S129524704) | 1 |
| Future Postharvest and Food | 2837-6846 | [S4390648503](https://openalex.org/S4390648503) | 1 |
| G3 Genes Genomes Genetics | 2160-1836 | [S109822313](https://openalex.org/S109822313) | 1 |
| Gas Science and Engineering | 2949-9089 | [S4387285525](https://openalex.org/S4387285525) | 1 |
| Genes & Diseases | 2352-3042 | [S2764642421](https://openalex.org/S2764642421) | 1 |
| Genetics | 0016-6731 | [S65932378](https://openalex.org/S65932378) | 1 |
| Genetics and Molecular Biology | 1415-4757 | [S151355818](https://openalex.org/S151355818) | 1 |
| GeoJournal | 0343-2521 | [S123313652](https://openalex.org/S123313652) | 1 |
| Geomicrobiology Journal | 0149-0451 | [S65040752](https://openalex.org/S65040752) | 1 |
| GeroScience | 2152-4041 | [S4210237251](https://openalex.org/S4210237251) | 1 |
| Global Challenges | 2056-6646 | [S4210214099](https://openalex.org/S4210214099) | 1 |
| Green Energy & Environment | 2096-2797 | [S2898348030](https://openalex.org/S2898348030) | 1 |
| Green Technologies and Sustainability | 2949-7361 | [S4387284297](https://openalex.org/S4387284297) | 1 |
| Healthcare Technology Letters | 2053-3713 | [S2764707789](https://openalex.org/S2764707789) | 1 |
| Heat and Mass Transfer | 0947-7411 | [S29537273](https://openalex.org/S29537273) | 1 |
| Heat Transfer Research | 1064-2285 | [S4210198580](https://openalex.org/S4210198580) | 1 |
| Hematology/Oncology and Stem Cell Therapy | 1658-3876 | [S2898422462](https://openalex.org/S2898422462) | 1 |
| Heteroatom Chemistry | 1042-7163 | [S84090441](https://openalex.org/S84090441) | 1 |
| Histochemistry and Cell Biology | 0948-6143 | [S78725770](https://openalex.org/S78725770) | 1 |
| Homeopathy | 1475-4916 | [S4310451](https://openalex.org/S4310451) | 1 |
| Hybrid Advances | 2773-207X | [S4387284451](https://openalex.org/S4387284451) | 1 |
| Hydrology and earth system sciences | 1027-5606 | [S93121129](https://openalex.org/S93121129) | 1 |
| Hypertension | 0194-911X | [S67880631](https://openalex.org/S67880631) | 1 |
| Hypertension Research | 0916-9636 | [S67902008](https://openalex.org/S67902008) | 1 |
| IBRO Neuroscience Reports | 2667-2421 | [S4210237554](https://openalex.org/S4210237554) | 1 |
| IEEE Transactions on Computational Biology and Bioinformatics | 1545-5963 | [S36029991](https://openalex.org/S36029991) | 1 |
| IEEE Transactions on Electron Devices | 0018-9383 | [S162355128](https://openalex.org/S162355128) | 1 |
| IEEE Transactions on Industrial Electronics | 0278-0046 | [S58031724](https://openalex.org/S58031724) | 1 |
| IEEE Transactions on Magnetics | 0018-9464 | [S50523690](https://openalex.org/S50523690) | 1 |
| IEEE Transactions on Neural Networks and Learning Systems | 2162-237X | [S4210175523](https://openalex.org/S4210175523) | 1 |
| IET Systems Biology | 1751-8849 | [S30934864](https://openalex.org/S30934864) | 1 |
| In Silico Research in Biomedicine | 3050-7871 | [S5407047481](https://openalex.org/S5407047481) | 1 |
| Indian Forester | 0019-4816 | [S2764360124](https://openalex.org/S2764360124) | 1 |
| Indian Journal of Biochemistry and Biophysics | 0301-1208 | [S104480359](https://openalex.org/S104480359) | 1 |
| Indian Journal of Entomology | 0367-8288 | [S2764438082](https://openalex.org/S2764438082) | 1 |
| Indian Journal of Medical and Paediatric Oncology | 0971-5851 | [S112025928](https://openalex.org/S112025928) | 1 |
| Indian Journal of Medical Ethics | 0974-8466 | [S2754473584](https://openalex.org/S2754473584) | 1 |
| Indian Journal of Nephrology | 0971-4065 | [S65200941](https://openalex.org/S65200941) | 1 |
| Indian Journal of Pharmacology | 0253-7613 | [S112348374](https://openalex.org/S112348374) | 1 |
| Indian Welding Journal | 0046-9092 | [S4210197864](https://openalex.org/S4210197864) | 1 |
| Indonesian Journal of Chemistry | 1411-9420 | [S2764840418](https://openalex.org/S2764840418) | 1 |
| Industrial Biotechnology | 1550-9087 | [S93158239](https://openalex.org/S93158239) | 1 |
| Infectious Diseases Now | 2666-9919 | [S4210196242](https://openalex.org/S4210196242) | 1 |
| Infectious Medicine | 2097-0684 | [S4210185135](https://openalex.org/S4210185135) | 1 |
| InfoMat | 2567-3165 | [S4210212605](https://openalex.org/S4210212605) | 1 |
| Infoscience (Ecole Polytechnique Fédérale de Lausanne) |  | [S4306400487](https://openalex.org/S4306400487) | 1 |
| Innovative Food Science & Emerging Technologies | 1466-8564 | [S130676932](https://openalex.org/S130676932) | 1 |
| Inorganic Materials | 0020-1685 | [S70837955](https://openalex.org/S70837955) | 1 |
| Integrated ferroelectrics | 1026-7530 | [S194927175](https://openalex.org/S194927175) | 1 |
| Interdisciplinary Sciences Computational Life Sciences | 1867-1462 | [S188962457](https://openalex.org/S188962457) | 1 |
| International Biodeterioration & Biodegradation | 0964-8305 | [S138354367](https://openalex.org/S138354367) | 1 |
| International Dairy Journal | 0958-6946 | [S184773532](https://openalex.org/S184773532) | 1 |
| International Journal For Multidisciplinary Research | 2582-2160 | [S4210207214](https://openalex.org/S4210207214) | 1 |
| International Journal for Parasitology | 0020-7519 | [S163169856](https://openalex.org/S163169856) | 1 |
| International Journal for Research in Applied Science and Engineering Technology | 2321-9653 | [S2764566388](https://openalex.org/S2764566388) | 1 |
| International Journal of Advanced Research | 2320-5407 | [S4210206230](https://openalex.org/S4210206230) | 1 |
| International Journal of Agricultural Research | 1816-4897 | [S67388669](https://openalex.org/S67388669) | 1 |
| International Journal of Antimicrobial Agents | 0924-8579 | [S5248501](https://openalex.org/S5248501) | 1 |
| International Journal of Applied Chemistry | 2393-9133 | [S4210167694](https://openalex.org/S4210167694) | 1 |
| International Journal of Biochemistry Research & Review | 2231-086X | [S2764761641](https://openalex.org/S2764761641) | 1 |
| International Journal of Biometeorology | 0020-7128 | [S84867234](https://openalex.org/S84867234) | 1 |
| International Journal of Bioorganic and Medicinal Chemistry | 2769-3023 | [S4387280982](https://openalex.org/S4387280982) | 1 |
| International Journal of Cell Science & Molecular Biology | 2572-1100 | [S4210211251](https://openalex.org/S4210211251) | 1 |
| International Journal of Ceramic Engineering & Science | 2578-3270 | [S4210181343](https://openalex.org/S4210181343) | 1 |
| International Journal of Chemoinformatics and Chemical Engineering | 2155-4110 | [S4210200112](https://openalex.org/S4210200112) | 1 |
| International Journal of Coal Preparation and Utilization | 1939-2699 | [S100482762](https://openalex.org/S100482762) | 1 |
| International Journal of Coal Science & Technology | 2095-8293 | [S2738503445](https://openalex.org/S2738503445) | 1 |
| International Journal of Computer Applications | 0975-8887 | [S4210206007](https://openalex.org/S4210206007) | 1 |
| International Journal of Computers Communications & Control | 1841-9836 | [S147751515](https://openalex.org/S147751515) | 1 |
| International Journal of Concrete Structures and Materials | 1976-0485 | [S176808670](https://openalex.org/S176808670) | 1 |
| International Journal of Corrosion | 1687-9325 | [S165238713](https://openalex.org/S165238713) | 1 |
| International Journal of Current Research in Biosciences and Plant Biology | 2349-8072 | [S2764804930](https://openalex.org/S2764804930) | 1 |
| International Journal of Diabetes in Developing Countries | 0973-3930 | [S201635232](https://openalex.org/S201635232) | 1 |
| International Journal of Drug Design and Discovery | 0975-8275 | [S5406942616](https://openalex.org/S5406942616) | 1 |
| International Journal of Engineering | 1025-2495 | [S2764816760](https://openalex.org/S2764816760) | 1 |
| International Journal of Environmental Engineering | 1756-8463 | [S164050468](https://openalex.org/S164050468) | 1 |
| International Journal of Environmental Research | 1735-6865 | [S1040098286](https://openalex.org/S1040098286) | 1 |
| International Journal of Environmental Research and Public Health | 1660-4601 | [S15239247](https://openalex.org/S15239247) | 1 |
| International Journal of Environmental Science and Development | 2010-0264 | [S2764870503](https://openalex.org/S2764870503) | 1 |
| International Journal of Environmental Sciences | 2229-7359 | [S5406984696](https://openalex.org/S5406984696) | 1 |
| International Journal of Environmental Technology and Management | 1466-2132 | [S199851821](https://openalex.org/S199851821) | 1 |
| International Journal of Exergy | 1742-8297 | [S32302261](https://openalex.org/S32302261) | 1 |
| International Journal of Fatigue | 0142-1123 | [S71623918](https://openalex.org/S71623918) | 1 |
| International Journal of Green Energy | 1543-5075 | [S65809584](https://openalex.org/S65809584) | 1 |
| International Journal of Health Sciences | 2550-696X | [S4210179027](https://openalex.org/S4210179027) | 1 |
| International Journal of Health Technology and Innovation | 2583-8547 | [S4387291216](https://openalex.org/S4387291216) | 1 |
| International Journal of Heat and Fluid Flow | 0142-727X | [S40322869](https://openalex.org/S40322869) | 1 |
| International Journal of Heat and Mass Transfer | 0017-9310 | [S90999920](https://openalex.org/S90999920) | 1 |
| International Journal of Industrial Chemistry | 2228-5547 | [S2764852611](https://openalex.org/S2764852611) | 1 |
| International Journal of Infectious Diseases | 1201-9712 | [S35071406](https://openalex.org/S35071406) | 1 |
| International Journal of Innovative Science and Research Technology (IJISRT) | 2456-2165 | [S4210189963](https://openalex.org/S4210189963) | 1 |
| International Journal of Internet Marketing and Advertising | 1477-5212 | [S47640537](https://openalex.org/S47640537) | 1 |
| International Journal of Medical Microbiology | 1438-4221 | [S41453107](https://openalex.org/S41453107) | 1 |
| International Journal of Modern Physics B | 0217-9792 | [S130197424](https://openalex.org/S130197424) | 1 |
| International Journal of Organic Chemistry Synthesis | 2769-2086 | [S4210179467](https://openalex.org/S4210179467) | 1 |
| International Journal of Pavement Research and Technology | 1996-6814 | [S2764903752](https://openalex.org/S2764903752) | 1 |
| International Journal of Pharma and Bio Sciences | 0975-6299 | [S2764788474](https://openalex.org/S2764788474) | 1 |
| International Journal of Pharmaceutical Sciences and Drug Research | 0975-248X | [S2764983607](https://openalex.org/S2764983607) | 1 |
| International Journal of Pharmaceutics X | 2590-1567 | [S4210204060](https://openalex.org/S4210204060) | 1 |
| International Journal of Pharmacognosy and Phytochemical Research | 0975-4873 | [S4210188147](https://openalex.org/S4210188147) | 1 |
| International Journal of Phytomedicine | 0975-0185 | [S143008211](https://openalex.org/S143008211) | 1 |
| International Journal of Plant & Soil Science | 2320-7035 | [S2764346760](https://openalex.org/S2764346760) | 1 |
| International Journal of Rapid Manufacturing | 1757-8817 | [S4210173505](https://openalex.org/S4210173505) | 1 |
| International Journal of Science Strategic Management and Technology | 3108-1762 | [S7407053991](https://openalex.org/S7407053991) | 1 |
| INTERNATIONAL JOURNAL OF SCIENTIFIC RESEARCH |  | [S4363604216](https://openalex.org/S4363604216) | 1 |
| International Journal of Scientific Research in Science and Technology | 2395-6011 | [S2764908356](https://openalex.org/S2764908356) | 1 |
| International Journal of Sustainable Engineering | 1939-7038 | [S183821374](https://openalex.org/S183821374) | 1 |
| International Journal of Systems Assurance Engineering and Management | 0975-6809 | [S40280859](https://openalex.org/S40280859) | 1 |
| International Journal of the Society of Materials Engineering for Resources | 1347-9725 | [S2764576755](https://openalex.org/S2764576755) | 1 |
| International Journal of Traditional Medicine and Applications | 2689-1638 | [S4210193796](https://openalex.org/S4210193796) | 1 |
| International Journal of Yoga | 0973-6131 | [S98882656](https://openalex.org/S98882656) | 1 |
| International Journal on Advanced Computer Theory and Engineering | 2319-2526 | [S5407054254](https://openalex.org/S5407054254) | 1 |
| International Research Journal of Multidisciplinary Technovation | 2582-1040 | [S4210191970](https://openalex.org/S4210191970) | 1 |
| International Research Journal of Pharmacy | 2230-8407 | [S4210205243](https://openalex.org/S4210205243) | 1 |
| Investigational New Drugs | 0167-6997 | [S6037287](https://openalex.org/S6037287) | 1 |
| IOSR Journal of Applied Chemistry | 2278-5736 | [S4210188417](https://openalex.org/S4210188417) | 1 |
| Iranian Journal of Science and Technology Transactions of Civil Engineering | 2228-6160 | [S2479525500](https://openalex.org/S2479525500) | 1 |
| ISA Transactions | 0019-0578 | [S89543202](https://openalex.org/S89543202) | 1 |
| Israel Journal of Chemistry | 0021-2148 | [S195061198](https://openalex.org/S195061198) | 1 |
| IUCrData | 2414-3146 | [S2738518343](https://openalex.org/S2738518343) | 1 |
| JAMA Neurology | 2168-6149 | [S164389565](https://openalex.org/S164389565) | 1 |
| JAMA Psychiatry | 2168-622X | [S2495708506](https://openalex.org/S2495708506) | 1 |
| Japanese Journal of Applied Physics | 0021-4922 | [S143744711](https://openalex.org/S143744711) | 1 |
| JHEP Reports | 2589-5559 | [S4210202621](https://openalex.org/S4210202621) | 1 |
| JMIR Research Protocols | 1929-0748 | [S2739058702](https://openalex.org/S2739058702) | 1 |
| Joule | 2542-4351 | [S2898305631](https://openalex.org/S2898305631) | 1 |
| Journal of Adhesion Science and Technology | 0169-4243 | [S20355562](https://openalex.org/S20355562) | 1 |
| JOURNAL OF ADVANCED APPLIED SCIENTIFIC RESEARCH | 2454-3225 | [S4387281230](https://openalex.org/S4387281230) | 1 |
| Journal of Advanced Joining Processes | 2666-3309 | [S4210200780](https://openalex.org/S4210200780) | 1 |
| Journal of Advanced Scientific Research | 0976-9595 | [S4220651155](https://openalex.org/S4220651155) | 1 |
| Journal of Advanced Thermal Science Research | 2409-5826 | [S4210217660](https://openalex.org/S4210217660) | 1 |
| Journal of Advances in Biology & Biotechnology | 2394-1081 | [S2764613355](https://openalex.org/S2764613355) | 1 |
| Journal of Analysis and Testing | 2096-241X | [S4210168667](https://openalex.org/S4210168667) | 1 |
| Journal of Analytical and Applied Pyrolysis | 0165-2370 | [S58603569](https://openalex.org/S58603569) | 1 |
| Journal of Antimicrobial Chemotherapy | 0305-7453 | [S124275759](https://openalex.org/S124275759) | 1 |
| Journal of Applied Biomedicine | 1214-021X | [S49362916](https://openalex.org/S49362916) | 1 |
| Journal of Applied Research on Medicinal and Aromatic Plants | 2214-7861 | [S2764636153](https://openalex.org/S2764636153) | 1 |
| Journal of Applied Sciences | 1812-5654 | [S107214695](https://openalex.org/S107214695) | 1 |
| Journal of Applied Spectroscopy | 0021-9037 | [S131318974](https://openalex.org/S131318974) | 1 |
| Journal of Asian Ceramic Societies | 2187-0764 | [S2764532622](https://openalex.org/S2764532622) | 1 |
| Journal of Atmospheric and Solar-Terrestrial Physics | 1364-6826 | [S207559368](https://openalex.org/S207559368) | 1 |
| Journal of Biological Control | 0971-930X | [S2764416458](https://openalex.org/S2764416458) | 1 |
| Journal of Biomedical Informatics | 1532-0464 | [S11622463](https://openalex.org/S11622463) | 1 |
| Journal of Biomedical Materials Research Part A | 1549-3296 | [S184573928](https://openalex.org/S184573928) | 1 |
| Journal of Biomolecular NMR | 0925-2738 | [S181390377](https://openalex.org/S181390377) | 1 |
| Journal of Bioscience and Bioengineering | 1347-4421 | [S63783143](https://openalex.org/S63783143) | 1 |
| Journal of Building Engineering | 2352-7102 | [S2764478331](https://openalex.org/S2764478331) | 1 |
| Journal of Cardiovascular Translational Research | 1937-5387 | [S62013175](https://openalex.org/S62013175) | 1 |
| Journal of Central South University | 2095-2899 | [S4210239277](https://openalex.org/S4210239277) | 1 |
| Journal of Chemical Crystallography | 1074-1542 | [S21922812](https://openalex.org/S21922812) | 1 |
| Journal of Chemical Ecology | 0098-0331 | [S134698528](https://openalex.org/S134698528) | 1 |
| Journal of Chemical Engineering | 2221-7436 | [S2764647441](https://openalex.org/S2764647441) | 1 |
| Journal of Chemical Neuroanatomy | 0891-0618 | [S6010938](https://openalex.org/S6010938) | 1 |
| Journal of Chemical Research | 1747-5198 | [S4210180763](https://openalex.org/S4210180763) | 1 |
| Journal of Cheminformatics | 1758-2946 | [S180838163](https://openalex.org/S180838163) | 1 |
| Journal of Chromatographic Science | 0021-9665 | [S144192255](https://openalex.org/S144192255) | 1 |
| Journal of Chromatography Open | 2772-3917 | [S4210211886](https://openalex.org/S4210211886) | 1 |
| Journal of Coating Science and Technology | 2369-3355 | [S4210203995](https://openalex.org/S4210203995) | 1 |
| Journal of Computer-Aided Molecular Design | 0920-654X | [S64621741](https://openalex.org/S64621741) | 1 |
| Journal of Conservative Dentistry | 0972-0707 | [S71239593](https://openalex.org/S71239593) | 1 |
| Journal of Dermatology Research | 3050-8460 | [S5407055776](https://openalex.org/S5407055776) | 1 |
| Journal of Earth System Science | 0253-4126 | [S157804282](https://openalex.org/S157804282) | 1 |
| Journal of Electrochemical Energy Conversion and Storage | 1550-624X | [S126985745](https://openalex.org/S126985745) | 1 |
| Journal of Electrochemical Science and Engineering | 1847-9286 | [S2764557848](https://openalex.org/S2764557848) | 1 |
| Journal of Electrochemical Science and Technology | 2093-8551 | [S2764590354](https://openalex.org/S2764590354) | 1 |
| Journal of Energy Resources Technology | 0195-0738 | [S17843412](https://openalex.org/S17843412) | 1 |
| Journal of Environmental Biology | 0254-8704 | [S133027048](https://openalex.org/S133027048) | 1 |
| Journal of Environmental Chemistry and Ecotoxicology | 2141-226X | [S4210186312](https://openalex.org/S4210186312) | 1 |
| Journal of Environmental Engineering | 0733-9372 | [S156179317](https://openalex.org/S156179317) | 1 |
| Journal of Environmental Microbiology and Toxicology | 2289-5906 | [S4210170032](https://openalex.org/S4210170032) | 1 |
| Journal of Environmental Science and Health Part A | 1093-4529 | [S4393917029](https://openalex.org/S4393917029) | 1 |
| Journal of Environmental Sciences | 1001-0742 | [S35825460](https://openalex.org/S35825460) | 1 |
| Journal of Essential Oil and Plant Composition | 2958-9630 | [S4387288221](https://openalex.org/S4387288221) | 1 |
| Journal of Essential Oil Bearing Plants | 0972-060X | [S999813893](https://openalex.org/S999813893) | 1 |
| Journal of Evidence-Based Integrative Medicine | 2515-690X | [S4210203230](https://openalex.org/S4210203230) | 1 |
| Journal of Experimental & Theoretical Artificial Intelligence | 0952-813X | [S153467142](https://openalex.org/S153467142) | 1 |
| Journal of Experimental and Theoretical Physics | 0038-5646 | [S47388274](https://openalex.org/S47388274) | 1 |
| Journal of Failure Analysis and Prevention | 1547-7029 | [S66787172](https://openalex.org/S66787172) | 1 |
| Journal of Food Process Engineering | 0145-8876 | [S151747869](https://openalex.org/S151747869) | 1 |
| Journal of Food Processing and Preservation | 0145-8892 | [S188241495](https://openalex.org/S188241495) | 1 |
| Journal of Food Quality | 0146-9428 | [S70979639](https://openalex.org/S70979639) | 1 |
| Journal of Food Research | 1927-0887 | [S4210204040](https://openalex.org/S4210204040) | 1 |
| Journal of Forensic Sciences | 0022-1198 | [S62072220](https://openalex.org/S62072220) | 1 |
| Journal of Functional Foods | 1756-4646 | [S8548135](https://openalex.org/S8548135) | 1 |
| Journal of Genetic Engineering and Biotechnology | 1687-157X | [S2764867799](https://openalex.org/S2764867799) | 1 |
| Journal of Genomics | 1839-9940 | [S4210229175](https://openalex.org/S4210229175) | 1 |
| Journal of Hazardous Materials Advances | 2772-4166 | [S4210197718](https://openalex.org/S4210197718) | 1 |
| Journal of Herbal Medicine | 2210-8033 | [S184565882](https://openalex.org/S184565882) | 1 |
| Journal of Human Lactation | 0890-3344 | [S84590487](https://openalex.org/S84590487) | 1 |
| Journal of Immunotoxicology | 1547-6901 | [S82112532](https://openalex.org/S82112532) | 1 |
| Journal of Indian Society of Pedodontics and Preventive Dentistry | 0970-4388 | [S40951238](https://openalex.org/S40951238) | 1 |
| Journal of Information and Knowledge | 2583-9314 | [S4387997576](https://openalex.org/S4387997576) | 1 |
| Journal of Infrared Millimeter and Terahertz Waves | 1866-6892 | [S120213556](https://openalex.org/S120213556) | 1 |
| Journal of Investigative Dermatology | 0022-202X | [S28607811](https://openalex.org/S28607811) | 1 |
| Journal of King Saud University - Computer and Information Sciences | 1319-1578 | [S2764955546](https://openalex.org/S2764955546) | 1 |
| Journal of Magnetic Resonance | 1090-7807 | [S90573847](https://openalex.org/S90573847) | 1 |
| Journal of Manufacturing Processes | 1526-6125 | [S120037611](https://openalex.org/S120037611) | 1 |
| Journal of Manufacturing Science and Engineering | 1087-1357 | [S193263997](https://openalex.org/S193263997) | 1 |
| Journal of Material Cycles and Waste Management | 1438-4957 | [S111367495](https://openalex.org/S111367495) | 1 |
| Journal of Materiomics | 2352-8478 | [S2764607427](https://openalex.org/S2764607427) | 1 |
| Journal of Medical Biomedical And Applied Sciences | 2349-0748 | [S4306515866](https://openalex.org/S4306515866) | 1 |
| Journal of Medical Virology | 0146-6615 | [S49828768](https://openalex.org/S49828768) | 1 |
| Journal of Medicinal Food | 1096-620X | [S78718175](https://openalex.org/S78718175) | 1 |
| Journal of Mental Health Disorders | 2770-761X | [S4387997376](https://openalex.org/S4387997376) | 1 |
| Journal of Microbiology and Infectious Diseases | 2146-3158 | [S2764850316](https://openalex.org/S2764850316) | 1 |
| Journal of Microbiology Biotechnology and Food Sciences | 1338-5178 | [S2764909764](https://openalex.org/S2764909764) | 1 |
| Journal of Molecular Catalysis B Enzymatic | 1381-1177 | [S21009921](https://openalex.org/S21009921) | 1 |
| Journal of Molecular Chemistry. | 3048-6033 | [S4404670431](https://openalex.org/S4404670431) | 1 |
| Journal of Natural Fibers | 1544-046X | [S29409266](https://openalex.org/S29409266) | 1 |
| Journal of Natural Gas Science and Engineering | 1875-5100 | [S125705681](https://openalex.org/S125705681) | 1 |
| Journal of Natural Pesticide Research | 2773-0786 | [S4220651597](https://openalex.org/S4220651597) | 1 |
| Journal of Neurochemistry | 0022-3042 | [S135837084](https://openalex.org/S135837084) | 1 |
| Journal of Neuroscience Research | 0360-4012 | [S76417895](https://openalex.org/S76417895) | 1 |
| Journal of Nuclear Materials | 0022-3115 | [S149516416](https://openalex.org/S149516416) | 1 |
| Journal of Oil Palm Research | 1511-2780 | [S134592288](https://openalex.org/S134592288) | 1 |
| Journal of Peptide Science | 1075-2617 | [S184443419](https://openalex.org/S184443419) | 1 |
| Journal of Petroleum Geology | 0141-6421 | [S198628674](https://openalex.org/S198628674) | 1 |
| Journal of Pharmaceutical and Biomedical Analysis Letters | 2347-4742 | [S5406993220](https://openalex.org/S5406993220) | 1 |
| Journal of Pharmaceutical Negative Results | 0976-9234 | [S2764350261](https://openalex.org/S2764350261) | 1 |
| Journal of Pharmacology and Experimental Therapeutics | 0022-3565 | [S102125482](https://openalex.org/S102125482) | 1 |
| Journal of Pharmacy and Pharmacology | 0022-3573 | [S118304455](https://openalex.org/S118304455) | 1 |
| Journal of Photochemistry and Photobiology C Photochemistry Reviews | 1389-5567 | [S143106029](https://openalex.org/S143106029) | 1 |
| Journal of Physics B Atomic Molecular and Optical Physics | 0953-4075 | [S108417319](https://openalex.org/S108417319) | 1 |
| Journal of Physics Communications | 2399-6528 | [S4210180840](https://openalex.org/S4210180840) | 1 |
| Journal of Physics Condensed Matter | 0953-8984 | [S190924190](https://openalex.org/S190924190) | 1 |
| Journal of Physics Materials | 2515-7639 | [S4210204056](https://openalex.org/S4210204056) | 1 |
| Journal of Physiology and Biochemistry | 1138-7548 | [S68195922](https://openalex.org/S68195922) | 1 |
| Journal of Phytonanotechnology and Pharmaceutical Sciences | 2583-0376 | [S4220651516](https://openalex.org/S4220651516) | 1 |
| Journal of Phytopathology | 0931-1785 | [S14509825](https://openalex.org/S14509825) | 1 |
| Journal of Pipeline Science and Engineering | 2667-1433 | [S4210223785](https://openalex.org/S4210223785) | 1 |
| Journal of Plant Biochemistry and Biotechnology | 0971-7811 | [S70161554](https://openalex.org/S70161554) | 1 |
| Journal of Plant Physiology | 0176-1617 | [S148694123](https://openalex.org/S148694123) | 1 |
| Journal of Polymer Engineering | 0334-6447 | [S40213007](https://openalex.org/S40213007) | 1 |
| Journal of Population Therapeutics and Clinical Pharmacology | 1710-6222 | [S4210224141](https://openalex.org/S4210224141) | 1 |
| Journal of Psychiatric Research | 0022-3956 | [S160879026](https://openalex.org/S160879026) | 1 |
| Journal of Quality in Health Care & Economics | 2642-6250 | [S4210231514](https://openalex.org/S4210231514) | 1 |
| Journal of Receptors and Signal Transduction | 1079-9893 | [S116485566](https://openalex.org/S116485566) | 1 |
| JOURNAL OF RENEWABLE MATERIALS | 2164-6325 | [S2764967724](https://openalex.org/S2764967724) | 1 |
| Journal of Scientific & Industrial Research | 0022-4456 | [S20781845](https://openalex.org/S20781845) | 1 |
| Journal of Scientific Research | 2070-0237 | [S167873845](https://openalex.org/S167873845) | 1 |
| Journal of Sea Research | 1385-1101 | [S132103761](https://openalex.org/S132103761) | 1 |
| Journal of Siberian Federal University Chemistry | 1998-2836 | [S4210173335](https://openalex.org/S4210173335) | 1 |
| Journal of Structural Integrity and Maintenance | 2470-5314 | [S4210172103](https://openalex.org/S4210172103) | 1 |
| Journal of Sustainable Bioenergy Systems | 2165-400X | [S2764779874](https://openalex.org/S2764779874) | 1 |
| Journal of the American Society for Mass Spectrometry | 1044-0305 | [S60743949](https://openalex.org/S60743949) | 1 |
| Journal of the Brazilian Society of Mechanical Sciences and Engineering | 1678-5878 | [S76397174](https://openalex.org/S76397174) | 1 |
| Journal of the Chilean Chemical Society | 0717-9324 | [S114494114](https://openalex.org/S114494114) | 1 |
| Journal of the Geological Society of India | 0016-7622 | [S60020396](https://openalex.org/S60020396) | 1 |
| Journal of The Institution of Engineers (India) Series C | 2250-0545 | [S4210178808](https://openalex.org/S4210178808) | 1 |
| Journal of The Institution of Engineers (India) Series E | 2250-2483 | [S4210172530](https://openalex.org/S4210172530) | 1 |
| Journal of the Optical Society of America B | 0740-3224 | [S64486668](https://openalex.org/S64486668) | 1 |
| Journal of the Serbian Chemical Society | 0352-5139 | [S10052521](https://openalex.org/S10052521) | 1 |
| Journal of Theoretical Biology | 0022-5193 | [S109682412](https://openalex.org/S109682412) | 1 |
| Journal of Thermal Science and Engineering Applications | 1948-5085 | [S186254152](https://openalex.org/S186254152) | 1 |
| Journal of Thermoplastic Composite Materials | 0892-7057 | [S159246406](https://openalex.org/S159246406) | 1 |
| Journal of Threatened Taxa | 0974-7893 | [S2764419951](https://openalex.org/S2764419951) | 1 |
| Journal of Toxicology and Environmental Health | 0098-4108 | [S85071590](https://openalex.org/S85071590) | 1 |
| Journal of Trace Elements in Medicine and Biology | 0946-672X | [S165809374](https://openalex.org/S165809374) | 1 |
| Journal of Traditional Chinese Medical Sciences | 2095-7548 | [S2765057931](https://openalex.org/S2765057931) | 1 |
| Journal of Travel Medicine | 1195-1982 | [S31999364](https://openalex.org/S31999364) | 1 |
| Journal of Tribology | 0742-4787 | [S4210169712](https://openalex.org/S4210169712) | 1 |
| Journal of Vacuum Science & Technology A Vacuum Surfaces and Films | 0734-2101 | [S4210190837](https://openalex.org/S4210190837) | 1 |
| Journal of Vinyl and Additive Technology | 1083-5601 | [S162486132](https://openalex.org/S162486132) | 1 |
| Journal of Virology | 0022-538X | [S96615428](https://openalex.org/S96615428) | 1 |
| Journal of Water Reuse and Desalination | 2220-1319 | [S2487679084](https://openalex.org/S2487679084) | 1 |
| JSM clinical pharmaceutics. | 2379-9498 | [S4404664015](https://openalex.org/S4404664015) | 1 |
| Jurnal Riset Kimia | 1978-628X | [S4210177714](https://openalex.org/S4210177714) | 1 |
| Karbala International Journal of Modern Science | 2405-609X | [S4210226571](https://openalex.org/S4210226571) | 1 |
| Knowledge and Information Systems | 0219-1377 | [S81770430](https://openalex.org/S81770430) | 1 |
| Learning & Memory | 1072-0502 | [S73374563](https://openalex.org/S73374563) | 1 |
| Leukemia & lymphoma/Leukemia and lymphoma | 1026-8022 | [S27064115](https://openalex.org/S27064115) | 1 |
| Life | 2075-1729 | [S4210200765](https://openalex.org/S4210200765) | 1 |
| Life Science Alliance | 2575-1077 | [S4210202458](https://openalex.org/S4210202458) | 1 |
| Light Science & Applications | 2047-7538 | [S2498964232](https://openalex.org/S2498964232) | 1 |
| Lubricants | 2075-4442 | [S2736800165](https://openalex.org/S2736800165) | 1 |
| Luminescence | 1522-7235 | [S19375554](https://openalex.org/S19375554) | 1 |
| Machine Learning Science and Technology | 2632-2153 | [S4210200687](https://openalex.org/S4210200687) | 1 |
| MAPAN | 0970-3950 | [S122014475](https://openalex.org/S122014475) | 1 |
| Marine Biology | 0025-3162 | [S118082147](https://openalex.org/S118082147) | 1 |
| Marine Drugs | 1660-3397 | [S146563757](https://openalex.org/S146563757) | 1 |
| Marine Environmental Research | 0141-1136 | [S205788060](https://openalex.org/S205788060) | 1 |
| Marine Geophysical Research | 0025-3235 | [S82978933](https://openalex.org/S82978933) | 1 |
| Materiali in tehnologije | 1580-2949 | [S168665667](https://openalex.org/S168665667) | 1 |
| Materialia | 2589-1529 | [S2898317371](https://openalex.org/S2898317371) | 1 |
| Materials and Corrosion | 0043-2822 | [S123418790](https://openalex.org/S123418790) | 1 |
| Materials Characterization | 1044-5803 | [S53842986](https://openalex.org/S53842986) | 1 |
| Materials Letters X | 2590-1508 | [S4210180943](https://openalex.org/S4210180943) | 1 |
| Materials Performance | 0094-1492 | [S71281032](https://openalex.org/S71281032) | 1 |
| Materials Research Innovations | 1432-8917 | [S183484819](https://openalex.org/S183484819) | 1 |
| Materials Science and Engineering R Reports | 0927-796X | [S1018252914](https://openalex.org/S1018252914) | 1 |
| Materials Science and Technology | 0267-0836 | [S82336448](https://openalex.org/S82336448) | 1 |
| Materials Today Bio | 2590-0064 | [S4210219546](https://openalex.org/S4210219546) | 1 |
| Materials Today Catalysis | 2949-754X | [S4387288101](https://openalex.org/S4387288101) | 1 |
| Mathematical and Computational Applications | 1300-686X | [S4210201516](https://openalex.org/S4210201516) | 1 |
| Mathematical Biosciences | 0025-5564 | [S4210190100](https://openalex.org/S4210190100) | 1 |
| Measurement | 0263-2241 | [S147767848](https://openalex.org/S147767848) | 1 |
| Mechanics of Time-Dependent Materials | 1385-2000 | [S126682488](https://openalex.org/S126682488) | 1 |
| Mechanisms of Ageing and Development | 0047-6374 | [S6761461](https://openalex.org/S6761461) | 1 |
| Medicinal Chemistry | 1573-4064 | [S155723790](https://openalex.org/S155723790) | 1 |
| Medicine in Drug Discovery | 2590-0986 | [S4210216844](https://openalex.org/S4210216844) | 1 |
| Meta Gene | 2214-5400 | [S2898106244](https://openalex.org/S2898106244) | 1 |
| Metabolic Brain Disease | 0885-7490 | [S31409034](https://openalex.org/S31409034) | 1 |
| Metabolites | 2218-1989 | [S2764402194](https://openalex.org/S2764402194) | 1 |
| MetalMat | 2940-1402 | [S4387997647](https://openalex.org/S4387997647) | 1 |
| Methods and Applications in Fluorescence | 2050-6120 | [S2764635591](https://openalex.org/S2764635591) | 1 |
| Micro & Nano Letters | 1750-0443 | [S95685352](https://openalex.org/S95685352) | 1 |
| Micro and Nanostructures | 2773-0123 | [S4210180586](https://openalex.org/S4210180586) | 1 |
| Microbial Biotechnology | 1751-7915 | [S4210238104](https://openalex.org/S4210238104) | 1 |
| Microbial Ecology | 0095-3628 | [S97758720](https://openalex.org/S97758720) | 1 |
| Microbiology | 1350-0872 | [S196799759](https://openalex.org/S196799759) | 1 |
| Microbiology | 0026-2617 | [S4210199608](https://openalex.org/S4210199608) | 1 |
| Microbiology Australia | 1324-4272 | [S2764555716](https://openalex.org/S2764555716) | 1 |
| Microbiology Spectrum | 2165-0497 | [S2764766708](https://openalex.org/S2764766708) | 1 |
| Microscopy and Microanalysis | 1431-9276 | [S98208149](https://openalex.org/S98208149) | 1 |
| Modeling Earth Systems and Environment | 2363-6203 | [S2764607366](https://openalex.org/S2764607366) | 1 |
| MOJ Solar and Photoenergy Systems | 2577-8374 | [S4210203425](https://openalex.org/S4210203425) | 1 |
| Molecular and Biochemical Parasitology | 0166-6851 | [S144099348](https://openalex.org/S144099348) | 1 |
| Molecular and Clinical Oncology | 2049-9450 | [S2754683124](https://openalex.org/S2754683124) | 1 |
| Molecular Biology of the Cell | 1059-1524 | [S188085164](https://openalex.org/S188085164) | 1 |
| Molecular Crystals and Liquid Crystals | 1542-1406 | [S146005121](https://openalex.org/S146005121) | 1 |
| Molecular Medicine | 1076-1551 | [S6769275](https://openalex.org/S6769275) | 1 |
| Molecular Pain | 1744-8069 | [S49886757](https://openalex.org/S49886757) | 1 |
| Molecular Plant | 1674-2052 | [S150334665](https://openalex.org/S150334665) | 1 |
| Molecular Simulation | 0892-7022 | [S45504773](https://openalex.org/S45504773) | 1 |
| Molecular Therapy | 1525-0016 | [S51596929](https://openalex.org/S51596929) | 1 |
| Molecular Therapy — Nucleic Acids | 2162-2531 | [S2764969478](https://openalex.org/S2764969478) | 1 |
| Molecular Therapy — Oncolytics | 2372-7705 | [S2898235705](https://openalex.org/S2898235705) | 1 |
| MRS Bulletin | 0883-7694 | [S55806205](https://openalex.org/S55806205) | 1 |
| Nano hybrids and composites | 2234-9871 | [S4210222556](https://openalex.org/S4210222556) | 1 |
| Nano Select | 2688-4011 | [S4210201393](https://openalex.org/S4210201393) | 1 |
| Nano Today | 1748-0132 | [S183222223](https://openalex.org/S183222223) | 1 |
| Nano Trends | 2666-9781 | [S4387287985](https://openalex.org/S4387287985) | 1 |
| NanoImpact | 2452-0748 | [S2898242488](https://openalex.org/S2898242488) | 1 |
| Nanomedicine & Nanotechnology Open Access | 2574-187X | [S4210239728](https://openalex.org/S4210239728) | 1 |
| Nanotheranostics | 2206-7418 | [S4210240876](https://openalex.org/S4210240876) | 1 |
| Natural Product Reports | 0265-0568 | [S18855311](https://openalex.org/S18855311) | 1 |
| Natural Products Chemistry & Research | 2329-6836 | [S2764882758](https://openalex.org/S2764882758) | 1 |
| Nature Chemistry | 1755-4330 | [S202193212](https://openalex.org/S202193212) | 1 |
| Nature Environment and Pollution Technology | 0972-6268 | [S2764514638](https://openalex.org/S2764514638) | 1 |
| Nature Materials | 1476-1122 | [S103895331](https://openalex.org/S103895331) | 1 |
| Nature Nanotechnology | 1748-3387 | [S7822423](https://openalex.org/S7822423) | 1 |
| Nature Physics | 1745-2473 | [S156274416](https://openalex.org/S156274416) | 1 |
| Nature Reviews Methods Primers | 2662-8449 | [S4210231269](https://openalex.org/S4210231269) | 1 |
| Nelumbo | 0976-5069 | [S4210198012](https://openalex.org/S4210198012) | 1 |
| Network Modeling Analysis in Health Informatics and Bioinformatics | 2192-6670 | [S4210178532](https://openalex.org/S4210178532) | 1 |
| Neural Computing and Applications | 0941-0643 | [S147897268](https://openalex.org/S147897268) | 1 |
| Neurochemical Journal | 1819-7124 | [S115587109](https://openalex.org/S115587109) | 1 |
| Neurochemistry International | 0197-0186 | [S53315755](https://openalex.org/S53315755) | 1 |
| Neuroglia | 2571-6980 | [S4210223255](https://openalex.org/S4210223255) | 1 |
| Neuropharmacology | 0028-3908 | [S160566677](https://openalex.org/S160566677) | 1 |
| Neuroscience & Biobehavioral Reviews | 0149-7634 | [S170052170](https://openalex.org/S170052170) | 1 |
| Neuroscience Insights Advances in Brain Studies | 3071-0138 | [S7407056633](https://openalex.org/S7407056633) | 1 |
| Neuroscience Letters | 0304-3940 | [S203050076](https://openalex.org/S203050076) | 1 |
| Neurotoxicity Research | 1029-8428 | [S95346388](https://openalex.org/S95346388) | 1 |
| New Biotechnology | 1871-6784 | [S139345353](https://openalex.org/S139345353) | 1 |
| Next Sustainability | 2949-8236 | [S4387292877](https://openalex.org/S4387292877) | 1 |
| NFS Journal | 2352-3646 | [S2898411350](https://openalex.org/S2898411350) | 1 |
| Nitric Oxide | 1089-8603 | [S152998702](https://openalex.org/S152998702) | 1 |
| NOT FOUND REPOSITORY (Indian Institute of Science Bangalore) |  | [S4377196309](https://openalex.org/S4377196309) | 1 |
| npj Biofilms and Microbiomes | 2055-5008 | [S4210229179](https://openalex.org/S4210229179) | 1 |
| npj Materials Degradation | 2397-2106 | [S4210234193](https://openalex.org/S4210234193) | 1 |
| npj Microgravity | 2373-8065 | [S4210211936](https://openalex.org/S4210211936) | 1 |
| npj Systems Biology and Applications | 2056-7189 | [S4210213125](https://openalex.org/S4210213125) | 1 |
| Nuclear Instruments and Methods in Physics Research Section B Beam Interactions with Materials and Atoms | 0168-583X | [S113542562](https://openalex.org/S113542562) | 1 |
| Nucleic Acid Therapeutics | 2159-3337 | [S2489440031](https://openalex.org/S2489440031) | 1 |
| Nucleosides Nucleotides & Nucleic Acids | 1525-7770 | [S111464279](https://openalex.org/S111464279) | 1 |
| Nusantara Bioscience | 2087-3948 | [S4210174890](https://openalex.org/S4210174890) | 1 |
| Nutrition | 0899-9007 | [S59739785](https://openalex.org/S59739785) | 1 |
| Nutrition Metabolism and Cardiovascular Diseases | 0939-4753 | [S4455515](https://openalex.org/S4455515) | 1 |
| Nutrition Research | 0271-5317 | [S123713480](https://openalex.org/S123713480) | 1 |
| Nutritional Neuroscience | 1028-415X | [S132280141](https://openalex.org/S132280141) | 1 |
| Oncology Reports | 1021-335X | [S124357017](https://openalex.org/S124357017) | 1 |
| Oncology Research Featuring Preclinical and Clinical Cancer Therapeutics | 0965-0407 | [S146643948](https://openalex.org/S146643948) | 1 |
| Open Access Journal of Microbiology & Biotechnology | 2576-7771 | [S4210203039](https://openalex.org/S4210203039) | 1 |
| Open Access Journal of Science | 2575-9086 | [S4210234537](https://openalex.org/S4210234537) | 1 |
| Open Archive Toulouse Archive Ouverte (University of Toulouse) |  | [S4306401987](https://openalex.org/S4306401987) | 1 |
| Open Biology | 2046-2441 | [S80033963](https://openalex.org/S80033963) | 1 |
| Open Chemistry | 2391-5420 | [S4210229753](https://openalex.org/S4210229753) | 1 |
| Open Engineering | 2081-9927 | [S2738317984](https://openalex.org/S2738317984) | 1 |
| Open Forum Infectious Diseases | 2328-8957 | [S2735126445](https://openalex.org/S2735126445) | 1 |
| Open Journal of Physical Chemistry | 2162-1969 | [S2764559428](https://openalex.org/S2764559428) | 1 |
| Open Journal of Synthesis Theory and Applications | 2168-1244 | [S4210169739](https://openalex.org/S4210169739) | 1 |
| OpenNano | 2352-9520 | [S2898377343](https://openalex.org/S2898377343) | 1 |
| Optical and Quantum Electronics | 0306-8919 | [S133811445](https://openalex.org/S133811445) | 1 |
| Optical Engineering | 0091-3286 | [S175543413](https://openalex.org/S175543413) | 1 |
| Optics Express | 1094-4087 | [S178776955](https://openalex.org/S178776955) | 1 |
| Orbital - The Electronic Journal of Chemistry | 1984-6428 | [S2737921212](https://openalex.org/S2737921212) | 1 |
| Organic Communications | 1307-6175 | [S4210213175](https://openalex.org/S4210213175) | 1 |
| Pancreatology | 1424-3903 | [S193617204](https://openalex.org/S193617204) | 1 |
| Parasite Epidemiology and Control | 2405-6731 | [S2898382742](https://openalex.org/S2898382742) | 1 |
| Particulate Science And Technology | 0272-6351 | [S124230369](https://openalex.org/S124230369) | 1 |
| Pathogens and Disease | 2049-632X | [S2735191819](https://openalex.org/S2735191819) | 1 |
| Pathophysiology | 0928-4680 | [S14625721](https://openalex.org/S14625721) | 1 |
| Perspectives in Science | 2213-0209 | [S4210209735](https://openalex.org/S4210209735) | 1 |
| Pharmaceutical Chemistry Journal | 0091-150X | [S180695361](https://openalex.org/S180695361) | 1 |
| Pharmaceutical Development and Technology | 1083-7450 | [S80622011](https://openalex.org/S80622011) | 1 |
| Pharmaceutical Research | 0724-8741 | [S103865650](https://openalex.org/S103865650) | 1 |
| Pharmaceutics | 1999-4923 | [S30283931](https://openalex.org/S30283931) | 1 |
| Pharmacognosy Journal | 0975-3575 | [S2764874817](https://openalex.org/S2764874817) | 1 |
| Pharmacognosy Research | 0974-8490 | [S150556310](https://openalex.org/S150556310) | 1 |
| Pharmacological Reports | 1734-1140 | [S180401253](https://openalex.org/S180401253) | 1 |
| Pharmacological Research - Natural Products | 2950-1997 | [S4389157795](https://openalex.org/S4389157795) | 1 |
| Pharmacology Biochemistry and Behavior | 0091-3057 | [S59685179](https://openalex.org/S59685179) | 1 |
| Photosynthesis Research | 0166-8595 | [S88471346](https://openalex.org/S88471346) | 1 |
| physica status solidi (b) | 0370-1972 | [S71689831](https://openalex.org/S71689831) | 1 |
| Physical and Engineering Sciences in Medicine | 2662-4729 | [S4210170766](https://openalex.org/S4210170766) | 1 |
| Physics of the Solid State | 0367-3294 | [S1070115](https://openalex.org/S1070115) | 1 |
| Physiologia Plantarum | 0031-9317 | [S185046733](https://openalex.org/S185046733) | 1 |
| Phytoparasitica | 0334-2123 | [S116008648](https://openalex.org/S116008648) | 1 |
| Phytotherapy Research | 0951-418X | [S206789554](https://openalex.org/S206789554) | 1 |
| Plant and Cell Physiology | 0032-0781 | [S110997964](https://openalex.org/S110997964) | 1 |
| Plant and Soil | 0032-079X | [S11781297](https://openalex.org/S11781297) | 1 |
| Plant Biotechnology Reports | 1863-5466 | [S44784542](https://openalex.org/S44784542) | 1 |
| Plant Genetic Resources | 1479-2621 | [S116331598](https://openalex.org/S116331598) | 1 |
| Plant Growth Regulation | 0167-6903 | [S3204633](https://openalex.org/S3204633) | 1 |
| Plant Hormones | 3067-221X | [S5407048866](https://openalex.org/S5407048866) | 1 |
| Plant Pathology | 0032-0862 | [S63107127](https://openalex.org/S63107127) | 1 |
| Plant Signaling & Behavior | 1559-2316 | [S21838795](https://openalex.org/S21838795) | 1 |
| Planta Medica | 0032-0943 | [S39653451](https://openalex.org/S39653451) | 1 |
| Planta Medica Letters | 2199-157X | [S4210174759](https://openalex.org/S4210174759) | 1 |
| Plants | 2223-7747 | [S4210230202](https://openalex.org/S4210230202) | 1 |
| Plasma Processes and Polymers | 1612-8850 | [S17577527](https://openalex.org/S17577527) | 1 |
| PLoS Pathogens | 1553-7366 | [S2004986](https://openalex.org/S2004986) | 1 |
| Polymer Crystallization | 2573-7619 | [S4210178111](https://openalex.org/S4210178111) | 1 |
| Polymer-Plastics Technology and Engineering | 0360-2559 | [S203352922](https://openalex.org/S203352922) | 1 |
| Polymers from Renewable Resources | 2041-2479 | [S4210191292](https://openalex.org/S4210191292) | 1 |
| Polysaccharides | 2673-4176 | [S4210221811](https://openalex.org/S4210221811) | 1 |
| Powders | 2674-0516 | [S4210191603](https://openalex.org/S4210191603) | 1 |
| Pramana | 0304-4289 | [S4394736650](https://openalex.org/S4394736650) | 1 |
| Prayogik Rasayan | 2581-3323 | [S4210213597](https://openalex.org/S4210213597) | 1 |
| Precambrian Research | 0301-9268 | [S1025118869](https://openalex.org/S1025118869) | 1 |
| Proceedings of the Institution of Mechanical Engineers Part A Journal of Power and Energy | 0957-6509 | [S109525458](https://openalex.org/S109525458) | 1 |
| Proceedings of the National Academy of Sciences India Section A Physical Sciences | 0369-8203 | [S4210173097](https://openalex.org/S4210173097) | 1 |
| Progress in Energy | 2516-1083 | [S4210235888](https://openalex.org/S4210235888) | 1 |
| Progress in Energy and Combustion Science | 0360-1285 | [S65236890](https://openalex.org/S65236890) | 1 |
| Progress in Petrochemical Science | 2637-8035 | [S4210240200](https://openalex.org/S4210240200) | 1 |
| Progress in Reaction Kinetics and Mechanism | 0079-6743 | [S121492938](https://openalex.org/S121492938) | 1 |
| Propellants Explosives Pyrotechnics | 0721-3115 | [S181849574](https://openalex.org/S181849574) | 1 |
| Prospects in Pharmaceutical Sciences | 2080-1602 | [S4387282865](https://openalex.org/S4387282865) | 1 |
| Psychoneuroendocrinology | 0306-4530 | [S81924583](https://openalex.org/S81924583) | 1 |
| Pure and Applied Chemistry | 0033-4545 | [S142816121](https://openalex.org/S142816121) | 1 |
| Recent Progress in Materials | 2689-5846 | [S4210196564](https://openalex.org/S4210196564) | 1 |
| Recent Progress in Sciences | 3067-1574 | [S5407048855](https://openalex.org/S5407048855) | 1 |
| Regenerative Engineering and Translational Medicine | 2364-4133 | [S4210196775](https://openalex.org/S4210196775) | 1 |
| Regional Studies in Marine Science | 2352-4855 | [S2764732502](https://openalex.org/S2764732502) | 1 |
| Reports in Electrochemistry | 2230-4096 | [S4210220358](https://openalex.org/S4210220358) | 1 |
| Reproductive Biology | 1642-431X | [S2493898138](https://openalex.org/S2493898138) | 1 |
| Research & Reviews A Journal of Pharmacognosy | 2394-7276 | [S4210176574](https://openalex.org/S4210176574) | 1 |
| Research & Reviews: A Journal of Biotechnology | 2231-3826 | [S4306525878](https://openalex.org/S4306525878) | 1 |
| Research & Reviews: A Journal of Pharmacology | 2230-9861 | [S4306525880](https://openalex.org/S4306525880) | 1 |
| Research & Reviews: Journal of Herbal Science | 2278-2257 | [S4306525889](https://openalex.org/S4306525889) | 1 |
| Research in Microbiology | 0769-2609 | [S37853641](https://openalex.org/S37853641) | 1 |
| Research in Pharmaceutical Sciences | 1735-5362 | [S2739408508](https://openalex.org/S2739408508) | 1 |
| Research Portal (Queen's University Belfast) |  | [S4306402319](https://openalex.org/S4306402319) | 1 |
| Resources Conservation and Recycling | 0921-3449 | [S18051569](https://openalex.org/S18051569) | 1 |
| Results in Physics | 2211-3797 | [S2764941219](https://openalex.org/S2764941219) | 1 |
| Reviews in Chemical Engineering | 0167-8299 | [S186775512](https://openalex.org/S186775512) | 1 |
| Reviews in Environmental Science and Bio/Technology | 1569-1705 | [S4210175777](https://openalex.org/S4210175777) | 1 |
| Reviews in Medical Virology | 1052-9276 | [S163174342](https://openalex.org/S163174342) | 1 |
| Revista de Fomento Social | 0019-5235 | [S2764779124](https://openalex.org/S2764779124) | 1 |
| Rhizosphere | 2452-2198 | [S2898510056](https://openalex.org/S2898510056) | 1 |
| Ribogospodarsʹka nauka Ukraïni | 2075-1508 | [S2738126403](https://openalex.org/S2738126403) | 1 |
| RMIT Research Repository (RMIT University Library) |  | [S4306402074](https://openalex.org/S4306402074) | 1 |
| RNA Biology | 1547-6286 | [S143072383](https://openalex.org/S143072383) | 1 |
| RSC Applied Interfaces | 2755-3701 | [S4387288696](https://openalex.org/S4387288696) | 1 |
| Russian Journal of Applied Chemistry | 0021-888X | [S178325816](https://openalex.org/S178325816) | 1 |
| Russian Journal of Physical Chemistry A | 0036-0244 | [S15526297](https://openalex.org/S15526297) | 1 |
| Safety in Extreme Environments | 2524-8170 | [S4210219449](https://openalex.org/S4210219449) | 1 |
| Saudi Pharmaceutical Journal | 1319-0164 | [S34003737](https://openalex.org/S34003737) | 1 |
| Science China Chemistry | 1001-652X | [S147836164](https://openalex.org/S147836164) | 1 |
| Scientific African | 2468-2276 | [S4210198261](https://openalex.org/S4210198261) | 1 |
| Seeds | 2674-1024 | [S4210210535](https://openalex.org/S4210210535) | 1 |
| Sensing and Bio-Sensing Research | 2214-1804 | [S2764350490](https://openalex.org/S2764350490) | 1 |
| Sensors and Actuators Reports | 2666-0539 | [S4210203583](https://openalex.org/S4210203583) | 1 |
| Sensors International | 2666-3511 | [S4210227652](https://openalex.org/S4210227652) | 1 |
| SERIES CHEMISTRY AND TECHNOLOGY | 2224-5286 | [S4210189621](https://openalex.org/S4210189621) | 1 |
| Signal Image and Video Processing | 1863-1703 | [S156904493](https://openalex.org/S156904493) | 1 |
| Signal Transduction and Targeted Therapy | 2059-3635 | [S2739142469](https://openalex.org/S2739142469) | 1 |
| Sleep Medicine | 1389-9457 | [S183718435](https://openalex.org/S183718435) | 1 |
| SM Journal of Biometrics & Biostatistics | 2573-5470 | [S4210184347](https://openalex.org/S4210184347) | 1 |
| Smart Agricultural Technology | 2772-3755 | [S4210238883](https://openalex.org/S4210238883) | 1 |
| Social Network Analysis and Mining | 1869-5450 | [S2764891196](https://openalex.org/S2764891196) | 1 |
| Soft Materials | 1539-445X | [S72998273](https://openalex.org/S72998273) | 1 |
| SOJ Materials Science & Engineering | 2372-0964 | [S4210223925](https://openalex.org/S4210223925) | 1 |
| Solvent Extraction and Ion Exchange | 0736-6299 | [S81873017](https://openalex.org/S81873017) | 1 |
| Solvent Extraction Research and Development Japan | 1341-7215 | [S4210176173](https://openalex.org/S4210176173) | 1 |
| South African Journal of Botany | 0254-6299 | [S31493525](https://openalex.org/S31493525) | 1 |
| South African Journal of Chemical Engineering | 1026-9185 | [S2764476899](https://openalex.org/S2764476899) | 1 |
| South Asian Journal of Experimental Biology | 2230-9799 | [S2764711942](https://openalex.org/S2764711942) | 1 |
| Spatial Information Research | 2366-3286 | [S2764600325](https://openalex.org/S2764600325) | 1 |
| SPE Journal | 1086-055X | [S35794861](https://openalex.org/S35794861) | 1 |
| SRELS Journal of Information Management | 0972-2467 | [S2764949411](https://openalex.org/S2764949411) | 1 |
| Standards in Genomic Sciences | 1944-3277 | [S174963459](https://openalex.org/S174963459) | 1 |
| Stem Cell Reports | 2213-6711 | [S2764425922](https://openalex.org/S2764425922) | 1 |
| Stem Cell Research | 1873-5061 | [S81007815](https://openalex.org/S81007815) | 1 |
| Stroke | 0039-2499 | [S62532593](https://openalex.org/S62532593) | 1 |
| Sugar Tech | 0972-1525 | [S94618080](https://openalex.org/S94618080) | 1 |
| Surface and Interface Analysis | 0142-2421 | [S114406758](https://openalex.org/S114406758) | 1 |
| Sustainability | 2071-1050 | [S10134376](https://openalex.org/S10134376) | 1 |
| Sustainable Chemistry | 2673-4079 | [S4210193079](https://openalex.org/S4210193079) | 1 |
| Sustainable Cities and Society | 2210-6707 | [S163634330](https://openalex.org/S163634330) | 1 |
| Sustainable Microbiology | 2755-1970 | [S5407027484](https://openalex.org/S5407027484) | 1 |
| Systems Biology in Reproductive Medicine | 1939-6368 | [S171426405](https://openalex.org/S171426405) | 1 |
| Talanta | 0039-9140 | [S124795565](https://openalex.org/S124795565) | 1 |
| Tenside Surfactants Detergents | 0040-3490 | [S132611805](https://openalex.org/S132611805) | 1 |
| Thalassas An International Journal of Marine Sciences | 0212-5919 | [S2764589869](https://openalex.org/S2764589869) | 1 |
| The Bryologist | 0007-2745 | [S114265159](https://openalex.org/S114265159) | 1 |
| The Egyptian Journal of Aquatic Research | 1687-4285 | [S2764850074](https://openalex.org/S2764850074) | 1 |
| The European Physical Journal Special Topics | 1951-6355 | [S138062970](https://openalex.org/S138062970) | 1 |
| The ISME Journal | 1751-7362 | [S149218730](https://openalex.org/S149218730) | 1 |
| The Journal of Basic and Applied Zoology | 2090-9896 | [S2764605959](https://openalex.org/S2764605959) | 1 |
| The Journal of Immunology | 0022-1767 | [S38008053](https://openalex.org/S38008053) | 1 |
| The Journal of Phytology | 2075-6240 | [S2764427209](https://openalex.org/S2764427209) | 1 |
| The Journal of Steroid Biochemistry and Molecular Biology | 0960-0760 | [S168421034](https://openalex.org/S168421034) | 1 |
| The Lancet | 0099-5355 | [S49861241](https://openalex.org/S49861241) | 1 |
| The Microbe | 2950-1946 | [S4387290354](https://openalex.org/S4387290354) | 1 |
| The Natural Products Journal | 2210-3155 | [S4210177943](https://openalex.org/S4210177943) | 1 |
| Theoretical and Applied Fracture Mechanics | 0167-8442 | [S179906512](https://openalex.org/S179906512) | 1 |
| Theoretical Foundations of Chemical Engineering | 0040-5795 | [S56676470](https://openalex.org/S56676470) | 1 |
| Therapeutic Delivery | 2041-5990 | [S89829989](https://openalex.org/S89829989) | 1 |
| Thermal Science and Engineering Progress | 2451-9049 | [S4210220034](https://openalex.org/S4210220034) | 1 |
| Thermochimica Acta | 0040-6031 | [S160957154](https://openalex.org/S160957154) | 1 |
| Total Environment Microbiology | 3050-6417 | [S5407047435](https://openalex.org/S5407047435) | 1 |
| Toxicology | 0300-483X | [S128555845](https://openalex.org/S128555845) | 1 |
| Toxicology and Industrial Health | 0748-2337 | [S6336342](https://openalex.org/S6336342) | 1 |
| Toxicology Research | 2045-452X | [S2494971184](https://openalex.org/S2494971184) | 1 |
| Traffic | 1398-9219 | [S174148068](https://openalex.org/S174148068) | 1 |
| Transboundary and Emerging Diseases | 1865-1674 | [S91749377](https://openalex.org/S91749377) | 1 |
| Transition Metal Chemistry | 0340-4285 | [S9018758](https://openalex.org/S9018758) | 1 |
| Transportation research procedia | 2352-1457 | [S2764743394](https://openalex.org/S2764743394) | 1 |
| Trends in Chemistry | 2589-5974 | [S4210210487](https://openalex.org/S4210210487) | 1 |
| Trends in Pharmacological Sciences | 0165-6147 | [S31167473](https://openalex.org/S31167473) | 1 |
| Tribology International | 0301-679X | [S24284137](https://openalex.org/S24284137) | 1 |
| Tropical Medicine and Infectious Disease | 2414-6366 | [S2737916383](https://openalex.org/S2737916383) | 1 |
| Tropical Plant Research | 2349-1183 | [S4210212737](https://openalex.org/S4210212737) | 1 |
| Tuberculosis | 1472-9792 | [S29633479](https://openalex.org/S29633479) | 1 |
| TURKISH JOURNAL OF CHEMISTRY | 1300-0527 | [S185920249](https://openalex.org/S185920249) | 1 |
| UPI Journal of Pharmaceutical Medical and Health Sciences | 2581-4532 | [S4210224360](https://openalex.org/S4210224360) | 1 |
| Vegetos | 0970-4078 | [S48234298](https://openalex.org/S48234298) | 1 |
| Veterinary World | 0972-8988 | [S2738474774](https://openalex.org/S2738474774) | 1 |
| Virology Journal | 1743-422X | [S115714813](https://openalex.org/S115714813) | 1 |
| Virulence | 2150-5594 | [S2484688887](https://openalex.org/S2484688887) | 1 |
| Virus Evolution | 2057-1577 | [S2734951655](https://openalex.org/S2734951655) | 1 |
| Virus Genes | 0920-8569 | [S69033458](https://openalex.org/S69033458) | 1 |
| Virus Research | 0168-1702 | [S114911520](https://openalex.org/S114911520) | 1 |
| Viruses | 1999-4915 | [S55776271](https://openalex.org/S55776271) | 1 |
| Waste Management | 0956-053X | [S19266977](https://openalex.org/S19266977) | 1 |
| Waste Management Bulletin | 2949-7507 | [S4387289639](https://openalex.org/S4387289639) | 1 |
| Water Conservation Science and Engineering | 2364-5687 | [S4210232357](https://openalex.org/S4210232357) | 1 |
| Water Science and Engineering | 1674-2370 | [S2764536960](https://openalex.org/S2764536960) | 1 |
| Wear | 0043-1648 | [S16737290](https://openalex.org/S16737290) | 1 |
| Wiley Interdisciplinary Reviews Nanomedicine and Nanobiotechnology | 1939-0041 | [S132212666](https://openalex.org/S132212666) | 1 |
| Wireless Communications and Mobile Computing | 1530-8669 | [S235346](https://openalex.org/S235346) | 1 |
| World Journal of Applied Chemistry | 2637-5966 | [S4210228653](https://openalex.org/S4210228653) | 1 |
| World Journal of Nano Science and Engineering | 2161-4954 | [S2764627458](https://openalex.org/S2764627458) | 1 |
| Wound Repair and Regeneration | 1067-1927 | [S121715350](https://openalex.org/S121715350) | 1 |
| YMER Digital | 0044-0477 | [S4210183410](https://openalex.org/S4210183410) | 1 |
| Zeitschrift für anorganische und allgemeine Chemie | 0044-2313 | [S171987449](https://openalex.org/S171987449) | 1 |
| Zeitschrift für Physikalische Chemie | 0044-3336 | [S89003483](https://openalex.org/S89003483) | 1 |
| Физика металлов и металловедение | 0015-3230 | [S99252752](https://openalex.org/S99252752) | 1 |
| Химико-фармацевтический журнал | 0023-1134 | [S4210218453](https://openalex.org/S4210218453) | 1 |

## Appendix B — Conferences and proceedings (82)

22 conference papers have no venue name in OpenAlex.

| Venue | ISSN | OpenAlex source | Papers |
|---|---|---|---:|
| AIP conference proceedings |  | [S2764696622](https://openalex.org/S2764696622) | 25 |
| ACS symposium series |  | [S205053445](https://openalex.org/S205053445) | 9 |
| IOP Conference Series Materials Science and Engineering |  | [S4210189194](https://openalex.org/S4210189194) | 8 |
| Indian Control Conference |  | [S4306418869](https://openalex.org/S4306418869) | 6 |
| International Symposium on Embedded Computing and System Design (ISED) |  | [S7407087878](https://openalex.org/S7407087878) | 6 |
| Communications in computer and information science |  | [S2764900261](https://openalex.org/S2764900261) | 4 |
| EPJ Web of Conferences |  | [S19068271](https://openalex.org/S19068271) | 4 |
| Journal of Physics Conference Series |  | [S4210187594](https://openalex.org/S4210187594) | 4 |
| Energy Procedia |  | [S75069817](https://openalex.org/S75069817) | 3 |
| International Conference on Technological Advancements and Innovations (ICTAI) |  | [S4363608330](https://openalex.org/S4363608330) | 3 |
| International Conference on Wireless Communications, Signal Processing and Networking (WiSPNET) |  | [S7407086507](https://openalex.org/S7407086507) | 3 |
| International Vacuum Nanoelectronics Conference |  | [S4306420253](https://openalex.org/S4306420253) | 3 |
| Photonics in Dermatology and Plastic Surgery |  | [S7407088441](https://openalex.org/S7407088441) | 3 |
| Conference on Lasers and Electro-Optics |  | [S4306418073](https://openalex.org/S4306418073) | 2 |
| Conference on Lasers and Electro-Optics Pacific Rim (CLEO-PR) |  | [S7407089323](https://openalex.org/S7407089323) | 2 |
| ECS Transactions |  | [S4210205149](https://openalex.org/S4210205149) | 2 |
| Environmental science and engineering |  | [S4210184122](https://openalex.org/S4210184122) | 2 |
| IEEE Asia Pacific Conference on Circuits and Systems (APCCAS) |  | [S7407087888](https://openalex.org/S7407087888) | 2 |
| IEEE International Conference on Nano/Micro Engineered and Molecular Systems |  | [S4393918698](https://openalex.org/S4393918698) | 2 |
| IEEE Region 10 Symposium (TENSYMP) |  | [S4363605250](https://openalex.org/S4363605250) | 2 |
| International Conference on Advances in Computing, Communications and Informatics (ICACCI) |  | [S7407087405](https://openalex.org/S7407087405) | 2 |
| International Conference on Communication Systems & Networks (COMSNETS) |  | [S7407088473](https://openalex.org/S7407088473) | 2 |
| International conference on fiber optics and photonics |  | [S4306513744](https://openalex.org/S4306513744) | 2 |
| International Conference on Ultrafast Phenomena |  | [S4306513827](https://openalex.org/S4306513827) | 2 |
| Language Resources and Evaluation Conference (LREC) |  | [S7407088301](https://openalex.org/S7407088301) | 2 |
| Lecture notes in civil engineering |  | [S4210178770](https://openalex.org/S4210178770) | 2 |
| Lecture notes on data engineering and communications technologies |  | [S4210216571](https://openalex.org/S4210216571) | 2 |
| 2020 IEEE International Systems Conference (SysCon) |  | [S4306498685](https://openalex.org/S4306498685) | 1 |
| Accademia University Press eBooks |  | [S4306462766](https://openalex.org/S4306462766) | 1 |
| Advances in science and technology |  | [S136072078](https://openalex.org/S136072078) | 1 |
| Annual Meeting of the Forum for Information Retrieval Evaluation (FIRE) |  | [S7407088045](https://openalex.org/S7407088045) | 1 |
| ASCE International Airfield and Highway Pavements Conference |  | [S4306501207](https://openalex.org/S4306501207) | 1 |
| E3S Web of Conferences |  | [S4210186093](https://openalex.org/S4210186093) | 1 |
| Frontiers in Optics + Laser Science (FiO, LS) |  | [S4363604389](https://openalex.org/S4363604389) | 1 |
| HAL (Le Centre pour la Communication Scientifique Directe) |  | [S4306402512](https://openalex.org/S4306402512) | 1 |
| IEEE International Conference on Advanced Computing (IACC) |  | [S7407087243](https://openalex.org/S7407087243) | 1 |
| IEEE International Conference on Nanotechnology (IEEE-NANO) |  | [S4363608401](https://openalex.org/S4363608401) | 1 |
| IEEE International Conference on Power Electronics, Drives and Energy Systems |  | [S4306418702](https://openalex.org/S4306418702) | 1 |
| IEEE International Conference on Smart Technologies for Power, Energy and Control (STPEC) |  | [S4363608150](https://openalex.org/S4363608150) | 1 |
| IEEE International Conference on Sustainable Energy and Future Electric Transportation (SEFET) |  | [S4363607997](https://openalex.org/S4363607997) | 1 |
| IEEE International Transportation Electrification Conference (ITEC-India) |  | [S7407087001](https://openalex.org/S7407087001) | 1 |
| IEEE International WIE Conference on Electrical and Computer Engineering |  | [S4306422764](https://openalex.org/S4306422764) | 1 |
| IEEE Power India International Conference |  | [S4306422824](https://openalex.org/S4306422824) | 1 |
| IEEE Transportation Electrification Conference (ITEC-India) |  | [S4306498168](https://openalex.org/S4306498168) | 1 |
| IEEE Wireless Communications and Networking Conference |  | [S4210195247](https://openalex.org/S4210195247) | 1 |
| Infoscience (Ecole Polytechnique Fédérale de Lausanne) |  | [S4306400487](https://openalex.org/S4306400487) | 1 |
| International Conference on Automation, Computing and Renewable Systems (ICACRS) |  | [S4363607919](https://openalex.org/S4363607919) | 1 |
| International Conference on Computational Linguistics |  | [S4306419219](https://openalex.org/S4306419219) | 1 |
| International Conference on Computer and Communication Technology |  | [S4306419230](https://openalex.org/S4306419230) | 1 |
| International Conference on Computer, Control and Robotics (ICCCR) |  | [S7407085927](https://openalex.org/S7407085927) | 1 |
| International Conference on Computing and Communications Technologies (ICCCT) |  | [S4363608425](https://openalex.org/S4363608425) | 1 |
| International Conference on Computing Communication Control and automation |  | [S4306419281](https://openalex.org/S4306419281) | 1 |
| International Conference on Computing, Analytics and Security Trends |  | [S4306423445](https://openalex.org/S4306423445) | 1 |
| International Conference on Computing, Communication and Networking Technologies (ICCCNT) |  | [S4306497833](https://openalex.org/S4306497833) | 1 |
| International Conference on Edge Computing and Applications (ICECAA) |  | [S4363607824](https://openalex.org/S4363607824) | 1 |
| International Conference on Electrical, Electronics, Information and Communication Technologies (ICEEICT) |  | [S4363608040](https://openalex.org/S4363608040) | 1 |
| International Conference on Emerging Electronics (ICEE) |  | [S7407087837](https://openalex.org/S7407087837) | 1 |
| International Conference on High Performance Big Data and Intelligent Systems (HPBD&IS) |  | [S7407089310](https://openalex.org/S7407089310) | 1 |
| International Conference on Innovative Computing, Intelligent Communication and Smart Electrical Systems (ICSES) |  | [S4363607988](https://openalex.org/S4363607988) | 1 |
| International Conference on Innovative Practices in Technology and Management (ICIPTM) |  | [S4363608223](https://openalex.org/S4363608223) | 1 |
| International Conference on Multidisciplinary Engineering and Applied Science (ICMEAS) |  | [S7407087522](https://openalex.org/S7407087522) | 1 |
| International Conference on Power and Embedded Drive Control (ICPEDC) |  | [S4306498406](https://openalex.org/S4306498406) | 1 |
| International Conference on Recent Trends on Electronics, Information, Communication & Technology (RTEICT) |  | [S4306498424](https://openalex.org/S4306498424) | 1 |
| International Conference on Smart Electronics and Communication (ICOSEC) |  | [S4306498765](https://openalex.org/S4306498765) | 1 |
| International Conference on Technological Advancements in Power and Energy (TAP Energy) |  | [S4306498213](https://openalex.org/S4306498213) | 1 |
| Interspeech (USB) |  | [S4393918409](https://openalex.org/S4393918409) | 1 |
| IOP Conference Series Earth and Environmental Science |  | [S4210195883](https://openalex.org/S4210195883) | 1 |
| JSAP-Optica Joint Symposia |  | [S7407088332](https://openalex.org/S7407088332) | 1 |
| Lecture notes in electrical engineering |  | [S4210179954](https://openalex.org/S4210179954) | 1 |
| Lecture notes in mechanical engineering |  | [S4210184193](https://openalex.org/S4210184193) | 1 |
| MEC International Conference on Big Data and Smart City (ICBDSC) |  | [S7407086117](https://openalex.org/S7407086117) | 1 |
| National and International ISHMT-ASTFE Heat and Mass Transfer Conference (IHMTC) |  | [S4306523302](https://openalex.org/S4306523302) | 1 |
| Nonlinear Optics |  | [S104011845](https://openalex.org/S104011845) | 1 |
| Optical Sensors |  | [S7407088807](https://openalex.org/S7407088807) | 1 |
| Procedia Engineering |  | [S45645249](https://openalex.org/S45645249) | 1 |
| Proceedings of IEEE Southeastcon |  | [S4393917016](https://openalex.org/S4393917016) | 1 |
| Qatar Foundation Annual Research Conference (ARC) |  | [S4306525075](https://openalex.org/S4306525075) | 1 |
| Research Portal (Queen's University Belfast) |  | [S4306402319](https://openalex.org/S4306402319) | 1 |
| SAE technical papers on CD-ROM/SAE technical paper series |  | [S4210202285](https://openalex.org/S4210202285) | 1 |
| Sustainable civil infrastructures |  | [S4210174136](https://openalex.org/S4210174136) | 1 |
| Text REtrieval Conference |  | [S4306421043](https://openalex.org/S4306421043) | 1 |
| Wireless Network Security |  | [S4306421195](https://openalex.org/S4306421195) | 1 |
