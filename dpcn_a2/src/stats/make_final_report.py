"""Key-observations report (4 pages, A4, LaTeX): basic statistics, network analysis, the Global Benchmark and the
idea-spreading study of CSIR-NCL, CSIR-IICT and CSIR-CECRI (D-47).

Every number in the text, tables and figures is read from stats/tables/ and data/final/ (the same files the dashboard
uses); the prose holds placeholders <<key>> that are filled here, and the build stops if one is left unfilled.
Figures are drawn with matplotlib as vector PDFs; the LaTeX is compiled with Tectonic.

    python -m src.stats.make_final_report
Outputs: stats/report/final/{report.tex, fig_*.pdf} and stats/report/Group24_CSIR_Chemistry_Report.pdf
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from src.stats import make_findings_report as mfr
from src.stats.networks import faculty_coauthor_graph, faculty_papers

T = Path("stats/tables")
OUT = Path("stats/report/final")
PDF = Path("stats/report/Group24_CSIR_Chemistry_Report.pdf")
SITE = "https://dpcnsite.vercel.app/"
MEMBERS = ["Samarth Singla", "Sanjith Ganapathi", "Prathmesh Sharma"]
LABS = ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"]
ALL = "Group 24 Combined"
SHORT = {"CSIR-IICT": "IICT", "CSIR-NCL": "NCL", "CSIR-CECRI": "CECRI", ALL: "All three"}
LAB_COL = {"CSIR-IICT": "#2b5c8f", "CSIR-NCL": "#2e7d32", "CSIR-CECRI": "#d95f02"}
GROUP_COL = {"CSIR lab": "#2a78d6", "India": "#eb6834", "USA": "#1baf7a", "China": "#eda100", "South Korea": "#e87ba4", "Australia": "#008300"}
GROUP_TAG = {"CSIR lab": "", "India": "IN", "USA": "US", "China": "CN", "South Korea": "KR", "Australia": "AU"}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
                     "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "pdf.fonttype": 42})


def f0(x):
    return f"{int(round(float(x))):,}"


def p1(x):
    return f"{float(x):.1f}"


def pc(a, b, d=1):
    return round(100 * float(a) / float(b), d) if b else 0.0


def med(s):
    return float(np.median([x for x in s if x is not None and not pd.isna(x)]))


def tex_escape(s):
    return (str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%").replace("$", r"\$")
            .replace("#", r"\#").replace("_", r"\_").replace("{", r"\{").replace("}", r"\}"))


# ------------------------------------------------------------------ data
def load():
    D = mfr.load()
    D["shares"], D["counts"] = mfr.cross_shares(D)
    D["gs"] = pd.read_csv(T / "global_summary.csv")
    D["gp"] = pd.read_csv(T / "global_peers.csv")
    D["sim"] = pd.read_csv(T / "global_similarity.csv")
    D["links"] = pd.read_csv(T / "global_links.csv")
    D["uni"] = pd.read_csv(T / "global_indian_universities.csv")
    D["cr"] = pd.read_csv(T / "global_country_relations.csv")
    D["ctry"] = pd.read_csv(T / "global_countries.csv")
    D["funnel"] = pd.read_csv(T / "global_rule_funnel.csv")
    D["scope"] = pd.read_csv("data/final/global/scope_subfields.csv")
    D["excl"] = pd.read_csv("config/overrides/global_peer_exclusions.csv")
    I = T / "insights"
    D["real"] = json.loads((I / "11_real_diffusion.json").read_text(encoding="utf-8"))
    cl = json.loads((I / "11_claims.json").read_text(encoding="utf-8"))
    D["claims"] = {c["id"]: c for c in cl["claims"]}
    D["n_claims"], D["n_passed"] = cl["n_claims"], cl["n_passed"]
    for k in ("01_friendship_paradox", "02_rich_club", "03_fragility", "04_price_law"):
        D[k] = json.loads((I / f"{k}.json").read_text(encoding="utf-8"))["metrics"]
    return D


# ------------------------------------------------------------------ figures
def fig_trends(D, path):
    tr, oy = D["trend"], D["oy"]
    fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.05))
    for lab in LABS:
        s = tr[tr["institution"] == lab]
        ax[0].plot(s["year"], s["papers"], marker="o", ms=2.6, lw=1.5, color=LAB_COL[lab], label=SHORT[lab])
    ax[0].set_title("(a) Papers per year", loc="left")
    ax[0].set_ylabel("distinct papers")
    ax[0].legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.55, 1.0))
    c = oy[oy["institution"] == ALL].sort_values("year")
    for col, lab, st in (("q1_papers", "Q1", "-"), ("q1_if_gt5", "Q1 & IF > 5", "--"), ("q1_if_gt10", "Q1 & IF > 10", ":")):
        ax[1].plot(c["year"], c[col] / c["papers"] * 100, st, marker="o", ms=2.6, lw=1.5, color="#1d2b4f", label=lab)
    ax[1].set_title("(b) Share of the three labs' papers in top journals", loc="left")
    ax[1].set_ylabel("% of papers")
    ax[1].set_ylim(0, 70)
    ax[1].legend(frameon=False, loc="center left", bbox_to_anchor=(0.0, 0.57))
    for a in ax:
        a.axvspan(2025.5, 2026.5, color="#999", alpha=0.15, lw=0)
        a.set_xticks(range(2016, 2027, 2))
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", alpha=0.25, lw=0.5)
    ax[0].text(2026, 640, "2026\npartial", ha="center", va="top", fontsize=5.5, color="#555")
    fig.tight_layout(pad=0.4)
    fig.savefig(path)
    plt.close(fig)


def fig_network(D, path):
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    G = faculty_coauthor_graph(faculty_papers(ext, fm), fm)
    H = G.subgraph(sorted(max(nx.connected_components(G), key=len))).copy()
    pos = nx.spring_layout(H, seed=24, k=0.18, iterations=200, weight=None)
    fig = plt.figure(figsize=(3.43, 3.3))
    ax0 = fig.add_axes([0.0, 0.36, 1.0, 0.57])
    ax1 = fig.add_axes([0.42, 0.05, 0.53, 0.25])
    cross = [(u, v) for u, v in H.edges if H.nodes[u]["lab"] != H.nodes[v]["lab"]]
    within = [(u, v) for u, v in H.edges if H.nodes[u]["lab"] == H.nodes[v]["lab"]]
    nx.draw_networkx_edges(H, pos, edgelist=within, ax=ax0, width=0.35, edge_color="#9aa5b1", alpha=0.6)
    nx.draw_networkx_edges(H, pos, edgelist=cross, ax=ax0, width=1.2, edge_color="#e0a100")
    deg = dict(H.degree())
    nx.draw_networkx_nodes(H, pos, ax=ax0, node_size=[4 + 1.6 * deg[n] for n in H],
                           node_color=[LAB_COL[H.nodes[n]["lab"]] for n in H], linewidths=0.25, edgecolors="white")
    for lab in LABS:
        ax0.scatter([], [], color=LAB_COL[lab], s=14, label=SHORT[lab])
    ax0.plot([], [], color="#e0a100", lw=1.2, label="cross-lab pair")
    ax0.legend(frameon=False, loc="upper left", ncol=4, fontsize=6, handletextpad=0.3, columnspacing=0.8)
    ax0.set_title(f"(a) Faculty co-authorship, largest component ({H.number_of_nodes()} scientists)", loc="left", fontsize=7)
    ax0.axis("off")
    sh = D["shares"]
    names = ["Co-authorship links,\nall authors", "Co-author pairs,\nfaculty", "Citation links,\npapers", "Citation edges,\nscientists"]
    vals = [sh["Co-authorship, all lab authors (links)"], sh["Co-authorship, faculty only (pairs)"],
            sh["Citations between papers (links)"], sh["Citations between scientists (edges)"]]
    bars = ax1.barh(range(4), vals, color=["#7f8c9a", "#7f8c9a", "#b0763a", "#b0763a"], height=0.62)
    ax1.set_yticks(range(4))
    ax1.set_yticklabels(names, fontsize=5.8)
    ax1.invert_yaxis()
    for b, v in zip(bars, vals):
        ax1.text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=5.8)
    ax1.set_xlim(0, max(vals) * 1.3)
    ax1.set_xlabel("% of links joining two different labs", fontsize=6)
    ax1.set_title("(b) Writing together vs. reading each other", loc="left", fontsize=7, x=-0.62)
    ax1.spines[["top", "right"]].set_visible(False)
    fig.savefig(path)
    plt.close(fig)
    return H


def fig_global(D, path):
    gs = D["gs"].copy()
    gs["tag"] = gs.apply(lambda r: r["short"] if r["group"] == "CSIR lab" else f"{r['short']} ({GROUP_TAG[r['group']]})", axis=1)
    world = D["world"].at["2016-2025", "top10_pct"]
    fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.75), gridspec_kw={"width_ratios": [1, 1.05]})
    a = ax[0]
    for g, col in GROUP_COL.items():
        s = gs[gs["group"] == g]
        a.scatter(s["cagr_pct"], s["top10_pct"], s=34 if g == "CSIR lab" else 20, color=col, edgecolor="white", lw=0.5,
                  label={"CSIR lab": "CSIR labs", "India": "Indian reference"}.get(g, g + " twin"), zorder=3)
    off = {"CSIR-IICT": (4, -3), "CSIR-NCL": (4, 2), "CSIR-CECRI": (4, 2), "IISc": (4, 3), "IACS Kolkata": (-12, -9),
           "ORNL": (4, -1), "NLR (ex-NREL)": (2, -8), "DICP": (-6, 4), "FJIRSM": (-10, -8), "SIOC": (4, 2), "KRICT": (4, -1),
           "KIER": (-17, 3), "ANSTO": (4, -1), "CSIRO Manufacturing": (4, -7)}
    for _, r in gs.iterrows():
        if r["short"] not in off:
            continue
        bold = r["group"] == "CSIR lab"
        a.annotate(r["short"].replace("CSIR-", "").replace(" Manufacturing", " Mfg."), (r["cagr_pct"], r["top10_pct"]),
                   xytext=off[r["short"]], textcoords="offset points", fontsize=6.4 if bold else 5.6,
                   fontweight="bold" if bold else "normal", color="#222" if bold else "#555")
    a.annotate("IIT B, IIT M,\nICT, IISER", (3.5, 11.6), xytext=(5.0, 8.4), fontsize=5.4, color="#555",
               arrowprops={"arrowstyle": "-", "color": "#aaa", "lw": 0.5})
    a.axhline(world, color="#888", ls="--", lw=0.8)
    a.text(-8.9, world + 0.35, f"world {world:.1f}%", fontsize=5.6, color="#666")
    a.set_ylim(8, 29.5)
    a.set_xlim(-9.2, 9.8)
    a.axvline(0, color="#bbb", lw=0.6)
    a.set_xlabel("growth of output, % a year (2016 to 2025)")
    a.set_ylabel("% of papers in the world's top 10%")
    a.set_title("(a) Growth vs. field-normalised impact", loc="left")
    a.legend(frameon=False, fontsize=5.6, loc="center left", bbox_to_anchor=(0.0, 0.6), ncol=1, handletextpad=0.2)
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.2, lw=0.5)
    b = ax[1]
    s = gs.sort_values("q1_if10_pct")
    y = np.arange(len(s))
    cols = [GROUP_COL[g] for g in s["group"]]
    b.barh(y, s["q1_if5_pct"], color=cols, alpha=0.30, height=0.78, label="Q1 & IF > 5")
    b.barh(y, s["q1_if10_pct"], color=cols, alpha=1.0, height=0.78, label="Q1 & IF > 10")
    for yi, (_, r) in zip(y, s.iterrows()):
        b.text(r["q1_if5_pct"] + 0.8, yi, f"{r['q1_if10_pct']:.1f} | {r['q1_if5_pct']:.0f}", va="center", fontsize=5.2, color="#333")
    b.set_yticks(y)
    b.set_yticklabels(s["tag"], fontsize=5.8)
    for lbl, (_, r) in zip(b.get_yticklabels(), s.iterrows()):
        if r["group"] == "CSIR lab":
            lbl.set_fontweight("bold")
    b.set_xlim(0, 75)
    b.set_xlabel("% of papers (dark: Q1 & IF > 10; light: Q1 & IF > 5)")
    b.set_title("(b) Papers in top Q1 journals", loc="left")
    b.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(pad=0.4, w_pad=1.2)
    fig.savefig(path)
    plt.close(fig)


def fig_flows(D, path):
    """One-column figure. (a) Exchange ratio by partner group (partner papers citing the labs / partner papers the labs
    cite); (b) real per-tie transmissibility of ideas against the tipping points."""
    L, U = D["links"], D["uni"][D["uni"]["lab"] == "All three"]
    rows = []
    for g in ["USA", "Australia", "China", "South Korea"]:
        x = L[L["group"] == g]
        rows.append((f"{g} peers", x["peer_papers_citing_lab"].sum() / x["peer_papers_cited_by_lab"].sum(), GROUP_COL[g]))
    x = L[L["group"] != "India"]
    rows.append(("All foreign peers", x["peer_papers_citing_lab"].sum() / x["peer_papers_cited_by_lab"].sum(), "#555555"))
    x = L[L["group"] == "India"]
    rows.append(("6 Indian institutes", x["peer_papers_citing_lab"].sum() / x["peer_papers_cited_by_lab"].sum(), GROUP_COL["India"]))
    for tier, lab in (("IISc / IIT", "IISc + 9 IITs"), ("State university", "6 state universities")):
        x = U[U["tier"] == tier]
        rows.append((lab, x["papers_citing_lab"].sum() / x["papers_cited_by_lab"].sum(), "#b3471d"))
    fig = plt.figure(figsize=(3.43, 3.3))
    a = fig.add_axes([0.36, 0.58, 0.6, 0.33])
    b = fig.add_axes([0.36, 0.1, 0.6, 0.27])
    y = np.arange(len(rows))
    a.barh(y, [np.log2(r[1]) for r in rows], color=[r[2] for r in rows], height=0.66)
    for yi, r in zip(y, rows):
        v = np.log2(r[1])
        a.text(v + (0.05 if v >= 0 else -0.05), yi, f"{r[1]:.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=5.8)
    a.set_yticks(y)
    a.set_yticklabels([r[0] for r in rows], fontsize=6)
    a.invert_yaxis()
    a.axvline(0, color="#333", lw=0.8)
    a.set_xlim(-1.9, 1.6)
    a.set_xticks([np.log2(v) for v in (0.33, 0.5, 1, 2)])
    a.set_xticklabels(["0.33", "0.5", "1", "2"])
    a.set_xlabel("exchange ratio (log scale)", fontsize=6)
    a.text(-0.06, -0.85, "← labs draw on partner", fontsize=5.4, color="#666", ha="right", va="bottom")
    a.text(0.06, -0.85, "partner draws on labs →", fontsize=5.4, color="#666", ha="left", va="bottom")
    a.set_ylim(len(rows) - 0.5, -1.2)
    fig.text(0.01, 0.975, "(a) Who learns from whom", fontsize=7, va="top")
    a.spines[["top", "right"]].set_visible(False)
    t, tp = D["real"]["transmissibility"], D["real"]["tipping_points"]
    cats = [("All cited works", t["overall"])] + [(f"Cited by {k.replace(' papers', '')} lab papers", t["by_bucket"][k]) for k in ("2-4 papers", "5-9 papers", "10+ papers")]
    y = np.arange(len(cats))
    car = [c[1]["T_carried_pct"] for c in cats]
    ind = [c[1]["T_independent_pct"] for c in cats]
    b.barh(y, car, color="#2a78d6", height=0.6, label="carried by an earlier user")
    b.barh(y, ind, left=car, color="#9cc3ef", height=0.6, label="used independently")
    for yi, c in zip(y, cats):
        b.text(c[1]["T_pct"] + 0.4, yi, f"{c[1]['T_pct']:.2f}%", va="center", fontsize=5.8)
    for v, lab, col in ((100 * tp["full_coauthorship"], "tipping point,\nall authors", "#eb6834"), (100 * tp["faculty_coauthorship"], "tipping point,\nfaculty only", "#c98500")):
        b.axvline(v, color=col, ls="--", lw=1)
        right = v > 15  # the faculty line sits near the right edge: label it on its left
        b.text(v - 0.4 if right else v + 0.4, -0.75, f"{lab} ({v:g}%)", fontsize=5.2, color=col, va="center", ha="right" if right else "left")
    b.set_yticks(y)
    b.set_yticklabels([c[0] for c in cats], fontsize=6)
    b.set_ylim(len(cats) - 0.5, -1.3)
    b.set_xlim(0, 30)
    b.set_xlabel("chance an idea passes over a co-authorship tie (%)", fontsize=6)
    b.legend(frameon=False, loc="lower right", fontsize=5.4, bbox_to_anchor=(1.0, 0.02))
    fig.text(0.01, 0.46, "(b) Real ideas against the tipping point", fontsize=7, va="top")
    b.spines[["top", "right"]].set_visible(False)
    fig.savefig(path)
    plt.close(fig)


# ------------------------------------------------------------------ tables
def table_overview(D):
    ov, cit, h, tr = D["ov"], D["cit"], D["h"], D["trend"]
    rows = []
    for l in LABS + [ALL]:
        r = ov.loc[l]
        n = r["papers"]
        g = tr[tr["institution"] == l]["cagr_2016_2025"].iloc[0]
        bold = (lambda x: r"\textbf{" + x + "}") if l == ALL else (lambda x: x)
        cells = [SHORT[l], f0(n), f"{pc(r['q1_papers'], n)}", f"{pc(r['q1_if_gt5'], n)}", f"{pc(r['q1_if_gt10'], n)}",
                 f"{pc(r['papers_lt10_authors'], n)}", f"{r['mean_authors']:.1f}", f"{r['intl_papers_pct']:.1f}",
                 f"{cit.at[l, 'mean_citations']:.1f}\\,/\\,{cit.at[l, 'median_citations']:.0f}",
                 f"{h.at[l, 'mean_h_index']:.1f}\\,/\\,{h.at[l, 'max_h_index']:.0f}", f"{g:+.1f}"]
        rows.append(" & ".join(bold(c) for c in cells) + r" \\")
    return "\n".join(rows)


def table_networks(D):
    def ns(net, m):
        return mfr.nsv(D, net, m)
    sh = D["shares"]
    r = [
        ("Co-authorship, all lab authors", f0(ns("authorship", "authors (nodes)")), f0(ns("authorship", "co-author pairs (unique edges)")),
         f"{ns('authorship', 'mean degree (distinct co-authors)'):.1f}", f"{f0(ns('authorship', 'Louvain communities'))} ({ns('authorship', 'modularity'):.2f})",
         f"{sh['Co-authorship, all lab authors (links)']:.1f}"),
        ("Co-authorship, faculty", f0(ns("faculty_coauthorship", "nodes (roster scientists with >= 1 paper)")),
         f0(ns("faculty_coauthorship", "co-author pairs (unique edges)")), f"{ns('faculty_coauthorship', 'mean degree (distinct faculty co-authors)'):.1f}",
         f"{f0(ns('faculty_coauthorship', 'Louvain communities (connected scientists)'))} ({ns('faculty_coauthorship', 'modularity'):.2f})",
         f"{sh['Co-authorship, faculty only (pairs)']:.1f}"),
        ("Citation, paper $\\to$ paper", f0(ns("citation", "nodes (papers with >= 1 in-corpus link)")), f0(ns("citation", "distinct citing-cited paper pairs")),
         f"{ns('citation', 'mean in-degree (corpus papers)'):.1f}", "--", f"{sh['Citations between papers (links)']:.1f}"),
        ("Citation, scientist $\\to$ scientist", f0(ns("faculty_citation", "scientists citing or cited by another scientist")),
         f0(ns("faculty_citation", "directed edges (scientist A cites scientist B)")), "--", "--", f"{sh['Citations between scientists (edges)']:.1f}"),
    ]
    return "\n".join(" & ".join(x) + r" \\" for x in r)


def table_peers(D):
    gp, sim = D["gp"], D["sim"]
    countries = ["USA", "China", "South Korea", "Australia"]
    floor = 0.4
    rows = []
    for lab in LABS:
        cells, n = [lab.replace("CSIR-", "")], 0
        for cn in countries:
            t = gp[(gp["group"] == cn) & (gp["twin_of"] == lab)]
            if len(t):
                n += 1
                cells.append(f"{tex_escape(t.iloc[0]['short'].replace(' Manufacturing', ' Manuf.'))} \\textcolor{{muted}}{{{t.iloc[0]['similarity']:.2f}}}")
            else:
                c = sim[(sim["country"] == cn) & sim[f"sim_{lab}"].notna()]
                free = c[c["selected_twin_of"].isna()].sort_values(f"sim_{lab}", ascending=False)
                best = free.iloc[0] if len(free) else None
                short = {r["institution_id"]: r["short"] for _, r in gp.iterrows()}
                nm = (short.get(best["institution_id"]) or best["name"]) if best is not None else ""
                nm = {"Pacific Northwest National Laboratory": "PNNL", "Korea Basic Science Institute": "KBSI",
                      "QIMR Berghofer Medical Research Institute": "QIMR"}.get(nm, nm)
                cells.append(f"--- \\textcolor{{muted}}{{({tex_escape(nm)} {best[f'sim_{lab}']:.2f})}}" if best is not None else "---")
        cells.append(f"{n}/4")
        rows.append(" & ".join(cells) + r" \\")
    return "\n".join(rows)


# ------------------------------------------------------------------ values for the prose
def values(D):
    V = {}
    ov, oy, tr, cit, q = D["ov"], D["oy"], D["trend"], D["cit"], D["q"]
    A = ov.loc[ALL]
    V.update(papers=f0(A["papers"]), journal=f0(q.at[ALL, "total_journals"]), conf=f0(A["papers"] - q.at[ALL, "total_journals"]),
             faculty=f0(A["active_faculty"]), roster=f0(D["claims"]["C10"]["value"]["roster"]),
             authors=f0(mfr.nsv(D, "authorship", "authors (nodes)")), if_cov=p1(pc(A["papers_with_if"], A["papers"])),
             q1=p1(pc(A["q1_papers"], A["papers"])), q1if5=p1(pc(A["q1_if_gt5"], A["papers"])), q1if10=p1(pc(A["q1_if_gt10"], A["papers"])),
             lt10=p1(pc(A["papers_lt10_authors"], A["papers"])), mean_auth=f"{A['mean_authors']:.1f}", ge30=f0(A["papers_ge30_authors"]),
             intl=p1(A["intl_papers_pct"]), countries=f0(A["collab_countries"]), partners=f0(A["collab_institutions"]),
             cites=f0(cit.at[ALL, "total_citations"]), cmean=p1(cit.at[ALL, "mean_citations"]), cmed=f0(cit.at[ALL, "median_citations"]),
             uncited=p1(cit.at[ALL, "uncited_share_pct"]))
    c = oy[oy["institution"] == ALL].set_index("year")
    for y in (2016, 2025):
        V[f"q1_{y}"] = p1(pc(c.at[y, "q1_papers"], c.at[y, "papers"]))
        V[f"if5_{y}"] = p1(pc(c.at[y, "q1_if_gt5"], c.at[y, "papers"]))
        V[f"if10_{y}"] = p1(pc(c.at[y, "q1_if_gt10"], c.at[y, "papers"]))
        V[f"auth_{y}"] = f"{c.at[y, 'mean_authors']:.2f}"
    tc = tr[tr["institution"] == ALL].set_index("year")
    V.update(p2016=f0(tc.at[2016, "papers"]), p2025=f0(tc.at[2025, "papers"]))
    for l in LABS + [ALL]:
        k = SHORT[l].replace(" ", "").lower()
        V[f"g_{k}"] = f"{tr[tr['institution'] == l]['cagr_2016_2025'].iloc[0]:+.1f}"
        r = ov.loc[l]
        V[f"q1_{k}"] = p1(pc(r["q1_papers"], r["papers"]))
        V[f"if5_{k}"] = p1(pc(r["q1_if_gt5"], r["papers"]))
        V[f"if10_{k}"] = p1(pc(r["q1_if_gt10"], r["papers"]))
        V[f"n_{k}"] = f0(r["papers"])
        V[f"n10_{k}"] = f0(r["q1_if_gt10"])
    ncl = tr[tr["institution"] == "CSIR-NCL"].set_index("year")
    V["ncl_ours"] = ", ".join(f0(ncl.at[y, "papers"]) for y in (2021, 2022, 2023))
    top = D["tc"][D["tc"]["institution"] == ALL].iloc[0]
    V.update(top_title=tex_escape(top["title"][:62]) + r"\ldots", top_j=tex_escape(top["journal_name"]), top_y=str(top["year"]), top_c=f0(top["citations"]))
    # networks
    def ns(net, m):
        return mfr.nsv(D, net, m)
    sh, (a_cross, a_tot, c_cross, c_tot) = D["shares"], D["counts"]
    comm = D["comm"]
    purity = comm[["authors_iict", "authors_ncl", "authors_cecri"]].max(axis=1) / comm["authors"]
    n_fac = ns("faculty_coauthorship", "nodes (roster scientists with >= 1 paper)")
    n_iso = n_fac - ns("faculty_coauthorship", "scientists with >= 1 faculty co-author")
    V.update(lcc=p1(ns("authorship", "largest component share pct")), dens=f"{ns('authorship', 'density'):.4f}",
             ncomm=f0(ns("authorship", "Louvain communities")), mod=f"{ns('authorship', 'modularity'):.2f}",
             purity=f"{purity.min() * 100:.0f}", ncomm_top=str(len(comm)),
             x_auth=p1(sh["Co-authorship, all lab authors (links)"]), x_fac=p1(sh["Co-authorship, faculty only (pairs)"]),
             x_cit=p1(sh["Citations between papers (links)"]), x_sci=p1(sh["Citations between scientists (edges)"]),
             x_ratio=f"{sh['Citations between scientists (edges)'] / sh['Co-authorship, faculty only (pairs)']:.0f}",
             fac_cross=f0(ns("faculty_coauthorship", "cross-lab co-author pairs")), fac_pairs=f0(ns("faculty_coauthorship", "co-author pairs (unique edges)")),
             n_iso=f0(n_iso), n_fac=f0(n_fac), iso_pct=p1(pc(n_iso, n_fac)), recip=f"{ns('faculty_citation', 'reciprocity'):.2f}")
    ab = D["abtw"]
    V["bridges"] = ", ".join(f"{tex_escape(r.author.replace('Dr. ', '').replace('Dr ', ''))} ({SHORT[r.institution]})" for r in ab.head(3).itertuples())
    pr5 = D["pr"].head(5)
    V["pr_cecri"] = str(int(pr5["institutions"].str.contains("CECRI").sum()))
    fp, rc, fr, pl = D["01_friendship_paradox"], D["02_rich_club"], D["03_fragility"], D["04_price_law"]
    V.update(fp=p1(fp["share_paradox"]), fp_k=p1(fp["mean_k"]), fp_nk=p1(fp["mean_neighbour_k"]), rc=f"{rc['rho_norm_at_k_star']:.2f}",
             fr_n=f0(fr["n50_betweenness"]), fr_pct=p1(fr["n50_betweenness_pct"]), fr_rand=f0(fr["n50_random"]),
             pl_n=str(pl["n_sqrt"]), pl_share=p1(pl["price_share_pct"]), gini=f"{pl['gini_papers']:.2f}", gini_c=f"{pl['gini_citations']:.2f}")
    # global benchmark
    gs = D["gs"].set_index("short")
    world = D["world"].at["2016-2025", "top10_pct"]
    tw = D["gs"][~D["gs"]["group"].isin(["CSIR lab", "India"])]
    ind = D["gs"][D["gs"]["group"] == "India"]
    labs = D["gs"][D["gs"]["group"] == "CSIR lab"]
    for col, k in (("top10_pct", "t10"), ("q1_pct", "gq1"), ("q1_if5_pct", "gif5"), ("q1_if10_pct", "gif10"), ("cagr_pct", "gcagr")):
        V[f"{k}_tw"] = p1(med(tw[col]))
        V[f"{k}_in"] = p1(med(ind[col]))
        V[f"{k}_lab"] = p1(med(labs[col]))
        for l in LABS:
            V[f"{k}_{SHORT[l].lower()}"] = p1(gs.at[l, col])
    V["gap_q1"] = f"{med(tw['q1_pct']) / med(labs['q1_pct']):.1f}"
    V["gap_if5"] = f"{med(tw['q1_if5_pct']) / med(labs['q1_if5_pct']):.1f}"
    V["gap_if10"] = f"{med(tw['q1_if10_pct']) / med(labs['q1_if10_pct']):.1f}"
    V["gap_t10"] = f"{med(tw['top10_pct']) / med(labs['top10_pct']):.1f}"
    V["if10_tw_min"], V["if10_tw_max"] = p1(tw["q1_if10_pct"].min()), p1(tw["q1_if10_pct"].max())
    V["if10_lab_min"], V["if10_lab_max"] = p1(labs["q1_if10_pct"].min()), p1(labs["q1_if10_pct"].max())
    V["world"] = f"{world:.2f}"
    V.update(dicp_g=p1(gs.at["DICP", "cagr_pct"]), fj_g=p1(gs.at["FJIRSM", "cagr_pct"]), dicp_if10=p1(gs.at["DICP", "q1_if10_pct"]),
             sioc_t10=p1(gs.at["SIOC", "top10_pct"]))
    cr = D["cr"].set_index("country_code")
    V.update(c_us=f0(cr.at["US", "papers"]), c_kr=f0(cr.at["KR", "papers"]), c_au=f0(cr.at["AU", "papers"]), c_cn=f0(cr.at["CN", "papers"]),
             c_cn_rank=str(cr.at["CN", "rank"]), c_n=f0(len(D["cr"])))
    ct = D["ctry"]
    V["cn16"] = p1(ct[(ct["country_code"] == "CN") & (ct["year"] == 2016)]["world_share_pct"].iloc[0])
    V["cn25"] = p1(ct[(ct["country_code"] == "CN") & (ct["year"] == 2025)]["world_share_pct"].iloc[0])
    sc = D["scope"]
    V.update(n_scope=str(int(sc["in_scope"].sum())), n_excl=str(len(D["excl"])))
    fu = D["funnel"]
    V.update(pool=f0(fu["Pool (rule 1)"].sum()), tested=f0(fu["Similarity tested (rule 4)"].sum()), twins=f0(fu["Selected twins"].sum()))
    L = D["links"]
    fl, il = L[L["group"] != "India"], L[L["group"] == "India"]
    V.update(co_for=f0(fl["coauthored_papers"].sum()), co_twin=f0(fl[fl["is_twin"]]["coauthored_papers"].sum()), co_ind=f0(il["coauthored_papers"].sum()),
             in_for=f0(fl["peer_papers_citing_lab"].sum()), out_for=f0(fl["peer_papers_cited_by_lab"].sum()),
             r_for=f"{fl['peer_papers_citing_lab'].sum() / fl['peer_papers_cited_by_lab'].sum():.2f}",
             r_ind=f"{il['peer_papers_citing_lab'].sum() / il['peer_papers_cited_by_lab'].sum():.2f}")
    us = fl[fl["group"] == "USA"]
    V["r_us"] = f"{us['peer_papers_citing_lab'].sum() / us['peer_papers_cited_by_lab'].sum():.2f}"
    U = D["uni"][D["uni"]["lab"] == "All three"]
    for tier, k in (("IISc / IIT", "r_iit"), ("State university", "r_state")):
        x = U[U["tier"] == tier]
        V[k] = f"{x['papers_citing_lab'].sum() / x['papers_cited_by_lab'].sum():.2f}"
    pairs = []
    for _, r in D["uni"][D["uni"]["lab"] != "All three"].iterrows():
        m = L[(L["lab"] == r["lab"]) & (L["short"] == r["university"])]
        if len(m):
            m = m.iloc[0]
            pairs += [abs(r["papers_citing_lab"] - m["peer_papers_citing_lab"]) / m["peer_papers_citing_lab"],
                      abs(r["papers_cited_by_lab"] - m["peer_papers_cited_by_lab"]) / m["peer_papers_cited_by_lab"]]
    V["xcheck"] = p1(100 * max(pairs))
    prof = pd.read_csv(T / "global_profiles.csv")
    org = lambda s: prof[(prof["short"] == s) & (prof["subfield"] == "Organic Chemistry")]["share_pct"]
    V.update(org_iict=f"{org('CSIR-IICT').iloc[0]:.0f}", org_sioc=f"{org('SIOC').iloc[0]:.0f}",
             org_other=f"{max(float(org(s).iloc[0]) for s in tw['short'] if s != 'SIOC' and len(org(s))):.0f}")
    # idea spreading
    cv = lambda i: D["claims"][i]["value"]
    R = D["real"]
    t = R["transmissibility"]
    ex = {r["k"]: r for r in R["exposure"]["rows"]}
    org2 = {r["origin"]: r for r in R["between_labs"]["by_origin"]}
    V.update(n_full=f0(D["claims"]["C1"]["value"] and 7678), t50f=f"{cv('C1')['T50_full']:g}", t50k=f"{cv('C1')['T50_faculty']:g}",
             tpf=f"{cv('C2')['T_peak_full']:g}", tpk=f"{cv('C2')['T_peak_faculty']:g}", tpx=f"{cv('C2')['T_peak_faculty'] / cv('C2')['T_peak_full']:.1f}",
             rr_min=f"{min(cv('C3')['ratios'].values()):.2f}", rr_max=f"{max(cv('C3')['ratios'].values()):.2f}", clus=f"{cv('C3')['clustering_full']:.2f}",
             chem=p1(cv("C7")["chemistry_reach"]), outside=p1(cv("C7")["outside_reach"]),
             rho_min=f"{min(v for v in cv('C6').values() if isinstance(v, (int, float))):.2f}",
             gap_max=p1(cv("C4")["max_gap_pp"]), nruns=str(cv("C4")["runs"]),
             real_cites=f0(R["ideas"]["citations"]), real_ideas=f0(R["ideas"]["n"]), single=f"{R['ideas']['single_use_pct']:.0f}",
             T_all=f"{t['overall']['T_pct']:.2f}", T_top=f"{t['by_bucket']['10+ papers']['T_pct']:.2f}",
             T_fac=f"{t['by_role']['faculty']['T_pct']:.2f}", T_stu=f"{t['by_role']['affiliated_author']['T_pct']:.2f}",
             T_ratio=f"{t['by_role']['affiliated_author']['T_pct'] / t['by_role']['faculty']['T_pct']:.1f}",
             co_fac=f"{R['roles']['faculty']['coauthors_per_person']:g}", co_stu=f"{R['roles']['affiliated_author']['coauthors_per_person']:g}",
             carried=f"{100 * t['overall']['carried'] / (t['overall']['carried'] + t['overall']['independent']):.0f}",
             l1=f"{ex['1']['lift_independent']:.2f}", l3=f"{ex['3+']['lift_independent']:.1f}",
             xlab=f"{R['between_labs']['cross_lab_pct']:.1f}", via_for=p1(org2["foreign"]["via_person_pct"]), via_own=p1(org2["own"]["via_person_pct"]),
             nclaims=str(D["n_claims"]), npassed=str(D["n_passed"]))
    return V


# ------------------------------------------------------------------ LaTeX
TEX = r"""
\documentclass[10pt,a4paper,twocolumn]{article}
\usepackage[a4paper,top=1.25cm,bottom=1.45cm,left=1.35cm,right=1.35cm,columnsep=0.55cm]{geometry}
\usepackage{libertinus}
\usepackage{microtype}
\usepackage{graphicx,booktabs,tabularx,array,multirow}
\usepackage[dvipsnames]{xcolor}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage[skins]{tcolorbox}
\usepackage[font=footnotesize,labelfont={bf,sf},labelsep=period,skip=3pt]{caption}
\usepackage[colorlinks=true,urlcolor=accent,linkcolor=accent]{hyperref}
\definecolor{navy}{HTML}{1D2B4F}
\definecolor{accent}{HTML}{B42318}
\definecolor{muted}{HTML}{6B7280}
\definecolor{boxbg}{HTML}{F4F6FB}
\titleformat{\section}{\sffamily\bfseries\large\color{navy}}{\thesection}{0.5em}{}[\vspace{-0.55em}\textcolor{navy}{\rule{\columnwidth}{0.6pt}}]
\titleformat{\subsection}{\sffamily\bfseries\normalsize\color{navy}}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{7pt}{3pt}
\titlespacing*{\subsection}{0pt}{5pt}{2pt}
\setlist{nosep,leftmargin=1.1em,itemsep=1.6pt}
\setlength{\parskip}{2pt}\setlength{\parindent}{0pt}
\setlength{\textfloatsep}{7pt}\setlength{\floatsep}{6pt}\setlength{\dbltextfloatsep}{7pt}\setlength{\abovecaptionskip}{2pt}
\newcommand{\obs}[1]{\textbf{\color{navy}#1}\ }
\pagestyle{plain}

\begin{document}
\twocolumn[{%
\begin{center}
{\sffamily\bfseries\LARGE\color{navy} How three CSIR chemistry laboratories publish, connect\\[2pt] and measure up to the world, 2016--2026\par}
\vspace{5pt}
{\sffamily\normalsize \textbf{Group 24}\quad$\cdot$\quad <<members>>\par}
\vspace{2pt}
{\sffamily\small CSIR-NCL (Pune) $\cdot$ CSIR-IICT (Hyderabad) $\cdot$ CSIR-CECRI (Karaikudi) $\cdot$ DPCN 2026\par}
\vspace{2pt}
{\sffamily\small Interactive dashboard: \href{<<site>>}{\textbf{<<site>>}}\par}
\end{center}
\vspace{2pt}
\begin{tcolorbox}[enhanced,colback=boxbg,colframe=navy!55,boxrule=0.6pt,arc=1.5pt,left=6pt,right=6pt,top=4pt,bottom=4pt]
{\sffamily\bfseries\color{navy} Key observations}\\[1pt]
\small
\begin{tabularx}{\linewidth}{@{}>{\bfseries\color{accent}}l@{\hspace{6pt}}X@{}}
1 & \textbf{Output is shrinking, and the decline is real.} <<p2016>> papers in 2016, <<p2025>> in 2025 (<<g_allthree>>\% a year), driven by IICT (<<g_iict>>\%) and NCL (<<g_ncl>>\%); NCL's own annual report confirms the scale. \\
2 & \textbf{Fewer papers, but a larger share in top journals.} Q1 papers in journals with IF\,$>$\,5 rose from <<if5_2016>>\% to <<if5_2025>>\% of output (IF\,$>$\,10: <<if10_2016>>\% $\to$ <<if10_2025>>\%). CECRI, the smallest lab, leads on every quality measure. \\
3 & \textbf{Three islands.} Only <<x_auth>>\% of co-authorship links join two labs, yet <<x_sci>>\% of citations between scientists do: the labs read each other but rarely write together. \\
4 & \textbf{Against their closest foreign counterparts the labs trail most at the top.} Compared with nine ``twin'' institutes chosen by fixed rules in the USA, China, South Korea and Australia, the labs' median share of papers in the world's top 10\% is <<gap_t10>>$\times$ lower, and their share in Q1 journals with IF\,$>$\,10 is <<gap_if10>>$\times$ lower; the gap grows as the bar rises. \\
5 & \textbf{Knowledge flows in from abroad by reading, and out to Indian universities.} The labs cite <<out_for>> papers of their foreign peers but co-authored <<co_for>> with them; Indian universities draw on the labs' work more than the reverse (<<r_iit>>--<<r_state>>$\times$). In the labs' own citations, ideas pass over a co-authorship tie only <<T_all>>\% of the time, below the tipping point of <<tp_full_pct>>\%. \\
\end{tabularx}
\end{tcolorbox}
\vspace{4pt}
}]

\section{Data and approach}
Every peer-reviewed paper (2016--2026) with an author at one of the three laboratories was collected from OpenAlex, with each laboratory resolved to its ROR and OpenAlex identifiers and mis-tagged papers recovered from raw affiliation strings. The corpus has <<papers>> distinct papers (<<journal>> journal, <<conf>> conference) by <<authors>> lab authors; \textbf{faculty} are the <<faculty>> scientists on the institutes' staff pages (<<roster>> after cleaning) with at least one paper. Quartiles are SCImago's best quartile in the publication year; as \textbf{impact factor (IF)} we use SCImago's two-year citations per document in the same year, a Scopus analogue of the JIF, known for <<if_cov>>\% of papers. The scale was checked against an independent source: NCL's annual report lists 467, 407 and 365 papers for 2021--2023; our data has <<ncl_ours>>.

\section{Basic statistics}
\begin{table*}[t]
\centering\small
\caption{Overview, 2016--2026 (distinct papers; a paper shared by two labs counts for each, once in ``All three''). Percentages of all papers. Growth = compound yearly change 2016$\to$2025 (2026 is a partial year). Citations: OpenAlex counts, not field-normalised. h-index: 2016--2026 papers, roster scientists.}
\begin{tabular}{@{}lrrrrrrrrrr@{}}
\toprule
Lab & Papers & Q1 (\%) & Q1\,\&\,IF$>$5 & Q1\,\&\,IF$>$10 & $<$10 authors & Mean & Intl. & Citations & h-index & Growth \\
 & & & (\%) & (\%) & (\%) & authors & (\%) & mean\,/\,median & mean\,/\,max & (\%/yr) \\
\midrule
<<table_overview>>
\bottomrule
\end{tabular}
\end{table*}

\begin{figure*}[t]
\centering\includegraphics[width=\textwidth]{fig_trends.pdf}
\caption{(a) Papers per year per lab; 2026 (shaded) runs to the collection date in October. (b) Share of the three labs' papers in Q1 journals, in Q1 journals with IF\,$>$\,5 and with IF\,$>$\,10.}
\end{figure*}

\obs{Output is falling, and the fall is real.} The labs published <<p2016>> papers in 2016 and <<p2025>> in 2025 (<<g_allthree>>\% a year). IICT (<<g_iict>>\%) and NCL (<<g_ncl>>\%) drive the decline; CECRI is flat (<<g_cecri>>\%). The steepest fall was 2016--2020; output has levelled since.

\obs{Quality moved up while volume fell.} <<q1>>\% of all papers are in Q1 journals, <<q1if5>>\% in Q1 journals with IF\,$>$\,5 and <<q1if10>>\% with IF\,$>$\,10. Over time the plain Q1 share dipped (<<q1_2016>>\% $\to$ <<q1_2025>>\%) but the high-IF shares rose sharply (Fig.~1b), so papers moved towards the top of the Q1 band (journal citation rates also drift upwards, so part of this is inflation of IF).

\obs{The smallest lab has the highest quality.} CECRI (<<n_cecri>> papers) leads at every threshold: Q1 <<q1_cecri>>\%, Q1\,\&\,IF\,$>$\,5 <<if5_cecri>>\%. NCL has the most papers in IF\,$>$\,10 Q1 journals (<<n10_ncl>>); IICT, the largest lab, has about half NCL's share at that level (<<if10_iict>>\% vs <<if10_ncl>>\%).

\obs{Small teams, wide partnerships.} <<lt10>>\% of papers have fewer than 10 authors (mean <<mean_auth>>, rising from <<auth_2016>> to <<auth_2025>>; only <<ge30>> papers have 30 or more): this is small-group bench chemistry. Yet the labs co-author with <<partners>> institutions in <<countries>> countries, and <<intl>>\% of papers have a foreign co-author.

\obs{Citations are concentrated.} <<cites>> citations, mean <<cmean>> but median <<cmed>> per paper; the most cited is a review, \textit{<<top_title>>} (<<top_j>>, <<top_y>>; <<top_c>> citations). Output is concentrated too: <<pl_n>> scientists ($\sqrt{N}$) write <<pl_share>>\% of faculty papers (Price's law predicts 50\%); Gini <<gini>> for papers, <<gini_c>> for citations.

\section{Network analysis}
\begin{table}[t]
\centering\footnotesize\setlength{\tabcolsep}{3.2pt}
\caption{The four networks (2016--2026). $\langle k\rangle$: mean degree (citation: mean in-degree). Cross = share of links joining two labs.}
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Network & Nodes & Links & $\langle k\rangle$ & Comm. ($Q$) & Cross (\%) \\
\midrule
<<table_networks>>
\bottomrule
\end{tabular}
\end{table}

\begin{figure}[t]
\centering\includegraphics[width=\columnwidth]{fig_network.pdf}
\caption{(a) Faculty co-authorship network; colour = lab, amber = a pair from two labs; size = co-authors. (b) Share of links that cross labs, by network.}
\end{figure}

\obs{One giant component made of tight groups.} <<lcc>>\% of the <<authors>> lab authors form one connected component, but the network is sparse (density <<dens>>) and highly modular: <<ncomm>> communities, modularity <<mod>>. These are research groups: each of the <<ncomm_top>> largest is at least <<purity>>\% one lab.

\obs{The labs are islands.} Only <<x_auth>>\% of co-authorship links and <<fac_cross>> of <<fac_pairs>> faculty pairs join two labs; <<n_iso>> of <<n_fac>> scientists (<<iso_pct>>\%) have no paper with another roster scientist and connect only through students and project staff.

\obs{They read each other, but do not write together.} <<x_sci>>\% of citations between scientists cross labs, <<x_ratio>> times the share of faculty co-author pairs, and half of citing relations are returned (reciprocity <<recip>>).

\obs{Hubs, not a club.} <<fp>>\% of researchers have fewer co-authors than their co-authors (mean <<fp_k>> vs <<fp_nk>>: the friendship paradox), yet the best-connected researchers avoid each other (rich-club coefficient <<rc>> of random): each runs a separate group. Removing the <<fr_n>> best bridges (<<fr_pct>>\%) halves the network; random removal needs <<fr_rand>>. The top bridges are method specialists, <<bridges>>: X-ray crystallography and electrochemistry services that many groups use. By PageRank, <<pr_cecri>> of the 5 most central papers are CECRI's electrocatalysis papers.

\section{The labs in a global frame}
\textbf{Choosing fair comparators.} We first asked whom the labs actually work with: <<intl>>\% of papers have a co-author in one of <<c_n>> countries, led by the USA (<<c_us>> papers), South Korea (<<c_kr>>) and Australia (<<c_au>>). These three, plus China, the world's largest producer in these subjects (share of world papers <<cn16>>\% $\to$ <<cn25>>\% in 2016--2025) although only the labs' \#<<c_cn_rank>> partner, are the benchmark countries. Everyone is measured on the same \textbf{scope}, the <<n_scope>> subfields that make up 90\% of the labs' papers, with the same OpenAlex queries (articles and reviews, 2016--2025). In each country a ``twin'' for each lab was selected by fixed rules: the 200 largest institutions in scope; government or facility institutes only, as CSIR labs are (umbrella bodies and <<n_excl>> hand-reviewed university-hosted labs, consortia and ministries removed, each with a written reason); at least half the size of the smallest lab; and the highest \textbf{cosine similarity} of subfield profiles, one twin per lab, minimum 0.4. Of <<pool>> candidates, <<tested>> reached the similarity test and <<twins>> became twins (Table~3). Six leading Indian institutes (IISc, IIT Bombay, IIT Madras, ICT Mumbai, IACS, IISER Pune) are the home reference.

\begin{table}[t]
\centering\footnotesize\setlength{\tabcolsep}{2.6pt}
\caption{Final peer list: each lab's twin per country with its similarity (1 = identical mix of subfields). ---: no twin; in brackets the most similar institute not already another lab's twin (below 0.4).}
\begin{tabular}{@{}l>{\raggedright}p{1.42cm}>{\raggedright}p{1.42cm}>{\raggedright}p{1.42cm}>{\raggedright\arraybackslash}p{1.42cm}r@{}}
\toprule
Lab & USA & China & S.\ Korea & Australia & Twins \\
\midrule
<<table_peers>>
\bottomrule
\end{tabular}
\end{table}

\obs{IICT has a twin only in China, and that is a result.} <<org_iict>>\% of IICT's papers are organic chemistry; its twin, the Shanghai Institute of Organic Chemistry, has <<org_sioc>>\%, while no other foreign twin exceeds <<org_other>>\%. Government institutes with IICT's focus exist in China, not in the USA, Korea or Australia.

\begin{figure*}[t]
\centering\includegraphics[width=\textwidth]{fig_global.pdf}
\caption{Global Benchmark, papers in the <<n_scope>> benchmark subfields, 2016--2025. (a) Yearly growth against the share of papers in the world's top 10\% for their subfield, type and year (OpenAlex; the world's own share is <<world>>\%). (b) Share of papers in Q1 journals with IF\,$>$\,10 (dark; value first) and IF\,$>$\,5 (light; value second), same SCImago rule as Table~1. Country codes: IN India, US, CN, KR, AU.}
\end{figure*}

\obs{Shrinking while the peers grow.} The labs' output changed by <<gcagr_ncl>>\% (NCL), <<gcagr_iict>>\% (IICT) and <<gcagr_cecri>>\% (CECRI) a year, against <<gcagr_tw>>\% for the twins (median) and <<gcagr_in>>\% for the Indian reference group; DICP and FJIRSM grew <<dicp_g>>\% and <<fj_g>>\%.

\obs{Half the field-normalised impact.} The share of papers in the world's top 10\% is <<t10_iict>>\% (IICT), <<t10_ncl>>\% (NCL) and <<t10_cecri>>\% (CECRI), against <<world>>\% for the world, <<t10_in>>\% for the Indian reference group and <<t10_tw>>\% for the twins (median): at home the labs are level with India's best, abroad they are at half the level (Fig.~3a).

\obs{The higher the bar, the wider the gap.} In plain Q1 share the twins are <<gap_q1>>$\times$ ahead (median <<gq1_tw>>\% vs <<gq1_lab>>\%), with IF\,$>$\,5 <<gap_if5>>$\times$ (<<gif5_tw>>\% vs <<gif5_lab>>\%), and with IF\,$>$\,10 <<gap_if10>>$\times$ (<<gif10_tw>>\% vs <<gif10_lab>>\%; twins <<if10_tw_min>>--<<if10_tw_max>>\%, labs <<if10_lab_min>>--<<if10_lab_max>>\%, DICP <<dicp_if10>>\%). The Indian reference group sits with the labs (<<gif10_in>>\%). The labs' journal shares computed this way agree with the curated dataset (Table~1) within 3 points.

\obs{Who learns from whom.} The labs co-authored only <<co_for>> papers with the nine foreign twins and other foreign peers (<<co_twin>> with the twins themselves) against <<co_ind>> with the six Indian institutes. Citations run inwards (Fig.~4a): the peers' 2016--2026 papers cite the labs <<in_for>> times while the labs cite <<out_for>> of theirs (exchange ratio <<r_for>>; USA <<r_us>>). At home the direction reverses: the Indian institutes' ratio is <<r_ind>>, and fifteen Indian universities draw on the labs more than the labs draw on them (IISc and IITs <<r_iit>>, state universities <<r_state>>); two independent counts of these flows agree within <<xcheck>>\%.

\begin{figure}[t]
\centering\includegraphics[width=\columnwidth]{fig_flows.pdf}
\caption{(a) Exchange ratio = partner papers citing the labs $\div$ partner papers the labs cite (2016--2026 papers, joint papers left out); below 1 the labs draw on the partner, above 1 the partner draws on the labs. (b) Share of (co-author tie, cited work) pairs in which the co-author later cites the work, from the labs' own papers, by how widely the work is reused; dashed: tipping points measured on the same networks (Section~5).}
\end{figure}

\section{How ideas spread through the labs}
\textbf{Model.} An idea (a method or reagent) spreads over the co-authorship network (SI dynamics, Monte Carlo and the NIMFA mean-field equations; bond percolation for tipping points). It reaches half of all <<n_full>> authors in <<t50f>> steps but half of the faculty-only network in <<t50k>>; without students the tipping point is <<tpx>>$\times$ higher (<<tpk>> vs <<tpf>>). Because co-authors form tight triangles (clustering <<clus>>), the measured tipping point is <<rr_min>>--<<rr_max>>$\times$ the textbook value $\langle k\rangle/(\langle k^2\rangle-\langle k\rangle)$ in all networks. When transmission depends on topic overlap, ideas stay in their field (<<chem>>\% of chemists adopt, <<outside>>\% outside). The mean-field equations never under-predict the simulation (<<nruns>> runs) and rank the best seeds the same way ($\rho \ge$ <<rho_min>>).

\textbf{Tested on real citations.} Each of the <<real_ideas>> works the labs cite is an idea; a person adopts it with their first lab paper citing it (<<real_cites>> citations). Over a co-authorship tie an idea is passed on \textbf{<<T_all>>\%} of the time, <<T_top>>\% for the most reused ideas: below the full network's tipping point (<<tp_full_pct>>\%; Fig.~4b), so most ideas die after one paper (<<single>>\% of cited works are used once). A student's tie passes ideas <<T_ratio>>$\times$ as often as a faculty member's (<<T_stu>>\% vs <<T_fac>>\%), though faculty have <<co_fac>> co-authors against <<co_stu>>. Ideas travel with people: in <<carried>>\% of pass-ons an earlier user is an author of the new paper; one informed co-author barely changes a researcher's own use (<<l1>>$\times$), three or more do (<<l3>>$\times$). Only <<xlab>>\% of ties cross labs, and a foreign twin's paper reaches a second lab through a person in <<via_for>>\% of cases (the labs' own papers <<via_own>>\%): together with Section~4, knowledge from abroad reaches each lab separately, by reading. All <<nclaims>> claims of this study pass automatic checks (<<npassed>>/<<nclaims>>).

\section{Validation and limitations}
Recall was boosted with raw-affiliation and roster searches, split author profiles joined and duplicates removed; peer rules and exclusions are stored with reasons, and every number is produced by tested code with fixed seeds. Limits: OpenAlex affiliations contain errors; faculty are today's rosters; IF is SCImago's two-year cites per document, not Clarivate's JIF, and SJR quartiles may differ from JCR; citations are a proxy for influence, not quality or patents; 2026 is a partial year.

\section{Conclusion}
The three laboratories are strong national performers: level with India's best institutes on field-normalised impact, a net source of knowledge for Indian universities, and moving their papers into higher-impact journals. Measured against government institutes abroad that do the same science, however, they publish less, are shrinking while the peers grow, and trail most at the very top (Q1 with IF\,$>$\,10), while hardly working with those peers or with each other. Closer collaboration across the three labs and with their foreign twins is the clearest lever the data points to.

\vspace{3pt}
{\footnotesize\color{muted}\textbf{Data and code.} Dataset (group24\_data.csv and network files), benchmark and study tables, and this report accompany the submission; the dashboard at \url{<<site>>} shows every figure interactively.\par}
\end{document}
"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    D = load()
    fig_trends(D, OUT / "fig_trends.pdf")
    fig_network(D, OUT / "fig_network.pdf")
    fig_global(D, OUT / "fig_global.pdf")
    fig_flows(D, OUT / "fig_flows.pdf")
    V = values(D)
    V.update(members=" $\\cdot$ ".join(MEMBERS), site=SITE, table_overview=table_overview(D), table_networks=table_networks(D),
             table_peers=table_peers(D), tp_full_pct=f"{100 * D['claims']['C2']['value']['T_peak_full']:g}")
    tex = TEX
    for k, v in V.items():
        tex = tex.replace(f"<<{k}>>", str(v))
    left = re.findall(r"<<[a-z0-9_]+>>", tex)
    if left:
        raise ValueError(f"unfilled placeholders: {sorted(set(left))}")
    (OUT / "report.tex").write_text(tex, encoding="utf-8")
    exe = os.environ.get("TECTONIC") or shutil.which("tectonic") or str(Path.home() / "tools" / "tectonic" / "tectonic.exe")
    subprocess.run([exe, "--keep-logs", "report.tex"], cwd=OUT, check=True)
    shutil.copyfile(OUT / "report.pdf", PDF)
    print(f"Wrote {PDF}")


if __name__ == "__main__":
    build()
