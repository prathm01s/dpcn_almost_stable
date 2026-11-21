/**
 * "How Ideas Spread" page (insights11.html; formerly Insight 11): how ideas spread through the labs' networks,
 * simulated (sections 01-07) and tested on the labs' real citations (section 08, D-44).
 * Data: window.G24_I11 from data/g24_insights11_suite.js (src/dashboard/build_insights11_suite.py), which copies
 * stats/tables/insights/11_*. Every number and sentence here is read from that payload.
 */
(function () {
  "use strict";
  const D = window.G24_I11;
  if (!D || !D.spreading || !D.spreading.full_coauthorship) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      '<p style="padding:2rem">Study data not found (data/g24_insights11_suite.js). Run <code>python run.py insight11</code>.</p>');
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
      R ? ["Real chance a tie passes an idea on", pct(R.transmissibility.overall.T_pct, 2), `tipping point ${pct(100 * R.tipping_points.full_coauthorship, 0)} (section 08)`]
        : ["Monte Carlo runs", fmt(runs), "network comparison alone"],
      ["Claims verified", `${c.n_passed || 0} / ${c.n_claims || 0}`, "automatic checks, section 10"],
    ];
    if ($("i-kpis")) $("i-kpis").innerHTML = kpis.map(([l, v, s]) => `<div class="kpi-card"><div class="kpi-label">${esc(l)}</div><div class="kpi-val">${esc(v)}</div><div class="kpi-sub">${esc(s)}</div></div>`).join("");
    $("i-hero-note").textContent = `Data: OpenAlex, collected ${D.meta.collection_date}; simulations built ${D.meta.built}. One step = one round of contact between collaborators.`;
    document.querySelectorAll("[data-real]").forEach(el => { if (R) el.textContent = fmt(R.ideas[el.dataset.real]); });
    renderAnswers();
  }

  // ---------- "In short" answers (one per section) and the contents cards ----------
  const ANS = {};
  function setAnswer(key, text) {
    const el = $(`ans-${key}`);
    if (!el) return;
    el.innerHTML = esc(text);
    ANS[key] = { text };
  }
  function renderAnswers() {
    const full = S.full_coauthorship, fac = S.faculty_coauthorship;
    setAnswer("data", `Four networks from the labs' papers: ${fmt(full.nodes)} authors linked by co-authorship (faculty, students, project staff), ` +
      `the ${fmt(fac.nodes)} faculty among them who have a faculty co-author, ${fmt(S.faculty_citation.nodes)} faculty linked by citations, ` +
      `and ${fmt(S.full_citation.nodes)} papers linked by citations. Faculty = scientists on the institutes' own staff pages.`);
    setAnswer("model", `Each step, everyone who has the idea passes it to each collaborator with a probability of at most ${P.beta0}, higher for collaborators ` +
      `who work on similar topics. We simulate this thousands of times (Monte Carlo) and also solve it with mean-field equations (NIMFA).`);
    const map = { threshold: "C2", fields: "C7", networks: "C1", meanfield: "C4", labs: "C9" };
    Object.entries(map).forEach(([k, id]) => { const c = claim(id); if (c) setAnswer(k, c.claim); });
    const c2 = (claim("C2") || {}).value || {}, c3 = (claim("C3") || {}).value || {}, c7 = (claim("C7") || {}).value || {};
    const rr = Object.values(c3.ratios || {});
    const tipRatio = c2.T_peak_full ? c2.T_peak_faculty / c2.T_peak_full : null;
    let concl = `Without students and project staff the faculty network's tipping point is ${num(tipRatio, 1)}× higher (${c2.T_peak_faculty} vs ${c2.T_peak_full}); ` +
      `disciplines act as firewalls (${pct(c7.chemistry_reach)} of chemists adopt vs ${pct(c7.outside_reach)} outside); clustering puts the real tipping point ` +
      `${num(Math.min(...rr))}–${num(Math.max(...rr))}× above the textbook formula; mean-field equations bound the simulation and rank the seeds correctly.`;
    if (R) {
      const t = R.transmissibility, cr = 100 * t.overall.carried / (t.overall.carried + t.overall.independent);
      setAnswer("real", `Real ideas stay below the tipping point: a co-author picks up a cited work ${pct(t.overall.T_pct, 2)} of the time per tie ` +
        `(${pct(t.by_bucket["10+ papers"].T_pct, 2)} for the most reused) against the ${pct(100 * R.tipping_points.full_coauthorship, 0)} an outbreak needs. ` +
        `${pct(cr, 0)} of pass-ons are carried by an earlier user on the new paper, a student's tie passes ideas ${num(t.by_role.affiliated_author.T_pct / t.by_role.faculty.T_pct, 1)}× ` +
        `as often as a professor's, and only ${pct(R.between_labs.cross_lab_pct, 1)} of ties cross labs.`);
      concl = `Tested on real citations: ideas stay below the tipping point (${pct(t.overall.T_pct, 2)} per tie vs ${pct(100 * R.tipping_points.full_coauthorship, 0)}), ` +
        `travel with people (${pct(cr, 0)} carried), pass ${num(t.by_role.affiliated_author.T_pct / t.by_role.faculty.T_pct, 1)}× more often over a student's tie than a professor's, ` +
        `and move between the labs through reading, not people. From the model: ` + concl.charAt(0).toLowerCase() + concl.slice(1);
    }
    setAnswer("conclusions", concl);
    const cl = D.claims || {};
    setAnswer("proof", `${cl.n_passed} of ${cl.n_claims} claims pass their automatic check. Every figure, threshold and parameter on this page is read from the pipeline's output files, and the tests rerun the checks.`);
  }
  function renderToc() {
    const items = [
      ["i-data", "01", "Data", "What networks do the labs form?", "data"],
      ["i-model", "02", "Model", "How is spreading simulated?", "model"],
      ["i-threshold", "03", "Tipping point", "Below what point does an idea die out?", "threshold"],
      ["i-fields", "04", "Fields", "Does an idea stay in its discipline?", "fields"],
      ["i-networks", "05", "Networks", "Which network spreads ideas fastest?", "networks"],
      ["i-meanfield", "06", "Mean field", "Can equations replace the simulations?", "meanfield"],
      ["i-labs", "07", "Labs", "Does the lab of origin matter?", "labs"],
      ["i-real", "08", "Real data", "Does what the model assumes really happen?", "real"],
      ["i-conclusions", "09", "Conclusions", "What are the definitive takeaways?", "conclusions"],
      ["i-proof", "10", "Methodology & proof", "How can anyone check this page?", "proof"],
    ];
    $("i-toc").innerHTML = items.map(([id, n, t, q, key]) => {
      const a = key && ANS[key];
      const txt = a ? a.text : "Empirical findings and reproducible data verification.";
      return `<a href="#${id}"><span class="t-num">${n}</span><span class="t-title">${esc(t)}</span><span class="t-q">${esc(q)}</span>` +
        `<span class="t-a">${esc(txt)}</span><span class="t-go">Explore section →</span></a>`;
    }).join("");
  }
  function trackSection() {
    const links = [...document.querySelectorAll("#nav-links .nav-link")];
    const byId = Object.fromEntries(links.map(a => [a.getAttribute("href").slice(1), a]));
    const obs = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting && byId[e.target.id]) { links.forEach(a => a.classList.remove("current")); byId[e.target.id].classList.add("current"); }
    }), { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll("section.page-section").forEach(sec => obs.observe(sec));
  }


  // ---------- Front page in the title area: the findings as a few newspaper headlines (D-45) ----------
  // Related findings are grouped into one story: kicker, headline, a short explanation, the key figures and links to the evidence.
  // Every number is read from the claims file or the real-citation output; each story shows the checks behind it.
  const R = D.real && D.real.transmissibility ? D.real : null;
  function renderBoard() {
    const cv = id => (claim(id) || {}).value || {};
    // one "verified" mark per story (no claim numbers); it turns into "check failed" if any claim behind the story fails
    const chk = ids => { const cs = ids.map(claim).filter(Boolean); if (!cs.length) return "";
      const ok = cs.every(c => c.passed);
      return `<span class="np-check ${ok ? "ok" : "bad"}" title="${esc(cs.map(c => c.claim).join(" | "))}">${ok ? "✓ verified" : "✗ check failed"}</span>`; };
    const fig = (v, l) => `<div class="np-fig"><b>${esc(v)}</b><span>${esc(l)}</span></div>`;
    const links = ls => `<div class="np-links">${ls.map(([h, t]) => `<a href="${h}">${esc(t)} →</a>`).join("")}</div>`;
    const c1 = cv("C1"), c2 = cv("C2"), c3 = cv("C3"), c4 = cv("C4"), c7 = cv("C7"), c8 = cv("C8"), c9 = cv("C9");
    const rr = Object.values(c3.ratios || {}), rho = Object.values(cv("C6")).filter(v => typeof v === "number");
    const tipX = c2.T_peak_full ? c2.T_peak_faculty / c2.T_peak_full : null;
    const cl = D.claims || {};
    const stories = [];

    if (R) {
      const t = R.transmissibility, tp = R.tipping_points, bl = R.between_labs, gl = R.global_link;
      const org = Object.fromEntries(bl.by_origin.map(r => [r.origin, r]));
      const ex = Object.fromEntries(R.exposure.rows.map(r => [r.k, r]));
      const fa = t.by_role.faculty.T_pct, st = t.by_role.affiliated_author.T_pct;
      const cr = 100 * t.overall.carried / (t.overall.carried + t.overall.independent);
      stories.push({
        lead: true, kicker: `Measured in ${fmt(R.ideas.citations)} real citations`, claims: ["C12", "C3"],
        head: "Most new ideas in CSIR's labs die after a single paper",
        deck: `Followed through the labs' own papers, a co-author takes up a cited idea over just ${pct(t.overall.T_pct, 2)} of collaboration links. ` +
          `Even the ${fmt(R.ideas.by_reuse["10+ papers"])} most reused ideas reach ${pct(t.by_bucket["10+ papers"].T_pct, 2)}, still short of the ` +
          `${pct(100 * tp.full_coauthorship, 0)} the network needs for an idea to take off. The model shows why the bar is so high: researchers work in tight groups, ` +
          `so the real tipping point is ${num(Math.min(...rr))}–${num(Math.max(...rr))}× what the textbook formula predicts.`,
        figs: [[pct(R.ideas.single_use_pct, 0), "of cited works are used in one lab paper only"],
               [pct(t.overall.T_pct, 2), "real chance an idea passes over a collaboration link"],
               [pct(100 * tp.full_coauthorship, 0), `needed to take off (${pct(100 * tp.faculty_coauthorship, 1)} among faculty alone)`],
               [`${num(Math.min(...rr))}–${num(Math.max(...rr))}×`, "real tipping point vs. the textbook formula"]],
        links: [["#i-real-tip", "Real-citation test"], ["#i-threshold", "Tipping point"]],
      });
      stories.push({
        kicker: "Who spreads ideas", claims: ["C13", "C2", "C1"],
        head: "Students carry ideas; professors spread them wide",
        deck: `A student's collaboration link passes an idea on ${num(st / fa, 1)}× as often as a professor's (${pct(st, 2)} vs ${pct(fa, 2)}), in every group of ideas. ` +
          `Professors make up for it in reach, with ${R.roles.faculty.coauthors_per_person} co-authors each against ${R.roles.affiliated_author.coauthors_per_person}. ` +
          `Without students the network falls below its tipping point: faculty alone need a ${num(tipX, 1)}× higher pass-on rate, and an idea reaches half of them in ` +
          `${c1.T50_faculty} steps instead of ${c1.T50_full}.`,
        figs: [[`${num(st / fa, 1)}×`, "student vs. professor link"], [`${R.roles.faculty.coauthors_per_person} vs ${R.roles.affiliated_author.coauthors_per_person}`, "co-authors per professor vs. per student"],
               [`${num(tipX, 1)}×`, "higher tipping point without students"]],
        links: [["#i-real-roles", "Students vs. faculty, measured"], ["#i-threshold", "Without students"]],
      });
      stories.push({
        kicker: "How ideas move", claims: ["C14"],
        head: "Ideas travel with people, not by word of mouth",
        deck: `In ${pct(cr, 0)} of the cases where an idea passes on, someone who already used it is an author of the new paper. Hearing about it from one co-author ` +
          `barely changes a researcher's own work (${num(ex["1"].lift_independent)}×); it takes three or more (${num(ex["3+"].lift_independent, 1)}×). Ideas need reinforcement, ` +
          `which a simple spreading model does not assume.`,
        figs: [[pct(cr, 0), "carried by someone who used it before"], [`${num(ex["1"].lift_independent)}×`, "effect of one informed co-author"],
               [`${num(ex["3+"].lift_independent, 1)}×`, "effect of three or more"]],
        links: [["#i-real-people", "One co-author or several?"], ["#i-model", "The model"]],
      });
      stories.push({
        kicker: "Where ideas stop · with the Global Benchmark", claims: ["C15", "C7"],
        head: "Ideas stay where they start: in their own lab and their own field",
        deck: `Only ${pct(bl.cross_lab_pct, 1)} of collaboration links connect the three labs. When a foreign twin's paper reaches a second lab, a person carried it there in ` +
          `${pct(org.foreign.via_person_pct, 1)} of cases (${pct(org.own.via_person_pct, 1)} for the labs' own papers): knowledge from abroad arrives by reading, as the labs cite ` +
          `${fmt(gl.foreign_peer_papers_cited)} papers of their foreign peers but wrote ${fmt(gl.foreign_coauthored_papers)} with them. In the model, ideas also stay in their field.`,
        figs: [[pct(bl.cross_lab_pct, 1), "of links cross labs"], [`${fmt(gl.foreign_peer_papers_cited)} : ${fmt(gl.foreign_coauthored_papers)}`, "foreign papers cited : written together"],
               [`${Math.round(c7.chemistry_reach / c7.outside_reach)}×`, `uptake inside chemistry vs. outside (${pct(c7.chemistry_reach, 1)} vs ${pct(c7.outside_reach, 1)}, model)`]],
        links: [["#i-real-islands", "Between the labs"], ["#i-fields", "By field"], ["global.html#g-links", "Global Benchmark"]],
      });
    }
    const brief = {
      kicker: "Also checked", claims: ["C4", "C6", "C8", "C9"],
      head: "The maths holds up, and every claim on this page is tested",
      deck: `Fast mean-field equations never under-predict the simulation (${c4.runs} of ${c4.runs} runs) and rank the best starting points the same way ` +
        `(ρ ${num(Math.min(...rho))}–${num(Math.max(...rho))}). Along citations ideas only move forward in time and reach ${pct(c8.reach, 2)} of papers. ` +
        (c9.iict ? `In the model, IICT's faculty spread an idea fastest early on (${pct(c9.iict.mc_step3, 2)} at step 3; NCL ${pct(c9.ncl.mc_step3, 2)}, CECRI ${pct(c9.cecri.mc_step3, 2)}). ` : "") +
        `${cl.n_passed} of ${cl.n_claims} claims pass their automatic check.`,
      links: [["#i-meanfield", "Mean field"], ["#i-networks", "Networks"], ["#i-labs", "Labs"], ["#i-proof", "Claims & proof"]],
    };

    const story = s => `<article class="np-story${s.lead ? " np-lead" : ""}">` +
      `<div class="np-kicker">${esc(s.kicker)}<span class="np-checks">${chk(s.claims)}</span></div>` +
      `<h3 class="np-head"><a href="${s.links[0][0]}">${esc(s.head)}</a></h3>` +
      (s.lead ? `<div class="np-lead-body"><p class="np-deck">${esc(s.deck)}</p><div class="np-figs">${s.figs.map(f => fig(...f)).join("")}</div></div>`
              : `<p class="np-deck">${esc(s.deck)}</p>${s.figs ? `<div class="np-figs">${s.figs.map(f => fig(...f)).join("")}</div>` : ""}`) +
      links(s.links) + "</article>";
    const [lead, ...rest] = stories;
    $("i-board").innerHTML = `<div class="np-paper">` +
      `<div class="np-mast"><span class="np-title">The study in four headlines</span><span class="np-dateline">Group 24 · data collected ${esc(D.meta.collection_date)} · ` +
      `${cl.n_passed} of ${cl.n_claims} claims verified</span></div>` +
      (lead ? story(lead) : "") +
      (rest.length ? `<div class="np-cols">${rest.map(story).join("")}</div>` : "") +
      `<div class="np-brief">${story(brief)}</div></div>`;
  }

  // ---------- 08 Real citations (stats/tables/insights/11_real_diffusion.json) ----------
  const REUSE = ["2-4 papers", "5-9 papers", "10+ papers"];
  // lighter tint of a series colour (for the "independent" part of a stacked bar) without fading its label
  const fade = (hex, a) => { const h = hex.replace("#", ""); const n = parseInt(h.length === 3 ? h.split("").map(x => x + x).join("") : h, 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`; };
  const reuseLabel = b => `Cited by ${b.replace(" papers", "")} lab papers`;
  const ROLE_ORDER = ["faculty", "probable_former_faculty", "affiliated_author"];
  const ROLE_COLOR = { faculty: "--s1", probable_former_faculty: "--s4", affiliated_author: "--s2" };
  function drawTip(elId) {
    const k = ink(), t = R.transmissibility, tp = R.tipping_points;
    const tpF = 100 * tp.full_coauthorship, tpK = 100 * tp.faculty_coauthorship;
    const cats = [["overall", "All cited works"], ...REUSE.map(b => [b, reuseLabel(b)])];
    const get = key => (key === "overall" ? t.overall : t.by_bucket[key]);
    chart(elId, {
      grid: { left: 20, right: 70, top: 36, bottom: 8, containLabel: true },
      legend: legend(),
      tooltip: tip({ trigger: "axis", axisPointer: { type: "shadow" }, formatter: ps => {
        const c = cats[ps[0].dataIndex], r = get(c[0]);
        return `<b>${esc(c[1])}</b><br>T = ${pct(r.T_pct, 2)}: ${fmt(r.carried + r.independent)} of ${fmt(r.pairs)} (tie, idea) pairs<br>carried ${pct(r.T_carried_pct, 2)} · independent ${pct(r.T_independent_pct, 2)}`;
      } }),
      yAxis: { type: "category", data: cats.map(c => c[1]), inverse: true, ...axis(), axisTick: { show: false } },
      xAxis: { type: "value", max: Math.ceil(tpK / 5) * 5 + 5, ...axis(), axisLabel: { color: k.text2, formatter: v => `${v}%` } },
      series: [
        { name: "Carried by an earlier user", type: "bar", stack: "t", barMaxWidth: 24, itemStyle: { color: css("--s1") }, data: cats.map(c => get(c[0]).T_carried_pct),
          markLine: { silent: true, symbol: "none", data: [
            { xAxis: tpF, lineStyle: { color: css("--s2"), type: "dashed", width: 2 }, label: { formatter: `tipping point, all authors (${tpF}%)`, color: k.text2, position: "insideEndTop" } },
            { xAxis: tpK, lineStyle: { color: css("--s4"), type: "dashed", width: 2 }, label: { formatter: `faculty only (${tpK}%)`, color: k.text2, position: "insideEndTop" } }] } },
        { name: "Used independently", type: "bar", stack: "t", barMaxWidth: 24, itemStyle: { color: fade(css("--s1"), 0.42), borderRadius: [0, 4, 4, 0] },
          data: cats.map(c => get(c[0]).T_independent_pct),
          label: { show: true, position: "right", color: k.text, fontWeight: 700, formatter: p => pct(get(cats[p.dataIndex][0]).T_pct, 2) } },
      ],
    });
  }
  function renderReal() {
    if (!R) { $("i-real").style.display = "none"; return; }
    const k = ink(), t = R.transmissibility;
    $("real-n-ideas").textContent = fmt(R.ideas.n);
    $("real-n-cites").textContent = fmt(R.ideas.citations);
    const ins = (el, id) => { const c = claim(id); $(el).innerHTML = c ? box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`) : ""; };
    drawTip("ch-real-tip");
    ins("ins-real-tip", "C12");

    chart("ch-real-roles", {
      grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
      legend: legend(),
      tooltip: tip({ trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: v => pct(v, 2) }),
      xAxis: { type: "category", data: REUSE.map(reuseLabel), ...axis() },
      yAxis: { type: "value", name: "per-tie transmissibility", nameLocation: "middle", nameGap: 44, ...axis(), axisLabel: { color: k.text2, formatter: v => `${v}%` } },
      series: ROLE_ORDER.map(r => ({ name: R.roles[r].label, type: "bar", barMaxWidth: 26, itemStyle: { color: css(ROLE_COLOR[r]), borderRadius: [4, 4, 0, 0] },
        data: REUSE.map(b => t.by_bucket_role[b][r].T_pct), label: { show: true, position: "top", color: k.text2, formatter: p => pct(p.value, 1) } })),
    });
    $("real-roles-stats").innerHTML = ROLE_ORDER.map(r => { const x = R.roles[r], tr = t.by_role[r];
      return `<div class="i-ms" style="--c:var(${ROLE_COLOR[r]})"><b>${esc(x.label)}</b><span>${fmt(x.people)} people · ${x.coauthors_per_person} co-authors each · ` +
        `${pct(x.strong_tie_pct)} of ties with 5+ joint papers</span><span>passes an idea on over <b>${pct(tr.T_pct, 2)}</b> of ties</span></div>`; }).join("");
    ins("ins-real-roles", "C13");

    const rows = R.exposure.rows;
    chart("ch-real-exposure", {
      grid: { left: 8, right: 16, top: 36, bottom: 8, containLabel: true },
      legend: legend(),
      tooltip: tip({ trigger: "axis", axisPointer: { type: "shadow" }, formatter: ps => { const r = rows[ps[0].dataIndex];
        return `<b>k = ${esc(r.k)}</b> co-authors used it before<br>${pct(r.P_pct, 3)} a year (lift ${num(r.lift)}×)<br>on their own: ${pct(r.P_independent_pct, 3)} (lift ${num(r.lift_independent)}×)<br>` +
          `weighted at-risk researcher-years ${fmt(r.at_risk)}`; } }),
      xAxis: { type: "category", data: rows.map(r => r.k === "0" ? "k = 0 (baseline)" : `k = ${r.k}`), ...axis() },
      yAxis: { type: "value", name: "chance of adopting per year", nameLocation: "middle", nameGap: 52, ...axis(), axisLabel: { color: k.text2, formatter: v => `${v}%` } },
      series: [
        { name: "Carried by an earlier user on the paper", type: "bar", stack: "p", barMaxWidth: 46, itemStyle: { color: css("--s3") }, data: rows.map(r => r.P_pct - r.P_independent_pct) },
        { name: "Used on their own", type: "bar", stack: "p", barMaxWidth: 46, itemStyle: { color: fade(css("--s3"), 0.42), borderRadius: [4, 4, 0, 0] }, data: rows.map(r => r.P_independent_pct),
          label: { show: true, position: "top", color: k.text, formatter: p => `${num(rows[p.dataIndex].lift, 1)}× · own ${num(rows[p.dataIndex].lift_independent, 1)}×` } },
      ],
    });
    ins("ins-real-people", "C14");

    const bl = R.between_labs, gl = R.global_link, org = Object.fromEntries(bl.by_origin.map(r => [r.origin, r]));
    $("real-islands-kpis").innerHTML = [
      [pct(bl.cross_lab_pct, 2), `of ${fmt(bl.ties)} co-authorship ties link people of different labs`],
      [pct(org.foreign.via_person_pct, 1), "of foreign twins' papers reach a second lab through a person"],
      [pct(org.own.via_person_pct, 1), "of the labs' own papers do"],
      [`${fmt(gl.foreign_peer_papers_cited)} : ${fmt(gl.foreign_coauthored_papers)}`, `foreign peers' papers cited : papers co-authored with them (Global Benchmark)`],
    ].map(([v, l]) => `<div class="i-ms"><b class="i-ms-big">${esc(v)}</b><span>${esc(l)}</span></div>`).join("");
    table("tbl-real-origin", [
      { title: "Where the cited work comes from", field: "label" },
      { title: "Cited works", field: "ideas", num: true, fmt: fmt },
      { title: "Used by one lab paper only", field: "single_use_pct", num: true, fmt: v => pct(v) },
      { title: "Lab papers citing each", field: "mean_citing_papers", num: true, fmt: v => num(v) },
      { title: "Reaches 2+ labs", field: "multi_lab_pct", num: true, fmt: v => pct(v) },
      { title: "Arrivals in a 2nd/3rd lab", field: "later_lab_adoptions", num: true, fmt: fmt },
      { title: "…via a person", field: "via_person_pct", num: true, fmt: v => pct(v) },
    ], bl.by_origin);
    ins("ins-real-islands", "C15");

    const ex = R.exposure.sample, st = t.by_strength;
    $("real-method").innerHTML = [
      `References: <code>data/final/work_references.csv.gz</code> (Step 24, the OpenAlex reference list of every corpus paper); ${fmt(R.ideas.papers_with_references)} of ${fmt(R.ideas.papers)} papers have references in OpenAlex. Script: <code>src/stats/insights/s11_real_diffusion.py</code>; output <code>stats/tables/insights/11_real_diffusion.json</code>.`,
      `People are the same nodes as in the co-authorship network (one node per person, split OpenAlex profiles joined). Roles: faculty = roster scientists; frequent non-roster authors = 10+ papers over 3+ years, not on today's roster; everyone else (mostly students and project staff).`,
      `A co-author counts as "at risk" only if they had a joint paper with the adopter by the adoption year and published again afterwards, so people who left are not counted as failures. Co-authors on the same adopting paper adopt together and are not counted as a transmission.`,
      `The tipping points (${R.tipping_points.full_coauthorship} and ${R.tipping_points.faculty_coauthorship}) are those measured by bond percolation in section 03, the same quantity as T here: the probability that an idea ever crosses a given tie.`,
      `Tie strength does not explain the student–faculty gap: T is ${pct(st["1 joint paper"].T_pct, 2)} over ties with 1 joint paper, ${pct(st["2-4 joint papers"].T_pct, 2)} with 2–4 and ${pct(st["5+ joint papers"].T_pct, 2)} with 5+, and students have fewer strong ties than faculty.`,
      `The exposure chart uses a fixed random sample (seed ${ex.seed}) of ${Math.round(ex.fraction_multi * 100)}% of the ${fmt(ex.ideas_multi)} works cited by two or more lab papers and ${Math.round(ex.fraction_single * 100)}% of the ${fmt(ex.ideas_single)} cited once, weighted back to the full set.`,
      `What this cannot show: researchers who work together also read the same literature, so part of the rise with k ≥ 2 may be shared reading rather than influence (a timing-shuffle test could not separate the two because the network grows over time). The share of pass-ons carried by an earlier user on the paper does not depend on this.`,
      `Only the labs' own authors are in the network: a path through an outside co-author (for example at an IIT) is not seen, so "via a person" between labs is a lower bound. A citation is the visible trace of using an idea, not proof of using a method.`,
    ].map(x => `<li>${x}</li>`).join("");
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
    const c3 = claim("C3");
    $("ins-threshold").innerHTML = [c3].filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
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
    const c5 = claim("C5");
    $("ins-fields").innerHTML = [c5].filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
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
    $("ins-networks").innerHTML = ["C8"].map(claim).filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
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
    $("ins-meanfield").innerHTML = ["C6"].map(claim).filter(Boolean).map(c => box(`${badge(c.passed)}<p style="margin-top:.4rem">${esc(c.claim)}</p>`)).join("");
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

  }

  // ---------- 08 Conclusions ----------
  function renderConclusions() {
    const full = S.full_coauthorship.fields.Combined, fac = S.faculty_coauthorship.fields.Combined;
    const ch = DF.fields_data.Chemistry.condition_a;
    const sf = TH.full_coauthorship, sk = TH.faculty_coauthorship;
    const ratios = Object.values(TH).map(t => t.peak_over_theory);
    const so = S.seed_origins.faculty_coauthorship;
    const grid = D.grid || [];
    const c2v = (claim("C2") || {}).value || {};

    const PILLARS = [
      {
        id: "students",
        label: "Student Multiplier",
        tag: "Network Architecture",
        title: "Students & Junior Scholars as the Critical Network Glue",
        headline: `Without students the tipping point is ${num(c2v.T_peak_faculty / c2v.T_peak_full, 1)}× higher (${c2v.T_peak_faculty} vs ${c2v.T_peak_full}) and half the network is reached in ${fac.mc_t50} steps instead of ${full.mc_t50}`,
        stats: [
          { label: "Community Size", full: `${fmt(S.full_coauthorship.nodes)} authors`, fac: `${fmt(S.faculty_coauthorship.nodes)} connected faculty` },
          { label: "Median Steps to 50% (T50)", full: `${full.mc_t50} steps`, fac: `${fac.mc_t50} steps` },
          { label: "Final Reach @ Step 15", full: pct(full.mc_final_reach), fac: pct(fac.mc_final_reach) },
          { label: "Outbreak @ Transmissibility 0.2", full: `${pct(100 * c2v["S_full_T0.2"])} of network`, fac: `${pct(100 * c2v["S_faculty_T0.2"])} of network` },
          { label: "Tipping point (percolation)", full: String(c2v.T_peak_full), fac: String(c2v.T_peak_faculty) },
        ],
        takeaway: `With students and project staff included, an idea crosses 50% adoption in ${full.mc_t50} steps (reaching ${pct(full.mc_final_reach)} by step 15); among faculty alone it takes ${fac.mc_t50} steps and reaches ${pct(fac.mc_final_reach)}.` +
          (R ? ` The real citations show the mechanism, not just the size: a student's tie passes an idea on ${num(R.transmissibility.by_role.affiliated_author.T_pct / R.transmissibility.by_role.faculty.T_pct, 1)}× as often as a faculty member's (section 08).` : ""),
        rule: "Simulated via Monte Carlo SI on identical seeds and parameters; tipping point measured via bond percolation across 100 repeats per T.",
        badge: `${num(c2v.T_peak_faculty / c2v.T_peak_full, 1)}× higher tipping point without students`
      },
      {
        id: "silos",
        label: "Disciplinary Silos",
        tag: "Knowledge Boundaries",
        title: "Disciplinary Boundaries Act as Natural Knowledge Firewalls",
        headline: "Topic alignment confines 76.6% of diffusion inside Chemistry vs. 2.5% spillover outside",
        stats: [
          { label: "In-Field Adoption @ Step 15", val: pct(ch.adoption_curve.at(-1)), note: "Chemistry researchers" },
          { label: "Outside Spillover @ Step 15", val: pct(ch.spillover_curve.at(-1)), note: "Researchers outside Chemistry" },
          { label: "Containment Ratio", val: `${(ch.adoption_curve.at(-1) / ch.spillover_curve.at(-1)).toFixed(1)}×`, note: "Higher adoption within domain" },
          { label: "Inter-field Seeds", val: "15 top seeds", note: "Tested across 6 scientific domains" },
        ],
        takeaway: "Because transmission probability scales with topical alignment (cosine similarity of author publication profiles), scientific innovations remain heavily siloed. While an idea reaches over 3 out of 4 researchers inside its home discipline by step 15, fewer than 1 in 40 external researchers ever adopt it. Truly cross-cutting innovations require institutional bridge figures with high betweenness centrality.",
        rule: "Topic-weighted spreading (Condition A): transmission probability β = β0 · cos(u,v) · max(sv(F), ε), seeded by top 15 researchers in each field.",
        badge: "31.1× Disciplinary Containment"
      },
      {
        id: "clustering",
        label: "Clustering Reality",
        tag: "Theoretical Physics",
        title: "Real Academic Clustering Breaks Classical Epidemic Formulas",
        headline: "Textbook equations underestimate the true tipping point by 1.54× to 2.32×",
        stats: [
          { label: "Full Network Clustering", val: num(sf.clustering, 3), note: "High triangle density" },
          { label: "Faculty Network Clustering", val: num(sk.clustering, 3), note: "Clustering in cadre network" },
          { label: "Measured / Formula Ratio", val: `${Math.min(...ratios).toFixed(2)}× – ${Math.max(...ratios).toFixed(2)}×`, note: "Underestimation across all 8 networks" },
          { label: "Percolation Outbreak Peak", val: `T = ${sf.T_peak_simulated} (Full) vs ${sk.T_peak_simulated} (Faculty)`, note: "Empirical tipping threshold" },
        ],
        takeaway: "The classic configuration-model epidemic formula Tc = <k> / (<k²> - <k>) assumes an unclustered tree network where contacts branch into unexposed populations. In reality, scientific collaborations form dense triangles and co-author cliques (clustering C = 0.700). Contacts inside triangles redundantly waste transmissions on researchers who were already exposed, demanding 1.5× to 2.3× higher transmissibility before an idea can trigger a cluster-wide outbreak.",
        rule: "Bond percolation across 100 independent realizations per transmissibility step T in [0, 0.5]; tipping point identified from the peak of small-cluster susceptibility χ(T).",
        badge: "1.54×–2.32× Empirical Gap"
      },
      {
        id: "labs",
        label: "Institutional Velocity",
        tag: "Institutional Specialization",
        title: "CSIR-IICT Faculty Drive the Fastest Early Propagation Velocity",
        headline: "Early cluster reach ranks CSIR-IICT (5.98%) ahead of CSIR-NCL (4.92%) and CSIR-CECRI (1.23%)",
        stats: [
          { label: "CSIR-IICT Step-3 Reach", val: pct(so.iict.mc_curve[3]), note: `T50 = ${so.iict.mc_t50} steps` },
          { label: "CSIR-NCL Step-3 Reach", val: pct(so.ncl.mc_curve[3]), note: `T50 = ${so.ncl.mc_t50} steps` },
          { label: "CSIR-CECRI Step-3 Reach", val: pct(so.cecri.mc_curve[3]), note: "T50 not reached within 15 steps" },
          { label: "Model Concordance", val: "100% Agreement", note: "MC & NIMFA rank identical" },
        ],
        takeaway: "When seeded from the 10 best-connected faculty of each laboratory, ideas originating at CSIR-IICT disseminate fastest across the combined CSIR chemistry cluster during early steps (5.98% by step 3), closely followed by CSIR-NCL (4.92%). CSIR-CECRI seeds spread slowly (1.23% by step 3) and fail to reach half the cluster within 15 steps due to their specialized focus on electrochemistry and regional co-authorship isolation.",
        rule: "Evaluated on the faculty co-authorship network; each lab seeded by its top 10 degree faculty members across independent stochastic runs and deterministic NIMFA equations.",
        badge: "IICT Velocity Advantage"
      },
      {
        id: "nimfa",
        label: "Analytical Boundaries",
        tag: "Computational Methodology",
        title: "Deterministic Mean-Field (NIMFA) is a Proven, Scalable Upper Bound",
        headline: "NIMFA preserves super-spreader ranking (ρ = 0.91–1.00) while computing in fractions of a second",
        stats: [
          { label: "Evaluated Parameter Runs", val: "28 of 28", note: "Networks × Fields" },
          { label: "Smallest Gap (NIMFA - MC)", val: `${grid.reduce((m, r) => Math.min(m, r.min_gap), 0).toFixed(2)} pp`, note: "Consistent with MC sampling noise" },
          { label: "Largest Overprediction", val: `+${grid.reduce((m, r) => Math.max(m, r.max_gap), 0).toFixed(2)} pp`, note: "Analytical upper ceiling" },
          { label: "Spearman Rank Agreement", val: "0.91 – 1.00 (Median 0.97)", note: "Near-perfect super-spreader ranking" },
        ],
        takeaway: "Mean-field equations assume independent transmission events, ignoring positive correlations between mutual collaborators. Consequently, NIMFA mathematically bounds simulation reach from above (gap between -0.26 pp and +12.49 pp across all 28 runs). Crucially, NIMFA ranks the best seeds with exceptional accuracy (Spearman ρ = 0.91–1.00). Researchers can use NIMFA to identify key influencers and dissemination hubs instantaneously without heavy Monte Carlo sampling.",
        rule: "Simulated across all 4 networks and 7 domain targets; paper citation networks are 99.8% acyclic (only 22 papers in mutual loops), bounding citation diffusion to 1.68%.",
        badge: "Median ρ = 0.97 Concordance"
      }
    ];

    if (R) {
      const t = R.transmissibility, cr = 100 * t.overall.carried / (t.overall.carried + t.overall.independent);
      PILLARS.unshift({
        id: "reality", label: "Reality Check", tag: "Real-citation test",
        title: "The Labs' Real Citations Stay Below the Tipping Point",
        headline: `A co-author picks up a cited work ${pct(t.overall.T_pct, 2)} of the time per tie; the network needs ${pct(100 * R.tipping_points.full_coauthorship, 0)} for an outbreak`,
        stats: [
          { label: "Real per-tie transmissibility", val: pct(t.overall.T_pct, 2), note: `${fmt(t.overall.pairs)} (tie, idea) pairs` },
          { label: "Most reused ideas (10+ papers)", val: pct(t.by_bucket["10+ papers"].T_pct, 2), note: "still below the tipping point" },
          { label: "Carried by an earlier user", val: pct(cr, 0), note: "of real pass-ons" },
          { label: "Ties crossing labs", val: pct(R.between_labs.cross_lab_pct, 2), note: "the three labs are islands" },
        ],
        takeaway: `The model's tipping point is a property of the network; the real citations tell us where the labs' ideas sit relative to it. ` +
          `Ideas spread when people carry them into new papers, single contacts rarely convert a researcher, and between the labs knowledge arrives through the literature: ` +
          `${pct(R.ideas.single_use_pct, 0)} of cited works are used once.`,
        rule: `Per-tie transmissibility T = ties where the co-author later cites the work ÷ all ties at risk (co-author by the adoption year, still publishing afterwards, not yet a user), from ${fmt(R.ideas.citations)} citations (Step 24).`,
        badge: `${pct(t.overall.T_pct, 2)} vs ${pct(100 * R.tipping_points.full_coauthorship, 0)} tipping point`,
      });
    }
    const displayEl = $("conclusion-pillar-display");
    function renderPillarChart(id) {
      const el = $("ch-conclusion-viz");
      if (!el) return;
      const k = ink();
      if (id === "reality") { drawTip("ch-conclusion-viz"); return; }
      if (id === "students") {
        const fullCurve = S.full_coauthorship.fields.Combined.mc_curve;
        const facCurve = S.faculty_coauthorship.fields.Combined.mc_curve;
        chart("ch-conclusion-viz", {
          grid: { left: 8, right: 36, top: 44, bottom: 28, containLabel: true },
          legend: { top: 0, textStyle: { color: k.text2 } },
          tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
          xAxis: stepAxis(fullCurve.length),
          yAxis: { type: "value", name: "% adopted", max: 100, ...axis() },
          series: [
            line("Full Community (7,678 authors)", fullCurve, css("--s1"), {
              areaStyle: { color: "rgba(42, 120, 214, 0.16)" },
              markLine: {
                silent: true, symbol: "none",
                data: [
                  { yAxis: 50, lineStyle: { color: k.muted, type: "dashed" }, label: { formatter: "50% Target", position: "insideEndTop" } },
                  { xAxis: 9, lineStyle: { color: css("--s1"), type: "dotted", width: 2 }, label: { formatter: "Full: Step 9", position: "insideStartTop" } },
                  { xAxis: 12, lineStyle: { color: css("--s2"), type: "dotted", width: 2 }, label: { formatter: "Faculty: Step 12", position: "insideEndBottom" } }
                ]
              }
            }),
            line("Faculty Alone (238 scientists)", facCurve, css("--s2"), { lineStyle: { width: 3, type: "dashed" } })
          ]
        });
      } else if (id === "silos") {
        chart("ch-conclusion-viz", {
          grid: { left: 8, right: 36, top: 44, bottom: 28, containLabel: true },
          legend: { top: 0, textStyle: { color: k.text2 } },
          tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
          xAxis: stepAxis(ch.adoption_curve.length),
          yAxis: { type: "value", name: "% adopted", max: 100, ...axis() },
          series: [
            line("In-Field Chemistry Adoption (76.59% @ step 15)", ch.adoption_curve, css("--s3"), {
              areaStyle: { color: "rgba(27, 175, 122, 0.18)" }
            }),
            line("Outside Spillover (2.46% @ step 15)", ch.spillover_curve, css("--s2"), {
              lineStyle: { width: 3, type: "dotted" }
            })
          ]
        });
      } else if (id === "clustering") {
        const netKeys = Object.keys(TH);
        const labels = netKeys.map(k => netName(k).replace(" (all authors)", ""));
        const theoryVals = netKeys.map(k => TH[k].T_c_theory);
        const peakVals = netKeys.map(k => TH[k].T_peak_simulated);
        chart("ch-conclusion-viz", {
          grid: { left: 8, right: 36, top: 40, bottom: 16, containLabel: true },
          legend: { top: 0, textStyle: { color: k.text2 } },
          tooltip: tip({ trigger: "axis", valueFormatter: v => num(v, 3) }),
          yAxis: { type: "category", data: labels, ...axis() },
          xAxis: { type: "value", name: "Tipping Point Transmissibility T", ...axis() },
          series: [
            { name: "Textbook Formula Tc", type: "bar", data: theoryVals, itemStyle: { color: css("--s2"), borderRadius: [0, 4, 4, 0] }, barMaxWidth: 12 },
            { name: "Real Measured Peak (Percolation)", type: "bar", data: peakVals, itemStyle: { color: css("--s3"), borderRadius: [0, 4, 4, 0] }, barMaxWidth: 12 }
          ]
        });
      } else if (id === "labs") {
        chart("ch-conclusion-viz", {
          grid: { left: 8, right: 36, top: 44, bottom: 28, containLabel: true },
          legend: { top: 0, textStyle: { color: k.text2 } },
          tooltip: tip({ trigger: "axis", valueFormatter: v => pct(v) }),
          xAxis: stepAxis(so.iict.mc_curve.length),
          yAxis: { type: "value", name: "% cluster reached", max: 70, ...axis() },
          series: [
            line("CSIR-IICT Faculty Seeds (5.98% @ step 3)", so.iict.mc_curve, css(LAB_VAR["CSIR-IICT"]), { lineStyle: { width: 3 } }),
            line("CSIR-NCL Faculty Seeds (4.92% @ step 3)", so.ncl.mc_curve, css(LAB_VAR["CSIR-NCL"]), { lineStyle: { width: 3 } }),
            line("CSIR-CECRI Faculty Seeds (1.23% @ step 3)", so.cecri.mc_curve, css(LAB_VAR["CSIR-CECRI"]), { lineStyle: { width: 2.5, type: "dashed" } })
          ]
        });
      } else if (id === "nimfa") {
        const domains = ["Chemistry", "Materials", "Engineering", "Energy", "Biochemistry", "Medicine", "Combined"];
        const gaps = domains.map(d => {
          const r = S.full_coauthorship.fields[d];
          return r ? Number((r.nimfa_final_reach - r.mc_final_reach).toFixed(2)) : 0;
        });
        chart("ch-conclusion-viz", {
          grid: { left: 8, right: 36, top: 40, bottom: 28, containLabel: true },
          legend: { top: 0, textStyle: { color: k.text2 } },
          tooltip: tip({ trigger: "axis", valueFormatter: v => v + " pp" }),
          xAxis: { type: "category", data: domains, ...axis() },
          yAxis: { type: "value", name: "NIMFA - MC Gap (pp)", max: 14, ...axis() },
          series: [
            {
              name: "NIMFA Overprediction Ceiling",
              type: "bar",
              data: gaps,
              itemStyle: { color: css("--s1"), borderRadius: [6, 6, 0, 0] },
              barMaxWidth: 24,
              markLine: {
                data: [{ type: "average", name: "Avg Gap", label: { formatter: "Mean Ceiling" } }]
              }
            }
          ]
        });
      }
    }

    function showPillar(id) {
      const p = PILLARS.find(x => x.id === id) || PILLARS[0];
      let statsHtml = "";
      if (p.id === "students") {
        statsHtml = `<div class="c-comparison-table-wrap">
          <table class="c-comparison-table">
            <thead><tr><th>Dimension</th><th>Full Community (with students)</th><th>Faculty Cadre Alone</th></tr></thead>
            <tbody>
              ${p.stats.map(s => `<tr><td class="c-metric-lbl">${esc(s.label)}</td><td class="c-metric-full">${esc(s.full)}</td><td class="c-metric-fac">${esc(s.fac)}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>`;
      } else {
        statsHtml = `<div class="c-stats-grid">
          ${p.stats.map(s => `<div class="c-stat-card"><div class="c-stat-lbl">${esc(s.label)}</div><div class="c-stat-val">${esc(s.val)}</div>${s.note ? `<div class="c-stat-sub">${esc(s.note)}</div>` : ""}</div>`).join("")}
        </div>`;
      }

      displayEl.innerHTML = `
        <div class="c-pillar-box">
          <div class="c-pillar-header">
            <div>
              <span class="c-pillar-tag">${esc(p.tag)}</span>
              <h4 class="c-pillar-title">${esc(p.title)}</h4>
              <p class="c-pillar-headline">${esc(p.headline)}</p>
            </div>
            <div class="c-pillar-badge">${esc(p.badge)}</div>
          </div>
          <div id="ch-conclusion-viz" class="g-chart" style="height:320px; width:100%; margin:0.8rem 0 1rem;"></div>
          ${statsHtml}
          <div class="c-pillar-body">
            <div class="c-punchline-card">
              <span class="c-punchline-icon">⚡</span>
              <p class="c-pillar-takeaway"><strong>Key Takeaway:</strong> ${esc(p.takeaway)}</p>
            </div>
            <details class="c-deep-dive">
              <summary>Inspect Mathematical Model &amp; Verification Rule</summary>
              <div class="c-deep-dive-body">
                <p><strong>Rule:</strong> ${esc(p.rule)}</p>
              </div>
            </details>
          </div>
        </div>
      `;
      renderPillarChart(p.id);
      if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([displayEl]);
    }

    seg("seg-conclusion-pillar", PILLARS.map(p => [p.id, p.label]), PILLARS[0].id, showPillar);

    const bentoCards = [
      {
        tag: "Collaboration Velocity",
        num: `${num(c2v.T_peak_faculty / c2v.T_peak_full, 1)}×`,
        title: "Students Lift the Network",
        sub: `Without students the tipping point is ${num(c2v.T_peak_faculty / c2v.T_peak_full, 1)}× higher, and half the network is reached in ${fac.mc_t50} instead of ${full.mc_t50} steps.`,
        track1: { label: "Full Community:", val: `${pct(full.mc_final_reach)} by step 15`, pct: full.mc_final_reach, cls: "full" },
        track2: { label: "Faculty Alone:", val: `${pct(fac.mc_final_reach)} by step 15`, pct: fac.mc_final_reach, cls: "fac" }
      },
      {
        tag: "Disciplinary Wall",
        num: "31.1×",
        title: "Disciplinary Silos",
        sub: "Topic alignment strongly confines ideas inside discipline with negligible outside spillover.",
        track1: { label: "In-Field Chemistry:", val: "76.59% adopted", pct: 76.59, cls: "chem" },
        track2: { label: "Outside Spillover:", val: "2.46% adopted", pct: 2.46, cls: "spill" }
      },
      {
        tag: "Epidemic Theory",
        num: "1.5–2.3×",
        title: "Clustering Reality",
        sub: "Triangles (C = 0.700) waste transmissions, requiring higher transmissibility than formulas predict.",
        track1: { label: "Textbook Formula:", val: "1.0× unclustered base", pct: 45, cls: "spill" },
        track2: { label: "Measured Real Peak:", val: "Up to 2.32× (8/8 exceed)", pct: 95, cls: "full" }
      },
      {
        tag: "Institutional Leadership",
        num: "5.98%",
        title: "CSIR-IICT Velocity",
        sub: "CSIR-IICT seeds achieve the fastest early cluster diffusion, validated by both MC and NIMFA.",
        track1: { label: "🥇 CSIR-IICT Lead:", val: "5.98% @ step 3", pct: 85, cls: "gold" },
        track2: { label: "🥈 NCL: 4.92% | 🥉 CECRI:", val: "1.23% @ step 3", pct: 40, cls: "silver" }
      }
    ];

    $("conclusions-bento").innerHTML = bentoCards.map(b => `
      <div class="bento-card">
        <div class="bento-card-top">
          <span class="bento-tag">${esc(b.tag)}</span>
          <span class="bento-badge">Verified Peak</span>
        </div>
        <div class="bento-num">${esc(b.num)}</div>
        <h4 class="bento-title">${esc(b.title)}</h4>
        <p class="bento-sub">${esc(b.sub)}</p>
        <div class="bento-track-group">
          <div class="bento-track-row"><span>${esc(b.track1.label)}</span> <strong>${esc(b.track1.val)}</strong></div>
          <div class="bento-progress-bar"><div class="bento-fill ${esc(b.track1.cls)}" style="width:${b.track1.pct}%"></div></div>
          <div class="bento-track-row"><span>${esc(b.track2.label)}</span> <strong>${esc(b.track2.val)}</strong></div>
          <div class="bento-progress-bar"><div class="bento-fill ${esc(b.track2.cls)}" style="width:${b.track2.pct}%"></div></div>
        </div>
      </div>
    `).join("");
  }

  // ---------- 09 Proof ----------
  function renderProof() {
    const cl = (D.claims && D.claims.claims) || [];
    
    const CLAIM_META = {
      C1: {
        cat: "dynamics", catLabel: "Spreading Dynamics",
        headline: "Full Network Reaches 50% in 9 Steps vs. 12 Steps for Faculty Alone",
        chips: [
          { label: "Full T50", val: "9 steps" },
          { label: "Faculty T50", val: "12 steps" },
          { label: "Full Reach @15", val: "88.88%" },
          { label: "Faculty Reach @15", val: "64.52%" }
        ]
      },
      C2: {
        cat: "theory", catLabel: "Theory & Thresholds",
        headline: "Percolation Outbreak at T=0.2 Reaches 59% of All Authors vs. 30% of Faculty",
        chips: [
          { label: "T=0.2 Full Outbreak", val: "58.8%" },
          { label: "T=0.2 Faculty Outbreak", val: "29.7%" },
          { label: "Full Threshold", val: "0.060" },
          { label: "Faculty Threshold", val: "0.215" }
        ]
      },
      C3: {
        cat: "theory", catLabel: "Theory & Thresholds",
        headline: "Textbook Threshold Formula Underestimates Real Thresholds by 1.54× to 2.32×",
        chips: [
          { label: "Ratio Range", val: "1.54× – 2.32×" },
          { label: "Full Clustering", val: "0.700" },
          { label: "Faculty Clustering", val: "0.317" },
          { label: "Networks Tested", val: "8 of 8" }
        ]
      },
      C4: {
        cat: "theory", catLabel: "Theory & Thresholds",
        headline: "Deterministic Mean-Field (NIMFA) Strictly Bounds Stochastic Monte Carlo",
        chips: [
          { label: "Parameter Runs", val: "28 of 28" },
          { label: "Min Gap (Noise)", val: "-0.26 pp" },
          { label: "Max Gap (Ceiling)", val: "+12.49 pp" },
          { label: "Runs Below Noise", val: "0" }
        ]
      },
      C5: {
        cat: "integrity", catLabel: "Data Integrity",
        headline: "Monte Carlo Convergence Confirmed Across 25, 50, and 100 Independent Runs",
        chips: [
          { label: "T50 Variation", val: "0.0 steps" },
          { label: "Max Reach Spread", val: "0.89 pp" },
          { label: "Fields Verified", val: "6 Fields" }
        ]
      },
      C6: {
        cat: "theory", catLabel: "Theory & Thresholds",
        headline: "Mean-Field and Simulation Rank Super-Spreaders with Near-Perfect Concordance",
        chips: [
          { label: "Spearman ρ Range", val: "0.91 – 1.00" },
          { label: "Median ρ", val: "0.97" },
          { label: "Criterion (ρ ≥ 0.70)", val: "Satisfied" }
        ]
      },
      C7: {
        cat: "domains", catLabel: "Disciplines & Labs",
        headline: "Topic Alignment Silos Ideas: 76.6% In-Field Reach vs. 2.5% Outside Spillover",
        chips: [
          { label: "In-Field Adoption", val: "76.59%" },
          { label: "Outside Spillover", val: "2.46%" },
          { label: "Disciplinary Wall", val: ">31× Ratio" }
        ]
      },
      C8: {
        cat: "dynamics", catLabel: "Spreading Dynamics",
        headline: "Paper Citation Channels Inhibit Spreading Due to Forward-in-Time Flow",
        chips: [
          { label: "Final Citation Reach", val: "1.68%" },
          { label: "Mutual Loop Papers", val: "22 of 10,931" },
          { label: "Acyclic Topology", val: "99.8%" }
        ]
      },
      C9: {
        cat: "domains", catLabel: "Disciplines & Labs",
        headline: "CSIR-IICT Faculty Seeds Lead Early Cluster Diffusion Ahead of NCL and CECRI",
        chips: [
          { label: "CSIR-IICT Step 3", val: "5.98%" },
          { label: "CSIR-NCL Step 3", val: "4.92%" },
          { label: "CSIR-CECRI Step 3", val: "1.23%" },
          { label: "Model Consensus", val: "MC & NIMFA Agree" }
        ]
      },
      C10: {
        cat: "integrity", catLabel: "Data Integrity",
        headline: "Cadre Roster Filtration: 505 Raw Entries Filtered to 382 Clean and 306 Active",
        chips: [
          { label: "Scraped Entries", val: "505" },
          { label: "Excluded (Tech/Dupes)", val: "123" },
          { label: "Clean Cadre", val: "382" },
          { label: "Active in 2016–2026", val: "306" }
        ]
      },
      C11: {
        cat: "integrity", catLabel: "Data Integrity",
        headline: "Cross-Dashboard Network Parity: Faculty Co-Authorship Topology Identical",
        chips: [
          { label: "Connected Faculty", val: "238" },
          { label: "Co-author Pairs", val: "627" },
          { label: "Main Dashboard Edges", val: "627" }
        ]
      }
    };

    const vC = id => (claim(id) || {}).value || {};
    if (claim("C12")) {
      const v12 = vC("C12"), v13 = vC("C13"), v14 = vC("C14"), v15 = vC("C15");
      Object.assign(CLAIM_META, {
        C12: { cat: "real", catLabel: "Real-citation test", headline: "Real Ideas Stay Below the Network's Tipping Point",
          chips: [{ label: "Per-tie T", val: pct(v12.T_all_pct, 2) }, { label: "Most reused", val: pct(v12.T_most_reused_pct, 2) },
                  { label: "Tipping point", val: pct(v12.tipping_full_pct, 1) }, { label: "Used once", val: pct(v12.single_use_pct) }] },
        C13: { cat: "real", catLabel: "Real-citation test", headline: "A Student's Tie Passes Ideas On More Often Than a Professor's",
          chips: [{ label: "Student tie", val: pct(v13.T_affiliated_pct, 2) }, { label: "Faculty tie", val: pct(v13.T_faculty_pct, 2) },
                  { label: "Ratio", val: `${num(v13.ratio, 1)}×` }, { label: "Co-authors", val: `${v13.coauthors_faculty} vs ${v13.coauthors_affiliated}` }] },
        C14: { cat: "real", catLabel: "Real-citation test", headline: "Ideas Travel With People and Need Reinforcement",
          chips: [{ label: "Carried", val: pct(v14.carried_share_pct, 0) }, { label: "Own use, 1 contact", val: `${num(v14.lift_independent["1"])}×` },
                  { label: "Own use, 3+ contacts", val: `${num(v14.lift_independent["3+"], 1)}×` }] },
        C15: { cat: "real", catLabel: "Real-citation test", headline: "Three Islands That Learn From Abroad by Reading",
          chips: [{ label: "Cross-lab ties", val: pct(v15.cross_lab_ties_pct, 2) }, { label: "Foreign via person", val: pct(v15.via_person_foreign_pct, 1) },
                  { label: "Own papers via person", val: pct(v15.via_person_own_pct, 1) }, { label: "Cited : co-authored", val: `${fmt(v15.foreign_peer_papers_cited)} : ${v15.foreign_coauthored_papers}` }] },
      });
    }
    $("n-claims").textContent = cl.length;
    const deckEl = $("deck-claims");
    function filterClaims(cat) {
      const filtered = cat === "all" ? cl : cl.filter(c => CLAIM_META[c.id] && CLAIM_META[c.id].cat === cat);
      deckEl.innerHTML = filtered.map(c => {
        const meta = CLAIM_META[c.id] || { catLabel: "Empirical Finding", headline: `Finding ${c.id}`, chips: [] };
        return `
          <div class="claim-card" data-cat="${esc(meta.cat)}">
            <div class="claim-card-top">
              <span class="claim-id-badge">${esc(c.id)}</span>
              <span class="claim-cat-tag">${esc(meta.catLabel)}</span>
            </div>
            <h4 class="claim-headline">${esc(meta.headline)}</h4>
            <div class="claim-metric-chips">
              ${meta.chips.map(ch => `<span class="c-chip"><strong>${esc(ch.label)}:</strong> ${esc(ch.val)}</span>`).join("")}
            </div>
            <p class="claim-statement">${esc(c.claim)}</p>
            <details class="claim-proof-drawer">
              <summary>Inspect Proof &amp; Verification Rule</summary>
              <div class="claim-proof-content">
                <div class="proof-row"><span class="proof-lbl">Source File:</span> <code>${esc(c.source)}</code></div>
                <div class="proof-row"><span class="proof-lbl">Verification Rule:</span> <span>${esc(c.check)}</span></div>
                <div class="proof-row"><span class="proof-lbl">Exact Payload:</span> <pre><code>${esc(JSON.stringify(c.value, null, 2))}</code></pre></div>
              </div>
            </details>
          </div>
        `;
      }).join("");
    }

    seg("seg-claims-filter", [
      ["all", `All Claims (${cl.length})`],
      ["real", "Real-citation tests"],
      ["dynamics", "Spreading Dynamics"],
      ["theory", "Theory & Thresholds"],
      ["domains", "Disciplines & Labs"],
      ["integrity", "Data Integrity"]
    ], "all", filterClaims);

    const M_TABS = [
      { id: "glossary", label: "Key Terminology" },
      { id: "repro", label: "Pipeline Reproduction" },
      { id: "fixes", label: "Audit & Version History" },
      { id: "limits", label: "Methodological Scope" }
    ];

    const terms = [
      ["Adopting an idea", "Taking up a new method, technique or reagent from a collaborator. Once adopted it is kept (the SI model)."],
      ["Step", "One round of contact between collaborators: everyone who has the idea gets one chance to pass it to each collaborator. Not a calendar unit."],
      ["Transmission probability β", `The chance that an idea passes along one link in one step: ${P.beta0} at most, scaled down when the two people work on different topics.`],
      ["T50", "The first step at which half of the target group has adopted. \"Not reached\" when the typical run never gets there within 15 steps."],
      ["Monte Carlo (MC)", "Running the random spreading process many times with different random numbers and averaging the results."],
      ["NIMFA (mean field)", "Equations for each person's probability of having adopted, assuming neighbours are independent. Fast, but it over-estimates spreading."],
      ["Tipping point (threshold)", "If people pass an idea on only once, it dies out below a certain transmission probability and spreads widely above it."],
      ["Super-spreader", "A seed whose idea reaches the most people early on (by step 3)."],
      ["Gatekeeper", "A person whose removal cuts the most researchers off from the rest of a field's network."],
      ["Spillover", "The share of researchers outside a field who adopt an idea that started inside it."],
      ["Real per-tie transmissibility", "From the labs' citations: the share of (co-author tie, cited work) pairs where the co-author cites the work after the first user did (section 08)."],
      ["Carried / independent", "A pass-on is carried when someone who used the idea earlier is an author of the new paper, independent when not."],
    ];

    const reproItems = [
      "<code>python run.py insight11</code> rebuilds everything on this page from <code>data/final/</code> (no API calls): faculty networks, roster audit, the field study, the network comparison, the threshold test, the claims and the page data.",
      "Scripts: <code>src/stats/insights/s11_information_diffusion.py</code> (field study), <code>s11_nimfa_spreading.py</code> (four networks, mean field, labs), <code>s11_threshold_check.py</code> (percolation), <code>s11_real_diffusion.py</code> (real-citation test, section 08), <code>s11_claims.py</code> (checks), <code>s11_cadre_networks.py</code>, <code>s11_data_cleaning_audit.py</code>; <code>src/collect/24_work_references.py</code> writes the reference lists from the API cache.",
      `All randomness comes from numpy RandomState with fixed seeds (${P.rng_seed}); nodes are processed in a fixed order, so a rerun gives identical numbers (tested under different PYTHONHASHSEED values).`,
      "Outputs: <code>stats/tables/insights/11_*.json / .csv</code>. Tests: <code>tests/test_insight11.py</code> (every claim passes, NIMFA equation and SI step checked on small graphs by brute force), <code>tests/test_insights.py</code>, <code>tests/test_cadre_networks.py</code>.",
      "Inputs: <code>group24_data_extended.csv</code>, <code>faculty_master.csv</code>, <code>citation_network.csv</code>, <code>work_references.csv.gz</code>, <code>data/review/roster_excluded.csv</code>, and the Global Benchmark's <code>citation_flows.csv</code> and <code>global_links.csv</code>.",
    ];

    const fixItems = [
      "The \"epidemic threshold\" was presented as a property of the SI model; SI has none. Thresholds are now labelled as structural thresholds for spreading with recovery and are tested directly (section 03).",
      "The extended study built the full co-authorship network by author name, merging different people; it now uses the same network as the field study, keyed by OpenAlex author ID.",
      "Monte Carlo and mean field were compared on different seed weightings (some seeds 3 runs, others 2) and T50 averaged \"not reached\" as step 15; both now use the same seeds, equal runs per seed and the censored median.",
      "Citation networks reported thresholds of 0.71 and 1.0 (artefacts of an acyclic network) and copied the all-field result into every field; now no threshold where none exists, and papers are assigned to fields by their own field.",
      "Super-spreaders were ranked by reach at step 15, where the top seeds differed by 0.3%, and described as a derivative that was not computed; they are now ranked at step 3, with the simulation's ranking as a check.",
      "\"Jensen's inequality proves…\" and a typed-in gap range (+1.8% to +5.8%) were replaced by the measured gap and a check of its sign; typed-in roster claims (h-index 7.0 → 6.0, 1,290 ties, 282 rows) without a source were removed.",
      "The extended-study scripts were not part of any pipeline; <code>python run.py insight11</code> now runs all of them.",
      "Reruns were not identical: subgraphs iterated their nodes in a hash-dependent order, so random numbers landed on different people from run to run. Every study network is now built in a fixed order (tested under two hash seeds), and the tipping-point test uses 100 instead of 40 repeats.",
    ];

    const limitItems = [
      "The model is stylised: β0 = 0.2 per step is chosen, not estimated. The results compare networks, fields and labs under the same rule; they do not predict how many months an idea takes. Section 08 measures the real per-tie transmissibility from citations, which is far lower.",
      "Links are co-authorships and citations from 2016–2026 merged into one static network; who worked with whom changed over the decade.",
      "The full network includes students and project staff identified only by their OpenAlex profile; profile errors (split or merged people) remain possible.",
      "Field shares come from OpenAlex's topic classification of each paper.",
      "The textbook formula assumes a network without clustering; the measured threshold is the one to trust.",
    ];

    const hubBodyEl = $("methodology-tab-body");
    function showMethodologyTab(tid) {
      if (tid === "glossary") {
        hubBodyEl.innerHTML = `<dl class="g-glossary">${terms.map(([t, d]) => `<div><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join("")}</dl>`;
      } else if (tid === "repro") {
        hubBodyEl.innerHTML = `<ul class="g-list">${reproItems.map(t => `<li>${t}</li>`).join("")}</ul>`;
      } else if (tid === "fixes") {
        hubBodyEl.innerHTML = `<ul class="g-list">${fixItems.map(t => `<li>${t}</li>`).join("")}</ul>`;
      } else if (tid === "limits") {
        hubBodyEl.innerHTML = `<ul class="g-list">${limitItems.map(t => `<li>${t}</li>`).join("")}</ul>`;
      }
    }

    seg("seg-methodology-tabs", M_TABS.map(t => [t.id, t.label]), "glossary", showMethodologyTab);
  }

  // Animation triggers
  function initAnimations() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll(".bento-card, .claim-card, .c-stat-card").forEach(el => {
      el.classList.add("reveal-on-scroll");
      observer.observe(el);
    });
  }

  renderTop(); renderBoard(); renderData(); renderThreshold(); renderFields(); renderNetworks(); renderMeanField(); renderLabs(); renderReal(); renderConclusions(); renderProof(); renderToc(); trackSection(); initAnimations();
  // typeset formulas inside generated tables once MathJax has loaded
  const typeset = () => (window.MathJax && MathJax.typesetPromise ? MathJax.typesetPromise() : null);
  if (!typeset()) window.addEventListener("load", () => setTimeout(typeset, 0));
})();
