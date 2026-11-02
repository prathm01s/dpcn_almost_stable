"""Study 1.1: The Academic-Industrial Bridge Pipeline.

Calculates the Knowledge Exchange Ratio (KER) and bidirectional citation flows
between CSIR labs (NCL, IICT, CECRI) and Indian Higher Education Institutions (IITs, IISc, State Universities).
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

OUTPUT_DIR = Path("stats/tables/macro_insights")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_HEIS = [
    {"name": "Indian Institute of Science Bangalore", "short": "IISc Bangalore", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Bombay", "short": "IIT Bombay", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Madras", "short": "IIT Madras", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Delhi", "short": "IIT Delhi", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Kharagpur", "short": "IIT Kharagpur", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Kanpur", "short": "IIT Kanpur", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Roorkee", "short": "IIT Roorkee", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Guwahati", "short": "IIT Guwahati", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Indian Institute of Technology Hyderabad", "short": "IIT Hyderabad", "tier": "Tier 1: Elite National Flagship"},
    {"name": "Savitribai Phule Pune University", "short": "SPPU (Pune Univ)", "tier": "Tier 2: Regional State University"},
    {"name": "University of Hyderabad", "short": "Univ of Hyderabad (UoH)", "tier": "Tier 2: Regional State University"},
    {"name": "Osmania University", "short": "Osmania University", "tier": "Tier 2: Regional State University"},
    {"name": "Alagappa University", "short": "Alagappa University", "tier": "Tier 2: Regional State University"},
    {"name": "Anna University", "short": "Anna University (Chennai)", "tier": "Tier 2: Regional State University"},
    {"name": "University of Madras", "short": "Madras University", "tier": "Tier 2: Regional State University"}
]

CSIR_LABS = ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"]


def run_academic_bridge_analysis():
    print("Running Academic-Industrial Bridge analysis (Insight 1.1)...")
    cit_path = Path("data/final/citation_network.csv")
    conn_path = Path("data/final/indian_connections.csv")
    
    df_cit = pd.read_csv(cit_path)
    df_conn = pd.read_csv(conn_path)
    
    # Pre-filter citations involving CSIR labs
    csir_source = df_cit[df_cit["source_inst"].isin(CSIR_LABS)]
    csir_target = df_cit[df_cit["target_inst"].isin(CSIR_LABS)]
    
    bridge_results = []
    flow_matrix_rows = []
    
    for hei_meta in TARGET_HEIS:
        name = hei_meta["name"]
        short = hei_meta["short"]
        tier = hei_meta["tier"]
        
        # Aggregate across cluster
        c_out_total = int(csir_source["target_inst"].str.contains(name, na=False).sum())
        c_in_total = int(csir_target["source_inst"].str.contains(name, na=False).sum())
        
        ker_cluster = round(c_in_total / c_out_total, 3) if c_out_total > 0 else 0.0
        delta_cluster = c_in_total - c_out_total
        
        role = "Net Knowledge Exporter" if ker_cluster >= 1.0 else "Net Knowledge Importer"
        
        # Per-lab breakdown
        lab_breakdowns = {}
        for lab in CSIR_LABS:
            c_out_lab = int(((csir_source["source_inst"] == lab) & (csir_source["target_inst"].str.contains(name, na=False))).sum())
            c_in_lab = int(((csir_target["target_inst"] == lab) & (csir_target["source_inst"].str.contains(name, na=False))).sum())
            ker_lab = round(c_in_lab / c_out_lab, 3) if c_out_lab > 0 else 0.0
            lab_breakdowns[lab] = {
                "c_in": c_in_lab,
                "c_out": c_out_lab,
                "ker": ker_lab,
                "delta": c_in_lab - c_out_lab
            }
            
            flow_matrix_rows.append({
                "csir_lab": lab,
                "academic_hei": short,
                "tier": tier,
                "c_hei_to_csir": c_in_lab,
                "c_csir_to_hei": c_out_lab,
                "ker": ker_lab,
                "net_flow": c_in_lab - c_out_lab
            })

        # Co-authorship strength from indian_connections.csv
        conn_rows = df_conn[df_conn["partner_inst"].str.contains(name, na=False)]
        coauthored_papers = int(conn_rows["shared_papers"].sum()) if not conn_rows.empty else 0
        coauthored_cites = int(conn_rows["total_citations"].sum()) if not conn_rows.empty else 0
        
        bridge_results.append({
            "academic_institution": short,
            "full_name": name,
            "tier": tier,
            "c_in_received_from_hei": c_in_total,
            "c_out_sent_to_hei": c_out_total,
            "ker": ker_cluster,
            "net_citation_delta": delta_cluster,
            "exchange_role": role,
            "coauthored_papers": coauthored_papers,
            "shared_citations": coauthored_cites,
            "by_lab": lab_breakdowns
        })

    bridge_df = pd.DataFrame(bridge_results).sort_values(by="ker", ascending=False)
    bridge_df.to_csv(OUTPUT_DIR / "11_academic_bridge_ker.csv", index=False)
    
    flow_df = pd.DataFrame(flow_matrix_rows)
    flow_df.to_csv(OUTPUT_DIR / "11_academic_bridge_flows.csv", index=False)
    
    # Summary by Tier
    tier_summary = bridge_df.groupby("tier").agg(
        total_c_in=("c_in_received_from_hei", "sum"),
        total_c_out=("c_out_sent_to_hei", "sum"),
        mean_ker=("ker", "mean"),
        coauthored_papers=("coauthored_papers", "sum")
    ).reset_index()
    tier_summary["aggregate_ker"] = round(tier_summary["total_c_in"] / tier_summary["total_c_out"], 3)
    
    export_payload = {
        "metadata": {
            "title": "Academic-Industrial Bridge & Knowledge Exchange Ratio",
            "study_id": "1.1",
            "date": "November 2026",
            "total_citation_edges_evaluated": len(df_cit),
            "cluster": "Group 24 CSIR Chemistry"
        },
        "institutions_evaluated": bridge_results,
        "tier_summary": tier_summary.to_dict(orient="records"),
        "top_exporters_from_csir": bridge_df.head(5).to_dict(orient="records"),
        "top_importers_to_csir": bridge_df.tail(5).to_dict(orient="records")
    }
    
    with open(OUTPUT_DIR / "11_academic_bridge.json", "w") as f:
        json.dump(export_payload, f, indent=2)
        
    print(f"✓ Academic-Industrial Bridge artifacts exported to {OUTPUT_DIR}")
    return export_payload


if __name__ == "__main__":
    run_academic_bridge_analysis()
