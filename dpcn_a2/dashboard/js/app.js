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
    renderFacultyPanels();
    renderVenuesPanels();
    renderResearchAreasCharts();
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

  // 3. Faculty Panels
  let facultyTable = null;
  function renderFacultyPanels() {
    const bundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];

    // Faculty Directory Table via Tabulator
    const tableEl = document.getElementById("table-faculty");
    if (tableEl && !facultyTable) {
      facultyTable = new Tabulator(tableEl, {
        data: bundle.faculty,
        layout: "fitColumns",
        pagination: "local",
        paginationSize: 15,
        columns: [
          { title: "Name", field: "name", widthGrow: 2 },
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

  // Window resize handler
  window.addEventListener("resize", () => {
    Object.values(charts).forEach(c => c && c.resize && c.resize());
    if (facultyTable) facultyTable.redraw(true);
    if (topPapersTable) topPapersTable.redraw(true);
  });

  // Initial draw
  updateDashboard();
});
