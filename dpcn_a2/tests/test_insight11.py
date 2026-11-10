"""Insight 11 (D-38): the claims hold, and the simulation code is right on graphs with known answers."""

import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from src.stats.insights.s11_nimfa_spreading import (censored_median, first_reach, mc_si, nimfa, simulate, thresholds)

T = Path("stats/tables/insights")


def _load(name):
    return json.loads((T / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the published results
def test_every_claim_passes():
    c = _load("11_claims.json")
    failed = [x["id"] for x in c["claims"] if not x["passed"]]
    assert c["n_claims"] >= 10 and not failed, f"failed claims: {failed}"


def test_page_payload_matches_outputs():
    text = Path("dashboard/data/g24_insights11_suite.js").read_text(encoding="utf-8")
    d = json.loads(text[len("window.G24_I11 = "):].rstrip().rstrip(";"))
    assert d["claims"] == _load("11_claims.json")
    assert len(d["grid"]) == len(pd.read_csv(T / "11_simulation_grid_metrics.csv"))
    assert d["spreading"]["full_coauthorship"]["nodes"] == _load("11_nimfa_vs_si_comparison.json")["full_coauthorship"]["nodes"]


def test_both_parts_use_the_same_full_network():
    """Part 1 (field study) and part 2 (network comparison) simulate on the same ID-keyed network."""
    assert _load("11_information_diffusion.json")["metrics"]["global_lcc_nodes"] == \
        _load("11_nimfa_vs_si_comparison.json")["full_coauthorship"]["nodes"]


def test_mc_and_nimfa_use_equal_runs_per_seed():
    p = _load("11_nimfa_vs_si_comparison.json")
    runs = p["parameters"]["mc_runs_per_seed"]
    for key in ("full_coauthorship", "faculty_coauthorship", "full_citation", "faculty_citation"):
        for f in p[key]["fields"].values():
            assert f["mc_runs"] == f["n_seeds"] * runs


def test_citation_fields_are_not_copies():
    f = _load("11_nimfa_vs_si_comparison.json")["full_citation"]["fields"]
    assert f["Chemistry"]["target_population"] < f["Combined"]["target_population"]
    assert f["Chemistry"]["mc_curve"] != f["Combined"]["mc_curve"]


def test_threshold_sweep_shapes():
    for key, r in _load("11_threshold_check.json")["networks"].items():
        S = np.array(r["S"])
        assert len(S) == len(r["T_grid"]) == len(r["chi"])
        assert np.all(np.diff(S) > -0.03), key  # outbreak share grows with T (up to sampling noise)
        assert r["T_grid"][0] <= r["T_peak_simulated"] <= r["T_grid"][-1]


# ---------------------------------------------------------------- the code, on graphs with known answers
def test_nimfa_is_exact_on_a_star_from_the_centre():
    """Each leaf's only neighbour is the seed (adopted with certainty), so nothing is correlated:
    NIMFA gives the exact leaf probability 1 - (1 - b)^t."""
    b, n = 0.3, 6
    src, dst = np.zeros(n - 1, dtype=int), np.arange(1, n)
    frac, total = nimfa(n, src, dst, np.full(n - 1, b), 0, np.ones(n, dtype=bool), steps=5)
    for t in range(6):
        assert abs(total[t] - (1 + (n - 1) * (1 - (1 - b) ** t))) < 1e-12


def test_chain_exact_answer_simulation_matches_and_mean_field_bounds_it():
    """On a chain node k adopts by step t with probability P(Binomial(t, b) >= k) (exact SI).
    Monte Carlo must match it; NIMFA ignores that k adopted implies k-1 adopted, so it must not fall below it."""
    from scipy.stats import binom
    b, n, steps = 0.4, 5, 6
    src, dst = np.arange(n - 1), np.arange(1, n)
    beta = np.full(n - 1, b)
    exact = np.array([1 + sum(binom.sf(k - 1, t, b) for k in range(1, n)) for t in range(steps + 1)])
    _, nim = nimfa(n, src, dst, beta, 0, np.ones(n, dtype=bool), steps=steps)
    assert np.all(nim >= exact - 1e-12) and nim[-1] > exact[-1]
    out_adj = [[(k + 1, b)] for k in range(n - 1)] + [[]]
    _, totals = mc_si(n, out_adj, 0, np.ones(n, dtype=bool), 5000, np.random.RandomState(1), steps=steps)
    assert np.max(np.abs(totals.mean(axis=0) - exact)) < 0.06


def test_mean_field_overestimates_on_a_clustered_graph():
    G = nx.relabel_nodes(nx.complete_graph(6), str)
    vecs = {n: np.array([1.0]) for n in G}
    r = simulate(G, vecs, set(G), ["0"], runs_per_seed=3000)
    assert r["min_gap"] > -1.0 and r["max_gap"] > 1.0


def test_thresholds():
    ring = nx.cycle_graph(10)
    t = thresholds(ring)
    assert t["beta_c_hmf"] == 0.5 and abs(t["beta_c_qmf"] - 0.5) < 1e-6
    dag = nx.DiGraph([(0, 1), (1, 2), (0, 2)])
    t = thresholds(dag)
    assert t["beta_c_qmf"] is None and t["beta_c_hmf"] is None


def test_censored_median_and_first_reach():
    assert censored_median([3, 5, None]) == 5
    assert censored_median([3, None, None]) is None
    assert first_reach(np.array([0, 0.2, 0.6, 0.9])) == 2
    assert first_reach(np.array([0, 0.2])) is None


def test_simulation_is_deterministic():
    G = nx.relabel_nodes(nx.barabasi_albert_graph(200, 3, seed=2), str)
    vecs = {n: np.array([1.0]) for n in G}
    a = simulate(G, vecs, set(G), ["0", "1", "2"], runs_per_seed=5)
    b = simulate(G, vecs, set(G), ["0", "1", "2"], runs_per_seed=5)
    assert a["mc_curve"] == b["mc_curve"] and a["nimfa_curve"] == b["nimfa_curve"]


def test_network_simulation_is_independent_of_hash_seed():
    import os
    import subprocess
    import sys
    code = ("import networkx as nx, numpy as np;"
            "from src.stats.insights.s11_nimfa_spreading import simulate;"
            "G=nx.relabel_nodes(nx.barabasi_albert_graph(150,3,seed=4),lambda i:f'n{i}');"
            "v={n:np.array([1.0]) for n in G};"
            "r=simulate(G,v,set(G),['n0','n5'],runs_per_seed=4);print(r['mc_curve'],r['nimfa_curve'])")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                           env={**os.environ, "PYTHONHASHSEED": h}).stdout for h in ("1", "987")}
    assert len(outs) == 1


def test_study_networks_have_a_fixed_node_order():
    """Every network the study simulates is built in the same node order whatever PYTHONHASHSEED is
    (G.subgraph() would not be), so random numbers land on the same nodes and reruns are identical."""
    import os
    import subprocess
    import sys
    code = ("import hashlib;"
            "from src.stats.insights.s11_nimfa_spreading import build_networks, lab_subgraph, LABS;"
            "from src.stats.insights.s11_threshold_check import study_graphs;"
            "nets,_,_=build_networks();"
            "gs=[n['G'] for n in nets.values()]+list(study_graphs(nets).values());"
            "G=nets['full_coauthorship']['G'];"
            "gs+=[lab_subgraph(G,[n for n in G if G.nodes[n].get('lab')==l]) for l in LABS];"
            "print(hashlib.md5(repr([list(g.nodes()) for g in gs]+[list(g.edges()) for g in gs]).encode()).hexdigest())")
    outs = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                           env={**os.environ, "PYTHONHASHSEED": h}).stdout.strip().splitlines()[-1] for h in ("1", "987")}
    assert len(outs) == 1
