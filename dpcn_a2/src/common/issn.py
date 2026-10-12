"""ISSN formatting and normalization utilities."""

import re
from typing import Optional

ISSN_REGEX = re.compile(r"^\d{4}-?\d{3}[\dX]$", re.IGNORECASE)


def is_valid_issn(issn: str) -> bool:
    """Check if string is a valid 8-character ISSN pattern."""
    if not issn:
        return False
    clean = issn.strip().replace(" ", "")
    return bool(ISSN_REGEX.match(clean))


def normalize_issn(issn: Optional[str]) -> Optional[str]:
    """Convert to standard hyphenated uppercase format NNNN-NNNC."""
    if not issn or not isinstance(issn, str):
        return None
    clean = issn.strip().upper().replace(" ", "").replace("-", "")
    if len(clean) == 8 and clean[:7].isdigit() and (clean[7].isdigit() or clean[7] == "X"):
        return f"{clean[:4]}-{clean[4:]}"
    return None


def to_sjr_issn(issn: str) -> Optional[str]:
    """Convert to 8-character hyphenless uppercase format used by SCImago."""
    norm = normalize_issn(issn)
    if norm:
        return norm.replace("-", "")
    return None
