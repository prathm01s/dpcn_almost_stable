/**
 * Insight 11 Interactive Scientific Portal Logic
 * Renders Cadre Networks, 4-Network Overlay, Seed Origin Differences, Intra-Institute Spreading,
 * SI vs. NIMFA Spreading Suite, and Data Cleaning Provenance.
 */

(function () {
  const SUITE = window.G24_INSIGHTS11_SUITE || {};

  // State
  let currentSection = "overlay";
  let currentNetworkTab = "coauthorship";
  let currentSimNetwork = "cadre_authorship";
  let currentSimField = "Chemistry";
  let currentSimModel = "overlay";
  let currentOverlayField = "Chemistry";
  let currentSeedOriginNet = "cadre_authorship";
  let currentIntraNet = "cadre_authorship";

  let networkChart = null;
  let overlayChart = null;
  let seedOriginChart = null;
  let intraChart = null;
  let diffusionChart = null;

  const LAB_COLORS = {
    "CSIR-IICT": "#2563eb",
    "CSIR-NCL": "#059669",
    "CSIR-CECRI": "#ea580c"
  };

  function fmt(n) {
    return Number(n || 0).toLocaleString();
  }

  /* ---------------- Navigation ---------------- */
  function initNav() {
    document.querySelectorAll(".nav-btn[data-section]").forEach(btn => {
      btn.addEventListener("click", () => {
        const sec = btn.getAttribute("data-section");
        showSection(sec);
      });
    });
  }

  function showSection(secId) {
    currentSection = secId;
    document.querySelectorAll(".nav-btn[data-section]").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-section") === secId);
    });
    document.querySelectorAll(".section-view").forEach(v => {
      v.classList.toggle("active", v.id === `section-${secId}`);
    });

    if (secId === "overlay") {
      setTimeout(renderOverlayChart, 60);
    } else if (secId === "seed-origin") {
      setTimeout(renderSeedOriginChart, 60);
    } else if (secId === "intra-institute") {
      setTimeout(renderIntraChart, 60);
    } else if (secId === "networks") {
      setTimeout(renderNetworkGraph, 60);
    } else if (secId === "diffusion") {
      setTimeout(renderDiffusionChart, 60);
    }
  }

  /* ---------------- Section: 4-Network Overlay Comparison ---------------- */
  function initOverlay() {
    document.querySelectorAll(".pill-btn[data-overlay-field]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-overlay-field]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentOverlayField = b.getAttribute("data-overlay-field");
        renderOverlayChart();
      });
    });
  }

  function renderOverlayChart() {
    const el = document.getElementById("overlay-chart-canvas");
    if (!el || !window.echarts) return;
    if (overlayChart) overlayChart.dispose();
    overlayChart = echarts.init(el);

    const sims = SUITE.simulations || {};
    const ovData = (sims.overlay_comparison || {})[currentOverlayField] || {};

    const steps = ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"];

    const series = [
      {
        name: "Full Co-Authorship (All 7,509 Researchers)",
        type: "line",
        data: ovData.full_authorship_nimfa || [],
        smooth: true,
        itemStyle: { color: "#2563eb" },
        lineStyle: { width: 3.5 },
        symbolSize: 6
      },
      {
        name: "Cadre Co-Authorship (235 Cadre Faculty)",
        type: "line",
        data: ovData.cadre_authorship_nimfa || [],
        smooth: true,
        itemStyle: { color: "#ea580c" },
        lineStyle: { width: 3, type: "dashed" },
        symbolSize: 6
      },
      {
        name: "Cadre Faculty Citation (245 Faculty Directed)",
        type: "line",
        data: ovData.cadre_citation_nimfa || [],
        smooth: true,
        itemStyle: { color: "#7c3aed" },
        lineStyle: { width: 2.5 },
        symbolSize: 5
      },
      {
        name: "Full In-Corpus Citation (10,988 Papers DAG)",
        type: "line",
        data: ovData.full_citation_nimfa || [],
        smooth: true,
        itemStyle: { color: "#059669" },
        lineStyle: { width: 2, type: "dotted" },
        symbolSize: 4
      },
      {
        name: "50% Adoption Threshold (T50)",
        type: "line",
        data: Array(16).fill(50),
        itemStyle: { color: "#e11d48" },
        lineStyle: { width: 1.5, type: "dashed" },
        symbol: "none"
      }
    ];

    overlayChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a" },
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        formatter: prm => {
          let s = `<div style="font-weight:700; color:#4f46e5; margin-bottom:0.25rem;">Diffusion Step ${prm[0].name}</div>`;
          prm.forEach(item => {
            s += `<div>${item.marker} ${item.seriesName}: <b>${item.value}%</b></div>`;
          });
          return s;
        }
      },
      legend: {
        data: series.map(s => s.name),
        textStyle: { color: "#475569", fontSize: 11 },
        top: "bottom"
      },
      grid: { left: "4%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
      xAxis: {
        type: "category",
        name: "Step (t)",
        nameTextStyle: { color: "#64748b" },
        data: steps,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569" }
      },
      yAxis: {
        type: "value",
        name: "% Population Adoption I(t)",
        nameTextStyle: { color: "#64748b" },
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#475569" }
      },
      series: series
    });
  }

  /* ---------------- Section: Seed Origin Comparison ---------------- */
  function initSeedOrigin() {
    document.querySelectorAll(".pill-btn[data-seed-net]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-seed-net]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentSeedOriginNet = b.getAttribute("data-seed-net");
        renderSeedOriginChart();
      });
    });
  }

  function renderSeedOriginChart() {
    const el = document.getElementById("seed-origin-chart-canvas");
    if (!el || !window.echarts) return;
    if (seedOriginChart) seedOriginChart.dispose();
    seedOriginChart = echarts.init(el);

    const sims = SUITE.simulations || {};
    const seedData = (sims.seed_origins || {})[currentSeedOriginNet] || {};

    const steps = ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"];

    const ncl = seedData.ncl || { curve: [0]*16, t50: 15, final_reach: 0 };
    const iict = seedData.iict || { curve: [0]*16, t50: 15, final_reach: 0 };
    const cecri = seedData.cecri || { curve: [0]*16, t50: 15, final_reach: 0 };

    document.getElementById("seed-stat-ncl-t50").textContent = ncl.t50 + " steps";
    document.getElementById("seed-stat-iict-t50").textContent = iict.t50 + " steps";
    document.getElementById("seed-stat-cecri-t50").textContent = cecri.t50 + " steps";

    document.getElementById("seed-stat-ncl-reach").textContent = ncl.final_reach + "%";
    document.getElementById("seed-stat-iict-reach").textContent = iict.final_reach + "%";
    document.getElementById("seed-stat-cecri-reach").textContent = cecri.final_reach + "%";

    const series = [
      {
        name: "Seeds at CSIR-IICT (Hyderabad)",
        type: "line",
        data: iict.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-IICT"] },
        lineStyle: { width: 3.5 },
        symbolSize: 6
      },
      {
        name: "Seeds at CSIR-NCL (Pune)",
        type: "line",
        data: ncl.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-NCL"] },
        lineStyle: { width: 3.5 },
        symbolSize: 6
      },
      {
        name: "Seeds at CSIR-CECRI (Karaikudi)",
        type: "line",
        data: cecri.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-CECRI"] },
        lineStyle: { width: 3.5, type: currentSeedOriginNet === "cadre_authorship" ? "dashed" : "solid" },
        symbolSize: 6
      },
      {
        name: "50% Adoption Threshold",
        type: "line",
        data: Array(16).fill(50),
        itemStyle: { color: "#e11d48" },
        lineStyle: { width: 1.5, type: "dashed" },
        symbol: "none"
      }
    ];

    seedOriginChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a" },
        formatter: prm => {
          let s = `<div style="font-weight:700; color:#4f46e5; margin-bottom:0.25rem;">Step ${prm[0].name}</div>`;
          prm.forEach(item => {
            s += `<div>${item.marker} ${item.seriesName}: <b>${item.value}%</b></div>`;
          });
          return s;
        }
      },
      legend: {
        data: series.map(s => s.name),
        textStyle: { color: "#475569", fontSize: 11 },
        top: "bottom"
      },
      grid: { left: "4%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
      xAxis: {
        type: "category",
        name: "Step (t)",
        nameTextStyle: { color: "#64748b" },
        data: steps,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569" }
      },
      yAxis: {
        type: "value",
        name: "% Cluster Adoption I(t)",
        nameTextStyle: { color: "#64748b" },
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#475569" }
      },
      series: series
    });
  }

  /* ---------------- Section: Intra-Institute Spreading ---------------- */
  function initIntra() {
    document.querySelectorAll(".pill-btn[data-intra-net]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-intra-net]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentIntraNet = b.getAttribute("data-intra-net");
        renderIntraChart();
      });
    });
  }

  function renderIntraChart() {
    const el = document.getElementById("intra-chart-canvas");
    if (!el || !window.echarts) return;
    if (intraChart) intraChart.dispose();
    intraChart = echarts.init(el);

    const sims = SUITE.simulations || {};
    const intra = sims.intra_institute || {};

    const iict = (intra.iict || {})[currentIntraNet] || { curve: [0]*16, t50: 15, reach: 0, beta_c: 0, nodes: 0, edges: 0 };
    const ncl = (intra.ncl || {})[currentIntraNet] || { curve: [0]*16, t50: 15, reach: 0, beta_c: 0, nodes: 0, edges: 0 };
    const cecri = (intra.cecri || {})[currentIntraNet] || { curve: [0]*16, t50: 15, reach: 0, beta_c: 0, nodes: 0, edges: 0 };

    document.getElementById("intra-stat-iict-nodes").textContent = fmt(iict.nodes);
    document.getElementById("intra-stat-ncl-nodes").textContent = fmt(ncl.nodes);
    document.getElementById("intra-stat-cecri-nodes").textContent = fmt(cecri.nodes);

    document.getElementById("intra-stat-iict-t50").textContent = iict.t50 + " steps";
    document.getElementById("intra-stat-ncl-t50").textContent = ncl.t50 + " steps";
    document.getElementById("intra-stat-cecri-t50").textContent = cecri.t50 + " steps";

    document.getElementById("intra-stat-iict-betac").textContent = iict.beta_c;
    document.getElementById("intra-stat-ncl-betac").textContent = ncl.beta_c;
    document.getElementById("intra-stat-cecri-betac").textContent = cecri.beta_c;

    const steps = ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"];

    const series = [
      {
        name: "Intra CSIR-IICT (Internal Diffusion)",
        type: "line",
        data: iict.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-IICT"] },
        lineStyle: { width: 3.5 },
        symbolSize: 6
      },
      {
        name: "Intra CSIR-NCL (Internal Diffusion)",
        type: "line",
        data: ncl.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-NCL"] },
        lineStyle: { width: 3.5 },
        symbolSize: 6
      },
      {
        name: "Intra CSIR-CECRI (Internal Diffusion)",
        type: "line",
        data: cecri.curve || [],
        smooth: true,
        itemStyle: { color: LAB_COLORS["CSIR-CECRI"] },
        lineStyle: { width: 3.5, type: currentIntraNet === "cadre_authorship" ? "dashed" : "solid" },
        symbolSize: 6
      },
      {
        name: "50% Adoption Threshold",
        type: "line",
        data: Array(16).fill(50),
        itemStyle: { color: "#e11d48" },
        lineStyle: { width: 1.5, type: "dashed" },
        symbol: "none"
      }
    ];

    intraChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a" },
        formatter: prm => {
          let s = `<div style="font-weight:700; color:#4f46e5; margin-bottom:0.25rem;">Step ${prm[0].name}</div>`;
          prm.forEach(item => {
            s += `<div>${item.marker} ${item.seriesName}: <b>${item.value}%</b></div>`;
          });
          return s;
        }
      },
      legend: {
        data: series.map(s => s.name),
        textStyle: { color: "#475569", fontSize: 11 },
        top: "bottom"
      },
      grid: { left: "4%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
      xAxis: {
        type: "category",
        name: "Step (t)",
        nameTextStyle: { color: "#64748b" },
        data: steps,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569" }
      },
      yAxis: {
        type: "value",
        name: "% Intra-Lab Adoption I(t)",
        nameTextStyle: { color: "#64748b" },
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#475569" }
      },
      series: series
    });
  }

  /* ---------------- Section: Cadre Networks ---------------- */
  function initNetworks() {
    document.querySelectorAll(".pill-btn[data-net-tab]").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-net-tab]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentNetworkTab = btn.getAttribute("data-net-tab");
        renderNetworkGraph();
      });
    });
  }

  function renderNetworkGraph() {
    const el = document.getElementById("cadre-network-canvas");
    if (!el || !window.echarts) return;
    if (networkChart) networkChart.dispose();
    networkChart = echarts.init(el);

    const isAuth = currentNetworkTab === "coauthorship";
    const graphData = isAuth ? SUITE.cadre_coauthorship : SUITE.cadre_citation;

    if (!graphData || !graphData.nodes) {
      el.innerHTML = '<div style="padding:2rem; text-align:center; color:#94a3b8;">Network data loading...</div>';
      return;
    }

    const m = graphData.metrics || {};
    document.getElementById("net-stat-nodes").textContent = fmt(m.connected_faculty || m.total_cadre_faculty);
    document.getElementById("net-stat-edges").textContent = fmt(m.edges);
    document.getElementById("net-stat-density").textContent = m.density;
    document.getElementById("net-stat-special").textContent = isAuth ? (m.clustering || "0.291") : (m.reciprocity || "0.285");
    document.getElementById("net-stat-special-label").textContent = isAuth ? "Avg Clustering" : "Reciprocity";

    const nodes = (graphData.nodes || []).map(n => {
      const val = isAuth ? (n.degree || 1) : ((n.in_degree || 0) + (n.out_degree || 0));
      return {
        id: n.id,
        name: n.name,
        lab: n.lab,
        dept: n.dept,
        faculty_id: n.faculty_id,
        symbolSize: Math.max(12, Math.min(36, Math.sqrt(val) * 6)),
        itemStyle: { color: LAB_COLORS[n.lab] || "#64748b", borderColor: "#ffffff", borderWidth: 2 },
        value: val,
        raw: n
      };
    });

    const links = (graphData.links || []).map(l => ({
      source: l.source,
      target: l.target,
      value: l.weight || 1,
      lineStyle: {
        color: isAuth ? "rgba(100, 116, 139, 0.3)" : "rgba(37, 99, 235, 0.4)",
        width: Math.min(4, Math.max(1, (l.weight || 1) * 0.7)),
        curveness: isAuth ? 0 : 0.15
      }
    }));

    networkChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a" },
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        formatter: p => {
          if (p.dataType === "edge") {
            return `<b>${isAuth ? "Co-authorship" : "Citation"} Link</b><br/>${p.data.source} → ${p.data.target}<br/>Weight: <b>${p.data.value}</b> ${isAuth ? "joint papers" : "citations"}`;
          }
          const d = p.data.raw;
          if (isAuth) {
            return `<div style="font-weight:700; color:#4f46e5;">${d.name}</div>
                    <div style="font-size:0.8rem; color:#64748b;">${d.desig || ""} · ${d.lab}</div>
                    <div style="font-size:0.8rem; color:#64748b;">${d.dept}</div>
                    <div style="margin-top:0.4rem; font-size:0.85rem;">
                      Faculty Degree: <b>${d.degree}</b> peers<br/>
                      Strength: <b>${d.strength}</b> joint papers<br/>
                      Betweenness: <b>${d.betweenness}</b><br/>
                      In-Corpus Papers: <b>${d.papers}</b> · h-index: <b>${d.h_index}</b>
                    </div>`;
          } else {
            return `<div style="font-weight:700; color:#4f46e5;">${d.name}</div>
                    <div style="font-size:0.8rem; color:#64748b;">${d.lab}</div>
                    <div style="margin-top:0.4rem; font-size:0.85rem;">
                      In-Citations (From Cadre): <b>${d.in_degree}</b><br/>
                      Out-Citations (To Cadre): <b>${d.out_degree}</b><br/>
                      PageRank Centrality: <b>${d.pagerank}</b>
                    </div>`;
          }
        }
      },
      series: [{
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        data: nodes,
        links: links,
        edgeSymbol: isAuth ? ["none", "none"] : ["none", "arrow"],
        edgeSymbolSize: isAuth ? [0, 0] : [0, 6],
        force: {
          repulsion: isAuth ? 160 : 190,
          edgeLength: [40, 140],
          gravity: 0.1
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 3 }
        }
      }]
    });

    renderNetworkTables(isAuth, graphData);
  }

  function renderNetworkTables(isAuth, data) {
    const leaderEl = document.getElementById("net-leaderboard-body");
    const matrixEl = document.getElementById("net-matrix-body");
    if (!leaderEl || !matrixEl) return;

    if (isAuth) {
      document.getElementById("net-leader-title").textContent = "Top Cadre Collaborators (Degree & Strength)";
      document.getElementById("net-matrix-title").textContent = "Inter-Lab Co-Authorship Matrix";

      leaderEl.innerHTML = (data.top_degree || []).slice(0, 8).map(r => `
        <tr>
          <td><b>${r.name}</b></td>
          <td><span class="inst-badge ${r.lab === 'CSIR-IICT' ? 'iict' : (r.lab === 'CSIR-NCL' ? 'ncl' : 'cecri')}">${r.lab}</span></td>
          <td><b>${r.degree}</b> peers</td>
          <td>${r.strength} papers</td>
        </tr>
      `).join("");

      matrixEl.innerHTML = (data.collab_matrix || []).map(r => `
        <tr>
          <td><b>${r.pair}</b></td>
          <td><b>${fmt(r.joint_papers)}</b> joint papers</td>
        </tr>
      `).join("");
    } else {
      document.getElementById("net-leader-title").textContent = "Top Cited Cadre Faculty (In-Degree & PageRank)";
      document.getElementById("net-matrix-title").textContent = "Inter-Lab Citation Flow Matrix";

      leaderEl.innerHTML = (data.top_cited_faculty || []).slice(0, 8).map(r => `
        <tr>
          <td><b>${r.name}</b></td>
          <td><span class="inst-badge ${r.lab === 'CSIR-IICT' ? 'iict' : (r.lab === 'CSIR-NCL' ? 'ncl' : 'cecri')}">${r.lab}</span></td>
          <td><b>${r.in_citations}</b> citations</td>
          <td>PR: ${r.pagerank}</td>
        </tr>
      `).join("");

      matrixEl.innerHTML = (data.citation_flow_matrix || []).map(r => `
        <tr>
          <td><b>${r.source_lab} → ${r.target_lab}</b></td>
          <td><b>${fmt(r.citations)}</b> citations</td>
        </tr>
      `).join("");
    }
  }

  /* ---------------- Section: Data Cleaning ---------------- */
  function initCleaning() {
    const cl = SUITE.cleaning || {};
    const f = cl.funnel || {};

    if (f.stage_1_raw_scraped) {
      document.getElementById("clean-stat-raw").textContent = fmt(f.stage_1_raw_scraped.total);
      document.getElementById("clean-stat-ex").textContent = fmt(f.stage_2_excluded_technical_and_duplicates.total_excluded);
      document.getElementById("clean-stat-roster").textContent = fmt(f.stage_3_clean_roster.total);
      document.getElementById("clean-stat-active").textContent = fmt(f.stage_4_active_cadre_with_papers.total);
    }

    renderCleaningAuditTable(cl.sample_excluded || []);

    const searchInput = document.getElementById("clean-search");
    if (searchInput) {
      searchInput.addEventListener("input", e => {
        const query = e.target.value.toLowerCase();
        const filtered = (cl.sample_excluded || []).filter(r => 
          r.full_name.toLowerCase().includes(query) ||
          r.job_title.toLowerCase().includes(query) ||
          r.department.toLowerCase().includes(query) ||
          r.reason.toLowerCase().includes(query)
        );
        renderCleaningAuditTable(filtered);
      });
    }
  }

  function renderCleaningAuditTable(records) {
    const tbody = document.getElementById("clean-audit-tbody");
    if (!tbody) return;

    if (!records.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:1.5rem; color:#64748b;">No matching excluded records found.</td></tr>';
      return;
    }

    tbody.innerHTML = records.slice(0, 50).map(r => `
      <tr>
        <td><b>${r.full_name}</b></td>
        <td><span class="inst-badge ${r.lab === 'CSIR-IICT' ? 'iict' : (r.lab === 'CSIR-NCL' ? 'ncl' : 'cecri')}">${r.lab}</span></td>
        <td><span style="color:#e11d48; font-weight:600;">${r.job_title}</span></td>
        <td>${r.department}</td>
        <td style="font-size:0.8rem; color:var(--text-secondary);">${r.reason}</td>
      </tr>
    `).join("");
  }

  /* ---------------- Section: Diffusion Suite (SI vs NIMFA) ---------------- */
  function initDiffusion() {
    document.querySelectorAll(".pill-btn[data-sim-net]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-sim-net]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentSimNetwork = b.getAttribute("data-sim-net");
        renderDiffusionChart();
      });
    });

    document.querySelectorAll(".pill-btn[data-sim-model]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-sim-model]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentSimModel = b.getAttribute("data-sim-model");
        renderDiffusionChart();
      });
    });

    document.querySelectorAll(".pill-btn[data-sim-field]").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".pill-btn[data-sim-field]").forEach(btn => btn.classList.remove("active"));
        b.classList.add("active");
        currentSimField = b.getAttribute("data-sim-field");
        renderDiffusionChart();
      });
    });
  }

  function renderDiffusionChart() {
    const el = document.getElementById("diffusion-chart-canvas");
    if (!el || !window.echarts) return;
    if (diffusionChart) diffusionChart.dispose();
    diffusionChart = echarts.init(el);

    const sims = SUITE.simulations || {};
    const netData = sims[currentSimNetwork] || {};
    const fieldData = (netData.fields || {})[currentSimField] || {};

    if (!fieldData.mc_curve) {
      el.innerHTML = '<div style="padding:2rem; text-align:center; color:#94a3b8;">Simulation data unavailable for this selection.</div>';
      return;
    }

    const th = netData.thresholds || {};
    document.getElementById("diff-kpi-nimfa-t50").textContent = fieldData.nimfa_t50 != null ? fieldData.nimfa_t50 + " steps" : "–";
    document.getElementById("diff-kpi-mc-t50").textContent = fieldData.mc_t50 != null ? fieldData.mc_t50 + " steps" : "–";
    document.getElementById("diff-kpi-gap").textContent = (fieldData.mean_jensen_gap != null ? "+" + fieldData.mean_jensen_gap + "%" : "–");
    document.getElementById("diff-kpi-betac").textContent = th.beta_c || "–";
    document.getElementById("diff-kpi-spectral").textContent = th.beta_c_spec || "–";

    const steps = ["0","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15"];
    const series = [];

    if (currentSimModel === "overlay" || currentSimModel === "mc") {
      series.push({
        name: "Monte Carlo SI (M=35 Stochastic Trials)",
        type: "line",
        data: fieldData.mc_curve,
        smooth: true,
        itemStyle: { color: "#0284c7" },
        lineStyle: { width: 3 },
        symbolSize: 6
      });
    }

    if (currentSimModel === "overlay" || currentSimModel === "nimfa") {
      series.push({
        name: "Discrete-Time Markov Chain (NIMFA Closed-Form)",
        type: "line",
        data: fieldData.nimfa_curve,
        smooth: true,
        itemStyle: { color: "#7c3aed" },
        lineStyle: { width: 2.5, type: currentSimModel === "overlay" ? "dashed" : "solid" },
        symbolSize: 6
      });
    }

    series.push({
      name: "50% Adoption Threshold (T50)",
      type: "line",
      data: Array(16).fill(50),
      itemStyle: { color: "#e11d48" },
      lineStyle: { width: 1.5, type: "dotted" },
      symbol: "none"
    });

    diffusionChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: "#cbd5e1",
        textStyle: { color: "#0f172a" },
        formatter: prm => {
          let s = `<div style="font-weight:700; color:#4f46e5; margin-bottom:0.25rem;">Step ${prm[0].name}</div>`;
          prm.forEach(item => {
            s += `<div>${item.marker} ${item.seriesName}: <b>${item.value}%</b></div>`;
          });
          return s;
        }
      },
      legend: {
        data: series.map(s => s.name),
        textStyle: { color: "#475569", fontSize: 11 },
        top: "bottom"
      },
      grid: { left: "4%", right: "4%", bottom: "12%", top: "8%", containLabel: true },
      xAxis: {
        type: "category",
        name: "Step (t)",
        nameTextStyle: { color: "#64748b" },
        data: steps,
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#475569" }
      },
      yAxis: {
        type: "value",
        name: "% Adoption I(t)",
        nameTextStyle: { color: "#64748b" },
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#475569" }
      },
      series: series
    });

    renderSuperSpreaders(fieldData.top_super_spreaders || []);
  }

  function renderSuperSpreaders(spreaders) {
    const tbody = document.getElementById("diff-spreaders-tbody");
    if (!tbody) return;

    if (!spreaders.length) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:1rem; color:#64748b;">No super-spreader data available.</td></tr>';
      return;
    }

    tbody.innerHTML = spreaders.map(s => `
      <tr>
        <td><b>${s.name}</b></td>
        <td><span class="inst-badge ${s.lab === 'CSIR-IICT' ? 'iict' : (s.lab === 'CSIR-NCL' ? 'ncl' : 'cecri')}">${s.lab}</span></td>
        <td><b style="color:#7c3aed;">${s.dynamical_impact}</b> expected adopters</td>
        <td><b>${s.out_degree}</b> ties</td>
      </tr>
    `).join("");
  }

  /* ---------------- Init on DOM Ready ---------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initNav();
    initOverlay();
    initSeedOrigin();
    initIntra();
    initNetworks();
    initCleaning();
    initDiffusion();

    const hash = window.location.hash.replace("#", "");
    if (["overlay", "seed-origin", "intra-institute", "networks", "diffusion", "cleaning"].includes(hash)) {
      showSection(hash);
    } else {
      showSection("overlay");
    }

    window.addEventListener("resize", () => {
      if (overlayChart) overlayChart.resize();
      if (seedOriginChart) seedOriginChart.resize();
      if (intraChart) intraChart.resize();
      if (networkChart) networkChart.resize();
      if (diffusionChart) diffusionChart.resize();
    });
  });
})();
