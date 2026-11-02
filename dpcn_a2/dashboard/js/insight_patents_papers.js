/**
 * Controller for Study 5.2: Patent-to-Paper Decoupling.
 */

let quadrantChart = null;
let labPatChart = null;
let currentScatterAxis = 'h_index';

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_PATENTS_PAPERS_DATA) {
    console.error("G24_PATENTS_PAPERS_DATA not loaded!");
    return;
  }
  
  initQuadrantChart();
  initLabPatentChart();
  renderTransfersTable();
  
  window.addEventListener("resize", () => {
    if (quadrantChart) quadrantChart.resize();
    if (labPatChart) labPatChart.resize();
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

function initQuadrantChart() {
  const dom = document.getElementById("chart-quadrant");
  if (!dom) return;
  quadrantChart = echarts.init(dom);
  renderQuadrantView();
}

function switchScatterAxis(axis) {
  currentScatterAxis = axis;
  document.getElementById("btn-axis-hindex").classList.toggle("active", axis === 'h_index');
  document.getElementById("btn-axis-citations").classList.toggle("active", axis === 'citations');
  renderQuadrantView();
}

function renderQuadrantView() {
  const faculty = window.G24_PATENTS_PAPERS_DATA.faculty_scatter;
  
  // Quadrant colors
  const colorMap = {
    "Applied Process Pioneer (High Patent / Low Citation)": "#d97706",
    "Dual-Impact Star (High Patent / High Citation)": "#059669",
    "Theoretical & Basic Chemist (Low Patent / High Citation)": "#2563eb",
    "Emerging / Specialized Faculty (Low Patent / Low Citation)": "#94a3b8"
  };
  
  const seriesByQuadrant = {};
  for (let q in colorMap) {
    seriesByQuadrant[q] = [];
  }
  
  faculty.forEach(f => {
    const xVal = currentScatterAxis === 'h_index' ? f.h_index_corpus : f.n_citations_corpus;
    const yVal = f.patents_total;
    if (seriesByQuadrant[f.quadrant]) {
      seriesByQuadrant[f.quadrant].push([xVal, yVal, f.full_name, f.inst_key, f.designation, f.department, f.n_papers_corpus, f.n_citations_corpus, f.h_index_corpus]);
    }
  });
  
  const seriesList = [];
  for (let q in colorMap) {
    seriesList.push({
      name: q,
      type: 'scatter',
      data: seriesByQuadrant[q],
      itemStyle: { color: colorMap[q], opacity: 0.8 },
      symbolSize: 9
    });
  }
  
  const option = {
    tooltip: {
      formatter: (param) => {
        const d = param.value;
        return `<strong>${d[2]}</strong> (${d[3]})<br/>
                ${d[4]} — ${d[5]}<br/>
                Patents Total: <strong>${d[1]}</strong><br/>
                H-Index: <strong>${d[8]}</strong><br/>
                Corpus Papers: ${d[6]} | Citations: ${d[7].toLocaleString()}<br/>
                <em>${param.seriesName}</em>`;
      }
    },
    legend: {
      orient: 'horizontal',
      bottom: 10,
      textStyle: { color: '#334155', fontSize: 11 }
    },
    grid: { left: '8%', right: '8%', top: '8%', bottom: '15%' },
    xAxis: {
      type: currentScatterAxis === 'h_index' ? 'value' : 'log',
      name: currentScatterAxis === 'h_index' ? 'Academic H-Index' : 'Academic Citations (Log Scale)',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    yAxis: {
      type: 'value',
      name: 'Industrial Patents Filed',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series: seriesList
  };
  
  quadrantChart.setOption(option, true);
}

function initLabPatentChart() {
  const dom = document.getElementById("chart-lab-patents");
  if (!dom) return;
  labPatChart = echarts.init(dom);
  
  const labs = window.G24_PATENTS_PAPERS_DATA.lab_patent_totals;
  const categories = labs.map(d => `${d.institution} (${d.city})`);
  const domestic = labs.map(d => d.domestic_ipo_filed);
  const foreign = labs.map(d => d.foreign_pct_filed);
  const granted = labs.map(d => d.patents_granted);
  const licenses = labs.map(d => d.commercial_licenses);
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      data: ['Domestic IPO Filed', 'Foreign PCT/US Filed', 'Patents Granted', 'Commercial Licenses'],
      bottom: 10
    },
    grid: { left: '8%', right: '5%', top: '10%', bottom: '15%' },
    xAxis: { type: 'category', data: categories, axisLabel: { fontWeight: 600, color: '#0f172a' } },
    yAxis: { type: 'value', name: 'Patent Asset Count', splitLine: { lineStyle: { color: '#f1f5f9' } } },
    series: [
      {
        name: 'Domestic IPO Filed',
        type: 'bar',
        stack: 'filed',
        data: domestic,
        itemStyle: { color: '#2563eb' }
      },
      {
        name: 'Foreign PCT/US Filed',
        type: 'bar',
        stack: 'filed',
        data: foreign,
        itemStyle: { color: '#0891b2' }
      },
      {
        name: 'Patents Granted',
        type: 'bar',
        data: granted,
        itemStyle: { color: '#059669', borderRadius: [4, 4, 0, 0] }
      },
      {
        name: 'Commercial Licenses',
        type: 'bar',
        data: licenses,
        itemStyle: { color: '#d97706', borderRadius: [4, 4, 0, 0] }
      }
    ]
  };
  
  labPatChart.setOption(option, true);
}

function renderTransfersTable() {
  const transfers = window.G24_PATENTS_PAPERS_DATA.marquee_tech_transfers;
  const tbody = document.getElementById("transfers-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  transfers.forEach(t => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="badge-pill badge-purple">${t.lab}</span></td>
      <td class="highlight">${t.technology}</td>
      <td><strong>${t.industry_partner}</strong></td>
      <td>${t.impact}</td>
    `;
    tbody.appendChild(tr);
  });
}
