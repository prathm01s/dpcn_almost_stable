"""Insight 11 (part 3): does the network really have the spreading threshold that theory predicts?

Plain SI spreading has no threshold: with any beta > 0 an idea eventually reaches the whole connected
network. A threshold exists once adopters stop passing the idea on (recovery). The simplest such model is
discrete-time SIR in which an adopter tells each contact once, with probability T, and then stops. Its
final outbreak from a seed is exactly the seed's cluster in bond percolation with edge occupation T
(Grassberger 1983; Newman 2002), so it can be measured without simulating time steps:

  for each T: keep every edge with probability T (REPEATS times), find the connected clusters, and record
    S(T)   = largest cluster / N                      (share of the network a large outbreak reaches)
    chi(T) = sum over the other clusters of s^2 / N   (mean size of a small outbreak; peaks at the threshold)
  theory (configuration model, Newman 2002):  T_c = <k> / (<k^2> - <k>)

With REPEATS = 100 the peak is located to within about one grid step (0.005-0.01).
The co-authorship networks are highly clustered, which the configuration-model formula ignores, so the
measured peak T_peak is expected to lie somewhat above T_c; the ratio is reported, not assumed.

Networks: the full co-authorship network (all authors, by OpenAlex ID), the faculty co-authorship network,
and the six field subgraphs of the full network used in part 1 (largest component of the researchers
active in the field).

Output: stats/tables/insights/11_threshold_check.json and 11_threshold_check.csv
"""

import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from src.common.logging import get_logger
from src.stats.insights.common import ordered_subgraph
from src.stats.insights.s11_nimfa_spreading import TARGET_FIELDS, build_networks

logger = get_logger("s11_threshold_check")

TABLES_DIR = Path("stats/tables/insights")
SEED = 24
T_GRID = np.round(np.arange(0.005, 0.5001, 0.005), 3)
REPEATS = 100


def percolation_sweep(G: nx.Graph, rng: np.random.RandomState):
    nodes = list(G.nodes())
    pos = {v: i for i, v in enumerate(nodes)}
    n = len(nodes)
    u = np.array([pos[a] for a, _ in G.edges()])
    v = np.array([pos[b] for _, b in G.edges()])
    S, chi = [], []
    for T in T_GRID:
        s_rep, c_rep = [], []
        for _ in range(REPEATS):
            keep = rng.random_sample(len(u)) < T
            A = csr_matrix((np.ones(keep.sum()), (u[keep], v[keep])), shape=(n, n))
            _, lab = connected_components(A, directed=False)
            sizes = np.bincount(lab).astype(float)
            big = sizes.max()
            s_rep.append(big / n)
            c_rep.append(((sizes ** 2).sum() - big ** 2) / n)
        S.append(float(np.mean(s_rep)))
        chi.append(float(np.mean(c_rep)))
    deg = np.array([d for _, d in G.degree()], dtype=float)
    k1, k2 = deg.mean(), (deg ** 2).mean()
    t_c = k1 / (k2 - k1)
    i_peak = int(np.argmax(chi))
    return {
        "nodes": n, "edges": G.number_of_edges(), "k_mean": round(k1, 2), "k2_mean": round(k2, 2),
        "clustering": round(nx.average_clustering(G), 3),
        "T_c_theory": round(t_c, 4), "T_peak_simulated": float(T_GRID[i_peak]),
        "peak_over_theory": round(float(T_GRID[i_peak]) / t_c, 2),
        "S_at_2Tc": round(float(np.interp(2 * t_c, T_GRID, S)), 4),
        "T_grid": T_GRID.tolist(), "S": [round(x, 4) for x in S], "chi": [round(x, 3) for x in chi],
    }


def study_graphs(nets) -> dict:
    """The networks tested, built in a fixed node order (ordered_subgraph, not G.subgraph(): the latter
    iterates in set order, which changes with PYTHONHASHSEED and would move the random numbers)."""
    full, fac = nets["full_coauthorship"], nets["faculty_coauthorship"]
    graphs = {"full_coauthorship": full["G"], "faculty_coauthorship": fac["G"]}
    for field, short in TARGET_FIELDS:
        if short == "Combined":
            continue
        sub = ordered_subgraph(full["G"], [n for n in full["G"] if full["in_field"](n, field)])
        graphs[f"field_{short}"] = ordered_subgraph(sub, max(nx.connected_components(sub), key=len))
    return graphs


def run_threshold_check() -> dict:
    nets, _, _ = build_networks()
    rng = np.random.RandomState(SEED)
    graphs = study_graphs(nets)
    out = {"method": {"model": "discrete-time SIR, one transmission chance per contact (= bond percolation)",
                      "T_grid": [float(T_GRID[0]), float(T_GRID[-1]), 0.005], "repeats": REPEATS, "rng_seed": SEED},
           "networks": {}}
    rows = []
    for key, G in graphs.items():
        r = percolation_sweep(G, rng)
        out["networks"][key] = r
        rows.append({"network": key, **{k: v for k, v in r.items() if k not in ("T_grid", "S", "chi")}})
        logger.info(f"{key}: N={r['nodes']}, T_c theory {r['T_c_theory']}, simulated peak {r['T_peak_simulated']}")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    (TABLES_DIR / "11_threshold_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    pd.DataFrame(rows).to_csv(TABLES_DIR / "11_threshold_check.csv", index=False)
    return out


if __name__ == "__main__":
    run_threshold_check()
