/**
 * Scientist profiles: hover card + full profile panel.
 * Layout adapted from https://jfmendes-sciart.github.io/research.html
 * (stat tiles, lollipop timeline, interest tags, collaborator strip, ego network).
 *
 * Data: window.G24_PROFILES (dashboard/data/g24_profiles.js, built by
 * src/dashboard/build_profiles.py). Any element with data-fid="<faculty_id>" gets the
 * hover card and opens the profile on click. Deep link: #profile=<faculty_id>.
 */
(function () {
  const PROFILES = window.G24_PROFILES || {};
  const LAB_COLORS = { iict: "#2b5c8f", ncl: "#2e7d32", cecri: "#d95f02", all: "#4a148c" };
  const LAB_COLOR_BY_NAME = { "CSIR-IICT": LAB_COLORS.iict, "CSIR-NCL": LAB_COLORS.ncl, "CSIR-CECRI": LAB_COLORS.cecri };
  const PARTIAL_YEAR = 2026;

  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = n => Number(n || 0).toLocaleString();
  const titleCase = s => (s && s === s.toUpperCase() ? s.toLowerCase().replace(/\b\w/g, c => c.toUpperCase()) : s || "");

  function initials(name) {
    const parts = String(name || "").replace(/\b(Dr|Prof|Mr|Mrs|Ms|Smt|Sri|Shri)\.?\s+/gi, "").split(/[\s.]+/).filter(Boolean);
    if (!parts.length) return "?";
    return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
  }

  function avatar(p, large) {
    const color = LAB_COLORS[p.lab_key] || LAB_COLOR_BY_NAME[p.lab] || LAB_COLORS.all;
    return `<span class="prof-avatar${large ? " lg" : ""}" style="background:${color}" aria-hidden="true">${esc(initials(p.name))}</span>`;
  }

  // Name -> faculty_id, only for names that identify a single roster scientist
  const byName = {};
  const nameCount = {};
  const byOpenAlex = {};
  Object.values(PROFILES).forEach(p => {
    nameCount[p.name] = (nameCount[p.name] || 0) + 1;
    if (p.openalex) byOpenAlex[p.openalex] = p.id;
  });
  Object.values(PROFILES).forEach(p => { if (nameCount[p.name] === 1) byName[p.name] = p.id; });

  /* ---------------- Hover card ---------------- */
  let hoverEl = null;
  function hoverCard() {
    if (!hoverEl) {
      hoverEl = document.createElement("div");
      hoverEl.className = "prof-hover";
      hoverEl.setAttribute("role", "tooltip");
      document.body.appendChild(hoverEl);
    }
    return hoverEl;
  }

  function showHover(fid, x, y) {
    const p = PROFILES[fid];
    if (!p) return;
    const el = hoverCard();
    const topic = p.interests && p.interests[0] ? p.interests[0].name : "";
    el.innerHTML = `
      <div class="prof-hover-top">${avatar(p)}
        <div><div class="prof-hover-name">${esc(p.name)}</div>
        <div class="prof-hover-sub">${esc(p.designation)}</div>
        <div class="prof-hover-sub">${esc(p.lab)} · ${esc(titleCase(p.division))}</div></div>
      </div>
      <div class="prof-hover-stats">
        <div><b>${fmt(p.papers)}</b><span>Papers</span></div>
        <div><b>${fmt(p.citations)}</b><span>Citations</span></div>
        <div><b>${p.h_index}</b><span>h-index</span></div>
        <div><b>${p.papers ? p.q1_share_pct + "%" : "–"}</b><span>Q1</span></div>
      </div>
      <div class="prof-hover-foot">${topic ? `Main area: ${esc(topic)} · ` : ""}<em>Click for full profile</em></div>`;
    positionHover(x, y);
    el.classList.add("show");
  }

  function positionHover(x, y) {
    const el = hoverCard();
    const w = el.offsetWidth || 300, h = el.offsetHeight || 160, pad = 14;
    let left = x + pad, top = y + pad;
    if (left + w > window.innerWidth - 8) left = x - w - pad;
    if (top + h > window.innerHeight - 8) top = y - h - pad;
    el.style.left = `${Math.max(8, left)}px`;
    el.style.top = `${Math.max(8, top)}px`;
  }

  function hideHover() { if (hoverEl) hoverEl.classList.remove("show"); }

  // Delegated hover/click for any [data-fid] element
  let hoverFid = null;
  document.addEventListener("mouseover", e => {
    const t = e.target.closest && e.target.closest("[data-fid]");
    if (!t || t.closest(".prof-overlay .prof-net")) return;
    const fid = t.getAttribute("data-fid");
    if (fid !== hoverFid) { hoverFid = fid; showHover(fid, e.clientX, e.clientY); }
  });
  document.addEventListener("mousemove", e => { if (hoverFid) positionHover(e.clientX, e.clientY); });
  document.addEventListener("mouseout", e => {
    const t = e.target.closest && e.target.closest("[data-fid]");
    if (t && !(e.relatedTarget && t.contains(e.relatedTarget))) { hoverFid = null; hideHover(); }
  });
  document.addEventListener("click", e => {
    const t = e.target.closest && e.target.closest("[data-fid]");
    if (t && !e.target.closest("a")) { e.preventDefault(); open(t.getAttribute("data-fid")); }
  });
  document.addEventListener("keydown", e => {
    const t = e.target.closest && e.target.closest("[data-fid]");
    if (t && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); open(t.getAttribute("data-fid")); }
    if (e.key === "Escape") close();
  });

  /* ---------------- Cards (featured strip, collaborators) ---------------- */
  function scientistCard(p) {
    return `<div class="prof-card" data-fid="${esc(p.id)}" tabindex="0" role="button" aria-label="Open profile of ${esc(p.name)}">
      <div class="prof-card-top">${avatar(p)}
        <div style="overflow:hidden"><div class="prof-card-name">${esc(p.name)}</div>
        <div class="prof-card-role">${esc(titleCase(p.division))} · ${esc(p.lab.replace("CSIR-", ""))}</div></div>
      </div>
      <div class="prof-card-bottom"><span class="prof-chip">${fmt(p.citations)} citations</span>
        <span class="prof-card-status">h-index ${p.h_index}</span></div>
    </div>`;
  }

  function collaboratorCard(c) {
    const p = c.faculty_id && PROFILES[c.faculty_id];
    const pseudo = { name: c.name, lab: c.lab, lab_key: "" };
    const attrs = p ? `data-fid="${esc(c.faculty_id)}" tabindex="0" role="button"` : "";
    return `<div class="prof-card" ${attrs}>
      <div class="prof-card-top">${avatar(p || pseudo)}
        <div style="overflow:hidden"><div class="prof-card-name">${esc(c.name)}</div>
        <div class="prof-card-role">${esc(p ? titleCase(p.division) : "Co-author")} · ${esc(c.lab.replace("CSIR-", ""))}</div></div>
      </div>
      <div class="prof-card-bottom"><span class="prof-chip">${c.joint_papers} joint paper${c.joint_papers === 1 ? "" : "s"}</span>
        <span class="prof-card-status">${p ? "CSIR faculty" : "Lab co-author"}</span></div>
    </div>`;
  }

  function marquee(cardsHtml, n) {
    // Duplicate the cards so the -50% scroll loops seamlessly
    const dur = Math.max(20, n * 4);
    return `<div class="prof-marquee"><div class="prof-track" style="--dur:${dur}s">${cardsHtml}${cardsHtml.replace(/data-fid=/g, "aria-hidden=\"true\" data-fid=").replace(/tabindex="0"/g, 'tabindex="-1"')}</div></div>`;
  }

  /** Render the featured-scientists strip for a lab key ("all" | "iict" | "ncl" | "cecri"). */
  function renderFeatured(containerId, labKey, n = 16) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const list = Object.values(PROFILES)
      .filter(p => p.papers > 0 && (labKey === "all" || labKey === "compare" || p.lab_key === labKey))
      .sort((a, b) => b.citations - a.citations || a.name.localeCompare(b.name))
      .slice(0, n);
    el.innerHTML = list.length ? marquee(list.map(scientistCard).join(""), list.length) : `<div class="prof-empty">No scientists for this selection.</div>`;
  }

  /* ---------------- Profile panel ---------------- */
  let overlay = null, netChart = null, current = null, lastFocus = null;

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement("div");
    overlay.className = "prof-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.addEventListener("click", e => { if (e.target === overlay) close(); });
    document.body.appendChild(overlay);
    return overlay;
  }

  function lollipop(byYear) {
    const max = Math.max(1, ...byYear.map(y => y.papers));
    const peak = byYear.filter(y => y.year < PARTIAL_YEAR).reduce((a, b) => (b.papers > a.papers ? b : a), byYear[0]);
    return `<div class="lolli">${byYear.map(y => {
      const h = Math.round((y.papers / max) * 100);
      const partial = y.year === PARTIAL_YEAR;
      const isPeak = y.year === peak.year && y.papers > 0;
      const tip = `${y.papers} paper${y.papers === 1 ? "" : "s"} in ${y.year}${partial ? " (partial year)" : ""} · ${fmt(y.citations)} citations to these papers`;
      return `<div class="lolli-col" title="${esc(tip)}">
        ${isPeak ? `<span class="lolli-peak">▴ peak</span>` : ""}
        <div class="lolli-dot${isPeak ? " peak" : ""}${partial ? " partial" : ""}"></div>
        <div class="lolli-stem" style="height:${h}%"></div>
        <span class="lolli-year">'${String(y.year).slice(2)}${partial ? "*" : ""}</span>
        <span class="lolli-count">${y.papers}</span>
      </div>`;
    }).join("")}</div>`;
  }

  function render(p) {
    const hasPapers = p.papers > 0;
    const links = [
      p.openalex ? `<a href="${esc(p.openalex)}" target="_blank" rel="noopener">OpenAlex profile ↗</a>` : "",
      p.rank_in_lab ? `<span class="prof-badge">#${p.rank_in_lab} of ${p.lab_active_faculty} in ${esc(p.lab)} by citations</span>` : "",
      p.hub ? `<span class="prof-badge">Hub author: links ${p.hub.institutions_bridged} institutions</span>` : "",
    ].join("");

    const tiles = [
      ["Papers 2016–26", fmt(p.papers)], ["Citations", fmt(p.citations)], ["h-index (2016–26)", p.h_index],
      ["Q1 journal share", hasPapers ? `${p.q1_share_pct}%` : "–"], ["Citations / paper", hasPapers ? p.mean_citations : "–"],
      ["Corresponding author", fmt(p.corresponding_papers)],
    ].map(([k, v]) => `<div class="prof-tile"><b>${v}</b><span>${k}</span></div>`).join("");

    let body = `<div class="prof-tiles">${tiles}</div>`;
    if (!hasPapers) {
      body += `<div class="card"><div class="prof-empty">No papers by this scientist in the 2016–2026 corpus (OpenAlex), so there is no publication profile to show.</div></div>`;
    } else {
      const collabs = p.collaborators || [];
      body += `
        <div class="card">
          <div class="prof-section-title">Papers per year</div>
          <div class="prof-section-sub">Distinct papers by publication year; hover a year for the citations those papers have received. * 2026 is a partial year.</div>
          ${lollipop(p.by_year)}
        </div>
        <div class="card">
          <div class="prof-section-title">Research areas</div>
          <div class="prof-section-sub">OpenAlex subfields of their papers (number of papers)</div>
          <div class="prof-tags">${(p.interests || []).map(t => `<span class="prof-tag">${esc(t.name)}<small>${t.papers}</small></span>`).join("")}</div>
        </div>
        <div class="card">
          <div class="prof-strip-head"><div class="prof-section-title">Key collaborators</div><span>${collabs.length ? "Hover to pause · click a CSIR faculty card to open their profile" : ""}</span></div>
          ${collabs.length ? marquee(collabs.slice(0, 12).map(collaboratorCard).join(""), Math.min(12, collabs.length))
                           : `<div class="prof-empty">No co-authors from the three labs with an OpenAlex ID.</div>`}
        </div>
        <div class="prof-grid-2">
          <div class="card">
            <div class="prof-section-title">Most-cited papers</div>
            <div class="prof-section-sub">2016–2026 papers by OpenAlex citation count</div>
            ${(p.top_papers || []).map(t => `<div class="prof-pub">
              ${t.doi ? `<a href="${esc(t.doi)}" target="_blank" rel="noopener">${esc(t.title)}</a>` : `<span class="prof-pub-title">${esc(t.title)}</span>`}
              <div class="meta">${esc(t.journal)} · ${t.year}${t.quartile ? ` · ${esc(t.quartile)}` : ""} · <b>${fmt(t.citations)}</b> citations</div>
            </div>`).join("")}
          </div>
          <div style="display:flex; flex-direction:column; gap:1.25rem;">
            <div class="card">
              <div class="prof-section-title">Top journals</div>
              <ul class="prof-list">${(p.journals || []).map(j => `<li><span>${esc(j.name)}${j.quartile ? ` <small>(${esc(j.quartile)})</small>` : ""}</span><span>${j.papers} papers</span></li>`).join("")}</ul>
            </div>
            <div class="card">
              <div class="prof-section-title">Indian partner institutions</div>
              ${(p.partners || []).length ? `<ul class="prof-list">${p.partners.map(x => `<li><span>${esc(x.name)}</span><span>${x.papers} papers</span></li>`).join("")}</ul>`
                                           : `<div class="prof-empty">No co-authors from other Indian institutions.</div>`}
            </div>
          </div>
        </div>
        <div class="card">
          <div class="prof-section-title">Collaboration network</div>
          <div class="prof-net-bar">
            <span><b id="prof-net-n">0</b> collaborators · <b id="prof-net-e">0</b> connections · drag nodes · scroll to zoom</span>
            <label>Show <select id="prof-net-top" class="filter-select" style="padding:0.25rem 0.5rem;">
              <option value="10">top 10</option><option value="20" selected>top 20</option><option value="30">top 30</option></select></label>
          </div>
          ${collabs.length ? `<div id="prof-net" class="prof-net" role="img" aria-label="Co-authorship network of ${esc(p.name)}"></div>`
                           : `<div class="prof-empty">No collaborators to draw.</div>`}
          <div class="prof-note" style="margin-top:0.5rem;">Co-authors from NCL, IICT and CECRI with an OpenAlex author ID (${fmt(p.n_coauthors || 0)} in total). Coloured nodes are CSIR faculty (click to open their profile), grey nodes other lab co-authors (students, project staff). Grey lines join collaborators who also wrote papers together with ${esc(p.name)}. Node size = joint papers.</div>
        </div>`;
    }

    return `<div class="prof-panel">
      <div class="prof-header">${avatar(p, true)}
        <div><h2 id="prof-title">${esc(p.name)}</h2>
          <div class="sub">${esc(p.designation)} · ${esc(titleCase(p.division))} · ${esc(p.lab)}${p.active_years ? ` · active ${esc(p.active_years)}` : ""}</div>
          <div class="links">${links}</div></div>
        <button class="prof-close" aria-label="Close profile">×</button>
      </div>
      <div class="prof-body">${body}
        <div class="prof-note">Source: OpenAlex works 2016–2026 (collected 13 Oct 2026), faculty roster from the institute websites, SJR quartiles. Counts are distinct papers; citations are OpenAlex cited-by counts.</div>
      </div>
    </div>`;
  }

  function drawNetwork(p, topN) {
    const el = document.getElementById("prof-net");
    if (!el || !window.echarts) return;
    if (netChart) netChart.dispose();
    netChart = echarts.init(el);
    const collabs = (p.collaborators || []).slice(0, topN);
    const color = LAB_COLORS[p.lab_key] || LAB_COLORS.all;
    const nodes = [{
      id: "ego", name: p.name, symbolSize: 42, fixed: false,
      itemStyle: { color, borderColor: "#0f172a", borderWidth: 2 },
      label: { show: true, formatter: initials(p.name), color: "#fff", fontWeight: 700 }, ego: true,
    }].concat(collabs.map((c, i) => ({
      id: String(i), name: c.name, value: c.joint_papers, fid: c.faculty_id || null, lab: c.lab,
      symbolSize: Math.max(10, Math.min(32, Math.sqrt(c.joint_papers) * 5)),
      itemStyle: { color: c.faculty_id ? (LAB_COLOR_BY_NAME[c.lab] || color) : "#94a3b8", borderColor: "#fff", borderWidth: 1.5 },
      label: { show: c.joint_papers >= Math.max(3, collabs[Math.min(4, collabs.length - 1)].joint_papers), position: "right", fontSize: 10, color: "#334155" },
    })));
    const links = collabs.map((c, i) => ({ source: "ego", target: String(i), value: c.joint_papers,
      lineStyle: { color: "rgba(26,35,126,0.35)", width: c.joint_papers >= 10 ? 2.2 : 1.2 } }));
    (p.collab_links || []).forEach(([a, b, n]) => {
      if (a < topN && b < topN) links.push({ source: String(a), target: String(b), value: n, lineStyle: { color: "rgba(0,0,0,0.12)", width: 1 } });
    });
    document.getElementById("prof-net-n").textContent = collabs.length;
    document.getElementById("prof-net-e").textContent = links.length;
    netChart.setOption({
      tooltip: {
        formatter: prm => {
          if (prm.dataType === "edge") return `${prm.value} joint paper${prm.value === 1 ? "" : "s"}`;
          const d = prm.data;
          if (d.ego) return `<b>${esc(d.name)}</b><br/>${fmt(p.papers)} papers`;
          return `<b>${esc(d.name)}</b><br/>${esc(d.lab)}<br/>${d.value} joint paper${d.value === 1 ? "" : "s"}${d.fid ? "<br/><i>Click to open profile</i>" : ""}`;
        },
      },
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true, data: nodes, links,
        force: { repulsion: 220, edgeLength: [60, 150], gravity: 0.08 },
        emphasis: { focus: "adjacency", lineStyle: { width: 2.5 } },
      }],
    });
    netChart.on("click", prm => { if (prm.dataType === "node" && prm.data.fid) open(prm.data.fid); });
  }

  function open(fid) {
    const p = PROFILES[fid];
    if (!p) return;
    hideHover(); hoverFid = null;
    if (!current) lastFocus = document.activeElement;
    current = fid;
    const ov = ensureOverlay();
    ov.innerHTML = render(p);
    ov.setAttribute("aria-labelledby", "prof-title");
    ov.classList.add("open");
    ov.scrollTop = 0;
    document.body.classList.add("prof-lock");
    ov.querySelector(".prof-close").addEventListener("click", close);
    ov.querySelector(".prof-close").focus();
    const sel = ov.querySelector("#prof-net-top");
    if (sel) sel.addEventListener("change", () => drawNetwork(p, parseInt(sel.value, 10)));
    drawNetwork(p, 20);
    if (location.hash !== `#profile=${fid}`) history.replaceState(null, "", `#profile=${fid}`);
  }

  function close() {
    if (!overlay || !current) return;
    overlay.classList.remove("open");
    document.body.classList.remove("prof-lock");
    if (netChart) { netChart.dispose(); netChart = null; }
    current = null;
    if (location.hash.startsWith("#profile=")) history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function openFromHash() {
    const m = location.hash.match(/^#profile=([\w-]+)/);
    if (m && PROFILES[m[1]]) open(m[1]);
  }
  window.addEventListener("hashchange", openFromHash);
  window.addEventListener("resize", () => { if (netChart) netChart.resize(); });
  document.addEventListener("DOMContentLoaded", () => setTimeout(openFromHash, 0));

  window.G24Profiles = {
    open, close, showHover, hideHover, renderFeatured,
    has: fid => !!PROFILES[fid],
    fidByName: name => byName[name] || null,
    fidByOpenAlex: id => byOpenAlex[id] || null,
  };
})();
