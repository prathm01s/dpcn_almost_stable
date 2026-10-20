import importlib

import pandas as pd
import pytest

from src.common.sectors import assign_sector_cluster

flags = importlib.import_module("src.collect.15_refresh_indian_flags")


@pytest.mark.parametrize("name, expected", [
    ("Indian Institute of Technology Bombay", "IIT"),
    ("Indian Institute of Information Technology Allahabad", "IIIT"),
    ("Indian Institute of Science Education and Research Pune", "IISER"),
    ("Indian Institute of Science Bangalore", "IISc"),
    ("Academy of Scientific and Innovative Research", "CSIR"),
    ("Centre for Cellular and Molecular Biology", "CSIR"),
    ("Bhabha Atomic Research Centre", "DAE"),
    ("University of Hyderabad", "CentralUniv"),
    ("Savitribai Phule Pune University", "StateUniv"),  # "NIV" inside UNIVERSITY must not match ICMR
    ("Osmania University", "StateUniv"),
    ("ICMR-National Institute of Virology", "ICMR"),
    ("SRM Institute of Science and Technology", "Private"),
])
def test_sector_classification(name, expected):
    assert assign_sector_cluster(name) == expected


def _ext(rows):
    return pd.DataFrame(rows, columns=["work_id", "doi", "institution", "coauthor_institutes"])


def test_flag_rule_counts_other_labs_and_coauthor_institutes():
    df_ext = _ext([
        ("W1", "d1", "CSIR-NCL", ""),                    # NCL-only paper
        ("W2", "d2", "CSIR-NCL", "Osmania University"),  # NCL paper with an Indian partner
        ("W3", "d3", "CSIR-IICT", ""),                   # IICT-only paper
    ])
    df_cite = pd.DataFrame([
        ("d1", "d2", "CSIR-NCL", "CSIR-NCL"),   # NCL cites NCL+Osmania -> counts
        ("d3", "d1", "CSIR-IICT", "CSIR-NCL"),  # IICT cites NCL -> counts both ways
    ], columns=["source_doi", "target_doi", "source_inst", "target_inst"])

    cites, cited_by = flags.compute_flags(df_ext, df_cite)
    assert cites == {("W1", "CSIR-NCL"), ("W3", "CSIR-IICT")}
    assert cited_by == {("W1", "CSIR-NCL")}  # W2 is cited only by an NCL-only paper


def test_pure_self_citation_does_not_count():
    df_ext = _ext([("W1", "d1", "CSIR-NCL", ""), ("W2", "d2", "CSIR-NCL", "")])
    df_cite = pd.DataFrame([("d1", "d2", "CSIR-NCL", "CSIR-NCL")],
                           columns=["source_doi", "target_doi", "source_inst", "target_inst"])
    assert flags.compute_flags(df_ext, df_cite) == (set(), set())


def test_exported_flags_are_backed_by_citation_edges():
    """Every TRUE flag in the final dataset must come from an observed citation edge."""
    main = pd.read_csv("data/final/group24_data.csv", dtype=str, keep_default_na=False)
    cite = pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
    citing = set(zip(cite["source_doi"], cite["source_inst"]))
    cited = set(zip(cite["target_doi"], cite["target_inst"]))

    t_cites = main[main["cites_indian_inst"] == "TRUE"]
    t_cited = main[main["cited_by_indian_inst"] == "TRUE"]
    assert all(k in citing for k in zip(t_cites["doi"], t_cites["institution"]))
    assert all(k in cited for k in zip(t_cited["doi"], t_cited["institution"]))
