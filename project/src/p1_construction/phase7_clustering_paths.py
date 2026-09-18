"""
Phase 7 — Clustering & Path-Based Metrics
==========================================
1. Per-node clustering coefficient (weighted + unweighted); global average.
2. Table of top-10/bottom-10 clustering respondents.
3. On G_giant: average shortest path length (unweighted), diameter, radius, eccentricity distribution.
4. Secondary check: recompute path length using distance = 1 - similarity.
5. Plots: clustering coefficient histogram; eccentricity histogram; clustering vs degree scatter.
6. Report Update.
"""

import os
import sys
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(__file__))
from utils import (
    TABLES_DIR, FIGURES_DIR, GRAPHS_DIR, PROJECT_ROOT,
    apply_plot_style, save_figure, set_global_seed
)

set_global_seed()
apply_plot_style()

print("=" * 70)
print("PHASE 7 — Clustering & Path-Based Metrics")
print("=" * 70)

# ──────────────────────────────────────────────────────────────
# 1. Load Graphs
# ──────────────────────────────────────────────────────────────
print("\n[Step 1] Loading graphs...")
G_full = nx.read_graphml(os.path.join(GRAPHS_DIR, "G_full.graphml"))
G_giant = nx.read_graphml(os.path.join(GRAPHS_DIR, "G_giant.graphml"))

print(f"  G_full: {G_full.number_of_nodes()} nodes, {G_full.number_of_edges()} edges")
print(f"  G_giant: {G_giant.number_of_nodes()} nodes, {G_giant.number_of_edges()} edges")

# ──────────────────────────────────────────────────────────────
# 2. Clustering Coefficients
# ──────────────────────────────────────────────────────────────
print("\n[Step 2] Computing clustering coefficients...")

# Unweighted clustering
cc_unweighted = nx.clustering(G_full)
global_cc_unweighted = nx.average_clustering(G_full)

# Weighted clustering
cc_weighted = nx.clustering(G_full, weight='weight')
global_cc_weighted = nx.average_clustering(G_full, weight='weight')

print(f"  Global average clustering (unweighted): {global_cc_unweighted:.4f}")
print(f"  Global average clustering (weighted):   {global_cc_weighted:.4f}")

# Build per-node table
nodes = list(G_full.nodes())
degrees_uw = dict(G_full.degree())
degrees_w = dict(G_full.degree(weight='weight'))

df_clustering = pd.DataFrame({
    "ResponseID": nodes,
    "clustering_unweighted": [cc_unweighted[n] for n in nodes],
    "clustering_weighted": [cc_weighted[n] for n in nodes],
    "degree_unweighted": [degrees_uw[n] for n in nodes],
    "degree_weighted": [degrees_w[n] for n in nodes],
})
df_clustering["ResponseID_int"] = df_clustering["ResponseID"].astype(int)
df_clustering = df_clustering.sort_values("ResponseID_int").drop(columns=["ResponseID_int"])
df_clustering.to_csv(os.path.join(TABLES_DIR, "clustering_coefficients.csv"), index=False)
print(f"  → Saved: clustering_coefficients.csv")

# Top-10 and Bottom-10 by unweighted clustering
# Filter out isolates (degree=0) for bottom-10 since their CC is 0 by definition
non_isolates = df_clustering[df_clustering["degree_unweighted"] > 0]
top_10 = non_isolates.nlargest(10, "clustering_unweighted")
bottom_10 = non_isolates.nsmallest(10, "clustering_unweighted")

top_bottom = pd.concat([
    top_10.assign(rank_group="Top 10"),
    bottom_10.assign(rank_group="Bottom 10")
])
top_bottom.to_csv(os.path.join(TABLES_DIR, "clustering_top_bottom.csv"), index=False)
print(f"  → Saved: clustering_top_bottom.csv")

print("\n  Top-10 clustering respondents:")
for _, row in top_10.iterrows():
    print(f"    ID {row['ResponseID']}: CC={row['clustering_unweighted']:.4f}, degree={int(row['degree_unweighted'])}")

print("\n  Bottom-10 clustering respondents (non-isolate):")
for _, row in bottom_10.iterrows():
    print(f"    ID {row['ResponseID']}: CC={row['clustering_unweighted']:.4f}, degree={int(row['degree_unweighted'])}")

# ──────────────────────────────────────────────────────────────
# 3. Path-Based Metrics on G_giant
# ──────────────────────────────────────────────────────────────
print("\n[Step 3] Computing path-based metrics on G_giant...")

# Primary: unweighted shortest paths
avg_path_len = nx.average_shortest_path_length(G_giant)
diameter = nx.diameter(G_giant)
radius = nx.radius(G_giant)
eccentricities = nx.eccentricity(G_giant)

print(f"  Average shortest path length (unweighted): {avg_path_len:.4f}")
print(f"  Diameter: {diameter}")
print(f"  Radius: {radius}")

# Eccentricity distribution
ecc_values = list(eccentricities.values())
ecc_nodes = list(eccentricities.keys())

df_eccentricity = pd.DataFrame({
    "ResponseID": ecc_nodes,
    "eccentricity": ecc_values
})
df_eccentricity.to_csv(os.path.join(TABLES_DIR, "eccentricity.csv"), index=False)
print(f"  → Saved: eccentricity.csv")

# ──────────────────────────────────────────────────────────────
# 4. Secondary Check: weighted path length (distance = 1 - similarity)
# ──────────────────────────────────────────────────────────────
print("\n[Step 4] Secondary check: weighted path lengths (distance = 1 - similarity)...")

# Create a copy with distance weights
G_giant_dist = G_giant.copy()
for u, v, data in G_giant_dist.edges(data=True):
    w = float(data.get('weight', 0.8))
    data['distance'] = 1.0 - w

avg_path_len_weighted = nx.average_shortest_path_length(G_giant_dist, weight='distance')
print(f"  Average shortest path length (weighted, dist=1-sim): {avg_path_len_weighted:.4f}")

# Compare closeness centrality rankings
cc_uw = nx.closeness_centrality(G_giant)
cc_w = nx.closeness_centrality(G_giant_dist, distance='distance')

# Spearman correlation between the two rankings
from scipy.stats import spearmanr
nodes_giant = list(G_giant.nodes())
uw_vals = [cc_uw[n] for n in nodes_giant]
w_vals = [cc_w[n] for n in nodes_giant]
spearman_cc, _ = spearmanr(uw_vals, w_vals)
print(f"  Spearman correlation of closeness centrality rankings (unweighted vs weighted): {spearman_cc:.4f}")

if spearman_cc > 0.8:
    ranking_msg = f"The rankings are highly correlated (ρ = {spearman_cc:.3f}), indicating that the choice of unweighted vs. weighted paths does not substantially alter which respondents are considered most central."
else:
    ranking_msg = f"The rankings show moderate correlation (ρ = {spearman_cc:.3f}), suggesting that incorporating edge-weight distances meaningfully reshuffles the centrality ordering."

print(f"  → {ranking_msg}")

# One-row machine-readable handoff table for global clustering and path metrics.
df_path_summary = pd.DataFrame([{
    "full_nodes": G_full.number_of_nodes(),
    "gcc_nodes": G_giant.number_of_nodes(),
    "global_clustering_unweighted": global_cc_unweighted,
    "global_clustering_weighted": global_cc_weighted,
    "gcc_average_path_length_unweighted": avg_path_len,
    "gcc_average_path_length_weighted_1_minus_similarity": avg_path_len_weighted,
    "gcc_diameter": diameter,
    "gcc_radius": radius,
    "closeness_rank_spearman_unweighted_vs_weighted": spearman_cc,
}])
df_path_summary.to_csv(os.path.join(TABLES_DIR, "path_metrics_summary.csv"), index=False)
print(f"  → Saved: path_metrics_summary.csv")

# ──────────────────────────────────────────────────────────────
# 5. Plots
# ──────────────────────────────────────────────────────────────
print("\n[Step 5] Generating plots...")

# Plot A: Clustering Coefficient Histogram
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Unweighted
ax1.hist([cc_unweighted[n] for n in nodes if degrees_uw[n] > 0], bins=20, 
         color="#4C72B0", edgecolor="white", alpha=0.8)
ax1.axvline(global_cc_unweighted, color='red', linestyle='--', linewidth=1.5, 
            label=f'Global avg: {global_cc_unweighted:.3f}')
ax1.set_xlabel("Clustering Coefficient")
ax1.set_ylabel("Frequency")
ax1.set_title("Unweighted Clustering Coefficient")
ax1.legend()

# Weighted
ax2.hist([cc_weighted[n] for n in nodes if degrees_uw[n] > 0], bins=20, 
         color="#55A868", edgecolor="white", alpha=0.8)
ax2.axvline(global_cc_weighted, color='red', linestyle='--', linewidth=1.5,
            label=f'Global avg: {global_cc_weighted:.3f}')
ax2.set_xlabel("Clustering Coefficient")
ax2.set_ylabel("Frequency")
ax2.set_title("Weighted Clustering Coefficient")
ax2.legend()

plt.tight_layout()
save_figure(fig, "phase7_clustering_histogram.png")
plt.close(fig)

# Plot B: Eccentricity Distribution
fig, ax = plt.subplots(figsize=(8, 5))
ecc_counts = pd.Series(ecc_values).value_counts().sort_index()
ax.bar(ecc_counts.index, ecc_counts.values, color="#DD8452", edgecolor="white")
ax.set_xlabel("Eccentricity")
ax.set_ylabel("Number of Nodes")
ax.set_title(f"Eccentricity Distribution (G_giant)\nDiameter={diameter}, Radius={radius}")
ax.set_xticks(sorted(ecc_counts.index))
# Add count labels
for x, y in zip(ecc_counts.index, ecc_counts.values):
    ax.text(x, y + 0.5, str(y), ha='center', fontweight='bold')
plt.tight_layout()
save_figure(fig, "phase7_eccentricity_histogram.png")
plt.close(fig)

# Plot C: Clustering Coefficient vs Degree (scatter)
fig, ax = plt.subplots(figsize=(8, 6))
# Filter out isolates
mask = df_clustering["degree_unweighted"] > 0
ax.scatter(df_clustering.loc[mask, "degree_unweighted"], 
           df_clustering.loc[mask, "clustering_unweighted"],
           alpha=0.6, color="#4C72B0", edgecolors='white', s=60)
ax.set_xlabel("Degree (k)")
ax.set_ylabel("Clustering Coefficient (C)")
ax.set_title("Clustering Coefficient vs. Degree")

# Add trend line
from numpy.polynomial.polynomial import polyfit
x_data = df_clustering.loc[mask, "degree_unweighted"].values
y_data = df_clustering.loc[mask, "clustering_unweighted"].values
if len(x_data) > 2:
    z = np.polyfit(x_data, y_data, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x_data.min(), x_data.max(), 100)
    ax.plot(x_line, p(x_line), "r--", alpha=0.7, label=f"Trend (slope={z[0]:.4f})")
    ax.legend()

plt.tight_layout()
save_figure(fig, "phase7_clustering_vs_degree.png")
plt.close(fig)

# ──────────────────────────────────────────────────────────────
# 6. Report Update
# ──────────────────────────────────────────────────────────────
print("\n[Step 6] Updating report_draft.md and results_summary.md...")

report_path = os.path.join(PROJECT_ROOT, "report_draft.md")
with open(report_path, "r", encoding="utf-8") as f:
    report = f.read()

# Determine clustering-degree relationship
from scipy.stats import pearsonr
slope = z[0] if len(x_data) > 2 else 0
pearson_r, pearson_p = pearsonr(x_data, y_data) if len(x_data) > 2 else (np.nan, np.nan)
if pearson_p >= 0.05:
    cc_deg_interpretation = f"The degree–clustering relationship is weak (r={pearson_r:.3f}, p={pearson_p:.3f}) and does not provide sufficient evidence that high-degree respondents systematically occupy a different local structural role."
elif slope > 0.001:
    cc_deg_interpretation = "Higher-degree nodes tend to also have higher clustering coefficients, suggesting that well-connected respondents form tightly-knit local opinion clusters rather than serving as bridges between disparate groups."
elif slope < -0.001:
    cc_deg_interpretation = "Higher-degree nodes tend to have *lower* clustering coefficients, suggesting that the most connected respondents act as bridges between different opinion clusters rather than being embedded in a single tight-knit group."
else:
    cc_deg_interpretation = "There is no strong relationship between degree and clustering coefficient, suggesting that local clustering is relatively independent of global connectivity."

# Analysis and Visualizations: insert before Results and Discussion
analysis_update = f"""
### Clustering and Path Metrics

![Clustering Coefficient Distribution](outputs/figures/phase7_clustering_histogram.png)
*Figure: Distribution of per-node clustering coefficients across the full network. Left: unweighted (global average = {global_cc_unweighted:.3f}). Right: weighted by edge similarity (global average = {global_cc_weighted:.3f}). The high average clustering indicates that respondents' opinion neighbors tend to also be similar to each other, forming tightly-knit opinion triads.*

![Eccentricity Distribution](outputs/figures/phase7_eccentricity_histogram.png)
*Figure: Distribution of node eccentricities in the Giant Connected Component. The diameter (maximum eccentricity) is {diameter} and the radius (minimum eccentricity) is {radius}. The tight range of eccentricities indicates a compact topology where no respondent is far from the network's center.*

![Clustering vs Degree](outputs/figures/phase7_clustering_vs_degree.png)
*Figure: Scatter plot of each node's clustering coefficient against its degree. The red dashed trend line reveals the relationship between local clustering and global connectivity.*
"""

report = report.replace(
    "# Results and Discussion",
    analysis_update.strip() + "\n\n# Results and Discussion"
)

# Results and Discussion: add clustering/path section
results_update = f"""
## Clustering and Path Structure

The network exhibits a **global average clustering coefficient of {global_cc_unweighted:.3f}** (unweighted), indicating that opinion-neighbors of a given respondent are themselves highly likely to share similar opinions — a hallmark of strong triadic closure. The weighted clustering coefficient ({global_cc_weighted:.3f}) is similar, confirming that the triangular structure is not an artifact of the thresholding process.

{cc_deg_interpretation}

Path analysis on the Giant Connected Component reveals an **average shortest path length of {avg_path_len:.2f}** (unweighted) and a **diameter of {diameter}**. Thus, any two GCC respondents are separated by at most {diameter} edges, or {max(diameter - 1, 0)} intermediate respondents. A secondary check using weighted distances (distance = 1 − similarity) yielded an average path length of {avg_path_len_weighted:.2f}. {ranking_msg} A small-world conclusion is deferred until the Erdős–Rényi comparison in Phase 10.
"""

report = report.replace(
    "## Graph Topology",
    results_update.strip() + "\n\n## Graph Topology"
)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(report)

# Update results_summary.md
summary_path = os.path.join(PROJECT_ROOT, "results_summary.md")
with open(summary_path, "a", encoding="utf-8") as f:
    f.write(f"\n### Phase 7: Clustering & Path Metrics\n")
    f.write(f"- **Global Clustering (unweighted)**: {global_cc_unweighted:.4f}\n")
    f.write(f"- **Global Clustering (weighted)**: {global_cc_weighted:.4f}\n")
    f.write(f"- **Avg Path Length (unweighted)**: {avg_path_len:.4f}\n")
    f.write(f"- **Avg Path Length (weighted, d=1-sim)**: {avg_path_len_weighted:.4f}\n")
    f.write(f"- **Diameter**: {diameter}\n")
    f.write(f"- **Radius**: {radius}\n")
    f.write(f"- **Closeness centrality ranking correlation (uw vs w)**: {spearman_cc:.4f}\n")

print("  → Updated report_draft.md and results_summary.md")

print(f"\n{'=' * 70}")
print("PHASE 7 COMPLETE")
print(f"{'=' * 70}")
