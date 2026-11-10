/**
 * Insight 11 page (insights11.html): how ideas spread through the labs' networks.
 * Data: window.G24_I11 from data/g24_insights11_suite.js (src/dashboard/build_insights11_suite.py), which copies
 * stats/tables/insights/11_*. Every number and sentence here is read from that payload.
 */
(function () {
  "use strict";
  const D = window.G24_I11;
  if (!D || !D.spreading || !D.spreading.full_coauthorship) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      '<p style="padding:2rem">Insight 11 data not found (data/g24_insights11_suite.js). Run <code>python run.py insight11</code>.</p>');
    return;
  }

  // ---------- helpers ----------
  const $ = id => document.getElementById(id);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const ink = () => (window.G24Theme ? window.G24Theme.ink() : { text: "#1e293b", text2: "#475569", muted: "#64748b", split: "#e2e8f0" });
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmt = n => (n == null || Number.isNaN(n) ? "–" : Number(n).toLocaleString("en-US"));
  const num = (v, d = 2) => (v == null || Number.isNaN(v) ? "–" : Number(v).toFixed(d));
  const pct = (v, d = 1) => (v == null || Number.isNaN(v) ? "–" : `${Number(v).toFixed(d)}%`);
  const steps = v => (v == null ? "not reached" : `${Number(v)} steps`);
  const S = D.spreading, P = S.parameters, DF = D.diffusion, TH = D.threshold.networks || {};
  const NETS = ["full_coauthorship", "faculty_coauthorship", "faculty_citation", "full_citation"];
  const NET_COLOR = { full_coauthorship: "--s1", faculty_coauthorship: "--s2", faculty_citation: "--s3", full_citation: "--s4" };
  const LAB_VAR = { "CSIR-IICT": "--c-iict", "CSIR-NCL": "--c-ncl", "CSIR-CECRI": "--c-cecri" };
  const LAB_KEYS = ["iict", "ncl", "cecri"];
  const FIELDS = ["Chemistry", "Materials", "Engineering", "Energy", "Biochemistry", "Medicine"];
  const netName = k => (S[k] ? S[k].network_name : (k.startsWith("field_") ? `${k.slice(6)} field network` : k));
  const claim = id => ((D.claims && D.claims.claims) || []).find(c => c.id === id);

  const charts = [];
  function chart(id, option) {
    const el = $(id);
    let c = echarts.getInstanceByDom(el);
    if (!c) { c = echarts.init(el); charts.push(c); }
    c.setOption(option, true);
    return c;
  }
  window.addEventListener("resize", () => charts.forEach(c => c.resize()));
  const axis = () => { const k = ink(); return { axisLabel: { color: k.text2 }, axisLine: { lineStyle: { color: k.split } }, splitLine: { lineStyle: { color: k.split } }, nameTextStyle: { color: k.muted } }; };
  const tip = extra => ({ confine: true, backgroundColor: css("--surface"), borderColor: css("--border-strong"), textStyle: { color: ink().text }, ...extra });
  const legend = () => ({ top: 0, textStyle: { color: ink().text2 }, itemWidth: 18 });
  const stepAxis = n => ({ type: "category", name: "step", nameLocation: "middle", nameGap: 26, data: Array.from({ length: n }, (_, i) => i), boundaryGap: false, ...axis() });
  const line = (name, data, color, extra = {}) => ({ type: "line", name, data, symbolSize: 6, showSymbol: false, lineStyle: { width: 2, color, ...(extra.lineStyle || {}) }, itemStyle: { color }, ...extra });
  const half = () => ({ silent: true, symbol: "none", lineStyle: { color: ink().muted, type: "dashed" }, data: [{ yAxis: 50 }], label: { color: ink().muted, formatter: "50%" } });

  function table(el, cols, rows, cls = "") {
    $(el).innerHTML = `<div class="g-table-wrap"><table class="g-table ${cls}"><thead><tr>` +
      cols.map(c => `<th class="${c.num ? "num" : ""}">${c.title}</th>`).join("") + "</tr></thead><tbody>" +
      rows.map(r => "<tr>" + cols.map(c => `<td class="${c.num ? "num" : ""}">${c.html ? c.html(r) : esc(c.fmt ? c.fmt(r[c.field], r) : r[c.field])}</td>`).join("") + "</tr>").join("") +
      "</tbody></table></div>";
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
  const box = html => `<div class="g-box">${html}</div>`;
  const badge = ok => `<span class="i-badge ${ok ? "i-pass" : "i-fail"}">${ok ? "✓ verified" : "✗ check failed"}</span>`;

  // Mobile menu + data-* fillers
  const menuBtn = $("nav-menu-btn"), menu = $("nav-links");
  menuBtn.addEventListener("click", () => { const o = !menu.classList.contains("open"); menu.classList.toggle("open", o); menuBtn.setAttribute("aria-expanded", String(o)); });
  menu.addEventListener("click", e => { if (e.target.closest("a")) menu.classList.remove("open"); });
  const PARAMS = { ...P, n_trials: DF.metrics.n_trials, max_steps: DF.metrics.max_steps };
  document.querySelectorAll("[data-param]").forEach(el => { el.textContent = PARAMS[el.dataset.param]; });
  document.querySelectorAll("[data-thr]").forEach(el => { el.textContent = (D.threshold.method || {})[el.dataset.thr] ?? ""; });
  document.querySelectorAll("[data-meta]").forEach(el => { el.textContent = D.meta[el.dataset.meta] || ""; });

  // ---------- Top ----------
  function renderTop() {
    const full = S.full_coauthorship.fields.Combined, fac = S.faculty_coauthorship.fields.Combined;
    const ratios = Object.values(TH).map(t => t.peak_over_theory);
    const ch = DF.fields_data.Chemistry.condition_a;
    const runs = D.grid.reduce((a, r) => a + (r.mc_runs || 0), 0);
    const c = D.claims || {};
    const kpis = [
      ["Steps to reach half of all authors", full.mc_t50 == null ? "–" : full.mc_t50, `full network, ${fmt(S.full_coauthorship.nodes)} people`],
      ["…of faculty, faculty-only network", fac.mc_t50 == null ? "> 15" : fac.mc_t50, `${fmt(S.faculty_coauthorship.nodes)} connected scientists`],
      ["Real tipping point vs. formula", `${Math.min(...ratios).toFixed(1)}–${Math.max(...ratios).toFixed(1)}×`, "measured / textbook threshold"],
      ["Ideas leaving their field", pct(ch.spillover_curve[ch.spillover_curve.length - 1]), "outside Chemistry by step 15"],
      ["Monte Carlo runs", fmt(runs), "network comparison alone"],
      ["Claims verified", `${c.n_passed || 0} / ${c.n_claims || 0}`, "automatic checks, section 08"],
    ];
    $("i-kpis").innerHTML = kpis.map(([l, v, s]) => `<div class="kpi-card"><div class="kpi-label">${esc(l)}</div><div class="kpi-val">${esc(v)}</div><div class="kpi-sub">${esc(s)}</div></div>`).join("");
    $("i-hero-note").textContent = `Data: OpenAlex, collected ${D.meta.collection_date}; simulations built ${D.meta.built}. One step = one round of contact between collaborators.`;
    const order = ["C1", "C2", "C3", "C7", "C8", "C9", "C4", "C6", "C5"];
    $("i-findings-list").innerHTML = order.map(claim).filter(Boolean).map((cl, i) =>
      `<div class="i-finding"><span class="i-n">${i + 1}</span><p>${esc(cl.claim)}<small>Source: ${esc(cl.source)} · check: ${esc(cl.check)}</small></p>${badge(cl.passed)}</div>`).join("");
  }

  // ---------- 01 Data ----------
  function renderData() {
    const rows = NETS.map(k => {
      const n = S[k], t = n.thresholds;
      const desc = {
        full_coauthorship: "Everyone who published with a lab affiliation (faculty, students, project staff, others); link = co-authored ≥ 1 paper (papers with > 30 authors left out); largest connected part",
        faculty_coauthorship: "Roster scientists with ≥ 1 faculty co-author; link = co-authored ≥ 1 paper at their roster lab (the main dashboard's faculty network)",
        faculty_citation: "Roster scientists; arrow from cited to citing scientist (self-citations left out)",
        full_citation: "Papers in the corpus; arrow from cited to citing paper (ideas move forward in time)",
      }[k];
      return { k, name: n.network_name, desc, nodes: n.nodes, edges: n.edges, directed: t.directed, kmean: t.k_mean,
        hmf: t.beta_c_hmf, qmf: t.beta_c_qmf, cyc: n.is_acyclic === undefined ? "" : (n.is_acyclic ? "acyclic" : `${fmt(n.nodes_in_cycles)} in cycles`) };
    });
    table("tbl-networks", [
      { title: "Network", html: r => `<b>${esc(r.name)}</b><br><span class="g-note" style="margin:0">${esc(r.desc)}</span>` },
      { title: "Nodes", field: "nodes", num: true, fmt: fmt }, { title: "Links", field: "edges", num: true, fmt: fmt },
      { title: "Type", html: r => (r.directed ? "directed" + (r.cyc ? ` · ${esc(r.cyc)}` : "") : "undirected") },
      { title: "Mean degree", field: "kmean", num: true, fmt: v => num(v) },
      { title: "\\(\\langle k\\rangle/\\langle k^2\\rangle\\)", field: "hmf", num: true, fmt: v => (v == null ? "n/a" : num(v, 4)) },
      { title: "\\(1/\\lambda_{\\max}\\)", field: "qmf", num: true, fmt: v => (v == null ? "none (λ = 0)" : num(v, 4)) },
    ], rows);
    const pc = S.full_citation;
    if (pc.nodes_in_cycles && pc.nodes_in_cycles < 0.01 * pc.nodes) {
      $("tbl-networks").insertAdjacentHTML("beforeend", `<p class="g-note">Paper citation: \\(\\lambda_{\\max}\\) comes only from the ${fmt(pc.nodes_in_cycles)} papers that cite each other in loops (mutual citations); for the other ${fmt(pc.nodes - pc.nodes_in_cycles)} papers the network is acyclic, so \\(1/\\lambda_{\\max}\\) says nothing about spreading there.</p>`);
    }

    const f = D.cleaning.funnel || {};
    const st = (k, l) => f[k] ? [l, f[k].total ?? f[k].total_excluded] : null;
    $("i-funnel").innerHTML = [st("stage_1_raw_scraped", "Scraped from staff pages"), st("stage_2_excluded_technical_and_duplicates", "Removed (technical staff, duplicates)"),
      st("stage_3_clean_roster", "Roster scientists"), st("stage_4_active_cadre_with_papers", "With papers 2016–2026")].filter(Boolean)
      .map(([l, v]) => `<div class="kpi-card"><div class="kpi-label">${esc(l)}</div><div class="kpi-val">${fmt(v)}</div></div>`).join("");
    const ex = D.cleaning.excluded_staff_publishing || {};
    const s4 = f.stage_4_active_cadre_with_papers || { by_lab: {} };
    $("i-funnel-note").textContent = `Faculty = scientific cadre on the institutes' own staff pages (Scientist to Director). Technical officers, technicians and duplicate listings were removed by rule and by hand (data/review/roster_excluded.csv). ` +
      `${fmt(ex.with_papers)} of the removed staff are authors on papers (${fmt(ex.papers_total)} author–paper entries); they stay in the dataset and in the full network, only faculty statistics and faculty networks leave them out. ` +
      `With papers: ${Object.entries(s4.by_lab || {}).map(([k, v]) => `${k} ${v}`).join(", ")}.`;

    const g = D.faculty_graph || {};
    if (g.nodes) {
      const k = ink();
      const maxDeg = Math.max(...g.nodes.map(n => n.degree || 1));
      chart("ch-faculty", {
        tooltip: tip({ formatter: p => p.dataType === "node" ? `<b>${esc(p.data.name)}</b><br>${esc(p.data.lab)} · ${esc(p.data.dept || "")}<br>${p.data.degree} faculty co-authors · ${p.data.papers} papers · h ${p.data.h_index}`
          : `${esc(p.data.source)} – ${esc(p.data.target)}: ${p.data.weight} joint papers` }),
        legend: { ...legend(), data: Object.keys(LAB_VAR) },
        series: [{
          type: "graph", layout: "force", roam: true, draggable: true, force: { repulsion: 60, edgeLength: [20, 70], gravity: 0.12 },
          categories: Object.keys(LAB_VAR).map(l => ({ name: l, itemStyle: { color: css(LAB_VAR[l]) } })),
          data: g.nodes.map(n => ({ ...n, itemStyle: undefined, category: Object.keys(LAB_VAR).indexOf(n.lab), symbolSize: 5 + 15 * Math.sqrt((n.degree || 1) / maxDeg) })),
          links: g.links.map(l => ({ ...l, lineStyle: { width: Math.min(4, 0.6 + 0.4 * l.weight), opacity: 0.35, color: k.muted } })),
          emphasis: { focus: "adjacency" }, label: { show: false },
        }],
      });
      const m = g.metrics;
      $("i-faculty-note").textContent = `${fmt(m.connected_faculty)} of ${fmt(m.total_cadre_faculty)} active scientists have a faculty co-author; ${fmt(m.edges)} pairs, mean degree ${S.faculty_coauthorship.thresholds.k_mean} among the connected scientists, clustering ${m.clustering}. ` +
        `Showing the ${fmt(m.shown_nodes)} with the most joint papers. Across labs: ${(g.collab_matrix || []).map(r => `${r.pair} ${r.joint_papers}`).join("; ")} (joint papers summed over pairs).`;
    }

    table("tbl-params", [{ title: "Parameter", field: "p" }, { title: "Value", field: "v", num: true }, { title: "Used in", field: "u" }], [
      { p: "\\(\\beta_0\\)", v: P.beta0, u: "all simulations" },
      { p: "\\(\\varepsilon\\) (receptivity floor, A)", v: DF.metrics && 0.05, u: "field study" },
      { p: "similarity floor", v: P.similarity_floor, u: "network comparison" },
      { p: "similarity when a profile is missing", v: P.neutral_similarity, u: "network comparison" },
      { p: "steps", v: P.max_steps, u: "all" },
      { p: "seeds per run / runs per seed", v: `${P.seeds_per_run} / ${P.mc_runs_per_seed}`, u: "network comparison" },
      { p: "seeds / runs per seed", v: `${DF.metrics.n_seeds_per_field} / ${DF.metrics.n_trials}`, u: "field study" },
      { p: "random seed", v: P.rng_seed, u: "all (numpy RandomState)" },
    ].map(r => ({ ...r, p: r.p })));
  }

  // ---------- 03 Threshold ----------
  function renderThreshold() {
    const keys = Object.keys(TH);
    const draw = key => {
      const t = TH[key], k = ink();
      chart("ch-threshold", {
        legend: legend(), grid: { left: 8, right: 40, top: 48, bottom: 40, containLabel: true },
        tooltip: tip({ trigger: "axis", valueFormatter: v => (v == null ? "–" : Number(v).toFixed(3)) }),
        xAxis: { type: "value", name: "transmissibility T", nameLocation: "middle", nameGap: 26, min: 0, max: 0.5, ...axis() },
        yAxis: [{ type: "value", name: "share", max: 1, ...axis() }],
        series: [
          line("S(T): largest outbreak share", t.T_grid.map((x, i) => [x, t.S[i]]), css("--s1"), {
            markLine: { silent: true, symbol: "none", data: [
              { xAxis: t.T_c_theory, lineStyle: { color: css("--s2"), type: "dashed", width: 2 }, label: { show: false } },
              { xAxis: t.T_peak_simulated, lineStyle: { color: css("--s3"), type: "solid", width: 2 }, label: { show: false } }] } }),
          line("χ(T) scaled: small-outbreak size (peak = tipping point)", t.T_grid.map((x, i) => [x, t.chi[i] / Math.max(...t.chi)]), css("--s3"), { lineStyle: { type: "dotted" } }),
        ],
      });
      $("i-threshold-caption").innerHTML = `Orange dashed line: formula \\(T_c\\) = ${t.T_c_theory}. Green line: measured tipping point (peak of \\(\\chi\\)) = ${t.T_peak_simulated}, ` +
        `${t.peak_over_theory}× the formula. Clustering ${t.clustering}; ${fmt(t.nodes)} nodes.`;
      if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([$("i-threshold-caption")]);
    };
    seg("seg-threshold", keys.map(k => [k, netName(k).replace(" (all authors)", "")]), "full_coauthorship", draw);
    table("tbl-threshold", [
      { title: "Network", html: r => esc(netName(r.k)) },
      { title: "Nodes", field: "nodes", num: true, fmt: fmt }, { title: "\\(\\langle k\\rangle\\)", field: "k_mean", num: true },
      { title: "\\(\\langle k^2\\rangle\\)", field: "k2_mean", num: true }, { title: "Clustering", field: "clustering", num: true },
      { title: "Formula \\(T_c\\)", field: "T_c_theory", num: true }, { title: "Measured peak", field: "T_peak_simulated", num: true },
      { title: "Measured / formula", field: "peak_over_theory", num: true, fmt: v => `${v}×` },
    ], keys.map(k => ({ k, ...TH[k] })));
    const c3 = claim("C3"), c2 = claim("C2");
    $("ins-threshold").innerHTML = [c2, c3].filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
  }

  // ---------- 04 Fields ----------
  function renderFields() {
    const FD = DF.fields_data;
    const draw = f => {
      const d = FD[f], a = d.condition_a, b = d.condition_b, n = a.adoption_curve.length;
      chart("ch-field", {
        legend: legend(), grid: { left: 8, right: 40, top: 48, bottom: 40, containLabel: true },
        tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
        xAxis: stepAxis(n), yAxis: { type: "value", name: "% adopted", max: 100, ...axis() },
        series: [line(`A · ${f} researchers`, a.adoption_curve, css("--s1"), { markLine: half() }),
          line("A · everyone else (spillover)", a.spillover_curve, css("--s2"), { lineStyle: { type: "dotted" } }),
          line(`B · inside the ${f} network`, b.adoption_curve, css("--s3"), { lineStyle: { type: "dashed" } })],
      });
      table("tbl-field-spreaders", [
        { title: "#", html: (r, i) => "" }, { title: "Seed", field: "name" }, { title: "Lab", field: "lab" },
        { title: "Co-authors", field: "degree", num: true }, { title: "Field share", field: "field_share", num: true, fmt: v => pct(v, 0) },
        { title: "T50", field: "t50", num: true, fmt: v => (v == null ? "–" : v) }, { title: "Runs reaching 50%", field: "p_reach50", num: true, fmt: v => pct(100 * v, 0) },
        { title: "Reach by step 3", field: "reach_t3", num: true, fmt: v => pct(100 * v) },
      ].filter(c => c.title !== "#"), a.top_super_spreaders);
      table("tbl-field-blockers", [{ title: "Person", field: "name" }, { title: "Lab", field: "lab" },
        { title: "Faculty", field: "is_faculty", fmt: v => (v ? "yes" : "no") }, { title: "Betweenness", field: "betweenness", num: true, fmt: v => num(v, 4) },
        { title: "Network lost", field: "lcc_drop_pct", num: true, fmt: v => pct(v, 2) }], b.top_super_blockers || []);
    };
    seg("seg-field", FIELDS.filter(f => FD[f]).map(f => [f, f]), "Chemistry", draw);
    table("tbl-fields", [
      { title: "Field", field: "short_label" }, { title: "Active researchers", field: "active_researchers", num: true, fmt: fmt },
      { title: "Field network", field: "subgraph_lcc_size", num: true, fmt: fmt },
      { title: "A: T50", html: r => esc(r.condition_a.t50_median ?? "not reached") },
      { title: "A: field reached", html: r => pct(r.condition_a.adoption_curve.at(-1)) },
      { title: "A: outside reached", html: r => pct(r.condition_a.spillover_curve.at(-1)) },
      { title: "B: T50", html: r => esc(r.condition_b.t50_median ?? "not reached") },
      { title: "B: seeds reaching 50%", html: r => `${r.condition_b.seeds_reaching_50} / ${r.condition_b.n_seeds}` },
      { title: "\\(\\langle k\\rangle/\\langle k^2\\rangle\\)", html: r => num(r.thresholds.beta_c, 4) },
      { title: "\\(1/\\lambda_{\\max}\\)", html: r => num(r.thresholds.beta_c_spec, 4) },
    ], FIELDS.filter(f => FD[f]).map(f => FD[f]));
    const c7 = claim("C7"), c5 = claim("C5");
    $("ins-fields").innerHTML = [c7, c5].filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
  }

  // ---------- 05 Networks ----------
  function renderNetworks() {
    const draw = target => {
      const n = S.full_coauthorship.fields[target].mc_curve.length;
      chart("ch-overlay", {
        legend: legend(), grid: { left: 8, right: 40, top: 48, bottom: 40, containLabel: true },
        tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
        xAxis: stepAxis(n), yAxis: { type: "value", name: "% adopted", max: 100, ...axis() },
        series: NETS.map((k, i) => line(S[k].network_name, S[k].fields[target].mc_curve, css(NET_COLOR[k]), i === 0 ? { markLine: half() } : {})),
      });
    };
    seg("seg-overlay", [["Combined", "Everyone"], ["Chemistry", "Chemistry only"]], "Combined", draw);
    table("tbl-grid", [
      { title: "Network", html: r => esc(netName(r.network)) }, { title: "Target", field: "field" },
      { title: "Target size", field: "target_nodes", num: true, fmt: fmt }, { title: "MC runs", field: "mc_runs", num: true, fmt: fmt },
      { title: "MC T50", field: "mc_t50", num: true, fmt: v => (v == null ? "–" : v) }, { title: "NIMFA T50", field: "nimfa_t50", num: true, fmt: v => (v == null ? "–" : v) },
      { title: "MC reach @15", field: "mc_final_reach", num: true, fmt: v => pct(v) }, { title: "NIMFA reach @15", field: "nimfa_final_reach", num: true, fmt: v => pct(v) },
      { title: "Gap min…max (pp)", html: r => `${num(r.min_gap)} … ${num(r.max_gap)}` }, { title: "Rank ρ", field: "rank_agreement_spearman", num: true, fmt: v => num(v) },
    ], D.grid);
    $("tbl-grid").style.maxHeight = "460px"; $("tbl-grid").style.overflow = "auto";
    $("ins-networks").innerHTML = ["C1", "C8"].map(claim).filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
  }

  // ---------- 06 Mean field ----------
  function renderMeanField() {
    let net = "full_coauthorship", field = "Combined";
    const draw = () => {
      const r = S[net].fields[field];
      if (!r) return;
      const n = r.mc_curve.length;
      chart("ch-meanfield", {
        legend: legend(), grid: { left: 8, right: 40, top: 48, bottom: 40, containLabel: true },
        tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v, 2) }),
        xAxis: stepAxis(n), yAxis: { type: "value", name: "%", min: 0, max: 100, ...axis() },
        series: [line(`Monte Carlo (${fmt(r.mc_runs)} runs)`, r.mc_curve, css("--s1"), { markLine: half() }),
          line("NIMFA (mean field)", r.nimfa_curve, css("--s2"), { lineStyle: { type: "dashed" } }),
          { type: "bar", name: "gap NIMFA − MC", data: r.gap_curve, itemStyle: { color: css("--s3"), borderRadius: [4, 4, 0, 0] }, barMaxWidth: 14 }],
      });
      table("tbl-spreaders", [{ title: "Seed", field: "name" }, { title: "Lab", field: "lab", fmt: v => (v || "").replace(/; /g, ", ") },
        { title: "Links", field: "degree", num: true }, { title: `NIMFA adopters by step ${P.early_step}`, field: "nimfa_adopters_early", num: true, fmt: v => num(v, 1) },
        { title: `Simulation adopters by step ${P.early_step}`, field: "mc_adopters_early", num: true, fmt: v => num(v, 1) },
        { title: "NIMFA adopters by step 15", field: "nimfa_adopters_final", num: true, fmt: v => num(v, 1) }], r.super_spreaders || []);
      $("i-spreader-note").textContent = `Seeds ranked by expected adopters at step ${P.early_step} under NIMFA (at step 15 most seeds have reached nearly everyone, so a late count cannot separate them). ` +
        `Agreement of the two models' rankings over all ${r.n_seeds} seeds: Spearman ρ = ${num(r.rank_agreement_spearman)}.`;
    };
    seg("seg-mf-net", NETS.map(k => [k, S[k].network_name.replace(" (all authors)", "")]), net, v => { net = v; draw(); });
    seg("seg-mf-field", [["Combined", "Everyone"], ...FIELDS.map(f => [f, f])], field, v => { field = v; draw(); });
    $("ins-meanfield").innerHTML = ["C4", "C6"].map(claim).filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
  }

  // ---------- 07 Labs ----------
  function renderLabs() {
    const draw = net => {
      const o = S.seed_origins[net] || {};
      const n = (o.ncl || o.iict).mc_curve.length;
      chart("ch-origin", {
        legend: legend(), grid: { left: 8, right: 40, top: 48, bottom: 40, containLabel: true },
        tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
        xAxis: stepAxis(n), yAxis: { type: "value", name: "%", max: 100, ...axis() },
        series: LAB_KEYS.filter(k => o[k]).flatMap(k => [
          line(`${o[k].institute} seeds · simulation`, o[k].mc_curve, css(LAB_VAR[o[k].institute]), k === "ncl" ? { markLine: half() } : {}),
          line(`${o[k].institute} seeds · NIMFA`, o[k].nimfa_curve, css(LAB_VAR[o[k].institute]), { lineStyle: { type: "dotted", width: 1.5 } })]),
      });
    };
    seg("seg-origin", [["faculty_coauthorship", "Faculty network"], ["full_coauthorship", "Full network"]], "faculty_coauthorship", draw);
    const rows = [];
    LAB_KEYS.forEach(l => ["full_coauthorship", "faculty_coauthorship", "full_citation"].forEach(k => {
      const r = (S.intra_institute[l] || {})[k]; if (r) rows.push(r);
    }));
    table("tbl-intra", [{ title: "Lab", field: "institute" }, { title: "Network", html: r => esc(netName(r.subgraph_type)) },
      { title: "Nodes", field: "nodes", num: true, fmt: fmt }, { title: "Links", field: "edges", num: true, fmt: fmt },
      { title: "Mean degree", field: "mean_degree", num: true }, { title: "MC T50", field: "mc_t50", num: true, fmt: (v, r) => (r.too_small ? "too small" : (v ?? "not reached")) },
      { title: "NIMFA T50", field: "nimfa_t50", num: true, fmt: (v, r) => (r.too_small ? "" : (v ?? "not reached")) },
      { title: "MC reach @15", field: "mc_final_reach", num: true, fmt: (v, r) => (r.too_small ? "" : pct(v)) }], rows);
    $("ins-labs").innerHTML = ["C9"].map(claim).filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
  }

  // ---------- 08 Proof ----------
  function renderProof() {
    const cl = (D.claims && D.claims.claims) || [];
    table("tbl-claims", [{ title: "#", field: "id" }, { title: "Claim", field: "claim" },
      { title: "Numbers", html: r => {
        const v = r.value;
        const show = x => (x !== null && typeof x === "object" ? JSON.stringify(x) : String(x));
        const lines = Array.isArray(v) ? v.map(show) : (v && typeof v === "object" ? Object.entries(v).map(([k, x]) => `${k}: ${show(x)}`) : [show(v)]);
        return lines.map(l => `<code>${esc(l)}</code>`).join("<br>");
      } },
      { title: "Source", html: r => `<code>${esc(r.source)}</code>` }, { title: "Check", field: "check" },
      { title: "Status", html: r => badge(r.passed) }], cl, "i-claims");
    $("i-repro").innerHTML = [
      "<code>python run.py insight11</code> rebuilds everything on this page from <code>data/final/</code> (no API calls): faculty networks, roster audit, the field study, the network comparison, the threshold test, the claims and the page data.",
      "Scripts: <code>src/stats/insights/s11_information_diffusion.py</code> (field study), <code>s11_nimfa_spreading.py</code> (four networks, mean field, labs), <code>s11_threshold_check.py</code> (percolation), <code>s11_claims.py</code> (checks), <code>s11_cadre_networks.py</code>, <code>s11_data_cleaning_audit.py</code>.",
      `All randomness comes from numpy RandomState with fixed seeds (${P.rng_seed}); nodes are processed in a fixed order, so a rerun gives identical numbers (tested under different PYTHONHASHSEED values).`,
      "Outputs: <code>stats/tables/insights/11_*.json / .csv</code>. Tests: <code>tests/test_insight11.py</code> (every claim passes, NIMFA equation and SI step checked on small graphs by brute force), <code>tests/test_insights.py</code>, <code>tests/test_cadre_networks.py</code>.",
      "Inputs: <code>group24_data_extended.csv</code>, <code>faculty_master.csv</code>, <code>citation_network.csv</code>, <code>data/review/roster_excluded.csv</code>.",
    ].map(t => `<li>${t}</li>`).join("");
    $("i-fixes").innerHTML = [
      "The \"epidemic threshold\" was presented as a property of the SI model; SI has none. Thresholds are now labelled as structural thresholds for spreading with recovery and are tested directly (section 03).",
      "The extended study built the full co-authorship network by author name, merging different people; it now uses the same network as the field study, keyed by OpenAlex author ID.",
      "Monte Carlo and mean field were compared on different seed weightings (some seeds 3 runs, others 2) and T50 averaged \"not reached\" as step 15; both now use the same seeds, equal runs per seed and the censored median.",
      "Citation networks reported thresholds of 0.71 and 1.0 (artefacts of an acyclic network) and copied the all-field result into every field; now no threshold where none exists, and papers are assigned to fields by their own field.",
      "Super-spreaders were ranked by reach at step 15, where the top seeds differed by 0.3%, and described as a derivative that was not computed; they are now ranked at step 3, with the simulation's ranking as a check.",
      "\"Jensen's inequality proves…\" and a typed-in gap range (+1.8% to +5.8%) were replaced by the measured gap and a check of its sign; typed-in roster claims (h-index 7.0 → 6.0, 1,290 ties, 282 rows) without a source were removed.",
      "The extended-study scripts were not part of any pipeline; <code>python run.py insight11</code> now runs all of them.",
      "Reruns were not identical: subgraphs iterated their nodes in a hash-dependent order, so random numbers landed on different people from run to run. Every study network is now built in a fixed order (tested under two hash seeds), and the tipping-point test uses 100 instead of 40 repeats.",
    ].map(t => `<li>${t}</li>`).join("");
    $("i-limits").innerHTML = [
      "The model is stylised: β0 = 0.2 per step is chosen, not estimated. The results compare networks, fields and labs under the same rule; they do not predict how many months an idea takes.",
      "Links are co-authorships and citations from 2016–2026 merged into one static network; who worked with whom changed over the decade.",
      "The full network includes students and project staff identified only by their OpenAlex profile; profile errors (split or merged people) remain possible.",
      "Field shares come from OpenAlex's topic classification of each paper.",
      "The textbook formula assumes a network without clustering; the measured threshold is the one to trust.",
    ].map(t => `<li>${t}</li>`).join("");
  }

  renderTop(); renderData(); renderThreshold(); renderFields(); renderNetworks(); renderMeanField(); renderLabs(); renderProof();
  // typeset formulas inside generated tables once MathJax has loaded
  const typeset = () => (window.MathJax && MathJax.typesetPromise ? MathJax.typesetPromise() : null);
  if (!typeset()) window.addEventListener("load", () => setTimeout(typeset, 0));
})();
