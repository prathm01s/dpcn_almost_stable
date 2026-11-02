/**
 * Controller for Study 5.1: Scientific Frugal Innovation & Macro GERD.
 */

let costChart = null;
let gerdChart = null;
let currentCostMode = 'nominal';

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_FRUGAL_RD_DATA) {
    console.error("G24_FRUGAL_RD_DATA not loaded!");
    return;
  }
  
  initCostChart();
  initGerdChart();
  renderLabFinTable();
  
  window.addEventListener("resize", () => {
    if (costChart) costChart.resize();
    if (gerdChart) gerdChart.resize();
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

function initCostChart() {
  const dom = document.getElementById("chart-cost-q1");
  if (!dom) return;
  costChart = echarts.init(dom);
  renderCostView();
}

function switchCostMode(mode) {
  currentCostMode = mode;
  document.getElementById("btn-cost-nominal").classList.toggle("active", mode === 'nominal');
  document.getElementById("btn-cost-ppp").classList.toggle("active", mode === 'ppp');
  renderCostView();
}

function renderCostView() {
  const benchmarks = window.G24_FRUGAL_RD_DATA.global_benchmarks;
  const names = benchmarks.map(d => `${d.organization} (${d.country})`);
  const values = benchmarks.map(d => currentCostMode === 'nominal' ? d.cost_per_q1_nominal_usd : d.cost_per_q1_ppp_usd);
  
  const colors = benchmarks.map(d => d.country === 'India' ? '#059669' : '#2563eb');
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = benchmarks[params[0].dataIndex];
        const val = currentCostMode === 'nominal' ? item.cost_per_q1_nominal_usd : item.cost_per_q1_ppp_usd;
        return `<strong>${item.organization}</strong><br/>
                Country: ${item.country}<br/>
                Annual Budget: $${item.annual_budget_usd_m}M USD<br/>
                Annual Q1 Papers: ${item.annual_q1_papers}<br/>
                Cost per Q1 (${currentCostMode.toUpperCase()}): <strong>$${val.toLocaleString()} USD</strong><br/>
                Cost per Citation: $${item.cost_per_citation_usd} USD`;
      }
    },
    grid: { left: '30%', right: '8%', top: '8%', bottom: '10%' },
    xAxis: {
      type: 'value',
      name: `Cost per Q1 Paper (${currentCostMode.toUpperCase()} USD)`,
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { formatter: (v) => `$${v / 1000}k` }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontWeight: 600, color: '#0f172a', fontSize: 11 }
    },
    series: [
      {
        type: 'bar',
        data: values.map((v, i) => ({
          value: v,
          itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] }
        })),
        barWidth: '45%'
      }
    ]
  };
  
  costChart.setOption(option, true);
}

function initGerdChart() {
  const dom = document.getElementById("chart-gerd");
  if (!dom) return;
  gerdChart = echarts.init(dom);
  
  const benchmarks = window.G24_FRUGAL_RD_DATA.global_benchmarks;
  const names = benchmarks.map(d => d.country);
  const gerdValues = benchmarks.map(d => d.gerd_gdp_pct);
  const q1Papers = benchmarks.map(d => d.annual_q1_papers);
  
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['National GERD (% of GDP)', 'Annual Q1 Papers Produced'], bottom: 10 },
    grid: { left: '8%', right: '8%', top: '12%', bottom: '15%' },
    xAxis: { type: 'category', data: names, axisLabel: { fontWeight: 600, color: '#0f172a' } },
    yAxis: [
      { type: 'value', name: 'GERD (% of GDP)', min: 0, max: 4.0, splitLine: { lineStyle: { color: '#f1f5f9' } } },
      { type: 'value', name: 'Annual Q1 Publications', splitLine: { show: false } }
    ],
    series: [
      {
        name: 'National GERD (% of GDP)',
        type: 'bar',
        data: gerdValues,
        itemStyle: { color: '#d97706', borderRadius: [4, 4, 0, 0] },
        barWidth: '28%'
      },
      {
        name: 'Annual Q1 Papers Produced',
        type: 'line',
        yAxisIndex: 1,
        data: q1Papers,
        itemStyle: { color: '#2563eb' },
        lineStyle: { width: 3 },
        symbolSize: 8
      }
    ]
  };
  
  gerdChart.setOption(option, true);
}

function renderLabFinTable() {
  const labs = window.G24_FRUGAL_RD_DATA.lab_financials;
  const tbody = document.getElementById("lab-fin-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  labs.forEach(lab => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="highlight">${lab.institution}</td>
      <td>₹${lab.annual_grant_in_aid_cr.toFixed(1)} Cr</td>
      <td>$${lab.annual_budget_usd_m.toFixed(2)}M</td>
      <td><strong>${lab.annual_q1_papers}</strong> papers/yr</td>
      <td style="color: #059669; font-weight: 600;">$${lab.cost_per_q1_nominal_usd.toLocaleString()}</td>
      <td style="color: #2563eb; font-weight: 600;">$${lab.cost_per_q1_ppp_usd.toLocaleString()}</td>
      <td><strong>$${lab.cost_per_citation_usd.toFixed(2)}</strong></td>
    `;
    tbody.appendChild(tr);
  });
}
