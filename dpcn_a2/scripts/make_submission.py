"""Build the submission folder Group24_Submission/ (and Group24_Submission.zip) from the project outputs.

    python scripts/make_submission.py

Copies, never recomputes: the report PDF, the dataset, the network files, the tables behind the report and the
dashboard, the Global Benchmark and idea-spreading data, an offline copy of the dashboard and a README.
No API key, cache or raw response is included.
"""


import json
import shutil
import zipfile
from datetime import date
from pathlib import Path

OUT = Path("Group24_Submission")
SITE = "https://dpcnsite.vercel.app/"
MEMBERS = ["Samarth Singla", "Sanjith Ganapathi", "Prathmesh Sharma"]

FILES = {
    "Group24_CSIR_Chemistry_Report.pdf": "stats/report/Group24_CSIR_Chemistry_Report.pdf",
    # 1. dataset
    "1_dataset/group24_data.csv": "data/final/group24_data.csv",
    "1_dataset/group24_data_extended.csv": "data/final/group24_data_extended.csv",
    "1_dataset/faculty_master.csv": "data/final/faculty_master.csv",
    # 2. networks
    "2_networks/citation_network.csv": "data/final/citation_network.csv",
    "2_networks/authorship_network.csv": "data/final/authorship_network.csv",
    "2_networks/indian_connections.csv": "data/final/indian_connections.csv",
    "2_networks/work_references.csv.gz": "data/final/work_references.csv.gz",
    "2_networks/network_summary.csv": "stats/tables/network_summary.csv",
    # 3. basic statistics (the tables behind the report and the dashboard)
    "3_statistics/overview_by_lab.csv": "stats/tables/phase2_overview.csv",
    "3_statistics/overview_by_year.csv": "stats/tables/phase2_overview_by_year.csv",
    "3_statistics/publication_trend.csv": "stats/tables/publication_trend.csv",
    "3_statistics/quartile_distribution.csv": "stats/tables/quartile_distribution.csv",
    "3_statistics/citation_summary.csv": "stats/tables/citation_summary.csv",
    "3_statistics/h_index_summary.csv": "stats/tables/h_index_summary.csv",
    "3_statistics/top_journals.csv": "stats/tables/top_journals.csv",
    "3_statistics/top_cited_papers.csv": "stats/tables/top_cited_papers.csv",
    "3_statistics/research_areas_field.csv": "stats/tables/research_areas_field.csv",
    "3_statistics/faculty_performance.csv": "stats/tables/faculty_performance.csv",
    "3_statistics/department_performance.csv": "stats/tables/department_performance.csv",
    # 4. global benchmark
    "4_global_benchmark/final_peer_list.csv": "stats/tables/global_peers.csv",
    "4_global_benchmark/benchmark_summary.csv": "stats/tables/global_summary.csv",
    "4_global_benchmark/benchmark_by_year.csv": "stats/tables/global_by_year.csv",
    "4_global_benchmark/peer_selection_similarity.csv": "stats/tables/global_similarity.csv",
    "4_global_benchmark/peer_selection_funnel.csv": "stats/tables/global_rule_funnel.csv",
    "4_global_benchmark/peer_exclusions_with_reasons.csv": "config/overrides/global_peer_exclusions.csv",
    "4_global_benchmark/peer_rules.yaml": "config/global_benchmark.yaml",
    "4_global_benchmark/scope_subfields.csv": "data/final/global/scope_subfields.csv",
    "4_global_benchmark/country_relations.csv": "stats/tables/global_country_relations.csv",
    "4_global_benchmark/countries_world_share.csv": "stats/tables/global_countries.csv",
    "4_global_benchmark/world_baseline.csv": "stats/tables/global_world_baseline.csv",
    "4_global_benchmark/links_coauthorship_and_citations.csv": "stats/tables/global_links.csv",
    "4_global_benchmark/indian_universities_exchange.csv": "stats/tables/global_indian_universities.csv",
    "4_global_benchmark/research_profiles.csv": "stats/tables/global_profiles.csv",
    "4_global_benchmark/raw/bench_by_year.csv": "data/final/global/bench_by_year.csv",
    "4_global_benchmark/raw/journal_by_year.csv": "data/final/global/journal_by_year.csv",
    "4_global_benchmark/raw/sources.csv": "data/final/global/sources.csv",
    "4_global_benchmark/raw/country_by_year.csv": "data/final/global/country_by_year.csv",
    "4_global_benchmark/raw/collab_by_year.csv": "data/final/global/collab_by_year.csv",
    "4_global_benchmark/raw/citation_flows.csv": "data/final/global/citation_flows.csv",
    "4_global_benchmark/raw/candidates.csv": "data/final/global/candidates.csv",
    # 5. how ideas spread
    "5_how_ideas_spread/real_citation_test.json": "stats/tables/insights/11_real_diffusion.json",
    "5_how_ideas_spread/claims_with_checks.json": "stats/tables/insights/11_claims.json",
    "5_how_ideas_spread/tipping_points.csv": "stats/tables/insights/11_threshold_check.csv",
    "5_how_ideas_spread/simulation_grid.csv": "stats/tables/insights/11_simulation_grid_metrics.csv",
    "5_how_ideas_spread/seed_origin_comparison.csv": "stats/tables/insights/11_seed_origin_comparison.csv",
    "5_how_ideas_spread/field_diffusion_metrics.csv": "stats/tables/insights/11_field_diffusion_metrics.csv",
}
DASH_SKIP = {"screenshots"}


def rows(p: Path):
    if p.suffix != ".csv":
        return ""
    with open(p, encoding="utf-8", errors="replace") as f:
        return f"{sum(1 for _ in f) - 1:,}"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for dst, src in FILES.items():
        d = OUT / dst
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, d)
    # offline copy of the dashboard (open index.html)
    zp = OUT / "6_dashboard_offline.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(Path("dashboard").rglob("*")):
            if f.is_file() and not (set(f.relative_to("dashboard").parts) & DASH_SKIP):
                z.write(f, Path("dashboard") / f.relative_to("dashboard"))
    man = json.loads(Path("data/MANIFEST.json").read_text(encoding="utf-8")) if Path("data/MANIFEST.json").exists() else {}
    listing = "\n".join(f"| `{dst}` | {rows(OUT / dst)} |" for dst in FILES if dst.endswith(".csv"))
    readme = f"""# Group 24 — CSIR-NCL, CSIR-IICT, CSIR-CECRI (DPCN 2026)

**Members:** {", ".join(MEMBERS)}
**Interactive dashboard:** {SITE}
**Report:** `Group24_CSIR_Chemistry_Report.pdf` (key observations, 4 pages)
**Data:** OpenAlex, collected {man.get("collection_date", "13 Oct 2026")} (2026 is a partial year); quartiles and impact factor: SCImago.
Package built {date.today().isoformat()}.

## Contents

| Folder | What it holds |
|---|---|
| `1_dataset/` | `group24_data.csv`: one row per (paper, author at one of the three labs), the 14 required columns. `group24_data_extended.csv`: the same rows with OpenAlex IDs, faculty role, field/subfield, journal metadata and more. `faculty_master.csv`: the roster scientists with h-indices. |
| `2_networks/` | `citation_network.csv` (source_doi, target_doi, source_inst, target_inst, year), `authorship_network.csv` (author_a, author_b, paper_doi, inst_a, inst_b, year), `indian_connections.csv` (your_inst, partner_inst, shared_papers, total_citations), `work_references.csv.gz` (every reference of every paper), `network_summary.csv`. |
| `3_statistics/` | The tables behind the report and dashboard: overview per lab and per year (Q1, Q1 & IF>5, Q1 & IF>10, #authors <10 / >=10 / >=30, partners), trends, quartiles, citations, h-index, journals, most-cited papers, research areas, faculty and departments. |
| `4_global_benchmark/` | The comparison with similar institutes in the USA, China, South Korea, Australia and India: final peer list, the rules (`peer_rules.yaml`), every exclusion with its reason, the similarity of every candidate, the selection funnel, the benchmark numbers (output, growth, world top-10%/1%, Q1, Q1 & IF>5, Q1 & IF>10), co-authorship and citation links, exchange with 15 Indian universities; `raw/` holds the OpenAlex counts they are computed from. |
| `5_how_ideas_spread/` | The idea-spreading study: the test on the labs' real citations, the tipping points, the simulation results and every claim with its automatic check. |
| `6_dashboard_offline.zip` | The dashboard as static files: unzip and open `dashboard/index.html` in a browser (works offline). The same site is online at {SITE}. |

## CSV files

| File | Rows |
|---|---|
{listing}
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    zf = Path(f"{OUT}.zip")
    with zipfile.ZipFile(zf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, Path(OUT.name) / p.relative_to(OUT))
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{OUT}/: {len(files)} files, {size / 1e6:.1f} MB; {zf}: {zf.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
