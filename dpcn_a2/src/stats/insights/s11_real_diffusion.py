"""How Ideas Spread, part 5 (D-44): testing the spreading model on the labs' real citations.

The model (parts 1-3) lets an "idea" pass between co-authors. Here we look at what really happened:
every work a lab paper cites is an idea, and a person ADOPTS it in the year of their first lab paper citing it.

1. Per-tie transmissibility T (the quantity the model's tipping point is about): for every adopter u and every
   co-author v (joint paper in a year <= u's adoption year, v still publishing afterwards, v not yet an adopter),
   T = share of such (tie, idea) pairs where v adopts later. Split by the role of u, by how widely the idea is
   reused, by tie strength, and into "carried" (an earlier adopter is an author of v's adopting paper) and
   "independent" (no earlier adopter on that paper). Compared with the tipping points measured in part 3.
2. Exposure response: the yearly chance that a researcher adopts an idea, by the number k of co-authors who
   adopted it before (k = 0: researchers active in the same subfield as the earlier adopting papers, no adopting
   co-author). Computed on a fixed random sample of ideas (seed 24) with weights, because there are 512,000.
3. Between the labs: share of co-authorship ties linking people of different labs; for each idea reaching a
   second or third lab, whether a person on that lab's first adopting paper had adopted it before or has an
   earlier-adopting co-author ("via a person") or not ("independent"). Ideas are grouped by origin using the
   Global Benchmark: papers of the foreign twins and of the Indian reference institutes the labs cite
   (data/final/global/citation_flows.csv), the labs' own papers, and everything else.

Inputs: data/final/group24_data_extended.csv, data/final/work_references.csv.gz (Step 24),
        data/final/global/citation_flows.csv, stats/tables/global_peers.csv, stats/tables/global_links.csv,
        stats/tables/insights/11_threshold_check.json
Output: stats/tables/insights/11_real_diffusion.json
"""

import bisect
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from src.common.logging import get_logger
from src.stats.insights.common import author_key

logger = get_logger("s11_real_diffusion")
FINAL = Path("data/final")
T_DIR = Path("stats/tables/insights")
SEED = 24
SAMPLE_MULTI, SAMPLE_SINGLE = 0.25, 0.02   # exposure-response sample: ideas cited by >= 2 papers / by 1 paper
ROLE_LABEL = {"faculty": "Faculty (roster scientists)",
              "probable_former_faculty": "Frequent non-roster authors",
              "affiliated_author": "Students, project staff and other authors"}
BUCKETS = ["2-4 papers", "5-9 papers", "10+ papers"]
STRENGTH = ["1 joint paper", "2-4 joint papers", "5+ joint papers"]
NEVER = 10 ** 6


def bucket(n: int) -> str:
    return "1 paper" if n == 1 else "2-4 papers" if n <= 4 else "5-9 papers" if n <= 9 else "10+ papers"


def strength(w: int) -> str:
    return "1 joint paper" if w == 1 else "2-4 joint papers" if w <= 4 else "5+ joint papers"


# ---------------------------------------------------------------- inputs
def load_inputs():
    """papers: list of dicts (wid, year, persons, labs, subfield); refs: {wid: [W...]}; role: {person: author_role}."""
    ext = pd.read_csv(FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False,
                      usecols=["work_id", "year", "institution", "subfield", "author", "author_openalex_id", "faculty_id", "author_role"])
    ext["person"] = author_key(ext)
    ext["wid"] = ext["work_id"].str.rsplit("/", n=1).str[-1]
    g = ext.groupby("wid", sort=True)
    papers = [{"wid": w, "year": int(d["year"].iat[0]), "subfield": d["subfield"].iat[0],
               "persons": tuple(sorted(set(d["person"]))), "labs": tuple(sorted(set(d["institution"])))} for w, d in g]
    role = ext.groupby("person")["author_role"].agg(lambda s: s.value_counts().sort_index().idxmax()).to_dict()
    ref = pd.read_csv(FINAL / "work_references.csv.gz", dtype=str)
    refs = ref.groupby("work_id")["referenced_work_id"].apply(list).to_dict()
    return papers, refs, role


def index(papers, refs):
    """Shared indexes: ties {(a, b): sorted years of joint papers}, last publishing year per person, idea -> paper indexes."""
    ties = defaultdict(list)
    last = defaultdict(int)
    for p in papers:
        for a in p["persons"]:
            last[a] = max(last[a], p["year"])
            for b in p["persons"]:
                if a != b:
                    ties[(a, b)].append(p["year"])
    for v in ties.values():
        v.sort()
    nbr = defaultdict(list)
    for (a, b), ys in ties.items():
        nbr[a].append((b, ys))
    by_idea = defaultdict(list)
    for i, p in enumerate(papers):
        for r in dict.fromkeys(refs.get(p["wid"], [])):
            by_idea[r].append(i)
    return ties, nbr, last, by_idea


def first_adoption(papers, idx):
    first = {}
    for i in idx:
        for u in papers[i]["persons"]:
            if u not in first or papers[i]["year"] < first[u]:
                first[u] = papers[i]["year"]
    return first


def carried_set(papers, idx, first):
    """People whose adopting paper has an author who adopted the idea in an earlier year."""
    out = set()
    for i in idx:
        y = papers[i]["year"]
        ps = papers[i]["persons"]
        if any(first[q] < y for q in ps):
            out.update(v for v in ps if first[v] == y)
    return out


# ---------------------------------------------------------------- 1. per-tie transmissibility
def transmissibility(papers, by_idea, nbr, ties, last, role):
    """Per-tie transmissibility T, overall and split by idea reuse, role of the earlier adopter and tie strength."""
    den, car, ind = Counter(), Counter(), Counter()
    live_cache = {}

    def live_profile(u, t):
        """Co-authors of u with a joint paper in a year <= t who still publish after t, counted by tie strength at t."""
        k = (u, t)
        if k not in live_cache:
            c = Counter()
            for v, ys in nbr.get(u, ()):
                w = bisect.bisect_right(ys, t)
                if w and last[v] > t:
                    c[strength(w)] += 1
            live_cache[k] = c
        return live_cache[k]

    for W, idx in by_idea.items():
        b = bucket(len(idx))
        first = first_adoption(papers, idx)
        carried = carried_set(papers, idx, first) if len(idx) > 1 else set()
        for u, tu in first.items():
            r = role.get(u)
            prof = Counter(live_profile(u, tu))
            later = []
            for v, tv in first.items():
                if v == u:
                    continue
                ys = ties.get((u, v))
                if not ys:
                    continue
                w = bisect.bisect_right(ys, tu)
                if not w:
                    continue
                if tv <= tu:
                    if last[v] > tu:
                        prof[strength(w)] -= 1      # already an adopter: not at risk
                else:
                    later.append((v, strength(w)))  # adopts later (and so publishes after tu): at risk and a transmission
            n = sum(prof.values())
            for key in (("all", "all", "all"), (b, "all", "all"), ("all", r, "all"), (b, r, "all")):
                den[key] += n
            for s, c in prof.items():
                den[("all", "all", s)] += c
            for v, s in later:
                tgt = car if v in carried else ind
                for key in (("all", "all", "all"), (b, "all", "all"), ("all", r, "all"), (b, r, "all"), ("all", "all", s)):
                    tgt[key] += 1

    def rate(key):
        d = den[key]
        return {"pairs": int(d), "carried": int(car[key]), "independent": int(ind[key]),
                "T_pct": round(100 * (car[key] + ind[key]) / d, 4) if d else None,
                "T_carried_pct": round(100 * car[key] / d, 4) if d else None,
                "T_independent_pct": round(100 * ind[key] / d, 4) if d else None}

    roles = list(ROLE_LABEL)
    return {
        "overall": rate(("all", "all", "all")),
        "by_bucket": {b: rate((b, "all", "all")) for b in BUCKETS},
        "by_role": {r: rate(("all", r, "all")) for r in roles},
        "by_bucket_role": {b: {r: rate((b, r, "all")) for r in roles} for b in BUCKETS},
        "by_strength": {s: rate(("all", "all", s)) for s in STRENGTH},
    }


# ---------------------------------------------------------------- 2. exposure response
def exposure_response(papers, by_idea, nbr, ties, sample_multi=SAMPLE_MULTI, sample_single=SAMPLE_SINGLE, seed=SEED):
    act, act_sub = defaultdict(set), defaultdict(lambda: defaultdict(set))
    for p in papers:
        act[p["year"]].update(p["persons"])
        act_sub[p["year"]][p["subfield"]].update(p["persons"])
    y_max = max(p["year"] for p in papers)
    ideas = sorted(by_idea)
    multi = [W for W in ideas if len(by_idea[W]) >= 2]
    single = [W for W in ideas if len(by_idea[W]) == 1]
    rng = random.Random(seed)
    pick = rng.sample(multi, round(len(multi) * sample_multi)) + rng.sample(single, round(len(single) * sample_single))
    N, A, I = Counter(), Counter(), Counter()
    for W in pick:
        idx = by_idea[W]
        wgt = 1 / sample_multi if len(idx) >= 2 else 1 / sample_single
        first = first_adoption(papers, idx)
        carried = carried_set(papers, idx, first) if len(idx) > 1 else set()
        t0 = min(first.values())
        for t in range(t0 + 1, y_max + 1):
            prior = {u for u, ty in first.items() if ty < t}
            new = {u for u, ty in first.items() if ty == t}
            k = Counter()
            for u in prior:
                for v, ys in nbr.get(u, ()):
                    if ys[0] < t and v not in prior and v in act[t]:
                        k[v] += 1
            subs = {papers[i]["subfield"] for i in idx if papers[i]["year"] < t}
            pool = set().union(*(act_sub[t][s] for s in subs)) - prior - set(k)
            N[0] += wgt * len(pool)
            hit0 = new & pool
            A[0] += wgt * len(hit0)
            I[0] += wgt * len(hit0 - carried)
            for v, kv in k.items():
                kk = min(kv, 3)
                N[kk] += wgt
                if v in new:
                    A[kk] += wgt
                    if v not in carried:
                        I[kk] += wgt
    base, base_i = A[0] / N[0], I[0] / N[0]
    out = []
    for kk in range(4):
        out.append({"k": "3+" if kk == 3 else str(kk), "at_risk": round(N[kk]), "adopted": round(A[kk]), "independent": round(I[kk]),
                    "P_pct": round(100 * A[kk] / N[kk], 4), "P_independent_pct": round(100 * I[kk] / N[kk], 4),
                    "lift": round(A[kk] / N[kk] / base, 2), "lift_independent": round(I[kk] / N[kk] / base_i, 2),
                    "carried_share_pct": round(100 * (A[kk] - I[kk]) / A[kk], 1) if A[kk] else None})
    return {"sample": {"ideas_multi": len(multi), "ideas_single": len(single), "fraction_multi": sample_multi,
                       "fraction_single": sample_single, "seed": seed}, "rows": out}


# ---------------------------------------------------------------- 3. between the labs, by origin of the idea
def idea_origins(own_ids):
    peers = pd.read_csv("stats/tables/global_peers.csv", dtype=str)
    grp = dict(zip(peers["institution_id"], peers["group"]))
    fl = pd.read_csv(FINAL / "global" / "citation_flows.csv", dtype=str)
    fl = fl[fl["direction"] == "lab_cites_peer"]
    origin = {}
    for w, inst in zip(fl["work_id"], fl["institution_id"]):
        o = "indian" if grp.get(inst) == "India" else "foreign"
        if origin.get(w) != "foreign":
            origin[w] = o
    for w in own_ids:
        origin[w] = "own"
    return origin


ORIGIN_LABEL = {"foreign": "Papers of the foreign twins", "indian": "Papers of the Indian reference institutes",
                "own": "The labs' own papers", "other": "Everything else the labs cite"}


def between_labs(papers, by_idea, nbr, role, origin):
    lab_count = defaultdict(Counter)
    for p in papers:
        for u in p["persons"]:
            for lab in p["labs"]:
                lab_count[u][lab] += 1
    home = {u: sorted(c.items(), key=lambda x: (-x[1], x[0]))[0][0] for u, c in lab_count.items()}
    pairs = {(a, b) for a, nb in nbr.items() for b, _ in nb if a < b}
    cross = sum(home[a] != home[b] for a, b in pairs)
    stats = defaultdict(lambda: Counter())
    for W, idx in by_idea.items():
        o = origin.get(W, "other")
        s = stats[o]
        idx = sorted(idx, key=lambda i: papers[i]["year"])
        t0 = papers[idx[0]]["year"]
        s["ideas"] += 1
        s["citing_papers"] += len(idx)
        s["single_use"] += len(idx) == 1
        s["entry_with_faculty"] += any(role.get(u) == "faculty" for i in idx if papers[i]["year"] == t0 for u in papers[i]["persons"])
        lab_first = {}
        for i in idx:
            for lab in papers[i]["labs"]:
                lab_first.setdefault(lab, papers[i]["year"])
        s["multi_lab"] += len(lab_first) > 1
        first_lab_year = min(lab_first.values())
        for lab, ty in lab_first.items():
            if ty == first_lab_year:
                continue
            earlier = {u for i in idx if papers[i]["year"] < ty for u in papers[i]["persons"]}
            people = {u for i in idx if papers[i]["year"] == ty and lab in papers[i]["labs"] for u in papers[i]["persons"]}
            via = any(u in earlier or any(v in earlier and ys[0] < ty for v, ys in nbr.get(u, ())) for u in people)
            s["later_lab_adoptions"] += 1
            s["via_person"] += via
    table = []
    for o in ["foreign", "indian", "own", "other"]:
        s = stats[o]
        n = s["ideas"]
        table.append({"origin": o, "label": ORIGIN_LABEL[o], "ideas": n,
                      "single_use_pct": round(100 * s["single_use"] / n, 1) if n else None,
                      "mean_citing_papers": round(s["citing_papers"] / n, 2) if n else None,
                      "multi_lab_pct": round(100 * s["multi_lab"] / n, 1) if n else None,
                      "entry_with_faculty_pct": round(100 * s["entry_with_faculty"] / n, 1) if n else None,
                      "later_lab_adoptions": s["later_lab_adoptions"],
                      "via_person_pct": round(100 * s["via_person"] / s["later_lab_adoptions"], 1) if s["later_lab_adoptions"] else None})
    return {"ties": len(pairs), "cross_lab_ties": cross, "cross_lab_pct": round(100 * cross / len(pairs), 2), "by_origin": table}


# ---------------------------------------------------------------- run
def run() -> dict:
    papers, refs, role = load_inputs()
    ties, nbr, last, by_idea = index(papers, refs)
    use = Counter(bucket(len(ix)) for ix in by_idea.values())
    thr = json.loads((T_DIR / "11_threshold_check.json").read_text(encoding="utf-8"))["networks"]
    logger.info(f"{len(by_idea):,} ideas cited {sum(len(ix) for ix in by_idea.values()):,} times by {len(papers):,} papers")
    tr = transmissibility(papers, by_idea, nbr, ties, last, role)
    logger.info(f"per-tie transmissibility {tr['overall']['T_pct']}%")
    ex = exposure_response(papers, by_idea, nbr, ties)
    origin = idea_origins({p["wid"] for p in papers})
    bl = between_labs(papers, by_idea, nbr, role, origin)
    # people and ties by role
    deg, strong = Counter(), Counter()
    for (a, b), ys in ties.items():
        deg[role.get(a)] += 1
        strong[role.get(a)] += len(ys) >= 5
    n_people = Counter(role.get(u) for u in {u for p in papers for u in p["persons"]})
    roles = {r: {"label": ROLE_LABEL[r], "people": n_people[r], "coauthors_per_person": round(deg[r] / n_people[r], 1),
                 "strong_tie_pct": round(100 * strong[r] / deg[r], 1) if deg[r] else None} for r in ROLE_LABEL}
    links = pd.read_csv("stats/tables/global_links.csv")
    fl = links[links["group"] != "India"]
    out = {
        "ideas": {"n": len(by_idea), "citations": int(sum(len(ix) for ix in by_idea.values())), "papers": len(papers),
                  "papers_with_references": sum(1 for p in papers if refs.get(p["wid"])),
                  "by_reuse": {k: use.get(k, 0) for k in ["1 paper", *BUCKETS]},
                  "single_use_pct": round(100 * use["1 paper"] / len(by_idea), 1)},
        "tipping_points": {"full_coauthorship": thr["full_coauthorship"]["T_peak_simulated"],
                           "faculty_coauthorship": thr["faculty_coauthorship"]["T_peak_simulated"]},
        "transmissibility": tr,
        "roles": roles,
        "exposure": ex,
        "between_labs": bl,
        "global_link": {"foreign_peer_papers_cited": int(fl["peer_papers_cited_by_lab"].sum()),
                        "foreign_coauthored_papers": int(fl["coauthored_papers"].sum()),
                        "foreign_peers": int(fl["institution_id"].nunique())},
        "method": {"adoption": "first lab paper of a person citing the work", "max_year": max(p["year"] for p in papers),
                   "live_coauthor": "co-author with a joint paper in a year <= the adopter's adoption year and a lab paper after it",
                   "exposure_baseline": "researchers active that year in a subfield of the earlier adopting papers, no adopting co-author",
                   "sample_seed": SEED},
    }
    T_DIR.mkdir(parents=True, exist_ok=True)
    (T_DIR / "11_real_diffusion.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Saved stats/tables/insights/11_real_diffusion.json")
    return out


if __name__ == "__main__":
    run()
