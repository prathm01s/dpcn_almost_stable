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
