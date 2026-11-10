"""Global benchmark tables (D-35): our three labs against their twins in the USA, China, South Korea
and Australia and the Indian reference group, plus the labs' links with every foreign country.

Inputs: data/final/global/* (Steps 22-23), config/global_benchmark.yaml,
config/overrides/global_peer_exclusions.csv, and for the country table the curated dataset
(group24_data_extended.csv, work_author_counts.csv, institutions_seen.csv).

Outputs (stats/tables/global_*.csv)
- global_peers.csv            the 19 institutions: group, short name, twin_of, similarity
- global_summary.csv          per institution, 2016-2025, benchmark scope: papers, growth,
                              top 10% / top 1% / above-world-average / international shares
- global_by_year.csv          per institution and year: papers, index (2016 = 100), top 10% share
- global_countries.csv        India, USA, China, South Korea, Australia, world: in-scope papers
                              and top 10% share by year
- global_links.csv            per CSIR lab and peer: co-authored papers, peer papers citing the
                              lab, peer papers the lab cites (each excluding papers co-authored
                              with the lab), and the exchange ratio
- global_country_relations.csv every country co-authoring with the labs (curated data, 2016-2026)
- global_rule_funnel.csv      per country: institutions removed by each selection rule
- global_similarity.csv       research-profile similarity of every candidate to each lab
- global_profiles.csv         share of each institution's papers in the main scope subfields
"""

from pathlib import Path

import pandas as pd
import yaml

from src.common.logging import get_logger

logger = get_logger("global_benchmark")

G = Path("data/final/global")
T = Path("stats/tables")
LAB_SHORT = {"CSIR-NCL": "CSIR-NCL", "CSIR-IICT": "CSIR-IICT", "CSIR-CECRI": "CSIR-CECRI"}
COUNTRY_NAMES = {"IN": "India", "US": "USA", "CN": "China", "KR": "South Korea", "AU": "Australia", "WORLD": "World"}


def _cfg() -> dict:
    with open("config/global_benchmark.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _pct(a, b):
    return round(100 * a / b, 2) if b else None


def peers_table(cfg: dict) -> pd.DataFrame:
    p = pd.read_csv(G / "peers.csv", dtype={"institution_id": str})
    short = {**{x["id"]: x["short"] for x in cfg["indian_peers"]}, **(cfg.get("short_names") or {})}
    p["short"] = [short.get(i, n) for i, n in zip(p["institution_id"], p["name"])]
    p["twin_of"] = p["twin_of"].fillna("")
    p["city"] = p["city"].fillna("")
    order = {"CSIR lab": 0, "India": 1, "USA": 2, "China": 3, "South Korea": 4, "Australia": 5}
    p["order"] = p["group"].map(order)
    return p.sort_values(["order", "in_scope_papers"], ascending=[True, False]).drop(columns="order")


def cagr(a, b, n):
    return round(100 * ((b / a) ** (1 / n) - 1), 2) if a and b else None


def summary_tables(peers: pd.DataFrame, cfg: dict):
    by = pd.read_csv(G / "bench_by_year.csv", dtype={"institution_id": str})
    y0, y1 = cfg["years"]["start"], cfg["years"]["end"]
    rows, yrows = [], []
    for _, p in peers.iterrows():
        g = by[by["institution_id"] == p["institution_id"]].set_index("year")
        tot = g.sum()
        first, last = g.loc[y0, "papers_scope"], g.loc[y1, "papers_scope"]
        early, late = g.loc[y0:y0 + 4], g.loc[y1 - 4:y1]
        rows.append({
            "institution_id": p["institution_id"], "short": p["short"], "group": p["group"], "twin_of": p["twin_of"],
            "papers_all": int(tot["papers_all"]), "papers_scope": int(tot["papers_scope"]),
            "scope_share_pct": _pct(tot["papers_scope"], tot["papers_all"]),
            f"papers_{y0}": int(first), f"papers_{y1}": int(last),
            "cagr_pct": cagr(first, last, y1 - y0),
            "top10_pct": _pct(tot["top10"], tot["papers_scope"]),
            "top1_pct": _pct(tot["top1"], tot["papers_scope"]),
            "above_world_pct": _pct(tot["above_world"], tot["papers_scope"]),
            "intl_pct": _pct(tot["intl"], tot["papers_scope"]),
            "top10_pct_early": _pct(early["top10"].sum(), early["papers_scope"].sum()),
            "top10_pct_late": _pct(late["top10"].sum(), late["papers_scope"].sum()),
        })
        for y, r in g.iterrows():
            yrows.append({"institution_id": p["institution_id"], "short": p["short"], "group": p["group"], "year": y,
                          "papers_scope": int(r["papers_scope"]),
                          "index_2016": round(100 * r["papers_scope"] / first, 1) if first else None,
                          "top10_pct": _pct(r["top10"], r["papers_scope"]),
                          "intl_pct": _pct(r["intl"], r["papers_scope"])})
    return pd.DataFrame(rows), pd.DataFrame(yrows)


def countries_table() -> pd.DataFrame:
    c = pd.read_csv(G / "country_by_year.csv", keep_default_na=False)
    world = c[c["country_code"] == "WORLD"].set_index("year")["papers_scope"]
    c["country"] = c["country_code"].map(COUNTRY_NAMES)
    c["world_share_pct"] = [_pct(n, world[y]) for n, y in zip(c["papers_scope"], c["year"])]
    c["top10_pct"] = [_pct(a, b) for a, b in zip(c["top10"], c["papers_scope"])]
    c["top1_pct"] = [_pct(a, b) for a, b in zip(c["top1"], c["papers_scope"])]
    return c[["country_code", "country", "year", "papers_scope", "world_share_pct", "top10_pct", "top1_pct"]]


def links_table(peers: pd.DataFrame) -> pd.DataFrame:
    co = pd.read_csv(G / "collab_by_year.csv", dtype={"institution_id": str})
    fl = pd.read_csv(G / "citation_flows.csv", dtype={"institution_id": str, "work_id": str})
    fl["coauthored_with_lab"] = fl["coauthored_with_lab"].astype(str).str.upper() == "TRUE"
    clean = fl[~fl["coauthored_with_lab"]]
    rows = []
    for _, p in peers[peers["group"] != "CSIR lab"].iterrows():
        for lab in LAB_SHORT:
            iid = p["institution_id"]
            cites = clean[(clean["lab"] == lab) & (clean["institution_id"] == iid)]
            inn = cites[cites["direction"] == "peer_cites_lab"]["work_id"].nunique()
            out = cites[cites["direction"] == "lab_cites_peer"]["work_id"].nunique()
            rows.append({
                "lab": lab, "institution_id": iid, "short": p["short"], "group": p["group"],
                "is_twin": p["group"] != "India" and p["twin_of"] == lab,  # Indian peers: closest lab only
                "coauthored_papers": int(co[(co["lab"] == lab) & (co["institution_id"] == iid)]["papers"].sum()),
                "peer_papers_citing_lab": int(inn), "peer_papers_cited_by_lab": int(out),
                "exchange_ratio": round(inn / out, 2) if out else None,
            })
    return pd.DataFrame(rows)


def country_relations() -> pd.DataFrame:
    """Every foreign country on the labs' curated papers (2016-2026)."""
    wac = pd.read_csv("data/final/work_author_counts.csv", dtype=str, keep_default_na=False)
    ext = pd.read_csv("data/final/group24_data_extended.csv", dtype=str, keep_default_na=False,
                      usecols=["work_id", "institution", "year"]).drop_duplicates(["work_id", "institution"])
    inst = pd.read_csv("data/final/institutions_seen.csv", dtype=str, keep_default_na=False)
    iname = dict(zip(inst["institution_id"], inst["display_name"]))
    icc = dict(zip(inst["institution_id"], inst["country_code"]))
    year = ext.drop_duplicates("work_id").set_index("work_id")["year"].astype(int)
    labs = ext.groupby("work_id")["institution"].agg(set)

    pc = wac[["work_id", "countries"]].assign(cc=wac["countries"].str.split(";")).explode("cc")
    pc = pc[(pc["cc"] != "") & (pc["cc"] != "IN")]
    foreign_total = pc["work_id"].nunique()
    pi = wac[["work_id", "institution_ids"]].assign(i=wac["institution_ids"].str.split(";")).explode("i")
    pi["cc"] = pi["i"].map(icc)
    pi = pi[pi["cc"].notna() & (pi["cc"] != "IN") & (pi["cc"] != "")]

    focus = {"US", "CN", "KR", "AU"}
    rows = []
    for cc, g in pc.groupby("cc"):
        works = set(g["work_id"])
        yrs = year.reindex(list(works))
        ins = pi[pi["cc"] == cc].groupby("i")["work_id"].nunique().sort_values(ascending=False)
        top = ins.head(3)
        rows.append({
            "country_code": cc, "focus_country": cc in focus, "papers": len(works),
            "share_of_foreign_coauthored_pct": _pct(len(works), foreign_total),
            "papers_ncl": sum("CSIR-NCL" in labs.get(w, set()) for w in works),
            "papers_iict": sum("CSIR-IICT" in labs.get(w, set()) for w in works),
            "papers_cecri": sum("CSIR-CECRI" in labs.get(w, set()) for w in works),
            "papers_2016_2020": int((yrs <= 2020).sum()), "papers_2021_2026": int((yrs >= 2021).sum()),
            "partner_institutions": int(len(ins)),
            "top_partners": "; ".join(f"{iname.get(i, i)} ({n})" for i, n in top.items()),
        })
    out = pd.DataFrame(rows).sort_values("papers", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    out.attrs["foreign_total"] = foreign_total
    return out


# Indian universities (merged from the former Study 1.1 "Academic Bridge", D-39)
UNIVERSITIES = [
    ("Indian Institute of Science Bangalore", "IISc", "IISc / IIT"),
    ("Indian Institute of Technology Bombay", "IIT Bombay", "IISc / IIT"),
    ("Indian Institute of Technology Madras", "IIT Madras", "IISc / IIT"),
    ("Indian Institute of Technology Delhi", "IIT Delhi", "IISc / IIT"),
    ("Indian Institute of Technology Kharagpur", "IIT Kharagpur", "IISc / IIT"),
    ("Indian Institute of Technology Kanpur", "IIT Kanpur", "IISc / IIT"),
    ("Indian Institute of Technology Roorkee", "IIT Roorkee", "IISc / IIT"),
    ("Indian Institute of Technology Guwahati", "IIT Guwahati", "IISc / IIT"),
    ("Indian Institute of Technology Hyderabad", "IIT Hyderabad", "IISc / IIT"),
    ("Savitribai Phule Pune University", "Pune University", "State university"),
    ("University of Hyderabad", "Univ. of Hyderabad", "State university"),
    ("Osmania University", "Osmania University", "State university"),
    ("Alagappa University", "Alagappa University", "State university"),
    ("Anna University, Chennai", "Anna University", "State university"),
    ("University of Madras", "University of Madras", "State university"),
]


def indian_universities() -> pd.DataFrame:
    """Knowledge exchange between each lab and 15 Indian universities, from the dataset's citation network
    (data/final/citation_network.csv: Indian citing / cited papers, 2016-2026) and co-authorship
    (indian_connections.csv). Same definition as the peer links (global_links.csv):
      papers_citing_lab   = distinct university papers that cite >= 1 of the lab's papers
      papers_cited_by_lab = distinct university papers that >= 1 of the lab's papers cite
    both leaving out papers co-authored with the lab; exchange_ratio = citing / cited_by.
    Institutions are matched by exact name in the ';'-separated lists (no substring matching)."""
    c = pd.read_csv("data/final/citation_network.csv", dtype=str, keep_default_na=False)
    conn = pd.read_csv("data/final/indian_connections.csv", dtype=str, keep_default_na=False)
    src = c["source_inst"].str.split(";").apply(set)
    tgt = c["target_inst"].str.split(";").apply(set)
    rows = []
    for name, short, tier in UNIVERSITIES:
        u_src, u_tgt = src.apply(lambda s: name in s), tgt.apply(lambda s: name in s)
        all_in, all_out = set(), set()
        per_lab = {}
        for lab in LAB_SHORT:
            l_src, l_tgt = src.apply(lambda s: lab in s), tgt.apply(lambda s: lab in s)
            inn = set(c.loc[u_src & l_tgt & ~l_src, "source_doi"])   # university paper cites the lab
            out = set(c.loc[l_src & u_tgt & ~l_tgt, "target_doi"])   # lab paper cites the university
            co = conn[(conn["your_inst"] == lab) & (conn["partner_inst"] == name)]["shared_papers"]
            per_lab[lab] = (len(inn), len(out), int(co.astype(int).sum()) if len(co) else 0)
            all_in |= inn
            all_out |= out
        for lab, (i, o, co) in per_lab.items():
            rows.append({"university": short, "full_name": name, "tier": tier, "lab": lab, "papers_citing_lab": i,
                         "papers_cited_by_lab": o, "exchange_ratio": round(i / o, 2) if o else None, "coauthored_papers": co})
        rows.append({"university": short, "full_name": name, "tier": tier, "lab": "All three",
                     "papers_citing_lab": len(all_in), "papers_cited_by_lab": len(all_out),
                     "exchange_ratio": round(len(all_in) / len(all_out), 2) if all_out else None,
                     "coauthored_papers": sum(v[2] for v in per_lab.values())})
    return pd.DataFrame(rows)


def funnel_table(cfg: dict) -> pd.DataFrame:
    c = pd.read_csv(G / "candidates.csv", dtype={"institution_id": str})
    c["rejected_because"] = c["rejected_because"].fillna("")

    def step(r):
        s = r["rejected_because"]
        if s == "located in another country":
            return "Outside the country"
        if s.startswith("type"):
            return "Rule 2: not a government institute"
        if s.startswith("umbrella"):
            return "Rule 2: umbrella body"
        if s.startswith("not a stand-alone"):
            return "Rule 2b: not a stand-alone institute"
        if "size floor" in s or "largest" in s:
            return "Rule 3: too small"
        return "Similarity tested (rule 4)"
    c["step"] = c.apply(step, axis=1)
    f = c.groupby(["country", "step"]).size().unstack(fill_value=0)
    f["Selected twins"] = c[c["selected_twin_of"].fillna("") != ""].groupby("country").size()
    f = f.fillna(0).astype(int)
    f["Pool (rule 1)"] = c.groupby("country").size()
    cols = ["Pool (rule 1)", "Outside the country", "Rule 2: not a government institute", "Rule 2: umbrella body",
            "Rule 2b: not a stand-alone institute", "Rule 3: too small", "Similarity tested (rule 4)", "Selected twins"]
    f = f.reindex(columns=cols, fill_value=0)
    return f.loc[[n for n in cfg["countries"].values() if n in f.index]].reset_index()


def similarity_table() -> pd.DataFrame:
    c = pd.read_csv(G / "candidates.csv", dtype={"institution_id": str})
    c = c[c["sim_CSIR-NCL"].notna()].copy()
    c["selected_twin_of"] = c["selected_twin_of"].fillna("")
    cols = ["country", "institution_id", "name", "city", "in_scope_papers", "sim_CSIR-NCL", "sim_CSIR-IICT",
            "sim_CSIR-CECRI", "selected_twin_of"]
    return c[cols].sort_values(["country", "in_scope_papers"], ascending=[True, False])


def profiles_table(peers: pd.DataFrame, n_sub: int = 12) -> pd.DataFrame:
    sp = pd.read_csv(G / "subfield_profiles.csv", dtype={"institution_id": str, "subfield_id": str})
    sc = pd.read_csv(G / "scope_subfields.csv", dtype={"subfield_id": str})
    top = sc.head(n_sub)
    rows = []
    for _, p in peers.iterrows():
        g = sp[sp["institution_id"] == p["institution_id"]]
        total = g["papers"].sum()
        for _, s in top.iterrows():
            n = g.loc[g["subfield_id"] == s["subfield_id"], "papers"].sum()
            rows.append({"institution_id": p["institution_id"], "short": p["short"], "group": p["group"],
                         "subfield": s["subfield"], "share_pct": _pct(n, total)})
    return pd.DataFrame(rows)


def run_global_benchmark() -> None:
    if not (G / "bench_by_year.csv").exists():
        logger.warning("data/final/global/bench_by_year.csv missing; run collect steps 22-23 first")
        return
    cfg = _cfg()
    T.mkdir(parents=True, exist_ok=True)
    peers = peers_table(cfg)
    peers.to_csv(T / "global_peers.csv", index=False)
    summ, by_year = summary_tables(peers, cfg)
    summ.to_csv(T / "global_summary.csv", index=False)
    by_year.to_csv(T / "global_by_year.csv", index=False)
    countries_table().to_csv(T / "global_countries.csv", index=False)
    links_table(peers).to_csv(T / "global_links.csv", index=False)
    cr = country_relations()
    cr.to_csv(T / "global_country_relations.csv", index=False)
    funnel_table(cfg).to_csv(T / "global_rule_funnel.csv", index=False)
    similarity_table().to_csv(T / "global_similarity.csv", index=False)
    profiles_table(peers).to_csv(T / "global_profiles.csv", index=False)
    indian_universities().to_csv(T / "global_indian_universities.csv", index=False)
    logger.info(f"Global benchmark tables written ({len(peers)} institutions, {len(cr)} countries)")


if __name__ == "__main__":
    run_global_benchmark()
