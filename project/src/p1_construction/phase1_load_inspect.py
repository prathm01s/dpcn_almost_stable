"""
Phase 1 — Load & Inspect Raw Data
==================================
1. Load CSV with encoding='utf-8-sig'
2. Confirm shape (96 × 61) and print dtypes
3. Parse column headers into question_id, block, question_text → question_map.csv
4. Data quality report → data_quality_summary.csv
5. Plots: missing per question (colored by block); missing per respondent histogram
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for saving figures
import seaborn as sns

from utils import (
    RAW_CSV, PROCESSED_DATA_DIR, TABLES_DIR, FIGURES_DIR,
    BLOCK_LABELS, BLOCK_ORDER, BLOCK_COLORS, MISSING_VALUES,
    apply_plot_style, ensure_dirs, parse_question_id, save_figure
)

# ──────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────
ensure_dirs()
apply_plot_style()

print("=" * 70)
print("PHASE 1 — Load & Inspect Raw Data")
print("=" * 70)

# ──────────────────────────────────────────────────────────────
# Step 1: Load CSV
# ──────────────────────────────────────────────────────────────
print("\n[Step 1] Loading raw data...")
df = pd.read_csv(RAW_CSV, encoding="utf-8-sig")
print(f"  File: {RAW_CSV}")
print(f"  Shape: {df.shape}")

# ──────────────────────────────────────────────────────────────
# Step 2: Confirm shape and dtypes
# ──────────────────────────────────────────────────────────────
print(f"\n[Step 2] Shape confirmation...")
n_rows, n_cols = df.shape
print(f"  Rows (respondents): {n_rows}")
print(f"  Columns: {n_cols}")
assert n_rows == 96, f"Expected 96 rows, got {n_rows}"
assert n_cols == 61, f"Expected 61 columns, got {n_cols}"
print("  ✓ Shape confirmed: 96 × 61")

print(f"\n  Dtypes:")
for dtype, count in df.dtypes.value_counts().items():
    print(f"    {dtype}: {count} columns")

# Clean column name for the ID column (strip whitespace)
df.columns = [col.strip() for col in df.columns]
id_col = df.columns[0]  # 'id. Response ID'
print(f"\n  ID column: '{id_col}'")
print(f"  ID range: {df[id_col].min()} – {df[id_col].max()}")
print(f"  Unique IDs: {df[id_col].nunique()}")

# Rename ID column for easier access
df = df.rename(columns={id_col: "ResponseID"})

# ──────────────────────────────────────────────────────────────
# Step 3: Parse column headers → question_map.csv
# ──────────────────────────────────────────────────────────────
print(f"\n[Step 3] Parsing question headers...")
question_columns = df.columns[1:]  # All except ResponseID

question_map_rows = []
for col in question_columns:
    parsed = parse_question_id(col)
    if parsed is None:
        print(f"  ⚠ Could not parse column: '{col}'")
        continue
    parsed["original_column"] = col
    question_map_rows.append(parsed)

question_map = pd.DataFrame(question_map_rows)
print(f"  Parsed {len(question_map)} question columns")
print(f"\n  Questions per block:")
for block in BLOCK_ORDER:
    block_qs = question_map[question_map["block"] == block]
    print(f"    {block} ({BLOCK_LABELS[block]}): {len(block_qs)} questions "
          f"({block_qs['question_id'].iloc[0]} – {block_qs['question_id'].iloc[-1]})")

# Save question map
qmap_path = os.path.join(PROCESSED_DATA_DIR, "question_map.csv")
question_map.to_csv(qmap_path, index=False)
print(f"\n  → Saved: {qmap_path}")

# ──────────────────────────────────────────────────────────────
# Step 4: Data quality report
# ──────────────────────────────────────────────────────────────
print(f"\n[Step 4] Data quality analysis...")

# Create a boolean mask for missing values: NaN (blank cells) and "No Comments"
question_data = df[question_columns].copy()

# Build missing mask: True where cell is NaN OR equals "No Comments" (stripped)
missing_mask = question_data.isna() | question_data.apply(
    lambda col: col.astype(str).str.strip().eq("No Comments")
)

# Count NaN vs "No Comments" separately for reporting
nan_count = int(question_data.isna().sum().sum())
no_comments_count = int(question_data.apply(
    lambda col: col.astype(str).str.strip().eq("No Comments")
).sum().sum())

# ── Total missing cells ──
total_cells = missing_mask.size
total_missing = int(missing_mask.sum().sum())
print(f"\n  Total cells: {total_cells}")
print(f"  Total missing: {total_missing} ({100*total_missing/total_cells:.1f}%)")
print(f"    - Blank/NaN cells: {nan_count}")
print(f"    - 'No Comments' cells: {no_comments_count}")

# ── Missing per respondent ──
missing_per_respondent = missing_mask.sum(axis=1)
df["missing_count"] = missing_per_respondent.values
df["missing_pct"] = (missing_per_respondent.values / 60 * 100).round(1)
df["flagged_gt_50pct"] = df["missing_pct"] > 50

print(f"\n  Missing per respondent:")
print(f"    Min: {missing_per_respondent.min()}")
print(f"    Max: {missing_per_respondent.max()}")
print(f"    Mean: {missing_per_respondent.mean():.1f}")
print(f"    Median: {missing_per_respondent.median()}")

flagged = df[df["flagged_gt_50pct"]]
print(f"\n  Respondents with >50% missing ({len(flagged)} total):")
for _, row in flagged.iterrows():
    print(f"    ID {int(row['ResponseID'])}: {int(row['missing_count'])}/60 missing ({row['missing_pct']}%)")

# ── Missing per question ──
missing_per_question = missing_mask.sum(axis=0)
question_missing = pd.DataFrame({
    "question_id": [parse_question_id(col)["question_id"] for col in question_columns],
    "block": [parse_question_id(col)["block"] for col in question_columns],
    "missing_count": missing_per_question.values,
    "missing_pct": (missing_per_question.values / n_rows * 100).round(1),
})

print(f"\n  Missing per question:")
print(f"    Min: {question_missing['missing_count'].min()} (question {question_missing.loc[question_missing['missing_count'].idxmin(), 'question_id']})")
print(f"    Max: {question_missing['missing_count'].max()} (question {question_missing.loc[question_missing['missing_count'].idxmax(), 'question_id']})")
print(f"\n  Missing per block (mean):")
for block in BLOCK_ORDER:
    block_mean = question_missing[question_missing["block"] == block]["missing_count"].mean()
    print(f"    {block}: {block_mean:.1f}")

# ── Build and save the comprehensive data quality summary ──
# Part A: respondent-level summary
respondent_quality = df[["ResponseID", "missing_count", "missing_pct", "flagged_gt_50pct"]].copy()
respondent_quality.to_csv(os.path.join(TABLES_DIR, "respondent_missing_summary.csv"), index=False)

# Part B: question-level summary
question_missing.to_csv(os.path.join(TABLES_DIR, "question_missing_summary.csv"), index=False)

# Part C: aggregate summary
summary_stats = {
    "metric": [
        "total_respondents",
        "total_questions",
        "total_cells",
        "total_missing_cells",
        "total_missing_pct",
        "respondents_with_zero_missing",
        "respondents_flagged_gt_50pct_missing",
        "respondents_fully_blank",
        "missing_type_blank_nan",
        "missing_type_no_comments",
    ],
    "value": [
        n_rows,
        len(question_columns),
        total_cells,
        total_missing,
        round(100 * total_missing / total_cells, 2),
        int((missing_per_respondent == 0).sum()),
        int(len(flagged)),
        int((missing_per_respondent == 60).sum()),
        nan_count,
        no_comments_count,
    ],
}
summary_df = pd.DataFrame(summary_stats)
summary_path = os.path.join(TABLES_DIR, "data_quality_summary.csv")
summary_df.to_csv(summary_path, index=False)
print(f"\n  → Saved: {summary_path}")

# ──────────────────────────────────────────────────────────────
# Step 5: Plots
# ──────────────────────────────────────────────────────────────
print(f"\n[Step 5] Generating plots...")

# ── Plot 1: Missing count per question, colored by block ──
fig, ax = plt.subplots(figsize=(16, 6))

# Sort by missing count descending
q_sorted = question_missing.sort_values("missing_count", ascending=False).reset_index(drop=True)
colors = [BLOCK_COLORS[b] for b in q_sorted["block"]]

bars = ax.bar(range(len(q_sorted)), q_sorted["missing_count"], color=colors, edgecolor="white", linewidth=0.5)
ax.set_xlabel("Question")
ax.set_ylabel("Missing Count")
ax.set_title("Missing Values per Question (sorted descending, colored by block)")
ax.set_xticks(range(len(q_sorted)))
ax.set_xticklabels(q_sorted["question_id"], rotation=90, fontsize=8)

# Legend for blocks
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=BLOCK_COLORS[b], label=f"{b}: {BLOCK_LABELS[b]}") 
                   for b in BLOCK_ORDER]
ax.legend(handles=legend_elements, loc="upper right", title="Block")

ax.axhline(y=missing_per_question.mean(), color="gray", linestyle="--", alpha=0.7, 
           label=f"Mean = {missing_per_question.mean():.1f}")

plt.tight_layout()
save_figure(fig, "phase1_missing_per_question.png")
plt.close(fig)

# ── Plot 2: Histogram of missing count per respondent ──
fig, ax = plt.subplots(figsize=(10, 6))

# Custom bins to show the distribution clearly
bins = [-0.5, 0.5, 5.5, 10.5, 15.5, 20.5, 30.5, 45.5, 60.5]
counts, edges, patches = ax.hist(missing_per_respondent, bins=bins, 
                                  color="#4C72B0", edgecolor="white", linewidth=1)

# Annotate each bar with count
for count_val, patch in zip(counts, patches):
    if count_val > 0:
        ax.annotate(f"{int(count_val)}", 
                    xy=(patch.get_x() + patch.get_width() / 2, count_val),
                    ha="center", va="bottom", fontsize=11, fontweight="bold")

ax.set_xlabel("Number of Missing Values (out of 60)")
ax.set_ylabel("Number of Respondents")
ax.set_title("Distribution of Missing Values per Respondent")

# Add a text box with key stats
textstr = (f"Total respondents: {n_rows}\n"
           f"Zero missing: {int((missing_per_respondent == 0).sum())}\n"
           f"Fully blank: {int((missing_per_respondent == 60).sum())}\n"
           f"Flagged (>50%): {len(flagged)}")
props = dict(boxstyle="round", facecolor="wheat", alpha=0.8)
ax.text(0.72, 0.95, textstr, transform=ax.transAxes, fontsize=10,
        verticalalignment="top", bbox=props)

plt.tight_layout()
save_figure(fig, "phase1_missing_per_respondent.png")
plt.close(fig)

# ──────────────────────────────────────────────────────────────
# Step 6: Print unique response values for verification
# ──────────────────────────────────────────────────────────────
print(f"\n[Step 6] Response value distribution (across all question cells):")
all_values = question_data.values.flatten()
value_counts = pd.Series(all_values).value_counts(dropna=False)
for val, cnt in value_counts.items():
    if pd.isna(val):
        print(f"    <NaN/blank>: {cnt}")
    elif str(val).strip() == "No Comments":
        print(f"    No Comments: {cnt}")
    else:
        print(f"    {val}: {cnt}")

# ──────────────────────────────────────────────────────────────
# Final summary
# ──────────────────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print("PHASE 1 COMPLETE")
print(f"{'=' * 70}")
print(f"\n  Outputs saved:")
print(f"    data/processed/question_map.csv")
print(f"    outputs/tables/data_quality_summary.csv")
print(f"    outputs/tables/respondent_missing_summary.csv")
print(f"    outputs/tables/question_missing_summary.csv")
print(f"    outputs/figures/phase1_missing_per_question.png")
print(f"    outputs/figures/phase1_missing_per_respondent.png")
print(f"\n  Key findings:")
print(f"    • {n_rows} respondents, {len(question_columns)} questions (4 blocks × 15)")
print(f"    • {total_missing} missing cells total ({100*total_missing/total_cells:.1f}%)")
print(f"    • {int((missing_per_respondent == 0).sum())} respondents have zero missing values")
print(f"    • {int((missing_per_respondent == 60).sum())} respondents are fully blank (all 60 answers missing)")
print(f"    • {len(flagged)} respondents flagged with >50% missing")
print(f"    • Responses are heavily right-skewed: most answers are Agree/Strongly Agree")
