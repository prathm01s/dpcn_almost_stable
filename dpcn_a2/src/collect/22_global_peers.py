"""Step 22: choose the global benchmark peers by fixed rules (D-35).

The rules live in config/global_benchmark.yaml and are shown on dashboard/global.html:

Scope   The research subfields (OpenAlex primary_topic.subfield) that together make up
        `scope_coverage` (90%) of the three labs' papers, 2016-2025, articles and reviews.
Rule 1  Candidate pool: per country, the `top_n_by_output` institutions with the most in-scope
        papers (OpenAlex group_by on authorships.institutions.lineage, so a unit's sub-units count
        with it), keeping only institutions located in that country.
Rule 2  Same kind of organisation as CSIR: OpenAlex type government or facility (no universities,
        companies, hospitals). Umbrella bodies (an institution that is the parent of another one
        of another possible peer in the pool, e.g. the whole Chinese Academy of Sciences or the US
        Department of Energy) are dropped: CSIR is compared lab by lab, so its peers are labs too.
Rule 2b A stand-alone institute with its own staff. OpenAlex also types university-hosted labs,
        multi-university consortia, shared user facilities (synchrotrons) and government
        departments as government/facility; these were reviewed by hand and are listed, each with
        its reason, in config/overrides/global_peer_exclusions.csv.
Rule 3  Comparable size: at least `min_size_ratio` x the in-scope papers of our smallest lab.
        The `max_candidates` largest that pass go to the similarity test.
Rule 4  Research-profile similarity: cosine similarity of the subfield counts of all papers
        (2016-2025) between a candidate and each CSIR lab. Per country, the most similar
        (lab, candidate) pair is fixed first, then the next among the remaining labs and
        candidates, and so on: each lab gets one distinct "twin" per country. A pair counts only
        when the similarity is at least `min_similarity`; otherwise that lab has no twin there.

The Indian reference group is fixed in the config (chosen with the team) and measured the same way.

API cost: about 115 group_by / list calls (~$0.012), all cached in data/cache.

Outputs (data/final/global/)
- scope_subfields.csv   subfield_id, subfield, lab_papers, share_pct, cum_share_pct, in_scope
- candidates.csv        every institution in each country's pool with the rule it failed, or its
                        similarity to each lab and whether it was selected
- peers.csv             the final list: group, country, institution_id, name, type, city, twin_of,
                        similarity, in_scope_papers
- subfield_profiles.csv institution_id, subfield_id, subfield, papers (labs, peers, candidates)
"""

import math
from pathlib import Path

import pandas as pd
import yaml

from src.common.http import http_client
from src.common.logging import get_logger

logger = get_logger("22_global_peers")

API = "https://api.openalex.org"
OUT = Path("data/final/global")
LABS = {"ncl": "CSIR-NCL", "iict": "CSIR-IICT", "cecri": "CSIR-CECRI"}


def short(url) -> str:
    return str(url or "").rstrip("/").rsplit("/", 1)[-1]


def load_cfg() -> dict:
    with open("config/global_benchmark.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def lab_ids() -> dict:
    with open("config/institutions.yaml", encoding="utf-8") as f:
        reg = yaml.safe_load(f)
    return {LABS[k]: [short(i) for i in reg[k]["openalex_institution_ids"]] for k in LABS}


def base_filter(cfg: dict) -> str:
    y = cfg["years"]
    return f"publication_year:{y['start']}-{y['end']},type:{'|'.join(cfg['work_types'])}"


def group_by(flt: str, key: str) -> list:
    d = http_client.get_json(f"{API}/works", params={"filter": flt, "group_by": key, "per_page": 200})
    return d.get("group_by", [])


def subfield_vector(inst_ids: list, base: str) -> dict:
    """{subfield_id: (name, papers)} for all papers of the institution (and its sub-units)."""
    rows = group_by(f"authorships.institutions.lineage:{'|'.join(inst_ids)},{base}", "primary_topic.subfield.id")
    return {short(r["key"]): (r.get("key_display_name") or "", int(r["count"]))
            for r in rows if r.get("key") and short(r["key"]) != "unknown"}


def cosine(a: dict, b: dict) -> float:
    keys = set(a) | set(b)
    dot = sum(a.get(k, (0, 0))[1] * b.get(k, (0, 0))[1] for k in keys)
    na = math.sqrt(sum(v[1] ** 2 for v in a.values()))
    nb = math.sqrt(sum(v[1] ** 2 for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def institutions_meta(ids: list) -> pd.DataFrame:
    rows = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        d = http_client.get_json(f"{API}/institutions", params={
            "filter": "openalex_id:" + "|".join(chunk), "per_page": 100,
            "select": "id,display_name,type,country_code,lineage,geo,ror"})
        for r in d.get("results", []):
            rows.append({"institution_id": short(r["id"]), "name": r.get("display_name", ""),
                         "type": r.get("type") or "", "country_code": r.get("country_code") or "",
                         "city": (r.get("geo") or {}).get("city") or "", "ror": r.get("ror") or "",
                         "lineage": [short(x) for x in (r.get("lineage") or [])]})
    return pd.DataFrame(rows)


def assign_twins(sims: pd.DataFrame, n: int, floor: float) -> dict:
    """Greedy one-to-one matching of labs to candidates by highest similarity. {candidate: lab}."""
    pairs = sims.stack().sort_values(ascending=False)  # index (candidate, lab)
    used_c, used_l, out = set(), set(), {}
    for (cand, lab), _ in pairs.items():
        if cand in used_c or lab in used_l or _ < floor:
            continue
        out[cand] = lab
        used_c.add(cand)
        used_l.add(lab)
        if len(out) == n:
            break
    return out


def run_step_22() -> None:
    cfg = load_cfg()
    OUT.mkdir(parents=True, exist_ok=True)
    base = base_filter(cfg)
    labs = lab_ids()

    # Scope from the labs' own subfield profiles
    lab_vec = {lab: subfield_vector(ids, base) for lab, ids in labs.items()}
    comb: dict = {}
    for v in lab_vec.values():
        for k, (name, n) in v.items():
            comb[k] = (name, comb.get(k, (name, 0))[1] + n)
    sc = pd.DataFrame([{"subfield_id": k, "subfield": v[0], "lab_papers": v[1]} for k, v in comb.items()])
    sc = sc.sort_values(["lab_papers", "subfield_id"], ascending=[False, True]).reset_index(drop=True)
    sc["share_pct"] = 100 * sc["lab_papers"] / sc["lab_papers"].sum()
    sc["cum_share_pct"] = sc["share_pct"].cumsum()
    sc["in_scope"] = (sc["cum_share_pct"] - sc["share_pct"]) < 100 * cfg["scope_coverage"]
    sc.round(2).to_csv(OUT / "scope_subfields.csv", index=False)
    scope_ids = sc.loc[sc["in_scope"], "subfield_id"].tolist()
    scope = f"primary_topic.subfield.id:{'|'.join(scope_ids)}"
    logger.info(f"Scope: {len(scope_ids)} subfields cover {sc.loc[sc['in_scope'], 'share_pct'].sum():.1f}% of lab papers")

    lab_scope = {lab: sum(n for k, (_, n) in v.items() if k in set(scope_ids)) for lab, v in lab_vec.items()}
    min_size = cfg["candidates"]["min_size_ratio"] * min(lab_scope.values())
    logger.info(f"Lab in-scope papers {lab_scope}; size floor {min_size:.0f}")

    keep_types = set(cfg["candidates"]["keep_types"])
    ex = pd.read_csv("config/overrides/global_peer_exclusions.csv", dtype=str)
    excluded = dict(zip(ex["institution_id"], ex["reason"]))
    profiles = []
    for lab, v in lab_vec.items():
        profiles += [{"institution_id": "|".join(labs[lab]), "subfield_id": k, "subfield": nm, "papers": n} for k, (nm, n) in v.items()]

    cand_rows, peer_rows = [], []
    for lab, ids in labs.items():
        peer_rows.append({"group": "CSIR lab", "country": "India", "institution_id": "|".join(ids), "name": lab,
                          "type": "facility", "city": "", "twin_of": "", "similarity": 1.0,
                          "in_scope_papers": lab_scope[lab]})

    for cc, cname in cfg["countries"].items():
        pool = group_by(f"authorships.institutions.country_code:{cc},{base},{scope}", "authorships.institutions.lineage")
        pool = pool[: cfg["candidates"]["top_n_by_output"]]
        counts = {short(r["key"]): int(r["count"]) for r in pool}
        meta = institutions_meta(list(counts))
        meta["in_scope_papers"] = meta["institution_id"].map(counts)
        meta = meta.sort_values("in_scope_papers", ascending=False)
        # Umbrella bodies: parents of another pool member that is itself a possible peer
        # (in the country, right type, not excluded by rule 2b).
        real = meta[(meta["country_code"] == cc) & meta["type"].isin(keep_types) & ~meta["institution_id"].isin(excluded)]
        parents = {p for lin, me in zip(real["lineage"], real["institution_id"]) for p in lin if p != me}

        def reason(r):
            if r["country_code"] != cc:
                return "located in another country"
            if r["type"] not in keep_types:
                return f"type {r['type'] or 'unknown'} (rule 2)"
            if r["institution_id"] in excluded:
                return "not a stand-alone institute (rule 2b): " + excluded[r["institution_id"]]
            if r["institution_id"] in parents:
                return "umbrella body of other pool members (rule 2)"
            if r["in_scope_papers"] < min_size:
                return "below size floor (rule 3)"
            return ""
        meta["rejected_because"] = meta.apply(reason, axis=1)
        ok = meta[meta["rejected_because"] == ""].head(cfg["candidates"]["max_candidates"])
        overflow = meta[(meta["rejected_because"] == "") & ~meta["institution_id"].isin(ok["institution_id"])].index
        meta.loc[overflow, "rejected_because"] = f"not among the {cfg['candidates']['max_candidates']} largest that pass (rule 3)"

        sims = {}
        for iid in ok["institution_id"]:
            v = subfield_vector([iid], base)
            profiles += [{"institution_id": iid, "subfield_id": k, "subfield": nm, "papers": n} for k, (nm, n) in v.items()]
            sims[iid] = {lab: cosine(v, lv) for lab, lv in lab_vec.items()}
        sim = pd.DataFrame(sims).T
        twins = assign_twins(sim, cfg["peers_per_country"], cfg["min_similarity"]) if len(sim) else {}

        for _, r in meta.iterrows():
            iid = r["institution_id"]
            row = {"country": cname, "country_code": cc, "institution_id": iid, "name": r["name"], "type": r["type"],
                   "city": r["city"], "ror": r["ror"], "in_scope_papers": r["in_scope_papers"],
                   "rejected_because": r["rejected_because"]}
            for lab in LABS.values():
                row[f"sim_{lab}"] = round(sims[iid][lab], 4) if iid in sims else None
            row["selected_twin_of"] = twins.get(iid, "")
            cand_rows.append(row)
            if iid in twins:
                peer_rows.append({"group": cname, "country": cname, "institution_id": iid, "name": r["name"],
                                  "type": r["type"], "city": r["city"], "twin_of": twins[iid],
                                  "similarity": round(sims[iid][twins[iid]], 4), "in_scope_papers": r["in_scope_papers"]})
        logger.info(f"{cname}: pool {len(meta)}, candidates {len(ok)}, twins {twins}")

    # Indian reference group
    ind = cfg["indian_peers"]
    meta = institutions_meta([p["id"] for p in ind]).set_index("institution_id")
    for p in ind:
        r = meta.loc[p["id"]]
        assert r["country_code"] == "IN", p
        v = subfield_vector([p["id"]], base)
        profiles += [{"institution_id": p["id"], "subfield_id": k, "subfield": nm, "papers": n} for k, (nm, n) in v.items()]
        s = {lab: cosine(v, lv) for lab, lv in lab_vec.items()}
        best = max(s, key=s.get)
        peer_rows.append({"group": "India", "country": "India", "institution_id": p["id"], "name": r["name"],
                          "type": r["type"], "city": r["city"], "twin_of": best, "similarity": round(s[best], 4),
                          "in_scope_papers": sum(n for k, (_, n) in v.items() if k in set(scope_ids))})

    pd.DataFrame(cand_rows).to_csv(OUT / "candidates.csv", index=False)
    pd.DataFrame(peer_rows).to_csv(OUT / "peers.csv", index=False)
    pd.DataFrame(profiles).to_csv(OUT / "subfield_profiles.csv", index=False)
    logger.info(f"Peers: {len(peer_rows)} rows -> {OUT / 'peers.csv'}")


def reapply_exclusions() -> None:
    """Re-apply rule 2b and rule 4 after config/overrides/global_peer_exclusions.csv changed, from the
    saved candidates.csv (no API calls). Exact as long as no excluded institution made another one an
    umbrella body and no candidate is newly promoted into the tested set; otherwise run Step 22 again."""
    cfg = load_cfg()
    ex = pd.read_csv("config/overrides/global_peer_exclusions.csv", dtype=str)
    excluded = dict(zip(ex["institution_id"], ex["reason"]))
    cand = pd.read_csv(OUT / "candidates.csv", dtype={"institution_id": str})
    peers = pd.read_csv(OUT / "peers.csv", dtype={"institution_id": str})
    sim_cols = [f"sim_{lab}" for lab in LABS.values()]
    # Rule order as in run_step_22: country, type, 2b, umbrella, size. A candidate rejected by a later rule
    # only gets the rule 2b reason; one that reached the similarity test also changes the twins.
    why = cand["rejected_because"].fillna("")
    later = why.str.startswith(("umbrella", "below size", "not among"))
    relabel = cand["institution_id"].isin(excluded) & later
    cand.loc[relabel, "rejected_because"] = ["not a stand-alone institute (rule 2b): " + excluded[i] for i in cand.loc[relabel, "institution_id"]]
    for n in cand.loc[relabel, "name"]:
        logger.info(f"Rule 2b reason recorded for {n}")
    newly = cand["institution_id"].isin(excluded) & why.eq("")
    if not newly.any():
        if relabel.any():
            cand.to_csv(OUT / "candidates.csv", index=False)
        logger.info("No new exclusions; candidates.csv and peers.csv unchanged")
        return
    for iid in cand.loc[newly, "institution_id"]:
        logger.info(f"Rule 2b: {cand.loc[cand['institution_id'] == iid, 'name'].iloc[0]} ({iid}) excluded: {excluded[iid]}")
    countries = cand.loc[newly, "country"].unique()
    overflow = cand["rejected_because"].fillna("").str.startswith("not among the")
    if cand.loc[overflow, "country"].isin(countries).any():
        raise RuntimeError("An excluded candidate frees a place in the similarity test; run Step 22 with the API")
    cand.loc[newly, "rejected_because"] = ["not a stand-alone institute (rule 2b): " + excluded[i] for i in cand.loc[newly, "institution_id"]]
    cand.loc[newly, sim_cols] = None

    twins_of = {}
    for cname in countries:
        c = cand[(cand["country"] == cname) & cand[sim_cols[0]].notna()].set_index("institution_id")
        twins = assign_twins(c[sim_cols].rename(columns=lambda x: x[len("sim_"):]), cfg["peers_per_country"], cfg["min_similarity"])
        sel = cand["country"] == cname
        cand.loc[sel, "selected_twin_of"] = cand.loc[sel, "institution_id"].map(twins)
        twins_of[cname] = twins
        logger.info(f"{cname}: twins {twins}")
    old = {(g, i): t for g, i, t in zip(peers["group"], peers["institution_id"], peers["twin_of"])}
    if any(old.get((cname, i)) != lab for cname, tw in twins_of.items() for i, lab in tw.items()):
        raise RuntimeError("The exclusion changes another twin; run Step 22 with the API")
    still_twin = pd.Series([twins_of.get(g, {}).get(i) == t for g, i, t in
                            zip(peers["group"], peers["institution_id"], peers["twin_of"])], index=peers.index)
    out = peers[~peers["group"].isin(countries) | still_twin]
    cand.to_csv(OUT / "candidates.csv", index=False)
    out.to_csv(OUT / "peers.csv", index=False)
    logger.info(f"Peers: {len(out)} rows -> {OUT / 'peers.csv'}")


if __name__ == "__main__":
    import sys
    reapply_exclusions() if "--offline" in sys.argv else run_step_22()
