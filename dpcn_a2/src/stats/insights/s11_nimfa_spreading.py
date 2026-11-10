"""Insight 11 (part 2): mean-field (NIMFA) vs Monte Carlo SI spreading on four networks, by lab of origin
and inside each lab.

Networks (all built from data/final, see build_networks):
- full_coauthorship   every lab author incl. students and project staff, keyed by OpenAlex author ID
                      (src/stats/insights/common.coauthor_graph: largest component, papers with > 30
                      authors dropped). The same graph as part 1 (s11_information_diffusion).
- faculty_coauthorship roster scientists with >= 1 faculty co-author (src/stats/networks.py, D-33)
- full_citation       papers, edge cited -> citing (information flows forward in time); acyclic apart
                      from a few mutual citations
- faculty_citation    roster scientists, edge cited scientist -> citing scientist

Transmission probability on an edge u -> v:  beta_uv = beta0 * max(FLOOR, cos(u, v)), where cos is the
cosine similarity of the two subfield profiles (paper counts per OpenAlex subfield; for a paper its own
subfield, so cos = 1 for the same subfield and 0 otherwise). A node without a profile uses NEUTRAL_COS.

For every network and target field (researchers / papers active in the field; "Combined" = everyone):
- the same seeds (the SEEDS_PER_RUN best-connected faculty or papers in the field) drive both models;
- Monte Carlo SI: MC_RUNS_PER_SEED independent runs per seed, MAX_STEPS steps, numpy RandomState(SEED);
- NIMFA (discrete time, individual-based mean field, Van Mieghem et al.):
      x_i(t+1) = x_i(t) + (1 - x_i(t)) * [1 - prod_{j -> i} (1 - beta_ji x_j(t))],   x_seed(0) = 1,
  computed exactly (vectorised over edges) from each seed;
- T50 = first step at which >= 50% of the target set has adopted, per run (MC) or per seed (NIMFA);
  reported as the censored median (None = the median run/seed does not reach 50% within MAX_STEPS);
- gap(t) = NIMFA(t) - MC(t) in percentage points. Mean field ignores the positive correlation between
  neighbours' states, so it is expected to over-estimate spreading; the gap's minimum is reported so the
  direction can be checked rather than assumed;
- super-spreaders: seeds ranked by expected adopters at step EARLY_STEP under NIMFA (at step 15 nearly
  every seed saturates the network, so a late count cannot separate them), with the Monte Carlo mean at
  the same step and the Spearman correlation of the two rankings as a check.

Structural thresholds (meaningful for spreading with recovery, SIS/SIR; plain SI has none):
undirected: <k>/<k^2> (heterogeneous mean field) and 1/lambda_max (quenched mean field);
directed: 1/lambda_max of the adjacency matrix, None when lambda_max = 0 (acyclic network).

Outputs (stats/tables/insights/):
- 11_nimfa_vs_si_comparison.json  per network: size, thresholds, per field curves, T50, gap, spreaders;
                                   plus overlay_comparison, seed_origins, intra_institute
- 11_simulation_grid_metrics.csv  one row per network x field
- 11_seed_origin_comparison.csv, 11_intra_institute_comparison.csv
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.linalg import eigs
from scipy.stats import spearmanr

from src.common.logging import get_logger
from src.stats.insights.common import author_key, coauthor_graph, ordered_subgraph
from src.stats.networks import corpus_dois, incorpus_citation_edges, labelled_faculty_graphs

logger = get_logger("s11_nimfa_spreading")

DATA_FINAL = Path("data/final")
TABLES_DIR = Path("stats/tables/insights")
SEED = 24
MAX_STEPS = 15
BETA_BASE = 0.20
FLOOR = 0.1          # minimum similarity factor: unrelated co-authors still pass ideas on, at 10% of beta0
NEUTRAL_COS = 0.5    # profile missing
SEEDS_PER_RUN = 15
MC_RUNS_PER_SEED = 20
EARLY_STEP = 3

LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
INST_KEYS = {"CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri"}
TARGET_FIELDS = [
    ("Chemistry", "Chemistry"),
    ("Materials Science", "Materials"),
    ("Engineering", "Engineering"),
    ("Energy", "Energy"),
    ("Biochemistry, Genetics and Molecular Biology", "Biochemistry"),
    ("Medicine", "Medicine"),
    ("All fields", "Combined"),
]
NETWORK_NAMES = {
    "full_coauthorship": "Full co-authorship (all authors)",
    "faculty_coauthorship": "Faculty co-authorship",
    "full_citation": "Paper citation",
    "faculty_citation": "Faculty citation",
}


# --------------------------------------------------------------------------- helpers
def censored_median(values: List[Optional[float]]) -> Optional[float]:
    """Median where None = not reached within MAX_STEPS; None if the median itself is not reached."""
    if not values:
        return None
    m = float(np.median([np.inf if v is None else v for v in values]))
    return None if np.isinf(m) else round(m, 1)


def first_reach(curve: np.ndarray, level: float = 0.5) -> Optional[int]:
    hit = np.nonzero(curve >= level)[0]
    return int(hit[0]) if len(hit) else None


def thresholds(G: nx.Graph) -> Dict[str, Any]:
    """Structural spreading thresholds (see module docstring)."""
    out: Dict[str, Any] = {"directed": G.is_directed()}
    if G.number_of_edges() == 0:
        return {**out, "k_mean": 0.0, "k2_mean": 0.0, "beta_c_hmf": None, "beta_c_sir": None,
                "lambda_max": 0.0, "beta_c_qmf": None}
    if not G.is_directed():
        deg = np.array([d for _, d in G.degree()], dtype=float)
        k1, k2 = deg.mean(), (deg ** 2).mean()
        out.update(k_mean=round(k1, 2), k2_mean=round(k2, 2), beta_c_hmf=round(k1 / k2, 4),
                   beta_c_sir=round(k1 / (k2 - k1), 4) if k2 > k1 else None)
    else:
        deg = np.array([d for _, d in G.in_degree()], dtype=float)
        out.update(k_mean=round(deg.mean(), 2), k2_mean=round((deg ** 2).mean(), 2), beta_c_hmf=None, beta_c_sir=None)
    A = nx.adjacency_matrix(G, weight=None).astype(float)
    try:
        lam = float(np.real(eigs(A, k=1, which="LR", return_eigenvectors=False, v0=np.ones(A.shape[0]))[0]))
    except Exception:  # dense fallback for very small graphs
        lam = float(np.max(np.real(np.linalg.eigvals(A.toarray()))))
    lam = 0.0 if abs(lam) < 1e-6 else lam
    out.update(lambda_max=round(lam, 4), beta_c_qmf=round(1.0 / lam, 4) if lam > 1e-6 else None)
    return out


def profile_vectors(keys: pd.Series, subfields: pd.Series, fields: pd.Series):
    """Unit subfield vectors and field shares per key (one row per paper x person)."""
    subs = sorted(set(subfields) - {""})
    idx = {s: i for i, s in enumerate(subs)}
    counts: Dict[str, np.ndarray] = defaultdict(lambda: np.zeros(len(subs)))
    fcount: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total: Dict[str, int] = defaultdict(int)
    for k, s, f in zip(keys, subfields, fields):
        if not k:
            continue
        total[k] += 1
        if s in idx:
            counts[k][idx[s]] += 1
        if f:
            fcount[k][f] += 1
    vecs = {k: v / np.linalg.norm(v) for k, v in counts.items() if np.linalg.norm(v) > 0}
    shares = {k: {f: n / total[k] for f, n in fc.items()} for k, fc in fcount.items()}
    return vecs, shares


def edge_lists(G: nx.Graph, vecs: Dict[str, np.ndarray]):
    """Index arrays (src, dst, beta) for every directed transmission edge, nodes in G's order."""
    nodes = list(G.nodes())
    pos = {n: i for i, n in enumerate(nodes)}
    pairs = list(G.edges()) if G.is_directed() else [e for u, v in G.edges() for e in ((u, v), (v, u))]
    src = np.fromiter((pos[u] for u, _ in pairs), dtype=np.int64, count=len(pairs))
    dst = np.fromiter((pos[v] for _, v in pairs), dtype=np.int64, count=len(pairs))
    cos = np.array([float(vecs[u] @ vecs[v]) if (u in vecs and v in vecs) else NEUTRAL_COS for u, v in pairs])
    beta = np.minimum(1.0, BETA_BASE * np.maximum(FLOOR, cos))
    return nodes, pos, src, dst, beta


def nimfa(n: int, src, dst, beta, seed_idx: int, target_mask: np.ndarray, steps: int = MAX_STEPS):
    """Exact discrete-time NIMFA from one seed. Returns (target fraction per step, expected adopters per step)."""
    x = np.zeros(n)
    x[seed_idx] = 1.0
    n_t = max(1, int(target_mask.sum()))
    frac, total = [x[target_mask].sum() / n_t], [x.sum()]
    for _ in range(steps):
        log_safe = np.log1p(-np.minimum(beta * x[src], 1 - 1e-15))
        p_none = np.exp(np.bincount(dst, weights=log_safe, minlength=n))
        x = x + (1 - x) * (1 - p_none)
        frac.append(x[target_mask].sum() / n_t)
        total.append(x.sum())
    return np.array(frac), np.array(total)


def mc_si(n: int, out_adj: List[List[Tuple[int, float]]], seed_idx: int, target_mask: np.ndarray, runs: int,
          rng: np.random.RandomState, steps: int = MAX_STEPS):
    """Discrete-time SI, `runs` independent runs from one seed. Returns per-run target-fraction curves and
    per-run adopter counts. Nodes are visited in index order so results do not depend on hashing."""
    n_t = max(1, int(target_mask.sum()))
    curves = np.zeros((runs, steps + 1))
    totals = np.zeros((runs, steps + 1))
    for r in range(runs):
        infected = np.zeros(n, dtype=bool)
        infected[seed_idx] = True
        active = [seed_idx]
        n_inf, n_tgt = 1, int(target_mask[seed_idx])
        curves[r, 0], totals[r, 0] = n_tgt / n_t, 1
        for t in range(1, steps + 1):
            new = []
            still = []
            for u in active:
                susceptible = False
                for v, p in out_adj[u]:
                    if not infected[v]:
                        susceptible = True
                        if rng.random_sample() < p:
                            infected[v] = True
                            new.append(v)
                if susceptible:
                    still.append(u)
            n_inf += len(new)
            n_tgt += int(target_mask[new].sum()) if new else 0
            curves[r, t], totals[r, t] = n_tgt / n_t, n_inf
            active = sorted(set(still) | set(new))
            if not active:
                curves[r, t:], totals[r, t:] = curves[r, t], totals[r, t]
                break
    return curves, totals


def simulate(G: nx.Graph, vecs, target_nodes, seeds, runs_per_seed: int = MC_RUNS_PER_SEED,
             seed_names: Optional[Dict[str, str]] = None, with_mc: bool = True) -> Dict[str, Any]:
    """Both models from the same seeds on the same edges."""
    nodes, pos, src, dst, beta = edge_lists(G, vecs)
    n = len(nodes)
    target_mask = np.zeros(n, dtype=bool)
    target_mask[[pos[v] for v in target_nodes if v in pos]] = True
    out_adj: List[List[Tuple[int, float]]] = [[] for _ in range(n)]
    for s, d, b in zip(src, dst, beta):
        out_adj[s].append((int(d), float(b)))
    rng = np.random.RandomState(SEED)

    nim_curves, nim_t50, mc_curves, mc_t50, per_seed = [], [], [], [], []
    for s in seeds:
        i = pos[s]
        fr, tot = nimfa(n, src, dst, beta, i, target_mask)
        nim_curves.append(fr)
        nim_t50.append(first_reach(fr))
        row = {"name": (seed_names or {}).get(s, s), "lab": G.nodes[s].get("lab", ""),
               "degree": int(G.out_degree(s) if G.is_directed() else G.degree(s)),
               "nimfa_adopters_early": round(float(tot[EARLY_STEP]), 1), "nimfa_adopters_final": round(float(tot[-1]), 1)}
        if with_mc:
            c, t = mc_si(n, out_adj, i, target_mask, runs_per_seed, rng)
            mc_curves.append(c)
            mc_t50 += [first_reach(r) for r in c]
            row["mc_adopters_early"] = round(float(t[:, EARLY_STEP].mean()), 1)
        per_seed.append(row)

    nim = np.mean(nim_curves, axis=0) * 100
    res: Dict[str, Any] = {
        "target_population": int(target_mask.sum()), "n_seeds": len(seeds),
        "nimfa_curve": np.round(nim, 2).tolist(), "nimfa_t50": censored_median(nim_t50),
        "nimfa_final_reach": round(float(nim[-1]), 2),
    }
    if with_mc:
        mc = np.mean(np.vstack(mc_curves), axis=0) * 100
        gap = nim - mc
        ranks_n = [r["nimfa_adopters_early"] for r in per_seed]
        ranks_m = [r["mc_adopters_early"] for r in per_seed]
        rho = spearmanr(ranks_n, ranks_m).correlation if len(seeds) > 2 and np.std(ranks_m) > 0 else None
        res.update({
            "mc_runs": len(seeds) * runs_per_seed, "mc_curve": np.round(mc, 2).tolist(), "mc_t50": censored_median(mc_t50),
            "mc_final_reach": round(float(mc[-1]), 2), "gap_curve": np.round(gap, 2).tolist(),
            "mean_gap": round(float(gap.mean()), 2), "min_gap": round(float(gap.min()), 2), "max_gap": round(float(gap.max()), 2),
            "rank_agreement_spearman": None if rho is None or np.isnan(rho) else round(float(rho), 3),
        })
    res["super_spreaders"] = sorted(per_seed, key=lambda r: (-r["nimfa_adopters_early"], r["name"]))[:5]
    return res


def lab_subgraph(G: nx.Graph, members) -> nx.Graph:
    """One lab's members in G's node order; for an undirected network its largest connected part."""
    if G.is_directed():
        keep = set(members)
        H = nx.DiGraph()
        H.add_nodes_from((n, G.nodes[n]) for n in G if n in keep)
        H.add_edges_from((u, v) for u, v in G.edges() if u in keep and v in keep)
        return H
    H = ordered_subgraph(G, members)
    return ordered_subgraph(H, max(nx.connected_components(H), key=len)) if len(H) else H


def top_by_degree(G: nx.Graph, cands, k: int) -> List[str]:
    deg = (lambda n: G.out_degree(n)) if G.is_directed() else (lambda n: G.degree(n))
    return sorted(cands, key=lambda n: (-deg(n), str(n)))[:k]


# --------------------------------------------------------------------------- networks
def build_networks():
    ext = pd.read_csv(DATA_FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    fm = pd.read_csv(DATA_FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    cite = incorpus_citation_edges(pd.read_csv(DATA_FINAL / "citation_network.csv", dtype=str, keep_default_na=False),
                                   corpus_dois(ext))
    FA, FC, _, labels = labelled_faculty_graphs(ext, fm, cite)

    # profiles: people by OpenAlex author ID; faculty by faculty_id (-> display label); papers by DOI
    ext["key"] = author_key(ext)
    p_vecs, p_shares = profile_vectors(ext["key"], ext["subfield"], ext["field"])
    fac_rows = ext[ext["faculty_id"].isin(labels)]
    f_vecs, f_shares = profile_vectors(fac_rows["faculty_id"].map(labels), fac_rows["subfield"], fac_rows["field"])
    papers = ext[ext["doi"] != ""].drop_duplicates("doi")
    paper_vecs = {}
    subs = sorted(set(papers["subfield"]) - {""})
    for d, s in zip(papers["doi"], papers["subfield"]):
        if s:
            v = np.zeros(len(subs))
            v[subs.index(s)] = 1.0
            paper_vecs[d] = v
    paper_field = dict(zip(papers["doi"], papers["field"]))
    paper_labs = ext[ext["doi"] != ""].groupby("doi")["institution"].agg(lambda s: sorted(set(s)))

    G1 = coauthor_graph()
    # ordered_subgraph keeps the parent's node order; G.subgraph() iterates in set order, which changes with
    # PYTHONHASHSEED and would change which random number each node gets
    G2 = ordered_subgraph(FA, [n for n, d in FA.degree() if d > 0])
    G3 = nx.DiGraph()
    G3.add_edges_from(zip(cite["target_doi"], cite["source_doi"]))  # cited -> citing
    for n in G3:
        G3.nodes[n]["lab"] = "; ".join(paper_labs.get(n, []))
    G4 = nx.DiGraph()
    G4.add_nodes_from(FC.nodes(data=True))
    G4.add_edges_from((v, u) for u, v in FC.edges())  # FC: u cites v -> idea flows v -> u
    G4.remove_nodes_from([n for n, d in G4.degree() if d == 0])

    is_fac = {n for n in G1 if G1.nodes[n].get("is_faculty")}
    nets = {
        "full_coauthorship": dict(G=G1, vecs=p_vecs, kind="people",
                                  in_field=lambda n, f: p_shares.get(n, {}).get(f, 0) > 0, seed_pool=is_fac),
        "faculty_coauthorship": dict(G=G2, vecs=f_vecs, kind="people",
                                     in_field=lambda n, f: f_shares.get(n, {}).get(f, 0) > 0, seed_pool=set(G2)),
        "full_citation": dict(G=G3, vecs=paper_vecs, kind="papers",
                              in_field=lambda n, f: paper_field.get(n) == f, seed_pool=set(G3)),
        "faculty_citation": dict(G=G4, vecs=f_vecs, kind="people",
                                 in_field=lambda n, f: f_shares.get(n, {}).get(f, 0) > 0, seed_pool=set(G4)),
    }
    names = {n: G1.nodes[n].get("name", n) for n in G1}
    return nets, names, paper_labs


# --------------------------------------------------------------------------- main
def run_all_simulations() -> Dict[str, Any]:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    nets, names, paper_labs = build_networks()
    out: Dict[str, Any] = {"parameters": {
        "beta0": BETA_BASE, "similarity_floor": FLOOR, "neutral_similarity": NEUTRAL_COS, "max_steps": MAX_STEPS,
        "seeds_per_run": SEEDS_PER_RUN, "mc_runs_per_seed": MC_RUNS_PER_SEED, "early_step": EARLY_STEP, "rng_seed": SEED}}
    grid = []
    for key, net in nets.items():
        G = net["G"]
        th = thresholds(G)
        res = {"network_key": key, "network_name": NETWORK_NAMES[key], "kind": net["kind"],
               "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "thresholds": th, "fields": {}}
        if G.is_directed():
            res["is_acyclic"] = nx.is_directed_acyclic_graph(G)
            res["nodes_in_cycles"] = int(sum(len(c) for c in nx.strongly_connected_components(G) if len(c) > 1))
        logger.info(f"{key}: {res['nodes']:,} nodes, {res['edges']:,} edges, thresholds {th}")
        for field, short in TARGET_FIELDS:
            target = set(G) if short == "Combined" else {n for n in G if net["in_field"](n, field)}
            if not target:
                continue
            seeds = top_by_degree(G, [n for n in target if n in net["seed_pool"]] or list(target), SEEDS_PER_RUN)
            r = simulate(G, net["vecs"], target, seeds, seed_names=names)
            r["field_name"] = field
            res["fields"][short] = r
            grid.append({"network": key, "field": short, "target_nodes": r["target_population"], "seeds": r["n_seeds"],
                         "mc_runs": r["mc_runs"], "mc_t50": r["mc_t50"], "nimfa_t50": r["nimfa_t50"],
                         "mc_final_reach": r["mc_final_reach"], "nimfa_final_reach": r["nimfa_final_reach"],
                         "mean_gap": r["mean_gap"], "min_gap": r["min_gap"], "max_gap": r["max_gap"],
                         "rank_agreement_spearman": r["rank_agreement_spearman"],
                         "beta_c_hmf": th["beta_c_hmf"], "beta_c_qmf": th["beta_c_qmf"]})
            logger.info(f"  {short}: MC T50 {r['mc_t50']} | NIMFA T50 {r['nimfa_t50']} | gap {r['min_gap']}..{r['max_gap']}")
        out[key] = res

    out["overlay_comparison"] = {
        f: {f"{k}_{m}": out[k]["fields"][f][f"{m}_curve"] for k in nets for m in ("mc", "nimfa")}
        for f in ("Chemistry", "Combined")}

    # Lab of origin: the 10 best-connected faculty of each lab as seeds, whole network as target
    seed_rows, origins = [], {}
    for key in ("full_coauthorship", "faculty_coauthorship"):
        G, vecs = nets[key]["G"], nets[key]["vecs"]
        origins[key] = {}
        for lab in LABS:
            pool = [n for n in nets[key]["seed_pool"] if G.nodes[n].get("lab") == lab]
            seeds = top_by_degree(G, pool, 10)
            if not seeds:
                continue
            r = simulate(G, vecs, set(G), seeds, seed_names=names)
            origins[key][INST_KEYS[lab]] = {"institute": lab, "seeds_evaluated": len(seeds),
                                            "top_seeds": [names.get(s, s) for s in seeds[:3]], **r}
            seed_rows.append({"network": key, "seed_origin_institute": lab, "seeds_evaluated": len(seeds),
                              "nimfa_t50": r["nimfa_t50"], "mc_t50": r["mc_t50"],
                              "nimfa_reach_step3": r["nimfa_curve"][EARLY_STEP], "mc_reach_step3": r["mc_curve"][EARLY_STEP],
                              "nimfa_final_reach": r["nimfa_final_reach"], "mc_final_reach": r["mc_final_reach"]})
    out["seed_origins"] = origins
    pd.DataFrame(seed_rows).to_csv(TABLES_DIR / "11_seed_origin_comparison.csv", index=False)

    # Inside each lab: the lab's own members only (largest component), 8 best-connected seeds
    intra, intra_rows = {}, []
    for lab in LABS:
        intra[INST_KEYS[lab]] = {"institute": lab}
        for key in ("full_coauthorship", "faculty_coauthorship", "full_citation"):
            G, vecs = nets[key]["G"], nets[key]["vecs"]
            if key == "full_citation":
                members = [n for n in G if lab in paper_labs.get(n, [])]
            else:
                members = [n for n in G if G.nodes[n].get("lab") == lab]
            H = lab_subgraph(G, members)
            th = thresholds(H)
            row = {"institute": lab, "subgraph_type": key, "nodes": H.number_of_nodes(), "edges": H.number_of_edges(),
                   "mean_degree": th["k_mean"], "beta_c_hmf": th["beta_c_hmf"], "beta_c_qmf": th["beta_c_qmf"]}
            if H.number_of_nodes() >= 3 and H.number_of_edges() >= 2:
                r = simulate(H, vecs, set(H), top_by_degree(H, list(H), 8), seed_names=names)
                row.update(nimfa_t50=r["nimfa_t50"], mc_t50=r["mc_t50"], nimfa_final_reach=r["nimfa_final_reach"],
                           mc_final_reach=r["mc_final_reach"])
                intra[INST_KEYS[lab]][key] = {**row, "thresholds": th, "nimfa_curve": r["nimfa_curve"], "mc_curve": r["mc_curve"]}
            else:
                intra[INST_KEYS[lab]][key] = {**row, "thresholds": th, "too_small": True}
            intra_rows.append(row)
    out["intra_institute"] = intra
    pd.DataFrame(intra_rows).to_csv(TABLES_DIR / "11_intra_institute_comparison.csv", index=False)

    (TABLES_DIR / "11_nimfa_vs_si_comparison.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    pd.DataFrame(grid).to_csv(TABLES_DIR / "11_simulation_grid_metrics.csv", index=False)
    logger.info("Saved 11_nimfa_vs_si_comparison.json and the grid, seed-origin and intra-lab tables")
    return out


if __name__ == "__main__":
    run_all_simulations()
