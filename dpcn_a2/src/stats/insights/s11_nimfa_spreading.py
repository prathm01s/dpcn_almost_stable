"""Individual-Based Discrete-Time Markov Chain (DTMC / NIMFA) vs. Monte Carlo SI Spreading Engine.

Simulates spreading across:
1. Four Global Network Topologies (Full Co-Auth, Cadre Co-Auth, Full Citation, Cadre Citation)
2. Seed Origin Contrast (Diffusion originating at CSIR-NCL vs. CSIR-IICT vs. CSIR-CECRI)
3. Intra-Institute Spreading (Internal diffusion strictly within NCL, IICT, and CECRI)

Evaluates:
- Stochastic Monte Carlo SI (M=35 trials, active boundary tracking)
- Deterministic Discrete-Time Markov Chain (NIMFA):
  x_i(t+1) = x_i(t) + (1 - x_i(t)) * [1 - Prod_{j in N_in(i)} (1 - beta_ji * x_j(t))]
- Theoretical Mean-Field Gap (Jensen's inequality gap)
- Dynamical Influence Centrality: d Sum_k x_k(t) / d x_i(0)

Exports:
- stats/tables/insights/11_nimfa_vs_si_comparison.json
- stats/tables/insights/11_simulation_grid_metrics.csv
- stats/tables/insights/11_seed_origin_comparison.csv
- stats/tables/insights/11_intra_institute_comparison.csv
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse.linalg import eigs

from src.common.logging import get_logger
from src.stats.networks import corpus_dois, incorpus_citation_edges, labelled_faculty_graphs

logger = get_logger("s11_nimfa_spreading")

DATA_FINAL = Path("data/final")
TABLES_DIR = Path("stats/tables/insights")
SEED = 42
MAX_STEPS = 15
BETA_BASE = 0.20
MC_TRIALS = 35

LABS = ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
INST_KEYS = {"CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri"}

TARGET_FIELDS = [
    ("Chemistry", "Chemistry"),
    ("Materials Science", "Materials"),
    ("Engineering", "Engineering"),
    ("Energy", "Energy"),
    ("Biochemistry, Genetics and Molecular Biology", "Biochemistry"),
    ("Medicine", "Medicine"),
    ("All-Domain", "Combined")
]


def compute_spectral_threshold(G: nx.Graph) -> Tuple[float, float, float, float]:
    """Compute degree moments and spectral threshold."""
    if G.is_directed():
        degrees = [d for _, d in G.in_degree()]
    else:
        degrees = [d for _, d in G.degree()]

    if not degrees:
        return 0.0, 0.0, 0.0, 0.0

    k_mean = float(np.mean(degrees))
    k2_mean = float(np.mean([d ** 2 for d in degrees]))
    beta_c = (k_mean / k2_mean) if k2_mean > 0 else 0.0

    if G.number_of_edges() > 0:
        try:
            A = nx.adjacency_matrix(G).astype(float)
            vals = eigs(A, k=1, which="LR", return_eigenvectors=False)
            lambda_max = float(np.real(vals[0]))
            beta_c_spec = (1.0 / lambda_max) if lambda_max > 0 else beta_c
        except Exception:
            beta_c_spec = beta_c
    else:
        beta_c_spec = beta_c

    return round(k_mean, 2), round(k2_mean, 2), round(beta_c, 4), round(beta_c_spec, 4)


def build_author_profiles():
    """Build normalized subfield vectors and field shares for each author."""
    df_ext = pd.read_csv(
        DATA_FINAL / "group24_data_extended.csv",
        usecols=["author", "field", "subfield", "institution"],
        keep_default_na=False,
    )
    subfields = sorted(set(df_ext["subfield"].dropna().astype(str)) - {""})
    subfield_idx = {s: i for i, s in enumerate(subfields)}
    num_subfields = len(subfields)

    author_sub_counts = defaultdict(lambda: np.zeros(num_subfields, dtype=float))
    author_field_counts = defaultdict(lambda: defaultdict(int))
    author_total = defaultdict(int)
    author_labs = {}

    for a, f, s, inst in zip(df_ext["author"], df_ext["field"], df_ext["subfield"], df_ext["institution"]):
        if not a:
            continue
        author_total[a] += 1
        if inst in LABS and a not in author_labs:
            author_labs[a] = inst
        if f:
            author_field_counts[a][f] += 1
        if s and s in subfield_idx:
            author_sub_counts[a][subfield_idx[s]] += 1.0

    author_vecs = {}
    for a, counts in author_sub_counts.items():
        norm = np.linalg.norm(counts)
        author_vecs[a] = (counts / norm) if norm > 0 else counts

    author_field_shares = {}
    for a, f_counts in author_field_counts.items():
        tot = author_total[a]
        author_field_shares[a] = {f: cnt / tot for f, cnt in f_counts.items()}

    return author_vecs, author_field_shares, author_labs


def run_stochastic_mc_si(
    adj_with_probs: Dict[str, List[Tuple[str, float]]],
    seed_nodes: List[str],
    target_nodes: Set[str],
    num_trials: int = MC_TRIALS,
    max_steps: int = MAX_STEPS,
    rng_seed: int = SEED,
) -> Tuple[np.ndarray, float]:
    """Run discrete-time Monte Carlo SI simulation with active boundary tracking."""
    rng = np.random.RandomState(rng_seed)
    n_target = max(1, len(target_nodes))
    trajs = np.zeros((num_trials, max_steps + 1))
    t50_trials = []

    for trial in range(num_trials):
        seed = seed_nodes[trial % len(seed_nodes)]
        infected = {seed}
        active_infected = {seed}
        trajs[trial, 0] = (1.0 if seed in target_nodes else 0.0) / n_target
        found_t50 = False
        t50 = float(max_steps)

        for step in range(1, max_steps + 1):
            new_infections = set()
            still_active = set()

            for u in active_infected:
                has_susceptible = False
                for v, p in adj_with_probs.get(u, []):
                    if v not in infected and v not in new_infections:
                        has_susceptible = True
                        if rng.rand() < p:
                            new_infections.add(v)
                if has_susceptible:
                    still_active.add(u)

            infected.update(new_infections)
            active_infected = still_active | new_infections
            frac = len(infected & target_nodes) / n_target
            trajs[trial, step] = frac

            if not found_t50 and frac >= 0.50:
                t50 = float(step)
                found_t50 = True

            if not active_infected:
                trajs[trial, step:] = frac
                break

        t50_trials.append(t50)

    mean_curve = trajs.mean(axis=0) * 100.0
    mean_t50 = float(np.mean(t50_trials))
    return np.round(mean_curve, 2), round(mean_t50, 2)


def run_deterministic_nimfa(
    nodes_list: List[str],
    in_neighbors: Dict[str, List[Tuple[str, float]]],
    seed_nodes: List[str],
    target_nodes: Set[str],
    max_steps: int = MAX_STEPS,
) -> Tuple[np.ndarray, float, Dict[str, float]]:
    """Run exact Discrete-Time Markov Chain (NIMFA)."""
    N = len(nodes_list)
    node_to_idx = {n: i for i, n in enumerate(nodes_list)}
    target_indices = np.array([node_to_idx[n] for n in target_nodes if n in node_to_idx], dtype=int)
    n_target = max(1, len(target_indices))

    in_adj_idx = []
    for i, n in enumerate(nodes_list):
        in_adj_idx.append([(node_to_idx[j], beta) for j, beta in in_neighbors.get(n, []) if j in node_to_idx])

    all_trajs = []
    t50_seeds = []
    seed_marginal_impacts = {}

    for seed in seed_nodes:
        if seed not in node_to_idx:
            continue
        seed_idx = node_to_idx[seed]

        x = np.zeros(N, dtype=float)
        x[seed_idx] = 1.0

        curve = np.zeros(max_steps + 1, dtype=float)
        curve[0] = (1.0 if seed in target_nodes else 0.0) / n_target
        found_t50 = False
        t50 = float(max_steps)

        for step in range(1, max_steps + 1):
            x_next = np.copy(x)
            for i in range(N):
                if x[i] >= 0.9999:
                    continue
                prob_no_infect = 1.0
                for j_idx, beta in in_adj_idx[i]:
                    prob_no_infect *= (1.0 - beta * x[j_idx])

                p_new = (1.0 - x[i]) * (1.0 - prob_no_infect)
                x_next[i] = min(1.0, x[i] + p_new)

            x = x_next
            frac = float(np.sum(x[target_indices])) / n_target
            curve[step] = frac

            if not found_t50 and frac >= 0.50:
                t50 = float(step)
                found_t50 = True

        all_trajs.append(curve)
        t50_seeds.append(t50)
        seed_marginal_impacts[seed] = float(np.sum(x))

    mean_curve = np.mean(all_trajs, axis=0) * 100.0 if all_trajs else np.zeros(max_steps + 1)
    mean_t50 = float(np.mean(t50_seeds)) if t50_seeds else float(max_steps)
    return np.round(mean_curve, 2), round(mean_t50, 2), seed_marginal_impacts


def run_all_simulations():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    author_vecs, author_field_shares, author_labs = build_author_profiles()

    # Cadre (roster-faculty) graphs come from src/stats/networks.py, keyed by faculty_id and
    # relabelled to unique display labels, so they match the dashboard and network_summary.csv (D-33)
    fm = pd.read_csv(DATA_FINAL / "faculty_master.csv", dtype=str, keep_default_na=False)
    ext_all = pd.read_csv(DATA_FINAL / "group24_data_extended.csv", dtype=str, keep_default_na=False)
    cite_all = pd.read_csv(DATA_FINAL / "citation_network.csv", dtype=str, keep_default_na=False)
    FA, FC, _, labels = labelled_faculty_graphs(ext_all, fm, incorpus_citation_edges(cite_all, corpus_dois(ext_all)))
    fac_names = set(labels.values())
    fac_lab_map = dict(FA.nodes(data="lab"))
    # a label with the lab added (two scientists sharing a name) uses the profile of that name
    name_of = dict(zip(fm["faculty_id"], fm["full_name"]))
    for fid, lbl in labels.items():
        nm = name_of[fid]
        if lbl != nm:
            if nm in author_vecs:
                author_vecs[lbl] = author_vecs[nm]
            if nm in author_field_shares:
                author_field_shares[lbl] = author_field_shares[nm]
        author_labs[lbl] = fac_lab_map[lbl]

    auth_df = pd.read_csv(DATA_FINAL / "authorship_network.csv", keep_default_na=False)
    cite_df = pd.read_csv(DATA_FINAL / "citation_network.csv", keep_default_na=False)
    ext_df = pd.read_csv(DATA_FINAL / "group24_data_extended.csv", usecols=["doi", "author", "author_role", "institution"], keep_default_na=False)

    # Filter in-corpus co-authorship
    in_corpus_auth = auth_df[auth_df["inst_a"].isin(LABS) & auth_df["inst_b"].isin(LABS)]

    # 1. Full Co-Authorship LCC
    G1_full = nx.Graph()
    for a, b in zip(in_corpus_auth["author_a"], in_corpus_auth["author_b"]):
        if a and b and a != b:
            G1_full.add_edge(a, b)
    lcc_nodes_1 = max(nx.connected_components(G1_full), key=len)
    G1 = G1_full.subgraph(lcc_nodes_1).copy()

    # 2. Cadre Co-Authorship (scientists with >= 1 faculty co-author)
    G2 = nx.Graph()
    G2.add_edges_from(FA.edges())

    # 3. Full Citation
    corpus_doi_set = set(ext_df["doi"]) - {""}
    in_corpus_cite = cite_df[cite_df["source_doi"].isin(corpus_doi_set) & cite_df["target_doi"].isin(corpus_doi_set)]
    G3 = nx.DiGraph()
    for s, t in zip(in_corpus_cite["source_doi"], in_corpus_cite["target_doi"]):
        G3.add_edge(t, s)

    # 4. Cadre Citation: information flows from the cited scientist to the citing one
    G4 = nx.DiGraph()
    G4.add_edges_from((t, s) for s, t in FC.edges())

    networks_dict = {
        "full_authorship": {"G": G1, "name": f"Full Co-Authorship (N={G1.number_of_nodes():,})", "type": "author"},
        "cadre_authorship": {"G": G2, "name": f"Cadre Co-Authorship (N={G2.number_of_nodes():,})", "type": "cadre_author"},
        "full_citation": {"G": G3, "name": f"Full In-Corpus Citation (N={G3.number_of_nodes():,})", "type": "paper"},
        "cadre_citation": {"G": G4, "name": f"Cadre Faculty Citation (N={G4.number_of_nodes():,})", "type": "cadre_author"},
    }

    full_comparison = {}
    grid_rows = []

    for net_key, net_info in networks_dict.items():
        G = net_info["G"]
        net_name = net_info["name"]
        net_type = net_info["type"]
        N = G.number_of_nodes()
        E = G.number_of_edges()
        k_m, k2_m, b_c, b_c_spec = compute_spectral_threshold(G)

        logger.info(f"=== Simulating Global on {net_name} (Nodes={N:,}, Edges={E:,}) ===")
        net_results = {
            "network_key": net_key,
            "network_name": net_name,
            "nodes": N,
            "edges": E,
            "thresholds": {"k_mean": k_m, "k2_mean": k2_m, "beta_c": b_c, "beta_c_spec": b_c_spec},
            "fields": {}
        }

        adj_forward = defaultdict(list)
        adj_backward = defaultdict(list)

        for u, v in G.edges():
            if net_type in ("author", "cadre_author"):
                vu = author_vecs.get(u)
                vv = author_vecs.get(v)
                cossim = float(np.dot(vu, vv)) if (vu is not None and vv is not None) else 0.5
            else:
                cossim = 0.5

            p_trans = min(1.0, BETA_BASE * max(0.1, cossim))
            adj_forward[u].append((v, p_trans))
            adj_backward[v].append((u, p_trans))
            if not G.is_directed():
                adj_forward[v].append((u, p_trans))
                adj_backward[u].append((v, p_trans))

        nodes_list = list(G.nodes())

        for field_name, short_label in TARGET_FIELDS:
            if field_name == "All-Domain":
                target_nodes = set(G.nodes())
            else:
                if net_type in ("author", "cadre_author"):
                    target_nodes = set(n for n in G.nodes() if author_field_shares.get(n, {}).get(field_name, 0.0) > 0.0)
                else:
                    target_nodes = set(G.nodes())

            if len(target_nodes) == 0:
                target_nodes = set(G.nodes())

            if net_type in ("author", "cadre_author"):
                candidate_seeds = [n for n in target_nodes if n in fac_names]
                if not candidate_seeds:
                    candidate_seeds = list(target_nodes)
                candidate_seeds = sorted(candidate_seeds, key=lambda n: G.degree(n) if not G.is_directed() else G.out_degree(n), reverse=True)[:15]
            else:
                candidate_seeds = sorted(list(target_nodes), key=lambda n: G.out_degree(n), reverse=True)[:15]

            curve_mc, t50_mc = run_stochastic_mc_si(adj_forward, candidate_seeds, target_nodes, num_trials=MC_TRIALS)
            curve_nimfa, t50_nimfa, seed_impacts = run_deterministic_nimfa(nodes_list, adj_backward, candidate_seeds, target_nodes)

            mean_gap = float(np.mean(curve_nimfa - curve_mc))
            max_gap = float(np.max(curve_nimfa - curve_mc))

            top_spreaders = []
            for seed, imp in sorted(seed_impacts.items(), key=lambda x: -x[1])[:5]:
                top_spreaders.append({
                    "name": seed,
                    "lab": fac_lab_map.get(seed, "CSIR Cluster"),
                    "dynamical_impact": round(imp, 1),
                    "out_degree": G.degree(seed) if not G.is_directed() else G.out_degree(seed)
                })

            net_results["fields"][short_label] = {
                "field_name": field_name,
                "target_population": len(target_nodes),
                "mc_curve": curve_mc.tolist(),
                "nimfa_curve": curve_nimfa.tolist(),
                "mc_t50": t50_mc,
                "nimfa_t50": t50_nimfa,
                "t50_speedup": round(t50_mc - t50_nimfa, 2),
                "mean_jensen_gap": round(mean_gap, 2),
                "max_jensen_gap": round(max_gap, 2),
                "top_super_spreaders": top_spreaders
            }

            grid_rows.append({
                "network": net_name,
                "field": short_label,
                "target_nodes": len(target_nodes),
                "mc_t50": t50_mc,
                "nimfa_t50": t50_nimfa,
                "t50_speedup": round(t50_mc - t50_nimfa, 2),
                "mc_final_reach": curve_mc[-1],
                "nimfa_final_reach": curve_nimfa[-1],
                "mean_gap": round(mean_gap, 2),
                "beta_c": b_c,
                "beta_c_spectral": b_c_spec
            })

        full_comparison[net_key] = net_results

    # ------------------------------------------------------------------
    # 5. Four-Network Overlay Data (On the SAME plot for Chemistry & Combined)
    # ------------------------------------------------------------------
    logger.info("Computing 4-Network Overlay Comparison curves...")
    overlay_data = {
        "Chemistry": {
            "full_authorship_mc": full_comparison["full_authorship"]["fields"]["Chemistry"]["mc_curve"],
            "full_authorship_nimfa": full_comparison["full_authorship"]["fields"]["Chemistry"]["nimfa_curve"],
            "cadre_authorship_mc": full_comparison["cadre_authorship"]["fields"]["Chemistry"]["mc_curve"],
            "cadre_authorship_nimfa": full_comparison["cadre_authorship"]["fields"]["Chemistry"]["nimfa_curve"],
            "full_citation_mc": full_comparison["full_citation"]["fields"]["Chemistry"]["mc_curve"],
            "full_citation_nimfa": full_comparison["full_citation"]["fields"]["Chemistry"]["nimfa_curve"],
            "cadre_citation_mc": full_comparison["cadre_citation"]["fields"]["Chemistry"]["mc_curve"],
            "cadre_citation_nimfa": full_comparison["cadre_citation"]["fields"]["Chemistry"]["nimfa_curve"],
        },
        "Combined": {
            "full_authorship_mc": full_comparison["full_authorship"]["fields"]["Combined"]["mc_curve"],
            "full_authorship_nimfa": full_comparison["full_authorship"]["fields"]["Combined"]["nimfa_curve"],
            "cadre_authorship_mc": full_comparison["cadre_authorship"]["fields"]["Combined"]["mc_curve"],
            "cadre_authorship_nimfa": full_comparison["cadre_authorship"]["fields"]["Combined"]["nimfa_curve"],
            "full_citation_mc": full_comparison["full_citation"]["fields"]["Combined"]["mc_curve"],
            "full_citation_nimfa": full_comparison["full_citation"]["fields"]["Combined"]["nimfa_curve"],
            "cadre_citation_mc": full_comparison["cadre_citation"]["fields"]["Combined"]["mc_curve"],
            "cadre_citation_nimfa": full_comparison["cadre_citation"]["fields"]["Combined"]["nimfa_curve"],
        }
    }
    full_comparison["overlay_comparison"] = overlay_data

    # ------------------------------------------------------------------
    # 6. Seed Origin Differences (Seeds strictly in NCL vs IICT vs CECRI)
    # ------------------------------------------------------------------
    logger.info("Simulating Seed Origin Contrast (NCL vs IICT vs CECRI Originating Seeds)...")
    seed_origin_results = {}
    seed_csv_rows = []

    # Test on Full Co-Authorship and Cadre Co-Authorship
    for origin_net_key in ["full_authorship", "cadre_authorship"]:
        net_G = networks_dict[origin_net_key]["G"]
        nodes_list = list(net_G.nodes())
        seed_origin_results[origin_net_key] = {}

        adj_back = defaultdict(list)
        for u, v in net_G.edges():
            vu = author_vecs.get(u)
            vv = author_vecs.get(v)
            cossim = float(np.dot(vu, vv)) if (vu is not None and vv is not None) else 0.5
            p_trans = min(1.0, BETA_BASE * max(0.1, cossim))
            adj_back[v].append((u, p_trans))
            adj_back[u].append((v, p_trans))

        for lab in LABS:
            lab_key = INST_KEYS[lab]
            # Find seeds belonging to this institute
            lab_seeds = [
                n for n in net_G.nodes()
                if (fac_lab_map.get(n) == lab or author_labs.get(n) == lab)
            ]
            lab_seeds = sorted(lab_seeds, key=lambda n: net_G.degree(n), reverse=True)[:10]

            if not lab_seeds:
                continue

            curve_nimfa, t50_nimfa, impacts = run_deterministic_nimfa(
                nodes_list, adj_back, lab_seeds, set(net_G.nodes())
            )

            seed_origin_results[origin_net_key][lab_key] = {
                "institute": lab,
                "seeds_evaluated": len(lab_seeds),
                "top_seeds": lab_seeds[:3],
                "curve": curve_nimfa.tolist(),
                "t50": t50_nimfa,
                "early_reach_t3": float(curve_nimfa[3]),
                "final_reach": float(curve_nimfa[-1]),
            }

            seed_csv_rows.append({
                "network": origin_net_key,
                "seed_origin_institute": lab,
                "seeds_evaluated": len(lab_seeds),
                "t50": t50_nimfa,
                "reach_step_3": float(curve_nimfa[3]),
                "final_reach": float(curve_nimfa[-1])
            })

    full_comparison["seed_origins"] = seed_origin_results
    pd.DataFrame(seed_csv_rows).to_csv(TABLES_DIR / "11_seed_origin_comparison.csv", index=False)

    # ------------------------------------------------------------------
    # 7. Intra-Institute Spreading Simulation (Strictly within each institute)
    # ------------------------------------------------------------------
    logger.info("Simulating Intra-Institute Spreading (Internal NCL vs IICT vs CECRI)...")
    intra_results = {}
    intra_csv_rows = []

    for lab in LABS:
        lab_key = INST_KEYS[lab]
        intra_results[lab_key] = {"institute": lab}

        # 1. Intra-Lab Full Co-Authorship
        intra_auth = in_corpus_auth[(in_corpus_auth["inst_a"] == lab) & (in_corpus_auth["inst_b"] == lab)]
        G_intra_full = nx.Graph()
        for a, b in zip(intra_auth["author_a"], intra_auth["author_b"]):
            if a and b and a != b:
                G_intra_full.add_edge(a, b)
        if len(G_intra_full) > 0:
            lcc_intra = max(nx.connected_components(G_intra_full), key=len)
            G_intra_full_lcc = G_intra_full.subgraph(lcc_intra).copy()
        else:
            G_intra_full_lcc = nx.Graph()

        # 2. Intra-Lab Cadre Co-Authorship
        # (was zip(intra_cadre["author_a"], cadre_auth["author_b"]): mixed a filtered and an unfiltered
        #  column, pairing the wrong scientists; D-33)
        G_intra_cadre = nx.Graph()
        G_intra_cadre.add_edges_from((a, b) for a, b in G2.edges() if fac_lab_map[a] == lab and fac_lab_map[b] == lab)

        # 3. Intra-Lab Citation
        intra_cite = in_corpus_cite[(in_corpus_cite["source_inst"] == lab) & (in_corpus_cite["target_inst"] == lab)]
        G_intra_cite = nx.DiGraph()
        for s, t in zip(intra_cite["source_doi"], intra_cite["target_doi"]):
            G_intra_cite.add_edge(t, s)

        sub_graphs = {
            "full_authorship": (G_intra_full_lcc, "author"),
            "cadre_authorship": (G_intra_cadre, "cadre_author"),
            "full_citation": (G_intra_cite, "paper")
        }

        for sub_key, (subG, s_type) in sub_graphs.items():
            N_s = subG.number_of_nodes()
            E_s = subG.number_of_edges()
            k_m_s, k2_m_s, b_c_s, b_spec_s = compute_spectral_threshold(subG)

            if N_s < 3 or E_s < 2:
                intra_results[lab_key][sub_key] = {
                    "nodes": N_s, "edges": E_s, "curve": [0.0]*16, "t50": 15.0, "reach": 0.0, "beta_c": b_c_s
                }
                continue

            sub_nodes = list(subG.nodes())
            adj_b = defaultdict(list)
            for u, v in subG.edges():
                cossim = 0.5
                if s_type in ("author", "cadre_author"):
                    vu = author_vecs.get(u)
                    vv = author_vecs.get(v)
                    cossim = float(np.dot(vu, vv)) if (vu is not None and vv is not None) else 0.5
                p = min(1.0, BETA_BASE * max(0.1, cossim))
                adj_b[v].append((u, p))
                if not subG.is_directed():
                    adj_b[u].append((v, p))

            seeds_s = sorted(sub_nodes, key=lambda n: subG.degree(n) if not subG.is_directed() else subG.out_degree(n), reverse=True)[:8]
            c_nimfa, t50_s, _ = run_deterministic_nimfa(sub_nodes, adj_b, seeds_s, set(sub_nodes))

            intra_results[lab_key][sub_key] = {
                "nodes": N_s,
                "edges": E_s,
                "k_mean": k_m_s,
                "beta_c": b_c_s,
                "beta_c_spectral": b_spec_s,
                "curve": c_nimfa.tolist(),
                "t50": t50_s,
                "final_reach": float(c_nimfa[-1])
            }

            intra_csv_rows.append({
                "institute": lab,
                "subgraph_type": sub_key,
                "nodes": N_s,
                "edges": E_s,
                "mean_degree": k_m_s,
                "beta_c": b_c_s,
                "beta_c_spectral": b_spec_s,
                "nimfa_t50": t50_s,
                "final_reach": float(c_nimfa[-1])
            })

    full_comparison["intra_institute"] = intra_results
    pd.DataFrame(intra_csv_rows).to_csv(TABLES_DIR / "11_intra_institute_comparison.csv", index=False)

    # ------------------------------------------------------------------
    # 8. Export Master Results
    # ------------------------------------------------------------------
    (TABLES_DIR / "11_nimfa_vs_si_comparison.json").write_text(json.dumps(full_comparison, indent=2), encoding="utf-8")
    pd.DataFrame(grid_rows).to_csv(TABLES_DIR / "11_simulation_grid_metrics.csv", index=False)
    logger.info("✓ Successfully generated and saved full NIMFA spreading comparison suite.")
    return full_comparison


if __name__ == "__main__":
    run_all_simulations()
