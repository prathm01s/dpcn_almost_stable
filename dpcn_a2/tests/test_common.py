import pytest
from src.common.names import clean_name, tokenize_name, match_names
from src.common.issn import is_valid_issn, normalize_issn, to_sjr_issn
from src.common.cache import clean_url, get_cache_key


def test_clean_name():
    assert clean_name("Dr. A. K. Suresh") == "A K Suresh"
    assert clean_name("Prof. Sivaram, S.") == "Sivaram S"
    assert clean_name("Shri C. N. R. Rao") == "C N R Rao"


def test_name_matching():
    # Exact match after title removal
    score, init_match = match_names("Dr. S. Sivaram", "S. Sivaram")
    assert score >= 95
    assert init_match

    # Inverted tokens
    score, init_match = match_names("Sivaram Swaminathan", "Swaminathan Sivaram")
    assert score >= 95
    assert init_match

    # Initial vs full name
    score, init_match = match_names("S. Sivaram", "Swaminathan Sivaram")
    assert score >= 85
    assert init_match


def test_issn_formatting():
    assert is_valid_issn("0002-7863")
    assert is_valid_issn("00027863")
    assert is_valid_issn("1520-512X")
    assert normalize_issn("00027863") == "0002-7863"
    assert normalize_issn("1520512x") == "1520-512X"
    assert to_sjr_issn("0002-7863") == "00027863"
    assert to_sjr_issn("1520-512X") == "1520512X"


def test_clean_url():
    url1 = "https://api.openalex.org/works?api_key=secret123&filter=publication_year:2020"
    assert "secret123" not in clean_url(url1)
    assert clean_url(url1) == "https://api.openalex.org/works?filter=publication_year:2020"

    url2 = "https://api.openalex.org/works?filter=publication_year:2020&api_key=secret123"
    assert "secret123" not in clean_url(url2)
    assert clean_url(url2) == "https://api.openalex.org/works?filter=publication_year:2020"
