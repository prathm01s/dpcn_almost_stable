"""Phase II tables (src/stats/phase2.py, D-34): internal consistency with the dataset."""

import pandas as pd

T = "stats/tables/"


def _ov():
    return pd.read_csv(T + "phase2_overview.csv").set_index("institution")


def test_overview_counts_consistent():
    ov = _ov()
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    assert ov.at["Group 24 Combined", "papers"] == ext["work_id"].nunique()
    for lab in ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]:
        assert ov.at[lab, "papers"] == ext[ext["institution"] == lab]["work_id"].nunique()
    for name, r in ov.iterrows():
        assert r["q1_if_gt10"] <= r["q1_if_gt5"] <= r["q1_papers"] <= r["papers"], name
        assert r["papers_lt10_authors"] + r["papers_ge10_authors"] == r["papers"], name
        assert r["papers_100plus_authors"] <= r["papers_ge30_authors"] <= r["papers_ge10_authors"], name
        assert r["collab_institutions_indian"] + r["collab_institutions_foreign"] == r["collab_institutions"], name


def test_by_year_sums_to_total():
    ov, yr = _ov(), pd.read_csv(T + "phase2_overview_by_year.csv")
    for name, g in yr.groupby("institution"):
        for col in ["papers", "q1_papers", "q1_if_gt5", "q1_if_gt10", "papers_ge10_authors"]:
            assert g[col].sum() == ov.at[name, col], (name, col)


def test_author_counts_cover_corpus():
    wac = pd.read_csv("data/final/work_author_counts.csv")
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    assert set(wac["work_id"]) == set(ext["work_id"])
    assert (wac["n_authors"] >= 1).all() and (wac["n_authors"] <= 100).all()
    # every paper has at least as many authors as lab author rows
    lab_rows = ext.groupby("work_id")["author"].nunique()
    m = wac.set_index("work_id")["n_authors"]
    capped = wac.set_index("work_id")["authors_capped"].astype(str).str.upper() == "TRUE"
    short = (m < lab_rows.reindex(m.index)) & ~capped
    assert short.mean() < 0.005, f"{short.sum()} papers list fewer authors than lab author rows"


def test_faculty_comparison_matches_faculty_master():
    f = pd.read_csv(T + "phase2_faculty_comparison.csv")
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    m = f.merge(fm, on="faculty_id")
    assert len(f) == (fm["n_papers_corpus"].astype(int) > 0).sum()
    assert (m["papers"] == m["n_papers_corpus"].astype(int)).all()
    assert (m["citations"] == m["n_citations_corpus"].astype(int)).all()
    assert (f["q1_if_gt10"] <= f["q1_if_gt5"]).all() and (f["q1_if_gt5"] <= f["q1_papers"]).all()


def test_top30_sorted_by_if():
    t = pd.read_csv(T + "phase2_top30_by_if.csv")
    for name, g in t.groupby("institution"):
        assert len(g) == 30, name
        assert g.sort_values("rank")["journal_if"].is_monotonic_decreasing, name


def test_citing_diagnostics_shares_are_percentages():
    d = pd.read_csv(T + "phase2_citing_institutions_diagnostics.csv")
    for c in ["stacking_pct", "shared_author_pct", "lab_coauthor_pct", "top_author_pct", "recent_pct"]:
        assert d[c].between(0, 100).all(), c
    s = pd.read_csv(T + "phase2_citing_sectors_by_year.csv")
    assert (s["non_governmental_citing_papers"] <= s["indian_citing_papers"]).all()
