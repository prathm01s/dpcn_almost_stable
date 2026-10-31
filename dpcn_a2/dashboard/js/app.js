/**
 * DPCN Research Mapping Dashboard — Group 24 App Engine
 * Interactive client-side controller supporting offline execution via file://
 */

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_DATA) {
    console.error("G24_DATA not found. Run 'make dashboard' first.");
    return;
  }

  const data = window.G24_DATA;
  let currentInst = "all";
  let activeTab = "overview";
  const charts = {};

  // Color mapping
  const colors = {
    iict: "#2b5c8f",
    ncl: "#2e7d32",
    cecri: "#d95f02",
    all: "#4a148c",
    q1: "#10b981",
    q2: "#3b82f6",
    q3: "#f59e0b",
    q4: "#ef4444",
    unranked: "#94a3b8",
  };

  // Filter state
  const state = {
    yearMin: 2016,
    yearMax: 2026,
    type: "all",
    quartile: "all",
    field: "all",
  };

  // DOM Elements
  const kpiTotalPapers = document.getElementById("kpi-total-papers");
  const kpiJournalPapers = document.getElementById("kpi-journal-papers");
  const kpiQ1Share = document.getElementById("kpi-q1-share");
  const kpiTotalCitations = document.getElementById("kpi-total-citations");
  const kpiMeanCitations = document.getElementById("kpi-mean-citations");
  const kpiActiveFaculty = document.getElementById("kpi-active-faculty");
  const kpiMedianH = document.getElementById("kpi-median-h");

  // Filter selects
  const filterYearMin = document.getElementById("filter-year-min");
  const filterYearMax = document.getElementById("filter-year-max");
  const filterType = document.getElementById("filter-type");
  const filterQuartile = document.getElementById("filter-quartile");
  const filterField = document.getElementById("filter-field");
  const btnReset = document.getElementById("btn-reset-filters");

  // Populate Field filter options
  if (filterField) {
    const allFields = new Set();
    data.papers_compact.forEach(p => { if (p.f) allFields.add(p.f); });
    Array.from(allFields).sort().forEach(f => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      filterField.appendChild(opt);
    });
  }

  // Segmented Institute Selector
  document.querySelectorAll(".inst-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".inst-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentInst = btn.dataset.inst;
      updateDashboard();
    });
  });

  // Tab Navigation
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.dataset.tab;
      const target = document.getElementById(`tab-${activeTab}`);
      if (target) target.classList.add("active");
      // Resize visible charts and redraw tables
      setTimeout(() => {
        Object.values(charts).forEach(c => c && c.resize && c.resize());
        if (facultyTable) facultyTable.redraw(true);
        if (topPapersTable) topPapersTable.redraw(true);
        if (activeTab === "citation-net") renderCitationNetwork();
        if (activeTab === "authorship-net") renderAuthorshipNetwork();
        if (activeTab === "connectivity") renderConnectivity();
        if (activeTab === "insights") renderInsights();
      }, 50);
    });
  });

  // Filter Event Listeners
  const onFilterChange = () => {
    state.yearMin = parseInt(filterYearMin.value);
    state.yearMax = parseInt(filterYearMax.value);
    state.type = filterType.value;
    state.quartile = filterQuartile.value;
    state.field = filterField.value;
    updateDashboard();
  };

  [filterYearMin, filterYearMax, filterType, filterQuartile, filterField].forEach(el => {
    if (el) el.addEventListener("change", onFilterChange);
  });

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      filterYearMin.value = 2016;
      filterYearMax.value = 2026;
      filterType.value = "all";
      filterQuartile.value = "all";
      filterField.value = "all";
      onFilterChange();
    });
  }

  // Filter papers_compact based on state
  function getFilteredPapers() {
    return data.papers_compact.filter(p => {
      if (currentInst !== "all" && currentInst !== "compare" && p.inst !== currentInst) return false;
      if (p.yr < state.yearMin || p.yr > state.yearMax) return false;
      if (state.type !== "all" && p.t !== state.type) return false;
      if (state.quartile !== "all" && p.q !== state.quartile) return false;
      if (state.field !== "all" && p.f !== state.field) return false;
      return true;
    });
  }

  // Main Dashboard Update
  function updateDashboard() {
    renderKPIs();
    renderOverviewCharts();
    renderImpactRatio();
    renderFacultyPanels();
    renderVenuesPanels();
    renderResearchAreasCharts();
    if (activeTab === "citation-net") renderCitationNetwork();
    if (activeTab === "authorship-net") renderAuthorshipNetwork();
    if (activeTab === "connectivity") renderConnectivity();
  }

  // 1. KPI Strip Rendering
  function renderKPIs() {
    const isFiltered = state.yearMin !== 2016 || state.yearMax !== 2026 || state.type !== "all" || state.quartile !== "all" || state.field !== "all";
    const instBundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];

    // Faculty and h-index KPIs always come from pre-aggregated bundle
    // (they can't be derived from compact paper records)
    if (instBundle && instBundle.h_index && instBundle.h_index.summary) {
      const h = instBundle.h_index.summary;
      kpiActiveFaculty.textContent = h.active_faculty_count != null ? h.active_faculty_count.toLocaleString() : "-";
      kpiMedianH.textContent = h.median_h_index != null ? h.median_h_index.toFixed(1) : "-";
    } else {
      kpiActiveFaculty.textContent = "-";
      kpiMedianH.textContent = "-";
    }

    if (!isFiltered && instBundle) {
      // Authoritative baseline numbers
      const q = instBundle.quartiles.overall;
      const c = instBundle.citations.overall;
      const totPapers = instBundle.trend.reduce((acc, t) => acc + t.total, 0);
      const totJournals = instBundle.trend.reduce((acc, t) => acc + t.journal, 0);

      kpiTotalPapers.textContent = totPapers.toLocaleString();
      kpiJournalPapers.textContent = totJournals.toLocaleString();
      kpiQ1Share.textContent = `${q.q1_fraction_primary_pct.toFixed(1)}%`;
      kpiTotalCitations.textContent = c.total_citations.toLocaleString();
      kpiMeanCitations.textContent = c.mean_citations.toFixed(1);
    } else {
      // Re-computed from filtered papers
      const filtered = getFilteredPapers();
      const distinctWorks = new Map();
      filtered.forEach(p => {
        if (!distinctWorks.has(p.id)) distinctWorks.set(p.id, p);
      });
      const papers = Array.from(distinctWorks.values());

      const tot = papers.length;
      const journals = papers.filter(p => p.t === "journal");
      const q1 = journals.filter(p => p.q === "Q1").length;
      const rankedJournals = journals.filter(p => ["Q1", "Q2", "Q3", "Q4"].includes(p.q)).length;
      const q1Pct = rankedJournals > 0 ? (q1 / rankedJournals * 100).toFixed(1) : "0.0";
      const totalCites = papers.reduce((acc, p) => acc + p.c, 0);
      const meanCites = tot > 0 ? (totalCites / tot).toFixed(1) : "0.0";

      kpiTotalPapers.textContent = tot.toLocaleString();
      kpiJournalPapers.textContent = journals.length.toLocaleString();
      kpiQ1Share.textContent = `${q1Pct}%`;
      kpiTotalCitations.textContent = totalCites.toLocaleString();
      kpiMeanCitations.textContent = meanCites;
    }
  }

  // 2. Overview Charts (Trend + Quartiles)
  function renderOverviewCharts() {
    const trendEl = document.getElementById("chart-trend");
    if (!trendEl) return;
    if (!charts.trend) charts.trend = echarts.init(trendEl);

    const years = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

    if (currentInst === "compare") {
      // Comparison: 3 series for IICT, NCL, CECRI
      const series = ["iict", "ncl", "cecri"].map(k => {
        const bundle = data.by_institute[k];
        const counts = years.map(y => {
          const item = bundle.trend.find(t => t.year === y);
          return item ? item.total : 0;
        });
        return {
          name: bundle.name,
          type: "bar",
          data: counts,
          itemStyle: { color: colors[k] },
        };
      });

      charts.trend.setOption({
        tooltip: { trigger: "axis" },
        legend: { data: ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"], bottom: 0 },
        xAxis: { type: "category", data: years.map(y => y === 2026 ? "2026*" : y) },
        yAxis: { type: "value", name: "Distinct Papers" },
        series: series,
      }, true);
    } else {
      const bundle = data.by_institute[currentInst];
      const jData = years.map(y => {
        const item = bundle.trend.find(t => t.year === y);
        return item ? item.journal : 0;
      });
      const cData = years.map(y => {
        const item = bundle.trend.find(t => t.year === y);
        return item ? item.conference : 0;
      });

      charts.trend.setOption({
        tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
        legend: { data: ["Journal Articles", "Conference Proceedings"], bottom: 0 },
        xAxis: { type: "category", data: years.map(y => y === 2026 ? "2026 (Partial)*" : y) },
        yAxis: { type: "value", name: "Annual Papers" },
        series: [
          { name: "Journal Articles", type: "bar", stack: "total", data: jData, itemStyle: { color: colors[currentInst] } },
          { name: "Conference Proceedings", type: "bar", stack: "total", data: cData, itemStyle: { color: "#f59e0b" } },
        ],
      }, true);
    }

    // Quartile Donut Chart
    const qEl = document.getElementById("chart-quartile");
    if (!qEl) return;
    if (!charts.quartile) charts.quartile = echarts.init(qEl);

    const qOverall = data.by_institute[currentInst === "compare" ? "all" : currentInst].quartiles.overall;
    charts.quartile.setOption({
      tooltip: { trigger: "item", formatter: "{b}: {c} papers ({d}%)" },
      legend: { bottom: 0 },
      series: [{
        name: "Quartile Share",
        type: "pie",
        radius: ["40%", "70%"],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        data: [
          { value: qOverall.q1, name: "Q1 (Top 25%)", itemStyle: { color: colors.q1 } },
          { value: qOverall.q2, name: "Q2", itemStyle: { color: colors.q2 } },
          { value: qOverall.q3, name: "Q3", itemStyle: { color: colors.q3 } },
          { value: qOverall.q4, name: "Q4", itemStyle: { color: colors.q4 } },
          { value: qOverall.unranked, name: "Unranked", itemStyle: { color: colors.unranked } },
        ],
      }],
    }, true);
  }

  // 2b. Q1 by citation impact ratio (IR = citations received / references made)
  // Threshold = 75th percentile of paper IR over all papers (top 25%, like a quartile)
  const irThreshold = data.impact_ratio ? data.impact_ratio.percentile_threshold : null;

  // Same filters as getFilteredPapers(), for a given institute key ("all" = distinct papers)
  function filteredPapersFor(instKey) {
    const seen = new Set();
    return data.papers_compact.filter(p => {
      if (instKey !== "all" && p.inst !== instKey) return false;
      if (p.yr < state.yearMin || p.yr > state.yearMax) return false;
      if (state.type !== "all" && p.t !== state.type) return false;
      if (state.quartile !== "all" && p.q !== state.quartile) return false;
      if (state.field !== "all" && p.f !== state.field) return false;
      if (instKey === "all") {
        if (seen.has(p.id)) return false;
        seen.add(p.id);
      }
      return true;
    });
  }

  function impactStats(papers, threshold) {
    const withRefs = papers.filter(p => p.r != null && p.r > 0);
    const above = withRefs.filter(p => p.c / p.r > threshold).length;
    const cites = withRefs.reduce((a, p) => a + p.c, 0);
    const refs = withRefs.reduce((a, p) => a + p.r, 0);
    const ranked = papers.filter(p => p.t === "journal" && ["Q1", "Q2", "Q3", "Q4"].includes(p.q));
    const sjrQ1 = ranked.filter(p => p.q === "Q1").length;
    return {
      n: withRefs.length,
      noRefs: papers.length - withRefs.length,
      above,
      irQ1Pct: withRefs.length ? above / withRefs.length * 100 : 0,
      sjrQ1Pct: ranked.length ? sjrQ1 / ranked.length * 100 : 0,
      instIR: refs ? cites / refs : 0,
    };
  }

  function renderImpactRatio() {
    const el = document.getElementById("chart-impact-ratio");
    if (!el || irThreshold == null) return;
    if (!charts.impactRatio) charts.impactRatio = echarts.init(el);
    const threshold = irThreshold;
    const keys = ["iict", "ncl", "cecri", "all"];
    const names = { iict: "CSIR-IICT", ncl: "CSIR-NCL", cecri: "CSIR-CECRI", all: "All three" };
    const stats = keys.map(k => impactStats(filteredPapersFor(k), threshold));
    const label = { show: true, position: "top", formatter: p => `${p.value.toFixed(1)}%` };

    charts.impactRatio.setOption({
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: params => {
          const s = stats[params[0].dataIndex];
          return `<strong>${params[0].name}</strong><br/>` +
            `SJR Q1 journals: ${s.sjrQ1Pct.toFixed(1)}%<br/>` +
            `IR > ${threshold}: ${s.above.toLocaleString()} of ${s.n.toLocaleString()} papers (${s.irQ1Pct.toFixed(2)}%)<br/>` +
            `Institute IR: ${s.instIR.toFixed(3)}`;
        },
      },
      legend: { data: ["Q1 by journal (SJR)", `Q1 by impact ratio (IR > ${threshold})`], bottom: 0 },
      grid: { left: 50, right: 20, top: 30, bottom: 50 },
      xAxis: { type: "category", data: keys.map(k => names[k]) },
      yAxis: { type: "value", name: "% of papers", max: 100 },
      series: [
        { name: "Q1 by journal (SJR)", type: "bar", data: stats.map(s => s.sjrQ1Pct), itemStyle: { color: colors.q1 }, label },
        { name: `Q1 by impact ratio (IR > ${threshold})`, type: "bar", data: stats.map(s => s.irQ1Pct), itemStyle: { color: "#4a148c" }, label },
      ],
    }, true);

    const note = document.getElementById("ir-note");
    if (note) {
      note.innerHTML =
        `<strong>Institute impact ratio</strong> (all citations received ÷ all references made): ` +
        keys.map(k => `${names[k]} ${stats[keys.indexOf(k)].instIR.toFixed(2)}`).join(" · ") + ". " +
        `IR-Q1 share = papers with IR above the threshold ÷ papers with ≥1 reference ` +
        `(${stats[3].noRefs.toLocaleString()} papers without references in OpenAlex are excluded). ` +
        `The threshold IR > ${threshold} is the ${data.impact_ratio.percentile}th percentile of paper IR, so IR-Q1 is the top 25% of papers — the same share as a quartile. ` +
        `SJR Q1 ranks the journal; IR ranks the paper itself. ` +
        `Older papers have had longer to be cited, so IR-Q1 papers concentrate in early years.`;
    }
  }

  // 3. Faculty Panels
  let facultyTable = null;
  function renderFacultyPanels() {
    if (window.G24Profiles) G24Profiles.renderFeatured("featured-scientists", currentInst);
    const bundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];

    // Faculty Directory Table via Tabulator
    const tableEl = document.getElementById("table-faculty");
    if (tableEl && !facultyTable) {
      facultyTable = new Tabulator(tableEl, {
        data: bundle.faculty,
        layout: "fitColumns",
        pagination: "local",
        paginationSize: 15,
        // Each row opens the scientist's profile (hover card + click), see js/profiles.js
        rowFormatter: row => {
          const fid = row.getData().faculty_id;
          if (window.G24Profiles && G24Profiles.has(fid)) row.getElement().setAttribute("data-fid", fid);
        },
        columns: [
          { title: "Name", field: "name", widthGrow: 2, headerFilter: "input", headerFilterPlaceholder: "Search scientist…" },
          { title: "Institution", field: "institution", widthGrow: 1.5 },
          { title: "Department", field: "department", widthGrow: 2 },
          { title: "Designation", field: "designation", widthGrow: 1.5 },
          { title: "Papers", field: "papers", sorter: "number", width: 90 },
          { title: "Citations", field: "citations", sorter: "number", width: 95 },
          { title: "Q1 %", field: "q1_share_pct", sorter: "number", width: 85, formatter: c => `${c.getValue()}%` },
          { title: "h-Index", field: "h_index", sorter: "number", width: 90 },
        ],
      });
    } else if (facultyTable) {
      facultyTable.setData(bundle.faculty);
      facultyTable.redraw(true);
    }

    // Faculty h-index histogram
    const hEl = document.getElementById("chart-h-index");
    if (hEl) {
      if (!charts.hIndex) charts.hIndex = echarts.init(hEl);
      const hBins = bundle.h_index.bins;
      charts.hIndex.setOption({
        tooltip: { trigger: "axis" },
        xAxis: { type: "category", data: hBins.map(b => b.bin_label), name: "h-Index Range" },
        yAxis: { type: "value", name: "Faculty Count" },
        series: [{
          type: "bar",
          data: hBins.map(b => b.faculty_count),
          itemStyle: { color: colors[currentInst === "compare" ? "all" : currentInst] },
        }],
      }, true);
    }

    // Department & Divisional Performance Chart
    const deptEl = document.getElementById("chart-departments");
    if (deptEl) {
      if (!charts.departments) charts.departments = echarts.init(deptEl);
      const rawDepts = bundle.departments || [];
      const depts = [...rawDepts]
        .filter(d => d.papers > 0)
        .sort((a, b) => b.papers - a.papers)
        .slice(0, 7)
        .reverse();

      charts.departments.setOption({
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: params => {
            const item = depts[params[0].dataIndex];
            if (!item) return "";
            return `<strong>${item.department}</strong><br/>` +
              `Institution: ${item.institution}<br/>` +
              `Papers: ${item.papers.toLocaleString()}<br/>` +
              `Citations: ${item.citations.toLocaleString()}<br/>` +
              `Q1 Share: ${item.q1_share_pct.toFixed(1)}%<br/>` +
              `Active Faculty: ${item.active_faculty}<br/>` +
              `Mean h-Index: ${item.mean_h_index.toFixed(1)}<br/>` +
              `Top Field: ${item.top_field}`;
          }
        },
        grid: { left: "38%", right: "8%", top: "8%", bottom: "10%" },
        xAxis: { type: "value", name: "Papers" },
        yAxis: {
          type: "category",
          data: depts.map(d => d.department.length > 20 ? d.department.slice(0, 20) + "..." : d.department),
          axisLabel: { fontSize: 10 }
        },
        series: [{
          type: "bar",
          data: depts.map(d => d.papers),
          itemStyle: { color: colors[currentInst === "compare" ? "all" : currentInst] },
        }],
      }, true);
    }
  }

  // 4. Venues Panels
  let topPapersTable = null;
  function renderVenuesPanels() {
    const bundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];

    // Top Journals Chart
    const jEl = document.getElementById("chart-top-journals");
    if (jEl) {
      if (!charts.topJournals) charts.topJournals = echarts.init(jEl);
      const topJ = [...bundle.top_journals].reverse();
      charts.topJournals.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: "30%", right: "10%", top: "10%", bottom: "10%" },
        xAxis: { type: "value", name: "Distinct Papers" },
        yAxis: { type: "category", data: topJ.map(j => j.journal_name.length > 25 ? j.journal_name.slice(0, 25) + "..." : j.journal_name) },
        series: [{
          type: "bar",
          data: topJ.map(j => j.paper_count),
          itemStyle: { color: colors[currentInst === "compare" ? "all" : currentInst] },
        }],
      }, true);
    }

    // Top Papers Tabulator Table
    const pTableEl = document.getElementById("table-top-papers");
    if (pTableEl && !topPapersTable) {
      topPapersTable = new Tabulator(pTableEl, {
        data: bundle.top_papers,
        layout: "fitColumns",
        columns: [
          { title: "#", field: "rank", width: 50 },
          { title: "Title", field: "title", widthGrow: 3 },
          { title: "Journal", field: "journal_name", widthGrow: 2 },
          { title: "Year", field: "year", width: 70 },
          { title: "Citations", field: "citations", sorter: "number", width: 95 },
          { title: "Quartile", field: "quartile", width: 85, formatter: c => `<span class="badge-q badge-q1">${c.getValue()}</span>` },
          { title: "DOI Link", field: "doi", widthGrow: 1.5, formatter: c => c.getValue() ? `<a href="${c.getValue()}" target="_blank" style="color:#0288d1;text-decoration:none;">View Article ↗</a>` : "" },
        ],
      });
    } else if (topPapersTable) {
      topPapersTable.setData(bundle.top_papers);
      topPapersTable.redraw(true);
    }

    // Conference CORE rank chart
    const confEl = document.getElementById("chart-conference-rank");
    if (confEl) {
      if (!charts.conference) charts.conference = echarts.init(confEl);
      const cData = bundle.conference_rank;
      charts.conference.setOption({
        tooltip: { trigger: "item" },
        series: [{
          name: "CORE Ranks",
          type: "pie",
          radius: "65%",
          data: [
            { value: cData.core_a_star, name: "CORE A*" },
            { value: cData.core_a, name: "CORE A" },
            { value: cData.core_b, name: "CORE B" },
            { value: cData.core_c, name: "CORE C" },
            { value: cData.unranked, name: "Unranked / Non-CS Proceedings" },
          ],
        }],
      }, true);
    }
  }

  // 5. Research Areas Charts
  function renderResearchAreasCharts() {
    const fEl = document.getElementById("chart-research-fields");
    if (!fEl) return;
    if (!charts.fields) charts.fields = echarts.init(fEl);

    const bundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];
    const fields = bundle.research_areas.fields.slice(0, 7);

    charts.fields.setOption({
      tooltip: { trigger: "item", formatter: "{b}: {c} papers ({d}%)" },
      series: [{
        name: "Fields",
        type: "pie",
        radius: ["35%", "65%"],
        data: fields.map(f => ({ value: f.paper_count, name: f.field })),
      }],
    }, true);

    const sfEl = document.getElementById("chart-research-subfields");
    if (!sfEl) return;
    if (!charts.subfields) charts.subfields = echarts.init(sfEl);

    const subfields = [...bundle.research_areas.subfields.slice(0, 10)].reverse();
    charts.subfields.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: "30%", right: "10%", top: "5%", bottom: "10%" },
      xAxis: { type: "value", name: "Paper Count" },
      yAxis: { type: "category", data: subfields.map(sf => sf.subfield.length > 25 ? sf.subfield.slice(0, 25) + "..." : sf.subfield) },
      series: [{
        type: "bar",
        data: subfields.map(sf => sf.paper_count),
        itemStyle: { color: "#0288d1" },
      }],
    }, true);
  }

  // 6. Directed Citation Network Engine
  let citeNetworkInitialized = false;
  let citeFilterInst = "all";
  let citeMinDeg = 2;
  let citeSearchQuery = "";

  function renderCitationNetwork() {
    const cEl = document.getElementById("chart-citation-network");
    if (!cEl || !data.network || !data.network.citation) return;
    if (!charts.citationNet) {
      charts.citationNet = echarts.init(cEl);
    }

    const cData = data.network.citation;

    if (!citeNetworkInitialized) {
      citeNetworkInitialized = true;
      initCitationControls();
      populateCitationTables(cData);
    }

    const q = citeSearchQuery.toLowerCase().trim();
    let nodes = cData.nodes.filter(n => {
      if (n.in_degree < citeMinDeg) return false;
      if (citeFilterInst !== "all" && citeFilterInst !== "cross") {
        if (n.inst !== citeFilterInst) return false;
      }
      if (q) {
        const matchTitle = (n.full_title || n.name || "").toLowerCase().includes(q);
        const matchJournal = (n.journal || "").toLowerCase().includes(q);
        const matchDoi = (n.doi || "").toLowerCase().includes(q);
        if (!matchTitle && !matchJournal && !matchDoi) return false;
      }
      return true;
    });

    const nodeIds = new Set(nodes.map(n => n.id));
    let links = cData.links.filter(l => {
      if (!nodeIds.has(l.source) || !nodeIds.has(l.target)) return false;
      if (citeFilterInst === "cross") return l.is_cross;
      return true;
    });

    if (citeFilterInst === "cross") {
      const crossConnected = new Set();
      links.forEach(l => {
        crossConnected.add(l.source);
        crossConnected.add(l.target);
      });
      nodes = nodes.filter(n => crossConnected.has(n.id));
    }

    charts.citationNet.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(255, 255, 255, 0.96)",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: "#1e293b", fontFamily: "Inter, sans-serif" },
        formatter: function(params) {
          if (params.dataType === "node") {
            const d = params.data;
            return `
              <div style="font-weight:700; margin-bottom:4px; max-width:320px; white-space:normal; font-size:12px; color:#0f172a;">${d.full_title || d.name}</div>
              <div style="font-size:11px; color:#64748b; margin-bottom:6px;"><strong>${d.journal}</strong> (${d.year})</div>
              <div style="font-size:11px; line-height:1.6;">
                <div><strong>Institution:</strong> <span style="font-weight:600; color:#2b5c8f;">${d.inst}</span></div>
                <div><strong>In-Degree (Citations in Corpus):</strong> <strong>${d.in_degree}</strong></div>
                <div><strong>Total OpenAlex Citations:</strong> ${d.citations}</div>
                <div><strong>PageRank Centrality:</strong> ${d.pagerank}</div>
                <div style="margin-top:6px; font-size:10px; color:#0284c7;">DOI: ${d.doi}</div>
              </div>
            `;
          } else if (params.dataType === "edge") {
            const d = params.data;
            return `
              <div style="font-size:11px; line-height:1.5;">
                <div style="font-weight:700; color:#334155; margin-bottom:3px;">Directed Citation Edge</div>
                <div><strong>Citing Institute:</strong> ${d.s_inst}</div>
                <div><strong>Cited Institute:</strong> ${d.t_inst}</div>
                <div><strong>Connection Type:</strong> ${d.is_cross ? '<span style="color:#0284c7; font-weight:700;">Inter-Lab Citation</span>' : '<span style="color:#64748b;">Intra-Lab Citation</span>'}</div>
              </div>
            `;
          }
        }
      },
      legend: [{
        data: data.network.categories.map(c => c.name),
        top: "bottom",
        textStyle: { fontSize: 11, color: "#475569" },
      }],
      series: [{
        name: "Citation Network",
        type: "graph",
        layout: "force",
        data: nodes,
        links: links,
        categories: data.network.categories,
        roam: true,
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: [4, 8],
        label: {
          show: false,
          position: "right",
          formatter: "{b}",
          fontSize: 10,
        },
        force: {
          repulsion: 220,
          gravity: 0.12,
          edgeLength: [60, 160],
          friction: 0.6,
        },
        lineStyle: {
          color: "source",
          curveness: 0.2,
          opacity: 0.55,
          width: 1.5,
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 3.5, opacity: 0.95 },
          label: { show: true },
        },
      }],
    }, true);
  }

  function initCitationControls() {
    const filterInstEl = document.getElementById("net-cite-filter-inst");
    const sliderDegEl = document.getElementById("net-cite-slider-deg");
    const sliderDegVal = document.getElementById("net-cite-deg-val");
    const searchEl = document.getElementById("net-cite-search");
    const btnResetEl = document.getElementById("net-cite-btn-reset");

    if (filterInstEl) {
      filterInstEl.addEventListener("change", (e) => {
        citeFilterInst = e.target.value;
        renderCitationNetwork();
      });
    }

    if (sliderDegEl) {
      sliderDegEl.addEventListener("input", (e) => {
        citeMinDeg = parseInt(e.target.value, 10);
        if (sliderDegVal) sliderDegVal.textContent = citeMinDeg;
        renderCitationNetwork();
      });
    }

    if (searchEl) {
      searchEl.addEventListener("input", (e) => {
        citeSearchQuery = e.target.value;
        renderCitationNetwork();
      });
    }

    if (btnResetEl) {
      btnResetEl.addEventListener("click", () => {
        citeFilterInst = "all";
        citeMinDeg = 2;
        citeSearchQuery = "";
        if (filterInstEl) filterInstEl.value = "all";
        if (sliderDegEl) sliderDegEl.value = "2";
        if (sliderDegVal) sliderDegVal.textContent = "2";
        if (searchEl) searchEl.value = "";
        renderCitationNetwork();
        if (charts.citationNet) charts.citationNet.dispatchAction({ type: "restore" });
      });
    }
  }

  function populateCitationTables(cData) {
    const tbodyPr = document.getElementById("tbody-net-pagerank");
    if (tbodyPr && cData.top_pagerank) {
      tbodyPr.innerHTML = cData.top_pagerank.map(p => {
        const labColor = p.inst === "CSIR-IICT" ? "#2b5c8f" : p.inst === "CSIR-NCL" ? "#2e7d32" : "#d95f02";
        return `
          <tr>
            <td style="font-weight:700; color:#64748b;">${p.rank}</td>
            <td>
              <div style="font-weight:600; color:#1e293b; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${p.title}">${p.title}</div>
              <div style="font-size:0.75rem; color:#64748b;">${p.journal} (${p.year}) &bull; <span class="badge-q badge-q1">${p.quartile}</span></div>
            </td>
            <td><span class="net-badge-lab" style="background:${labColor};">${p.inst}</span></td>
            <td style="font-weight:700;">${p.in_degree}</td>
            <td style="font-family:monospace; font-weight:600; color:#0284c7;">${p.score.toFixed(5)}</td>
            <td><a href="${p.doi}" target="_blank" style="color:#0284c7; text-decoration:none; font-size:0.75rem;">DOI ↗</a></td>
          </tr>
        `;
      }).join("");
    }

    const tbodyFlow = document.getElementById("tbody-net-cite-matrix");
    if (tbodyFlow && cData.flow_matrix) {
      tbodyFlow.innerHTML = cData.flow_matrix.map(row => {
        const tot = row.iict + row.ncl + row.cecri;
        return `
          <tr>
            <td><strong>${row.source_inst}</strong></td>
            <td class="${row.source_inst === 'CSIR-IICT' ? 'matrix-diag' : 'matrix-cross'}">${row.iict.toLocaleString()}</td>
            <td class="${row.source_inst === 'CSIR-NCL' ? 'matrix-diag' : 'matrix-cross'}">${row.ncl.toLocaleString()}</td>
            <td class="${row.source_inst === 'CSIR-CECRI' ? 'matrix-diag' : 'matrix-cross'}">${row.cecri.toLocaleString()}</td>
            <td style="font-weight:700; background:#f8fafc;">${tot.toLocaleString()}</td>
          </tr>
        `;
      }).join("");
    }
  }

  // 7. Undirected Co-Authorship Network Engine
  let authNetworkInitialized = false;
  let authFilterInst = "all";
  let authMinWeight = 2;
  let authSearchQuery = "";

  function renderAuthorshipNetwork() {
    const aEl = document.getElementById("chart-authorship-network");
    if (!aEl || !data.network || !data.network.authorship) return;
    if (!charts.authorshipNet) {
      charts.authorshipNet = echarts.init(aEl);
    }

    const aData = data.network.authorship;

    if (!authNetworkInitialized) {
      authNetworkInitialized = true;
      initAuthorshipControls();
      populateAuthorshipTables(aData);
    }

    const q = authSearchQuery.toLowerCase().trim();
    let nodes = aData.nodes.filter(n => {
      if (authFilterInst !== "all" && authFilterInst !== "cross") {
        if (n.inst !== authFilterInst) return false;
      }
      if (q) {
        const matchName = (n.name || "").toLowerCase().includes(q);
        const matchDept = (n.department || "").toLowerCase().includes(q);
        if (!matchName && !matchDept) return false;
      }
      return true;
    });

    const nodeIds = new Set(nodes.map(n => n.id));
    let links = aData.links.filter(l => {
      if (!nodeIds.has(l.source) || !nodeIds.has(l.target)) return false;
      if (l.weight < authMinWeight) return false;
      if (authFilterInst === "cross") return l.is_cross;
      return true;
    });

    const connectedNodeIds = new Set();
    links.forEach(l => {
      connectedNodeIds.add(l.source);
      connectedNodeIds.add(l.target);
    });
    nodes = nodes.filter(n => connectedNodeIds.has(n.id));

    if (!charts.authorshipNet._profileClick) {
      charts.authorshipNet.on("click", prm => {
        const fid = prm.dataType === "node" && window.G24Profiles && G24Profiles.fidByName(prm.data.name);
        if (fid) G24Profiles.open(fid);
      });
      charts.authorshipNet._profileClick = true;
    }
    charts.authorshipNet.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(255, 255, 255, 0.96)",
        borderColor: "#cbd5e1",
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: "#1e293b", fontFamily: "Inter, sans-serif" },
        formatter: function(params) {
          if (params.dataType === "node") {
            const d = params.data;
            return `
              <div style="font-weight:700; font-size:13px; margin-bottom:4px; color:#0f172a;">${d.name}</div>
              <div style="font-size:11px; color:#64748b; margin-bottom:6px;">${d.designation} &bull; ${d.department}</div>
              <div style="font-size:11px; line-height:1.6;">
                <div><strong>Institution:</strong> <span style="font-weight:600; color:#2b5c8f;">${d.inst}</span></div>
                <div><strong>Collaborator Degree:</strong> <strong>${d.degree}</strong> researchers</div>
                <div><strong>Betweenness Centrality:</strong> ${d.betweenness}</div>
                <div><strong>Louvain Community:</strong> Cluster #${d.community}</div>
              </div>
              ${window.G24Profiles && G24Profiles.fidByName(d.name) ? '<div style="margin-top:6px; font-size:11px; color:#0288d1; font-weight:600;">Click to open full profile</div>' : ""}
            `;
          } else if (params.dataType === "edge") {
            const d = params.data;
            return `
              <div style="font-size:11px; line-height:1.5;">
                <div style="font-weight:700; color:#334155; margin-bottom:3px;">Co-Authorship Edge</div>
                <div><strong>Collaborators:</strong> ${d.source} &harr; ${d.target}</div>
                <div><strong>Joint Publications:</strong> <strong>${d.weight}</strong></div>
                <div><strong>Connection Type:</strong> ${d.is_cross ? '<span style="color:#d97706; font-weight:700;">Inter-Lab Collaboration</span>' : '<span style="color:#64748b;">Intra-Lab Collaboration</span>'}</div>
              </div>
            `;
          }
        }
      },
      legend: [{
        data: data.network.categories.map(c => c.name),
        top: "bottom",
        textStyle: { fontSize: 11, color: "#475569" },
      }],
      series: [{
        name: "Authorship Network",
        type: "graph",
        layout: "force",
        data: nodes,
        links: links,
        categories: data.network.categories,
        roam: true,
        label: {
          show: true,
          position: "right",
          formatter: "{b}",
          fontSize: 10,
        },
        force: {
          repulsion: 180,
          gravity: 0.1,
          edgeLength: [50, 140],
          friction: 0.65,
        },
        lineStyle: {
          color: "source",
          curveness: 0.1,
          opacity: 0.6,
          width: 1.5,
        },
        emphasis: {
          focus: "adjacency",
          lineStyle: { width: 4, opacity: 0.95 },
        },
      }],
    }, true);
  }

  function initAuthorshipControls() {
    const filterInstEl = document.getElementById("net-auth-filter-inst");
    const sliderWeightEl = document.getElementById("net-auth-slider-weight");
    const sliderWeightVal = document.getElementById("net-auth-weight-val");
    const searchEl = document.getElementById("net-auth-search");
    const btnResetEl = document.getElementById("net-auth-btn-reset");

    if (filterInstEl) {
      filterInstEl.addEventListener("change", (e) => {
        authFilterInst = e.target.value;
        renderAuthorshipNetwork();
      });
    }

    if (sliderWeightEl) {
      sliderWeightEl.addEventListener("input", (e) => {
        authMinWeight = parseInt(e.target.value, 10);
        if (sliderWeightVal) sliderWeightVal.textContent = authMinWeight;
        renderAuthorshipNetwork();
      });
    }

    if (searchEl) {
      searchEl.addEventListener("input", (e) => {
        authSearchQuery = e.target.value;
        renderAuthorshipNetwork();
      });
    }

    if (btnResetEl) {
      btnResetEl.addEventListener("click", () => {
        authFilterInst = "all";
        authMinWeight = 2;
        authSearchQuery = "";
        if (filterInstEl) filterInstEl.value = "all";
        if (sliderWeightEl) sliderWeightEl.value = "2";
        if (sliderWeightVal) sliderWeightVal.textContent = "2";
        if (searchEl) searchEl.value = "";
        renderAuthorshipNetwork();
        if (charts.authorshipNet) charts.authorshipNet.dispatchAction({ type: "restore" });
      });
    }
  }

  function populateAuthorshipTables(aData) {
    const tbodyBridges = document.getElementById("tbody-net-bridges");
    if (tbodyBridges && aData.top_bridges) {
      tbodyBridges.innerHTML = aData.top_bridges.map(b => {
        const labColor = b.institution === "CSIR-IICT" ? "#2b5c8f" : b.institution === "CSIR-NCL" ? "#2e7d32" : "#d95f02";
        return `
          <tr>
            <td style="font-weight:700; color:#64748b;">${b.rank}</td>
            <td style="font-weight:600; color:#1e293b;" ${(window.G24Profiles && G24Profiles.fidByName(b.author)) ? `data-fid="${G24Profiles.fidByName(b.author)}"` : ""}>${b.author}</td>
            <td><span class="net-badge-lab" style="background:${labColor};">${b.institution}</span></td>
            <td style="font-weight:700;">${b.collaborators_count}</td>
            <td style="font-family:monospace; font-weight:600; color:#0d9488;">${b.betweenness.toFixed(4)}</td>
            <td><span style="font-size:0.75rem; color:#64748b; background:#f1f5f9; padding:2px 6px; border-radius:4px;">Cluster #${b.community_id}</span></td>
          </tr>
        `;
      }).join("");
    }

    const tbodyCollab = document.getElementById("tbody-net-auth-matrix");
    if (tbodyCollab && aData.collab_matrix) {
      tbodyCollab.innerHTML = aData.collab_matrix.map(row => {
        const totInter = (row.inst === 'CSIR-IICT' ? (row.ncl + row.cecri) : row.inst === 'CSIR-NCL' ? (row.iict + row.cecri) : (row.iict + row.ncl));
        return `
          <tr>
            <td><strong>${row.inst}</strong></td>
            <td class="${row.inst === 'CSIR-IICT' ? 'matrix-diag' : 'matrix-cross'}">${row.iict.toLocaleString()}</td>
            <td class="${row.inst === 'CSIR-NCL' ? 'matrix-diag' : 'matrix-cross'}">${row.ncl.toLocaleString()}</td>
            <td class="${row.inst === 'CSIR-CECRI' ? 'matrix-diag' : 'matrix-cross'}">${row.cecri.toLocaleString()}</td>
            <td style="font-weight:700; background:#f8fafc; color:#d97706;">${totInter.toLocaleString()}</td>
          </tr>
        `;
      }).join("");
    }
  }

  // 8. Indian Connectivity (Sections 7a / 7b)
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const instNames = { iict: "CSIR-IICT", ncl: "CSIR-NCL", cecri: "CSIR-CECRI" };

  function renderConnectivity() {
    const conn = data.connectivity;
    if (!conn) return;
    const key = currentInst === "compare" ? "all" : currentInst;
    const fmt = v => (v === null || v === undefined ? "—" : Number(v).toLocaleString());

    // KPIs
    const summary = (data.by_institute[key].indian_connections || {}).summary || {};
    const flow = conn.flow_summary[key] || {};
    document.getElementById("conn-kpi-coauth").textContent = `${summary.indian_coauthor_pct ?? "—"}%`;
    document.getElementById("conn-kpi-cites").textContent = `${summary.cites_indian_inst_pct ?? "—"}%`;
    document.getElementById("conn-kpi-cited").textContent = `${summary.cited_by_indian_inst_pct ?? "—"}%`;
    document.getElementById("conn-kpi-ratio").textContent = flow.impact_ratio_indian != null ? flow.impact_ratio_indian.toFixed(2) : "—";
    document.getElementById("conn-kpi-ratio-sub").textContent =
      `In ${fmt(flow.in_citations_indian)} / out ${fmt(flow.out_citations_indian)} citations`;

    // Year-wise flow chart
    const flowEl = document.getElementById("chart-conn-flow");
    if (flowEl) {
      if (!charts.connFlow) charts.connFlow = echarts.init(flowEl);
      let series;
      if (currentInst === "compare") {
        series = Object.keys(instNames).flatMap(k => [
          { name: `${instNames[k]} in`, type: "line", smooth: true, itemStyle: { color: colors[k] },
            data: conn.flow_by_year[k].map(r => r.in_citations_indian) },
          { name: `${instNames[k]} out`, type: "line", smooth: true, lineStyle: { type: "dashed" }, itemStyle: { color: colors[k] },
            data: conn.flow_by_year[k].map(r => r.out_citations_indian) },
        ]);
      } else {
        const rows = conn.flow_by_year[key];
        series = [
          { name: "In-flow (cited by other Indian inst.)", type: "bar", itemStyle: { color: colors[key] }, data: rows.map(r => r.in_citations_indian) },
          { name: "Out-flow (cites other Indian inst.)", type: "bar", itemStyle: { color: "#94a3b8" }, data: rows.map(r => r.out_citations_indian) },
        ];
      }
      charts.connFlow.setOption({
        tooltip: { trigger: "axis" },
        legend: { top: 0, type: "scroll" },
        grid: { left: 50, right: 20, top: 40, bottom: 30 },
        xAxis: { type: "category", data: conn.flow_by_year.all.map(r => (r.year === 2026 ? "2026*" : String(r.year))) },
        yAxis: { type: "value", name: "Citations" },
        series,
      }, true);
    }

    // Partner sector chart
    const secEl = document.getElementById("chart-conn-sectors");
    if (secEl) {
      if (!charts.connSectors) charts.connSectors = echarts.init(secEl);
      const rows = [...(conn.cross_cluster[key] || [])].sort((a, b) => a.shared_papers - b.shared_papers);
      charts.connSectors.setOption({
        tooltip: {
          trigger: "axis", axisPointer: { type: "shadow" },
          formatter: p => {
            const r = rows[p[0].dataIndex];
            return `<strong>${esc(r.link_type)}</strong>${r.is_cross_cluster ? " (cross-cluster)" : ""}<br/>` +
              `Joint papers: ${r.shared_papers.toLocaleString()}<br/>Partner institutes: ${r.partner_institutions}<br/>` +
              `Citations: ${r.total_citations.toLocaleString()}`;
          },
        },
        grid: { left: 110, right: 30, top: 10, bottom: 30 },
        xAxis: { type: "value", name: "Joint papers" },
        yAxis: { type: "category", data: rows.map(r => r.partner_sector) },
        series: [{
          type: "bar",
          data: rows.map(r => ({ value: r.shared_papers, itemStyle: { color: r.is_cross_cluster ? colors[key] : "#94a3b8" } })),
        }],
      }, true);
    }

    // Top citing institutes
    document.getElementById("tbody-conn-citing").innerHTML = (conn.top_citing_institutes[key] || []).map(r => `
      <tr><td style="font-weight:700; color:#64748b;">${r.rank}</td><td>${esc(r.citing_institution)}</td>
      <td style="font-weight:700;">${r.citing_papers.toLocaleString()}</td><td>${r.citations.toLocaleString()}</td></tr>`).join("");

    // Top partners
    document.getElementById("tbody-conn-partners").innerHTML = ((data.by_institute[key].indian_connections || {}).top_partners || []).map(r => `
      <tr><td style="font-weight:700; color:#64748b;">${r.rank}</td><td>${esc(r.partner_institution)}</td>
      <td style="font-weight:700;">${r.collaborative_papers.toLocaleString()}</td><td>${r.share_pct}%</td></tr>`).join("");

    // Hub authors
    document.getElementById("tbody-conn-hubs").innerHTML = (conn.hub_authors[key] || []).map(r => `
      <tr><td style="font-weight:700; color:#64748b;">${r.rank}</td><td style="font-weight:600;" ${window.G24Profiles && G24Profiles.fidByOpenAlex(r.author_openalex_id) ? `data-fid="${esc(G24Profiles.fidByOpenAlex(r.author_openalex_id))}"` : ""}>${esc(r.author)}</td>
      <td>${esc(r.home_institution)}</td><td>${esc(r.author_role.replace(/_/g, " "))}</td><td>${r.papers}</td>
      <td style="font-weight:700; color:#0284c7;">${r.institutions_bridged}</td><td>${r.cross_institution_papers}</td>
      <td style="font-size:0.75rem; color:#64748b; max-width:320px;">${esc(r.top_partners)}</td></tr>`).join("");

    // Lab-to-lab topic Jaccard
    const jac = {};
    conn.topic_jaccard.forEach(r => { jac[`${r.institution_a}|${r.institution_b}`] = { ...(jac[`${r.institution_a}|${r.institution_b}`] || {}), [r.level]: r }; });
    document.getElementById("tbody-conn-jaccard").innerHTML = Object.entries(jac).map(([pair, lv]) => {
      const [a, b] = pair.split("|");
      return `<tr><td>${a}</td><td>${b}</td><td style="font-weight:700;">${lv.subfield.jaccard.toFixed(3)}</td>
        <td style="font-weight:700;">${lv.topic.jaccard.toFixed(3)}</td><td>${lv.topic.shared_topics} / ${lv.topic.topics_a + lv.topic.topics_b - lv.topic.shared_topics}</td></tr>`;
    }).join("");

    // Partner topic Jaccard
    const pKeys = key === "all" ? Object.keys(instNames) : [key];
    document.getElementById("tbody-conn-partner-jaccard").innerHTML = pKeys.flatMap(k =>
      (conn.partner_topic_jaccard[k] || []).slice(0, key === "all" ? 5 : 10).map(r => `
        <tr><td>${instNames[k]}</td><td>${esc(r.partner_institution)}</td><td>${r.shared_papers}</td>
        <td>${r.shared_topics}</td><td style="font-weight:700;">${r.jaccard.toFixed(3)}</td></tr>`)).join("");

    // Most-cited citing papers
    document.getElementById("tbody-conn-papers").innerHTML = (conn.top_citing_papers[key] || []).map(r => `
      <tr><td style="font-weight:700; color:#64748b;">${r.rank}</td>
      <td><div style="font-weight:600; max-width:360px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${esc(r.title)}">${esc(r.title)}</div>
      <div style="font-size:0.75rem; color:#64748b;">${esc(r.journal_name)}</div></td>
      <td>${r.year}</td><td style="font-weight:700;">${r.citations.toLocaleString()}</td>
      <td style="font-size:0.75rem; color:#64748b; max-width:260px;">${esc(r.citing_institutions)}</td>
      <td>${r.doi ? `<a href="${esc(r.doi)}" target="_blank" style="color:#0284c7; text-decoration:none; font-size:0.75rem;">DOI ↗</a>` : ""}</td></tr>`).join("");
  }

  // ---------------------------------------------------------------------------
  // Insights Panel (Ten Non-Obvious Findings)
  // ---------------------------------------------------------------------------
  const insightCharts = {};
  let insightsRendered = false;

  function formatHeadline(text) {
    if (!text) return "";
    return text.replace(/(\b\d+(\.\d+)?%|\b\d+(\.\d+)?×|\b\d{1,3}(,\d{3})+|\b[A-Za-z0-9_ρ]+(_norm)?\s*=\s*[\d\.]+|\b\d+\.\d+\b)/g, "<strong>$1</strong>");
  }

  function renderInsights() {
    if (!window.G24_INSIGHTS) return;
    const container = document.getElementById("insights-grid");
    if (!container) return;

    const insights = window.G24_INSIGHTS;
    const insightOrder = [
      "01_friendship_paradox",
      "02_rich_club",
      "03_fragility",
      "04_price_law",
      "05_quartile_vs_impact",
      "06_pagerank_vs_citations",
      "07_sleeping_beauties",
      "08_covid_shock",
      "09_brain_circulation",
      "10_succession_risk",
      "11_information_diffusion",
    ];

    if (!insightsRendered) {
      container.innerHTML = insightOrder.map((key, idx) => {
        const item = insights[key] || {
          question: `Finding ${idx + 1}`,
          headline: "Not computed",
          method_note: "",
        };

        if (key === "11_information_diffusion") {
          return `
            <div class="card" id="card-insight-11" style="grid-column: 1 / -1; display: flex; flex-direction: column; justify-content: space-between;">
              <div>
                <div class="card-header" style="flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.75rem; align-items: center; justify-content: space-between;">
                  <div>
                    <div class="card-title" style="font-size: 1.1rem; color: var(--primary-light); font-weight: 700;">
                      #11: ${esc(item.question)}
                    </div>
                  </div>
                  <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
                    <div class="inst-segmented" id="diff-field-selector">
                      <button class="inst-btn active" data-field="Chemistry">Chemistry</button>
                      <button class="inst-btn" data-field="Materials">Materials</button>
                      <button class="inst-btn" data-field="Engineering">Engineering</button>
                      <button class="inst-btn" data-field="Energy">Energy</button>
                      <button class="inst-btn" data-field="Biochemistry">Biochemistry</button>
                      <button class="inst-btn" data-field="Medicine">Medicine</button>
                    </div>
                    <div class="inst-segmented" id="diff-cond-selector">
                      <button class="inst-btn active" data-cond="condition_a">Topic-Modulated (Full Net)</button>
                      <button class="inst-btn" data-cond="condition_b">Domain Subgraph (Uniform)</button>
                    </div>
                  </div>
                </div>

                <div id="diff-headline" style="font-size: 1.05rem; font-weight: 500; color: var(--text); line-height: 1.45; margin-bottom: 1.25rem;">
                  ${formatHeadline(esc(item.headline))}
                </div>

                <div style="display: grid; grid-template-columns: minmax(320px, 1.4fr) minmax(280px, 1fr); gap: 1.5rem; align-items: start;">
                  <div>
                    <div id="chart-insight-11_information_diffusion" class="chart-container" style="height: 380px; width: 100%;"></div>
                  </div>
                  <div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1rem;">
                      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.6rem 0.8rem;">
                        <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Epidemic Threshold</div>
                        <div id="diff-kpi-betac" style="font-size: 1.25rem; font-weight: 800; color: #2563eb;">βc = 0.032</div>
                        <div id="diff-kpi-spectral" style="font-size: 0.75rem; color: #64748b;">Spectral: 0.0324 | &lt;k&gt; = 9.84</div>
                      </div>
                      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 0.6rem 0.8rem;">
                        <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase;">Adoption Speed (T50)</div>
                        <div id="diff-kpi-t50" style="font-size: 1.25rem; font-weight: 800; color: #16a34a;">9.2 steps</div>
                        <div id="diff-kpi-nodes" style="font-size: 0.75rem; color: #64748b;">LCC Nodes: 3,202</div>
                      </div>
                    </div>

                    <div style="border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; background: white;">
                      <div style="background: #f1f5f9; padding: 0.5rem 0.75rem; font-weight: 700; font-size: 0.825rem; color: #334155; display: flex; justify-content: space-between;">
                        <span id="diff-table-title">Top 5 Super-Spreaders (Full Net)</span>
                        <span style="font-size: 0.75rem; font-weight: 500; color: #64748b;">Adoption Traction</span>
                      </div>
                      <table class="net-table" style="font-size: 0.8rem;">
                        <thead>
                          <tr>
                            <th style="padding: 0.4rem 0.6rem;">#</th>
                            <th style="padding: 0.4rem 0.6rem;">Author</th>
                            <th style="padding: 0.4rem 0.6rem;">Lab</th>
                            <th style="padding: 0.4rem 0.6rem;">Field %</th>
                            <th style="padding: 0.4rem 0.6rem;">Reach (t=3)</th>
                          </tr>
                        </thead>
                        <tbody id="tbody-diff-spreaders">
                          <!-- Populated dynamically -->
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
              <div style="margin-top: 1rem; padding-top: 0.6rem; font-size: 0.75rem; color: var(--text-muted); line-height: 1.4; border-top: 1px solid var(--border);">
                ${esc(item.method_note || "")}
              </div>
            </div>
          `;
        }

        return `
          <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div class="card-header" style="margin-bottom: 0.5rem;">
                <div class="card-title" style="font-size: 1rem; color: var(--primary-light); font-weight: 700;">
                  #${idx + 1}: ${esc(item.question)}
                </div>
              </div>
              <div style="font-size: 1.05rem; font-weight: 500; color: var(--text); line-height: 1.45; margin-bottom: 1rem;">
                ${formatHeadline(esc(item.headline))}
              </div>
              <div id="chart-insight-${key}" class="chart-container" style="height: 330px; width: 100%;"></div>
            </div>
            <div style="margin-top: 1rem; padding-top: 0.6rem; font-size: 0.75rem; color: var(--text-muted); line-height: 1.4; border-top: 1px solid var(--border);">
              ${esc(item.method_note || "")}
            </div>
          </div>
        `;
      }).join("");
      insightsRendered = true;
    }


    setTimeout(() => {
      insightOrder.forEach(key => {
        const item = insights[key];
        if (!item || !item.chart) return;
        const el = document.getElementById(`chart-insight-${key}`);
        if (!el) return;

        if (key === "11_information_diffusion") {
          initDiffusionCard(item);
          return;
        }

        if (!insightCharts[key]) {
          insightCharts[key] = echarts.init(el);
        }
        const ch = insightCharts[key];
        const chartType = item.chart.type;
        const cData = item.chart.data || {};

        if (chartType === "none") {
          ch.clear();
          el.innerHTML = `<div style="padding:2rem; color:var(--text-muted); font-size:0.9rem;">${esc(item.headline)}</div>`;
          return;
        }

        // Category axes: years arrive as numbers; match them to the category labels as strings
        const asCategory = ax => (ax && ax.type === "category" && Array.isArray(ax.data))
          ? { ...ax, data: ax.data.map(String) } : ax;
        const withNames = (ax, gap) => ax ? { ...ax, nameLocation: "middle", nameGap: gap } : ax;
        const xCat = asCategory(cData.xAxis);
        const seriesFor = list => (list || []).map(sr => {
          if (!xCat || xCat.type !== "category") return sr;
          const out = { ...sr, data: (sr.data || []).map(d => Array.isArray(d) ? [String(d[0]), d[1]] : d) };
          if (sr.markPoint && sr.markPoint.data) {
            out.markPoint = { ...sr.markPoint, data: sr.markPoint.data.map(m => m.coord ? { ...m, coord: [String(m.coord[0]), m.coord[1]] } : m) };
          }
          return out;
        });
        const xAxisOpt = withNames(xCat, 28);
        const yAxisOpt = withNames(cData.yAxis, 48);
        const gridOpt = { left: 70, right: 25, top: 20, bottom: 80 };
        const legendOpt = { ...(cData.legend || {}), type: "scroll", bottom: 0 };  // one line, never over the plot

        let option = {};
        if (chartType === "scatter") {
          option = {
            tooltip: { trigger: "item", formatter: p => `<strong>${p.seriesName}</strong><br/>X: ${p.value[0]}, Y: ${p.value[1]}` },
            legend: legendOpt,
            xAxis: { ...xAxisOpt, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
            yAxis: { ...yAxisOpt, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
            series: seriesFor(cData.series),
            grid: gridOpt,
          };
        } else if (chartType === "line") {
          option = {
            tooltip: { trigger: "axis" },
            legend: legendOpt,
            xAxis: { ...xAxisOpt, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
            yAxis: { ...yAxisOpt, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
            series: seriesFor(cData.series),
            grid: gridOpt,
          };
        } else if (chartType === "stacked_bar") {
          option = {
            tooltip: {
              trigger: "axis",
              axisPointer: { type: "shadow" },
              formatter: params => {
                let res = `<strong>${params[0].axisValue}</strong><br/>`;
                params.forEach(p => { res += `${p.marker} ${p.seriesName}: ${p.value.toFixed(1)}%<br/>`; });
                return res;
              },
            },
            legend: legendOpt,
            xAxis: xAxisOpt,
            yAxis: yAxisOpt,
            series: seriesFor(cData.series),
            grid: gridOpt,
          };
        } else if (chartType === "grouped_bar") {
          option = {
            tooltip: {
              trigger: "axis",
              axisPointer: { type: "shadow" },
              formatter: params => {
                let res = `<strong>${params[0].axisValue}</strong><br/>`;
                params.forEach(p => {
                  const sIdx = p.seriesIndex;
                  const dIdx = p.dataIndex;
                  const errRange = cData.series[sIdx] && cData.series[sIdx].error_range ? cData.series[sIdx].error_range[dIdx] : null;
                  const errStr = errRange ? ` (T=32: ${errRange[0]}%, T=28: ${errRange[1]}%)` : "";
                  res += `${p.marker} ${p.seriesName}: ${p.value.toFixed(1)}%${errStr}<br/>`;
                });
                return res;
              },
            },
            legend: legendOpt,
            xAxis: xAxisOpt,
            yAxis: yAxisOpt,
            series: seriesFor(cData.series),
            grid: gridOpt,
          };
        } else if (chartType === "sankey") {
          option = {
            tooltip: { trigger: "item", triggerOn: "mousemove" },
            series: cData.series,
          };
        }

        if (Object.keys(option).length > 0) {
          ch.setOption(option, true);
        }
        ch.resize();
      });
    }, 60);
  }

  let currentDiffField = "Chemistry";
  let currentDiffCond = "condition_a";

  function initDiffusionCard(item) {
    const el = document.getElementById("chart-insight-11_information_diffusion");
    if (!el || !item || !item.fields_data) return;

    if (!insightCharts["11_information_diffusion"]) {
      insightCharts["11_information_diffusion"] = echarts.init(el);
    }

    function updateDiffusionView() {
      const fData = item.fields_data[currentDiffField];
      if (!fData) return;
      const condData = fData[currentDiffCond];
      if (!condData) return;

      const hlEl = document.getElementById("diff-headline");
      if (hlEl) {
        if (currentDiffCond === "condition_a") {
          const finalReach = condData.adoption_curve[condData.adoption_curve.length - 1];
          const finalSpill = condData.spillover_curve[condData.spillover_curve.length - 1];
          if (finalReach >= 50.0) {
            hlEl.innerHTML = formatHeadline(
              `In <strong>${esc(fData.field)}</strong>, topic-modulated diffusion achieves majority community adoption (reaching <strong>${finalReach}%</strong> of the field) with near-zero cross-disciplinary spillover (<strong>${finalSpill}%</strong> into other fields). Theoretical epidemic threshold is βc = <strong>${fData.thresholds.beta_c}</strong>.`
            );
          } else {
            hlEl.innerHTML = formatHeadline(
              `In <strong>${esc(fData.field)}</strong>, cognitive boundaries restrict topic-modulated diffusion to specialized research clusters (reaching <strong>${finalReach}%</strong> of the field) with near-zero cross-disciplinary spillover (<strong>${finalSpill}%</strong> into other fields). Theoretical epidemic threshold is βc = <strong>${fData.thresholds.beta_c}</strong>.`
            );
          }
        } else {
          hlEl.innerHTML = formatHeadline(
            `In the isolated <strong>${esc(fData.field)}</strong> domain subgraph (${fData.subgraph_lcc_size.toLocaleString()} nodes), uniform transmission reaches 50% adoption in <strong>${condData.mean_t50}</strong> steps. Theoretical epidemic threshold is βc = <strong>${fData.thresholds.beta_c}</strong>.`
          );
        }
      }

      const kpiBetaEl = document.getElementById("diff-kpi-betac");
      const kpiSpecEl = document.getElementById("diff-kpi-spectral");
      const kpiT50El = document.getElementById("diff-kpi-t50");
      const kpiNodesEl = document.getElementById("diff-kpi-nodes");

      if (kpiBetaEl) kpiBetaEl.textContent = `βc = ${fData.thresholds.beta_c}`;
      if (kpiSpecEl) kpiSpecEl.innerHTML = `Spectral: <strong>${fData.thresholds.beta_c_spec}</strong> | &lt;k&gt; = <strong>${fData.thresholds.k_mean}</strong>`;
      if (kpiT50El) {
        if (currentDiffCond === "condition_a") {
          const finalReach = condData.adoption_curve[condData.adoption_curve.length - 1];
          kpiT50El.textContent = condData.mean_t50 < 15.0 ? `T50 = ${condData.mean_t50} steps` : `Reach = ${finalReach}% (T50 > 15)`;
        } else {
          kpiT50El.textContent = `T50 = ${condData.mean_t50} steps`;
        }
      }
      if (kpiNodesEl) kpiNodesEl.textContent = `LCC Nodes: ${fData.subgraph_lcc_size.toLocaleString()} (${fData.subgraph_edges.toLocaleString()} edges)`;

      const tbodyEl = document.getElementById("tbody-diff-spreaders");
      const tableTitleEl = document.getElementById("diff-table-title");
      if (tableTitleEl) {
        tableTitleEl.textContent = currentDiffCond === "condition_a"
          ? `Top 5 Super-Spreaders (Full Net)`
          : `Top 5 Super-Spreaders (Domain Subgraph)`;
      }

      if (tbodyEl && condData.top_super_spreaders) {
        tbodyEl.innerHTML = condData.top_super_spreaders.map((sp, idx) => {
          const labColor = sp.lab === "CSIR-IICT" ? "#2b5c8f" : sp.lab === "CSIR-NCL" ? "#2e7d32" : "#d95f02";
          return `
            <tr>
              <td style="font-weight:700; color:#64748b; padding:0.4rem 0.6rem;">${idx + 1}</td>
              <td style="font-weight:600; color:#1e293b; padding:0.4rem 0.6rem; max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${esc(sp.name)}">
                ${esc(sp.name)}
              </td>
              <td style="padding:0.4rem 0.6rem;">
                <span class="net-badge-lab" style="background:${labColor}; font-size:0.7rem; padding:0.15rem 0.4rem;">${esc(sp.lab)}</span>
              </td>
              <td style="font-weight:600; color:#475569; padding:0.4rem 0.6rem;">${sp.field_share}%</td>
              <td style="font-weight:700; color:#2563eb; padding:0.4rem 0.6rem;">${(sp.reach_t3 * 100).toFixed(1)}%</td>
            </tr>
          `;
        }).join("");
      }

      const ch = insightCharts["11_information_diffusion"];
      const chartSteps = Array.from({ length: 16 }, (_, i) => String(i));
      let series = [];
      let legendData = [];

      if (currentDiffCond === "condition_a") {
        legendData = ["In-Field Adoption", "Cross-Field Spillover", "50% Adoption Line"];
        series = [
          {
            name: "In-Field Adoption",
            type: "line",
            data: fData.condition_a.adoption_curve,
            smooth: true,
            itemStyle: { color: "#2563eb" },
            lineStyle: { width: 3 },
          },
          {
            name: "Cross-Field Spillover",
            type: "line",
            data: fData.condition_a.spillover_curve,
            smooth: true,
            itemStyle: { color: "#f59e0b" },
            lineStyle: { width: 2.5, type: "dotted" },
          },
          {
            name: "50% Adoption Line",
            type: "line",
            data: Array(chartSteps.length).fill(50),
            itemStyle: { color: "#dc2626" },
            lineStyle: { width: 1.5, type: "dashed" },
          },
        ];
      } else {
        legendData = ["Domain Subgraph Adoption", "50% Adoption Line"];
        series = [
          {
            name: "Domain Subgraph Adoption",
            type: "line",
            data: fData.condition_b.adoption_curve,
            smooth: true,
            itemStyle: { color: "#16a34a" },
            lineStyle: { width: 3 },
          },
          {
            name: "50% Adoption Line",
            type: "line",
            data: Array(chartSteps.length).fill(50),
            itemStyle: { color: "#dc2626" },
            lineStyle: { width: 1.5, type: "dashed" },
          },
        ];
      }

      ch.setOption({
        tooltip: {
          trigger: "axis",
          formatter: p => {
            let s = `<strong>Step ${p[0].axisValue}</strong><br/>`;
            p.forEach(x => { s += `${x.marker} ${x.seriesName}: <strong>${x.value.toFixed(1)}%</strong><br/>`; });
            return s;
          },
        },
        legend: { data: legendData, top: "bottom", textStyle: { fontSize: 11, color: "#475569" } },
        xAxis: { type: "category", name: "Diffusion Step (t)", data: chartSteps, nameLocation: "middle", nameGap: 28, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
        yAxis: { type: "value", name: "% Adoption I(t)", min: 0, max: 100, nameLocation: "middle", nameGap: 48, splitLine: { lineStyle: { type: "dashed", opacity: 0.25 } } },
        series: series,
        grid: { left: 65, right: 25, top: 20, bottom: 65 },
      }, true);
      ch.resize();
    }

    const fBtns = document.querySelectorAll("#diff-field-selector button");
    fBtns.forEach(btn => {
      btn.onclick = () => {
        fBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentDiffField = btn.getAttribute("data-field");
        updateDiffusionView();
      };
    });

    const cBtns = document.querySelectorAll("#diff-cond-selector button");
    cBtns.forEach(btn => {
      btn.onclick = () => {
        cBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentDiffCond = btn.getAttribute("data-cond");
        updateDiffusionView();
      };
    });

    updateDiffusionView();
  }


  // Window resize handler
  window.addEventListener("resize", () => {
    Object.values(charts).forEach(c => c && c.resize && c.resize());
    Object.values(insightCharts).forEach(c => c && c.resize && c.resize());
    if (facultyTable) facultyTable.redraw(true);
    if (topPapersTable) topPapersTable.redraw(true);
  });

  // Initial draw
  updateDashboard();
});
