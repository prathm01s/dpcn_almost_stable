"""Insight 11 (part 4): every claim the Insight 11 page makes, computed from the outputs with a check.

Each claim has the sentence shown on the page (generated from the numbers), the numbers themselves, the
file they come from, how it was checked and whether the check passed. tests/test_insight11.py requires
every check to pass, so a rerun that changes a conclusion fails loudly instead of leaving stale text.

Output: stats/tables/insights/11_claims.json
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.common.logging import get_logger

logger = get_logger("s11_claims")
T = Path("stats/tables/insights")
NOISE_PP = 0.5  # Monte Carlo noise allowed when checking that mean field over-estimates (percentage points)


def _load(name):
    return json.loads((T / name).read_text(encoding="utf-8"))


def build_claims() -> dict:
    nim = _load("11_nimfa_vs_si_comparison.json")
    dif = _load("11_information_diffusion.json")
    thr_all = _load("11_threshold_check.json")
    thr, reps = thr_all["networks"], thr_all["method"]["repeats"]
    cln = _load("11_data_cleaning_stats.json")
    grid = pd.read_csv(T / "11_simulation_grid_metrics.csv")
    claims = []

    def add(cid, text, value, source, check, passed):
        claims.append({"id": cid, "claim": text, "value": value, "source": source, "check": check, "passed": bool(passed)})

    # 1. Faculty-only spreading is slower and reaches fewer people
    full, fac = nim["full_coauthorship"]["fields"]["Combined"], nim["faculty_coauthorship"]["fields"]["Combined"]
    t_full, t_fac = full["mc_t50"], fac["mc_t50"]
    slower = t_full is not None and (t_fac is None or t_fac > t_full)
    add("C1", f"An idea started by a well-connected scientist reaches half of all {nim['full_coauthorship']['nodes']:,} authors "
              f"in {t_full:g} steps (median of {full['mc_runs']} runs); among faculty alone half is reached "
              + (f"in {t_fac:g} steps" if t_fac is not None else "in none of the 15 steps for the typical run")
              + f" ({fac['mc_final_reach']:g}% reached by step 15 vs {full['mc_final_reach']:g}%).",
        {"T50_full": t_full, "T50_faculty": t_fac, "reach15_full": full["mc_final_reach"], "reach15_faculty": fac["mc_final_reach"]},
        "11_nimfa_vs_si_comparison.json (full_coauthorship / faculty_coauthorship, Combined)",
        "Monte Carlo, same rule and seeds-per-run on both networks; T50 is the censored median over runs",
        slower and fac["mc_final_reach"] < full["mc_final_reach"])

    # 2. Students and project staff carry ideas (one-shot transmission)
    sf, sk = thr["full_coauthorship"], thr["faculty_coauthorship"]
    s_full = float(np.interp(0.2, sf["T_grid"], sf["S"]))
    s_fac = float(np.interp(0.2, sk["T_grid"], sk["S"]))
    add("C2", f"If each person passes an idea on only once with probability 0.2, a large outbreak covers {s_full:.0%} of the full "
              f"network but only {s_fac:.0%} of the faculty-only network: 0.2 is above the full network's measured threshold "
              f"({sf['T_peak_simulated']}) and below the faculty network's ({sk['T_peak_simulated']}).",
        {"S_full_T0.2": round(s_full, 3), "S_faculty_T0.2": round(s_fac, 3), "T_peak_full": sf["T_peak_simulated"],
         "T_peak_faculty": sk["T_peak_simulated"]},
        "11_threshold_check.json", f"bond percolation, {reps} repeats per T; S = mean largest-cluster share",
        sf["T_peak_simulated"] < 0.2 <= sk["T_peak_simulated"] and s_full > s_fac)

    # 3. The textbook threshold formula underestimates the real threshold
    ratios = {k: v["peak_over_theory"] for k, v in thr.items()}
    add("C3", f"The textbook threshold <k>/(<k²>−<k>) underestimates the measured one in all {len(ratios)} networks: "
              f"the simulated threshold is {min(ratios.values()):g}–{max(ratios.values()):g} times the formula, because "
              f"co-authorship is clustered (clustering {sf['clustering']} in the full network) and the formula assumes no clustering.",
        {"ratios": ratios, "clustering_full": sf["clustering"], "clustering_faculty": sk["clustering"]},
        "11_threshold_check.json", "peak of the mean small-outbreak size chi(T) vs the configuration-model formula",
        all(r > 1 for r in ratios.values()))

    # 4. Mean field over-estimates spreading
    neg = grid[grid["min_gap"] < -NOISE_PP]
    add("C4", f"The mean-field model (NIMFA) never predicts less spreading than the simulation: across all {len(grid)} "
              f"network × field runs the smallest gap is {grid['min_gap'].min():g} percentage points (simulation noise), "
              f"the largest {grid['max_gap'].max():g}.",
        {"runs": len(grid), "min_gap_pp": float(grid["min_gap"].min()), "max_gap_pp": float(grid["max_gap"].max()),
         "runs_below_noise": int(len(neg))},
        "11_simulation_grid_metrics.csv", f"NIMFA(t) − MC(t) at every step, allowing {NOISE_PP} pp of Monte Carlo noise",
        len(neg) == 0)

    # 5. Monte Carlo is converged
    conv = []
    for f, d in dif["fields_data"].items():
        t = [c["t50"] for c in d["condition_a"]["convergence_check"]]
        r = [c["final_reach"] for c in d["condition_a"]["convergence_check"]]
        # "not reached" at every run count is a stable result (spread 0); a mix of reached / not reached is not
        spread = 0.0 if all(x is None for x in t) else ((max(t) - min(t)) if None not in t else None)
        conv.append({"field": f, "t50_by_trials": t, "final_reach_by_trials": r,
                     "t50_spread": spread, "reach_spread_pp": round(100 * (max(r) - min(r)), 2)})
    ok = all(c["t50_spread"] is not None and c["t50_spread"] <= 1 and c["reach_spread_pp"] <= 2 for c in conv)
    add("C5", f"The simulations are converged: for the top seed in every field, rerunning with 25, 50 and 100 runs changes T50 by at "
              f"most {max(c['t50_spread'] or 0 for c in conv):g} steps (or leaves it 'not reached' every time) and final reach by at most "
              f"{max(c['reach_spread_pp'] for c in conv):g} percentage points.",
        conv, "11_information_diffusion.json (condition_a.convergence_check)", "T50 within 1 step, reach within 2 pp", ok)

    # 6. The two models agree on who spreads best
    rho = {f"{r.network}/{r.field}": r.rank_agreement_spearman for r in grid.itertuples() if pd.notna(r.rank_agreement_spearman)}
    people = {k: v for k, v in rho.items() if "coauthorship" in k}
    add("C6", f"Mean field and simulation rank the seeds the same way: Spearman ρ between their early-reach rankings is "
              f"{min(people.values()):.2f}–{max(people.values()):.2f} on the co-authorship networks (median {np.median(list(rho.values())):.2f} over all runs).",
        rho, "11_simulation_grid_metrics.csv (rank_agreement_spearman)", "ρ ≥ 0.7 on every co-authorship run",
        all(v >= 0.7 for v in people.values()))

    # 7. Topic-weighted spreading stays inside the field
    ch = dif["fields_data"]["Chemistry"]["condition_a"]
    add("C7", f"When transmission depends on topic overlap, ideas stay in their field: {ch['adoption_curve'][-1]:g}% of Chemistry "
              f"researchers adopt by step {len(ch['adoption_curve']) - 1}, but only {ch['spillover_curve'][-1]:g}% of researchers outside Chemistry.",
        {"chemistry_reach": ch["adoption_curve"][-1], "outside_reach": ch["spillover_curve"][-1]},
        "11_information_diffusion.json (fields_data.Chemistry.condition_a)", "in-field reach > 5 × outside reach",
        ch["adoption_curve"][-1] > 5 * ch["spillover_curve"][-1])

    # 8. Paper citations are a poor channel
    pc = nim["full_citation"]
    add("C8", f"Along paper citations ideas travel only forward in time, so they stay local: from the {pc['fields']['Combined']['n_seeds']} "
              f"most-cited papers, {pc['fields']['Combined']['mc_final_reach']:g}% of the {pc['nodes']:,} papers are reached by step 15 "
              f"({'acyclic network' if pc.get('is_acyclic') else str(pc.get('nodes_in_cycles', 0)) + ' papers sit in citation cycles'}).",
        {"reach": pc["fields"]["Combined"]["mc_final_reach"], "is_acyclic": pc.get("is_acyclic"), "nodes_in_cycles": pc.get("nodes_in_cycles")},
        "11_nimfa_vs_si_comparison.json (full_citation)", "reach below 20%", pc["fields"]["Combined"]["mc_final_reach"] < 20)

    # 9. Lab of origin, both models agree on the order
    so = nim["seed_origins"]["faculty_coauthorship"]
    order_mc = sorted(so, key=lambda k: -so[k]["mc_curve"][3])
    order_nim = sorted(so, key=lambda k: -so[k]["nimfa_curve"][3])
    lab = {k: so[k]["institute"] for k in so}
    add("C9", f"On the faculty network, ideas started by {lab[order_mc[0]]} faculty spread fastest early on "
              f"(step-3 reach {', '.join(f'{lab[k]} {so[k]["mc_curve"][3]:g}%' for k in order_mc)}).",
        {k: {"mc_step3": so[k]["mc_curve"][3], "nimfa_step3": so[k]["nimfa_curve"][3], "mc_t50": so[k]["mc_t50"]} for k in so},
        "11_nimfa_vs_si_comparison.json (seed_origins.faculty_coauthorship)", "simulation and mean field give the same order",
        order_mc == order_nim)

    # 10. Roster funnel matches the files
    f = cln["funnel"]
    fm = pd.read_csv("data/final/faculty_master.csv", dtype=str, keep_default_na=False)
    ex = pd.read_csv("data/review/roster_excluded.csv", dtype=str, keep_default_na=False)
    active = int((fm["n_papers_corpus"].astype(int) > 0).sum())
    add("C10", f"Faculty = {f['stage_3_clean_roster']['total']} scientists on the institutes' rosters after removing "
               f"{f['stage_2_excluded_technical_and_duplicates']['total_excluded']} technical staff and duplicates from "
               f"{f['stage_1_raw_scraped']['total']} scraped entries; {f['stage_4_active_cadre_with_papers']['total']} have papers in 2016–2026.",
         {"raw": f["stage_1_raw_scraped"]["total"], "excluded": f["stage_2_excluded_technical_and_duplicates"]["total_excluded"],
          "roster": f["stage_3_clean_roster"]["total"], "active": f["stage_4_active_cadre_with_papers"]["total"]},
         "11_data_cleaning_stats.json; data/final/faculty_master.csv; data/review/roster_excluded.csv",
         "recounted from the two files", f["stage_3_clean_roster"]["total"] == len(fm) and
         f["stage_2_excluded_technical_and_duplicates"]["total_excluded"] == len(ex) and f["stage_4_active_cadre_with_papers"]["total"] == active)

    # 11. Same faculty network as the main dashboard
    ns = pd.read_csv("stats/tables/network_summary.csv")
    row = ns[(ns["network"] == "faculty_coauthorship") & (ns["metric"] == "co-author pairs (unique edges)")]["value"]
    pairs = int(row.iloc[0]) if len(row) else None
    add("C11", f"The faculty co-authorship network here is the main dashboard's: {nim['faculty_coauthorship']['nodes']} scientists, "
               f"{nim['faculty_coauthorship']['edges']} co-author pairs.",
         {"nodes": nim["faculty_coauthorship"]["nodes"], "edges": nim["faculty_coauthorship"]["edges"], "network_summary_pairs": pairs},
         "11_nimfa_vs_si_comparison.json; stats/tables/network_summary.csv", "edge counts equal",
         pairs == nim["faculty_coauthorship"]["edges"])

    out = {"n_claims": len(claims), "n_passed": sum(c["passed"] for c in claims), "claims": claims}
    (T / "11_claims.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Insight 11 claims: {out['n_passed']}/{out['n_claims']} checks pass")
    return out


if __name__ == "__main__":
    build_claims()
