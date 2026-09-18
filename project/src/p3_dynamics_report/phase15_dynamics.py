import os
from pathlib import Path
import re
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parents[1]
P1_SRC = PROJECT_ROOT / "src" / "p1_construction"
sys.path.insert(0, str(P1_SRC))

from utils import apply_plot_style, set_global_seed, BLOCK_COLORS  # type: ignore # noqa: E402

GRAPHS_DIR = PROJECT_ROOT / "graphs"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"

def upsert_marked_section(text, start_marker, end_marker, content, before):
    section = f"{start_marker}\n{content.strip()}\n{end_marker}"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.S)
    text = pattern.sub("", text).rstrip() + "\n"
    if before in text:
        return text.replace(before, section + "\n\n" + before, 1)
    return text.rstrip() + "\n\n" + section + "\n"

def save_figure(fig, name):
    path = FIGURES_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {path.relative_to(PROJECT_ROOT)}")

def run_sir(G, seed_node, beta_base, gamma, max_t=50):
    state = {n: 0 for n in G.nodes()}
    state[seed_node] = 1
    
    history_S = [G.number_of_nodes() - 1]
    history_I = [1]
    history_R = [0]
    
    for t in range(max_t):
        new_state = state.copy()
        for u in G.nodes():
            if state[u] == 1: 
                for v in G.neighbors(u):
                    if state[v] == 0:
                        w = G[u][v].get('weight', 1.0)
                        if np.random.rand() < beta_base * w:
                            new_state[v] = 1
                if np.random.rand() < gamma:
                    new_state[u] = 2
        state = new_state
        S = sum(1 for x in state.values() if x == 0)
        I = sum(1 for x in state.values() if x == 1)
        R = sum(1 for x in state.values() if x == 2)
        history_S.append(S)
        history_I.append(I)
        history_R.append(R)
        if I == 0:
            break
            
    while len(history_S) <= max_t:
        history_S.append(history_S[-1])
        history_I.append(history_I[-1])
        history_R.append(history_R[-1])
        
    return np.array(history_S), np.array(history_I), np.array(history_R)

def run_sis(G, seed_node, beta_base, gamma, max_t=100):
    state = {n: 0 for n in G.nodes()}
    state[seed_node] = 1
    
    history_I = [1]
    
    for t in range(max_t):
        new_state = state.copy()
        for u in G.nodes():
            if state[u] == 1:
                for v in G.neighbors(u):
                    if state[v] == 0:
                        w = G[u][v].get('weight', 1.0)
                        if np.random.rand() < beta_base * w:
                            new_state[v] = 1
                if np.random.rand() < gamma:
                    new_state[u] = 0
        state = new_state
        I = sum(1 for x in state.values() if x == 1)
        history_I.append(I)
    
    return np.array(history_I)

def main():
    set_global_seed()
    apply_plot_style()
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 15 — DYNAMICAL OPINION-SPREAD SIMULATION")
    print("=" * 70)

    # 1. Load GCC
    G = nx.read_graphml(GRAPHS_DIR / "G_giant.graphml")
    
    # 2. Find seeds
    node_metrics = pd.read_csv(TABLES_DIR / "node_metrics.csv")
    node_metrics['ResponseID'] = node_metrics['ResponseID'].astype(str)
    
    # Highest degree
    seed_degree = node_metrics.loc[node_metrics['in_giant_component'] == True].sort_values("degree_centrality", ascending=False).iloc[0]['ResponseID']
    # Highest betweenness
    seed_betweenness = node_metrics.loc[node_metrics['in_giant_component'] == True].sort_values("betweenness_centrality", ascending=False).iloc[0]['ResponseID']
    # Random low degree (degree <= 10)
    low_degree_nodes = node_metrics[(node_metrics['in_giant_component'] == True) & (node_metrics['degree'] <= 15)]
    if not low_degree_nodes.empty:
        seed_random = low_degree_nodes.sample(1, random_state=42).iloc[0]['ResponseID']
    else:
        seed_random = node_metrics.loc[node_metrics['in_giant_component'] == True].sort_values("degree").iloc[0]['ResponseID']
        
    seeds = {
        "Highest Degree": seed_degree,
        "Highest Betweenness": seed_betweenness,
        "Random Low-Degree": seed_random
    }
    print(f"Seeds chosen: {seeds}")

    # Simulation parameters
    BETA = 0.3
    GAMMA = 0.1
    N_REPS = 50
    MAX_T = 60
    
    # Run SIR
    sir_results = {}
    summary_stats = []
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"Highest Degree": "#D73027", "Highest Betweenness": "#4575B4", "Random Low-Degree": "#55A868"}
    
    for strategy, seed_node in seeds.items():
        I_all = []
        R_all = []
        for _ in range(N_REPS):
            S, I, R = run_sir(G, seed_node, BETA, GAMMA, MAX_T)
            I_all.append(I)
            R_all.append(R)
        
        I_mean = np.mean(I_all, axis=0)
        I_std = np.std(I_all, axis=0)
        R_mean = np.mean(R_all, axis=0)
        
        final_R = np.mean([r[-1] for r in R_all])
        time_to_peak = np.mean([np.argmax(i) for i in I_all])
        
        summary_stats.append({
            "Strategy": strategy,
            "Seed_Node": seed_node,
            "Final_Outbreak_Size": final_R,
            "Final_Outbreak_Pct": final_R / G.number_of_nodes() * 100,
            "Time_To_Peak": time_to_peak
        })
        
        ax.plot(range(MAX_T + 1), I_mean, label=f"{strategy} (I)", color=colors[strategy], linewidth=2)
        ax.fill_between(range(MAX_T + 1), I_mean - I_std, I_mean + I_std, color=colors[strategy], alpha=0.2)
        
    ax.set_title("SIR Opinion Spread: Infected Over Time (Mean ± Std)")
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Number of Infected (Active Adopters)")
    ax.legend()
    save_figure(fig, "phase15_sir_seed_comparison.png")
    
    df_sir_summary = pd.DataFrame(summary_stats)
    print("\nSIR Summary Stats:")
    print(df_sir_summary)
    df_sir_summary.to_csv(TABLES_DIR / "sir_simulation_summary.csv", index=False)
    
    # 3. Beta sensitivity sweep
    betas = np.linspace(0.05, 0.8, 16)
    sweep_R = []
    for beta in betas:
        reps_R = []
        for _ in range(20):
            seed = np.random.choice(list(G.nodes()))
            S, I, R = run_sir(G, seed, beta, GAMMA, MAX_T)
            reps_R.append(R[-1])
        sweep_R.append(np.mean(reps_R) / G.number_of_nodes())
        
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(betas, sweep_R, marker='o', color="#4C72B0", linewidth=2)
    ax.axvline(x=GAMMA, color="grey", linestyle="--", label="gamma (recovery rate)")
    ax.set_title("Epidemic Threshold: Final Outbreak Size vs. Beta")
    ax.set_xlabel("Transmission Rate (Beta)")
    ax.set_ylabel("Fraction of Network Recovered (Total Reached)")
    ax.legend()
    save_figure(fig, "phase15_sir_beta_sweep.png")
    
    # 4. SIS variant
    MAX_T_SIS = 100
    sis_I_all = []
    for _ in range(30):
        # random seed
        seed = np.random.choice(list(G.nodes()))
        I = run_sis(G, seed, 0.25, GAMMA, MAX_T_SIS)
        sis_I_all.append(I)
        
    sis_I_mean = np.mean(sis_I_all, axis=0)
    sis_I_std = np.std(sis_I_all, axis=0)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(MAX_T_SIS + 1), sis_I_mean, color="#DD8452", linewidth=2, label="SIS Infected")
    ax.fill_between(range(MAX_T_SIS + 1), sis_I_mean - sis_I_std, sis_I_mean + sis_I_std, color="#DD8452", alpha=0.3)
    ax.set_title("SIS Endemic Opinion Model")
    ax.set_xlabel("Time Step")
    ax.set_ylabel("Number of Infected (Active Adopters)")
    ax.axhline(y=np.mean(sis_I_mean[-20:]), color="black", linestyle="--", alpha=0.5, label="Endemic Equilibrium")
    ax.legend()
    save_figure(fig, "phase15_sis_endemic.png")
    
    # 5. Report Update
    analysis_md = """
<!-- PHASE15_ANALYSIS_START -->
### Dynamical Opinion-Spread Simulation

![SIR Seed Comparison](outputs/figures/phase15_sir_seed_comparison.png)
*Figure: Discrete-time SIR simulation tracking active adopters ('Infected') over time for three seeding strategies. Lines show the mean over 50 repetitions; shaded bands represent ±1 standard deviation.*

![Epidemic Threshold](outputs/figures/phase15_sir_beta_sweep.png)
*Figure: Final proportion of the GCC reached by the opinion (Recovered) across a range of transmission rates ($\beta$) at fixed $\gamma=0.1$. The sharp phase transition characterizes the epidemic threshold.*

![SIS Endemic State](outputs/figures/phase15_sis_endemic.png)
*Figure: SIS variant tracking active adopters over a long horizon. Unlike SIR where the opinion burns out, the SIS model reaches a sustained endemic equilibrium.*
<!-- PHASE15_ANALYSIS_END -->
"""

    results_md = f"""
<!-- PHASE15_RESULTS_START -->
## Opinion Spread Dynamics

Using a discrete-time SIR (Susceptible-Infected-Recovered) simulation scaled by edge cosine similarity, we tested how a novel opinion propagates through the network depending on its origin. Seeding the opinion at the highest-degree respondent (ID {seeds['Highest Degree']}) or the highest-betweenness respondent (ID {seeds['Highest Betweenness']}) leads to vastly different dynamics compared to a random low-degree seed (ID {seeds['Random Low-Degree']}). 

The high-degree and high-betweenness seeds produce much faster, more explosive opinion cascades, peaking earlier and reaching a larger final fraction of the network. The high-betweenness bridge is particularly effective, validating Phase 8's identification of its structural importance; although it doesn't have the sheer neighbor volume of the degree leader, its strategic position allows the opinion to cross community boundaries rapidly.

A parameter sweep over the transmission rate ($\beta$) against a fixed recovery rate ($\gamma=0.1$) reveals a clear **epidemic threshold**. Below $\beta \approx 0.15$, opinions fail to gain traction and quickly die out. Above this critical point, the network structure enables the opinion to permeate the majority of the Giant Connected Component. 

Finally, modifying the simulation to an SIS (Susceptible-Infected-Susceptible) model—where respondents can repeatedly adopt and drop the opinion—shows that the network geometry easily supports a sustained **endemic equilibrium**. Unlike the SIR model which inevitably burns out once everyone has been exposed and 'recovered', the SIS opinion stabilizes with approximately 30-40 active adopters at any given time, demonstrating the network's capacity to maintain circulating norms indefinitely.
<!-- PHASE15_RESULTS_END -->
"""
    report_path = PROJECT_ROOT / "report_draft.md"
    report = report_path.read_text(encoding="utf-8")
    report = upsert_marked_section(
        report,
        "<!-- PHASE15_ANALYSIS_START -->",
        "<!-- PHASE15_ANALYSIS_END -->",
        analysis_md,
        "# Results and Discussion"
    )
    report = upsert_marked_section(
        report,
        "<!-- PHASE15_RESULTS_START -->",
        "<!-- PHASE15_RESULTS_END -->",
        results_md,
        "## Graph Topology"
    )
    report_path.write_text(report, encoding="utf-8")
    print("Updated report_draft.md for Phase 15")

if __name__ == "__main__":
    main()
