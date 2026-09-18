"""
Shared utilities for the Opinion Network Formation project.
Provides common constants, file paths, color palettes, and helper functions
used across all three pipeline stages (P1, P2, P3).
"""

import os
import numpy as np

# ──────────────────────────────────────────────────────────────
# Global random seed — use this everywhere randomness appears
# ──────────────────────────────────────────────────────────────
SEED = 42

# ──────────────────────────────────────────────────────────────
# Project root & file paths
# ──────────────────────────────────────────────────────────────
# Resolve project root relative to this file's location
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, os.pardir, os.pardir))

# Data paths
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
RAW_CSV = os.path.join(RAW_DATA_DIR, "Survey_Results_UC.csv")

# Output paths
TABLES_DIR = os.path.join(PROJECT_ROOT, "outputs", "tables")
FIGURES_DIR = os.path.join(PROJECT_ROOT, "outputs", "figures")
GRAPHS_DIR = os.path.join(PROJECT_ROOT, "graphs")

# ──────────────────────────────────────────────────────────────
# Likert encoding map
# ──────────────────────────────────────────────────────────────
LIKERT_ENCODING = {
    "Strongly Disagree": -2,
    "Disagree": -1,
    "Neutral": 0,
    "Agree": 1,
    "Strongly Agree": 2,
}

# Values treated as missing
MISSING_VALUES = {"", "No Comments"}

# ──────────────────────────────────────────────────────────────
# Block definitions
# ──────────────────────────────────────────────────────────────
BLOCK_LABELS = {
    "T": "Technology",
    "E": "Education",
    "S": "Ethics/Society",
    "V": "Environment",
}

BLOCK_ORDER = ["T", "E", "S", "V"]

# ──────────────────────────────────────────────────────────────
# Color palette — consistent across all pipeline stages
# ──────────────────────────────────────────────────────────────
BLOCK_COLORS = {
    "T": "#4C72B0",   # Steel blue  – Technology
    "E": "#DD8452",   # Sandy orange – Education
    "S": "#55A868",   # Sage green   – Ethics/Society
    "V": "#C44E52",   # Muted red    – Environment
}

# Likert response colors (diverging: red → grey → blue)
LIKERT_COLORS = {
    "Strongly Disagree": "#d73027",
    "Disagree":          "#fc8d59",
    "Neutral":           "#cccccc",
    "Agree":             "#91bfdb",
    "Strongly Agree":    "#4575b4",
}

LIKERT_ORDER = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]

# ──────────────────────────────────────────────────────────────
# Plot style defaults
# ──────────────────────────────────────────────────────────────
PLOT_STYLE = {
    "figure.figsize": (12, 7),
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.family": "sans-serif",
}


def apply_plot_style():
    """Apply the project's global matplotlib style settings."""
    import matplotlib.pyplot as plt
    plt.rcParams.update(PLOT_STYLE)
    # Use a clean seaborn-compatible style
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("ggplot")


def ensure_dirs():
    """Create all output directories if they don't exist."""
    for d in [RAW_DATA_DIR, PROCESSED_DATA_DIR, TABLES_DIR, FIGURES_DIR, GRAPHS_DIR]:
        os.makedirs(d, exist_ok=True)


def set_global_seed():
    """Set random seeds for reproducibility."""
    np.random.seed(SEED)
    try:
        import random
        random.seed(SEED)
    except ImportError:
        pass


def parse_question_id(column_name: str) -> dict:
    """
    Parse a column header like 'T01. Artificial Intelligence will improve...'
    into its components.
    
    Returns:
        dict with keys: question_id, block, block_name, question_text
    """
    # Split on the first period+space
    parts = column_name.split(". ", 1)
    if len(parts) != 2:
        return None
    qid = parts[0].strip()
    qtext = parts[1].strip()
    block_letter = qid[0]
    block_name = BLOCK_LABELS.get(block_letter, "Unknown")
    return {
        "question_id": qid,
        "block": block_letter,
        "block_name": block_name,
        "question_text": qtext,
    }


def save_figure(fig, filename, tight=True):
    """Save a figure to the project figures directory."""
    ensure_dirs()
    path = os.path.join(FIGURES_DIR, filename)
    fig.savefig(path, bbox_inches="tight" if tight else None, dpi=150)
    print(f"  → Saved figure: {path}")
    return path
