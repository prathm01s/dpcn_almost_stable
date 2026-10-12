"""Step 16: Figure generation for Task 2 (Statistics Report).

Produces publication-quality 300 DPI PNGs and SVGs in stats/figures/
using consistent institute color styling and clear data labels.
"""

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Matplotlib configuration for publication quality
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

FIG_DIR = Path("stats/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR = Path("stats/tables")

COLORS = {
    "CSIR-IICT": "#2b5c8f",      # Deep Royal Blue
    "CSIR-NCL": "#2e7d32",       # Emerald Forest Green
    "CSIR-CECRI": "#d95f02",     # Amber Ochre
    "Group 24 Combined": "#4a148c", # Imperial Purple
    "Q1": "#1b9e77",             # Teal/Green
    "Q2": "#386cb0",             # Blue
    "Q3": "#fdb462",             # Yellow/Orange
    "Q4": "#e7298a",             # Pink/Red
    "Unranked": "#999999",       # Grey
}


def plot_fig1_publication_trends() -> None:
    """Fig 1: Annual Publication Trends across 3 institutes (2016-2026)."""
    df = pd.read_csv(TABLES_DIR / "publication_trend.csv")
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)

    years = sorted(df["year"].unique())
    x = np.arange(len(years))
    width = 0.25

    insts = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
    for i, inst in enumerate(insts):
        sub = df[df["institution"] == inst].sort_values("year")
        ax.bar(x + (i - 1) * width, sub["papers"], width=width, label=inst, color=COLORS[inst], alpha=0.9)

    # Combined line
    comb = df[df["institution"] == "Group 24 Combined"].sort_values("year")
    ax2 = ax.twinx()
    ax2.plot(x, comb["papers"], color=COLORS["Group 24 Combined"], marker="o", linewidth=2.5, label="Total Cluster (Combined)")
    ax2.set_ylabel("Total Papers (Combined)", color=COLORS["Group 24 Combined"], fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLORS["Group 24 Combined"])
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{y}*" if y == 2026 else str(y) for y in years], rotation=0)
    ax.set_xlabel("Publication Year (*2026 is partial through 13 Oct 2026)")
    ax.set_ylabel("Annual Distinct Papers per Institute")
    ax.set_title("Publication Output Trends (2016–2026) — CSIR Chemistry Cluster", pad=15, fontweight="bold")

    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", framealpha=0.9)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig1_publication_trends.png", dpi=300)
    fig.savefig(FIG_DIR / "fig1_publication_trends.svg")
    plt.close(fig)


def plot_fig2_quartile_distribution() -> None:
    """Fig 2: Journal Quartile Distribution (Stacked 100% and Counts)."""
    df = pd.read_csv(TABLES_DIR / "quartile_distribution.csv")
    df_overall = df[df["period"] == "2016-2026 Overall"].copy()

    inst_order = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI", "Group 24 Combined"]
    df_overall["order"] = df_overall["institution"].map(lambda x: inst_order.index(x) if x in inst_order else 99)
    df_overall = df_overall.sort_values("order")

    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=300)

    y_pos = np.arange(len(df_overall))
    q1_pcts = []
    q2_pcts = []
    q3_pcts = []
    q4_pcts = []
    un_pcts = []

    for _, r in df_overall.iterrows():
        tot = r["total_journals"]
        q1_pcts.append(r["q1_count"] / tot * 100)
        q2_pcts.append(r["q2_count"] / tot * 100)
        q3_pcts.append(r["q3_count"] / tot * 100)
        q4_pcts.append(r["q4_count"] / tot * 100)
        un_pcts.append(r["unranked_count"] / tot * 100)

    p1 = ax.barh(y_pos, q1_pcts, color=COLORS["Q1"], label="Q1 (Top 25%)", edgecolor="white")
    p2 = ax.barh(y_pos, q2_pcts, left=q1_pcts, color=COLORS["Q2"], label="Q2", edgecolor="white")
    left3 = np.array(q1_pcts) + np.array(q2_pcts)
    p3 = ax.barh(y_pos, q3_pcts, left=left3, color=COLORS["Q3"], label="Q3", edgecolor="white")
    left4 = left3 + np.array(q3_pcts)
    p4 = ax.barh(y_pos, q4_pcts, left=left4, color=COLORS["Q4"], label="Q4", edgecolor="white")
    left5 = left4 + np.array(q4_pcts)
    p5 = ax.barh(y_pos, un_pcts, left=left5, color=COLORS["Unranked"], label="Unranked", edgecolor="white")

    # Annotate Q1 percentages
    for i, pct in enumerate(q1_pcts):
        ax.text(pct / 2, i, f"{pct:.1f}%", ha="center", va="center", color="white", fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(df_overall["institution"], fontweight="bold")
    ax.set_xlabel("Share of Journal Publications (%)")
    ax.set_title("Journal Prestige Profile: SCImago Quartile Distribution (2016–2026)", pad=15, fontweight="bold")
    ax.set_xlim(0, 100)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=5, frameon=False)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig2_quartile_distribution.png", dpi=300)
    fig.savefig(FIG_DIR / "fig2_quartile_distribution.svg")
    plt.close(fig)


def plot_fig3_h_index_distribution() -> None:
    """Fig 3: Small multiples of faculty in-corpus h-index histograms."""
    df = pd.read_csv(TABLES_DIR / "h_index_distribution.csv")
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), dpi=300)
    axes = axes.flatten()

    insts = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI", "Group 24 Combined"]
    for i, inst in enumerate(insts):
        ax = axes[i]
        sub = df[df["institution"] == inst]
        bars = ax.bar(sub["bin_label"], sub["faculty_count"], color=COLORS.get(inst, "#555555"), alpha=0.85, edgecolor="black", linewidth=0.5)
        ax.set_title(f"{inst} Faculty", fontweight="bold")
        ax.set_ylabel("Number of Scientists")
        ax.set_xlabel("h-index (2016–2026 Corpus Window)")
        # Annotate top bar
        for b in bars:
            h = b.get_height()
            if h > 0:
                ax.text(b.get_x() + b.get_width() / 2, h + 0.5, str(int(h)), ha="center", va="bottom", fontsize=9)

    plt.suptitle("In-Corpus h-Index Distribution of Active Scientific Cadre Faculty", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig3_h_index_distribution.png", dpi=300)
    fig.savefig(FIG_DIR / "fig3_h_index_distribution.svg")
    plt.close(fig)


def plot_fig4_top_journals() -> None:
    """Fig 4: Top 5 journals per institution."""
    df = pd.read_csv(TABLES_DIR / "top_journals.csv")
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.5), dpi=300)

    insts = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
    for i, inst in enumerate(insts):
        ax = axes[i]
        sub = df[df["institution"] == inst].sort_values("rank", ascending=False)
        y_labels = [name[:28] + "..." if len(name) > 28 else name for name in sub["journal_name"]]
        bars = ax.barh(y_labels, sub["paper_count"], color=COLORS[inst], alpha=0.85)

        for b, (_, r) in zip(bars, sub.iterrows()):
            w = b.get_width()
            ax.text(w + 3, b.get_y() + b.get_height() / 2, f"{r['paper_count']} ({r['quartile']})", ha="left", va="center", fontsize=8.5, fontweight="bold")

        ax.set_title(f"Top 5 Journals: {inst}", fontweight="bold")
        ax.set_xlabel("Paper Count (2016–2026)")
        ax.set_xlim(0, max(sub["paper_count"]) * 1.25)

    plt.suptitle("Preferred Publishing Venues by Institute with Quartile Ratings", fontsize=14, fontweight="bold", y=1.0)
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig4_top_journals.png", dpi=300)
    fig.savefig(FIG_DIR / "fig4_top_journals.svg")
    plt.close(fig)


def plot_fig5_research_areas() -> None:
    """Fig 5: Research area share across the cluster."""
    df = pd.read_csv(TABLES_DIR / "research_areas_field.csv")
    comb = df[df["institution"] == "Group 24 Combined"].sort_values("paper_count", ascending=True)

    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=300)
    bars = ax.barh(comb["field"], comb["share_pct"], color="#3182bd", alpha=0.9, edgecolor="black", linewidth=0.5)

    for b, (_, r) in zip(bars, comb.iterrows()):
        w = b.get_width()
        ax.text(w + 0.8, b.get_y() + b.get_height() / 2, f"{r['share_pct']:.1f}% ({r['paper_count']:,} papers)", ha="left", va="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Cluster Publication Share (%)")
    ax.set_title("Research Domain Specialization (Primary Topics) — Group 24", pad=15, fontweight="bold")
    ax.set_xlim(0, max(comb["share_pct"]) * 1.25)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig5_research_areas.png", dpi=300)
    fig.savefig(FIG_DIR / "fig5_research_areas.svg")
    plt.close(fig)


def plot_fig6_citations_by_year() -> None:
    """Fig 6: Mean and Median citations per paper by publication vintage."""
    df = pd.read_csv(TABLES_DIR / "citation_summary.csv")
    df_years = df[(df["year"] != "ALL") & (df["institution"] != "Group 24 Combined")].copy()
    df_years["year"] = df_years["year"].astype(int)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    for inst in ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]:
        sub = df_years[df_years["institution"] == inst].sort_values("year")
        ax1.plot(sub["year"], sub["mean_citations"], marker="o", linewidth=2, label=inst, color=COLORS[inst])
        ax2.plot(sub["year"], sub["median_citations"], marker="s", linewidth=2, label=inst, color=COLORS[inst])

    ax1.set_title("Mean Citations per Paper by Vintage", fontweight="bold")
    ax1.set_xlabel("Publication Year")
    ax1.set_ylabel("Mean Lifetime Citations")
    ax1.legend()

    ax2.set_title("Median Citations per Paper by Vintage", fontweight="bold")
    ax2.set_xlabel("Publication Year")
    ax2.set_ylabel("Median Lifetime Citations")
    ax2.legend()

    plt.suptitle("Citation Accrual Dynamics by Publication Vintage (Older Cohorts Accrue Greater Impact)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig6_citations_by_year.png", dpi=300)
    fig.savefig(FIG_DIR / "fig6_citations_by_year.svg")
    plt.close(fig)


def plot_fig7_faculty_scatter() -> None:
    """Fig 7: Faculty scatter (Papers vs Citations, size proportional to h-index)."""
    df = pd.read_csv(TABLES_DIR / "faculty_performance.csv")
    df_active = df[df["papers"] > 0]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    for inst in ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]:
        sub = df_active[df_active["institution"] == inst]
        sizes = (sub["h_index_corpus"] + 3) * 6
        ax.scatter(sub["papers"], sub["citations"], s=sizes, color=COLORS[inst], alpha=0.65, edgecolors="none", label=f"{inst} Faculty")

    # Annotate top 3 standout scientists
    top3 = df_active.sort_values(by="citations", ascending=False).head(3)
    for _, r in top3.iterrows():
        ax.annotate(r["name"].replace("Dr. ", ""), (r["papers"], r["citations"]), textcoords="offset points", xytext=(8, 5), fontsize=8.5, fontweight="bold", arrowprops=dict(arrowstyle="->", color="#333333", lw=0.8))

    ax.set_xlabel("Publications in Corpus Window (2016–2026)")
    ax.set_ylabel("Total Citations Accrued")
    ax.set_title("Faculty Research Productivity & Citation Impact (Bubble Size ∝ Corpus h-Index)", pad=15, fontweight="bold")
    ax.legend(loc="upper left")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig7_faculty_scatter.png", dpi=300)
    fig.savefig(FIG_DIR / "fig7_faculty_scatter.svg")
    plt.close(fig)


def plot_fig8_department_performance() -> None:
    """Fig 8: Top 10 R&D departments across cluster by publication volume."""
    df = pd.read_csv(TABLES_DIR / "department_performance.csv")
    top_depts = df.sort_values("papers", ascending=True).tail(10)

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    y_pos = np.arange(len(top_depts))

    colors = [COLORS[inst] for inst in top_depts["institution"]]
    bars = ax.barh(y_pos, top_depts["papers"], color=colors, alpha=0.85)

    for b, (_, r) in zip(bars, top_depts.iterrows()):
        w = b.get_width()
        ax.text(w + 10, b.get_y() + b.get_height() / 2, f"{r['papers']} papers ({r['institution'].replace('CSIR-', '')})", ha="left", va="center", fontsize=8.5, fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels([d[:32] + "..." if len(d) > 32 else d for d in top_depts["department"]])
    ax.set_xlabel("Department Distinct Publications (2016–2026)")
    ax.set_title("Top 10 R&D Divisions by Publication Volume Across Cluster", pad=15, fontweight="bold")
    ax.set_xlim(0, max(top_depts["papers"]) * 1.3)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "fig8_department_performance.png", dpi=300)
    fig.savefig(FIG_DIR / "fig8_department_performance.svg")
    plt.close(fig)


def run_figure_generation() -> None:
    logger = Path("stats/figures")
    logger.mkdir(parents=True, exist_ok=True)
    print("Generating Fig 1: Publication Trends...")
    plot_fig1_publication_trends()
    print("Generating Fig 2: Quartile Distribution...")
    plot_fig2_quartile_distribution()
    print("Generating Fig 3: h-Index Distribution...")
    plot_fig3_h_index_distribution()
    print("Generating Fig 4: Top Journals...")
    plot_fig4_top_journals()
    print("Generating Fig 5: Research Areas...")
    plot_fig5_research_areas()
    print("Generating Fig 6: Citations by Vintage...")
    plot_fig6_citations_by_year()
    print("Generating Fig 7: Faculty Scatter...")
    plot_fig7_faculty_scatter()
    print("Generating Fig 8: Department Performance...")
    plot_fig8_department_performance()
    print("✓ All 8 figures successfully generated in PNG (300 DPI) and SVG formats!")


if __name__ == "__main__":
    run_figure_generation()
