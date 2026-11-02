/**
 * Controller for Study 3.1: Global Leiden Crown Indicators.
 */

let leidenCompChart = null;
let subfieldChart = null;
let currentLeidenMetric = 'pp10';

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_LEIDEN_BENCHMARKS_DATA) {
    console.error("G24_LEIDEN_BENCHMARKS_DATA not loaded!");
    return;
  }
  
  initLeidenCompChart();
  initSubfieldChart();
  renderLeidenTable();
  
  window.addEventListener("resize", () => {
    if (leidenCompChart) leidenCompChart.resize();
    if (subfieldChart) subfieldChart.resize();
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

function initLeidenCompChart() {
  const dom = document.getElementById("chart-leiden-comp");
  if (!dom) return;
  leidenCompChart = echarts.init(dom);
  renderLeidenCompView();
}

function switchLeidenMetric(metric) {
  currentLeidenMetric = metric;
  document.getElementById("btn-metric-pp10").classList.toggle("active", metric === 'pp10');
  document.getElementById("btn-metric-mncs").classList.toggle("active", metric === 'mncs');
  renderLeidenCompView();
}

function renderLeidenCompView() {
  const data = window.G24_LEIDEN_BENCHMARKS_DATA;
  const list = [...data.global_benchmarks, ...data.lab_results, data.cluster_consolidated];
  
  // Sort descending by chosen metric
  const sorted = list.slice().sort((a, b) => {
    return currentLeidenMetric === 'pp10' ? a.pp_top10_pct - b.pp_top10_pct : a.mncs - b.mncs;
  });
  
  const names = sorted.map(d => `${d.institution} (${d.country})`);
  const values = sorted.map(d => currentLeidenMetric === 'pp10' ? d.pp_top10_pct : d.mncs);
  
  const colors = sorted.map(d => {
    if (d.institution.includes("Cluster")) return '#059669';
    if (d.country === 'India') return '#2563eb';
    return '#94a3b8';
  });
  
  const baseline = currentLeidenMetric === 'pp10' ? 10.0 : 1.0;
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = sorted[params[0].dataIndex];
        return `<strong>${item.institution}</strong> (${item.country})<br/>
                Type: ${item.type}<br/>
                PP(top 10%): <strong>${item.pp_top10_pct}%</strong><br/>
                PP(top 1%): <strong>${item.pp_top1_pct}%</strong><br/>
                MNCS Score: <strong>${item.mncs}</strong><br/>
                Evaluated Papers: ${item.total_papers_evaluated.toLocaleString()}`;
      }
    },
    grid: { left: '32%', right: '8%', top: '8%', bottom: '10%' },
    xAxis: {
      type: 'value',
      name: currentLeidenMetric === 'pp10' ? 'PP(top 10%) Share (%)' : 'Mean Normalized Citation Score (MNCS)',
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { formatter: (v) => currentLeidenMetric === 'pp10' ? `${v}%` : v }
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
        barWidth: '45%',
        markLine: {
          data: [{ xAxis: baseline, label: { formatter: `World Avg (${baseline})`, position: 'end' } }],
          lineStyle: { type: 'dashed', color: '#dc2626', width: 2 }
        }
      }
    ]
  };
  
  leidenCompChart.setOption(option, true);
}

function initSubfieldChart() {
  const dom = document.getElementById("chart-subfield");
  if (!dom) return;
  subfieldChart = echarts.init(dom);
  
  const subfields = window.G24_LEIDEN_BENCHMARKS_DATA.subfield_breakdown;
  const names = subfields.map(d => d.subfield);
  const pp10 = subfields.map(d => d.pp_top10_pct);
  const pp1 = subfields.map(d => d.pp_top1_pct);
  
  const option = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['PP(top 10%) Share', 'PP(top 1%) Crown Jewel Share'], bottom: 10 },
    grid: { left: '26%', right: '8%', top: '8%', bottom: '12%' },
    xAxis: {
      type: 'value',
      name: 'Percentage of Publications (%)',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontWeight: 600, color: '#0f172a', fontSize: 11 }
    },
    series: [
      {
        name: 'PP(top 10%) Share',
        type: 'bar',
        data: pp10,
        itemStyle: { color: '#2563eb', borderRadius: [0, 4, 4, 0] },
        barWidth: '35%'
      },
      {
        name: 'PP(top 1%) Crown Jewel Share',
        type: 'bar',
        data: pp1,
        itemStyle: { color: '#7c3aed', borderRadius: [0, 4, 4, 0] },
        barWidth: '35%'
      }
    ]
  };
  
  subfieldChart.setOption(option, true);
}

function renderLeidenTable() {
  const data = window.G24_LEIDEN_BENCHMARKS_DATA;
  const list = [...data.global_benchmarks, ...data.lab_results, data.cluster_consolidated];
  const tbody = document.getElementById("leiden-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  list.forEach(item => {
    const tr = document.createElement("tr");
    const mncsColor = item.mncs >= 1.0 ? '#059669' : '#d97706';
    const pp10Color = item.pp_top10_pct >= 10.0 ? '#059669' : '#dc2626';
    
    tr.innerHTML = `
      <td class="highlight">${item.institution}</td>
      <td>${item.country}</td>
      <td><span class="badge-pill badge-blue">${item.type}</span></td>
      <td><strong>${item.total_papers_evaluated.toLocaleString()}</strong></td>
      <td style="color: ${pp10Color}; font-weight: 700;">${item.pp_top10_pct}%</td>
      <td style="color: #7c3aed; font-weight: 600;">${item.pp_top1_pct}%</td>
      <td style="color: ${mncsColor}; font-weight: 700;">${item.mncs}</td>
      <td>${item.q1_journal_share_pct ? item.q1_journal_share_pct + '%' : '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}
