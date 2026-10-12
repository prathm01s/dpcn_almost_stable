"""Author and scientist name normalization and matching utilities."""

import re
from typing import List, Set, Tuple
from unidecode import unidecode
from rapidfuzz import fuzz

TITLE_REGEX = re.compile(
    r"\b(dr|prof|professor|shri|sri|smt|shrimati|mr|mrs|ms|padma\s+shri|padma\s+bhushan|fellow|frsc|fna|fasce?)\b[\.\s]*",
    re.IGNORECASE,
)


def clean_name(name: str) -> str:
    """Strip academic/honorific titles, normalize unicode, punctuation and spacing."""
    if not name:
        return ""
    # Decode unicode accents
    cleaned = unidecode(name)
    # Remove titles
    cleaned = TITLE_REGEX.sub(" ", cleaned)
    # Remove commas, dots, hyphens between words or initials
    cleaned = re.sub(r"[,\.]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def tokenize_name(name: str) -> List[str]:
    """Tokenize normalized name into lowercase tokens."""
    cleaned = clean_name(name).lower()
    tokens = [t for t in cleaned.split() if t]
    return tokens


def get_initials(tokens: List[str]) -> str:
    """Extract first letter of each token."""
    return "".join(t[0] for t in tokens if t)


def get_name_fingerprint(name: str) -> str:
    """Sorted tokens string for permutation-invariant comparison."""
    tokens = sorted(tokenize_name(name))
    return " ".join(tokens)


def match_names(name1: str, name2: str) -> Tuple[float, bool]:
    """Calculate match score (0-100) and whether initials are consistent.
    
    Handles typical Indian name inversions:
    - S. S. Patil vs Somnath S. Patil vs Patil, S.S.
    - Sivaram S vs Swaminathan Sivaram
    """
    toks1 = tokenize_name(name1)
    toks2 = tokenize_name(name2)
    if not toks1 or not toks2:
        return 0.0, False

    # Exact normalized match
    if " ".join(toks1) == " ".join(toks2):
        return 100.0, True

    # Sorted token match (ignoring order)
    if sorted(toks1) == sorted(toks2):
        return 98.0, True

    # Check for initials consistency
    # Single letter tokens are initials
    initials1 = {t for t in toks1 if len(t) == 1}
    initials2 = {t for t in toks2 if len(t) == 1}
    full_words1 = {t for t in toks1 if len(t) > 1}
    full_words2 = {t for t in toks2 if len(t) > 1}

    # If both have full words, intersection must be compatible
    if full_words1 and full_words2:
        overlap = full_words1.intersection(full_words2)
        if not overlap:
            # No shared full words
            return fuzz.token_set_ratio(" ".join(toks1), " ".join(toks2)), False

    # Token set ratio
    score = float(fuzz.token_set_ratio(" ".join(toks1), " ".join(toks2)))
    
    # Check if all initials of shorter set match prefixes of words in longer set
    all_initials_match = True
    inits_all1 = [t[0] for t in toks1]
    inits_all2 = [t[0] for t in toks2]
    if len(inits_all1) == len(inits_all2) and sorted(inits_all1) == sorted(inits_all2):
        all_initials_match = True
    else:
        # Check subset consistency
        set1 = set(inits_all1)
        set2 = set(inits_all2)
        all_initials_match = set1.issubset(set2) or set2.issubset(set1)

    return score, all_initials_match
