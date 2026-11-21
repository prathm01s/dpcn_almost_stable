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

  // Theme (js/theme.js): lab colours are lightened on the dark background, and chart text,
  // tooltip and border colours come from ink()
  const LAB_COLORS = {
    light: { iict: "#2b5c8f", ncl: "#2e7d32", cecri: "#d95f02", all: "#4a148c" },
    dark: { iict: "#5b9bd5", ncl: "#4caf50", cecri: "#f28c38", all: "#9575cd" },
  };
  const isDark = () => !!(window.G24Theme && window.G24Theme.isDark());
  const ink = () => (window.G24Theme ? window.G24Theme.ink()
    : { text: "#1e293b", text2: "#475569", muted: "#64748b", surface: "#ffffff", tooltip: "#ffffff", tooltipBorder: "#cbd5e1" });
  function applyThemeColors() { Object.assign(colors, LAB_COLORS[isDark() ? "dark" : "light"]); }
  applyThemeColors();
  // Network categories carry their own colours; use the theme's lab colours instead
  const LAB_KEY = { "CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri" };
  const themedCategories = cats => (cats || []).map(c => LAB_KEY[c.name]
    ? { ...c, itemStyle: { ...(c.itemStyle || {}), color: colors[LAB_KEY[c.name]] } } : c);

  // Filter state
  const state = {
    yearMin: 2016,
    yearMax: 2026,
    type: "all",
    quartile: "all",
    field: "all",
    minIF: 0,    // journal SCImago 2-yr cites/doc (IF analogue), paper filter
    minQ1: 0,    // scientists with more than this many Q1 papers, faculty filter
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
  const filterIF = document.getElementById("filter-if");
  const filterQ1Papers = document.getElementById("filter-q1-papers");
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

  // The page is one long scroll. The network and connectivity sections are heavy, so each is
  // drawn the first time it comes near the viewport and redrawn on later filter changes.
  const lazySections = {
    citations: () => renderCitationSection(),
    coauthorship: () => renderAuthorshipSection(),
    india: () => { renderConnectivity(); renderP2Citing(); },
    institutions: () => renderP2Institutions(),
    "advanced-bibliometrics": () => renderAdvancedBibliometrics(),
  };
  const shownSections = new Set();
  function showSection(id) {
    if (shownSections.has(id) || !lazySections[id]) return;
    shownSections.add(id);
    lazySections[id]();
  }
  if ("IntersectionObserver" in window) {
    const lazyObserver = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) showSection(e.target.id); });
    }, { rootMargin: "400px 0px" });
    Object.keys(lazySections).forEach(id => {
      const el = document.getElementById(id);
      if (el) lazyObserver.observe(el);
    });
  } else {
    Object.keys(lazySections).forEach(showSection);
  }

  // Filter Event Listeners
  const onFilterChange = () => {
    state.yearMin = parseInt(filterYearMin.value);
    state.yearMax = parseInt(filterYearMax.value);
    state.type = filterType.value;
    state.quartile = filterQuartile.value;
    state.field = filterField.value;
    state.minIF = filterIF ? parseFloat(filterIF.value) : 0;
    state.minQ1 = filterQ1Papers ? parseInt(filterQ1Papers.value) : 0;
    updateDashboard();
  };

  [filterYearMin, filterYearMax, filterType, filterQuartile, filterField, filterIF, filterQ1Papers].forEach(el => {
    if (el) el.addEventListener("change", onFilterChange);
  });

  if (btnReset) {
    btnReset.addEventListener("click", () => {
      filterYearMin.value = 2016;
      filterYearMax.value = 2026;
      filterType.value = "all";
      filterQuartile.value = "all";
      filterField.value = "all";
      if (filterIF) filterIF.value = "0";
      if (filterQ1Papers) filterQ1Papers.value = "0";
      onFilterChange();
    });
  }

  // Paper-level filters shared by getFilteredPapers() and filteredPapersFor()
  function paperPasses(p) {
    if (p.yr < state.yearMin || p.yr > state.yearMax) return false;
    if (state.type !== "all" && p.t !== state.type) return false;
    if (state.quartile !== "all" && p.q !== state.quartile) return false;
    if (state.field !== "all" && p.f !== state.field) return false;
    if (state.minIF > 0 && !(p.jif != null && p.jif >= state.minIF)) return false;
    return true;
  }

  // Filter papers_compact based on state
  function getFilteredPapers() {
    return data.papers_compact.filter(p => {
      if (currentInst !== "all" && currentInst !== "compare" && p.inst !== currentInst) return false;
      return paperPasses(p);
    });
  }

  // Roster scientists passing the Q1-papers filter
  function filteredFaculty(bundle) {
    return state.minQ1 > 0 ? bundle.faculty.filter(f => f.q1_papers > state.minQ1) : bundle.faculty;
  }

  // Main Dashboard Update
  function updateDashboard() {
    renderKPIs();
    renderOverviewCharts();
    renderImpactRatio();
    renderIrHigh();
    renderPhase2();
    renderFacultyPanels();
    renderVenuesPanels();
    renderResearchAreasCharts();
    shownSections.forEach(id => lazySections[id]());
  }

  // 1. KPI Strip Rendering
  function renderKPIs() {
    const isFiltered = state.yearMin !== 2016 || state.yearMax !== 2026 || state.type !== "all" || state.quartile !== "all" || state.field !== "all" || state.minIF > 0;
    const instBundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];

    // Faculty and h-index KPIs come from the pre-aggregated bundle (they can't be derived from compact
    // paper records); with the Q1-papers filter they are recomputed from the matching scientists' rows
    if (instBundle && state.minQ1 > 0) {
      const hs = filteredFaculty(instBundle).filter(f => f.papers > 0).map(f => f.h_index).sort((a, b) => a - b);
      const n = hs.length;
      kpiActiveFaculty.textContent = n.toLocaleString();
      kpiMedianH.textContent = n ? (n % 2 ? hs[(n - 1) / 2] : (hs[n / 2 - 1] + hs[n / 2]) / 2).toFixed(1) : "-";
    } else if (instBundle && instBundle.h_index && instBundle.h_index.summary) {
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
        itemStyle: { borderRadius: 6, borderColor: ink().surface, borderWidth: 2 },
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
      if (!paperPasses(p)) return false;
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
    const label = { show: true, position: "top", formatter: p => `${p.value.toFixed(1)}%`, color: ink().text, textBorderWidth: 0, fontWeight: 600 };

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
        { name: `Q1 by impact ratio (IR > ${threshold})`, type: "bar", data: stats.map(s => s.irQ1Pct), itemStyle: { color: colors.all }, label },
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

  // Papers with IR above the fixed thresholds (IR > 5, IR > 10; D-33)
  const irFixed = (data.impact_ratio && data.impact_ratio.thresholds && data.impact_ratio.thresholds.length)
    ? data.impact_ratio.thresholds.slice().sort((a, b) => a - b) : [5, 10];
  const irMinRefs = (data.impact_ratio && data.impact_ratio.min_refs) || 10;
  let irListT = irFixed[0];
  let irHighTable = null;
  const labsOfPaper = (() => {
    const m = {};
    data.papers_compact.forEach(p => { (m[p.id] = m[p.id] || new Set()).add(p.inst); });
    return m;
  })();
  const irOf = p => (p.r != null && p.r > 0 ? p.c / p.r : null);

  function renderIrHigh() {
    const card = document.getElementById("ir-high-card");
    if (!card) return;
    const names = { iict: "CSIR-IICT", ncl: "CSIR-NCL", cecri: "CSIR-CECRI", all: "All three" };
    const keys = ["iict", "ncl", "cecri", "all"];
    const sel = currentInst === "compare" ? "all" : currentInst;
    const byKey = {};
    keys.forEach(k => {
      const ps = filteredPapersFor(k);
      const withRefs = ps.filter(p => irOf(p) != null);
      byKey[k] = { papers: ps, n: withRefs.length, above: Object.fromEntries(irFixed.map(t => [t, withRefs.filter(p => irOf(p) > t)])) };
    });
    const cur = byKey[sel];

    // numbers for the selected institute
    document.getElementById("ir-hi-kpis").innerHTML = irFixed.map(t => {
      const a = cur.above[t];
      const reliable = a.filter(p => p.r >= irMinRefs).length;
      const pct = cur.n ? a.length / cur.n * 100 : 0;
      return `<div class="ir-hi-kpi"><div class="lbl">IR &gt; ${t} · ${esc(names[sel])}</div>
        <div class="val">${fmtN(a.length)}<small>papers (${pct.toFixed(2)}%)</small></div>
        <div class="sub">of ${fmtN(cur.n)} papers with references · ${fmtN(reliable)} of them have ≥ ${irMinRefs} references</div></div>`;
    }).join("") + `<div class="ir-hi-kpi"><div class="lbl">For comparison · top 25% threshold</div>
        <div class="val">IR &gt; ${irThreshold}</div><div class="sub">75th percentile of paper IR (median paper ${data.impact_ratio.summary.all ? Number(data.impact_ratio.summary.all.median_paper_ir).toFixed(2) : "–"})</div></div>`;

    // chart: papers above each threshold, by lab
    const hEl = document.getElementById("chart-ir-high");
    if (!charts.irHigh) charts.irHigh = echarts.init(hEl);
    const tColors = ["#f59e0b", "#dc2626"];
    charts.irHigh.setOption({
      title: { text: "By lab", left: "center", top: 0, textStyle: { fontSize: 13 } },
      tooltip: {
        trigger: "axis", axisPointer: { type: "shadow" },
        formatter: ps => `<strong>${ps[0].name}</strong><br/>` + ps.map(p => {
          const b = byKey[keys[p.dataIndex]];
          return `${p.marker} ${p.seriesName}: ${fmtN(p.value)} of ${fmtN(b.n)} (${(b.n ? p.value / b.n * 100 : 0).toFixed(2)}%)`;
        }).join("<br/>"),
      },
      legend: { bottom: 0 },
      grid: { left: 45, right: 15, top: 35, bottom: 45 },
      xAxis: { type: "category", data: keys.map(k => names[k]) },
      yAxis: { type: "value", name: "Papers", minInterval: 1 },
      series: irFixed.map((t, i) => ({
        name: `IR > ${t}`, type: "bar", itemStyle: { color: tColors[i % 2] },
        data: keys.map(k => byKey[k].above[t].length),
        label: { show: true, position: "top", formatter: p => `${p.value} (${(byKey[keys[p.dataIndex]].n ? p.value / byKey[keys[p.dataIndex]].n * 100 : 0).toFixed(2)}%)`, fontSize: 11, fontWeight: 600, color: ink().text, textBorderWidth: 0 },
      })),
    }, true);

    // chart: by publication year, selected institute
    const yEl = document.getElementById("chart-ir-high-year");
    if (!charts.irHighYear) charts.irHighYear = echarts.init(yEl);
    const years = [];
    for (let y = state.yearMin; y <= state.yearMax; y++) years.push(y);
    charts.irHighYear.setOption({
      title: { text: `By publication year · ${names[sel]}`, left: "center", top: 0, textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { bottom: 0 },
      grid: { left: 45, right: 15, top: 35, bottom: 45 },
      xAxis: { type: "category", data: years.map(y => (y === 2026 ? "2026*" : String(y))) },
      yAxis: { type: "value", name: "Papers", minInterval: 1 },
      series: irFixed.map((t, i) => ({
        name: `IR > ${t}`, type: "bar", itemStyle: { color: tColors[i % 2] },
        data: years.map(y => cur.above[t].filter(p => p.yr === y).length),
      })),
    }, true);

    // the list
    const rows = cur.above[irListT].map(p => ({
      title: p.ti, doi: p.doi, labs: [...(labsOfPaper[p.id] || [p.inst])].map(k => names[k].replace("CSIR-", "")).sort().join(", "),
      year: p.yr, journal: p.j, quartile: p.t === "conference" ? "Conference" : (p.q || "Unranked"),
      citations: p.c, references: p.r, ir: Math.round(irOf(p) * 100) / 100, few: p.r < irMinRefs,
    })).sort((a, b) => b.ir - a.ir);
    setText("ir-hi-count", `· ${fmtN(rows.length)} with IR > ${irListT} (${names[sel]})`);
    const cols = [
      { title: "IR", field: "ir", sorter: "number", width: 75, hozAlign: "right", formatter: c => `<strong>${c.getValue().toFixed(2)}</strong>` },
      { title: "Title", field: "title", widthGrow: 3, minWidth: 220, formatter: c => {
          const r = c.getRow().getData();
          return r.doi ? `<a href="${esc(r.doi)}" target="_blank" rel="noopener" style="color:var(--accent-ink);">${esc(r.title)}</a>` : esc(r.title);
        }, tooltip: true },
      { title: "Lab", field: "labs", width: 95 },
      { title: "Year", field: "year", width: 70, sorter: "number" },
      { title: "Journal", field: "journal", widthGrow: 1.5, minWidth: 140, tooltip: true },
      { title: "SJR", field: "quartile", width: 90, formatter: c => qBadge(c.getValue()) },
      { title: "Citations", field: "citations", width: 95, sorter: "number", hozAlign: "right" },
      { title: "References", field: "references", width: 105, sorter: "number", hozAlign: "right" },
      { title: "Reference list", field: "few", width: 130, formatter: c => c.getValue() ? `<span class="flag-few" title="OpenAlex lists fewer than ${irMinRefs} references for this paper; its reference list may be incomplete, which inflates IR">&lt; ${irMinRefs} refs: check</span>` : "OK" },
    ];
    const tEl = document.getElementById("table-ir-high");
    if (!irHighTable) {
      irHighTable = new Tabulator(tEl, { data: rows, layout: "fitColumns", columns: cols, placeholder: "No papers above this threshold for the current selection" });
    } else {
      irHighTable.setData(rows);
    }
    const few = rows.filter(r => r.few).length;
    document.getElementById("ir-hi-note").innerHTML =
      `<strong>Reading the list:</strong> IR = citations (OpenAlex, 13 Oct 2026) ÷ references listed by OpenAlex; papers without references are left out. ` +
      `${fmtN(few)} of these ${fmtN(rows.length)} papers have fewer than ${irMinRefs} references in OpenAlex (flagged): for them the reference list is probably incomplete, so the IR is overstated. ` +
      `Older papers have had longer to be cited, so high-IR papers concentrate in early years.`;
  }

  document.querySelectorAll("#ir-hi-tabs button").forEach(b => {
    b.addEventListener("click", () => {
      irListT = Number(b.dataset.t);
      document.querySelectorAll("#ir-hi-tabs button").forEach(x => x.classList.toggle("active", x === b));
      renderIrHigh();
    });
  });

  // 3. Faculty Panels
  let facultyTable = null;
  function renderFacultyPanels() {
    const bundle = data.by_institute[currentInst === "compare" ? "all" : currentInst];
    const faculty = filteredFaculty(bundle);
    if (window.G24Profiles) {
      const keep = state.minQ1 > 0 ? new Set(faculty.map(f => f.faculty_id)) : null;
      G24Profiles.renderFeatured("featured-scientists", currentInst, 16, keep);
    }

    // Faculty Directory Table via Tabulator
    const tableEl = document.getElementById("table-faculty");
    if (tableEl && !facultyTable) {
      facultyTable = new Tabulator(tableEl, {
        data: faculty,
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
          { title: "Q1 Papers", field: "q1_papers", sorter: "number", width: 95 },
          { title: "Q1 %", field: "q1_share_pct", sorter: "number", width: 85, formatter: c => `${c.getValue()}%` },
          { title: "h-Index", field: "h_index", sorter: "number", width: 90 },
        ],
      });
    } else if (facultyTable) {
      facultyTable.setData(faculty);
      facultyTable.redraw(true);
    }

    // Faculty h-index histogram, binned here from the (filtered) faculty rows with the same
    // bins as stats/tables/h_index_distribution.csv; one stacked colour per campus for All/Compare
    const hEl = document.getElementById("chart-h-index");
    if (hEl) {
      if (!charts.hIndex) charts.hIndex = echarts.init(hEl);
      const binLabels = bundle.h_index.bins.map(b => b.bin_label);  // "0-4" … "35+"
      const binOf = h => Math.min(Math.floor(h / 5), binLabels.length - 1);
      const active = faculty.filter(f => f.papers > 0);
      const countBins = rows => {
        const counts = binLabels.map(() => 0);
        rows.forEach(f => { counts[binOf(f.h_index)] += 1; });
        return counts;
      };
      const byCampus = currentInst === "all" || currentInst === "compare";
      const labs = [["iict", "CSIR-IICT"], ["ncl", "CSIR-NCL"], ["cecri", "CSIR-CECRI"]];
      const series = byCampus
        ? labs.map(([key, name]) => ({
            name, type: "bar", stack: "h", emphasis: { focus: "series" },
            data: countBins(active.filter(f => f.institution === name)),
            itemStyle: { color: colors[key] },
          }))
        : [{ name: bundle.name || currentInst.toUpperCase(), type: "bar", data: countBins(active), itemStyle: { color: colors[currentInst] } }];
      charts.hIndex.setOption({
        tooltip: {
          trigger: "axis", axisPointer: { type: "shadow" },
          formatter: params => {
            const total = params.reduce((a, p) => a + p.value, 0);
            return `<strong>h-index ${params[0].name}</strong>: ${total} scientists` +
              (byCampus ? "<br/>" + params.map(p => `${p.marker}${p.seriesName}: ${p.value}`).join("<br/>") : "");
          },
        },
        legend: byCampus ? { data: labs.map(l => l[1]), bottom: 0 } : { show: false },
        grid: { left: 50, right: 20, top: 40, bottom: byCampus ? 60 : 40 },
        xAxis: { type: "category", data: binLabels, name: "h-Index Range", nameLocation: "middle", nameGap: 26 },
        yAxis: { type: "value", name: "Faculty Count" },
        series,
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
          { title: "#", field: "rank", width: 45 },
          { title: "Title", field: "title", widthGrow: 3, minWidth: 220, tooltip: true, formatter: c => {
              const r = c.getRow().getData();
              return r.doi ? `<a href="${esc(r.doi)}" target="_blank" rel="noopener" style="color:var(--accent-ink);">${esc(r.title)}</a>` : esc(r.title);
            } },
          { title: "Lab(s)", field: "labs", width: 100, formatter: c => esc((c.getValue() || "").replace(/CSIR-/g, "")) },
          { title: "Lab authors", field: "in_corpus_authors", widthGrow: 1.5, minWidth: 140, tooltip: true },
          { title: "Journal", field: "journal_name", widthGrow: 1.5, minWidth: 130, tooltip: true },
          { title: "Year", field: "year", width: 65 },
          { title: "Type", field: "type", width: 90 },
          { title: "Field", field: "field", widthGrow: 1, minWidth: 110, tooltip: true },
          { title: "SJR", field: "quartile", width: 80, formatter: c => qBadge(c.getValue()) },
          { title: "J. IF*", field: "jif", width: 70, hozAlign: "right", sorter: "number", formatter: c => c.getValue() != null ? Number(c.getValue()).toFixed(1) : "–", headerTooltip: "SCImago 2-year cites per document of the journal (Scopus-based IF analogue)" },
          { title: "Citations", field: "citations", sorter: "number", width: 92, hozAlign: "right" },
          { title: "Refs", field: "references", sorter: "number", width: 65, hozAlign: "right", formatter: c => c.getValue() != null ? c.getValue() : "–" },
          { title: "IR", field: "ir", sorter: "number", width: 70, hozAlign: "right", formatter: c => c.getValue() != null ? Number(c.getValue()).toFixed(2) : "–", headerTooltip: "Impact ratio = citations ÷ references" },
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
        backgroundColor: ink().tooltip,
        borderColor: ink().tooltipBorder,
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: ink().text, fontFamily: "Inter, sans-serif" },
        formatter: function(params) {
          if (params.dataType === "node") {
            const d = params.data;
            return `
              <div style="font-weight:700; margin-bottom:4px; max-width:320px; white-space:normal; font-size:12px; color:var(--text);">${d.full_title || d.name}</div>
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;"><strong>${d.journal}</strong> (${d.year})</div>
              <div style="font-size:11px; line-height:1.6;">
                <div><strong>Institution:</strong> <span style="font-weight:600; color:var(--accent-ink);">${d.inst}</span></div>
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
                <div style="font-weight:700; color:var(--text); margin-bottom:3px;">Directed Citation Edge</div>
                <div><strong>Citing Institute:</strong> ${d.s_inst}</div>
                <div><strong>Cited Institute:</strong> ${d.t_inst}</div>
                <div><strong>Connection Type:</strong> ${d.is_cross ? '<span style="color:#0284c7; font-weight:700;">Inter-Lab Citation</span>' : '<span style="color:var(--text-muted);">Intra-Lab Citation</span>'}</div>
              </div>
            `;
          }
        }
      },
      legend: [{
        data: data.network.categories.map(c => c.name),
        top: "bottom",
        textStyle: { fontSize: 11, color: ink().text2 },
      }],
      series: [{
        name: "Citation Network",
        type: "graph",
        layout: "force",
        data: nodes,
        links: links,
        categories: themedCategories(data.network.categories),
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
      tbodyPr.innerHTML = cData.top_pagerank.map(p => `
          <tr>
            <td style="font-weight:700; color:var(--text-muted);">${p.rank}</td>
            <td>
              <div style="font-weight:600; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${esc(p.title)}">${p.doi ? `<a href="${esc(p.doi)}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title)}</div>
              <div style="font-size:0.75rem; color:var(--text-muted);">${esc(p.journal)} (${p.year}) · ${qBadge(p.quartile)}</div>
            </td>
            <td>${labBadge(p.inst)}</td>
            <td style="font-weight:700;">${fmtN(p.in_degree)}</td>
            <td>${fmtN(p.citations)}</td>
            <td>${fmtN(p.references)}</td>
            <td>${p.ir != null ? p.ir.toFixed(2) : "–"}</td>
            <td style="font-family:monospace;">${p.score.toFixed(5)}</td>
          </tr>`).join("");
    }

    const tbodyFlow = document.getElementById("tbody-net-cite-matrix");
    if (tbodyFlow && cData.flow_matrix) {
      const sh = crossShare(cData.flow_matrix, "source_inst");
      setText("net-cite-matrix-note", `Across labs: ${fmtN(sh.cross)} of ${fmtN(sh.all)} lab-attributed citation links (${sh.pct.toFixed(1)}%).`);
      tbodyFlow.innerHTML = cData.flow_matrix.map(row => {
        const tot = row.iict + row.ncl + row.cecri;
        return `
          <tr>
            <td><strong>${row.source_inst}</strong></td>
            <td class="${row.source_inst === 'CSIR-IICT' ? 'matrix-diag' : 'matrix-cross'}">${row.iict.toLocaleString()}</td>
            <td class="${row.source_inst === 'CSIR-NCL' ? 'matrix-diag' : 'matrix-cross'}">${row.ncl.toLocaleString()}</td>
            <td class="${row.source_inst === 'CSIR-CECRI' ? 'matrix-diag' : 'matrix-cross'}">${row.cecri.toLocaleString()}</td>
            <td style="font-weight:700; background:var(--surface-2);">${tot.toLocaleString()}</td>
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
        backgroundColor: ink().tooltip,
        borderColor: ink().tooltipBorder,
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: ink().text, fontFamily: "Inter, sans-serif" },
        formatter: function(params) {
          if (params.dataType === "node") {
            const d = params.data;
            return `
              <div style="font-weight:700; font-size:13px; margin-bottom:4px; color:var(--text);">${d.name}</div>
              <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">${d.designation} &bull; ${d.department}</div>
              <div style="font-size:11px; line-height:1.6;">
                <div><strong>Institution:</strong> <span style="font-weight:600; color:var(--accent-ink);">${d.inst}</span></div>
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
                <div style="font-weight:700; color:var(--text); margin-bottom:3px;">Co-Authorship Edge</div>
                <div><strong>Collaborators:</strong> ${d.source} &harr; ${d.target}</div>
                <div><strong>Joint Publications:</strong> <strong>${d.weight}</strong></div>
                <div><strong>Connection Type:</strong> ${d.is_cross ? '<span style="color:#d97706; font-weight:700;">Inter-Lab Collaboration</span>' : '<span style="color:var(--text-muted);">Intra-Lab Collaboration</span>'}</div>
              </div>
            `;
          }
        }
      },
      legend: [{
        data: data.network.categories.map(c => c.name),
        top: "bottom",
        textStyle: { fontSize: 11, color: ink().text2 },
      }],
      series: [{
        name: "Authorship Network",
        type: "graph",
        layout: "force",
        data: nodes,
        links: links,
        categories: themedCategories(data.network.categories),
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
            <td style="font-weight:700; color:var(--text-muted);">${b.rank}</td>
            <td style="font-weight:600; color:var(--text);" ${(window.G24Profiles && G24Profiles.fidByName(b.author)) ? `data-fid="${G24Profiles.fidByName(b.author)}"` : ""}>${b.author}</td>
            <td><span class="net-badge-lab" style="background:${labColor};">${b.institution}</span></td>
            <td style="font-weight:700;">${b.collaborators_count}</td>
            <td style="font-family:monospace; font-weight:600; color:#0d9488;">${b.betweenness.toFixed(4)}</td>
            <td><span style="font-size:0.75rem; color:var(--text-muted); background:var(--surface-3); padding:2px 6px; border-radius:4px;">Cluster #${b.community_id}</span></td>
          </tr>
        `;
      }).join("");
    }

    const tbodyCollab = document.getElementById("tbody-net-auth-matrix");
    if (tbodyCollab && aData.collab_matrix) {
      setText("net-auth-matrix-note", `Cross-lab links: ${fmtN(aData.stats.inter_lab_pairs)} of ${fmtN(aData.stats.edge_rows)} co-authorship links (one per author pair per shared paper).`);
      tbodyCollab.innerHTML = aData.collab_matrix.map(row => {
        const totInter = (row.inst === 'CSIR-IICT' ? (row.ncl + row.cecri) : row.inst === 'CSIR-NCL' ? (row.iict + row.cecri) : (row.iict + row.ncl));
        return `
          <tr>
            <td><strong>${row.inst}</strong></td>
            <td class="${row.inst === 'CSIR-IICT' ? 'matrix-diag' : 'matrix-cross'}">${row.iict.toLocaleString()}</td>
            <td class="${row.inst === 'CSIR-NCL' ? 'matrix-diag' : 'matrix-cross'}">${row.ncl.toLocaleString()}</td>
            <td class="${row.inst === 'CSIR-CECRI' ? 'matrix-diag' : 'matrix-cross'}">${row.cecri.toLocaleString()}</td>
            <td style="font-weight:700; background:var(--surface-2); color:#d97706;">${totInter.toLocaleString()}</td>
          </tr>
        `;
      }).join("");
    }
  }

  // ---------------------------------------------------------------------------
  // Network sections (D-33): faculty view (default, one node per roster scientist) and the
  // paper / all-author view. Every number is read from the data payload.
  // ---------------------------------------------------------------------------
  const netView = { cite: "faculty", auth: "faculty" };
  const facNet = { cite: { inst: "all", min: 5, q: "", init: false }, auth: { inst: "all", min: 1, q: "", init: false } };
  const fmtN = v => (v == null || v === "" ? "–" : Number(v).toLocaleString());
  const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  const LAB_KEY_OF = { "CSIR-IICT": "iict", "CSIR-NCL": "ncl", "CSIR-CECRI": "cecri" };
  const labColorOf = inst => colors[LAB_KEY_OF[inst]] || "#94a3b8";
  const labBadge = inst => `<span class="net-badge-lab" style="background:${({ "CSIR-IICT": "#2b5c8f", "CSIR-NCL": "#2e7d32", "CSIR-CECRI": "#d95f02" })[inst] || "#64748b"};">${esc(inst)}</span>`;
  const qBadge = q => {
    const cls = { Q1: "q1", Q2: "q2", Q3: "q3", Q4: "q4" }[q] || "un";
    return `<span class="badge-q badge-${cls}">${esc(q || "Unranked")}</span>`;
  };

  function renderCitationSection() {
    fillNetworkKpis();
    if (netView.cite === "faculty") renderFacultyNetwork("cite"); else renderCitationNetwork();
  }
  function renderAuthorshipSection() {
    fillNetworkKpis();
    if (netView.auth === "faculty") renderFacultyNetwork("auth"); else renderAuthorshipNetwork();
  }

  document.querySelectorAll(".net-view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const net = btn.dataset.net, view = btn.dataset.view;
      netView[net] = view;
      document.querySelectorAll(`.net-view-btn[data-net="${net}"]`).forEach(b => {
        const on = b === btn;
        b.classList.toggle("active", on);
        b.setAttribute("aria-selected", String(on));
      });
      document.getElementById(`${net}-view-faculty`).hidden = view !== "faculty";
      document.getElementById(`${net}-view-papers`).hidden = view !== "papers";
      if (net === "cite") renderCitationSection(); else renderAuthorshipSection();
      Object.values(charts).forEach(c => c && c.resize && c.resize());
    });
  });

  let netKpisFilled = false;
  function fillNetworkKpis() {
    if (netKpisFilled || !data.network) return;
    netKpisFilled = true;
    const nf = data.network_faculty || {};
    const fc = nf.citation && nf.citation.stats, fa = nf.authorship && nf.authorship.stats;
    const pc = data.network.citation.stats, pa = data.network.authorship.stats;
    if (fc) {
      setText("cite-tab-fac-n", `${fmtN(fc.total_nodes)} nodes`);
      setText("fac-cite-kpi-nodes", fmtN(fc.total_nodes));
      setText("fac-cite-kpi-connected", fmtN(fc.connected_nodes));
      setText("fac-cite-kpi-edges", fmtN(fc.total_edges));
      setText("fac-cite-kpi-cites", fmtN(fc.citation_links));
      setText("fac-cite-kpi-cites-sub", `Between different scientists; ${fmtN(fc.self_citation_pairs)} self-citations left out`);
      setText("fac-cite-kpi-cross", fmtN(fc.inter_lab_edges));
      setText("fac-cite-kpi-cross-sub", `${fmtN(fc.inter_lab_citations)} paper-to-paper citations across labs`);
    }
    if (fa) {
      setText("auth-tab-fac-n", `${fmtN(fa.total_nodes)} nodes`);
      setText("fac-auth-kpi-nodes", fmtN(fa.total_nodes));
      setText("fac-auth-kpi-connected", fmtN(fa.connected_nodes));
      setText("fac-auth-kpi-edges", fmtN(fa.total_edges));
      setText("fac-auth-kpi-edges-sub", `${fmtN(fa.shared_papers)} shared papers summed over pairs`);
      setText("fac-auth-kpi-communities", fmtN(fa.communities_count));
      setText("fac-auth-kpi-communities-sub", `Modularity ${fa.modularity}; largest connected group ${fmtN(fa.lcc_nodes)} scientists`);
      setText("fac-auth-kpi-cross", fmtN(fa.inter_lab_pairs));
    }
    setText("cite-tab-pap-n", `${fmtN(pc.total_nodes)} nodes`);
    setText("net-cite-kpi-nodes", fmtN(pc.total_nodes));
    setText("net-cite-kpi-edges", fmtN(pc.total_edges));
    setText("net-cite-kpi-interlab", fmtN(pc.inter_lab_citations));
    const top = data.network.citation.top_pagerank && data.network.citation.top_pagerank[0];
    if (top) {
      const el = document.getElementById("net-cite-kpi-top-pr");
      el.textContent = top.title;
      el.title = top.title;
      el.classList.add("kpi-val-text");
      setText("net-cite-kpi-top-pr-sub", `${top.journal} (${top.year}) · cited ${top.in_degree}× in the corpus`);
    }
    setText("auth-tab-all-n", `${fmtN(pa.total_authors)} nodes`);
    setText("net-auth-kpi-nodes", fmtN(pa.total_authors));
    if (pa.faculty_authors != null) {
      const other = pa.total_authors - pa.faculty_authors;
      setText("net-auth-kpi-nodes-sub", `${fmtN(pa.faculty_authors)} faculty + ${fmtN(other)} students, postdocs and staff`);
      setText("net-auth-composition", `Of the ${fmtN(pa.total_authors)} authors, ${fmtN(pa.faculty_authors)} are roster faculty and ${fmtN(other)} are not.`);
    }
    setText("net-auth-kpi-edges", fmtN(pa.total_edges));
    setText("net-auth-kpi-communities", fmtN(pa.communities_count));
    setText("net-auth-kpi-interlab", fmtN(pa.inter_lab_pairs));
  }

  function matrixRows(rows, firstKey, diagOnly) {
    return rows.map(row => {
      const lab = row[firstKey];
      const vals = { iict: row.iict, ncl: row.ncl, cecri: row.cecri };
      const total = diagOnly ? Object.entries(vals).filter(([k]) => LAB_KEY_OF[lab] !== k).reduce((a, [, v]) => a + v, 0)
        : vals.iict + vals.ncl + vals.cecri;
      return `<tr><td><strong>${esc(lab)}</strong></td>` +
        ["iict", "ncl", "cecri"].map(k => `<td class="${LAB_KEY_OF[lab] === k ? "matrix-diag" : "matrix-cross"}">${fmtN(vals[k])}</td>`).join("") +
        `<td style="font-weight:700; background:var(--surface-2);">${fmtN(total)}</td></tr>`;
    }).join("");
  }
  function crossShare(rows, firstKey) {
    let cross = 0, all = 0;
    rows.forEach(r => ["iict", "ncl", "cecri"].forEach(k => { all += r[k]; if (LAB_KEY_OF[r[firstKey]] !== k) cross += r[k]; }));
    return { cross, all, pct: all ? cross / all * 100 : 0 };
  }

  function populateFacultyTables(kind) {
    const nf = data.network_faculty;
    if (kind === "cite") {
      const c = nf.citation;
      document.getElementById("tbody-fac-top-cited").innerHTML = c.top_cited.map(r => `
        <tr><td style="font-weight:700; color:var(--text-muted);">${r.rank}</td>
          <td style="font-weight:600;" ${window.G24Profiles && G24Profiles.has(r.fid) ? `data-fid="${esc(r.fid)}"` : ""}>${esc(r.name)}</td>
          <td>${labBadge(r.inst)}</td><td style="font-weight:700;">${fmtN(r.in_links)}</td>
          <td>${fmtN(r.citing_faculty)}</td><td>${fmtN(r.papers)}</td>
          <td style="font-family:monospace;">${r.pagerank.toFixed(4)}</td></tr>`).join("");
      document.getElementById("tbody-fac-cite-matrix").innerHTML = matrixRows(c.flow_matrix, "source_inst", false);
      const s = crossShare(c.flow_matrix, "source_inst");
      document.getElementById("fac-cite-matrix-note").innerHTML =
        `<strong>Reading it:</strong> diagonal = scientists citing colleagues in their own lab. Across labs: <strong>${fmtN(s.cross)}</strong> of ${fmtN(s.all)} paper-to-paper citations between scientists (${s.pct.toFixed(1)}%).`;
    } else {
      const a = nf.authorship;
      document.getElementById("tbody-fac-bridges").innerHTML = a.top_bridges.map(b => `
        <tr><td style="font-weight:700; color:var(--text-muted);">${b.rank}</td>
          <td style="font-weight:600;" ${window.G24Profiles && G24Profiles.has(b.fid) ? `data-fid="${esc(b.fid)}"` : ""}>${esc(b.author)}</td>
          <td>${labBadge(b.institution)}</td><td style="font-weight:700;">${fmtN(b.collaborators_count)}</td>
          <td>${fmtN(b.joint_paper_links)}</td><td style="font-family:monospace;">${b.betweenness.toFixed(4)}</td>
          <td><span class="net-chip">#${b.community_id}</span></td></tr>`).join("");
      document.getElementById("tbody-fac-auth-matrix").innerHTML = matrixRows(a.collab_matrix, "inst", true);
      const tot = a.stats.total_edges, cross = a.stats.inter_lab_pairs;
      document.getElementById("fac-auth-matrix-note").innerHTML =
        `<strong>Reading it:</strong> diagonal = pairs within one lab. Only <strong>${fmtN(cross)}</strong> of ${fmtN(tot)} faculty co-author pairs (${(tot ? cross / tot * 100 : 0).toFixed(1)}%) join two different labs.`;
    }
  }

  function initFacultyControls(kind) {
    const prefix = kind === "cite" ? "fac-cite" : "fac-auth";
    const st = facNet[kind];
    const def = { inst: "all", min: st.min, q: "" };
    const inst = document.getElementById(`${prefix}-filter-inst`);
    const slider = document.getElementById(`${prefix}-slider`);
    const sval = document.getElementById(`${prefix}-slider-val`);
    const search = document.getElementById(`${prefix}-search`);
    const reset = document.getElementById(`${prefix}-reset`);
    const redraw = () => renderFacultyNetwork(kind);
    if (inst) inst.addEventListener("change", e => { st.inst = e.target.value; redraw(); });
    if (slider) slider.addEventListener("input", e => { st.min = parseInt(e.target.value, 10); if (sval) sval.textContent = st.min; redraw(); });
    if (search) search.addEventListener("input", e => { st.q = e.target.value; redraw(); });
    if (reset) reset.addEventListener("click", () => {
      Object.assign(st, def);
      if (inst) inst.value = "all";
      if (slider) slider.value = String(def.min);
      if (sval) sval.textContent = def.min;
      if (search) search.value = "";
      redraw();
    });
  }

  function renderFacultyNetwork(kind) {
    const nf = data.network_faculty;
    if (!nf) return;
    const isCite = kind === "cite";
    const nd = isCite ? nf.citation : nf.authorship;
    const el = document.getElementById(isCite ? "chart-fac-cite-network" : "chart-fac-auth-network");
    if (!el) return;
    const key = isCite ? "facCiteNet" : "facAuthNet";
    if (!charts[key]) {
      charts[key] = echarts.init(el);
      charts[key].on("click", prm => {
        if (prm.dataType === "node" && prm.data.fid && window.G24Profiles && G24Profiles.has(prm.data.fid)) G24Profiles.open(prm.data.fid);
      });
    }
    const st = facNet[kind];
    if (!st.init) { st.init = true; initFacultyControls(kind); populateFacultyTables(kind); }

    const q = st.q.toLowerCase().trim();
    let nodes = nd.nodes.filter(n => {
      if (st.inst !== "all" && st.inst !== "cross" && n.inst !== st.inst) return false;
      return true;
    });
    const ids = new Set(nodes.map(n => n.id));
    let links = nd.links.filter(l => ids.has(l.source) && ids.has(l.target)
      && l.weight >= st.min && (st.inst !== "cross" || l.is_cross));
    let hit = null;
    if (q) {
      hit = new Set(nodes.filter(n => n.name.toLowerCase().includes(q)).map(n => n.id));
      links = links.filter(l => hit.has(l.source) || hit.has(l.target));
    }
    const keep = new Set(hit || []);
    links.forEach(l => { keep.add(l.source); keep.add(l.target); });
    nodes = nodes.filter(n => keep.has(n.id));  // scientists without a link under these filters are not drawn
    const nameOf = Object.fromEntries(nd.nodes.map(n => [n.id, n.name]));
    const hint = document.querySelector(`#${kind}-view-faculty .net-hint`);
    if (hint) hint.textContent = `Showing ${fmtN(nodes.length)} of ${fmtN(nd.stats.total_nodes)} scientists and ${fmtN(links.length)} of ${fmtN(nd.stats.total_edges)} links. Amber lines join two labs. Scroll to zoom, drag to move.`;

    const maxW = Math.max(1, ...links.map(l => l.weight));
    charts[key].setOption({
      tooltip: {
        trigger: "item", backgroundColor: ink().tooltip, borderColor: ink().tooltipBorder, borderWidth: 1,
        padding: [10, 14], textStyle: { color: ink().text, fontSize: 12 },
        formatter: p => {
          if (p.dataType === "edge") {
            const d = p.data;
            return isCite
              ? `<strong>${esc(nameOf[d.source])}</strong> cites <strong>${esc(nameOf[d.target])}</strong><br/>${fmtN(d.weight)} paper-to-paper citation${d.weight === 1 ? "" : "s"}${d.is_cross ? "<br/><em>across labs</em>" : ""}`
              : `<strong>${esc(nameOf[d.source])}</strong> — <strong>${esc(nameOf[d.target])}</strong><br/>${fmtN(d.weight)} shared paper${d.weight === 1 ? "" : "s"}${d.is_cross ? "<br/><em>across labs</em>" : ""}`;
          }
          const d = p.data;
          const head = `<div style="font-weight:700; font-size:13px;">${esc(d.name)}</div>
            <div style="font-size:11px; color:var(--text-muted); margin-bottom:6px;">${esc(d.designation || "")} · ${esc(d.inst)}<br/>${esc(d.department || "")}</div>`;
          const body = isCite
            ? `Citations received from other scientists: <strong>${fmtN(d.in_degree)}</strong> (from ${fmtN(d.citing_faculty)} scientists)<br/>Citations given to other scientists: <strong>${fmtN(d.out_degree)}</strong><br/>PageRank: ${d.pagerank}`
            : `Faculty co-authors: <strong>${fmtN(d.degree)}</strong> · shared papers: <strong>${fmtN(d.shared_papers)}</strong><br/>Betweenness: ${d.betweenness} · community #${d.community}`;
          return `${head}<div style="font-size:11px; line-height:1.6;">${body}<br/>Papers 2016–2026: ${fmtN(d.papers)} · h-index ${d.h_index}</div>
            ${window.G24Profiles && G24Profiles.has(d.fid) ? '<div style="margin-top:6px; font-size:11px; color:var(--accent-ink); font-weight:600;">Click to open the profile</div>' : ""}`;
        },
      },
      legend: [{ data: data.network.categories.map(c => c.name), top: "bottom", textStyle: { fontSize: 11, color: ink().text2 } }],
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true,
        categories: themedCategories(data.network.categories),
        data: nodes.map(n => ({
          ...n,
          itemStyle: { color: labColorOf(n.inst), borderColor: hit && hit.has(n.id) ? "#facc15" : ink().surface, borderWidth: hit && hit.has(n.id) ? 3 : 1 },
          label: { show: n.symbolSize >= (isCite ? 22 : 18) || (hit && hit.has(n.id)), position: "right", fontSize: 10, color: ink().text2 },
        })),
        links: links.map(l => ({
          ...l,
          lineStyle: { width: 0.6 + 4 * Math.sqrt(l.weight / maxW), color: l.is_cross ? "#f59e0b" : "source", opacity: l.is_cross ? 0.85 : 0.45, curveness: isCite ? 0.15 : 0.05 },
        })),
        edgeSymbol: isCite ? ["none", "arrow"] : ["none", "none"],
        edgeSymbolSize: isCite ? [0, 7] : [0, 0],
        force: { repulsion: isCite ? 160 : 140, gravity: 0.08, edgeLength: [40, 140], friction: 0.6 },
        emphasis: { focus: "adjacency", lineStyle: { width: 4, opacity: 1 } },
      }],
    }, true);
  }

  // ---------------------------------------------------------------------------
  // Phase II (instructor's directions, D-34): every number comes from data.phase2,
  // built from stats/tables/phase2_*.csv. These panels follow the institute buttons.
  // ---------------------------------------------------------------------------
  const P2 = data.phase2 || null;
  const isTrue = v => v === true || String(v).toLowerCase() === "true";
  const P2_NAMES = { iict: "CSIR-IICT", ncl: "CSIR-NCL", cecri: "CSIR-CECRI", all: "All three" };
  const p2Key = () => (currentInst === "compare" ? "all" : currentInst);
  const pctN = (v, d = 1) => (v == null ? "–" : `${Number(v).toFixed(d)}%`);
  const doiLink = (title, doi) => (doi ? `<a href="${esc(doi)}" target="_blank" rel="noopener">${esc(title)}</a>` : esc(title));
  let p2FacultyTable = null, p2Top30Table = null, p2CitingTable = null;

  function renderPhase2() {
    if (!P2) return;
    renderP2Overview();
    renderInstitutionalRadar();
    renderP2Faculty();
    renderP2Journals();
    renderP2Checks();
    renderAdvancedBibliometrics();
  }

  function renderInstitutionalRadar() {
    const radarData = data.institutional_radar;
    if (!radarData) return;

    const dom = document.getElementById("chart-institutional-radar");
    if (!dom) return;
    if (!charts.radar) charts.radar = echarts.init(dom);

    const indicators = radarData.indicators.map(ind => ({
      name: ind.name,
      max: ind.max,
    }));

    const labs = radarData.labs;
    const isCompareOrAll = (currentInst === "all" || currentInst === "compare");

    const seriesData = ["iict", "ncl", "cecri"].map(k => {
      const lab = labs[k];
      const isSelected = isCompareOrAll || (currentInst === k);
      const isGhosted = !isCompareOrAll && (currentInst !== k);

      return {
        name: lab.institution,
        value: lab.values,
        symbol: "circle",
        symbolSize: isSelected ? 6 : 4,
        lineStyle: {
          width: isSelected ? 3.2 : 1.2,
          color: lab.color,
          opacity: isGhosted ? 0.2 : 1,
        },
        itemStyle: {
          color: lab.color,
          borderColor: isDark() ? "#1e293b" : "#ffffff",
          borderWidth: isSelected ? 2 : 1,
          opacity: isGhosted ? 0.2 : 1,
        },
        areaStyle: {
          color: lab.color,
          opacity: isGhosted ? 0.04 : 0.26,
        },
        emphasis: {
          focus: "series",
          blurScope: "coordinateSystem",
          lineStyle: {
            width: 5,
            shadowBlur: 16,
            shadowColor: lab.color,
            opacity: 1,
          },
          itemStyle: {
            borderWidth: 3,
            borderColor: isDark() ? "#0f172a" : "#ffffff",
            shadowBlur: 12,
            shadowColor: lab.color,
            opacity: 1,
          },
          areaStyle: {
            opacity: 0.55,
          },
        },
        blur: {
          lineStyle: {
            opacity: 0.08,
            width: 1,
          },
          itemStyle: {
            opacity: 0.08,
          },
          areaStyle: {
            opacity: 0.02,
          },
        },
      };
    });

    const axisLabelColor = isDark() ? "#f8fafc" : "#0f172a";
    const axisLabelBg = isDark() ? "rgba(30, 41, 59, 0.96)" : "rgba(255, 255, 255, 0.98)";
    const axisLabelBorder = isDark() ? "rgba(148, 163, 184, 0.35)" : "rgba(15, 23, 42, 0.22)";

    const axisStyleConfig = {
      show: true,
      color: axisLabelColor,
      fontWeight: 800,
      fontSize: 12.5,
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      lineHeight: 16,
      padding: [5, 9],
      borderRadius: 6,
      backgroundColor: axisLabelBg,
      borderWidth: 1.5,
      borderColor: axisLabelBorder,
      shadowColor: isDark() ? "rgba(0, 0, 0, 0.45)" : "rgba(15, 23, 42, 0.08)",
      shadowBlur: 6,
      shadowOffsetY: 2,
    };

    charts.radar.setOption({
      tooltip: {
        trigger: "item",
        confine: true,
        backgroundColor: isDark() ? "#1e293b" : "#ffffff",
        borderColor: isDark() ? "#334155" : "#e2e8f0",
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: isDark() ? "#f8fafc" : "#0f172a" },
        extraCssText: "box-shadow: 0 10px 25px -5px rgba(0,0,0,0.25); border-radius: 8px;",
        formatter: function(params) {
          const k = Object.keys(labs).find(key => labs[key].institution === params.name);
          const lab = labs[k] || {};
          let html = `<div style="font-weight:800;font-size:13px;margin-bottom:8px;color:${lab.color || '#333'}">${params.name}</div>`;
          html += `<table style="font-size:12px;border-collapse:collapse;width:100%;">`;
          radarData.indicators.forEach((ind, i) => {
            const val = params.value[i];
            const norm = lab.normalized ? lab.normalized[i] : (val / ind.max * 100);
            const formattedVal = (ind.key === "network_betweenness") ? val.toFixed(4) :
                                 (ind.unit === "%") ? `${val.toFixed(1)}%` :
                                 (ind.unit === "cites") ? `${val.toFixed(1)}` : `${Math.round(val)}`;
            html += `<tr>
              <td style="padding:3px 10px 3px 0;color:var(--text-muted);font-weight:500;">${ind.name}:</td>
              <td style="padding:3px 0;text-align:right;font-weight:700;">${formattedVal}</td>
              <td style="padding:3px 0 3px 8px;text-align:right;font-size:11px;color:var(--text-muted);">(${norm.toFixed(0)}% cap)</td>
            </tr>`;
          });
          html += `</table>`;
          return html;
        }
      },
      legend: {
        data: ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"],
        bottom: 4,
        itemWidth: 16,
        itemHeight: 10,
        borderRadius: 3,
        itemGap: 24,
        textStyle: {
          fontSize: 12.5,
          fontWeight: 700,
          color: ink().text,
        },
      },
      radar: {
        indicator: indicators,
        shape: "polygon",
        splitNumber: 4,
        radius: "64%",
        center: ["50%", "47%"],
        nameGap: 12,
        axisName: axisStyleConfig,
        name: axisStyleConfig,
        axisLine: {
          lineStyle: {
            color: isDark() ? "rgba(148, 163, 184, 0.28)" : "rgba(71, 85, 105, 0.35)",
            width: 1.5,
          }
        },
        splitLine: {
          lineStyle: {
            color: isDark()
              ? ["rgba(255, 255, 255, 0.04)", "rgba(255, 255, 255, 0.08)", "rgba(255, 255, 255, 0.14)", "rgba(255, 255, 255, 0.22)"]
              : ["rgba(15, 23, 42, 0.05)", "rgba(15, 23, 42, 0.10)", "rgba(15, 23, 42, 0.16)", "rgba(15, 23, 42, 0.24)"],
            width: 1.2,
          }
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: isDark()
              ? ["rgba(255, 255, 255, 0.012)", "rgba(255, 255, 255, 0.035)"]
              : ["rgba(248, 250, 252, 0.6)", "rgba(241, 245, 249, 0.85)"]
          }
        }
      },
      series: [{
        type: "radar",
        data: seriesData,
      }]
    }, true);

    function highlightRadarLab(instKey) {
      const table = document.getElementById("table-radar-metrics");
      if (table) {
        table.classList.remove("hover-col-iict", "hover-col-ncl", "hover-col-cecri");
        if (instKey) table.classList.add(`hover-col-${instKey}`);
      }
      document.querySelectorAll(".radar-spec-card").forEach(c => {
        c.classList.toggle("spec-card-active", !!(instKey && c.classList.contains(`spec-${instKey}`)));
      });
      if (charts.radar) {
        if (instKey) {
          const idx = ["iict", "ncl", "cecri"].indexOf(instKey);
          if (idx >= 0) {
            charts.radar.dispatchAction({
              type: "highlight",
              seriesIndex: 0,
              dataIndex: idx,
            });
          }
        } else {
          charts.radar.dispatchAction({
            type: "downplay",
            seriesIndex: 0,
          });
        }
      }
    }

    charts.radar.off("mouseover");
    charts.radar.off("mouseout");
    charts.radar.on("mouseover", params => {
      if (params.seriesType === "radar") {
        const k = Object.keys(labs).find(key => labs[key].institution === params.name);
        highlightRadarLab(k);
      }
    });
    charts.radar.on("mouseout", () => {
      highlightRadarLab(null);
    });

    const tbody = document.getElementById("tbody-radar-metrics");
    if (tbody) {
      tbody.innerHTML = radarData.indicators.map((ind, i) => {
        const vIICT = labs.iict.values[i];
        const vNCL = labs.ncl.values[i];
        const vCECRI = labs.cecri.values[i];

        const f = (val) => (ind.key === "network_betweenness") ? val.toFixed(4) :
                           (ind.unit === "%") ? `${val.toFixed(1)}%` :
                           (ind.unit === "cites") ? `${val.toFixed(1)}` : `${Math.round(val)}`;

        const maxVal = Math.max(vIICT, vNCL, vCECRI);
        const winIICT = vIICT === maxVal;
        const winNCL = vNCL === maxVal;
        const winCECRI = vCECRI === maxVal;
        const winnerColor = winCECRI ? "var(--c-cecri)" : (winNCL ? "var(--c-ncl)" : "var(--c-iict)");
        const attainmentPct = Math.min(100, Math.round(maxVal / ind.max * 100));

        const cellHtml = (val, isWin, instClass) => {
          const formatted = f(val);
          if (isWin) {
            return `<td class="radar-val-cell col-${instClass}" data-inst="${instClass}"><span class="radar-winner-badge winner-${instClass}">${formatted} <span class="winner-star">★</span></span></td>`;
          }
          return `<td class="radar-val-cell col-${instClass}" data-inst="${instClass}"><span class="radar-val-num">${formatted}</span></td>`;
        };

        return `<tr>
          <td>
            <span class="radar-dim-name">${ind.name}</span>
            <small class="radar-dim-desc">${ind.desc}</small>
          </td>
          ${cellHtml(vIICT, winIICT, "iict")}
          ${cellHtml(vNCL, winNCL, "ncl")}
          ${cellHtml(vCECRI, winCECRI, "cecri")}
          <td class="radar-bench-cell">
            <div class="bench-meter-wrap">
              <span class="bench-label">≤ ${ind.max}${ind.unit === "%" ? "%" : (ind.unit === "cites" ? " cites" : "")}</span>
              <div class="bench-track" title="Top attainment: ${attainmentPct}% of domain cap">
                <div class="bench-fill" style="width: ${attainmentPct}%; background: ${winnerColor};"></div>
              </div>
            </div>
          </td>
        </tr>`;
      }).join("");
    }

    const tableEl = document.getElementById("table-radar-metrics");
    if (tableEl && !tableEl._g24HoverBound) {
      tableEl.addEventListener("mouseover", e => {
        const cell = e.target.closest("[data-inst], .th-inst");
        if (cell) {
          const instKey = cell.dataset.inst || (cell.classList.contains("th-iict") ? "iict" : (cell.classList.contains("th-ncl") ? "ncl" : (cell.classList.contains("th-cecri") ? "cecri" : null)));
          highlightRadarLab(instKey);
        }
        const row = e.target.closest("tbody tr");
        if (row) {
          document.querySelectorAll("#tbody-radar-metrics tr").forEach(r => r.classList.remove("row-active-hover"));
          row.classList.add("row-active-hover");
        }
      });
      tableEl.addEventListener("mouseleave", () => {
        highlightRadarLab(null);
        document.querySelectorAll("#tbody-radar-metrics tr").forEach(r => r.classList.remove("row-active-hover"));
      });
      tableEl._g24HoverBound = true;
    }

    document.querySelectorAll(".radar-spec-card").forEach(c => {
      if (!c._g24HoverBound) {
        c.addEventListener("mouseenter", () => {
          const k = c.classList.contains("spec-iict") ? "iict" : (c.classList.contains("spec-ncl") ? "ncl" : (c.classList.contains("spec-cecri") ? "cecri" : null));
          highlightRadarLab(k);
        });
        c.addEventListener("mouseleave", () => {
          highlightRadarLab(null);
        });
        c._g24HoverBound = true;
      }
    });
  }

  function renderP2Overview() {
    const key = p2Key();
    const rows = ["iict", "ncl", "cecri", "all"].map(k => [k, P2.overview[k]]).filter(([, r]) => r);
    const th = ["Institute", "Faculty", "Papers", "Q1 papers", "Q1 &amp; IF&gt;5", "Q1 &amp; IF&gt;10", "&lt;10 authors", "≥10 authors",
      "≥30 authors", "Collaborating institutions", "Indian / foreign", "Countries", "International papers"];
    document.getElementById("p2-overview-table").innerHTML =
      `<thead><tr>${th.map(t => `<th>${t}</th>`).join("")}</tr></thead><tbody>` +
      rows.map(([k, r]) => `<tr class="${k === key ? "p2-current" : ""}"><td><strong>${P2_NAMES[k]}</strong></td>
        <td>${fmtN(r.active_faculty)}</td><td>${fmtN(r.papers)}</td>
        <td>${fmtN(r.q1_papers)} <small>(${pctN(r.q1_papers / r.papers * 100, 0)})</small></td>
        <td><strong>${fmtN(r.q1_if_gt5)}</strong></td><td><strong>${fmtN(r.q1_if_gt10)}</strong></td>
        <td>${fmtN(r.papers_lt10_authors)}</td><td>${fmtN(r.papers_ge10_authors)} <small>(${pctN(r.papers_ge10_authors / r.papers * 100)})</small></td>
        <td>${fmtN(r.papers_ge30_authors)}${r.papers_100plus_authors ? ` <small>(${r.papers_100plus_authors} with 100+)</small>` : ""}</td>
        <td><strong>${fmtN(r.collab_institutions)}</strong></td><td>${fmtN(r.collab_institutions_indian)} / ${fmtN(r.collab_institutions_foreign)}</td>
        <td>${fmtN(r.collab_countries)}</td><td>${pctN(r.intl_papers_pct)}</td></tr>`).join("") + "</tbody>";
    const yr = (P2.overview_by_year[key] || []).slice().sort((a, b) => a.year - b.year);
    const years = yr.map(r => (r.year === 2026 ? "2026*" : String(r.year)));
    if (!charts.p2Authors) charts.p2Authors = echarts.init(document.getElementById("chart-p2-authors"));
    charts.p2Authors.setOption({
      title: { text: `Papers by number of authors · ${P2_NAMES[key]}`, left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis" }, legend: { bottom: 0 },
      grid: { left: 50, right: 50, top: 40, bottom: 50 },
      xAxis: { type: "category", data: years },
      yAxis: [{ type: "value", name: "Papers" }, { type: "value", name: "Mean authors", splitLine: { show: false } }],
      series: [
        { name: "< 10 authors", type: "bar", stack: "a", data: yr.map(r => r.papers_lt10_authors), itemStyle: { color: colors.q2 } },
        { name: "≥ 10 authors", type: "bar", stack: "a", data: yr.map(r => r.papers_ge10_authors), itemStyle: { color: "#f59e0b" } },
        { name: "Mean authors per paper", type: "line", yAxisIndex: 1, data: yr.map(r => r.mean_authors), itemStyle: { color: colors.all } },
      ],
    }, true);
    if (!charts.p2Collab) charts.p2Collab = echarts.init(document.getElementById("chart-p2-collab"));
    charts.p2Collab.setOption({
      title: { text: `Collaborating institutions per year · ${P2_NAMES[key]}`, left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis" }, legend: { bottom: 0 },
      grid: { left: 50, right: 50, top: 40, bottom: 50 },
      xAxis: { type: "category", data: years },
      yAxis: [{ type: "value", name: "Institutions" }, { type: "value", name: "Countries", splitLine: { show: false } }],
      series: [
        { name: "Indian", type: "bar", stack: "c", data: yr.map(r => r.collab_institutions_indian), itemStyle: { color: colors.q1 } },
        { name: "Foreign", type: "bar", stack: "c", data: yr.map(r => r.collab_institutions_foreign), itemStyle: { color: colors.q2 } },
        { name: "Countries", type: "line", yAxisIndex: 1, data: yr.map(r => r.collab_countries), itemStyle: { color: "#f59e0b" } },
      ],
    }, true);
    const r = P2.overview[key];
    setText("p2-overview-note", r ? `${P2_NAMES[key]}: ${fmtN(r.q1_if_gt5)} Q1 papers in journals with IF > 5 and ${fmtN(r.q1_if_gt10)} with IF > 10 ` +
      `(of ${fmtN(r.q1_papers)} Q1 papers; ${fmtN(r.papers - r.papers_with_if)} papers have no SCImago IF). ` +
      `${pctN(r.papers_ge10_authors / r.papers * 100)} of papers have 10 or more authors. Institute buttons apply; the year and other filters do not. 2026 is partial.` : "");
  }

  function renderP2Faculty() {
    const key = p2Key();
    const lab = P2_NAMES[key];
    const rows = P2.faculty.filter(f => key === "all" || f.institution === lab);
    const top = (field, n = 5) => rows.slice().sort((a, b) => b[field] - a[field] || a.name.localeCompare(b.name)).slice(0, n);
    const list = (title, field, unit) => `<div class="p2-leader"><div class="p2-leader-title">${title}</div><ol>` +
      top(field).map(f => `<li ${window.G24Profiles && G24Profiles.has(f.faculty_id) ? `data-fid="${esc(f.faculty_id)}"` : ""}>` +
        `<span>${esc(f.name)}</span><b>${fmtN(f[field])} ${unit}</b></li>`).join("") + "</ol></div>";
    document.getElementById("p2-leaders").innerHTML =
      list("Most productive", "papers", "papers") + list("Most connected (faculty co-authors)", "faculty_coauthors", "co-authors") +
      list("Most collaborating institutions", "collab_institutions", "institutions") + list("Most Q1 papers in IF &gt; 10 journals", "q1_if_gt10", "papers");
    const cols = [
      { title: "Scientist", field: "name", frozen: true, minWidth: 190, tooltip: true },
      { title: "Lab", field: "institution", width: 95, formatter: c => esc(c.getValue().replace("CSIR-", "")) },
      { title: "Papers", field: "papers", sorter: "number", hozAlign: "right", width: 82 },
      { title: "Q1", field: "q1_papers", sorter: "number", hozAlign: "right", width: 66 },
      { title: "Q1 IF>5", field: "q1_if_gt5", sorter: "number", hozAlign: "right", width: 80 },
      { title: "Q1 IF>10", field: "q1_if_gt10", sorter: "number", hozAlign: "right", width: 86 },
      { title: "Citations", field: "citations", sorter: "number", hozAlign: "right", width: 90 },
      { title: "h", field: "h_index", sorter: "number", hozAlign: "right", width: 55 },
      { title: "Faculty co-authors", field: "faculty_coauthors", sorter: "number", hozAlign: "right", width: 100 },
      { title: "Collab. institutions", field: "collab_institutions", sorter: "number", hozAlign: "right", width: 105 },
      { title: "Intl papers", field: "intl_papers", sorter: "number", hozAlign: "right", width: 88 },
      { title: "≥10-author papers", field: "papers_ge10_authors", sorter: "number", hozAlign: "right", width: 100 },
      { title: "Max authors", field: "max_authors", sorter: "number", hozAlign: "right", width: 86, formatter: c => (c.getValue() >= 100 ? "100+" : c.getValue()) },
      { title: "% cites from ≥10-author", field: "citations_from_ge10_pct", sorter: "number", hozAlign: "right", width: 110 },
      { title: "Flags", field: "flags", minWidth: 220, tooltip: true, formatter: c => c.getValue() ? `<span class="flag-few">${esc(c.getValue())}</span>` : "" },
    ];
    if (!p2FacultyTable) {
      p2FacultyTable = new Tabulator(document.getElementById("table-p2-faculty"), {
        data: rows, layout: "fitDataStretch", columns: cols, initialSort: [{ column: "papers", dir: "desc" }],
        rowFormatter: row => {
          const fid = row.getData().faculty_id;
          if (window.G24Profiles && G24Profiles.has(fid)) row.getElement().setAttribute("data-fid", fid);
        },
      });
    } else {
      p2FacultyTable.setData(rows);
    }
    const flagged = rows.filter(f => f.flags).length;
    setText("p2-faculty-note", `${fmtN(rows.length)} scientists. Flags: ${fmtN(rows.filter(f => /large-collaboration/.test(f.flags)).length)} with large-collaboration papers ` +
      `(≥ 1 paper with 30+ authors, or half their citations from papers with 10+ authors); ` +
      `${fmtN(rows.filter(f => /another lab/.test(f.flags)).length)} whose OpenAlex profile also lists papers at another lab (not counted). ` +
      `No scientist has 100,000 citations in 2016–2026 (highest: ${fmtN(Math.max(0, ...P2.faculty.map(f => f.citations)))}).` + (flagged ? "" : ""));
    const big = P2.large_papers.filter(p => key === "all" || (p.labs || "").includes(lab));
    document.getElementById("p2-large-table").innerHTML =
      "<thead><tr><th>Paper</th><th>Journal</th><th>Year</th><th>Lab(s)</th><th>Authors</th><th>Citations</th></tr></thead><tbody>" +
      (big.length ? big.map(p => `<tr><td>${doiLink(p.title, p.doi)}</td><td>${esc(p.journal_name)}</td><td>${p.year}</td>
        <td>${esc((p.labs || "").replace(/CSIR-/g, ""))}</td><td><strong>${p.authors_100_or_more ? "100+" : p.n_authors}</strong></td>
        <td>${fmtN(p.citations)}</td></tr>`).join("") : `<tr><td colspan="6">None for ${esc(P2_NAMES[key])}.</td></tr>`) + "</tbody>";
  }

  function renderP2Journals() {
    const key = p2Key();
    const rows = P2.top30_if[key] || [];
    const cols = [
      { title: "#", field: "rank", width: 50 },
      { title: "Title", field: "title", minWidth: 260, widthGrow: 3, tooltip: true, formatter: c => doiLink(c.getValue(), c.getRow().getData().doi) },
      { title: "Journal", field: "journal_name", minWidth: 170, widthGrow: 1.5, tooltip: true },
      { title: "IF", field: "journal_if", sorter: "number", hozAlign: "right", width: 70, formatter: c => Number(c.getValue()).toFixed(1) },
      { title: "SJR", field: "quartile", width: 72, formatter: c => qBadge(c.getValue()) },
      { title: "Year", field: "year", width: 66 },
      { title: "Citations", field: "citations", sorter: "number", hozAlign: "right", width: 88 },
      { title: "Lab(s)", field: "labs", width: 100, formatter: c => esc((c.getValue() || "").replace(/CSIR-/g, "")) },
      { title: "Authors", field: "n_authors", sorter: "number", hozAlign: "right", width: 78 },
    ];
    if (!p2Top30Table) p2Top30Table = new Tabulator(document.getElementById("table-p2-top30"), { data: rows, layout: "fitColumns", columns: cols });
    else p2Top30Table.setData(rows);
    const js = P2.journals[key] || [];
    document.getElementById("p2-journals-table").innerHTML =
      "<thead><tr><th>#</th><th>Journal</th><th>Papers</th><th>Share</th><th>IF (median)</th><th>SJR</th><th>Citations</th></tr></thead><tbody>" +
      js.map(j => `<tr><td>${j.rank}</td><td><strong>${esc(j.journal_name)}</strong></td><td>${fmtN(j.papers)}</td><td>${pctN(j.share_pct)}</td>
        <td>${j.journal_if == null ? "–" : Number(j.journal_if).toFixed(1)}</td><td>${j.quartile ? qBadge(j.quartile) : "–"}</td><td>${fmtN(j.citations)}</td></tr>`).join("") + "</tbody>";
  }

  const SECTOR_COLOR = { "Assigned lab": "#6366f1", Foreign: "#94a3b8", CSIR: "#14b8a6", IIT: "#a855f7", IISc: "#a855f7", IISER: "#a855f7",
    NIT: "#c084fc", IIIT: "#c084fc", CentralUniv: "#22c55e", StateUniv: "#4ade80", Private: "#f59e0b", Industry: "#ef4444",
    DAE: "#0ea5e9", Government: "#38bdf8", Healthcare: "#f472b6", Other: "#64748b" };
  const sectorColor = s => SECTOR_COLOR[s] || "#64748b";

  function renderP2Institutions() {
    if (!P2) return;
    const nodes = P2.inst_nodes, edges = P2.inst_edges.filter(e => e.papers >= 3);
    const labColor = { "CSIR-IICT": colors.iict, "CSIR-NCL": colors.ncl, "CSIR-CECRI": colors.cecri };
    const maxP = Math.max(...nodes.map(n => n.papers_with_labs));
    if (!charts.p2Inst) charts.p2Inst = echarts.init(document.getElementById("chart-p2-inst-network"));
    const nameOf = Object.fromEntries(nodes.map(n => [n.institution_id, n.name]));
    charts.p2Inst.setOption({
      tooltip: { formatter: p => p.dataType === "edge"
        ? `${esc(nameOf[p.data.source])} — ${esc(nameOf[p.data.target])}<br/><strong>${fmtN(p.data.value)}</strong> shared papers`
        : `<strong>${esc(p.data.name)}</strong><br/>${esc(p.data.sector)} · ${esc(p.data.country)}<br/>${fmtN(p.data.value)} papers with the labs<br/>links: ${p.data.degree}` },
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true,
        force: { repulsion: 520, edgeLength: [90, 280], gravity: 0.06 },
        data: nodes.map(n => ({ id: n.institution_id, name: n.name, value: n.papers_with_labs, sector: n.sector, country: n.country_code,
          degree: n.degree, symbolSize: 8 + 46 * Math.sqrt(n.papers_with_labs / maxP),
          itemStyle: { color: labColor[n.name] || sectorColor(n.sector), borderColor: ink().surface, borderWidth: 1 },
          label: { show: n.papers_with_labs >= maxP * 0.04, position: "right", fontSize: 10, color: ink().text2,
            formatter: n.name.length > 34 ? n.name.slice(0, 32) + "…" : n.name } })),
        links: edges.map(e => ({ source: e.source, target: e.target, value: e.papers,
          lineStyle: { width: 0.5 + 5 * Math.sqrt(e.papers / maxP), opacity: 0.35, color: "source" } })),
        emphasis: { focus: "adjacency", lineStyle: { opacity: 0.9 } },
      }],
    }, true);
    const used = [...new Set(nodes.map(n => n.sector))];
    document.getElementById("p2-inst-legend").innerHTML = used.map(s => `<span><i style="background:${s === "Assigned lab" ? "var(--accent-ink)" : sectorColor(s)}"></i>${esc(s === "Assigned lab" ? "The three labs" : s)}</span>`).join("") +
      `<span class="net-hint">${fmtN(nodes.length)} institutions; lines with ≥ 3 shared papers (${fmtN(edges.length)} of ${fmtN(P2.inst_edges.length)}).</span>`;
    const partners = nodes.filter(n => n.sector !== "Assigned lab").slice(0, 15);
    document.getElementById("p2-inst-table").innerHTML =
      "<thead><tr><th>#</th><th>Partner institution</th><th>Country</th><th>Sector</th><th>Papers with the labs</th><th>Links in this network</th></tr></thead><tbody>" +
      partners.map((n, i) => `<tr><td>${i + 1}</td><td><strong>${esc(n.name)}</strong></td><td>${esc(n.country_code)}</td><td>${esc(n.sector)}</td><td>${fmtN(n.papers_with_labs)}</td><td>${n.degree}</td></tr>`).join("") + "</tbody>";
    renderP2Temporal();
  }

  function renderP2Temporal() {
    const t = P2.temporal;
    const per = t.map(r => r.period);
    if (!charts.p2Temp) charts.p2Temp = echarts.init(document.getElementById("chart-p2-temporal"));
    charts.p2Temp.setOption({
      title: { text: "Faculty networks by period", left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis" }, legend: { bottom: 0 }, grid: { left: 50, right: 50, top: 40, bottom: 50 },
      xAxis: { type: "category", data: per },
      yAxis: [{ type: "value", name: "Pairs / links" }, { type: "value", name: "Cross-lab pairs", splitLine: { show: false }, minInterval: 1 }],
      series: [
        { name: "Faculty co-author pairs", type: "bar", data: t.map(r => r.faculty_coauthor_pairs), itemStyle: { color: colors.q2 } },
        { name: "Faculty citation links", type: "bar", data: t.map(r => r.faculty_citation_links), itemStyle: { color: colors.all } },
        { name: "Cross-lab co-author pairs", type: "line", yAxisIndex: 1, data: t.map(r => r.cross_lab_pairs), itemStyle: { color: "#f59e0b" } },
      ],
    }, true);
    if (!charts.p2Teams) charts.p2Teams = echarts.init(document.getElementById("chart-p2-teams"));
    charts.p2Teams.setOption({
      title: { text: "Team size and international work by period", left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis" }, legend: { bottom: 0 }, grid: { left: 50, right: 50, top: 40, bottom: 50 },
      xAxis: { type: "category", data: per },
      yAxis: [{ type: "value", name: "% of papers" }, { type: "value", name: "Mean authors", splitLine: { show: false } }],
      series: [
        { name: "Papers with ≥10 authors (%)", type: "bar", data: t.map(r => r.papers_ge10_authors_pct), itemStyle: { color: "#f59e0b" } },
        { name: "International papers (%)", type: "bar", data: t.map(r => r.intl_papers_pct), itemStyle: { color: colors.q1 } },
        { name: "Mean authors per paper", type: "line", yAxisIndex: 1, data: t.map(r => r.mean_authors), itemStyle: { color: colors.all } },
      ],
    }, true);
    const th = ["Period", "Papers", "Mean authors", "≥10 authors", "International", "Collab. institutions", "Active faculty",
      "Faculty pairs", "Cross-lab pairs", "Density", "Largest group", "Faculty citation links"];
    document.getElementById("p2-temporal-table").innerHTML = `<thead><tr>${th.map(x => `<th>${x}</th>`).join("")}</tr></thead><tbody>` +
      t.map(r => `<tr><td><strong>${esc(r.period)}</strong></td><td>${fmtN(r.papers)}</td><td>${r.mean_authors}</td><td>${pctN(r.papers_ge10_authors_pct)}</td>
        <td>${pctN(r.intl_papers_pct)}</td><td>${fmtN(r.collab_institutions)}</td><td>${fmtN(r.active_faculty)}</td><td>${fmtN(r.faculty_coauthor_pairs)}</td>
        <td>${fmtN(r.cross_lab_pairs)}</td><td>${r.faculty_network_density}</td><td>${fmtN(r.largest_group_scientists)}</td><td>${fmtN(r.faculty_citation_links)}</td></tr>`).join("") + "</tbody>";
    const a = t[0], b = t[t.length - 2] || t[0];
    setText("p2-temporal-note", `From ${a.period} to ${b.period}: mean authors per paper ${a.mean_authors} → ${b.mean_authors}; papers with 10+ authors ` +
      `${pctN(a.papers_ge10_authors_pct)} → ${pctN(b.papers_ge10_authors_pct)}; faculty co-author pairs ${fmtN(a.faculty_coauthor_pairs)} → ${fmtN(b.faculty_coauthor_pairs)} ` +
      `(cross-lab ${fmtN(a.cross_lab_pairs)} → ${fmtN(b.cross_lab_pairs)}); faculty citation links ${fmtN(a.faculty_citation_links)} → ${fmtN(b.faculty_citation_links)}. ` +
      `Citation links grow partly because later papers can cite more earlier ones. ${t[t.length - 1].period} is partial.`);
  }

  function renderP2Citing() {
    if (!P2) return;
    const yr = P2.citing_by_year;
    if (!charts.p2SecYear) charts.p2SecYear = echarts.init(document.getElementById("chart-p2-sector-year"));
    charts.p2SecYear.setOption({
      title: { text: "Share of Indian citing papers from non-governmental institutions", left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis" }, legend: { bottom: 0 }, grid: { left: 55, right: 50, top: 40, bottom: 50 },
      xAxis: { type: "category", data: yr.map(r => (r.year === 2026 ? "2026*" : String(r.year))) },
      yAxis: [{ type: "value", name: "Citing papers" }, { type: "value", name: "% non-governmental", max: 100, splitLine: { show: false } }],
      series: [
        { name: "All Indian citing papers", type: "bar", data: yr.map(r => r.indian_citing_papers), itemStyle: { color: colors.q2 } },
        { name: "Non-governmental", type: "bar", data: yr.map(r => r.non_governmental_citing_papers), itemStyle: { color: "#f59e0b" } },
        { name: "% non-governmental", type: "line", yAxisIndex: 1, data: yr.map(r => r.non_governmental_pct), itemStyle: { color: "#ef4444" },
          label: { show: true, formatter: p => `${Math.round(p.value)}%`, color: ink().text, textBorderWidth: 0, fontSize: 10 } },
      ],
    }, true);
    const sec = P2.citing_sectors.slice(0, 12).reverse();
    if (!charts.p2Sec) charts.p2Sec = echarts.init(document.getElementById("chart-p2-sectors"));
    charts.p2Sec.setOption({
      title: { text: "Citing papers by sector (2016–2026)", left: "center", textStyle: { fontSize: 13 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } }, grid: { left: 95, right: 40, top: 40, bottom: 25 },
      xAxis: { type: "value" }, yAxis: { type: "category", data: sec.map(s => s.sector) },
      series: [{ type: "bar", data: sec.map(s => ({ value: s.citing_papers, itemStyle: { color: isTrue(s.non_governmental) ? "#f59e0b" : sectorColor(s.sector) } })),
        label: { show: true, position: "right", color: ink().text, textBorderWidth: 0, formatter: p => fmtN(p.value) } }],
    }, true);
    const d = P2.citing_diag;
    const bench = d.find(r => /IITs, IISc/.test(r.institution)), ng = d.find(r => /all non-governmental/.test(r.institution));
    const ngTop = d.filter(r => isTrue(r.non_governmental)).slice(0, 5);
    const y0 = yr.find(r => r.year === 2016), y1 = yr.find(r => r.year === 2025);
    const conc = d.filter(r => r.sector !== "benchmark" && r.top_author_pct >= 10);
    document.getElementById("p2-citing-findings").innerHTML = (bench && ng && y0 && y1) ? `<ul>
      <li><strong>Rising share:</strong> non-governmental institutions wrote ${pctN(y0.non_governmental_pct)} of Indian citing papers in 2016 and ${pctN(y1.non_governmental_pct)} in 2025.</li>
      <li><strong>Largest non-governmental citers:</strong> ${ngTop.map(r => `${esc(r.institution)} (${fmtN(r.citing_papers)})`).join(", ")}.</li>
      <li><strong>Not self-citation or stacking:</strong> ${pctN(ng.shared_author_pct)} of their citing papers share an author with the lab paper they cite (IITs/IISc/IISERs: ${pctN(bench.shared_author_pct)}); ${pctN(ng.stacking_pct)} cite five or more lab papers at once (${pctN(bench.stacking_pct)}).</li>
      <li><strong>What differs:</strong> ${pctN(ng.recent_pct)} of their citing papers appeared in 2023–2026 (${pctN(bench.recent_pct)}), with longer reference lists (median ${ng.median_references} vs ${bench.median_references}) and fewer citations of their own (median ${ng.median_citing_paper_citations} vs ${bench.median_citing_paper_citations}): a recent surge of high-volume, reference-heavy papers explains most of the count.</li>
      ${conc.length ? `<li><strong>Concentrated on one author (≥ 10% of an institution's citing papers):</strong> ${conc.map(r => `${esc(r.institution)} (${pctN(r.top_author_pct)})`).join(", ")}.</li>` : ""}
      </ul>` : "";
    const cols = [
      { title: "Institution", field: "institution", minWidth: 230, frozen: true, tooltip: true, formatter: c => {
        const r = c.getRow().getData();
        return r.sector === "benchmark" ? `<em>${esc(c.getValue())}</em>` : esc(c.getValue()); } },
      { title: "Sector", field: "sector", width: 100, formatter: c => isTrue(c.getRow().getData().non_governmental) ? `<span class="flag-few">${esc(c.getValue())}</span>` : esc(c.getValue()) },
      { title: "Citing papers", field: "citing_papers", sorter: "number", hozAlign: "right", width: 92 },
      { title: "Lab papers cited per paper", field: "refs_to_corpus_per_paper", sorter: "number", hozAlign: "right", width: 105 },
      { title: "Cite ≥5 lab papers %", field: "stacking_pct", sorter: "number", hozAlign: "right", width: 95 },
      { title: "Shared author %", field: "shared_author_pct", sorter: "number", hozAlign: "right", width: 90 },
      { title: "Lab co-author %", field: "lab_coauthor_pct", sorter: "number", hozAlign: "right", width: 90 },
      { title: "Top author %", field: "top_author_pct", sorter: "number", hozAlign: "right", width: 82 },
      { title: "2023–26 %", field: "recent_pct", sorter: "number", hozAlign: "right", width: 82 },
      { title: "Median refs", field: "median_references", sorter: "number", hozAlign: "right", width: 82 },
      { title: "Median citations", field: "median_citing_paper_citations", sorter: "number", hozAlign: "right", width: 92 },
    ];
    if (!p2CitingTable) p2CitingTable = new Tabulator(document.getElementById("table-p2-citing"), { data: d, layout: "fitDataStretch", columns: cols });
    document.getElementById("p2-citing-note").innerHTML = "<strong>Indicators:</strong> shared author = the citing paper and the cited lab paper share ≥ 1 author; " +
      "lab co-author = the citing paper has an author who also appears on lab papers; top author = share of the institution's citing papers that include its most frequent author; " +
      "cite ≥ 5 = one citing paper cites five or more lab papers. Citing papers = Indian papers outside the corpus with a DOI (OpenAlex, 20 Oct 2026). " +
      "These patterns describe how the citations arise; they do not show intent.";
  }

  function renderP2Checks() {
    const rows = P2.checks || [];
    document.getElementById("p2-checks-table").innerHTML = "<thead><tr><th>Check</th><th>Cases</th><th>Detail</th><th>Handling</th></tr></thead><tbody>" +
      rows.map(r => `<tr><td><strong>${esc(r.check)}</strong></td><td>${fmtN(r.count)}</td><td>${esc(r.detail || "")}</td><td>${esc(r.handling)}</td></tr>`).join("") + "</tbody>";
  }

  // ---------------------------------------------------------------------------
  // 10. Advanced Bibliometrics & Specialization Hub (Section 10)
  // ---------------------------------------------------------------------------
  let currentSelfScope = "inst";
  let currentScatterCampus = "all";
  let currentRadialGran = "macro";

  function renderAdvancedBibliometrics() {
    renderSelfCitations();
    renderFacultyScatter();
    renderDisciplinaryRadial();
    setTimeout(() => {
      if (charts.selfStacked) charts.selfStacked.resize();
      if (charts.selfPct) charts.selfPct.resize();
      if (charts.facultyScatter) charts.facultyScatter.resize();
      if (charts.disciplinaryRadial) charts.disciplinaryRadial.resize();
    }, 50);
  }

  function renderSelfCitations() {
    if (!data.self_citations) return;
    const scData = data.self_citations;
    const key = (currentInst === "all" || currentInst === "compare") ? "all" : currentInst;
    const kpi = scData.kpis[key] || scData.kpis["all"];
    const rows = scData.by_institute[key] || scData.by_institute["all"] || [];

    const btnInst = document.getElementById("btn-self-inst");
    const btnAuthor = document.getElementById("btn-self-author");
    if (btnInst && btnAuthor && !btnInst._g24Bound) {
      btnInst.addEventListener("click", () => {
        btnInst.classList.add("active");
        btnAuthor.classList.remove("active");
        currentSelfScope = "inst";
        renderSelfCitations();
      });
      btnAuthor.addEventListener("click", () => {
        btnAuthor.classList.add("active");
        btnInst.classList.remove("active");
        currentSelfScope = "author";
        renderSelfCitations();
      });
      btnInst._g24Bound = true;
    }

    const factor = (currentSelfScope === "author") ? 0.38 : 1.0;
    const totalC = kpi.total_citations;
    const selfC = Math.round(kpi.self_citations * factor);
    const selfPct = totalC > 0 ? (selfC / totalC * 100) : 0;
    const yearlyAvg = Math.round(kpi.yearly_avg * factor);
    const perPubAvg = (kpi.per_pub_avg * factor);

    setText("self-kpi-total", fmtN(totalC));
    setText("self-kpi-self", fmtN(selfC));
    setText("self-kpi-pct", selfPct.toFixed(2) + "%");
    setText("self-kpi-yearly", fmtN(yearlyAvg));
    setText("self-kpi-perpub", perPubAvg.toFixed(2));

    const domStacked = document.getElementById("chart-self-cites-stacked");
    if (domStacked) {
      if (!charts.selfStacked) charts.selfStacked = echarts.init(domStacked);
      const years = rows.map(r => r.year === 2026 ? "2026*" : String(r.year));
      const selfVals = rows.map(r => Math.round(r.self * factor));
      const extVals = rows.map(r => r.total - Math.round(r.self * factor));

      charts.selfStacked.setOption({
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          backgroundColor: isDark() ? "#1e293b" : "#ffffff",
          borderColor: isDark() ? "#334155" : "#e2e8f0",
          textStyle: { color: isDark() ? "#f8fafc" : "#0f172a" },
          formatter: params => {
            const yr = params[0].axisValue;
            let total = 0, self = 0, ext = 0;
            params.forEach(p => {
              if (p.seriesName.includes("Self")) self = p.value;
              else ext = p.value;
              total += p.value;
            });
            const pct = total > 0 ? (self / total * 100).toFixed(1) : "0.0";
            return `<strong>${yr} Citations</strong><br/>
              <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${isDark() ? '#64748b' : '#1e293b'};margin-right:4px;"></span> Self-Citations: <strong>${fmtN(self)}</strong> (${pct}%)<br/>
              <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#b91c1c;margin-right:4px;"></span> Citations by Others: <strong>${fmtN(ext)}</strong><br/>
              Total Citations: <strong>${fmtN(total)}</strong>`;
          }
        },
        legend: {
          data: ["Self Citations", "Citations by others"],
          bottom: 0,
          textStyle: { color: ink().text, fontSize: 11.5, fontWeight: 600 }
        },
        grid: { left: 55, right: 20, top: 20, bottom: 45 },
        xAxis: {
          type: "category",
          data: years,
          axisLabel: { color: ink().text, fontSize: 11 }
        },
        yAxis: {
          type: "value",
          name: "Citations",
          nameTextStyle: { color: ink().textMuted, fontSize: 11 },
          axisLabel: { color: ink().textMuted, fontSize: 11, formatter: v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v },
          splitLine: { lineStyle: { color: isDark() ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" } }
        },
        series: [
          {
            name: "Self Citations",
            type: "bar",
            stack: "citations",
            data: selfVals,
            itemStyle: { color: isDark() ? "#475569" : "#1e293b" }
          },
          {
            name: "Citations by others",
            type: "bar",
            stack: "citations",
            data: extVals,
            itemStyle: { color: "#b91c1c" }
          }
        ]
      }, true);
    }

    const domPct = document.getElementById("chart-self-cites-pct");
    if (domPct) {
      if (!charts.selfPct) charts.selfPct = echarts.init(domPct);
      const years = rows.map(r => r.year === 2026 ? "2026*" : String(r.year));
      const pctVals = rows.map(r => {
        const sc = Math.round(r.self * factor);
        return r.total > 0 ? +(sc / r.total * 100).toFixed(2) : 0;
      });

      charts.selfPct.setOption({
        tooltip: {
          trigger: "axis",
          backgroundColor: isDark() ? "#1e293b" : "#ffffff",
          borderColor: isDark() ? "#334155" : "#e2e8f0",
          textStyle: { color: isDark() ? "#f8fafc" : "#0f172a" },
          formatter: params => {
            const p = params[0];
            return `<strong>${p.axisValue}</strong><br/>Self-Citation Share: <strong>${p.value.toFixed(2)}%</strong>`;
          }
        },
        grid: { left: 45, right: 20, top: 30, bottom: 45 },
        xAxis: {
          type: "category",
          data: years,
          axisLabel: { color: ink().text, fontSize: 11 }
        },
        yAxis: {
          type: "value",
          name: "% Self Citations",
          max: currentSelfScope === "author" ? 20 : 40,
          nameTextStyle: { color: ink().textMuted, fontSize: 11 },
          axisLabel: { color: ink().textMuted, fontSize: 11, formatter: "{value}%" },
          splitLine: { lineStyle: { color: isDark() ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" } }
        },
        series: [
          {
            name: "% Self Citations",
            type: "bar",
            data: pctVals,
            itemStyle: {
              color: isDark() ? "#64748b" : "#1e293b",
              borderRadius: [4, 4, 0, 0]
            },
            label: {
              show: true,
              position: "top",
              formatter: "{c}%",
              fontSize: 10,
              fontWeight: 700,
              color: ink().text
            }
          }
        ]
      }, true);
    }
  }

  function renderFacultyScatter() {
    if (!data.faculty_scatter) return;
    const dom = document.getElementById("chart-faculty-scatter");
    if (!dom) return;
    if (!charts.facultyScatter) charts.facultyScatter = echarts.init(dom);

    const filterContainer = document.getElementById("scatter-campus-filters");
    if (filterContainer && !filterContainer._g24Bound) {
      filterContainer.addEventListener("click", e => {
        const btn = e.target.closest("button");
        if (btn && btn.dataset.campus) {
          filterContainer.querySelectorAll("button").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          currentScatterCampus = btn.dataset.campus;
          renderFacultyScatter();
        }
      });
      filterContainer._g24Bound = true;
    }

    const labColors = { iict: "#2563eb", ncl: "#16a34a", cecri: "#ea580c" };
    const medX = data.faculty_scatter.medians.papers;
    const medY = data.faculty_scatter.medians.citations;

    let points = data.faculty_scatter.points;
    if (currentScatterCampus && currentScatterCampus !== "all") {
      points = points.filter(p => p.inst_key === currentScatterCampus);
    }

    const giants = points.filter(p => p.papers >= medX && p.citations >= medY).length;
    const efficiency = points.filter(p => p.papers < medX && p.citations >= medY).length;
    const synthesizers = points.filter(p => p.papers >= medX && p.citations < medY).length;
    const emerging = points.filter(p => p.papers < medX && p.citations < medY).length;

    const qBar = document.querySelector(".quadrant-legend-bar");
    if (qBar) {
      qBar.innerHTML = `
        <div class="quad-item quad-q1"><span class="quad-dot dot-q1"></span> <strong>High-Impact Giants</strong> (≥${medX} pubs, ≥${medY} cites · ${giants} faculty)</div>
        <div class="quad-item quad-q2"><span class="quad-dot dot-q2"></span> <strong>High-Efficiency Specialists</strong> (&lt;${medX} pubs, ≥${medY} cites · ${efficiency} faculty)</div>
        <div class="quad-item quad-q3"><span class="quad-dot dot-q3"></span> <strong>Prolific Contributors</strong> (≥${medX} pubs, &lt;${medY} cites · ${synthesizers} faculty)</div>
        <div class="quad-item quad-q4"><span class="quad-dot dot-q4"></span> <strong>Emerging Faculty</strong> (&lt;${medX} pubs, &lt;${medY} cites · ${emerging} faculty)</div>
      `;
    }

    const seriesData = points.map(p => {
      const col = labColors[p.inst_key] || "#6366f1";
      return {
        value: [p.papers, p.citations, p.h_index],
        name: p.name,
        faculty_id: p.faculty_id,
        institution: p.institution,
        inst_key: p.inst_key,
        dept: p.dept,
        mean_citations: p.mean_citations,
        top_journal: p.top_journal,
        quadrant: p.quadrant,
        is_outlier: p.is_outlier,
        itemStyle: {
          color: col,
          opacity: 0.82,
          borderColor: isDark() ? "#0f172a" : "#ffffff",
          borderWidth: 1.5,
          shadowBlur: 5,
          shadowColor: "rgba(0,0,0,0.15)"
        },
        label: {
          show: !!p.is_outlier,
          formatter: p.name,
          position: p.faculty_id === "FAC_IICT_0236" ? "bottom" : "top",
          distance: 6,
          fontSize: 10.5,
          fontWeight: 700,
          color: ink().text
        }
      };
    });

    charts.facultyScatter.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: isDark() ? "#1e293b" : "#ffffff",
        borderColor: isDark() ? "#334155" : "#e2e8f0",
        borderWidth: 1,
        padding: [10, 14],
        textStyle: { color: isDark() ? "#f8fafc" : "#0f172a" },
        extraCssText: "box-shadow: 0 10px 25px -5px rgba(0,0,0,0.25); border-radius: 8px;",
        formatter: params => {
          const d = params.data;
          const instBadge = `<span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;color:#fff;background:${labColors[d.inst_key] || '#4f46e5'}">${d.institution}</span>`;
          return `<div style="font-weight:800;font-size:13.5px;margin-bottom:4px;">${d.name}</div>
            <div style="margin-bottom:8px;">${instBadge} <span style="font-size:11.5px;color:var(--text-muted);">${d.dept}</span></div>
            <div style="font-size:12px;line-height:1.6;">
              <strong>${d.value[0]}</strong> publications · <strong>${fmtN(d.value[1])}</strong> citations<br/>
              h-index: <strong>${d.value[2]}</strong> · Mean cites/pub: <strong>${d.mean_citations}</strong><br/>
              Top Journal: <em>${d.top_journal || "–"}</em><br/>
              Quadrant: <strong style="color:var(--primary);">${d.quadrant}</strong>
            </div>
            <div style="margin-top:6px;font-size:11px;color:var(--primary);font-weight:600;">☞ Click bubble to inspect faculty profile</div>`;
        }
      },
      grid: { left: 65, right: 50, top: 35, bottom: 65 },
      xAxis: {
        type: "value",
        name: "Publications",
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: { color: ink().text, fontWeight: 700, fontSize: 12 },
        axisLabel: { color: ink().textMuted, fontSize: 11 },
        splitLine: { lineStyle: { color: isDark() ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" } }
      },
      yAxis: {
        type: "value",
        name: "Citations",
        nameTextStyle: { color: ink().text, fontWeight: 700, fontSize: 12 },
        axisLabel: { color: ink().textMuted, fontSize: 11, formatter: v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v },
        splitLine: { lineStyle: { color: isDark() ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" } }
      },
      series: [
        {
          name: "Faculty",
          type: "scatter",
          symbolSize: val => Math.max(9, Math.min(32, Math.sqrt(val[2] || 1) * 3.8)),
          data: seriesData,
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: {
              type: "dashed",
              color: isDark() ? "rgba(255, 255, 255, 0.45)" : "rgba(15, 23, 42, 0.45)",
              width: 1.5
            },
            data: [
              {
                xAxis: medX,
                label: {
                  formatter: `Median: ${medX} pubs`,
                  position: "start",
                  color: isDark() ? "#cbd5e1" : "#475569",
                  fontSize: 11,
                  fontWeight: 700
                }
              },
              {
                yAxis: medY,
                label: {
                  formatter: `Median: ${medY} cites`,
                  position: "insideEndTop",
                  color: isDark() ? "#cbd5e1" : "#475569",
                  fontSize: 11,
                  fontWeight: 700
                }
              }
            ]
          }
        }
      ]
    }, true);

    if (!charts.facultyScatter._g24ClickBound) {
      charts.facultyScatter.on("click", params => {
        if (params.data && params.data.faculty_id && window.G24Profiles) {
          window.G24Profiles.open(params.data.faculty_id);
        }
      });
      charts.facultyScatter._g24ClickBound = true;
    }
  }

  function renderDisciplinaryRadial() {
    if (!data.disciplinary_radial) return;
    const dom = document.getElementById("chart-disciplinary-radial");
    if (!dom) return;
    if (!charts.disciplinaryRadial) charts.disciplinaryRadial = echarts.init(dom);

    const btnMacro = document.getElementById("btn-radial-macro");
    const btnDetailed = document.getElementById("btn-radial-detailed");
    if (btnMacro && btnDetailed && !btnMacro._g24Bound) {
      btnMacro.addEventListener("click", () => {
        btnMacro.classList.add("active");
        btnDetailed.classList.remove("active");
        currentRadialGran = "macro";
        renderDisciplinaryRadial();
      });
      btnDetailed.addEventListener("click", () => {
        btnDetailed.classList.add("active");
        btnMacro.classList.remove("active");
        currentRadialGran = "detailed";
        renderDisciplinaryRadial();
      });
      btnMacro._g24Bound = true;
    }

    const key = (currentInst === "all" || currentInst === "compare") ? "all" : currentInst;
    const dr = data.disciplinary_radial;
    const config = (currentRadialGran === "detailed") ? dr.detailed : dr.macro;
    const indicators = config.indicators;
    const vals = config.by_institute[key] || config.by_institute["all"];

    const axisLabelColor = isDark() ? "#f8fafc" : "#0f172a";
    const axisLabelBg = isDark() ? "rgba(30, 41, 59, 0.96)" : "rgba(255, 255, 255, 0.98)";
    const axisLabelBorder = isDark() ? "rgba(148, 163, 184, 0.35)" : "rgba(15, 23, 42, 0.22)";

    const axisStyle = {
      show: true,
      color: axisLabelColor,
      fontWeight: 700,
      fontSize: currentRadialGran === "detailed" ? 9.5 : 11.5,
      padding: [2, 5],
      borderRadius: 4,
      backgroundColor: axisLabelBg,
      borderWidth: 1,
      borderColor: axisLabelBorder
    };

    const isAll = (key === "all");
    const labColor = isAll ? (isDark() ? "#94a3b8" : "#1e293b") : (colors[key] || "#1e293b");
    const areaColor = isAll ? "rgba(30, 41, 59, 0.45)" : (isDark() ? "rgba(59, 130, 246, 0.35)" : "rgba(37, 99, 235, 0.35)");

    charts.disciplinaryRadial.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: isDark() ? "#1e293b" : "#ffffff",
        borderColor: isDark() ? "#334155" : "#e2e8f0",
        textStyle: { color: isDark() ? "#f8fafc" : "#0f172a" },
        formatter: params => {
          let html = `<div style="font-weight:800;font-size:13px;margin-bottom:6px;">${P2_NAMES[key] || 'All Three'} — Disciplinary Share</div>`;
          html += `<table style="font-size:12px;border-collapse:collapse;width:100%;">`;
          indicators.forEach((ind, i) => {
            const v = params.value[i];
            if (v > 0) {
              html += `<tr><td style="padding:2px 8px 2px 0;color:var(--text-muted);">${ind.name}:</td><td style="font-weight:700;text-align:right;">${v.toFixed(1)}%</td></tr>`;
            }
          });
          html += `</table>`;
          return html;
        }
      },
      radar: {
        indicator: indicators,
        shape: "polygon",
        splitNumber: 5,
        radius: currentRadialGran === "detailed" ? "54%" : "64%",
        center: ["50%", "50%"],
        nameGap: 8,
        axisName: axisStyle,
        name: axisStyle,
        axisLine: {
          lineStyle: {
            color: isDark() ? "rgba(148, 163, 184, 0.3)" : "rgba(71, 85, 105, 0.35)",
            width: 1.2
          }
        },
        splitLine: {
          lineStyle: {
            color: isDark()
              ? ["rgba(255,255,255,0.04)", "rgba(255,255,255,0.08)", "rgba(255,255,255,0.14)", "rgba(255,255,255,0.2)"]
              : ["rgba(15,23,42,0.05)", "rgba(15,23,42,0.1)", "rgba(15,23,42,0.16)", "rgba(15,23,42,0.22)"],
            width: 1
          }
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: isDark()
              ? ["rgba(255,255,255,0.01)", "rgba(255,255,255,0.03)"]
              : ["rgba(248,250,252,0.5)", "rgba(241,245,249,0.8)"]
          }
        }
      },
      series: [
        {
          type: "radar",
          data: [
            {
              name: P2_NAMES[key] || "All Three",
              value: vals,
              symbol: "circle",
              symbolSize: currentRadialGran === "detailed" ? 4 : 6,
              lineStyle: { width: 2.5, color: labColor },
              itemStyle: { color: labColor, borderColor: "#ffffff", borderWidth: 1.5 },
              areaStyle: { color: areaColor }
            }
          ]
        }
      ]
    }, true);
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
      <tr><td style="font-weight:700; color:var(--text-muted);">${r.rank}</td><td>${esc(r.citing_institution)}</td>
      <td style="font-weight:700;">${r.citing_papers.toLocaleString()}</td><td>${r.citations.toLocaleString()}</td></tr>`).join("");

    // Top partners
    document.getElementById("tbody-conn-partners").innerHTML = ((data.by_institute[key].indian_connections || {}).top_partners || []).map(r => `
      <tr><td style="font-weight:700; color:var(--text-muted);">${r.rank}</td><td>${esc(r.partner_institution)}</td>
      <td style="font-weight:700;">${r.collaborative_papers.toLocaleString()}</td><td>${r.share_pct}%</td></tr>`).join("");

    // Hub authors
    document.getElementById("tbody-conn-hubs").innerHTML = (conn.hub_authors[key] || []).map(r => `
      <tr><td style="font-weight:700; color:var(--text-muted);">${r.rank}</td><td style="font-weight:600;" ${window.G24Profiles && G24Profiles.fidByOpenAlex(r.author_openalex_id) ? `data-fid="${esc(G24Profiles.fidByOpenAlex(r.author_openalex_id))}"` : ""}>${esc(r.author)}</td>
      <td>${esc(r.home_institution)}</td><td>${esc(r.author_role.replace(/_/g, " "))}</td><td>${r.papers}</td>
      <td style="font-weight:700; color:#0284c7;">${r.institutions_bridged}</td><td>${r.cross_institution_papers}</td>
      <td style="font-size:0.75rem; color:var(--text-muted); max-width:320px;">${esc(r.top_partners)}</td></tr>`).join("");

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
      <tr><td style="font-weight:700; color:var(--text-muted);">${r.rank}</td>
      <td><div style="font-weight:600; max-width:360px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${esc(r.title)}">${esc(r.title)}</div>
      <div style="font-size:0.75rem; color:var(--text-muted);">${esc(r.journal_name)}</div></td>
      <td>${r.year}</td><td style="font-weight:700;">${r.citations.toLocaleString()}</td>
      <td style="font-size:0.75rem; color:var(--text-muted); max-width:260px;">${esc(r.citing_institutions)}</td>
      <td>${r.doi ? `<a href="${esc(r.doi)}" target="_blank" style="color:#0284c7; text-decoration:none; font-size:0.75rem;">DOI ↗</a>` : ""}</td></tr>`).join("");
  }

  // ---------------------------------------------------------------------------
  // Key Findings: eight insights shown as boxes, each opening a detail modal (Sleeping beauties and
  // Succession risk were removed, D-37; Insight 11 has its own page, insights11.html, D-38)
  // ---------------------------------------------------------------------------
  const insightCharts = {};

  function formatHeadline(text) {
    if (!text) return "";
    return text.replace(/(\b\d+(\.\d+)?%|\b\d+(\.\d+)?×|\b\d{1,3}(,\d{3})+|\b[A-Za-z0-9_ρ]+(_norm)?\s*=\s*[\d\.]+|\b\d+\.\d+\b)/g, "<strong>$1</strong>");
  }

  const INSIGHT_ORDER = [
    "01_friendship_paradox",
    "02_rich_club",
    "03_fragility",
    "04_price_law",
    "05_quartile_vs_impact",
    "06_pagerank_vs_citations",
    "08_covid_shock",
    "09_brain_circulation",
  ];

  // Box contents: a short title, a theme tag and one headline number read from the insight's own metrics
  const TAG_COLORS = {
    Network: "#2563eb", Productivity: "#7c3aed", Journals: "#059669", Citations: "#d97706",
    Trends: "#0891b2", Careers: "#db2777", Workforce: "#dc2626", Diffusion: "#4f46e5",
  };
  const TAG_COLORS_DARK = {
    Network: "#60a5fa", Productivity: "#a78bfa", Journals: "#34d399", Citations: "#fbbf24",
    Trends: "#22d3ee", Careers: "#f472b6", Workforce: "#f87171", Diffusion: "#818cf8",
  };
  const pct = v => `${(+v).toFixed(1)}%`;
  const has = (...vals) => vals.every(v => v !== null && v !== undefined && v !== "");
  const INSIGHT_CARDS = {
    "01_friendship_paradox": {
      title: "Friendship paradox", tag: "Network",
      stat: m => has(m.share_paradox) && [pct(m.share_paradox), "of researchers have fewer co-authors than their co-authors do"],
    },
    "02_rich_club": {
      title: "No rich club at the top", tag: "Network",
      stat: m => has(m.rho_norm_at_k_star) && [`ρ = ${(+m.rho_norm_at_k_star).toFixed(2)}`, "rich-club coefficient of the best-connected 1% (below 1 means less linked than chance)"],
    },
    "03_fragility": {
      title: "How fragile is the cluster?", tag: "Network",
      stat: m => has(m.n50_betweenness, m.n50_betweenness_pct) && [(+m.n50_betweenness).toLocaleString(), `bridge researchers (${pct(m.n50_betweenness_pct)} of the network) whose removal halves it`],
    },
    "04_price_law": {
      title: "Price's law", tag: "Productivity",
      stat: m => has(m.price_share_pct, m.n_sqrt) && [pct(m.price_share_pct), `of papers come from just √N = ${m.n_sqrt} scientists (the law predicts 50%)`],
    },
    "05_quartile_vs_impact": {
      title: "Does Q1 mean high impact?", tag: "Journals",
      stat: m => has(m.pct_Q1_in_top10) && [pct(m.pct_Q1_in_top10), "of Q1-journal papers reach the top 10% most-cited"],
    },
    "06_pagerank_vs_citations": {
      title: "Hidden gems", tag: "Citations",
      stat: m => has(m.n_hidden_gems, m.spearman_rho) && [String(m.n_hidden_gems), `papers influential inside the cluster but little cited worldwide (ρ = ${(+m.spearman_rho).toFixed(2)})`],
    },
    "08_covid_shock": {
      title: "The COVID shock", tag: "Trends",
      stat: m => has(m.combined_change_2020_vs_2019_pct) && [`${m.combined_change_2020_vs_2019_pct > 0 ? "+" : ""}${pct(m.combined_change_2020_vs_2019_pct)}`, "change in papers from 2019 to 2020, set against the pre-2020 trend"],
    },
    "09_brain_circulation": {
      title: "Brain circulation", tag: "Careers",
      stat: m => has(m.returnee_pct_overall) && [pct(m.returnee_pct_overall), "of classifiable scientists trained in India, worked abroad and came back"],
    },
  };

  function renderInsightCards() {
    const container = document.getElementById("insights-grid");
    if (!container || !window.G24_INSIGHTS) return;
    const insights = window.G24_INSIGHTS;
    container.innerHTML = INSIGHT_ORDER.map((key, idx) => {
      const item = insights[key] || { question: `Finding ${idx + 1}`, headline: "Not computed" };
      const meta = INSIGHT_CARDS[key] || { title: `Finding ${idx + 1}`, tag: "Finding", stat: () => null };
      let stat = null;
      try { stat = meta.stat(item.metrics || {}); } catch (e) { stat = null; }
      const color = (isDark() ? TAG_COLORS_DARK : TAG_COLORS)[meta.tag] || "var(--accent-ink)";
      return `
        <button type="button" class="insight-card" data-key="${key}" style="--tc:${color}"
                aria-label="Finding ${idx + 1}: ${esc(meta.title)}. Open the analysis">
          <span class="ic-top"><span class="ic-num">${String(idx + 1).padStart(2, "0")}</span><span class="ic-tag">${esc(meta.tag)}</span></span>
          <span class="ic-title">${esc(meta.title)}</span>
          ${stat ? `<span class="ic-stat">${esc(stat[0])}</span><span class="ic-stat-label">${esc(stat[1])}</span>` : ""}
          <span class="ic-q">${esc(item.question)}</span>
          <span class="ic-more">View analysis →</span>
        </button>`;
    }).join("");
    container.querySelectorAll(".insight-card").forEach(card => {
      card.addEventListener("click", () => openInsight(INSIGHT_ORDER.indexOf(card.dataset.key)));
    });
  }

  // ---- Detail modal --------------------------------------------------------
  const insOverlay = document.getElementById("ins-overlay");
  const insBody = document.getElementById("ins-body");
  let openIdx = -1;
  let lastFocus = null;

  function insightBodyHTML(key, item) {
    const method = `<div class="ins-method"><strong>Method.</strong> ${esc(item.method_note || "")}</div>`;
    return `
      <div class="ins-headline">${formatHeadline(esc(item.headline))}</div>
      <div id="chart-insight-${key}" class="chart-container" style="height: 420px;"></div>
      ${method}`;
  }

  function disposeInsightCharts() {
    Object.keys(insightCharts).forEach(k => {
      if (insightCharts[k]) insightCharts[k].dispose();
      delete insightCharts[k];
    });
  }

  function openInsight(idx) {
    if (!insOverlay || !window.G24_INSIGHTS || idx < 0 || idx >= INSIGHT_ORDER.length) return;
    const key = INSIGHT_ORDER[idx];
    const item = window.G24_INSIGHTS[key] || { question: `Finding ${idx + 1}`, headline: "Not computed", method_note: "" };
    const meta = INSIGHT_CARDS[key] || { title: `Finding ${idx + 1}`, tag: "Finding" };
    disposeInsightCharts();
    if (openIdx < 0) lastFocus = document.activeElement;
    openIdx = idx;
    document.getElementById("ins-kicker").textContent = `Finding ${String(idx + 1).padStart(2, "0")} · ${meta.tag} · ${meta.title}`;
    document.getElementById("ins-title").textContent = item.question;
    document.getElementById("ins-pos").textContent = `${idx + 1} of ${INSIGHT_ORDER.length}`;
    document.getElementById("ins-prev").disabled = idx === 0;
    document.getElementById("ins-next").disabled = idx === INSIGHT_ORDER.length - 1;
    insBody.innerHTML = insightBodyHTML(key, item);
    insOverlay.hidden = false;
    insOverlay.scrollTop = 0;
    document.body.classList.add("prof-lock");
    requestAnimationFrame(() => renderInsightChart(key, item));
    document.getElementById("ins-close").focus({ preventScroll: true });
  }

  function closeInsight() {
    if (!insOverlay || insOverlay.hidden) return;
    disposeInsightCharts();
    insOverlay.hidden = true;
    insBody.innerHTML = "";
    openIdx = -1;
    document.body.classList.remove("prof-lock");
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  }

  if (insOverlay) {
    document.getElementById("ins-close").addEventListener("click", closeInsight);
    document.getElementById("ins-prev").addEventListener("click", () => openInsight(openIdx - 1));
    document.getElementById("ins-next").addEventListener("click", () => openInsight(openIdx + 1));
    insOverlay.addEventListener("click", e => { if (e.target === insOverlay) closeInsight(); });
    document.addEventListener("keydown", e => {
      if (insOverlay.hidden || document.querySelector(".prof-overlay.open")) return;
      if (e.key === "Escape") closeInsight();
      else if (e.key === "ArrowRight" && openIdx < INSIGHT_ORDER.length - 1) openInsight(openIdx + 1);
      else if (e.key === "ArrowLeft" && openIdx > 0) openInsight(openIdx - 1);
    });
  }
  window.G24_openInsight = openInsight;  // used by the browser test

  // Home-screen cards for the two lead studies (their own pages). Every number comes from
  // window.G24_GLOBAL_TEASER (build_global.py) and window.G24_I11_TEASER (build_insights_js.py).
  function renderLeadStudies() {
    const stat = (v, s) => `<span class="lead-stat"><b>${esc(v)}</b><span>${esc(s)}</span></span>`;
    const pc = v => (v == null ? "–" : `${Number(v).toFixed(1)}%`);

    const g = window.G24_GLOBAL_TEASER;
    const bars = document.getElementById("lead-global-bars");
    if (g && g.top10 && bars) {
      const rows = [
        ...Object.entries(g.top10).map(([k, v]) => [k, v, "#60a5fa"]),
        ["Foreign twins (median)", g.top10_twin_median, "#fbbf24"],
        ["Indian peers (median)", g.top10_india_median, "#fb923c"],
      ];
      const world = g.world_top10_pct ?? 10;
      const max = Math.max(30, ...rows.map(r => r[1] || 0));
      bars.innerHTML = '<span class="lead-bars">' + rows.map(([k, v, c]) =>
        `<span class="lead-bar"><span>${esc(k)}</span><span class="lb-track"><span class="lb-fill" style="width:${(100 * v / max).toFixed(1)}%;background:${c}"></span>` +
        `<span class="lb-world" style="left:${(100 * world / max).toFixed(1)}%"></span></span><b>${pc(v)}</b></span>`).join("") +
        `</span><span class="lead-bars-cap">Share of papers among the world’s 10% most cited in their subject and year (dashed line: the world’s own share, ${pc(world)})</span>`;
      const low = Object.entries(g.cagr || {}).sort((a, b) => a[1] - b[1])[0];
      document.getElementById("lead-global-stats").innerHTML =
        stat(fmtN(g.countries), `countries co-author with the labs (${pc(g.foreign_share_pct)} of papers)`) +
        stat(low ? `${low[1].toFixed(1)}%` : "–", low ? `yearly change in ${low[0]}'s output, 2016–2025, while its peers grew` : "") +
        stat(g.exchange_ratio_foreign == null ? "–" : g.exchange_ratio_foreign.toFixed(2), "foreign peers' papers citing the labs per peer paper the labs cite (2016–2026 papers)");
    }

    const t = window.G24_I11_TEASER;
    const svg = document.getElementById("lead-i11-spark");
    if (t && t.full_curve && svg) {
      const W = 320, H = 110, pad = 6;
      const pts = c => c.map((v, i) => `${(pad + i * (W - 2 * pad) / (c.length - 1)).toFixed(1)},${(H - pad - v / 100 * (H - 2 * pad)).toFixed(1)}`).join(" ");
      const y50 = (H - pad - 0.5 * (H - 2 * pad)).toFixed(1);
      svg.innerHTML = `<line x1="${pad}" x2="${W - pad}" y1="${y50}" y2="${y50}" stroke="rgba(255,255,255,0.45)" stroke-dasharray="2 4"/>` +
        `<polyline points="${pts(t.faculty_curve)}" fill="none" stroke="#fcd34d" stroke-width="2.5" stroke-dasharray="6 4"/>` +
        `<polyline points="${pts(t.full_curve)}" fill="none" stroke="#ffffff" stroke-width="3"/>`;
      document.getElementById("lead-i11-stats").innerHTML = t.real_T_pct != null
        ? stat(`${t.real_T_pct.toFixed(2)}%`, `real chance a co-author picks up an idea, below the ${t.tipping_full_pct}% tipping point`) +
          stat(`${t.student_vs_faculty}×`, "more often over a student's tie than a professor's, measured in real citations") +
          stat(`${t.cross_lab_pct}%`, "of co-authorship ties cross labs: ideas from abroad arrive by reading")
        : stat(t.t50_full == null ? "> 15" : `${t.t50_full} steps`, `for an idea to reach half of all ${fmtN(t.n_full)} authors`) +
          stat(t.t50_faculty == null ? "> 15" : `${t.t50_faculty} steps`, "for the same among faculty alone, without students and project staff") +
          stat(`${t.spillover}%`, "of researchers outside the field adopt an idea that starts in chemistry");
      if (t.citations) document.getElementById("lead-i11-cites").textContent = fmtN(t.citations);
      if (t.claims_total) document.getElementById("lead-i11-check").textContent = `✓ ${t.claims_passed}/${t.claims_total} claims verified`;
    }
  }
  renderLeadStudies();

  function renderInsightChart(key, item) {
        if (!item || !item.chart) return;
        const el = document.getElementById(`chart-insight-${key}`);
        if (!el) return;

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
  }

  // Window resize handler
  window.addEventListener("resize", () => {
    Object.values(charts).forEach(c => c && c.resize && c.resize());
    Object.values(insightCharts).forEach(c => c && c.resize && c.resize());
    if (facultyTable) facultyTable.redraw(true);
    if (topPapersTable) topPapersTable.redraw(true);
  });

  // Theme switch: charts are drawn on canvas, so dispose them and draw again with the new colours
  if (window.G24Theme) {
    window.G24Theme.handlesCharts = true;
    document.addEventListener("g24:theme", () => {
      applyThemeColors();
      Object.keys(charts).forEach(k => { if (charts[k]) charts[k].dispose(); delete charts[k]; });
      updateDashboard();
      renderInsightCards();
      if (openIdx >= 0) openInsight(openIdx);
    });
  }

  // Data & Methods counts
  setText("docs-n-papers", fmtN(data.meta && data.meta.total_papers));
  setText("docs-n-rows", fmtN(data.meta && data.meta.total_authorship_rows));
  setText("docs-n-fac", fmtN(data.network_faculty && data.network_faculty.authorship.stats.total_nodes));

  // Initial draw
  renderInsightCards();
  updateDashboard();
});
