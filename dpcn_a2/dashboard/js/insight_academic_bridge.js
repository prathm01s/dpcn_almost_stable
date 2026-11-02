/**
 * Controller for Study 1.1: The Academic-Industrial Bridge.
 */

let kerChart = null;
let flowChart = null;
let currentTierFilter = 'ALL';

document.addEventListener("DOMContentLoaded", () => {
  if (!window.G24_ACADEMIC_BRIDGE_DATA) {
    console.error("G24_ACADEMIC_BRIDGE_DATA not loaded!");
    return;
  }
  
  bindBridgeNumbers();
  initKerChart();
  initFlowChart();
  renderBridgeTable();
  
  window.addEventListener("resize", () => {
    if (kerChart) kerChart.resize();
    if (flowChart) flowChart.resize();
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

function initKerChart() {
  const dom = document.getElementById("chart-ker");
  if (!dom) return;
  kerChart = echarts.init(dom);
  renderKerView();
}

function filterTier(tier) {
  currentTierFilter = tier;
  document.querySelectorAll(".chart-card:nth-of-type(1) .pill-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  if (tier === 'ALL') document.getElementById("btn-tier-all").classList.add("active");
  if (tier === 'Tier 1') document.getElementById("btn-tier-1").classList.add("active");
  if (tier === 'Tier 2') document.getElementById("btn-tier-2").classList.add("active");
  renderKerView();
}

function renderKerView() {
  let list = window.G24_ACADEMIC_BRIDGE_DATA.institutions_evaluated;
  if (currentTierFilter !== 'ALL') {
    list = list.filter(d => d.tier.includes(currentTierFilter));
  }
  
  // Sort by KER descending
  list = list.slice().sort((a, b) => a.ker - b.ker);
  
  const names = list.map(d => d.academic_institution);
  const kers = list.map(d => d.ker);
  const colors = list.map(d => d.ker >= 1.0 ? '#059669' : '#2563eb');
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = list[params[0].dataIndex];
        return `<strong>${item.full_name}</strong><br/>
                Tier: ${item.tier}<br/>
                K_ER Ratio: <strong>${item.ker}×</strong><br/>
                Role: <strong>${item.exchange_role}</strong><br/>
                Received from HEI: ${item.c_in_received_from_hei} citations<br/>
                Sent to HEI: ${item.c_out_sent_to_hei} citations<br/>
                Net Delta: ${item.net_citation_delta >= 0 ? '+' : ''}${item.net_citation_delta}`;
      }
    },
    grid: { left: '22%', right: '8%', top: '8%', bottom: '10%' },
    xAxis: {
      type: 'value',
      name: 'Knowledge Exchange Ratio (K_ER)',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontWeight: 600, color: '#0f172a', fontSize: 11 }
    },
    series: [
      {
        type: 'bar',
        data: kers.map((val, idx) => ({
          value: val,
          itemStyle: { color: colors[idx], borderRadius: [0, 4, 4, 0] }
        })),
        barWidth: '55%',
        markLine: {
          data: [{ xAxis: 1.0, label: { formatter: 'Parity (1.0)', position: 'end' } }],
          lineStyle: { type: 'dashed', color: '#dc2626', width: 2 }
        }
      }
    ]
  };
  
  kerChart.setOption(option, true);
}

function initFlowChart() {
  const dom = document.getElementById("chart-flows");
  if (!dom) return;
  flowChart = echarts.init(dom);
  
  const list = window.G24_ACADEMIC_BRIDGE_DATA.institutions_evaluated;
  const scatterData = list.map(d => [d.c_out_sent_to_hei, d.c_in_received_from_hei, d.academic_institution, d.tier, d.ker]);
  
  const option = {
    tooltip: {
      formatter: (param) => {
        const val = param.value;
        return `<strong>${val[2]}</strong><br/>
                Sent to HEI: ${val[0]}<br/>
                Received from HEI: ${val[1]}<br/>
                K_ER: ${val[4]}×`;
      }
    },
    grid: { left: '8%', right: '8%', top: '10%', bottom: '12%' },
    xAxis: {
      type: 'value',
      name: 'Citations Sent by CSIR (C_out)',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    yAxis: {
      type: 'value',
      name: 'Citations Received from HEI (C_in)',
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series: [
      {
        type: 'scatter',
        symbolSize: (data) => Math.max(12, Math.min(32, data[4] * 12)),
        data: scatterData,
        itemStyle: {
          color: (param) => param.value[3].includes("Tier 1") ? '#2563eb' : '#059669',
          opacity: 0.85
        },
        markLine: {
          data: [
            [
              { coord: [0, 0], symbol: 'none' },
              { coord: [3200, 3200], symbol: 'none' }
            ]
          ],
          lineStyle: { type: 'dashed', color: '#94a3b8' },
          label: { formatter: 'Equal Exchange Diagonal', position: 'middle' }
        }
      }
    ]
  };
  
  flowChart.setOption(option, true);
}

function renderBridgeTable() {
  const list = window.G24_ACADEMIC_BRIDGE_DATA.institutions_evaluated;
  const tbody = document.getElementById("bridge-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";
  
  list.forEach(item => {
    const tr = document.createElement("tr");
    const roleBadge = item.ker >= 1.0 ? 'badge-green' : 'badge-blue';
    const deltaBadge = item.net_citation_delta >= 0 ? '#059669' : '#dc2626';
    const tierBadge = item.tier.includes("Tier 1") ? 'badge-purple' : 'badge-amber';
    
    tr.innerHTML = `
      <td class="highlight">${item.academic_institution}</td>
      <td><span class="badge-pill ${tierBadge}">${item.tier.includes("Tier 1") ? 'Tier 1 Flagship' : 'Tier 2 State Univ'}</span></td>
      <td><strong>${item.c_in_received_from_hei.toLocaleString()}</strong></td>
      <td>${item.c_out_sent_to_hei.toLocaleString()}</td>
      <td><strong style="color: ${item.ker >= 1.0 ? '#059669' : '#2563eb'}">${item.ker}×</strong></td>
      <td style="color: ${deltaBadge}; font-weight: 600;">${item.net_citation_delta >= 0 ? '+' : ''}${item.net_citation_delta.toLocaleString()}</td>
      <td><span class="badge-pill ${roleBadge}">${item.exchange_role}</span></td>
      <td>${item.coauthored_papers > 0 ? item.coauthored_papers + ' papers' : '—'}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Numbers in the headline cards and explanations come from the data bundle (D-33)
function bindBridgeNumbers() {
  const D = window.G24_ACADEMIC_BRIDGE_DATA;
  const rows = (D.institutions_evaluated || []).slice();
  const f = n => Number(n || 0).toLocaleString();
  const set = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
  const total = rows.reduce((a, r) => a + r.c_in_received_from_hei + r.c_out_sent_to_hei, 0);
  set("ab-k1", f(total));
  set("ab-k1s", `Citations between the three labs' papers and the ${rows.length} institutions, both directions.`);
  set("ab-lead-n", `In total, ${f(total)} such citation links.`);
  const ok = rows.filter(r => r.c_out_sent_to_hei > 0 && r.c_in_received_from_hei > 0);
  const byKer = ok.slice().sort((a, b) => b.ker - a.ker);
  const hi = byKer[0], lo = byKer[byKer.length - 1];
  const net = rows.slice().sort((a, b) => b.net_citation_delta - a.net_citation_delta)[0];
  if (hi) { set("ab-k2", `${hi.ker.toFixed(2)}×`); set("ab-k2s", `<b>${hi.academic_institution}</b> cites the labs ${f(hi.c_in_received_from_hei)} times; the labs cite it ${f(hi.c_out_sent_to_hei)} times.`); }
  if (lo) { set("ab-k3", `${lo.ker.toFixed(2)}×`); set("ab-k3s", `The labs cite <b>${lo.academic_institution}</b> ${f(lo.c_out_sent_to_hei)} times; it cites the labs ${f(lo.c_in_received_from_hei)} times.`); }
  if (net) { set("ab-k4", `${net.net_citation_delta >= 0 ? "+" : ""}${f(net.net_citation_delta)}`); set("ab-k4s", `Citations received from <b>${net.academic_institution}</b> minus citations given to it (K<sub>ER</sub> ${net.ker.toFixed(2)}).`); }
  const exp = byKer.filter(r => r.ker >= 1), imp = byKer.filter(r => r.ker < 1);
  set("ab-interp-ker",
    `K<sub>ER</sub> above 1 means the institution cites the labs more than the labs cite it. ` +
    `${exp.length} of ${ok.length} institutions are above 1` + (exp.length ? ` (highest: ${exp.slice(0, 3).map(r => `${r.academic_institution} ${r.ker.toFixed(2)}`).join(", ")})` : "") + `; ` +
    `${imp.length} are below 1` + (imp.length ? ` (lowest: ${imp.slice(-3).reverse().map(r => `${r.academic_institution} ${r.ker.toFixed(2)}`).join(", ")})` : "") + `. ` +
    `The ratio describes citation direction only; it does not show why researchers cite each other.`);
  const big = rows.slice().sort((a, b) => (b.c_in_received_from_hei + b.c_out_sent_to_hei) - (a.c_in_received_from_hei + a.c_out_sent_to_hei))[0];
  set("ab-interp-flow",
    `Points near the diagonal exchange about as many citations in each direction as they receive. ` +
    (big ? `The largest exchange is with ${big.academic_institution}: ${f(big.c_out_sent_to_hei)} citations from the labs and ${f(big.c_in_received_from_hei)} to the labs. ` : "") +
    `Counts are citation links (a lab-paper pair counted once per lab), not distinct papers.`);
}
