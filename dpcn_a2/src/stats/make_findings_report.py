"""Findings report (4 pages, A4 PDF): basic statistics and network analysis of the three labs.

Every number is read from stats/tables/ (and data/final/ for the faculty graph layout); nothing is typed in.
Writes stats/report/findings/{report.html, fig_trends.png, fig_networks.png} and
stats/report/24_CSIR_findings_report.pdf (rendered with headless Chrome/Chromium if available).

    python -m src.stats.make_findings_report
"""

import shutil
import subprocess
from html import escape
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from src.stats.networks import faculty_coauthor_graph, faculty_papers

T = Path("stats/tables")
OUT = Path("stats/report/findings")
PDF = Path("stats/report/24_CSIR_findings_report.pdf")
LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
ALL = "Group 24 Combined"
COL = {"CSIR-IICT": "#2B5C8F", "CSIR-NCL": "#2E7D32", "CSIR-CECRI": "#D95F02", ALL: "#4b3f8f"}
SHORT = {"CSIR-IICT": "IICT", "CSIR-NCL": "NCL", "CSIR-CECRI": "CECRI", ALL: "All three"}


def t(name, **kw):
    return pd.read_csv(T / f"{name}.csv", **kw)


def pct(a, b, d=1):
    return round(a / b * 100, d) if b else 0.0


def f0(x):
    return f"{int(round(x)):,}"


# ------------------------------------------------------------------ data
def load():
    D = {}
    ov = t("phase2_overview").set_index("institution")
    D["ov"] = ov
    D["oy"] = t("phase2_overview_by_year")
    D["trend"] = t("publication_trend")
    q = t("quartile_distribution")
    D["q"] = q[q["period"] == "2016-2026 Overall"].set_index("institution")
    D["qy"] = q[q["period"] != "2016-2026 Overall"]
    cs = t("citation_summary")
    D["cit"] = cs[cs["period"] == "2016-2026 Overall"].set_index("institution")
    D["h"] = t("h_index_summary").set_index("institution")
    D["hd"] = t("h_index_distribution")
    D["tj"] = t("top_journals")
    D["tc"] = t("top_cited_papers")
    D["ra"] = t("research_areas_field")
    D["dept"] = t("department_performance")
    D["fac"] = t("faculty_performance")
    ns = t("network_summary")
    D["ns"] = {(r.network, r.metric): r.value for r in ns.itertuples()}
    D["fbtw"] = t("network_faculty_top_betweenness")
    D["abtw"] = t("network_authorship_top_betweenness")
    D["pr"] = t("network_citation_pagerank_top10")
    D["comm"] = t("network_authorship_communities")
    D["acm"] = t("network_authorship_collab_matrix").set_index("institution")
    D["cfm"] = t("network_citation_flow_matrix").set_index("source_inst")
    D["ind"] = t("indian_connections_summary").set_index("institution")
    D["gs"] = t("global_summary")
    D["world"] = t("global_world_baseline").set_index("period")
    D["fm"] = pd.read_csv("data/final/faculty_master.csv")
    return D


def nsv(D, net, metric):
    return float(D["ns"][(net, metric)])


def cross_shares(D):
    acm, cfm = D["acm"], D["cfm"]
    a_tot = acm.values.sum() / 2 + sum(acm.at[l, l] for l in LABS) / 2  # diagonal once, off-diagonal pairs once
    a_cross = sum(acm.at[a, b] for i, a in enumerate(LABS) for b in LABS[i + 1:])
    c_tot = cfm.values.sum()
    c_cross = c_tot - sum(cfm.at[l, l] for l in LABS)
    return {
        "Co-authorship, all lab authors (links)": pct(a_cross, a_tot),
        "Co-authorship, faculty only (pairs)": pct(nsv(D, "faculty_coauthorship", "cross-lab co-author pairs"),
                                                    nsv(D, "faculty_coauthorship", "co-author pairs (unique edges)")),
        "Citations between papers (links)": pct(c_cross, c_tot),
        "Citations between scientists (edges)": pct(nsv(D, "faculty_citation", "cross-lab citation edges"),
                                                    nsv(D, "faculty_citation", "directed edges (scientist A cites scientist B)")),
    }, (a_cross, a_tot, c_cross, c_tot)


# ------------------------------------------------------------------ figures
def fig_trends(D, path):
    tr, oy = D["trend"], D["oy"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.1), dpi=200)
    for lab in LABS:
        s = tr[tr["institution"] == lab]
        ax[0].plot(s["year"], s["papers"], marker="o", ms=3, lw=1.8, color=COL[lab], label=SHORT[lab])
    ax[0].axvspan(2025.5, 2026.5, color="#999", alpha=0.15, lw=0)
    ax[0].text(2026, ax[0].get_ylim()[1] * 0.96, "2026\npartial", ha="center", va="top", fontsize=7, color="#555")
    ax[0].set_title("(a) Papers per year", fontsize=9, loc="left")
    ax[0].set_ylabel("distinct papers", fontsize=8)
    ax[0].legend(fontsize=7, frameon=False, ncol=3, loc="upper right", bbox_to_anchor=(0.88, 1.0))
    c = oy[oy["institution"] == ALL].sort_values("year")
    for col, lab, st in (("q1_papers", "Q1", "-"), ("q1_if_gt5", "Q1 & IF > 5", "--"), ("q1_if_gt10", "Q1 & IF > 10", ":")):
        ax[1].plot(c["year"], c[col] / c["papers"] * 100, st, marker="o", ms=3, lw=1.8, color="#333", label=lab)
    ax[1].axvspan(2025.5, 2026.5, color="#999", alpha=0.15, lw=0)
    ax[1].set_title("(b) Share of all three labs' papers, by year", fontsize=9, loc="left")
    ax[1].set_ylabel("% of papers", fontsize=8)
    ax[1].legend(fontsize=7, frameon=False, loc="center left", bbox_to_anchor=(0.0, 0.66))
    for a in ax:
        a.tick_params(labelsize=7)
        a.set_xticks(range(2016, 2027, 2))
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_networks(D, shares, path):
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    G = faculty_coauthor_graph(faculty_papers(ext, fm), fm)
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    pos = nx.spring_layout(H, seed=24, k=0.18, iterations=200, weight=None)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.0), dpi=200, gridspec_kw={"width_ratios": [1.15, 1]})
    cross = [(u, v) for u, v in H.edges if H.nodes[u]["lab"] != H.nodes[v]["lab"]]
    within = [(u, v) for u, v in H.edges if H.nodes[u]["lab"] == H.nodes[v]["lab"]]
    nx.draw_networkx_edges(H, pos, edgelist=within, ax=ax[0], width=0.4, edge_color="#9aa5b1", alpha=0.6)
    nx.draw_networkx_edges(H, pos, edgelist=cross, ax=ax[0], width=1.3, edge_color="#e0a100")
    deg = dict(H.degree())
    nx.draw_networkx_nodes(H, pos, ax=ax[0], node_size=[6 + 2.2 * deg[n] for n in H],
                           node_color=[COL[H.nodes[n]["lab"]] for n in H], linewidths=0.3, edgecolors="white")
    for lab in LABS:
        ax[0].scatter([], [], color=COL[lab], s=20, label=SHORT[lab])
    ax[0].plot([], [], color="#e0a100", lw=1.3, label="cross-lab pair")
    ax[0].legend(fontsize=7, frameon=False, loc="lower left", ncol=4, bbox_to_anchor=(0, -0.08))
    ax[0].set_title(f"(a) Faculty co-authorship, largest component ({H.number_of_nodes()} scientists, "
                    f"{H.number_of_edges()} pairs; size = co-authors)", fontsize=8, loc="left")
    ax[0].axis("off")
    names = list(shares)
    vals = [shares[n] for n in names]
    bars = ax[1].barh(range(len(names)), vals, color=["#7f8c9a", "#7f8c9a", "#b0763a", "#b0763a"])
    ax[1].set_yticks(range(len(names)))
    ax[1].set_yticklabels(names, fontsize=7)
    ax[1].invert_yaxis()
    for b, v in zip(bars, vals):
        ax[1].text(v + 0.3, b.get_y() + b.get_height() / 2, f"{v:.1f}%", va="center", fontsize=7)
    ax[1].set_xlabel("% of links that join two different labs", fontsize=8)
    ax[1].set_title("(b) Writing together vs reading each other", fontsize=8, loc="left")
    ax[1].tick_params(labelsize=7)
    ax[1].spines[["top", "right"]].set_visible(False)
    ax[1].set_xlim(0, max(vals) * 1.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return H


# ------------------------------------------------------------------ html
CSS = """
@page { size: A4; margin: 13mm 14mm 13mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Source Serif 4", "Georgia", serif; font-size: 9.6pt; line-height: 1.36; color: #1a1a1a; margin: 0; }
h1 { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 16pt; margin: 0 0 2pt; color: #1d2b4f; }
.sub { font-family: Arial, sans-serif; font-size: 8.4pt; color: #555; margin-bottom: 7pt; }
h2 { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 11pt; color: #1d2b4f; margin: 9pt 0 3pt;
     border-bottom: 1.2px solid #1d2b4f; padding-bottom: 1pt; }
h3 { font-family: Arial, sans-serif; font-size: 9.4pt; margin: 6pt 0 2pt; color: #333; }
p { margin: 2pt 0 4pt; }
ul { margin: 2pt 0 4pt 0; padding-left: 13pt; }
li { margin: 1.2pt 0; }
table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 7.9pt; margin: 3pt 0 4pt; }
th, td { padding: 2.2pt 4pt; border-bottom: 0.6px solid #d5d9e0; text-align: right; }
th { background: #eef1f6; color: #1d2b4f; font-weight: 600; vertical-align: bottom; }
td:first-child, th:first-child { text-align: left; }
tr.all td { font-weight: 600; background: #f7f7fb; }
.box { border: 1px solid #c9d1e3; background: #f5f7fb; padding: 5pt 8pt; margin: 4pt 0 6pt; }
.box ol { margin: 2pt 0; padding-left: 14pt; }
.cap { font-family: Arial, sans-serif; font-size: 7.6pt; color: #555; margin: 1pt 0 5pt; }
.fig img { width: 100%; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
.note { font-family: Arial, sans-serif; font-size: 7.5pt; color: #555; }
.pb { break-before: page; }
table.ins td, table.ins th { text-align: left; vertical-align: top; font-size: 7.2pt; line-height: 1.22; padding: 1.6pt 3.5pt; }
table.ins td:first-child { font-weight: 600; width: 16pt; }
table.ins td:nth-child(2) { width: 17%; }
table.ins td:nth-child(3) { width: 46%; }
table.ins { break-inside: auto; }
table.ins tr { break-inside: avoid; }
h2, h3 { break-after: avoid; }
table, .fig, .box { break-inside: avoid; }
.k { font-weight: 600; }
"""


def build_html(D, shares, counts, H):
    ov, q, cit, h, ind = D["ov"], D["q"], D["cit"], D["h"], D["ind"]
    oy, tr = D["oy"], D["trend"]
    rows = LABS + [ALL]
    gs = D["gs"].set_index("short")
    world = D["world"].at["2016-2025", "top10_pct"]
    comb = oy[oy["institution"] == ALL].set_index("year")
    tr_c = tr[tr["institution"] == ALL].set_index("year")
    cagr = {l: tr[tr["institution"] == l]["cagr_2016_2025"].iloc[0] for l in rows}
    a_cross, a_tot, c_cross, c_tot = counts
    peers = D["gs"].groupby("group")[["cagr_pct", "top10_pct"]].median()

    def qy(lab, y):
        r = D["qy"][(D["qy"]["institution"] == lab) & (D["qy"]["year"].astype(str) == str(y))]
        return float(r["q1_fraction_primary_pct"].iloc[0])

    def ifs(y, col):
        return pct(comb.at[y, col], comb.at[y, "papers"])

    # ---- Table 1: overview
    t1 = ["<table><tr><th>Lab</th><th>Active<br>faculty</th><th>Papers</th><th>Q1</th><th>Q1 &amp;<br>IF&nbsp;&gt;&nbsp;5</th>"
          "<th>Q1 &amp;<br>IF&nbsp;&gt;&nbsp;10</th><th>&lt;&nbsp;10<br>authors</th><th>≥&nbsp;10<br>authors</th>"
          "<th>≥&nbsp;30<br>authors</th><th>Mean<br>authors</th><th>Partner inst.<br>(Indian / foreign)</th>"
          "<th>Coun-<br>tries</th><th>Intl.<br>papers</th></tr>"]
    for l in rows:
        r = ov.loc[l]
        n = r["papers"]
        t1.append(
            f"<tr class='{'all' if l == ALL else ''}'><td>{SHORT[l]}</td><td>{f0(r['active_faculty'])}</td><td>{f0(n)}</td>"
            f"<td>{f0(r['q1_papers'])} ({pct(r['q1_papers'], n)}%)</td>"
            f"<td>{f0(r['q1_if_gt5'])} ({pct(r['q1_if_gt5'], n)}%)</td>"
            f"<td>{f0(r['q1_if_gt10'])} ({pct(r['q1_if_gt10'], n)}%)</td>"
            f"<td>{f0(r['papers_lt10_authors'])} ({pct(r['papers_lt10_authors'], n)}%)</td>"
            f"<td>{f0(r['papers_ge10_authors'])} ({pct(r['papers_ge10_authors'], n)}%)</td>"
            f"<td>{f0(r['papers_ge30_authors'])}</td><td>{r['mean_authors']:.2f}</td>"
            f"<td>{f0(r['collab_institutions'])}<br>({f0(r['collab_institutions_indian'])}&nbsp;/&nbsp;{f0(r['collab_institutions_foreign'])})</td>"
            f"<td>{f0(r['collab_countries'])}</td><td>{r['intl_papers_pct']:.1f}%</td></tr>")
    t1.append("</table>")

    # ---- Table 2: output, quality, impact
    t2 = ["<table><tr><th>Lab</th><th>Papers<br>2016</th><th>Papers<br>2025</th><th>Growth<br>/yr</th>"
          "<th>Q1 of ranked<br>journal papers</th><th>Quartile<br>coverage</th><th>Citations</th><th>Mean /<br>median</th>"
          "<th>Uncited</th><th>World top-10%<br>share (field-norm.)</th><th>h-index (2016–26)<br>mean / median / max</th></tr>"]
    for l in rows:
        s = tr[tr["institution"] == l].set_index("year")
        top10 = f"{gs.at[l, 'top10_pct']:.1f}%" if l in gs.index else "—"
        t2.append(
            f"<tr class='{'all' if l == ALL else ''}'><td>{SHORT[l]}</td><td>{f0(s.at[2016, 'papers'])}</td>"
            f"<td>{f0(s.at[2025, 'papers'])}</td><td>{cagr[l]:+.1f}%</td>"
            f"<td>{q.at[l, 'q1_fraction_primary_pct']:.1f}%</td><td>{q.at[l, 'quartile_coverage_pct']:.1f}%</td>"
            f"<td>{f0(cit.at[l, 'total_citations'])}</td><td>{cit.at[l, 'mean_citations']:.1f} / {cit.at[l, 'median_citations']:.0f}</td>"
            f"<td>{cit.at[l, 'uncited_share_pct']:.1f}%</td><td>{top10}</td>"
            f"<td>{h.at[l, 'mean_h_index']:.1f} / {h.at[l, 'median_h_index']:.0f} / {h.at[l, 'max_h_index']}</td></tr>")
    t2.append("</table>")

    # ---- facts used in prose
    hd = D["hd"]
    low_h = hd[(hd["institution"] == ALL) & (hd["bin_label"] == "0-4")]["share_pct"].iloc[0]
    ce = hd[hd["institution"] == "CSIR-CECRI"]
    ce_low = ce[ce["bin_lower"] < 5]["share_pct"].sum()
    ce_high = ce[ce["bin_lower"] >= 25]["share_pct"].sum()
    fac = D["fac"]
    top_h = fac.sort_values("h_index_corpus", ascending=False).head(3)
    tj = D["tj"]
    topj = {l: tj[(tj["institution"] == l)].sort_values("rank").head(2) for l in LABS}
    ra = D["ra"]
    ra_all = ra[ra["institution"] == ALL].sort_values("paper_count", ascending=False)
    ra_top = {l: ra[ra["institution"] == l].sort_values("paper_count", ascending=False).iloc[0] for l in LABS}
    dept = D["dept"].sort_values("papers", ascending=False).iloc[0]
    tc = D["tc"][D["tc"]["institution"] == ALL].head(3)
    ext_lab = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False,
                          usecols=["work_id", "institution"]).groupby("work_id")["institution"].agg(
        lambda s: "+".join(SHORT[x] for x in sorted(set(s))))
    comm = D["comm"]
    purity = (comm[["authors_iict", "authors_ncl", "authors_cecri"]].max(axis=1) / comm["authors"])
    fb, ab, pr = D["fbtw"], D["abtw"], D["pr"]
    pr5 = pr.head(5)
    pr_cecri = int(pr5["institutions"].str.contains("CECRI").sum())

    def ns(net, m):
        return nsv(D, net, m)

    import json
    cj = json.loads((T / "insights" / "11_claims.json").read_text(encoding="utf-8"))
    claims = {c["id"]: c["claim"] for c in (cj["claims"] if isinstance(cj, dict) else cj)}

    # ---- Table 3: networks
    t3 = f"""<table><tr><th>Network (2016–2026)</th><th>Nodes</th><th>Edges</th><th>Mean degree</th><th>Density</th>
<th>Largest component</th><th>Communities (modularity)</th><th>Cross-lab</th></tr>
<tr><td>Citation: paper → paper, both in corpus (directed)</td><td>{f0(ns('citation', 'nodes (papers with >= 1 in-corpus link)'))}</td>
<td>{f0(ns('citation', 'distinct citing-cited paper pairs'))}</td><td>in {ns('citation', 'mean in-degree (corpus papers)'):.2f} (max {f0(ns('citation', 'max in-degree'))})</td><td>—</td>
<td>{f0(ns('citation', 'largest weakly connected component (papers)'))} (weak)</td><td>—</td><td>{shares['Citations between papers (links)']:.1f}%</td></tr>
<tr><td>Co-authorship: all lab authors (undirected)</td><td>{f0(ns('authorship', 'authors (nodes)'))}</td>
<td>{f0(ns('authorship', 'co-author pairs (unique edges)'))}</td><td>{ns('authorship', 'mean degree (distinct co-authors)'):.2f}</td>
<td>{ns('authorship', 'density'):.4f}</td><td>{ns('authorship', 'largest component share pct'):.1f}%</td>
<td>{f0(ns('authorship', 'Louvain communities'))} ({ns('authorship', 'modularity'):.2f})</td><td>{shares['Co-authorship, all lab authors (links)']:.1f}%</td></tr>
<tr><td>Co-authorship: roster faculty only</td><td>{f0(ns('faculty_coauthorship', 'nodes (roster scientists with >= 1 paper)'))}</td>
<td>{f0(ns('faculty_coauthorship', 'co-author pairs (unique edges)'))}</td><td>{ns('faculty_coauthorship', 'mean degree (distinct faculty co-authors)'):.2f}</td>
<td>{ns('faculty_coauthorship', 'density'):.4f}</td><td>{f0(ns('faculty_coauthorship', 'largest connected component (scientists)'))} scientists</td>
<td>{f0(ns('faculty_coauthorship', 'Louvain communities (connected scientists)'))} ({ns('faculty_coauthorship', 'modularity'):.2f})</td><td>{shares['Co-authorship, faculty only (pairs)']:.1f}%</td></tr>
<tr><td>Citation: scientist → scientist (directed)</td><td>{f0(ns('faculty_citation', 'scientists citing or cited by another scientist'))}</td>
<td>{f0(ns('faculty_citation', 'directed edges (scientist A cites scientist B)'))}</td><td>—</td><td>{ns('faculty_citation', 'density'):.4f}</td>
<td>reciprocity {ns('faculty_citation', 'reciprocity'):.2f}</td><td>—</td><td>{shares['Citations between scientists (edges)']:.1f}%</td></tr></table>"""

    y0, y1 = 2016, 2025
    n_iso = int(ns('faculty_coauthorship', 'nodes (roster scientists with >= 1 paper)') - ns('faculty_coauthorship', 'scientists with >= 1 faculty co-author'))
    ncl_ar = "NCL's own 2023–24 annual report lists 467, 407 and 365 papers for 2021–2023 (docs/DATA_AUDIT_2026-11-11.md); our data has " + \
             ", ".join(str(int(tr[(tr['institution'] == 'CSIR-NCL') & (tr['year'] == y)]['papers'].iloc[0])) for y in (2021, 2022, 2023))

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Group 24 findings report</title><style>{CSS}</style></head><body>
<h1>Research output and collaboration of three CSIR chemistry labs, 2016–2026</h1>
<div class="sub">Group 24 · DPCN 2026 · CSIR-IICT (Hyderabad), CSIR-NCL (Pune), CSIR-CECRI (Karaikudi) ·
{f0(ov.at[ALL, 'papers'])} distinct papers ({f0(D['q'].at[ALL, 'total_journals'])} journal, {f0(ov.at[ALL, 'papers'] - D['q'].at[ALL, 'total_journals'])} conference) ·
OpenAlex, collected 13 Oct 2026 (2026 is a partial year) · quartiles: SCImago (SJR) · faculty: {f0(ov.at[ALL, 'active_faculty'])} roster scientists with ≥ 1 paper</div>

<div class="box"><span class="k">Main findings</span>
<ol>
<li><b>Output is falling, and the fall is real.</b> The three labs published {f0(tr_c.at[y0, 'papers'])} papers in {y0} and {f0(tr_c.at[y1, 'papers'])} in {y1}
({cagr[ALL]:+.1f}% a year). IICT ({cagr['CSIR-IICT']:+.1f}%/yr) and NCL ({cagr['CSIR-NCL']:+.1f}%/yr) drive it; CECRI is flat ({cagr['CSIR-CECRI']:+.1f}%/yr).
{ncl_ar}, so the scale matches.</li>
<li><b>Fewer papers, but more in top journals.</b> Q1 papers whose journal has IF&nbsp;&gt;&nbsp;5 rose from {ifs(y0, 'q1_if_gt5')}% of output in {y0} to {ifs(y1, 'q1_if_gt5')}% in {y1}
(IF&nbsp;&gt;&nbsp;10: {ifs(y0, 'q1_if_gt10')}% → {ifs(y1, 'q1_if_gt10')}%), while the plain Q1 share fell.</li>
<li><b>The smallest lab has the highest impact.</b> CECRI ({f0(ov.at['CSIR-CECRI', 'papers'])} papers) leads on every quality measure: Q1 {q.at['CSIR-CECRI', 'q1_fraction_primary_pct']:.1f}%,
Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;5 {pct(ov.at['CSIR-CECRI', 'q1_if_gt5'], ov.at['CSIR-CECRI', 'papers'])}%, and {gs.at['CSIR-CECRI', 'top10_pct']:.1f}% of papers in the world's top 10% for their field and year
(world: {world:.2f}%). IICT, the largest, is below the world level ({gs.at['CSIR-IICT', 'top10_pct']:.1f}%).</li>
<li><b>The three labs work as separate islands.</b> Only {shares['Co-authorship, all lab authors (links)']:.1f}% of co-authorship links and {shares['Citations between papers (links)']:.1f}% of
citation links join two labs; every large co-author community is ≥&nbsp;{purity.min() * 100:.0f}% one lab.</li>
<li><b>Scientists read each other far more than they write together.</b> {shares['Citations between scientists (edges)']:.1f}% of scientist-to-scientist citation edges cross labs,
against {shares['Co-authorship, faculty only (pairs)']:.1f}% of faculty co-author pairs.</li>
<li><b>The bridges are method specialists.</b> The most central people in the co-authorship networks are X-ray crystallographers and a computational chemist,
who appear on many groups' papers.</li>
</ol></div>

<h2>1. Overview of the three labs</h2>
<p class="cap"><b>Table 1.</b> Papers 2016–2026 (distinct; a paper shared by two labs counts for each lab and once in "All three"). Percentages are of all papers.
IF = SCImago "Cites/Doc (2 years)" of the journal in its quartile year — a Scopus-based analogue of the impact factor, not Clarivate's JIF
(IF known for {pct(ov.at[ALL, 'papers_with_if'], ov.at[ALL, 'papers'])}% of papers). Partner institutions: all OpenAlex institutions on the papers other than the three labs.</p>
{''.join(t1)}
<ul>
<li><b>Quality (Q1, Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;5, Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;10).</b> {pct(ov.at[ALL, 'q1_papers'], ov.at[ALL, 'papers'])}% of the cluster's papers are in Q1 journals
({q.at[ALL, 'q1_fraction_primary_pct']:.1f}% of journal papers with a known quartile). The ranking is the reverse of size: CECRI &gt; NCL &gt; IICT at every threshold.
At the top end NCL is strongest in absolute terms: {f0(ov.at['CSIR-NCL', 'q1_if_gt10'])} papers in Q1 journals with IF&nbsp;&gt;&nbsp;10,
against {f0(ov.at['CSIR-IICT', 'q1_if_gt10'])} for IICT, which is larger. IICT's share of Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;10 papers ({pct(ov.at['CSIR-IICT', 'q1_if_gt10'], ov.at['CSIR-IICT', 'papers'])}%) is about half of NCL's and CECRI's.</li>
<li><b>Team size (#authors).</b> {pct(ov.at[ALL, 'papers_lt10_authors'], ov.at[ALL, 'papers'])}% of papers have fewer than 10 authors and the mean is
{ov.at[ALL, 'mean_authors']:.1f}: this is small-group bench chemistry, not big-team science. Only {f0(ov.at[ALL, 'papers_ge30_authors'])} papers have 30 or more authors.
Teams are slowly growing: mean authors {comb.at[y0, 'mean_authors']:.2f} in {y0} → {comb.at[y1, 'mean_authors']:.2f} in {y1};
papers with ≥&nbsp;10 authors {f0(comb.at[y0, 'papers_ge10_authors'])} → {f0(comb.at[y1, 'papers_ge10_authors'])}.</li>
<li><b>Collaboration.</b> The labs co-author with {f0(ov.at[ALL, 'collab_institutions'])} institutions in {f0(ov.at[ALL, 'collab_countries'])} countries.
{ov.at[ALL, 'intl_papers_pct']:.1f}% of papers have a foreign co-author (CECRI {ov.at['CSIR-CECRI', 'intl_papers_pct']:.1f}%, NCL {ov.at['CSIR-NCL', 'intl_papers_pct']:.1f}%),
and {ind.at[ALL, 'indian_coauthor_pct']:.1f}% have another Indian institution. {ind.at[ALL, 'cites_indian_inst_pct']:.1f}% cite and
{ind.at[ALL, 'cited_by_indian_inst_pct']:.1f}% are cited by another Indian institution.</li>
</ul>

<h2>2. Output, journals and impact</h2>
<div class="fig"><img src="fig_trends.png"></div>
<p class="cap"><b>Figure 1.</b> (a) Distinct papers per year per lab. (b) Q1, Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;5 and Q1&nbsp;&amp;&nbsp;IF&nbsp;&gt;&nbsp;10 papers as a share of all papers of the three labs.
2026 (shaded) runs to 13 Oct. Source: publication_trend.csv, phase2_overview_by_year.csv.</p>
<p class="cap"><b>Table 2.</b> Output, journal quality, citations and faculty h-index. Growth = CAGR {y0}–{y1} (2026 excluded). Citations: OpenAlex counts on 13 Oct 2026, not field-normalised.
World top-10% share: OpenAlex citation-normalised percentile, papers in the benchmark's subject scope (Global Benchmark); the world value in the same subjects is {world:.2f}%.
h-index: in-corpus (2016–2026 papers at the lab), roster scientists with ≥ 1 paper.</p>
{''.join(t2)}
<ul>
<li><b>Trend.</b> The decline is steepest in 2016–2020 (IICT {f0(tr[(tr.institution == 'CSIR-IICT') & (tr.year == 2016)].papers.iloc[0])} → {f0(tr[(tr.institution == 'CSIR-IICT') & (tr.year == 2020)].papers.iloc[0])})
and has levelled off since 2021. The 2026 bars are partial and are not a further fall.</li>
<li><b>Q1 over time.</b> The Q1 fraction of ranked journal papers fell at IICT ({qy('CSIR-IICT', 2016):.1f}% in 2016 → {qy('CSIR-IICT', 2025):.1f}% in 2025)
and NCL ({qy('CSIR-NCL', 2016):.1f}% → {qy('CSIR-NCL', 2025):.1f}%) and held at CECRI ({qy('CSIR-CECRI', 2016):.1f}% → {qy('CSIR-CECRI', 2025):.1f}%).
At the same time more papers went to high-IF Q1 journals (Fig. 1b). Journals' citation rates also grow over time, so part of this rise may be general inflation of IF;
read it as a shift towards the top of the Q1 band rather than a measured quality gain.</li>
<li><b>Citations.</b> {f0(cit.at[ALL, 'total_citations'])} citations, mean {cit.at[ALL, 'mean_citations']:.1f} and median {cit.at[ALL, 'median_citations']:.0f} per paper: a few highly cited papers
pull the mean up. {cit.at[ALL, 'uncited_share_pct']:.1f}% are uncited, mostly 2025–26 papers that have had no time to be cited. Raw means favour older papers and
fast-citing fields (energy, materials), so the field-normalised top-10% share is the fair comparison: only CECRI is clearly above the world level.</li>
<li><b>Most-cited papers.</b> The top three are reviews or perspectives:
{'; '.join(f"{escape(r.title[:70])}{'…' if len(r.title) > 70 else ''} (<i>{escape(r.journal_name)}</i> {r.year}, {ext_lab.get(r.work_id, '')}, {f0(r.citations)})" for r in tc.itertuples())}.</li>
<li><b>Journals.</b> Output is spread thin: no journal carries more than {tj[tj['institution'] == ALL]['share_pct'].max():.1f}% of the cluster's papers. The most-used venue for IICT and NCL is
<i>{escape(topj['CSIR-IICT'].iloc[0]['journal_name'])}</i> ({topj['CSIR-IICT'].iloc[0]['quartile']}), a high-volume mid-tier journal; CECRI's top two are Q1
(<i>{escape(topj['CSIR-CECRI'].iloc[0]['journal_name'])}</i>, <i>{escape(topj['CSIR-CECRI'].iloc[1]['journal_name'])}</i>).</li>
<li><b>Research areas</b> (OpenAlex field of the primary topic): {', '.join(f"{r.field} {r.share_pct:.1f}%" for r in ra_all.head(5).itertuples())}.
The labs differ: IICT is {ra_top['CSIR-IICT'].field} ({ra_top['CSIR-IICT'].share_pct:.1f}%), CECRI {ra_top['CSIR-CECRI'].field} ({ra_top['CSIR-CECRI'].share_pct:.1f}%) and energy,
NCL the broadest ({ra_top['CSIR-NCL'].field} {ra_top['CSIR-NCL'].share_pct:.1f}%).</li>
<li><b>Faculty and departments.</b> {low_h:.1f}% of active scientists have an in-window h-index of 4 or less. CECRI is bimodal: {ce_low:.0f}% are at h&nbsp;&lt;&nbsp;5 and
{ce_high:.0f}% at h&nbsp;≥&nbsp;25 (only 26 of its scientists are matched). Highest h-indices: {', '.join(f"{r.name.replace('Dr. ', '').replace('Dr ', '')} ({SHORT[r.institution]}, {r.h_index_corpus})" for r in top_h.itertuples())}.
The most productive department is NCL's {escape(dept['department'])} ({f0(dept['papers'])} papers, {dept['q1_share_pct']:.1f}% Q1, mean h {dept['mean_faculty_h_index']:.1f}).</li>
</ul>

<h2 class="pb">3. Network analysis</h2>
<p class="cap"><b>Table 3.</b> The four networks. Citation network: links between two corpus papers (citation_network.csv restricted to the corpus). Co-authorship: every lab author
(students and project staff included) or roster faculty only (one node per scientist). Cross-lab = share of links joining two different labs. Papers with &gt; 30 authors are not dropped here.</p>
{t3}
<div class="fig"><img src="fig_networks.png"></div>
<p class="cap"><b>Figure 2.</b> (a) Faculty co-authorship network, largest connected component; colour = lab, amber = a pair from two labs. (b) Share of links that cross labs in each network.</p>

<h3>Co-authorship</h3>
<ul>
<li><b>One giant component, many tight groups.</b> {ns('authorship', 'largest component share pct'):.1f}% of the {f0(ns('authorship', 'authors (nodes)'))} lab authors are connected,
but the network is sparse (density {ns('authorship', 'density'):.4f}) and strongly modular: Louvain finds {f0(ns('authorship', 'Louvain communities'))} communities
({f0(ns('authorship', 'communities with >= 10 authors'))} with ≥&nbsp;10 authors), modularity {ns('authorship', 'modularity'):.2f}. These communities are research groups:
the {len(comm)} largest are each ≥&nbsp;{purity.min() * 100:.0f}% one lab (median {purity.median() * 100:.0f}%).</li>
<li><b>Labs are islands.</b> Of {f0(a_tot)} co-authorship links, {f0(a_cross)} ({shares['Co-authorship, all lab authors (links)']:.1f}%) join two labs.
Among faculty, {f0(ns('faculty_coauthorship', 'cross-lab co-author pairs'))} of {f0(ns('faculty_coauthorship', 'co-author pairs (unique edges)'))} pairs cross labs, and
{n_iso} of {f0(ns('faculty_coauthorship', 'nodes (roster scientists with >= 1 paper)'))} active scientists ({pct(n_iso, ns('faculty_coauthorship', 'nodes (roster scientists with >= 1 paper)'))}%)
have no paper with any other roster scientist: their links run through students and project staff, not through colleagues.
The faculty network has mean degree {ns('faculty_coauthorship', 'mean degree (distinct faculty co-authors)'):.1f}, clustering
{ns('faculty_coauthorship', 'average clustering (connected scientists)'):.2f} and {f0(ns('faculty_coauthorship', 'Louvain communities (connected scientists)'))} communities
(modularity {ns('faculty_coauthorship', 'modularity'):.2f}).</li>

<li><b>Who bridges.</b> Highest betweenness among all authors: {', '.join(f"{r.author.replace('Dr. ', '').replace('Dr ', '')} ({SHORT.get(r.institution, r.institution)}, {r.betweenness:.3f})" for r in ab.head(5).itertuples())}.
B. Sridhar, J.&nbsp;B. Nanubolu (IICT) and R.&nbsp;G. Gonnade (NCL) run X-ray crystallography; Kumar Vanka (NCL) is a computational chemist. Structure determination
and computation are services many groups need, so these people sit between otherwise separate groups (B. Sridhar's 329 papers are mostly middle-author).</li>
</ul>

<h3>Citations</h3>
<ul>
<li><b>Mostly within a lab.</b> {f0(ns('citation', 'nodes (papers with >= 1 in-corpus link)'))} of {f0(ns('citation', 'corpus papers with DOI'))} papers have at least one citation link to another corpus paper;
mean in-degree {ns('citation', 'mean in-degree (corpus papers)'):.2f}, maximum {f0(ns('citation', 'max in-degree'))}. Of {f0(c_tot)} links, {f0(c_cross)} ({shares['Citations between papers (links)']:.1f}%) cross labs
(IICT→NCL {f0(D['cfm'].at['CSIR-IICT', 'CSIR-NCL'])}, NCL→IICT {f0(D['cfm'].at['CSIR-NCL', 'CSIR-IICT'])}; CECRI sends {f0(D['cfm'].loc['CSIR-CECRI', ['CSIR-IICT', 'CSIR-NCL']].sum())} and receives {f0(D['cfm'].loc[['CSIR-IICT', 'CSIR-NCL'], 'CSIR-CECRI'].sum())}).</li>
<li><b>Reading crosses lab lines; writing does not.</b> Between scientists, {shares['Citations between scientists (edges)']:.1f}% of citation edges cross labs, {shares['Citations between scientists (edges)'] / shares['Co-authorship, faculty only (pairs)']:.0f} times the share of
faculty co-author pairs ({shares['Co-authorship, faculty only (pairs)']:.1f}%). Half of citing relations are returned (reciprocity {ns('faculty_citation', 'reciprocity'):.2f}).
The labs know each other's work but rarely publish together.</li>
<li><b>Most central papers.</b> By PageRank, {pr_cecri} of the top 5 corpus papers are CECRI's electrocatalysis papers (led by the {pr5.iloc[0]['year']} <i>{escape(pr5.iloc[0]['journal_name'])}</i>
water-splitting review). The smallest lab supplies the most-reused knowledge inside the cluster.</li>
</ul>

<h2>4. In a wider frame (Global Benchmark)</h2>
<p>Against similar institutes, the labs' median growth ({peers.at['CSIR lab', 'cagr_pct']:+.1f}%/yr) is the lowest of all groups: Indian peers {peers.at['India', 'cagr_pct']:+.1f}%,
Chinese twins {peers.at['China', 'cagr_pct']:+.1f}%, US twins {peers.at['USA', 'cagr_pct']:+.1f}%, Australian twins {peers.at['Australia', 'cagr_pct']:+.1f}% (median per group; CSIRO Manufacturing's {gs.at['CSIRO Manufacturing', 'cagr_pct']:+.1f}% is likely an attribution artefact). On impact the labs' median top-10% share
({peers.at['CSIR lab', 'top10_pct']:.1f}%) equals the Indian peers' ({peers.at['India', 'top10_pct']:.1f}%) but is about half of the Chinese ({peers.at['China', 'top10_pct']:.1f}%)
and US ({peers.at['USA', 'top10_pct']:.1f}%) twins. CECRI ({gs.at['CSIR-CECRI', 'top10_pct']:.1f}%) is the exception.</p>

{insights_html(D, claims)}

<h2>6. Limitations</h2>
<ul class="note">
<li>OpenAlex affiliations and author profiles contain errors (split profiles were joined, D-41).
Faculty = today's website rosters ({len(D['fm'])} entries, {(D['fm']['n_papers_corpus'] > 0).sum()} with papers); students and project staff count in paper but not faculty statistics.
Quartiles are SJR "best quartile" (Scopus-based; JCR may differ), 2025 values for 2026 papers; "IF" is SJR's two-year cites per document, not Clarivate's JIF.
Citations are as of 13 Oct 2026 and not field-normalised except the top-10% share; links to and from outside the corpus cover only Indian-affiliated papers.
2026 is partial; h-index is in-corpus (2016–2026); CORE ranks do not apply ({f0(ov.at[ALL, 'papers'] - D['q'].at[ALL, 'total_journals'])} conference papers).</li>
</ul>

</body></html>"""
    return html


INSIGHTS = [  # (number, file, question, what it means); answers are each study's own headline
    ("01", "01_friendship_paradox", "Do researchers' co-authors have more co-authors than they do?",
     "The network is built around hubs: a student or postdoc links to the cluster through a few heavily connected group leaders. "
     "Only {fac}% of faculty are in the paradox, because faculty are the hubs."),
    ("02", "02_rich_club", "Do the most-connected scientists collaborate mainly with each other?",
     "No. The best-connected people each lead their own group and seldom write together: there is no elite core, which matches "
     "the separate lab communities in Section 3."),
    ("03", "03_fragility", "How many researchers hold the cluster together?",
     "Robust to random loss, fragile to the loss of bridges. The top bridges are the crystallographers and Subrata Kundu (Section 3)."),
    ("04", "04_price_law", "Is output concentrated in a few scientists?",
     "Shares are of the {n} papers with a roster scientist, not of all papers. Concentrated, though less than Price's law predicts; "
     "citations are more unequal than papers: a few groups collect most of the impact."),
    ("05", "05_quartile_vs_impact", "Is a Q1 journal a reliable signal of a highly cited paper?",
     "Q1 is close to necessary but far from sufficient: most Q1 papers are not highly cited. Q1 shares (Table 1) measure where labs "
     "publish, not how much their papers are used. 'Top 10%' here is within the cluster and publication year (2016–2023 papers)."),
    ("06", "06_pagerank_vs_citations", "Are the papers most influential inside the cluster the world's most cited?",
     "Only partly. Some papers matter more to the labs' own later work than their global citation count shows."),
    ("07", "withdrawn/07_sleeping_beauties", "Which papers were ignored for years and then suddenly took off?",
     "Delayed recognition is rare: most late risers are short spikes. A 10-year window can only show short sleeps."),
    ("08", "08_covid_shock", "How much output did COVID cost, and did research shift?",
     "COVID did not cause the decline: output was already falling, and 2020–21 were above the pre-pandemic trend."),
    ("09", "09_brain_circulation", "How many scientists trained in India, worked abroad and came back, and did it change their research?",
     "About one in six are returnees, mostly from the US. Their citations are not measurably different; they co-author slightly more "
     "with foreign partners. Computed on 2 Nov 2026 from the OpenAlex career cache (not in this checkout); the classification is "
     "marked 'validation pending' in its output."),
    ("10", "withdrawn/10_succession_risk", "How much of each lab's output depends on scientists close to retirement?",
     "CECRI carries the largest retirement risk: about half its recent papers have no younger roster author. Age is estimated "
     "from the first publication year (no birth dates)."),
]


def insights_html(D, claims):
    import json
    rows = []
    for num, f, q, meaning in INSIGHTS:
        j = json.loads((T / "insights" / f"{f}.json").read_text(encoding="utf-8"))
        if f == "04_price_law":
            meaning = meaning.format(n=f0(j["metrics"]["total_faculty_papers"]))
        if f == "01_friendship_paradox":
            meaning = meaning.format(fac=f"{j['metrics']['faculty_share_paradox']:.0f}")
        rows.append(f"<tr><td>{num}</td><td><b>{escape(q)}</b></td><td>{escape(j['headline'])}</td><td>{escape(meaning)}</td></tr>")
    c11 = (f"{escape(claims['C12'].split('. 79%')[0])}. {escape(claims['C14'].split('. ')[0])}. "
           f"{escape(claims['C13'].split(' (')[0])}. {escape(claims['C15'].split(', and when')[0])}.")
    rows.append(f"<tr><td>11</td><td><b>How do ideas spread through the labs? (lead study, its own page)</b></td><td>{c11}</td>"
                "<td>Ideas travel with people, not along the network as a whole: most die after one use. Students and project staff carry "
                "them between groups. The labs learn from abroad by reading, each on its own.</td></tr>")
    wd_date = pd.Timestamp(json.loads((T / "insights" / "withdrawn" / "07_sleeping_beauties.json").read_text(encoding="utf-8"))
                           ["computed_at"]).strftime("%-d %b %Y")
    return ("<h2 class='pb'>5. The eleven insight studies</h2>"
            "<p class='cap'><b>Table 4.</b> The eleven insight studies, numbered by study id; 11, \"How Ideas Spread\", is the lead study with its own page. "
            "Answers are each study's own generated headline (stats/tables/insights/*.json), re-run on 21 Nov 2026 on the audited data "
            f"except 07, 09 and 10 (their OpenAlex caches are not in this checkout). 07 and 10 are as the website showed them before "
            f"their removal on 10 Nov 2026 (D-37), computed on {wd_date}, before the data audit "
            f"(stats/tables/insights/withdrawn/).</p>"
            "<table class='ins'><tr><th>#</th><th>Question</th><th>Answer (measured)</th><th>What it means</th></tr>"
            + "".join(rows) + "</table>")


def render_pdf(html_path: Path, pdf_path: Path) -> bool:
    for exe in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        if shutil.which(exe):
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={pdf_path.resolve()}", html_path.resolve().as_uri()],
                           check=True, capture_output=True, timeout=120)
            return True
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    D = load()
    shares, counts = cross_shares(D)
    fig_trends(D, OUT / "fig_trends.png")
    H = fig_networks(D, shares, OUT / "fig_networks.png")
    html = build_html(D, shares, counts, H)
    (OUT / "report.html").write_text(html, encoding="utf-8")
    ok = render_pdf(OUT / "report.html", PDF)
    print(f"Wrote {OUT / 'report.html'}" + (f" and {PDF}" if ok else " (no Chrome/Chromium found; PDF not rendered)"))


if __name__ == "__main__":
    main()
