"""Journal impact-factor analogue per paper: SCImago 'Cites / Doc. (2 years)' (Scopus data, not Clarivate JIF).

Shared by src/stats (Phase II tables) and src/dashboard (the "Journal IF" filter), so both use the same value.
"""

from typing import Dict

import pandas as pd

from src.common.logging import get_logger

logger = get_logger("journal_if")


def journal_if_lookup(df_papers: pd.DataFrame) -> Dict[str, float]:
    """work_id -> SCImago 'Cites / Doc. (2 years)' of the journal, an impact-factor analogue on Scopus data.

    Taken from the same SCImago year as the paper's quartile (quartile_year_used), matched on issn / issn_l and
    then on the cleaned journal title, as in step 08. Not Clarivate's JIF. Papers without a quartile get no value.
    """
    import importlib
    import pyreadr
    from src.common.issn import to_sjr_issn

    step08 = importlib.import_module("src.collect.08_resolve_quartiles")
    sjr = list(pyreadr.read_r("data/external/sjr_journals.rda").values())[0]
    sjr = sjr[(sjr["year"] >= 2014) & sjr["citations_doc_2years"].notna()]
    by_issn: Dict[tuple, float] = {}
    by_title: Dict[tuple, float] = {}
    for yr, issns, title, cd in zip(sjr["year"].astype(int), sjr["issn"], sjr["title"], sjr["citations_doc_2years"]):
        for i in step08.parse_issns_from_sjr(issns):
            by_issn[(yr, i)] = float(cd)
        t = step08.clean_title_for_match(title)
        if t:
            by_title[(yr, t)] = float(cd)

    out: Dict[str, float] = {}
    for wid, yr, issn, issn_l, journal in df_papers.loc[
        df_papers["quartile_year_used"].astype(str) != "",
        ["work_id", "quartile_year_used", "issn", "issn_l", "journal_name"],
    ].itertuples(index=False):
        y = int(float(yr))
        keys = [(y, k) for k in (to_sjr_issn(str(issn)), to_sjr_issn(str(issn_l))) if k]
        val = next((by_issn[k] for k in keys if k in by_issn), None)
        if val is None:
            val = by_title.get((y, step08.clean_title_for_match(journal)))
        if val is not None:
            out[wid] = round(val, 2)
    logger.info(f"Journal IF (SCImago 2-yr cites/doc) for {len(out):,} papers")
    return out
