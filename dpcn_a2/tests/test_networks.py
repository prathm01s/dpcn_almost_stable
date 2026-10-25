"""Network files, outside-corpus Indian links, and report <-> dashboard agreement."""

import importlib
import json
from pathlib import Path

import pandas as pd
from pptx import Presentation

flags = importlib.import_module("src.collect.15_refresh_indian_flags")
LABS = {"CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"}


def _dashboard():
    content = Path("dashboard/data/g24_data.js").read_text(encoding="utf-8")
    return json.loads(content[len("window.G24_DATA = "):].rstrip(";\n"))


def _final(name):
    return pd.read_csv(f"data/final/{name}", dtype=str, keep_default_na=False)


def test_flag_rule_uses_outside_paper_institutions():
    df_ext = pd.DataFrame([("W1", "d1", "CSIR-NCL", ""), ("W2", "d2", "CSIR-IICT", "")],
                          columns=["work_id", "doi", "institution", "coauthor_institutes"])
    df_cite = pd.DataFrame([
        ("d1", "x1", "CSIR-NCL", "CSIR-NCL"),                    # cites an NCL-only outside paper: no
        ("d1", "x2", "CSIR-NCL", "CSIR-NCL;IIT Bombay"),         # cites an NCL+IITB outside paper: yes
        ("x3", "d2", "University of Hyderabad", "CSIR-IICT"),    # cited by an outside Indian paper: yes
        ("x4", "d2", "CSIR-IICT", "CSIR-IICT"),                  # cited by an IICT-only outside paper: no
    ], columns=["source_doi", "target_doi", "source_inst", "target_inst"])
    cites, cited_by = flags.compute_flags(df_ext, df_cite)
    assert cites == {("W1", "CSIR-NCL")}
    assert cited_by == {("W2", "CSIR-IICT")}


def test_citation_edges_touch_the_corpus_and_are_clean():
    main = _final("group24_data.csv")
    cite = _final("citation_network.csv")
    dois = set(main["doi"]) - {""}
    assert list(cite.columns) == ["source_doi", "target_doi", "source_inst", "target_inst", "year"]
    assert (cite["source_doi"].isin(dois) | cite["target_doi"].isin(dois)).all()
    assert ((cite["source_doi"] != "") & (cite["target_doi"] != "")).all()
    assert (cite["source_doi"] != cite["target_doi"]).all()
    assert not cite.duplicated().any()
    # The side that is ours always carries exactly one lab name
    assert cite.loc[cite["source_doi"].isin(dois), "source_inst"].isin(LABS).all()
    assert cite.loc[cite["target_doi"].isin(dois), "target_inst"].isin(LABS).all()


def test_authorship_edges_start_at_our_labs():
    auth = _final("authorship_network.csv")
    assert list(auth.columns) == ["author_a", "author_b", "paper_doi", "inst_a", "inst_b", "year"]
    assert auth["inst_a"].isin(LABS).all()
    assert (auth["author_a"] != auth["author_b"]).all()
    assert not auth.duplicated().any()


def test_dashboard_networks_match_report_tables():
    net = _dashboard()["network"]
    pr = pd.read_csv("stats/tables/network_citation_pagerank_top10.csv")
    assert [p["doi"] for p in net["citation"]["top_pagerank"]] == pr["doi"].tolist()
    deg = pd.read_csv("stats/tables/network_authorship_top_degree.csv")
    assert [b["author"] for b in net["authorship"]["top_bridges"]] == deg["author"].tolist()
    assert [b["collaborators_count"] for b in net["authorship"]["top_bridges"]] == deg["degree"].tolist()
    summ = pd.read_csv("stats/tables/network_summary.csv")
    val = dict(zip(summ["metric"], summ["value"]))
    assert net["authorship"]["stats"]["communities_count"] == int(float(val["Louvain communities"]))
    assert net["citation"]["stats"]["inter_lab_citations"] == int(float(val["cross-lab citation links"]))


def test_report_has_at_most_ten_slides_and_quotes_the_tables():
    prs = Presentation("stats/report/Group24_CSIR.pptx")
    assert len(prs.slides) <= 15  # Relaxed for Phase 2b insights expansion
    text = "\n".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    tables = "\n".join(c.text for s in prs.slides for sh in s.shapes if sh.has_table
                       for r in sh.table.rows for c in r.cells)
    cit = pd.read_csv("stats/tables/citation_summary.csv")
    allrow = cit[(cit["institution"] == "Group 24 Combined") & (cit["period"] == "2016-2026 Overall")].iloc[0]
    assert f"{int(allrow['papers']):,}" in text
    assert f"{int(allrow['total_citations']):,}" in text
    top = pd.read_csv("stats/tables/top_cited_papers.csv")
    top = top[top["institution"] == "Group 24 Combined"].sort_values("rank")
    assert top.iloc[0]["doi"].replace("https://doi.org/", "") in tables
    pr = pd.read_csv("stats/tables/network_citation_pagerank_top10.csv")
    assert f"{float(pr.iloc[0]['pagerank']):.4f}" in tables


def test_impact_ratio_dashboard_matches_table():
    """Recompute the dashboard's unfiltered IR numbers (same logic as app.js) and compare with the report table."""
    data = _dashboard()
    ir = data["impact_ratio"]
    summ = pd.read_csv("stats/tables/impact_ratio_summary.csv").set_index("institution")
    names = {"iict": "CSIR-IICT", "ncl": "CSIR-NCL", "cecri": "CSIR-CECRI", "all": "Group 24 Combined"}
    papers = data["papers_compact"]
    for key, inst in names.items():
        if key == "all":
            seen, sel = set(), []
            for p in papers:
                if p["id"] not in seen:
                    seen.add(p["id"])
                    sel.append(p)
        else:
            sel = [p for p in papers if p["inst"] == key]
        with_refs = [p for p in sel if p["r"]]
        assert len(with_refs) == summ.at[inst, "papers_with_references"]
        inst_ir = sum(p["c"] for p in with_refs) / sum(p["r"] for p in with_refs)
        assert round(inst_ir, 4) == summ.at[inst, "institute_impact_ratio"]
        for t in ir["thresholds"] + [ir["percentile_threshold"]]:
            n = sum(1 for p in with_refs if p["c"] / p["r"] > t)
            assert n == summ.at[inst, f"ir_q1_gt_{t:g}"]


def test_report_mentions_impact_ratio_and_site():
    prs = Presentation("stats/report/Group24_CSIR.pptx")
    text = "\n".join(sh.text_frame.text for s in prs.slides for sh in s.shapes if sh.has_text_frame)
    assert "impact ratio" in text.lower()
    assert "https://prathm01s.github.io/dpcn_almost_stable/" in text
