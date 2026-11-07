/**
 * Global Benchmark page (global.html). Data: window.G24_GLOBAL from data/g24_global.js, built by
 * src/dashboard/build_global.py from stats/tables/global_*.csv. Every number and every sentence in
 * the insight boxes is computed here from that payload; nothing is typed in by hand.
 */
(function () {
  "use strict";
  const D = window.G24_GLOBAL;
  if (!D) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      '<p style="padding:2rem">Benchmark data not found (data/g24_global.js). Run <code>python run.py global</code>.</p>');
    return;
  }

  // ---------- helpers ----------
  const $ = id => document.getElementById(id);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const ink = () => (window.G24Theme ? window.G24Theme.ink() : { text: "#1e293b", text2: "#475569", muted: "#64748b", split: "#e2e8f0" });
  const LABS = ["CSIR-NCL", "CSIR-IICT", "CSIR-CECRI"];
  const GROUPS = ["CSIR lab", "India", "USA", "China", "South Korea", "Australia"];
  const GROUP_VAR = { "CSIR lab": "--g-csir", "India": "--g-india", "USA": "--g-usa", "China": "--g-china", "South Korea": "--g-korea", "Australia": "--g-australia" };
  const GROUP_LABEL = { "CSIR lab": "CSIR labs", "India": "India (reference)", "USA": "USA", "China": "China", "South Korea": "South Korea", "Australia": "Australia" };
  const CC_GROUP = { US: "USA", CN: "China", KR: "South Korea", AU: "Australia", IN: "India" };
  const gc = g => css(GROUP_VAR[g] || "--g-other");
  const fmt = n => (n == null || Number.isNaN(n) ? "–" : Number(n).toLocaleString("en-US"));
  const pct = (v, d = 1) => (v == null || Number.isNaN(v) ? "–" : `${Number(v).toFixed(d)}%`);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let regionNames = null;
  try { regionNames = new Intl.DisplayNames(["en"], { type: "region" }); } catch (e) { /* old browser */ }
  const cname = cc => { try { return (regionNames && regionNames.of(cc)) || cc; } catch (e) { return cc; } };
  const median = a => { const s = a.filter(x => x != null).sort((x, y) => x - y); if (!s.length) return null; const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

  const peers = D.peers;
  const peerById = Object.fromEntries(peers.map(p => [p.institution_id, p]));
  const sumById = Object.fromEntries(D.summary.map(s => [s.institution_id, s]));
  const labRow = name => peers.find(p => p.group === "CSIR lab" && p.name === name);
  const foreign = peers.filter(p => !["CSIR lab", "India"].includes(p.group));
  const y0 = D.meta.years.start, y1 = D.meta.years.end;

  const charts = [];
  function chart(id, option) {
    const el = $(id);
    let c = echarts.getInstanceByDom(el);
    if (!c) { c = echarts.init(el); charts.push(c); }
    c.setOption(option, true);
    return c;
  }
  window.addEventListener("resize", () => charts.forEach(c => c.resize()));

  function axisCommon() {
    const k = ink();
    return {
      axisLabel: { color: k.text2 }, axisLine: { lineStyle: { color: k.split } },
      splitLine: { lineStyle: { color: k.split } }, nameTextStyle: { color: k.muted },
    };
  }
  function tooltipBase() {
    const k = ink();
    return { confine: true, backgroundColor: css("--surface"), borderColor: css("--border-strong"), textStyle: { color: k.text } };
  }
  function legendHTML(groups) {
    return '<div class="g-legend" style="display:flex;flex-wrap:wrap;gap:.9rem;font-size:.8rem;color:var(--text-2);margin:.25rem 0 .5rem">' +
      groups.map(g => `<span style="display:inline-flex;align-items:center;gap:.35rem"><span class="g-swatch" style="background:${gc(g)}"></span>${esc(GROUP_LABEL[g])}</span>`).join("") + "</div>";
  }
  function addLegend(chartId, groups) {
    const el = $(chartId);
    if (el.previousElementSibling && el.previousElementSibling.classList.contains("g-legend")) el.previousElementSibling.remove();
    el.insertAdjacentHTML("beforebegin", legendHTML(groups));
  }
  function seg(id, items, active, onPick) {
    const box = $(id);
    box.innerHTML = items.map(([v, label]) => `<button type="button" data-v="${esc(v)}" class="${v === active ? "active" : ""}" aria-pressed="${v === active}">${esc(label)}</button>`).join("");
    box.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      box.querySelectorAll("button").forEach(x => { x.classList.toggle("active", x === b); x.setAttribute("aria-pressed", String(x === b)); });
      onPick(b.dataset.v);
    });
    onPick(active);
  }
  function table(el, cols, rows) {
    $(el).innerHTML = '<div class="g-table-wrap"><table class="g-table"><thead><tr>' +
      cols.map(c => `<th class="${c.num ? "num" : ""}">${esc(c.title)}</th>`).join("") + "</tr></thead><tbody>" +
      rows.map(r => "<tr>" + cols.map(c => `<td class="${c.num ? "num" : ""}">${c.html ? c.html(r) : esc(c.fmt ? c.fmt(r[c.field], r) : r[c.field])}</td>`).join("") + "</tr>").join("") +
      "</tbody></table></div>";
  }
  function box(html) { return `<div class="g-box">${html}</div>`; }
  // Text colour on the strong end of the sequential scale (dark blue in light mode, light blue in dark mode)
  const onStrong = () => (window.G24Theme && window.G24Theme.isDark() ? "#0b1120" : "#fff");

  // CSV downloads of the tables behind the page
  const CSV = {
    country_relations: () => D.country_relations.map(r => ({ country: cname(r.country_code), ...r })),
    similarity: () => D.similarity, summary: () => D.summary, links: () => D.links,
  };
  document.addEventListener("click", e => {
    const b = e.target.closest(".g-dl"); if (!b) return;
    const rows = CSV[b.dataset.dl](); if (!rows.length) return;
    const cols = Object.keys(rows[0]);
    const q = v => { const s = v == null ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
    const text = [cols.join(","), ...rows.map(r => cols.map(c => q(r[c])).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = `global_${b.dataset.dl}.csv`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });

  // Mobile section menu
  const menuBtn = $("nav-menu-btn"), menu = $("nav-links");
  menuBtn.addEventListener("click", () => { const o = !menu.classList.contains("open"); menu.classList.toggle("open", o); menuBtn.setAttribute("aria-expanded", String(o)); });
  menu.addEventListener("click", e => { if (e.target.closest("a")) { menu.classList.remove("open"); menuBtn.setAttribute("aria-expanded", "false"); } });

  // ---------- Top: KPIs ----------
  function renderTop() {
    const m = D.meta;
    const k = [
      ["Partner countries", fmt(D.country_relations.length), "Countries co-authoring with the labs"],
      ["Papers with a foreign co-author", pct(100 * m.foreign_coauthored_papers / m.corpus_papers), `${fmt(m.foreign_coauthored_papers)} of ${fmt(m.corpus_papers)} papers`],
      ["Benchmark countries", Object.keys(m.countries).length, Object.values(m.countries).join(", ")],
      ["Foreign twins", foreign.length, "Chosen by the rules below"],
      ["Indian reference institutes", peers.filter(p => p.group === "India").length, "Chosen by the team"],
      ["Subfields measured", D.scope.length, `${Math.round(m.scope_coverage * 100)}% of the labs' papers`],
    ];
    $("g-kpis").innerHTML = k.map(([l, v, s]) => `<div class="kpi-card"><div class="kpi-label">${esc(l)}</div><div class="kpi-val">${esc(v)}</div><div class="kpi-sub">${esc(s)}</div></div>`).join("");
    $("g-hero-note").textContent = `Source: OpenAlex (benchmark queried ${m.built}; main dataset collected ${m.collection_date}). Benchmark years ${y0}–${y1}; 2026 is partial and left out.`;
  }

  // ---------- 01 Countries ----------
  function renderCountries() {
    const cr = D.country_relations;
    const top = cr.slice(0, 15);
    const focusCC = Object.keys(D.meta.countries);
    const color = cc => (focusCC.includes(cc) ? gc(CC_GROUP[cc]) : css("--g-other"));
    const k = ink();
    chart("ch-countries", {
      grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...tooltipBase(), trigger: "item", formatter: p => {
        const r = top[top.length - 1 - p.dataIndex];
        return `<b>${esc(cname(r.country_code))}</b><br>${fmt(r.papers)} papers (${pct(r.share_of_foreign_coauthored_pct)} of foreign co-authored)<br>NCL ${fmt(r.papers_ncl)} · IICT ${fmt(r.papers_iict)} · CECRI ${fmt(r.papers_cecri)}<br>${fmt(r.partner_institutions)} partner institutions`;
      } },
      xAxis: { type: "value", ...axisCommon() },
      yAxis: { type: "category", data: top.map(r => cname(r.country_code)).reverse(), ...axisCommon(), axisTick: { show: false } },
      series: [{ type: "bar", barMaxWidth: 22, data: top.map(r => ({ value: r.papers, itemStyle: { color: color(r.country_code), borderRadius: [0, 4, 4, 0] } })).reverse(),
        label: { show: true, position: "right", color: k.text2, formatter: p => fmt(p.value) } }],
    });

    const total = D.meta.foreign_coauthored_papers;
    $("focus-countries").innerHTML = focusCC.map(cc => {
      const r = cr.find(x => x.country_code === cc);
      const g = CC_GROUP[cc];
      const tw = foreign.filter(p => p.group === g).map(p => p.short).join(", ") || "none";
      if (!r) return `<div class="g-fc" style="--c:${gc(g)}"><h4>${esc(D.meta.countries[cc])}</h4><p>No co-authored papers.</p></div>`;
      return `<div class="g-fc" style="--c:${gc(g)}">
        <h4>${esc(D.meta.countries[cc])}<small>#${r.rank} partner</small></h4>
        <div class="g-fc-num">${fmt(r.papers)} <small style="font-size:.8rem;color:var(--text-muted);font-weight:600">papers · ${pct(r.share_of_foreign_coauthored_pct)}</small></div>
        <p>NCL ${fmt(r.papers_ncl)} · IICT ${fmt(r.papers_iict)} · CECRI ${fmt(r.papers_cecri)}<br>
        ${fmt(r.papers_2016_2020)} papers in 2016–20 → ${fmt(r.papers_2021_2026)} in 2021–26<br>
        Top partners: ${esc(r.top_partners)}<br><b>Benchmark twins:</b> ${esc(tw)}</p></div>`;
    }).join("");

    const ranked = focusCC.map(cc => cr.find(x => x.country_code === cc)).filter(Boolean).sort((a, b) => a.rank - b.rank);
    const [c1, c2, c3] = cr;
    const china = cr.find(x => x.country_code === "CN");
    $("ins-countries").innerHTML = [
      box(`<b class="g-big">${pct(100 * total / D.meta.corpus_papers)}</b>of the labs' ${fmt(D.meta.corpus_papers)} papers have a co-author abroad, from ${fmt(cr.length)} countries.`),
      box(`<b class="g-big">${esc(cname(c1.country_code))}, ${esc(cname(c2.country_code))}, ${esc(cname(c3.country_code))}</b>are the three largest partners (${fmt(c1.papers)}, ${fmt(c2.papers)} and ${fmt(c3.papers)} papers).`),
      china ? box(`<b class="g-big">China #${china.rank}</b>with ${fmt(china.papers)} co-authored papers, although it is the world's largest producer in these subfields (section 03).`) : "",
      box(`<b class="g-big">${ranked.map(r => `#${r.rank}`).join(" · ")}</b>ranks of ${ranked.map(r => esc(D.meta.countries[r.country_code])).join(", ")} among all partner countries.`),
    ].join("");

    new Tabulator("#tbl-countries", {
      data: cr, layout: "fitColumns", height: 440, index: "country_code",
      rowFormatter: row => { if (row.getData().focus_country) row.getElement().style.boxShadow = `inset 4px 0 0 ${gc(CC_GROUP[row.getData().country_code])}`; },
      columns: [
        { title: "#", field: "rank", width: 56, hozAlign: "right" },
        { title: "Country", field: "country_code", minWidth: 140, formatter: c => esc(cname(c.getValue())) + (c.getRow().getData().focus_country ? " ★" : ""), sorter: (a, b) => cname(a).localeCompare(cname(b)) },
        { title: "Papers", field: "papers", hozAlign: "right", width: 90 },
        { title: "Share of foreign co-authored", field: "share_of_foreign_coauthored_pct", hozAlign: "right", width: 130, formatter: c => pct(c.getValue()) },
        { title: "NCL", field: "papers_ncl", hozAlign: "right", width: 72 },
        { title: "IICT", field: "papers_iict", hozAlign: "right", width: 72 },
        { title: "CECRI", field: "papers_cecri", hozAlign: "right", width: 78 },
        { title: "2016–20", field: "papers_2016_2020", hozAlign: "right", width: 88 },
        { title: "2021–26", field: "papers_2021_2026", hozAlign: "right", width: 88 },
        { title: "Partner inst.", field: "partner_institutions", hozAlign: "right", width: 100 },
        { title: "Top partners", field: "top_partners", minWidth: 280, formatter: "textarea" },
      ],
    });
  }

  // ---------- 02 Peers ----------
  function renderPeers() {
    const m = D.meta, c = m.candidates;
    const labScope = LABS.map(l => sumById[labRow(l).institution_id].papers_scope);
    const floor = Math.round(c.min_size_ratio * Math.min(...labScope));
    const indian = peers.filter(p => p.group === "India").map(p => p.short).join(", ");
    $("g-rules").innerHTML = [
      `<b>Scope.</b> Only research papers (${m.work_types.map(t => t + "s").join(" and ")}), ${y0}–${y1}, in the ${D.scope.length} subfields that together make up ${Math.round(m.scope_coverage * 100)}% of the three labs' papers are counted, for every institution. A university's medicine or civil engineering therefore neither helps nor hurts it.`,
      `<b>Pool.</b> In each country, the ${c.top_n_by_output} institutions with the most in-scope papers (an institute's sub-units count with it).`,
      `<b>Same kind of organisation as CSIR.</b> OpenAlex type ${c.keep_types.join(" or ")}: no universities, companies or hospitals. Umbrella bodies that are the parent of another candidate (the whole Chinese Academy of Sciences, the US Department of Energy) are dropped, because CSIR is compared lab by lab.`,
      `<b>Stand-alone institutes only (2b).</b> OpenAlex also labels university-hosted labs, multi-university consortia, synchrotrons and government departments as government/facility. These ${D.exclusions.length} were reviewed by hand and removed; each is listed below with its reason.`,
      `<b>Comparable size.</b> At least ${Math.round(c.min_size_ratio * 100)}% of the in-scope papers of the smallest CSIR lab (${fmt(floor)} papers). The ${c.max_candidates} largest that pass are tested.`,
      `<b>Most similar research profile.</b> Cosine similarity of paper counts across all subfields. In each country the most similar lab–institute pair is fixed first, then the next among the rest: each lab gets at most one twin per country, and only if the similarity is at least ${m.min_similarity}.`,
      `<b>Indian reference group.</b> ${esc(indian)}: leading Indian chemistry universities and institutes chosen by the team, measured on the same scope (not selected by similarity).`,
    ].map(t => `<li>${t}</li>`).join("");

    $("peer-cards").innerHTML = GROUPS.filter(g => g !== "CSIR lab").map(g => {
      const ps = peers.filter(p => p.group === g);
      const missing = g === "India" ? [] : LABS.filter(l => !ps.some(p => p.twin_of === l));
      return `<div class="g-peer-group"><h4><span class="g-swatch" style="background:${gc(g)}"></span>${esc(GROUP_LABEL[g])}</h4><div class="g-peer-row">` +
        ps.map(p => `<div class="g-peer" style="--c:${gc(g)}"><b>${esc(p.short)}</b><span>${esc(p.short !== p.name ? p.name + " · " : "")}${esc(p.city)}<br>${g === "India" ? "closest to" : "twin of"} ${esc(p.twin_of)} · similarity ${Number(p.similarity).toFixed(2)}</span></div>`).join("") +
        missing.map(l => `<div class="g-peer"><b>No twin for ${esc(l)}</b><span>no institute reached similarity ${m.min_similarity}</span></div>`).join("") +
        "</div></div>";
    }).join("");

    const fcols = Object.keys(D.funnel[0]);
    table("tbl-funnel", fcols.map(f => ({ title: f === "country" ? "Country" : f, field: f, num: f !== "country" })), D.funnel);

    const shade = v => {
      if (v == null) return "";
      const a = Math.max(0, Math.min(1, v));
      return `background: color-mix(in srgb, var(--g-seq-hi) ${Math.round(a * 85)}%, var(--g-seq-lo)); color: ${a > 0.55 ? onStrong() : "var(--text)"};`;
    };
    const simCol = lab => ({
      title: lab.replace("CSIR-", ""), field: `sim_${lab}`, hozAlign: "right", width: 92,
      formatter: cell => { cell.getElement().setAttribute("style", cell.getElement().getAttribute("style") + ";" + shade(cell.getValue())); return (cell.getValue() == null ? "–" : Number(cell.getValue()).toFixed(2)) + (cell.getRow().getData().selected_twin_of === lab ? " ★" : ""); },
    });
    new Tabulator("#tbl-sim", {
      data: D.similarity, layout: "fitColumns", height: 420, groupBy: "country",
      columns: [
        { title: "Institute", field: "name", minWidth: 260 },
        { title: "City", field: "city", width: 120 },
        { title: "In-scope papers", field: "in_scope_papers", hozAlign: "right", width: 120 },
        simCol("CSIR-NCL"), simCol("CSIR-IICT"), simCol("CSIR-CECRI"),
      ],
    });

    table("tbl-ex", [{ title: "Institution", field: "name" }, { title: "Country", field: "country" }, { title: "Reason", field: "reason" }], D.exclusions);
    $("tbl-ex").style.maxHeight = "420px"; $("tbl-ex").style.overflow = "auto";
    table("tbl-scope", [{ title: "Subfield", field: "subfield" }, { title: "Share of lab papers", field: "share_pct", num: true, fmt: v => pct(v, 2) }, { title: "Cumulative", field: "cum_share_pct", num: true, fmt: v => pct(v) }], D.scope);
    $("tbl-scope").style.maxHeight = "420px"; $("tbl-scope").style.overflow = "auto";
  }

  // ---------- 03 Output ----------
  function renderOutput() {
    const k = ink();
    const draw = lab => {
      const set = [labRow(lab), ...foreign.filter(p => p.twin_of === lab)];
      const years = [];
      for (let y = y0; y <= y1; y++) years.push(y);
      addLegend("ch-index", ["CSIR lab", ...set.slice(1).map(p => p.group)]);
      chart("ch-index", {
        grid: { left: 8, right: 160, top: 16, bottom: 8, containLabel: true },
        tooltip: { ...tooltipBase(), trigger: "axis", valueFormatter: v => (v == null ? "–" : v.toFixed(0)) },
        xAxis: { type: "category", data: years, boundaryGap: false, ...axisCommon() },
        yAxis: { type: "value", name: "2016 = 100", ...axisCommon() },
        series: set.map(p => {
          const rows = D.by_year.filter(r => r.institution_id === p.institution_id);
          return {
            type: "line", name: p.short, symbolSize: 8, lineStyle: { width: 2 }, itemStyle: { color: gc(p.group), borderColor: css("--surface"), borderWidth: 2 },
            data: years.map(y => { const r = rows.find(x => x.year === y); return r ? r.index_2016 : null; }),
            endLabel: { show: true, color: k.text2, formatter: s => s.seriesName },
            markLine: p.group === "CSIR lab" ? { silent: true, symbol: "none", lineStyle: { color: k.muted, type: "dashed" }, data: [{ yAxis: 100 }], label: { show: false } } : undefined,
          };
        }),
      });
    };
    seg("seg-index", LABS.map(l => [l, l]), LABS[0], draw);

    const rows = [...D.summary].filter(r => r.cagr_pct != null).sort((a, b) => a.cagr_pct - b.cagr_pct);
    addLegend("ch-cagr", GROUPS);
    chart("ch-cagr", {
      grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...tooltipBase(), trigger: "item", formatter: p => { const r = rows[p.dataIndex]; return `<b>${esc(r.short)}</b> (${esc(GROUP_LABEL[r.group])})<br>${fmt(r[`papers_${y0}`])} papers in ${y0} → ${fmt(r[`papers_${y1}`])} in ${y1}<br>${pct(r.cagr_pct)} a year`; } },
      xAxis: { type: "value", axisLabel: { color: k.text2, formatter: v => `${v}%` }, splitLine: { lineStyle: { color: k.split } } },
      yAxis: { type: "category", data: rows.map(r => r.short), ...axisCommon(), axisTick: { show: false } },
      series: [{ type: "bar", barMaxWidth: 18, data: rows.map(r => ({ value: r.cagr_pct, itemStyle: { color: gc(r.group), borderRadius: r.cagr_pct >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
        label: { show: true, position: "right", color: k.text2, formatter: p => pct(p.value) },
        markLine: { silent: true, symbol: "none", lineStyle: { color: k.muted }, data: [{ xAxis: 0 }], label: { show: false } } }],
    });

    const cc = ["IN", ...Object.keys(D.meta.countries)];
    const years = [...new Set(D.countries.map(r => r.year))].sort();
    addLegend("ch-world", cc.map(c => CC_GROUP[c]));
    chart("ch-world", {
      grid: { left: 8, right: 100, top: 16, bottom: 8, containLabel: true },
      tooltip: { ...tooltipBase(), trigger: "axis", valueFormatter: v => pct(v) },
      xAxis: { type: "category", data: years, boundaryGap: false, ...axisCommon() },
      yAxis: { type: "value", ...axisCommon(), axisLabel: { color: k.text2, formatter: v => `${v}%` } },
      series: cc.map(c => ({
        type: "line", name: c === "IN" ? "India" : D.meta.countries[c], symbolSize: 8, lineStyle: { width: 2 },
        itemStyle: { color: gc(CC_GROUP[c]), borderColor: css("--surface"), borderWidth: 2 },
        endLabel: { show: true, color: k.text2, formatter: s => s.seriesName },
        data: years.map(y => { const r = D.countries.find(x => x.country_code === c && x.year === y); return r ? r.world_share_pct : null; }),
      })),
    });

    const labs = LABS.map(l => sumById[labRow(l).institution_id]);
    const twinCagr = median(foreign.map(p => sumById[p.institution_id].cagr_pct));
    const indCagr = median(peers.filter(p => p.group === "India").map(p => sumById[p.institution_id].cagr_pct));
    const share = (c, y) => (D.countries.find(r => r.country_code === c && r.year === y) || {}).world_share_pct;
    $("ins-output").innerHTML = [
      box(`<b class="g-big">${labs.map(r => pct(r.cagr_pct)).join(" · ")}</b>yearly change of in-scope papers at NCL, IICT and CECRI, ${y0}→${y1} (${labs.map(r => `${fmt(r[`papers_${y0}`])}→${fmt(r[`papers_${y1}`])}`).join(", ")}).`),
      box(`<b class="g-big">${pct(twinCagr)}</b>median yearly change of the ${foreign.length} foreign twins; ${pct(indCagr)} for the Indian reference group.`),
      box(`<b class="g-big">${pct(share("CN", y0))} → ${pct(share("CN", y1))}</b>China's share of world papers in these subfields; India ${pct(share("IN", y0))} → ${pct(share("IN", y1))}, USA ${pct(share("US", y0))} → ${pct(share("US", y1))}.`),
    ].join("");
  }

  // ---------- 04 Impact ----------
  const METRICS = {
    top10_pct: { label: "World top 10%", title: "Share of papers in the world's top 10%", ref: 10, note: "A paper is in the top 10% when it is among the most cited 10% of papers of the same subfield, type and year worldwide (OpenAlex citation_normalized_percentile). The dashed line is the world expectation: 10%." },
    top1_pct: { label: "World top 1%", title: "Share of papers in the world's top 1%", ref: 1, note: "Among the most cited 1% of papers of the same subfield, type and year worldwide. The dashed line is the world expectation: 1%." },
    above_world_pct: { label: "Above world average", title: "Share of papers cited above the world average", ref: null, note: "Papers with field-weighted citation impact (FWCI) above 1, i.e. cited more than the world average for their subfield, type and year." },
    intl_pct: { label: "International", title: "Share of papers with a co-author in another country", ref: null, note: "Papers with authors in two or more countries. Not an impact measure; shown for context." },
  };
  function renderImpact() {
    const k = ink();
    const draw = key => {
      const M = METRICS[key];
      $("impact-title").textContent = M.title;
      $("impact-note").textContent = M.note;
      const rows = [...D.summary].sort((a, b) => a[key] - b[key]);
      chart("ch-impact", {
        grid: { left: 8, right: 60, top: 8, bottom: 8, containLabel: true },
        tooltip: { ...tooltipBase(), trigger: "item", formatter: p => { const r = rows[p.dataIndex]; return `<b>${esc(r.short)}</b> (${esc(GROUP_LABEL[r.group])})<br>${esc(M.title)}: ${pct(r[key])}<br>${fmt(r.papers_scope)} in-scope papers, ${y0}–${y1}`; } },
        xAxis: { type: "value", axisLabel: { color: k.text2, formatter: v => `${v}%` }, splitLine: { lineStyle: { color: k.split } } },
        yAxis: { type: "category", data: rows.map(r => r.short), ...axisCommon(), axisTick: { show: false },
          axisLabel: { color: k.text2, formatter: v => (LABS.includes(v) ? `{b|${v}}` : v), rich: { b: { fontWeight: 800, color: k.text } } } },
        series: [{ type: "bar", barMaxWidth: 18, data: rows.map(r => ({ value: r[key], itemStyle: { color: gc(r.group), borderRadius: [0, 4, 4, 0] } })),
          label: { show: true, position: "right", color: k.text2, formatter: p => pct(p.value) },
          markLine: M.ref == null ? undefined : { silent: true, symbol: "none", lineStyle: { color: k.muted, type: "dashed" }, data: [{ xAxis: M.ref }], label: { color: k.muted, formatter: "world" } } }],
      });
    };
    addLegend("ch-impact", GROUPS);
    seg("seg-impact", Object.entries(METRICS).map(([k2, v]) => [k2, v.label]), "top10_pct", draw);

    new Tabulator("#tbl-summary", {
      data: D.summary, layout: "fitColumns", height: 460,
      rowFormatter: row => { row.getElement().style.boxShadow = `inset 4px 0 0 ${gc(row.getData().group)}`; },
      columns: [
        { title: "Institution", field: "short", minWidth: 150, frozen: true },
        { title: "Group", field: "group", width: 110 },
        { title: "Twin of", field: "twin_of", width: 105 },
        { title: "In-scope papers", field: "papers_scope", hozAlign: "right", width: 110 },
        { title: "Scope share", field: "scope_share_pct", hozAlign: "right", width: 95, formatter: c => pct(c.getValue()) },
        { title: `${y0}`, field: `papers_${y0}`, hozAlign: "right", width: 72 },
        { title: `${y1}`, field: `papers_${y1}`, hozAlign: "right", width: 72 },
        { title: "Growth / yr", field: "cagr_pct", hozAlign: "right", width: 95, formatter: c => pct(c.getValue()) },
        { title: "Top 10%", field: "top10_pct", hozAlign: "right", width: 85, formatter: c => pct(c.getValue()) },
        { title: "Top 10% 2016–20", field: "top10_pct_early", hozAlign: "right", width: 110, formatter: c => pct(c.getValue()) },
        { title: "Top 10% 2021–25", field: "top10_pct_late", hozAlign: "right", width: 110, formatter: c => pct(c.getValue()) },
        { title: "Top 1%", field: "top1_pct", hozAlign: "right", width: 80, formatter: c => pct(c.getValue(), 2) },
        { title: "Above world", field: "above_world_pct", hozAlign: "right", width: 95, formatter: c => pct(c.getValue()) },
        { title: "International", field: "intl_pct", hozAlign: "right", width: 100, formatter: c => pct(c.getValue()) },
      ],
    });

    const rank = [...D.summary].sort((a, b) => b.top10_pct - a.top10_pct);
    const labs = LABS.map(l => sumById[labRow(l).institution_id]);
    const twinMed = median(foreign.map(p => sumById[p.institution_id].top10_pct));
    const indMed = median(peers.filter(p => p.group === "India").map(p => sumById[p.institution_id].top10_pct));
    const best = labs.reduce((a, b) => (b.top10_pct > a.top10_pct ? b : a));
    $("ins-impact").innerHTML = [
      box(`<b class="g-big">${labs.map(r => pct(r.top10_pct)).join(" · ")}</b>of NCL, IICT and CECRI papers are in the world's top 10% (world expectation 10%).`),
      box(`<b class="g-big">${pct(twinMed)}</b>median for the foreign twins, against ${pct(indMed)} for the Indian reference group.`),
      box(`<b class="g-big">#${rank.indexOf(best) + 1} of ${rank.length}</b>${esc(best.short)} is the best-placed CSIR lab on this measure among all ${rank.length} institutions.`),
    ].join("");
  }

  // ---------- 05 Profiles ----------
  function renderProfiles() {
    const k = ink();
    const subs = [...new Set(D.profiles.map(r => r.subfield))];
    const inst = peers.map(p => p.short);
    const data = D.profiles.map(r => [subs.indexOf(r.subfield), inst.indexOf(r.short), r.share_pct ?? 0]);
    // Colour scale capped at 30% so one very specialised institute does not wash out the rest
    const cap = 30;
    chart("ch-profiles", {
      grid: { left: 8, right: 16, top: 8, bottom: 70, containLabel: true },
      tooltip: { ...tooltipBase(), formatter: p => `<b>${esc(inst[p.value[1]])}</b><br>${esc(subs[p.value[0]])}: ${pct(p.value[2])} of its papers` },
      xAxis: { type: "category", data: subs, ...axisCommon(), axisLabel: { color: k.text2, rotate: 35, interval: 0, width: 150, overflow: "truncate" }, splitArea: { show: false } },
      yAxis: { type: "category", data: inst, inverse: true, ...axisCommon(),
        axisLabel: { color: k.text2, formatter: v => (LABS.includes(v) ? `{b|${v}}` : v), rich: { b: { fontWeight: 800, color: k.text } } } },
      visualMap: { min: 0, max: cap, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemHeight: 160,
        inRange: { color: [css("--g-seq-lo"), css("--g-seq-hi")] }, textStyle: { color: k.text2 }, formatter: v => (v >= cap ? `${cap}%+` : `${Math.round(v)}%`) },
      series: [{ type: "heatmap", itemStyle: { borderColor: css("--surface"), borderWidth: 2 },
        // label only the larger shares; the tooltip gives every value
        label: { show: true, textBorderWidth: 0, formatter: p => (p.value[2] >= 10 ? `${Math.round(p.value[2])}` : "") },
        data: data.map(d => ({ value: d, label: { color: d[2] / cap > 0.55 ? onStrong() : k.text } })),
        emphasis: { itemStyle: { borderColor: k.text, borderWidth: 1 } } }],
    });
  }

  // ---------- 06 Links ----------
  function renderLinks() {
    const k = ink();
    const others = peers.filter(p => p.group !== "CSIR lab");
    const cell = (lab, id) => D.links.find(r => r.lab === lab && r.institution_id === id) || {};
    const data = [];
    LABS.forEach((lab, yi) => others.forEach((p, xi) => data.push([xi, yi, cell(lab, p.institution_id).coauthored_papers || 0])));
    const max = Math.max(1, ...data.map(d => d[2]));
    chart("ch-collab", {
      grid: { left: 8, right: 16, top: 8, bottom: 60, containLabel: true },
      tooltip: { ...tooltipBase(), formatter: p => `<b>${esc(LABS[p.value[1]])} × ${esc(others[p.value[0]].short)}</b><br>${fmt(p.value[2])} co-authored papers, ${y0}–${y1}` },
      xAxis: { type: "category", data: others.map(p => p.short), ...axisCommon(), axisLabel: { color: k.text2, rotate: 35, interval: 0 }, splitArea: { show: false } },
      yAxis: { type: "category", data: LABS, inverse: true, ...axisCommon() },
      visualMap: { show: false, min: 0, max, inRange: { color: [css("--g-seq-lo"), css("--g-seq-hi")] } },
      series: [{ type: "heatmap", itemStyle: { borderColor: css("--surface"), borderWidth: 2 },
        label: { show: true, formatter: p => fmt(p.value[2]), textBorderWidth: 0 },
        data: data.map(d => ({ value: d, label: { color: d[2] / max > 0.55 ? onStrong() : k.text } })) }],
    });

    const s1 = window.G24Theme && window.G24Theme.isDark() ? "#9085e9" : "#6250d6";
    const s2 = window.G24Theme && window.G24Theme.isDark() ? "#e66767" : "#e34948";
    const draw = lab => {
      const rows = D.links.filter(r => r.lab === lab).sort((a, b) => (a.peer_papers_citing_lab + a.peer_papers_cited_by_lab) - (b.peer_papers_citing_lab + b.peer_papers_cited_by_lab));
      chart("ch-flows", {
        grid: { left: 8, right: 56, top: 36, bottom: 8, containLabel: true },
        legend: { top: 0, textStyle: { color: k.text2 } },
        tooltip: { ...tooltipBase(), trigger: "axis", axisPointer: { type: "shadow" }, formatter: ps => {
          const r = rows[ps[0].dataIndex];
          return `<b>${esc(r.short)}</b> (${esc(GROUP_LABEL[r.group])})<br>${fmt(r.peer_papers_citing_lab)} of its papers cite ${esc(lab)}<br>${fmt(r.peer_papers_cited_by_lab)} of its papers are cited by ${esc(lab)}<br>Exchange ratio ${r.exchange_ratio == null ? "–" : r.exchange_ratio.toFixed(2)}`;
        } },
        xAxis: { type: "value", ...axisCommon() },
        yAxis: { type: "category", data: rows.map(r => r.short + (r.is_twin ? " ★" : "")), ...axisCommon(), axisTick: { show: false } },
        series: [
          { name: `Peer papers citing ${lab}`, type: "bar", barMaxWidth: 12, barGap: "20%", itemStyle: { color: s1, borderRadius: [0, 4, 4, 0] }, data: rows.map(r => r.peer_papers_citing_lab) },
          { name: `Peer papers cited by ${lab}`, type: "bar", barMaxWidth: 12, itemStyle: { color: s2, borderRadius: [0, 4, 4, 0] }, data: rows.map(r => r.peer_papers_cited_by_lab) },
        ],
      });
    };
    seg("seg-flows", LABS.map(l => [l, l]), LABS[0], draw);

    new Tabulator("#tbl-links", {
      data: D.links, layout: "fitColumns", height: 420, groupBy: "lab",
      columns: [
        { title: "Peer", field: "short", minWidth: 150, formatter: c => esc(c.getValue()) + (c.getRow().getData().is_twin ? " ★" : "") },
        { title: "Group", field: "group", width: 120 },
        { title: "Co-authored papers", field: "coauthored_papers", hozAlign: "right", width: 140 },
        { title: "Peer papers citing the lab", field: "peer_papers_citing_lab", hozAlign: "right", width: 170 },
        { title: "Peer papers cited by the lab", field: "peer_papers_cited_by_lab", hozAlign: "right", width: 180 },
        { title: "Exchange ratio", field: "exchange_ratio", hozAlign: "right", width: 120, formatter: c => (c.getValue() == null ? "–" : Number(c.getValue()).toFixed(2)) },
      ],
    });

    const L = D.links;
    const top = LABS.map(lab => L.filter(r => r.lab === lab).reduce((a, b) => (b.coauthored_papers > a.coauthored_papers ? b : a)));
    const fx = L.filter(r => !["India"].includes(r.group));
    const inF = fx.reduce((a, r) => a + r.peer_papers_citing_lab, 0), outF = fx.reduce((a, r) => a + r.peer_papers_cited_by_lab, 0);
    const nForeign = new Set(fx.map(r => r.institution_id)).size;
    const forCo = fx.reduce((a, r) => a + r.coauthored_papers, 0);
    const indCo = L.filter(r => r.group === "India").reduce((a, r) => a + r.coauthored_papers, 0);
    $("ins-links").innerHTML = [
      box(`<b class="g-big">${top.map(r => esc(r.short)).join(" · ")}</b>closest co-author among the peers for NCL, IICT and CECRI (${top.map(r => fmt(r.coauthored_papers)).join(", ")} papers).`),
      box(`<b class="g-big">${fmt(forCo)} vs ${fmt(indCo)}</b>papers co-authored with the ${nForeign} foreign peers vs with the six Indian reference institutes, ${y0}–${y1} (lab–peer pairs summed).`),
      box(`<b class="g-big">${outF ? (inF / outF).toFixed(2) : "–"}</b>exchange ratio with the foreign peers: ${fmt(inF)} of their papers cite the labs, while the labs cite ${fmt(outF)} of theirs (lab–peer pairs summed). By country: ` +
        GROUPS.filter(g => g !== "CSIR lab").map(g => {
          const r = L.filter(x => x.group === g);
          const a = r.reduce((s, x) => s + x.peer_papers_citing_lab, 0), b = r.reduce((s, x) => s + x.peer_papers_cited_by_lab, 0);
          return `${esc(g)} ${b ? (a / b).toFixed(2) : "–"}`;
        }).join(", ") + "."),
    ].join("");
  }

  // ---------- 07 Method ----------
  function renderMethod() {
    const m = D.meta;
    $("g-sources").innerHTML = [
      `OpenAlex works API, queried ${esc(m.built)} with one rule for every institution: papers of the institution and its sub-units (authorships.institutions.lineage), ${y0}–${y1}, ${esc(m.work_types.join(" and "))}s, in the benchmark subfields.`,
      `Field-normalised impact: OpenAlex citation_normalized_percentile (top 10% / top 1%) and field-weighted citation impact (fwci), both computed by OpenAlex against all papers worldwide of the same subfield, type and year.`,
      `Country context: the same scope for all papers with an author in each country, and for the whole world.`,
      `Links: co-authored papers from the same queries; citation flows from the labs' ${fmt(m.corpus_papers)} curated papers (filters cites: and cited_by:, in batches of 100), keeping papers of the peers.`,
      `Partner countries (section 01): every author affiliation on the labs' curated papers, 2016–2026 (main dataset, collected ${esc(m.collection_date)}).`,
      `Files: config/global_benchmark.yaml (rules), config/overrides/global_peer_exclusions.csv (rule 2b), data/final/global/ (raw benchmark data), stats/tables/global_*.csv (every number on this page).`,
    ].map(t => `<li>${t}</li>`).join("");
    $("g-caveats").innerHTML = [
      `Our labs' numbers here come from the same raw OpenAlex query as the peers, not from the cleaned dataset used on the main dashboard, so they differ slightly from it (duplicates and non-research items are not removed for anyone).`,
      `OpenAlex affiliation quality varies: some institutes' papers are partly credited to a parent or a renamed entity. A sudden drop for one institute (for example a split or renamed unit) can be an artefact.`,
      `Top 10% / top 1% shares for the latest years are less settled: recent papers have had little time to be cited.`,
      `The twins are the most similar government institutes, not identical ones. US national labs publish more physics and materials science than the CSIR labs, so their similarity scores are lower (no US or Australian institute is close enough to CSIR-IICT).`,
      `Rule 2b and the similarity floor (${m.min_similarity}) are judgment calls, recorded in docs/DECISIONS.md (D-35). The Indian reference group was chosen by the team, not by the rules.`,
      `Counts are whole counts: a paper with authors at two institutions counts fully for both.`,
    ].map(t => `<li>${t}</li>`).join("");
  }

  renderTop();
  renderCountries();
  renderPeers();
  renderOutput();
  renderImpact();
  renderProfiles();
  renderLinks();
  renderMethod();
})();
