"""Automated tests for final dataset schema, constraints, and integrity."""

from pathlib import Path
import re
import pandas as pd
import pytest

MAIN_COLUMNS = [
    "group",
    "institution",
    "author",
    "title",
    "year",
    "type",
    "journal_name",
    "issn",
    "doi",
    "citations",
    "quartile",
    "coauthor_institutes",
    "cites_indian_inst",
    "cited_by_indian_inst",
]

ALLOWED_INSTS = {"CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"}
ALLOWED_QUARTILES = {"Q1", "Q2", "Q3", "Q4", "CORE A*", "CORE A", "CORE B", "CORE C", ""}


@pytest.fixture(scope="session")
def primary_df():
    csv_path = Path("data/final/group24_data.csv")
    assert csv_path.exists(), "data/final/group24_data.csv missing"
    # BOM-free check
    with open(csv_path, "rb") as f:
        assert not f.read(4).startswith(b"\xef\xbb\xbf"), "BOM found in UTF-8 file"
    return pd.read_csv(csv_path, dtype=str, keep_default_na=False)


def test_schema_and_columns(primary_df):
    assert list(primary_df.columns) == MAIN_COLUMNS
    assert len(primary_df) > 40000


def test_domain_constraints(primary_df):
    # Group is 24
    assert set(primary_df["group"].unique()) == {"24"}

    # Institutions
    assert set(primary_df["institution"].unique()) == ALLOWED_INSTS

    # Years
    years = [int(y) for y in primary_df["year"]]
    assert min(years) == 2016
    assert max(years) == 2026

    # Publication type
    assert set(primary_df["type"].unique()).issubset({"journal", "conference"})

    # Citations
    citations = [int(c) for c in primary_df["citations"]]
    assert min(citations) >= 0

    # Quartiles
    assert set(primary_df["quartile"].unique()).issubset(ALLOWED_QUARTILES)

    # Booleans
    assert set(primary_df["cites_indian_inst"].unique()).issubset({"TRUE", "FALSE"})
    assert set(primary_df["cited_by_indian_inst"].unique()).issubset({"TRUE", "FALSE"})


def test_issn_and_doi_rules(primary_df):
    issn_regex = re.compile(r"^\d{4}-\d{3}[\dX]$")
    doi_regex = re.compile(r"^https://doi\.org/10\..+")

    # Conference papers must not have ISSN
    conf_rows = primary_df[primary_df["type"] == "conference"]
    assert (conf_rows["issn"] == "").all()

    # Journals with ISSN must follow NNNN-NNNC
    journal_issns = primary_df[(primary_df["type"] == "journal") & (primary_df["issn"] != "")]["issn"]
    for issn in journal_issns.sample(n=min(500, len(journal_issns)), random_state=42):
        assert issn_regex.match(issn)

    # Valid DOIs
    dois = primary_df[primary_df["doi"] != ""]["doi"]
    for doi in dois.sample(n=min(500, len(dois)), random_state=42):
        assert doi_regex.match(doi)


def test_network_deliverables():
    # 1. citation_network.csv
    cite_path = Path("data/final/citation_network.csv")
    assert cite_path.exists(), "data/final/citation_network.csv missing"
    df_cite = pd.read_csv(cite_path, dtype=str, keep_default_na=False)
    assert list(df_cite.columns) == ["source_doi", "target_doi", "source_inst", "target_inst", "year"]
    assert len(df_cite) > 20000

    # 2. authorship_network.csv
    auth_path = Path("data/final/authorship_network.csv")
    assert auth_path.exists(), "data/final/authorship_network.csv missing"
    df_auth = pd.read_csv(auth_path, dtype=str, keep_default_na=False)
    assert list(df_auth.columns) == ["author_a", "author_b", "paper_doi", "inst_a", "inst_b", "year"]
    assert len(df_auth) > 50000

    # 3. indian_connections.csv
    conn_path = Path("data/final/indian_connections.csv")
    assert conn_path.exists(), "data/final/indian_connections.csv missing"
    df_conn = pd.read_csv(conn_path, dtype=str, keep_default_na=False)
    assert list(df_conn.columns) == ["your_inst", "partner_inst", "shared_papers", "total_citations"]
    assert len(df_conn) > 1000
    assert set(df_conn["your_inst"].unique()) == ALLOWED_INSTS
