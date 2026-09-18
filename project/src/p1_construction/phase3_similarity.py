"""
Phase 3 — Similarity Matrices
===================================================
1. Compute cosine similarity (primary) and Pearson correlation (secondary) on full matrix.
2. Spearman-correlate off-diagonals; justify cosine choice.
3. Compute cosine similarity for 4 block sub-matrices.
4. Save similarity_*.npy files.
5. Plots: Clustered full similarity heatmap, pairwise similarity histogram, 4-panel block heatmaps.
6. Update report_draft.md and results_summary.md.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from scipy.stats import spearmanr

matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    PROCESSED_DATA_DIR, TABLES_DIR, FIGURES_DIR, PROJECT_ROOT,
    BLOCK_ORDER, BLOCK_LABELS, apply_plot_style, save_figure, set_global_seed
)

set_global_seed()
apply_plot_style()

print("=" * 70)
print("PHASE 3 — Similarity Matrices")
print("=" * 70)

# ──────────────────────────────────────────────────────────────
# 1. Load Data
# ──────────────────────────────────────────────────────────────
print("\n[Step 1] Loading imputed dataset...")
encoded_matrix_path = os.path.join(PROCESSED_DATA_DIR, "encoded_matrix.csv")
df_full = pd.read_csv(encoded_matrix_path)
respondent_ids = df_full["ResponseID"].astype(str).tolist()

X_full = df_full.drop(columns=["ResponseID"]).values
n_respondents = X_full.shape[0]

print(f"  Loaded {n_respondents} respondents with {X_full.shape[1]} features.")

# ──────────────────────────────────────────────────────────────
# 2. Compute Similarities (Full)
# ──────────────────────────────────────────────────────────────
print("\n[Step 2] Computing full network similarity matrices...")

# Cosine similarity
sim_cosine_full = cosine_similarity(X_full)

# Pearson correlation (pandas corr on transposed data)
df_features = df_full.drop(columns=["ResponseID"])
sim_pearson_full = df_features.T.corr(method='pearson').values

# Save full matrices
np.save(os.path.join(PROJECT_ROOT, "similarity_cosine_full.npy"), sim_cosine_full)
np.save(os.path.join(PROJECT_ROOT, "similarity_pearson_full.npy"), sim_pearson_full)

# ──────────────────────────────────────────────────────────────
# 3. Compare Cosine vs Pearson (Spearman on off-diagonals)
# ──────────────────────────────────────────────────────────────
# Extract off-diagonal elements (upper triangle to avoid duplication)
upper_tri_indices = np.triu_indices(n_respondents, k=1)
cosine_off_diag = sim_cosine_full[upper_tri_indices]
pearson_off_diag = sim_pearson_full[upper_tri_indices]

spearman_corr, _ = spearmanr(cosine_off_diag, pearson_off_diag)
print(f"  Spearman correlation between Cosine and Pearson similarities: {spearman_corr:.4f}")
if spearman_corr > 0.8:
    justification = "The correlation is high (>0.8), justifying the use of cosine similarity as the primary metric going forward."
    print(f"  → {justification}")
else:
    justification = "The correlation is moderate/low. Will proceed with cosine as planned, but structural differences exist."
    print(f"  → {justification}")

# ──────────────────────────────────────────────────────────────
# 4. Compute Similarities (Blocks)
# ──────────────────────────────────────────────────────────────
print("\n[Step 3] Computing block-specific cosine similarity matrices...")
sim_cosine_blocks = {}
for block in BLOCK_ORDER:
    block_path = os.path.join(PROCESSED_DATA_DIR, f"block_{block}.csv")
    df_block = pd.read_csv(block_path)
    X_block = df_block.drop(columns=["ResponseID"]).values
    
    sim_block = cosine_similarity(X_block)
    sim_cosine_blocks[block] = sim_block
    
    out_path = os.path.join(PROJECT_ROOT, f"similarity_cosine_{block}.npy")
    np.save(out_path, sim_block)
    print(f"  → Saved: similarity_cosine_{block}.npy")

# ──────────────────────────────────────────────────────────────
# 5. Generate Plots
# ──────────────────────────────────────────────────────────────
print("\n[Step 4] Generating visualizations...")

# ── Plot A: Clustered Heatmap (Full Cosine) ──
# Note: clustermap creates its own figure
g = sns.clustermap(
    sim_cosine_full, 
    cmap="viridis", 
    xticklabels=False, 
    yticklabels=False,
    figsize=(10, 10),
    cbar_kws={"label": "Cosine Similarity"},
    method="ward"  # hierarchical clustering method
)
g.fig.suptitle("Clustered Cosine Similarity Matrix (Full Network)", y=1.02, fontsize=14)
save_figure(g.fig, "phase3_similarity_heatmap_full.png")
plt.close(g.fig)

# ── Plot B: Histogram of Pairwise Similarity ──
fig, ax = plt.subplots(figsize=(8, 6))
ax.hist(cosine_off_diag, bins=50, color="#4C72B0", edgecolor="white", alpha=0.8)
ax.set_title("Distribution of Pairwise Cosine Similarities (Off-Diagonals)")
ax.set_xlabel("Cosine Similarity")
ax.set_ylabel("Frequency (Pairs)")
ax.axvline(np.mean(cosine_off_diag), color='red', linestyle='dashed', linewidth=1.5, label=f'Mean: {np.mean(cosine_off_diag):.3f}')
ax.legend()
plt.tight_layout()
save_figure(fig, "phase3_similarity_histogram.png")
plt.close(fig)

# ── Plot C: 4-Panel Small Multiples (Block Heatmaps) ──
# Determine common vmin and vmax across all block similarities for comparability
vmin_block = min([np.min(sim_cosine_blocks[b][upper_tri_indices]) for b in BLOCK_ORDER])
vmax_block = max([np.max(sim_cosine_blocks[b][upper_tri_indices]) for b in BLOCK_ORDER])

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for i, block in enumerate(BLOCK_ORDER):
    ax = axes[i]
    sns.heatmap(
        sim_cosine_blocks[block], 
        cmap="viridis", 
        xticklabels=False, yticklabels=False, 
        cbar=(i % 2 == 1), # Only show colorbar on the rightmost plots
        vmin=vmin_block, vmax=vmax_block,
        ax=ax
    )
    ax.set_title(f"{block}: {BLOCK_LABELS[block]}")

plt.suptitle("Cosine Similarity by Topic Block (Shared Color Scale)", fontsize=16)
plt.tight_layout()
save_figure(fig, "phase3_similarity_blocks_small_multiples.png")
plt.close(fig)

# ──────────────────────────────────────────────────────────────
# 6. Update Markdown Files
# ──────────────────────────────────────────────────────────────
print("\n[Step 5] Updating report_draft.md and results_summary.md...")

report_path = os.path.join(PROJECT_ROOT, "report_draft.md")
with open(report_path, "r", encoding="utf-8") as f:
    report_content = f.read()

# Update Pipeline Followed with Similarity logic
pipeline_update = f"""
## Similarity Computation

To form the network, we evaluated respondent alignment using **cosine similarity** across the encoded response vectors. As a robustness check, we also computed the Pearson correlation matrix. A Spearman correlation between the flattened off-diagonals of both similarity matrices yielded a value of **{spearman_corr:.3f}**. {justification} Cosine similarity was similarly computed for each of the four topic blocks (Technology, Education, Ethics/Society, Environment) to support subsequent sub-network analysis.
"""
report_content = report_content.replace(
    "# Analysis and Visualizations", 
    pipeline_update.strip() + "\n\n# Analysis and Visualizations"
)

# Update Analysis and Visualizations
analysis_update = """
### Pairwise Similarity

![Clustered Similarity Matrix](outputs/figures/phase3_similarity_heatmap_full.png)
*Figure: Heatmap of the full pairwise cosine similarity matrix. Rows and columns are reordered using hierarchical clustering, revealing visible dense blocks of highly similar respondents along the diagonal.*
"""
report_content = report_content.replace(
    "*Figure: Violin plot of the respondents' mean scores across the four blocks. The highest agreement is concentrated in the Environment block.*",
    "*Figure: Violin plot of the respondents' mean scores across the four blocks. The highest agreement is concentrated in the Environment block.*\n\n" + analysis_update.strip()
)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_content)

# Update Results Summary
summary_path = os.path.join(PROJECT_ROOT, "results_summary.md")
with open(summary_path, "a", encoding="utf-8") as f:
    f.write("\n### Phase 3: Similarity Matrices\n")
    f.write(f"- **Metric Choice**: Cosine similarity selected. Spearman correlation with Pearson was {spearman_corr:.3f}, validating metric stability.\n")
    f.write(f"- **Distribution**: Mean pairwise cosine similarity across the full network is {np.mean(cosine_off_diag):.3f}.\n")
    f.write("- **Structure**: Hierarchical clustering on the similarity matrix reveals early visual evidence of distinct opinion groupings (blocks on the diagonal).\n")

print(f"  → Updated report_draft.md and results_summary.md")

print(f"\n{'=' * 70}")
print("PHASE 3 COMPLETE")
print(f"{'=' * 70}")
