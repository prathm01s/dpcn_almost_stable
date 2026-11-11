"""Global benchmark (D-35): the peer rules hold in the output and the tables are consistent."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

G = Path("data/final/global")
T = Path("stats/tables")
pytestmark = pytest.mark.skipif(not (T / "global_summary.csv").exists(), reason="global benchmark not built")

LABS = ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"]


def _cfg():
    with open("config/global_benchmark.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_scope_covers_configured_share():
    sc = pd.read_csv(G / "scope_subfields.csv")
    inside = sc[sc["in_scope"]]
    assert inside["share_pct"].sum() >= 100 * _cfg()["scope_coverage"] - 1e-6
    # minimal: dropping the last scope subfield falls below the target
    assert inside["share_pct"].sum() - inside["share_pct"].iloc[-1] < 100 * _cfg()["scope_coverage"]


def test_peers_follow_the_rules():
    cfg = _cfg()
    p = pd.read_csv(G / "peers.csv", dtype=str, keep_default_na=False)
    c = pd.read_csv(G / "candidates.csv", dtype=str, keep_default_na=False)
    ex = set(pd.read_csv("config/overrides/global_peer_exclusions.csv", dtype=str)["institution_id"])
    assert sorted(p[p["group"] == "CSIR lab"]["name"]) == sorted(LABS)
    for country in cfg["countries"].values():
        tw = p[p["group"] == country]
        assert len(tw) <= cfg["peers_per_country"]
        assert tw["twin_of"].is_unique and set(tw["twin_of"]) <= set(LABS)
        assert (tw["similarity"].astype(float) >= cfg["min_similarity"]).all()
        for iid in tw["institution_id"]:
            row = c[(c["institution_id"] == iid) & (c["country"] == country)].iloc[0]
            assert row["rejected_because"] == "" and row["type"] in cfg["candidates"]["keep_types"]
            assert iid not in ex
    assert set(p[p["group"] == "India"]["institution_id"]) == {x["id"] for x in cfg["indian_peers"]}


def test_twin_is_best_available_match():
    """Greedy rule: a candidate never picked was available all along, so it cannot be more similar
    to a lab than that lab's twin; a lab without a twin has no free candidate above the floor."""
    cfg = _cfg()
    c = pd.read_csv(G / "candidates.csv", keep_default_na=False)
    for country, g in c[c["sim_CSIR-NCL"] != ""].groupby("country"):
        twins = g[g["selected_twin_of"] != ""]
        free = g[g["selected_twin_of"] == ""]
        for lab in LABS:
            best_free = free[f"sim_{lab}"].astype(float).max() if len(free) else 0.0
            t = twins[twins["selected_twin_of"] == lab]
            if len(t):
                assert best_free <= float(t[f"sim_{lab}"].iloc[0]) + 1e-9, (country, lab)
            else:
                assert best_free < cfg["min_similarity"], (country, lab)


def test_excluded_institutions_are_marked():
    c = pd.read_csv(G / "candidates.csv", dtype=str, keep_default_na=False)
    ex = pd.read_csv("config/overrides/global_peer_exclusions.csv", dtype=str)
    for _, r in ex.iterrows():
        rows = c[(c["institution_id"] == r["institution_id"]) & (c["country"] == r["country"])]
        assert len(rows) == 1, r["name"]
        assert rows["rejected_because"].iloc[0].startswith("not a stand-alone institute"), r["name"]


def test_benchmark_counts_nest():
    b = pd.read_csv(G / "bench_by_year.csv")
    assert (b["top1"] <= b["top10"]).all()
    assert (b["top10"] <= b["papers_scope"]).all()
    assert (b["above_world"] <= b["papers_scope"]).all()
    assert (b["intl"] <= b["papers_scope"]).all()
    assert (b["papers_scope"] <= b["papers_all"]).all()
    cfg = _cfg()
    assert b["year"].min() == cfg["years"]["start"] and b["year"].max() == cfg["years"]["end"]


def test_summary_matches_yearly_data():
    b = pd.read_csv(G / "bench_by_year.csv", dtype={"institution_id": str})
    s = pd.read_csv(T / "global_summary.csv", dtype={"institution_id": str}).set_index("institution_id")
    tot = b.groupby("institution_id").sum(numeric_only=True)
    for iid, r in s.iterrows():
        assert r["papers_scope"] == tot.at[iid, "papers_scope"]
        assert abs(r["top10_pct"] - 100 * tot.at[iid, "top10"] / tot.at[iid, "papers_scope"]) < 0.01


def test_country_relations_consistent():
    cr = pd.read_csv(T / "global_country_relations.csv")
    assert "IN" not in set(cr["country_code"])
    assert (cr["papers_2016_2020"] + cr["papers_2021_2026"] == cr["papers"]).all()
    assert (cr[["papers_ncl", "papers_iict", "papers_cecri"]].sum(axis=1) >= cr["papers"]).all()
    assert cr["rank"].tolist() == list(range(1, len(cr) + 1))
    assert cr["papers"].is_monotonic_decreasing


def test_links_cover_every_lab_peer_pair():
    lk = pd.read_csv(T / "global_links.csv", dtype={"institution_id": str})
    p = pd.read_csv(T / "global_peers.csv", dtype={"institution_id": str})
    n_peers = (p["group"] != "CSIR lab").sum()
    assert len(lk) == 3 * n_peers
    assert (lk[["coauthored_papers", "peer_papers_citing_lab", "peer_papers_cited_by_lab"]] >= 0).all().all()
    f = p[~p["group"].isin(["CSIR lab", "India"])]
    twins = set(zip(f["twin_of"].fillna(""), f["institution_id"]))
    assert lk["is_twin"].sum() == len(f)
    for _, r in lk[lk["is_twin"]].iterrows():
        assert (r["lab"], r["institution_id"]) in twins


def test_dashboard_payload_matches_tables():
    path = Path("dashboard/data/g24_global.js")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("window.G24_GLOBAL = ")
    d = json.loads(text[len("window.G24_GLOBAL = "):].rstrip().rstrip(";"))
    s = pd.read_csv(T / "global_summary.csv", dtype={"institution_id": str})
    assert [r["papers_scope"] for r in d["summary"]] == s["papers_scope"].tolist()
    assert len(d["exclusions"]) == len(pd.read_csv("config/overrides/global_peer_exclusions.csv"))
    assert "api_key" not in text


def test_indian_universities_table():
    """Former Study 1.1 (D-39): same definition as the peer links, exact name matching."""
    u = pd.read_csv(T / "global_indian_universities.csv")
    from src.stats.global_benchmark import UNIVERSITIES
    assert len(u) == 4 * len(UNIVERSITIES)
    names = set(pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
                .pipe(lambda c: set(";".join(c["source_inst"]).split(";")) | set(";".join(c["target_inst"]).split(";"))))
    assert {n for n, _, _ in UNIVERSITIES} <= names
    for uni, g in u.groupby("university"):
        each = g[g["lab"] != "All three"]
        allr = g[g["lab"] == "All three"].iloc[0]
        # distinct papers over the three labs: at least the largest lab, at most the sum
        assert each["papers_citing_lab"].max() <= allr["papers_citing_lab"] <= each["papers_citing_lab"].sum(), uni
        assert each["papers_cited_by_lab"].max() <= allr["papers_cited_by_lab"] <= each["papers_cited_by_lab"].sum(), uni


def test_university_counts_agree_with_peer_links():
    """IISc, IIT Bombay and IIT Madras are counted twice from independent sources; they must agree closely."""
    u = pd.read_csv(T / "global_indian_universities.csv")
    lk = pd.read_csv(T / "global_links.csv")
    m = u.merge(lk, left_on=["lab", "university"], right_on=["lab", "short"])
    assert len(m) == 9
    for a, b in (("papers_citing_lab", "peer_papers_citing_lab"), ("papers_cited_by_lab", "peer_papers_cited_by_lab")):
        assert ((m[a] - m[b]).abs() / m[b]).max() < 0.10


def test_home_teaser_matches_tables():
    text = Path("dashboard/data/g24_global_teaser.js").read_text(encoding="utf-8")
    t = json.loads(text[len("window.G24_GLOBAL_TEASER = "):].rstrip().rstrip(";"))
    s = pd.read_csv(T / "global_summary.csv").set_index("short")
    for lab, v in t["top10"].items():
        assert abs(v - s.at[lab, "top10_pct"]) < 1e-9
    assert t["countries"] == len(pd.read_csv(T / "global_country_relations.csv"))


def test_citation_flows_use_the_same_window():
    """D-40: both directions count only partner papers from the dataset's years (2016-2026)."""
    from src.stats.global_benchmark import _flow_years
    y0, y1 = _flow_years()
    fl = pd.read_csv(G / "citation_flows.csv", dtype={"institution_id": str})
    fl = fl[(fl["coauthored_with_lab"].astype(str).str.upper() != "TRUE") & fl["year"].between(y0, y1)]
    lk = pd.read_csv(T / "global_links.csv", dtype={"institution_id": str})
    for _, r in lk.iterrows():
        g = fl[(fl["lab"] == r["lab"]) & (fl["institution_id"] == r["institution_id"])]
        assert g[g["direction"] == "peer_cites_lab"]["work_id"].nunique() == r["peer_papers_citing_lab"]
        assert g[g["direction"] == "lab_cites_peer"]["work_id"].nunique() == r["peer_papers_cited_by_lab"]


def test_world_baseline_is_measured():
    w = pd.read_csv(T / "global_world_baseline.csv")
    c = pd.read_csv(G / "country_by_year.csv")
    world = c[c["country_code"] == "WORLD"]
    assert abs(w["top10_pct"].iloc[0] - 100 * world["top10"].sum() / world["papers_scope"].sum()) < 0.01
    assert 9.5 < w["top10_pct"].iloc[0] < 12.5 and 0.9 < w["top1_pct"].iloc[0] < 1.3
