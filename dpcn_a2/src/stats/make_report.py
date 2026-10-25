"""Statistics report (Task 2): stats/report/Group24_CSIR.pptx (10 slides) + PDF.

Every number on a slide is read from stats/tables/ (or data/final/ for dataset counts),
so the report always matches the dashboard, which reads the same tables. Speaker notes
on each slide name the source tables. Charts are native PowerPoint charts.

PDF export: LibreOffice (soffice) if available, otherwise Microsoft PowerPoint via COM
on Windows. If neither is available the PPTX is still written and a warning is logged.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from src.common.logging import get_logger

logger = get_logger("make_report")

T = Path("stats/tables")
OUT_DIR = Path("stats/report")
PPTX = OUT_DIR / "Group24_CSIR.pptx"
PDF = OUT_DIR / "Group24_CSIR.pdf"

LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
ALL = "Group 24 Combined"
COLLECTED = "13 Oct 2026"
SITE_URL = "https://prathm01s.github.io/dpcn_almost_stable/"

# Palette: deep ink base, institute colours shared with the dashboard
INK = RGBColor(0x1F, 0x2A, 0x37)
MUTED = RGBColor(0x5B, 0x67, 0x76)
LIGHT = RGBColor(0xF2, 0xF4, 0xF7)
LINE = RGBColor(0xD5, 0xDB, 0xE3)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
NAVY = RGBColor(0x14, 0x21, 0x3D)
NAVY_SOFT = RGBColor(0xC9, 0xD6, 0xEA)
AMBER = RGBColor(0xC9, 0x7C, 0x10)
SECONDARY_LINK = RGBColor(0x1F, 0x5F, 0xA8)
LAB_COLOR = {
    "CSIR-IICT": RGBColor(0x2B, 0x5C, 0x8F),
    "CSIR-NCL": RGBColor(0x2E, 0x7D, 0x32),
    "CSIR-CECRI": RGBColor(0xD9, 0x5F, 0x02),
}
Q_COLOR = {
    "Q1": RGBColor(0x0F, 0x4C, 0x5C), "Q2": RGBColor(0x3B, 0x8E, 0xA5),
    "Q3": RGBColor(0x9C, 0xC5, 0xD3), "Q4": RGBColor(0xD6, 0xE6, 0xEC),
    "Unranked": RGBColor(0xB8, 0xBE, 0xC6),
}
HEAD_FONT = "Cambria"
BODY_FONT = "Calibri"

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.55)
CONTENT_W = SLIDE_W - 2 * MARGIN


# --------------------------------------------------------------------------- helpers
def short(lab: str) -> str:
    return lab.replace("CSIR-", "")


def fmt(n) -> str:
    return f"{int(round(float(n))):,}"


def pct(x, d: int = 1) -> str:
    return f"{float(x):.{d}f}%"


def clip(s: str, n: int) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def signed(v: float) -> str:
    """+1.2% / −4.9% with a true minus sign, so the sign never wraps away from the number."""
    return ("+" if v >= 0 else "−") + f"{abs(v):.1f}%"


def dept_name(name: str) -> str:
    """Title-case ALL-CAPS roster names; keep mixed-case names as published."""
    small = {"and", "of", "for", "in", "the", "&"}
    name = name.strip()
    if name.lower().endswith(" division"):
        name = name[: -len(" division")]
    if name.isupper():
        return " ".join(w.lower() if w.lower() in small and i else w.capitalize() for i, w in enumerate(name.split()))
    return " ".join(w.lower() if w.lower() in small and i else w for i, w in enumerate(name.split()))


def doi_short(d: str) -> str:
    return d.replace("https://doi.org/", "") if d else "—"


def load(name: str, **kw) -> pd.DataFrame:
    return pd.read_csv(T / name, keep_default_na=False, **kw)


def emu(*vals):
    """Whole EMUs: PowerPoint rejects fractional coordinates (Length arithmetic yields floats)."""
    return tuple(Emu(int(round(v))) for v in vals)


def textbox(slide, x, y, w, h, paras: Sequence[Tuple], anchor=MSO_ANCHOR.TOP, name: Optional[str] = None):
    """paras: (text, size, bold, color[, bullet, align, font]) or list of runs [(text, size, bold, color)]."""
    x, y, w, h = emu(x, y, w, h)
    tb = slide.shapes.add_textbox(x, y, w, h)
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    first = True
    for para in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        runs = para if isinstance(para, list) else [para]
        opts = runs[0]
        bullet = len(opts) > 4 and opts[4]
        align = opts[5] if len(opts) > 5 else PP_ALIGN.LEFT
        p.alignment = align
        p.space_after = Pt(5 if bullet else 2)
        for r in runs:
            run = p.add_run()
            run.text = r[0]
            run.font.size = Pt(r[1])
            run.font.bold = bool(r[2])
            run.font.color.rgb = r[3]
            run.font.name = r[6] if len(r) > 6 and r[6] else BODY_FONT
        if bullet:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(Inches(0.2)))
            pPr.set("indent", str(-Inches(0.2)))
            bu = etree.SubElement(pPr, qn("a:buChar"))
            bu.set("char", "•")
    return tb


def rect(slide, x, y, w, h, fill, rounded=True, name=None):
    x, y, w, h = emu(x, y, w, h)
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, x, y, w, h)
    if rounded:
        shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp


def header(slide, n: int, title: str, message: str):
    textbox(slide, MARGIN, Inches(0.4), CONTENT_W - Inches(0.8), Inches(0.6),
            [(title, 28, True, INK, False, PP_ALIGN.LEFT, HEAD_FONT)], name="Title")
    textbox(slide, MARGIN, Inches(1.02), CONTENT_W, Inches(0.5), [(message, 14, False, MUTED)], name="Key message")
    textbox(slide, SLIDE_W - MARGIN - Inches(0.8), Inches(0.48), Inches(0.8), Inches(0.3),
            [(f"{n} / 10", 11, True, MUTED, False, PP_ALIGN.RIGHT)], name="Slide number")


def footer(slide, text: str):
    textbox(slide, MARGIN, SLIDE_H - Inches(0.42), CONTENT_W, Inches(0.25), [(text, 10, False, MUTED)], name="Source")


def stat(slide, x, y, w, h, value: str, label: str, color=INK, fill=LIGHT, label_color=MUTED, vsize=30):
    rect(slide, x, y, w, h, fill)
    pad = Inches(0.18)
    textbox(slide, x + pad, y + Inches(0.12), w - 2 * pad, h - Inches(0.2),
            [(value, vsize, True, color), (label, 12, False, label_color)], anchor=MSO_ANCHOR.MIDDLE)


def table(slide, x, y, w, df: pd.DataFrame, widths: List[float], size=11, header_fill=NAVY,
          row_h=0.3, align_right: Sequence[int] = (), colors: Optional[List[Optional[RGBColor]]] = None, name=None):
    rows, cols = len(df) + 1, len(df.columns)
    x, y, w = emu(x, y, w)
    shp = slide.shapes.add_table(rows, cols, x, y, w, Inches(row_h * rows))
    if name:
        shp.name = name
    tbl = shp.table
    tbl.first_row = True
    tbl.horz_banding = False
    total = sum(widths)
    for i, wd in enumerate(widths):
        tbl.columns[i].width = int(w * wd / total)
    for r in range(rows):
        tbl.rows[r].height = Inches(row_h)
        for c in range(cols):
            cell = tbl.cell(r, c)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            txt = str(df.columns[c]) if r == 0 else str(df.iat[r - 1, c])
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT if c in align_right else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = txt
            run.font.name = BODY_FONT
            run.font.size = Pt(size)
            cell.fill.solid()
            if r == 0:
                run.font.bold = True
                run.font.color.rgb = WHITE
                cell.fill.fore_color.rgb = header_fill
            else:
                run.font.color.rgb = INK
                cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT
                if colors and c == 0 and colors[r - 1] is not None:
                    run.font.bold = True
                    run.font.color.rgb = colors[r - 1]
    return tbl


def add_chart(slide, kind, x, y, w, h, data):
    x, y, w, h = emu(x, y, w, h)
    return slide.shapes.add_chart(kind, x, y, w, h, data)


def style_chart(chart, legend=True, size=11):
    chart.font.size = Pt(size)
    chart.font.name = BODY_FONT
    chart.font.color.rgb = MUTED
    chart.has_legend = legend
    if legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(size)
    try:
        va = chart.value_axis
        va.has_major_gridlines = True
        va.major_gridlines.format.line.color.rgb = LINE
        va.format.line.fill.background()
        va.tick_labels.font.size = Pt(size)
        ca = chart.category_axis
        ca.format.line.color.rgb = LINE
        ca.tick_labels.font.size = Pt(size)
        ca.has_major_gridlines = False
    except (ValueError, AttributeError):
        pass


def color_series(chart, colors: List[RGBColor]):
    for s, c in zip(chart.plots[0].series, colors):
        s.format.fill.solid()
        s.format.fill.fore_color.rgb = c
        s.format.line.fill.background()


def chart_title(chart, text: str):
    chart.has_title = True
    tf = chart.chart_title.text_frame
    tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = INK
            r.font.name = BODY_FONT


def link_run(slide, url: str):
    """Make every run whose text is the URL a clickable hyperlink."""
    for shape in slide.shapes:
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                for r in p.runs:
                    if r.text == url:
                        r.hyperlink.address = url


def link_run_in_footer(slide, url: str):
    """Split the footer so the URL at its end becomes a clickable run."""
    for shape in slide.shapes:
        if shape.name == "Source" and shape.text_frame.text.endswith(url):
            p = shape.text_frame.paragraphs[0]
            r0 = p.runs[0]
            r0.text = r0.text[: -len(url)]
            r = p.add_run()
            r.text = url
            r.font.size, r.font.name = r0.font.size, r0.font.name
            r.font.color.rgb = SECONDARY_LINK
            r.hyperlink.address = url


def notes(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text


# --------------------------------------------------------------------------- data
class Data:
    def __init__(self):
        self.trend = load("publication_trend.csv")
        self.trend_type = load("publication_trend_type.csv")
        self.quart = load("quartile_distribution.csv")
        self.cit = load("citation_summary.csv")
        self.hsum = load("h_index_summary.csv")
        self.hdist = load("h_index_distribution.csv")
        self.journals = load("top_journals.csv")
        self.topcited = load("top_cited_papers.csv")
        self.fields = load("research_areas_field.csv")
        self.depts = load("department_performance.csv")
        self.faculty = load("faculty_performance.csv")
        self.flow = load("citation_flow_summary.csv")
        self.top_citing = load("top_citing_indian_institutes.csv")
        self.partners = load("indian_partner_institutions.csv")
        self.conn = load("indian_connections_summary.csv")
        self.conf = load("conference_ranks.csv")
        self.ir = load("impact_ratio_summary.csv")
        self.ir_sjr = load("impact_ratio_vs_sjr.csv")
        self.net = load("network_summary.csv")
        self.pr = load("network_citation_pagerank_top10.csv")
        self.indeg = load("network_citation_indegree_distribution.csv")
        self.cflow = load("network_citation_flow_matrix.csv")
        self.deg = load("network_authorship_top_degree.csv")
        self.btw = load("network_authorship_top_betweenness.csv")
        self.comms = load("network_authorship_communities.csv")
        self.collab = load("network_authorship_collab_matrix.csv")
        self.main = pd.read_csv("data/final/group24_data.csv", dtype=str, keep_default_na=False)
        self.fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)

    def net_value(self, network: str, metric_prefix: str):
        row = self.net[(self.net["network"] == network) & self.net["metric"].str.startswith(metric_prefix)]
        return float(row["value"].iloc[0])

    def overall(self, df: pd.DataFrame, inst: str) -> pd.Series:
        return df[(df["institution"] == inst) & (df["period"] == "2016-2026 Overall")].iloc[0]


# --------------------------------------------------------------------------- slides
def slide_title(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    cit_all = d.overall(d.cit, ALL)
    q_all = d.overall(d.quart, ALL)
    h_all = d.hsum[d.hsum["institution"] == ALL].iloc[0]
    textbox(s, MARGIN, Inches(0.7), Inches(11.5), Inches(0.4),
            [("DPCN 2026  ·  GROUP 24  ·  STATISTICS REPORT", 13, True, NAVY_SOFT)])
    textbox(s, MARGIN, Inches(1.2), Inches(11.8), Inches(1.6), [
        ("Research output of three CSIR chemistry laboratories, 2016–2026", 36, True, WHITE, False, PP_ALIGN.LEFT, HEAD_FONT),
    ])
    textbox(s, MARGIN, Inches(2.75), Inches(11.8), Inches(0.5), [
        ("CSIR-NCL (Pune)  ·  CSIR-IICT (Hyderabad)  ·  CSIR-CECRI (Karaikudi)", 18, False, NAVY_SOFT),
    ])
    cards = [
        (fmt(cit_all["papers"]), "distinct peer-reviewed papers"),
        (fmt(cit_all["total_citations"]), f"citations (OpenAlex, {COLLECTED})"),
        (pct(q_all["q1_fraction_primary_pct"]), "of ranked journal papers in Q1 (SJR)"),
        (fmt(h_all["active_faculty_count"]), f"roster scientists with ≥1 paper (of {len(d.fm)} listed)"),
    ]
    cw = (CONTENT_W - Inches(0.3) * 3) / 4
    for i, (v, l) in enumerate(cards):
        stat(s, MARGIN + i * (cw + Inches(0.3)), Inches(3.75), cw, Inches(1.45), v, l,
             color=WHITE, fill=RGBColor(0x22, 0x33, 0x55), label_color=NAVY_SOFT, vsize=32)
    textbox(s, MARGIN, Inches(5.6), CONTENT_W, Inches(0.7), [
        (f"Data: OpenAlex works affiliated to the three ROR-verified institutes (collected {COLLECTED}; "
         "links with other Indian institutions 20 Oct 2026). 2026 is a partial year.", 13, False, NAVY_SOFT),
        ("Quartiles: SCImago Journal Rank (best quartile of the publication year). Faculty: official institute staff pages.",
         13, False, NAVY_SOFT),
    ])
    # PowerPoint draws links in the theme's link blue, so give the link a light background
    rect(s, MARGIN, Inches(6.45), Inches(7.6), Inches(0.55), LIGHT, name="Dashboard link")
    textbox(s, MARGIN + Inches(0.2), Inches(6.45), Inches(7.3), Inches(0.55),
            [[("Interactive dashboard:  ", 14, True, INK), (SITE_URL, 14, True, SECONDARY_LINK)]],
            anchor=MSO_ANCHOR.MIDDLE, name="Dashboard URL")
    link_run(s, SITE_URL)
    notes(s, "Sources: stats/tables/citation_summary.csv, quartile_distribution.csv, h_index_summary.csv; "
             "data/final/faculty_master.csv.")


def slide_data(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    m = d.main
    key = m["doi"].where(m["doi"] != "", m["title"] + "|" + m["year"])
    rows = []
    for lab in LABS:
        sub = m[m["institution"] == lab]
        k = key[sub.index]
        papers = sub.assign(k=k).drop_duplicates("k")
        fm = d.fm[d.fm["inst_key"] == short(lab).lower()]
        q = d.overall(d.quart, lab)
        rows.append([lab, fmt(len(papers)), fmt((papers["type"] == "journal").sum()), fmt((papers["type"] == "conference").sum()),
                     fmt(len(sub)), fmt(len(fm)), fmt(d.hsum.loc[d.hsum["institution"] == lab, "active_faculty_count"].iloc[0]),
                     pct(q["quartile_coverage_pct"])])
    allp = m.assign(k=key).drop_duplicates("k")
    q = d.overall(d.quart, ALL)
    rows.append(["All three (distinct)", fmt(len(allp)), fmt((allp["type"] == "journal").sum()),
                 fmt((allp["type"] == "conference").sum()), fmt(len(m)), fmt(len(d.fm)),
                 fmt(d.hsum.loc[d.hsum["institution"] == ALL, "active_faculty_count"].iloc[0]), pct(q["quartile_coverage_pct"])])
    df = pd.DataFrame(rows, columns=["Institute", "Papers", "Journal", "Conference", "Author rows",
                                     "Roster scientists", "With ≥1 paper", "Quartile known"])
    conf = d.conf[d.conf["institution"] == ALL].iloc[0]
    header(s, 2, "Data and method",
           f"{fmt(len(allp))} distinct papers (2016 – 13 Oct 2026) from OpenAlex, one row per paper × institute author")
    table(s, MARGIN, Inches(1.65), CONTENT_W, df, [2.2, 1, 1, 1.1, 1.1, 1.3, 1.2, 1.3], size=12, row_h=0.36,
          align_right=range(1, 8), colors=[LAB_COLOR[l] for l in LABS] + [None], name="Coverage table")
    colw = (CONTENT_W - Inches(0.4)) / 2
    y = Inches(3.75)
    rect(s, MARGIN, y, colw, Inches(3.1), LIGHT)
    rect(s, MARGIN + colw + Inches(0.4), y, colw, Inches(3.1), LIGHT)
    pad = Inches(0.25)
    textbox(s, MARGIN + pad, y + Inches(0.2), colw - 2 * pad, Inches(2.8), [
        ("How the data was built", 16, True, INK),
        ("Works pulled from OpenAlex by the institutes' ROR-verified IDs, with recall checks on CSIR/AcSIR affiliations", 13, False, INK, True),
        ("Kept: articles, reviews, letters, conference papers; editorials, errata, preprints and book chapters excluded", 13, False, INK, True),
        ("Faculty = scientific cadre from official staff pages, matched to OpenAlex authors seen in the corpus", 13, False, INK, True),
        ("Quartile = SJR best quartile of the publication year (2025 values for 2026 papers)", 13, False, INK, True),
    ])
    textbox(s, MARGIN + colw + Inches(0.4) + pad, y + Inches(0.2), colw - 2 * pad, Inches(2.8), [
        ("Limits to keep in mind", 16, True, INK),
        ("OpenAlex author and affiliation matching is imperfect; some papers may be missing or mis-attributed", 13, False, INK, True),
        ("h-index is computed on 2016–2026 corpus papers only, not career-wide; students/project staff are not faculty", 13, False, INK, True),
        ("SJR quartiles can differ from JCR; citations are counts on the collection date", 13, False, INK, True),
        (f"None of the {fmt(conf['total_conferences'])} conference papers has a CORE rank (CORE ranks computer-science venues)", 13, False, INK, True),
    ])
    footer(s, "Source: data/final/group24_data.csv, faculty_master.csv; stats/tables/quartile_distribution.csv, conference_ranks.csv")
    notes(s, "Sources: data/final/group24_data.csv (paper and row counts), data/final/faculty_master.csv (roster), "
             "stats/tables/h_index_summary.csv (faculty with >=1 paper), quartile_distribution.csv (coverage), conference_ranks.csv.")


def slide_trend(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    years = list(range(2016, 2027))
    cd = CategoryChartData()
    cd.categories = [str(y) if y < 2026 else "2026*" for y in years]
    for lab in LABS:
        t = d.trend[d.trend["institution"] == lab].set_index("year")
        cd.add_series(short(lab), [int(t.at[y, "papers"]) for y in years])
    w = Inches(8.3)
    gf = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, MARGIN, Inches(1.65), w, Inches(5.1), cd)
    gf.name = "Publication trend chart"
    ch = gf.chart
    style_chart(ch)
    color_series(ch, [LAB_COLOR[l] for l in LABS])
    ch.plots[0].gap_width = 55
    ch.plots[0].overlap = -5
    chart_title(ch, "Distinct papers per year (* 2026 partial, to 13 Oct)")

    tot = {lab: int(d.trend[(d.trend["institution"] == lab)]["papers"].sum()) for lab in LABS}
    all_tot = int(d.trend[d.trend["institution"] == ALL]["papers"].sum())
    cagr = {lab: float(d.trend[d.trend["institution"] == lab]["cagr_2016_2025"].iloc[0]) for lab in LABS}
    peak = {}
    for lab in LABS:
        t = d.trend[(d.trend["institution"] == lab) & (d.trend["year"] < 2026)]
        peak[lab] = int(t.loc[t["papers"].idxmax(), "year"])
    a25 = d.trend[(d.trend["institution"] == ALL)].set_index("year")
    header(s, 3, "Publication trend",
           f"{fmt(all_tot)} distinct papers in 2016–2026; IICT {pct(tot['CSIR-IICT'] / all_tot * 100, 0)} of them, "
           f"NCL {pct(tot['CSIR-NCL'] / all_tot * 100, 0)}, CECRI {pct(tot['CSIR-CECRI'] / all_tot * 100, 0)}")
    x = MARGIN + w + Inches(0.35)
    pw = SLIDE_W - MARGIN - x
    paras = [("Totals and growth", 16, True, INK)]
    for lab in LABS:
        paras.append([(f"{short(lab)}: ", 13, True, LAB_COLOR[lab]),
                      (f"{fmt(tot[lab])} papers; CAGR 2016→2025 {signed(cagr[lab])}; peak year {peak[lab]}", 13, False, INK)])
    paras += [
        ("", 6, False, INK),
        ("Observations", 16, True, INK),
        (f"Combined output went from {fmt(a25.at[2016, 'papers'])} papers in 2016 to {fmt(a25.at[2025, 'papers'])} in 2025",
         13, False, INK, True),
        ("All three labs have a negative 2016→2025 growth rate in paper count", 13, False, INK, True)
        if all(v < 0 for v in cagr.values()) else
        ("Growth rates differ in sign across the three labs", 13, False, INK, True),
        (f"2026 covers papers to 13 Oct only ({fmt(a25.at[2026, 'papers'])} so far) and is left out of CAGR", 13, False, INK, True),
    ]
    rect(s, x, Inches(1.65), pw, Inches(5.1), LIGHT)
    textbox(s, x + Inches(0.22), Inches(1.85), pw - Inches(0.44), Inches(4.8), paras)
    footer(s, "Source: stats/tables/publication_trend.csv · Papers counted once per institute; combined counts distinct papers")
    notes(s, "Source: stats/tables/publication_trend.csv (papers, yoy_growth_pct, cagr_2016_2025).")


def slide_quartiles(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    groups = LABS + [ALL]
    cd = CategoryChartData()
    cd.categories = [short(g) if g != ALL else "All three" for g in groups]
    rows = {g: d.overall(d.quart, g) for g in groups}
    for q, col in [("Q1", "q1_count"), ("Q2", "q2_count"), ("Q3", "q3_count"), ("Q4", "q4_count"), ("Unranked", "unranked_count")]:
        cd.add_series(q, [int(rows[g][col]) / int(rows[g]["total_journals"]) for g in groups])
    w = Inches(6.3)
    gf = add_chart(s, XL_CHART_TYPE.BAR_STACKED_100, MARGIN, Inches(1.65), w, Inches(5.1), cd)
    gf.name = "Quartile chart"
    ch = gf.chart
    style_chart(ch)
    color_series(ch, list(Q_COLOR.values()))
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format = "0%"
    dl.number_format_is_linked = False
    dl.position = XL_LABEL_POSITION.CENTER
    dl.font.size = Pt(11)
    for i, ser in enumerate(plot.series):
        ser.data_labels.font.color.rgb = WHITE if i < 2 else INK
        ser.data_labels.font.size = Pt(11)
        ser.data_labels.number_format = "0%"
        ser.data_labels.number_format_is_linked = False
    ch.category_axis.reverse_order = True
    ch.value_axis.tick_labels.number_format = "0%"
    ch.value_axis.tick_labels.number_format_is_linked = False
    chart_title(ch, "Share of journal papers by SJR quartile")

    ir = d.ir.set_index("institution")
    thr_cols = [c for c in d.ir.columns if c.startswith("ir_q1_gt_") and not c.endswith("_pct")]
    thr = [c[len("ir_q1_gt_"):] for c in thr_cols]  # e.g. "5", "10", "0.59"
    p75 = f"{float(ir.at[ALL, 'percentile_threshold']):g}"
    q1_in_sjr = d.ir_sjr[(d.ir_sjr["institution"] == ALL) & (d.ir_sjr["sjr_quartile"] == "Q1")].iloc[0]
    header(s, 4, "Journal quartiles and citation impact ratio",
           f"{pct(rows[ALL]['q1_fraction_primary_pct'])} of ranked journal papers are in SJR-Q1 journals; Q1 by impact ratio "
           f"(IR > {p75}, top 25% of papers) ranges from {pct(ir.at['CSIR-IICT', f'ir_q1_gt_{p75}_pct'])} (IICT) "
           f"to {pct(ir.at['CSIR-CECRI', f'ir_q1_gt_{p75}_pct'])} (CECRI)")
    x = MARGIN + w + Inches(0.35)
    pw = SLIDE_W - MARGIN - x
    textbox(s, x, Inches(1.65), pw, Inches(0.35), [("Q1 by journal vs Q1 by impact ratio (% of papers)", 14, True, INK)])
    cols = ["Institute", "Q1 by journal (SJR)"] + [f"Q1 by IR (IR > {t})" for t in thr] + ["Institute IR"]
    df = pd.DataFrame([[short(g) if g != ALL else "All three", pct(rows[g]["q1_fraction_primary_pct"])]
                       + [pct(ir.at[g, f"ir_q1_gt_{t}_pct"]) for t in thr]
                       + [f"{float(ir.at[g, 'institute_impact_ratio']):.2f}"] for g in LABS + [ALL]], columns=cols)
    table(s, x, Inches(2.05), pw, df, [1.2, 1.3] + [1.3] * len(thr) + [1.1], size=12, row_h=0.36,
          align_right=range(1, len(cols)), colors=[LAB_COLOR[l] for l in LABS] + [None], name="IR table")
    textbox(s, x, Inches(4.2), pw, Inches(2.6), [
        [("Impact ratio (IR) ", 12, True, INK),
         ("= citations received ÷ citations made (references). A paper is IR‑Q1 when IR exceeds the threshold; "
          "the institute IR is all citations received ÷ all references made.", 12, False, INK)],
        (f"Threshold IR > {p75} is the 75th percentile of IR over all papers, so IR‑Q1 is the top 25% of papers — "
         f"the same share a quartile covers (median paper IR {float(ir.at[ALL, 'median_paper_ir']):.2f}).",
         12, False, INK, True),
        (f"The two definitions disagree: only {pct(q1_in_sjr[f'ir_q1_gt_{p75}_pct'])} of papers in SJR-Q1 journals are "
         f"top‑25% by IR. SJR ranks the journal; IR ranks the paper.", 12, False, INK, True),
        (f"Older papers have had longer to be cited; {fmt(ir.at[ALL, 'papers_without_references'])} papers with no "
         "references in OpenAlex are excluded.", 12, False, INK, True),
    ])
    footer(s, "Source: stats/tables/quartile_distribution.csv, impact_ratio_summary.csv, impact_ratio_vs_sjr.csv · SJR best quartile (Scopus-based); IR from OpenAlex citations (13 Oct) and references")
    notes(s, "Sources: stats/tables/quartile_distribution.csv (SJR Q1 = Q1 / journal papers with known quartile), "
             "impact_ratio_summary.csv, impact_ratio_vs_sjr.csv, impact_ratio_by_year.csv. IR thresholds are set in "
             "config/settings.yaml (impact_ratio.thresholds and quartile_percentile).")


def slide_faculty(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bins = d.hdist[d.hdist["institution"] == LABS[0]]["bin_label"].tolist()
    cd = CategoryChartData()
    cd.categories = bins
    for lab in LABS:
        h = d.hdist[d.hdist["institution"] == lab].set_index("bin_label")
        cd.add_series(short(lab), [int(h.at[b, "faculty_count"]) for b in bins])
    w = Inches(6.6)
    gf = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, MARGIN, Inches(1.65), w, Inches(5.1), cd)
    gf.name = "h-index histogram"
    ch = gf.chart
    style_chart(ch)
    color_series(ch, [LAB_COLOR[l] for l in LABS])
    ch.plots[0].gap_width = 50
    chart_title(ch, "Faculty by h-index (2016–2026 papers), count of scientists")

    hs = d.hsum.set_index("institution")
    header(s, 5, "Faculty h-index distribution",
           f"Median h-index of the {fmt(hs.at[ALL, 'active_faculty_count'])} roster scientists with papers is "
           f"{hs.at[ALL, 'median_h_index']:g}; CECRI {hs.at['CSIR-CECRI', 'median_h_index']:g}, "
           f"NCL {hs.at['CSIR-NCL', 'median_h_index']:g}, IICT {hs.at['CSIR-IICT', 'median_h_index']:g}")
    x = MARGIN + w + Inches(0.35)
    pw = SLIDE_W - MARGIN - x
    summ = pd.DataFrame([[short(g) if g != ALL else "All", fmt(hs.at[g, "active_faculty_count"]), f"{hs.at[g, 'median_h_index']:g}",
                          f"{hs.at[g, 'mean_h_index']:.1f}", f"{hs.at[g, 'p75_h_index']:g}", fmt(hs.at[g, "max_h_index"])]
                         for g in LABS + [ALL]], columns=["Institute", "Faculty", "Median", "Mean", "P75", "Max"])
    table(s, x, Inches(1.65), pw, summ, [1.4, 1, 1, 1, 0.9, 0.9], size=12, row_h=0.32, align_right=range(1, 6),
          colors=[LAB_COLOR[l] for l in LABS] + [None], name="h-index summary")
    top = d.faculty.sort_values(["h_index_corpus", "citations"], ascending=False).head(6)
    tdf = pd.DataFrame([[clip(r["name"], 26), short(r["institution"]), fmt(r["papers"]), fmt(r["citations"]), fmt(r["h_index_corpus"])]
                        for _, r in top.iterrows()], columns=["Top faculty by h-index", "Lab", "Papers", "Citations", "h"])
    textbox(s, x, Inches(3.55), pw, Inches(0.3), [("Highest h-index (2016–2026 window)", 14, True, INK)])
    table(s, x, Inches(3.95), pw, tdf, [2.6, 0.8, 0.9, 1.1, 0.6], size=11, row_h=0.3, align_right=range(2, 5),
          name="Top faculty table")
    footer(s, "Source: stats/tables/h_index_summary.csv, h_index_distribution.csv, faculty_performance.csv · h-index on 2016–2026 corpus papers")
    notes(s, "Sources: stats/tables/h_index_summary.csv, h_index_distribution.csv, faculty_performance.csv. "
             "Faculty = roster scientists matched to OpenAlex with >=1 paper. Career-wide h-index was not collected.")


def slide_journals(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    tops = {lab: d.journals[d.journals["institution"] == lab].sort_values("rank").head(5) for lab in LABS}
    header(s, 6, "Top 5 journals per institute",
           "Most frequent venues: " + "; ".join(f"{short(l)} – {tops[l].iloc[0]['journal_name']} ({fmt(tops[l].iloc[0]['paper_count'])})"
                                                for l in LABS))
    gap = Inches(0.3)
    cw = (CONTENT_W - 2 * gap) / 3
    for i, lab in enumerate(LABS):
        x = MARGIN + i * (cw + gap)
        rect(s, x, Inches(1.65), cw, Inches(0.55), LAB_COLOR[lab])
        tot = d.overall(d.cit, lab)["papers"]
        textbox(s, x + Inches(0.18), Inches(1.65), cw - Inches(0.36), Inches(0.55),
                [[(lab, 15, True, WHITE), (f"   {fmt(tot)} papers", 12, False, WHITE)]], anchor=MSO_ANCHOR.MIDDLE)
        df = pd.DataFrame([[int(r["rank"]), clip(r["journal_name"], 34), fmt(r["paper_count"]), pct(r["share_pct"]),
                            r["quartile"] or "—"] for _, r in tops[lab].iterrows()],
                          columns=["#", "Journal", "Papers", "Share", "Q"])
        table(s, x, Inches(2.35), cw, df, [0.32, 2.75, 0.95, 0.85, 0.45], size=12, row_h=0.62, align_right=(2, 3),
              header_fill=INK, name=f"Journals {short(lab)}")
    allj = d.journals[d.journals["institution"] == ALL].sort_values("rank").head(5)
    textbox(s, MARGIN, Inches(6.25), CONTENT_W, Inches(0.5), [
        [("All three combined: ", 13, True, INK),
         ("; ".join(f"{r['journal_name']} ({fmt(r['paper_count'])})" for _, r in allj.iterrows()), 13, False, INK)],
    ])
    footer(s, "Source: stats/tables/top_journals.csv · ranked by distinct papers; share = % of the institute's papers; Q = SJR quartile")
    notes(s, "Source: stats/tables/top_journals.csv (ties broken by total citations).")


def slide_top_cited(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    top = d.topcited[d.topcited["institution"] == ALL].sort_values("rank").head(10)
    labs_of = d.main.groupby("doi")["institution"].agg(lambda x: "/".join(short(i) for i in LABS if i in set(x)))
    df = pd.DataFrame([[int(r["rank"]), clip(r["title"], 92), clip(r["journal_name"], 30), int(r["year"]),
                        labs_of.get(r["doi"], ""), fmt(r["citations"]), doi_short(r["doi"])]
                       for _, r in top.iterrows()],
                      columns=["#", "Title", "Journal", "Year", "Lab", "Citations", "DOI"])
    c = {g: d.overall(d.cit, g) for g in LABS + [ALL]}
    header(s, 7, "Top 10 most-cited papers (all three institutes)",
           f"{fmt(c[ALL]['total_citations'])} citations in total; mean {c[ALL]['mean_citations']:.1f} and median "
           f"{c[ALL]['median_citations']:g} per paper; the top paper has {fmt(top.iloc[0]['citations'])}")
    table(s, MARGIN, Inches(1.62), CONTENT_W, df, [0.3, 5.6, 2.1, 0.55, 0.85, 0.85, 2.6], size=10.5, row_h=0.41,
          align_right=(3, 5), name="Top cited table")
    strip = "   ·   ".join(f"{short(g)}: {fmt(c[g]['total_citations'])} citations, mean {c[g]['mean_citations']:.1f}, "
                           f"uncited {pct(c[g]['uncited_share_pct'])}" for g in LABS)
    textbox(s, MARGIN, Inches(6.38), CONTENT_W, Inches(0.4), [(strip, 12, False, INK)])
    footer(s, "Source: stats/tables/top_cited_papers.csv, citation_summary.csv · OpenAlex cited_by_count on 13 Oct 2026; older papers have had longer to accrue citations")
    notes(s, "Sources: stats/tables/top_cited_papers.csv (institution = Group 24 Combined), citation_summary.csv. "
             "Per-institute top-10 lists are in the dashboard (Venues & Landmark Papers tab).")


def slide_areas(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    allf = d.fields[d.fields["institution"] == ALL].sort_values("paper_count", ascending=False)
    top_fields = allf["field"].head(7).tolist()
    cd = CategoryChartData()
    cd.categories = top_fields
    for lab in LABS:
        f = d.fields[d.fields["institution"] == lab].set_index("field")
        cd.add_series(short(lab), [float(f.at[x, "share_pct"]) / 100 if x in f.index else 0 for x in top_fields])
    w = Inches(6.9)
    gf = add_chart(s, XL_CHART_TYPE.BAR_CLUSTERED, MARGIN, Inches(1.65), w, Inches(5.1), cd)
    gf.name = "Research area chart"
    ch = gf.chart
    style_chart(ch)
    color_series(ch, [LAB_COLOR[l] for l in LABS])
    ch.plots[0].gap_width = 45
    ch.category_axis.reverse_order = True
    ch.value_axis.tick_labels.number_format = "0%"
    ch.value_axis.tick_labels.number_format_is_linked = False
    chart_title(ch, "Share of each institute's papers by OpenAlex field")
    lead = {lab: d.fields[d.fields["institution"] == lab].sort_values("paper_count", ascending=False).iloc[0] for lab in LABS}
    header(s, 8, "Research areas and departments",
           f"Chemistry is the largest field for all three ({', '.join(f'{short(l)} {pct(lead[l].share_pct, 0)}' for l in LABS)})"
           if all(lead[l]["field"] == "Chemistry" for l in LABS) else
           "Largest field: " + ", ".join(f"{short(l)} – {lead[l]['field']} ({pct(lead[l]['share_pct'], 0)})" for l in LABS))
    x = MARGIN + w + Inches(0.35)
    pw = SLIDE_W - MARGIN - x
    textbox(s, x, Inches(1.65), pw, Inches(0.3), [("Top 2 departments per institute by papers", 14, True, INK)])
    rows, cols = [], []
    for lab in LABS:
        dd = d.depts[d.depts["institution"] == lab].sort_values("papers", ascending=False).head(2)
        for _, r in dd.iterrows():
            rows.append([clip(dept_name(r["department"]), 40), short(lab), fmt(r["active_faculty"]), fmt(r["papers"]),
                         pct(r["q1_share_pct"], 0)])
            cols.append(LAB_COLOR[lab])
    df = pd.DataFrame(rows, columns=["Department", "Lab", "Faculty", "Papers", "Q1"])
    table(s, x, Inches(2.05), pw, df, [3.2, 0.75, 0.8, 0.8, 0.6], size=11, row_h=0.5, align_right=(2, 3, 4), name="Department table")
    textbox(s, x, Inches(5.65), pw, Inches(1.1), [
        ("Department = roster division of each faculty member; a paper counts in every department of its faculty authors. "
         "Papers by non-roster authors only are not assigned to a department.", 11, False, MUTED),
    ])
    footer(s, "Source: stats/tables/research_areas_field.csv, department_performance.csv · field = OpenAlex primary topic → field")
    notes(s, "Sources: stats/tables/research_areas_field.csv, research_areas_subfield.csv, department_performance.csv. "
             "Faculty = active roster scientists in the department.")


def slide_citation_network(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    nodes = d.net_value("citation", "nodes")
    pairs = d.net_value("citation", "distinct citing")
    cross = d.net_value("citation", "cross-lab")
    flow = d.flow.set_index("institution")
    tin, tout = flow.at[ALL, "in_citations_indian"], flow.at[ALL, "out_citations_indian"]
    header(s, 9, "Citation network",
           f"{fmt(pairs)} citation links among {fmt(nodes)} corpus papers; {fmt(cross)} cross between labs. "
           f"With other Indian institutions: {fmt(tin)} citations in, {fmt(tout)} out")
    cw = (CONTENT_W - Inches(0.3) * 3) / 4
    cards = [
        (fmt(nodes), "papers in the in-corpus citation graph"),
        (fmt(d.net_value("citation", "papers cited")), f"papers cited ≥1 time within corpus (max in-degree {fmt(d.net_value('citation', 'max in-degree'))})"),
        (fmt(cross), "citation links between the three labs"),
        (f"{float(flow.at[ALL, 'impact_ratio_indian']):.2f}", "in / out citation ratio with other Indian institutions"),
    ]
    for i, (v, l) in enumerate(cards):
        stat(s, MARGIN + i * (cw + Inches(0.3)), Inches(1.6), cw, Inches(0.95), v, l, vsize=22)
    pr = d.pr.head(10)
    df = pd.DataFrame([[int(r["rank"]), clip(r["title"], 56), r["institutions"].replace("CSIR-", ""), int(r["year"]),
                        int(r["in_degree_corpus"]), f"{float(r['pagerank']):.4f}"] for _, r in pr.iterrows()],
                      columns=["#", "PageRank top 10", "Lab", "Year", "In-deg", "PR"])
    lw = Inches(7.45)
    table(s, MARGIN, Inches(2.75), lw, df, [0.3, 4.4, 0.9, 0.55, 0.6, 0.75], size=10, row_h=0.36,
          align_right=(3, 4, 5), name="PageRank table")
    x = MARGIN + lw + Inches(0.3)
    pw = SLIDE_W - MARGIN - x
    cd = CategoryChartData()
    cd.categories = d.indeg["in_degree_bin"].tolist()
    cd.add_series("Papers", d.indeg["papers"].astype(int).tolist())
    gf = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, x, Inches(2.7), pw, Inches(2.15), cd)
    gf.name = "In-degree chart"
    ch = gf.chart
    style_chart(ch, legend=False, size=10)
    color_series(ch, [NAVY])
    ch.plots[0].gap_width = 40
    ch.plots[0].has_data_labels = True
    ch.plots[0].data_labels.font.size = Pt(9)
    ch.plots[0].data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    ch.plots[0].data_labels.number_format = "#,##0"
    ch.plots[0].data_labels.number_format_is_linked = False
    ch.value_axis.tick_labels.number_format = "#,##0"
    ch.value_axis.tick_labels.number_format_is_linked = False
    chart_title(ch, "In-degree distribution (corpus papers)")
    fdf = pd.DataFrame([[short(g), fmt(flow.at[g, "in_citations_indian"]), fmt(flow.at[g, "out_citations_indian"]),
                         f"{float(flow.at[g, 'impact_ratio_indian']):.2f}", fmt(flow.at[g, "distinct_citing_institutions"])]
                        for g in LABS], columns=["Lab", "Cited by Indian", "Cites Indian", "In/out", "Citing insts"])
    textbox(s, x, Inches(4.95), pw, Inches(0.3), [("Citation flow with other Indian institutions", 12, True, INK)])
    table(s, x, Inches(5.25), pw, fdf, [0.8, 1.1, 1.0, 0.7, 0.9], size=10, row_h=0.3, align_right=range(1, 5),
          colors=[LAB_COLOR[l] for l in LABS], name="Indian flow table")
    footer(s, "Source: stats/tables/network_summary.csv, network_citation_*.csv, citation_flow_summary.csv · in-degree = citations from other corpus papers; flows count links to DOI-bearing papers")
    notes(s, "Graph: directed, nodes = corpus papers, edge = A cites B (OpenAlex referenced_works), analysed within the three labs. "
             "Sources: stats/tables/network_summary.csv, network_citation_pagerank_top10.csv, "
             "network_citation_indegree_distribution.csv, network_citation_flow_matrix.csv, citation_flow_summary.csv. "
             "Flow 'Cited by Indian' = citation links from papers involving an Indian institution other than the lab "
             "(includes the other two labs and Indian papers outside the corpus).")


def slide_authorship_network(prs, d: Data):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    authors = d.net_value("authorship", "authors")
    pairs = d.net_value("authorship", "co-author pairs")
    ncom = d.net_value("authorship", "Louvain")
    big = d.net_value("authorship", "communities with")
    mod = d.net_value("authorship", "modularity")
    lcc = d.net_value("authorship", "largest component share")
    header(s, 10, "Authorship network",
           f"{fmt(authors)} authors, {fmt(pairs)} co-author pairs; Louvain finds {fmt(ncom)} communities "
           f"(modularity {mod:.2f}), almost all within a single lab")
    cw = (CONTENT_W - Inches(0.3) * 3) / 4
    cards = [
        (fmt(authors), f"authors; {pct(lcc, 0)} in the largest connected component"),
        (f"{d.net_value('authorship', 'mean degree'):.1f}", "mean number of distinct co-authors"),
        (fmt(ncom), f"Louvain communities ({fmt(big)} with ≥10 authors)"),
        (fmt(d.net_value("authorship", "cross-lab")), "co-authorship links between the three labs"),
    ]
    for i, (v, l) in enumerate(cards):
        stat(s, MARGIN + i * (cw + Inches(0.3)), Inches(1.6), cw, Inches(0.95), v, l, vsize=22)
    btw_rank = {a: i for i, a in enumerate(d.btw["author"], 1)}
    df = pd.DataFrame([[int(r["rank"]), clip(r["author"], 30), short(r["institution"]), fmt(r["degree"]),
                        f"{float(r['betweenness']):.3f}", f"#{btw_rank[r['author']]}" if r["author"] in btw_rank else "—",
                        int(r["community"])] for _, r in d.deg.iterrows()],
                      columns=["#", "Most collaborative (degree)", "Lab", "Degree", "Betweenness", "Btw rank", "Comm."])
    lw = Inches(7.45)
    table(s, MARGIN, Inches(2.75), lw, df, [0.3, 2.9, 0.7, 0.75, 1.0, 0.85, 0.7], size=10, row_h=0.36,
          align_right=(3, 4, 5, 6), name="Degree table")
    x = MARGIN + lw + Inches(0.3)
    pw = SLIDE_W - MARGIN - x
    comms = d.comms.head(8)
    cd = CategoryChartData()
    cd.categories = [f"C{int(c)}" for c in comms["community"]]
    cd.add_series("Authors", comms["authors"].astype(int).tolist())
    gf = add_chart(s, XL_CHART_TYPE.COLUMN_CLUSTERED, x, Inches(2.7), pw, Inches(2.15), cd)
    gf.name = "Community chart"
    ch = gf.chart
    style_chart(ch, legend=False, size=10)
    ch.plots[0].gap_width = 40
    ch.plots[0].vary_by_categories = False
    ser = ch.plots[0].series[0]
    for i, lab in enumerate(comms["dominant_institution"]):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = LAB_COLOR.get(lab, MUTED)
    ch.plots[0].has_data_labels = True
    ch.plots[0].data_labels.font.size = Pt(9)
    ch.plots[0].data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    chart_title(ch, "Largest communities (colour = main lab)")
    btop = d.btw.head(4)
    paras = [("Top brokers by betweenness", 12, True, INK)]
    for _, r in btop.iterrows():
        paras.append([(f"{clip(r['author'], 28)} ", 11, True, LAB_COLOR.get(r["institution"], INK)),
                      (f"{short(r['institution'])} · {float(r['betweenness']):.3f} · degree {fmt(r['degree'])}", 11, False, INK)])
    pt_ = d.partners[d.partners["institution"] == ALL].sort_values("rank").head(3)
    paras.append([("Top Indian partners: ", 11, True, INK),
                  ("; ".join(f"{clip(r['partner_institution'], 52)} ({fmt(r['collaborative_papers'])})" for _, r in pt_.iterrows()), 11, False, INK)])
    textbox(s, x, Inches(4.95), pw, Inches(1.9), paras)
    footer(s, f"Source: stats/tables/network_summary.csv, network_authorship_*.csv, indian_partner_institutions.csv · interactive graphs: {SITE_URL}")
    link_run_in_footer(s, SITE_URL)
    notes(s, "Graph: undirected, nodes = authors of the three labs, edge = co-authored >=1 paper (weight = joint papers). "
             "Degree = distinct co-authors; betweenness estimated from 1,000 sampled sources (unweighted); "
             "communities = Louvain (seed 42) on joint-paper weights. Partner co-authors at other Indian institutions are "
             "kept in authorship_network.csv as raw data but not analysed. Sources: stats/tables/network_summary.csv, "
             "network_authorship_top_degree.csv, network_authorship_top_betweenness.csv, network_authorship_communities.csv, "
             "indian_partner_institutions.csv.")


def slide_ten_findings(prs, d: Data):
    import json
    s = prs.slides.add_slide(prs.slide_layouts[6])
    header(s, 11, "Ten Non-Obvious Bibliometric & Network Findings",
           "Key empirical findings from cluster network fragility, brain circulation, succession risk, and citation dynamics")

    insights_dir = Path("stats/tables/insights")
    order = [
        "01_friendship_paradox", "02_rich_club", "03_fragility", "04_price_law",
        "05_quartile_vs_impact", "06_pagerank_vs_citations", "07_sleeping_beauties",
        "08_covid_shock", "09_brain_circulation", "10_succession_risk"
    ]
    rows = []
    for i, key in enumerate(order, 1):
        fpath = insights_dir / f"{key}.json"
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                item = json.load(f)
                rows.append([i, item.get("question", ""), item.get("headline", "")])
        else:
            rows.append([i, f"Finding {i}", "Not computed"])

    df = pd.DataFrame(rows, columns=["#", "Research Question", "Empirical Finding & Headline Result"])
    table(s, MARGIN, Inches(1.5), CONTENT_W, df, [0.35, 3.85, 8.4], size=8.5, row_h=0.47,
          name="Ten Non-Obvious Findings Table")

    footer(s, f"Source: stats/tables/insights/*.json · interactive charts and methodology notes: {SITE_URL}")
    link_run_in_footer(s, SITE_URL)
    notes(s, "All 10 non-obvious analyses are fully interactive with dedicated charts on the dashboard 'Insights' tab.")


# --------------------------------------------------------------------------- build + export
def build_presentation() -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    d = Data()
    for fn in (slide_title, slide_data, slide_trend, slide_quartiles, slide_faculty, slide_journals,
               slide_top_cited, slide_areas, slide_citation_network, slide_authorship_network, slide_ten_findings):
        fn(prs, d)
    prs.core_properties.title = "Group 24 Statistics Report — CSIR-NCL, CSIR-IICT, CSIR-CECRI (2016–2026)"
    prs.core_properties.author = "DPCN 2026 Group 24"
    return prs


def export_pdf(pptx: Path, pdf: Path) -> bool:
    if pdf.exists():
        pdf.unlink()  # so a failed export cannot look like success
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf.parent), str(pptx)],
                       check=True, capture_output=True, timeout=180)
        return pdf.exists()
    if sys.platform == "win32":
        ps = (
            "$pp = New-Object -ComObject PowerPoint.Application; "
            f"$p = $pp.Presentations.Open('{pptx.resolve()}', $true, $false, $false); "
            f"$p.SaveAs('{pdf.resolve()}', 32); $p.Close(); $pp.Quit()"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True, timeout=300)
        return pdf.exists()
    return False


def run_report_generation() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prs = build_presentation()
    prs.save(PPTX)
    logger.info(f"✓ Saved {PPTX} ({len(prs.slides)} slides)")
    try:
        if export_pdf(PPTX, PDF):
            logger.info(f"✓ Exported {PDF}")
        else:
            logger.warning("No LibreOffice or PowerPoint found; PDF not exported")
    except Exception as exc:  # PDF is a convenience copy; the PPTX is the source
        logger.warning(f"PDF export failed: {exc}")


if __name__ == "__main__":
    run_report_generation()
