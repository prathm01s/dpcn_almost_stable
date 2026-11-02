/**
 * Controller for Study 2.1: Smart Specialization & Regional Economy.
 */

let radarChart = null;
let longChart = null;
let currentRadarMode = 'radar';
let currentInstFilter = 'ALL';

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_SMART_SPEC_DATA) {
    console.error("G24_SMART_SPEC_DATA not loaded!");
    return;
  }
  
  initRadarChart();
  initLongitudinalChart();
  renderCorporateTable();
  
  window.addEventListener("resize", () => {
    if (radarChart) radarChart.resize();
    if (longChart) longChart.resize();
  });
});

function toggleAudit() {
  const content = document.getElementById("audit-content");
  const icon = document.getElementById("audit-toggle-icon");
  if (content.style.display === "none") {
    content.style.display = "block";
    icon.textContent = "[− Click to Collapse]";
  } else {
    content.style.display = "none";
    icon.textContent = "[+ Click to Expand]";
  }
}

function initRadarChart() {
  const dom = document.getElementById("chart-radar");
  if (!dom) return;
  radarChart = echarts.init(dom);
  renderRadarView();
}

function switchRadarMode(mode) {
  currentRadarMode = mode;
  document.querySelectorAll(".chart-card:nth-of-type(1) .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.textContent.toLowerCase().includes(mode));
  });
  renderRadarView();
}

function renderRadarView() {
  const data = window.G24_SMART_SPEC_DATA;
  const rows = data.matched_synergies;
  
  if (currentRadarMode === 'radar') {
    const indicators = [
      { name: 'Medicinal & Organic (Pharma)\nIICT vs Telangana', max: 4.0 },
      { name: 'Polymers & Catalysis\nNCL vs Maharashtra', max: 4.0 },
      { name: 'Electrochem & Energy\nCECRI vs Tamil Nadu', max: 4.0 }
    ];
    
    const labRcas = [rows[0].lab_rca, rows[1].lab_rca, rows[2].lab_rca];
    const stateLqs = [rows[0].state_lq, rows[1].state_lq, rows[2].state_lq];
    
    const option = {
      tooltip: { trigger: 'item' },
      legend: {
        data: ['Scientific Lab RCA', 'Host State Industrial LQ', 'Baseline (Parity = 1.0)'],
        bottom: 10,
        textStyle: { color: '#334155', fontWeight: 600 }
      },
      radar: {
        indicator: indicators,
        radius: '65%',
        splitArea: { areaStyle: { color: ['#ffffff', '#f8fafc', '#f1f5f9'] } },
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        splitLine: { lineStyle: { color: '#e2e8f0' } },
        axisName: { color: '#0f172a', fontWeight: 600, fontSize: 13 }
      },
      series: [{
        type: 'radar',
        data: [
          {
            value: labRcas,
            name: 'Scientific Lab RCA',
            itemStyle: { color: '#2563eb' },
            areaStyle: { color: 'rgba(37, 99, 235, 0.25)' },
            symbolSize: 8
          },
          {
            value: stateLqs,
            name: 'Host State Industrial LQ',
            itemStyle: { color: '#d97706' },
            areaStyle: { color: 'rgba(217, 119, 6, 0.25)' },
            symbolSize: 8
          },
          {
            value: [1.0, 1.0, 1.0],
            name: 'Baseline (Parity = 1.0)',
            lineStyle: { type: 'dashed', color: '#94a3b8' },
            symbol: 'none'
          }
        ]
      }]
    };
    radarChart.setOption(option, true);
  } else {
    // Bar Comparison Mode
    const categories = ['CSIR-IICT (Pharma)', 'CSIR-NCL (Polymers/Catalysis)', 'CSIR-CECRI (Batteries)'];
    const labRcas = [rows[0].lab_rca, rows[1].lab_rca, rows[2].lab_rca];
    const stateLqs = [rows[0].state_lq, rows[1].state_lq, rows[2].state_lq];
    
    const option = {
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['Scientific Lab RCA', 'Host State Industrial LQ'], bottom: 10 },
      grid: { left: '8%', right: '5%', bottom: '15%', top: '10%' },
      xAxis: { type: 'category', data: categories, axisLabel: { fontWeight: 600, color: '#0f172a' } },
      yAxis: { type: 'value', name: 'Index Value (Parity = 1.0)', splitLine: { lineStyle: { color: '#f1f5f9' } } },
      series: [
        {
          name: 'Scientific Lab RCA',
          type: 'bar',
          data: labRcas,
          itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] },
          barWidth: '28%'
        },
        {
          name: 'Host State Industrial LQ',
          type: 'bar',
          data: stateLqs,
          itemStyle: { color: '#d97706', borderRadius: [4, 4, 0, 0] },
          barWidth: '28%'
        }
      ]
    };
    radarChart.setOption(option, true);
  }
}

function initLongitudinalChart() {
  const dom = document.getElementById("chart-longitudinal");
  if (!dom) return;
  longChart = echarts.init(dom);
  renderLongitudinal();
}

function filterLongitudinal(inst) {
  currentInstFilter = inst;
  document.querySelectorAll(".chart-card:nth-of-type(2) .pill-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  if (inst === 'ALL') document.getElementById("btn-inst-all").classList.add("active");
  if (inst === 'CSIR-IICT') document.getElementById("btn-inst-iict").classList.add("active");
  if (inst === 'CSIR-NCL') document.getElementById("btn-inst-ncl").classList.add("active");
  if (inst === 'CSIR-CECRI') document.getElementById("btn-inst-cecri").classList.add("active");
  renderLongitudinal();
}

function renderLongitudinal() {
  const data = window.G24_SMART_SPEC_DATA.yearly_evolution;
  const years = Array.from(new Set(data.map(d => d.year))).sort();
  const domains = [
    "Medicinal & Organic Synthesis",
    "Polymers, Catalysis & Specialty Materials",
    "Electrochemistry & Energy Storage"
  ];
  
  const seriesList = [];
  const colors = ['#2563eb', '#059669', '#7c3aed'];
  
  domains.forEach((domName, idx) => {
    const yearCounts = years.map(y => {
      let filtered = data.filter(d => d.year === y && d.macro_domain === domName);
      if (currentInstFilter !== 'ALL') {
        filtered = filtered.filter(d => d.institution === currentInstFilter);
      }
      return filtered.reduce((acc, curr) => acc + curr.papers, 0);
    });
    
    seriesList.push({
      name: domName,
      type: 'line',
      smooth: true,
      data: yearCounts,
      itemStyle: { color: colors[idx] },
      lineStyle: { width: 3 },
      symbolSize: 6
    });
  });
  
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: domains, bottom: 10, textStyle: { color: '#334155' } },
    grid: { left: '6%', right: '5%', bottom: '15%', top: '10%' },
    xAxis: { type: 'category', data: years, axisLabel: { color: '#0f172a' } },
    yAxis: { type: 'value', name: 'Annual Publications', splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: seriesList
  };
  
  longChart.setOption(option, true);
}

function renderCorporateTable() {
  const corps = window.G24_SMART_SPEC_DATA.corporate_collaborations;
  const tbody = document.getElementById("corporate-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  const sectorMap = {
    "Reliance Industries": { sector: "Specialty Chemicals & Polymers", lab: "CSIR-NCL", impact: "Catalytic zeolites & polymer process scaling" },
    "Dr. Reddy's Laboratories": { sector: "Pharmaceutical APIs", lab: "CSIR-IICT", impact: "Continuous-flow synthesis of active ingredients" },
    "Cipla": { sector: "Pharmaceuticals", lab: "CSIR-IICT", impact: "Cost-effective antiretroviral & respiratory drug synthesis" },
    "Tata Steel": { sector: "Materials & Coatings", lab: "CSIR-NCL / CECRI", impact: "Electrochemical anti-corrosion & high-strength alloys" },
    "Bharat Biotech": { sector: "Vaccines & Biologics", lab: "CSIR-IICT", impact: "Adjuvant synthesis for indigenous vaccines" },
    "GVK": { sector: "Discovery Chemistry", lab: "CSIR-IICT", impact: "Novel heterocyclic screening libraries" },
    "Piramal": { sector: "Custom Synthesis", lab: "CSIR-IICT / NCL", impact: "Scalable chiral catalyst screening" },
    "Lupin Pharmaceuticals": { sector: "Generic Formulations", lab: "CSIR-IICT", impact: "Process route patenting & impurity removal" }
  };
  
  corps.forEach(c => {
    const pName = c.corporate_partner;
    let matched = null;
    for (let k in sectorMap) {
      if (pName.toLowerCase().includes(k.toLowerCase())) {
        matched = sectorMap[k];
        break;
      }
    }
    
    if (matched) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="highlight">${pName}</td>
        <td><span class="badge-pill badge-blue">${matched.sector}</span></td>
        <td><strong>${c.coauthored_papers}</strong> papers</td>
        <td><span class="badge-pill badge-purple">${matched.lab}</span></td>
        <td>${matched.impact}</td>
      `;
      tbody.appendChild(tr);
    }
  });
}
