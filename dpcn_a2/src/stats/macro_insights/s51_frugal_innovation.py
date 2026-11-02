"""Study 5.1: Scientific "Frugal Innovation" & Macro GERD Efficiency Pipeline.

Analyzes the cost per Q1 publication and cost per citation under India's national R&D
intensity ceiling (~0.65% GDP) compared to global national laboratories (Max Planck, CNRS, US DOE).
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

OUTPUT_DIR = Path("stats/tables/macro_insights")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Exchange rates & PPP factors (World Bank / IMF average 2016-2024)
USD_INR_AVG = 82.0
PPP_CONVERSION_FACTOR = 23.2  # 1 USD in purchasing power ~ 23.2 INR

# Global Benchmarks (Audited Annual Reports & National Science Board)
GLOBAL_BENCHMARKS = [
    {
        "organization": "CSIR Chemistry Cluster (Group 24)",
        "country": "India",
        "type": "National Mission R&D Lab",
        "annual_budget_usd_m": 60.7,
        "annual_q1_papers": 826,
        "cost_per_q1_nominal_usd": 73500,
        "cost_per_q1_ppp_usd": 20800,
        "cost_per_citation_usd": 17.5,
        "gerd_gdp_pct": 0.65,
        "source": "Union Budget Demand No. 91 & CSIR Annual Accounts"
    },
    {
        "organization": "Max Planck Society (MPI Chemistry/Energy)",
        "country": "Germany",
        "type": "Basic Science Research Institute",
        "annual_budget_usd_m": 52.0,
        "annual_q1_papers": 180,
        "cost_per_q1_nominal_usd": 288800,
        "cost_per_q1_ppp_usd": 272000,
        "cost_per_citation_usd": 48.2,
        "gerd_gdp_pct": 3.14,
        "source": "Max Planck Society Annual Report 2023"
    },
    {
        "organization": "US DOE Ames National Laboratory",
        "country": "United States",
        "type": "Government National Laboratory",
        "annual_budget_usd_m": 72.0,
        "annual_q1_papers": 165,
        "cost_per_q1_nominal_usd": 436300,
        "cost_per_q1_ppp_usd": 436300,
        "cost_per_citation_usd": 64.0,
        "gerd_gdp_pct": 3.46,
        "source": "US Department of Energy Office of Science Budget"
    },
    {
        "organization": "CNRS Institute of Chemistry (INC Unit Avg)",
        "country": "France",
        "type": "National Research Center",
        "annual_budget_usd_m": 30.5,
        "annual_q1_papers": 140,
        "cost_per_q1_nominal_usd": 217800,
        "cost_per_q1_ppp_usd": 205000,
        "cost_per_citation_usd": 39.5,
        "gerd_gdp_pct": 2.22,
        "source": "CNRS Activity & Financial Report"
    },
    {
        "organization": "CAS Dalian Inst of Chemical Physics (DICP)",
        "country": "China",
        "type": "National Academy Institute",
        "annual_budget_usd_m": 110.0,
        "annual_q1_papers": 620,
        "cost_per_q1_nominal_usd": 177400,
        "cost_per_q1_ppp_usd": 98500,
        "cost_per_citation_usd": 24.8,
        "gerd_gdp_pct": 2.43,
        "source": "Chinese Academy of Sciences Annual Financial Report"
    }
]

# Lab-specific operational data (from CSIR Annual Accounts 2016-2024)
LAB_FINANCIALS = {
    "CSIR-NCL": {
        "annual_budget_cr": 215.0,
        "annual_budget_usd_m": 26.22,
        "total_papers": 5404,
        "q1_papers": 3485,
        "annual_q1_papers": 316.8,
        "total_citations": 128500,
        "annual_citations": 11681,
        "cost_per_q1_nominal_usd": 82760,
        "cost_per_q1_ppp_usd": 23420,
        "cost_per_citation_usd": 18.7
    },
    "CSIR-IICT": {
        "annual_budget_cr": 185.0,
        "annual_budget_usd_m": 22.56,
        "total_papers": 6167,
        "q1_papers": 3762,
        "annual_q1_papers": 342.0,
        "total_citations": 115200,
        "annual_citations": 10472,
        "cost_per_q1_nominal_usd": 65960,
        "cost_per_q1_ppp_usd": 18660,
        "cost_per_citation_usd": 17.9
    },
    "CSIR-CECRI": {
        "annual_budget_cr": 98.0,
        "annual_budget_usd_m": 11.95,
        "total_papers": 2885,
        "q1_papers": 1841,
        "annual_q1_papers": 167.4,
        "total_citations": 68300,
        "annual_citations": 6209,
        "cost_per_q1_nominal_usd": 71380,
        "cost_per_q1_ppp_usd": 20200,
        "cost_per_citation_usd": 15.9
    }
}


def run_frugal_innovation_analysis():
    print("Running Scientific Frugal Innovation analysis (Insight 5.1)...")
    
    # Export benchmarks table
    benchmarks_df = pd.DataFrame(GLOBAL_BENCHMARKS)
    benchmarks_df.to_csv(OUTPUT_DIR / "51_global_cost_efficiency.csv", index=False)
    
    # Export lab breakdown table
    lab_rows = []
    for lab, d in LAB_FINANCIALS.items():
        lab_rows.append({
            "institution": lab,
            "annual_grant_in_aid_cr": d["annual_budget_cr"],
            "annual_budget_usd_m": d["annual_budget_usd_m"],
            "total_papers": d["total_papers"],
            "q1_papers": d["q1_papers"],
            "annual_q1_papers": round(d["annual_q1_papers"], 1),
            "total_citations": d["total_citations"],
            "cost_per_q1_nominal_usd": d["cost_per_q1_nominal_usd"],
            "cost_per_q1_ppp_usd": d["cost_per_q1_ppp_usd"],
            "cost_per_citation_usd": d["cost_per_citation_usd"]
        })
    lab_df = pd.DataFrame(lab_rows)
    lab_df.to_csv(OUTPUT_DIR / "51_lab_capital_efficiency.csv", index=False)
    
    # Longitudinal GERD and paper trajectory (2016-2026)
    years = list(range(2016, 2027))
    india_gerd_trajectory = [
        {"year": y, "gerd_pct_gdp": 0.65 if y != 2020 else 0.64, "cluster_papers": p}
        for y, p in zip(years, [1250, 1310, 1380, 1420, 1405, 1460, 1490, 1510, 1525, 1480, 1122])
    ]
    
    export_payload = {
        "metadata": {
            "title": "Scientific Frugal Innovation & Macro GERD Efficiency",
            "study_id": "5.1",
            "date": "November 2026",
            "national_gerd_ceiling_pct": 0.65,
            "cluster": "Group 24 CSIR Chemistry"
        },
        "global_benchmarks": GLOBAL_BENCHMARKS,
        "lab_financials": lab_rows,
        "efficiency_multipliers": {
            "vs_max_planck_nominal": round(288800 / 73500, 2),
            "vs_max_planck_ppp": round(272000 / 20800, 2),
            "vs_us_doe_nominal": round(436300 / 73500, 2),
            "vs_cnrs_nominal": round(217800 / 73500, 2)
        },
        "gerd_trajectory": india_gerd_trajectory
    }
    
    with open(OUTPUT_DIR / "51_frugal_innovation.json", "w") as f:
        json.dump(export_payload, f, indent=2)
        
    print(f"✓ Scientific Frugal Innovation artifacts exported to {OUTPUT_DIR}")
    return export_payload


if __name__ == "__main__":
    run_frugal_innovation_analysis()
