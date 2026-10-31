"""Scientist profiles (dashboard/data/g24_profiles.js) agree with the faculty tables."""

import json
from pathlib import Path

import pandas as pd


def load_profiles():
    s = Path("dashboard/data/g24_profiles.js").read_text(encoding="utf-8")
    return json.loads(s[s.index("{"): s.rstrip().rstrip(";").rindex("}") + 1])


def test_every_roster_scientist_has_a_profile():
    profiles = load_profiles()
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    assert set(fm["faculty_id"]) == set(profiles)


def test_profile_numbers_match_faculty_performance():
    profiles = load_profiles()
    perf = pd.read_csv("stats/tables/faculty_performance.csv", keep_default_na=False).set_index("faculty_id")
    for fid, p in profiles.items():
        assert p["papers"] == int(perf.loc[fid, "papers"]), fid
        assert p["citations"] == int(perf.loc[fid, "citations"]), fid
        if p["papers"]:
            assert sum(y["papers"] for y in p["by_year"]) == p["papers"], fid
            assert sum(y["citations"] for y in p["by_year"]) == p["citations"], fid


def test_collaborators_are_consistent():
    profiles = load_profiles()
    for fid, p in profiles.items():
        collabs = p.get("collaborators", [])
        assert all(c["joint_papers"] <= p["papers"] for c in collabs), fid
        assert all(c["openalex"] != p["openalex"] for c in collabs), fid
        joints = [c["joint_papers"] for c in collabs]
        assert joints == sorted(joints, reverse=True), fid
        n = len(collabs)
        assert all(0 <= a < b < n for a, b, _ in p.get("collab_links", [])), fid
        for c in collabs:
            if c["faculty_id"]:
                assert c["faculty_id"] in profiles
