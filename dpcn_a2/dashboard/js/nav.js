/**
 * Page navigation for the single-page dashboard: sticky-header offset, current-section
 * highlighting (top links + side dots), reading progress, the floating "next section"
 * button, the mobile section menu, and the filter panel with its active-filter chips.
 */
document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const header = document.getElementById("site-header");
  const sections = Array.from(document.querySelectorAll(".page-section"));
  const navLinks = Array.from(document.querySelectorAll(".nav-link[data-sec], .dot-nav a[data-sec]"));
  const progress = document.getElementById("scroll-progress-bar");
  const fab = document.getElementById("fab-next");
  const fabLabel = document.getElementById("fab-label");
  const fabArrow = fab ? fab.querySelector(".next-sec-arrow") : null;
  const menuBtn = document.getElementById("nav-menu-btn");
  const menu = document.getElementById("nav-links");
  if (!sections.length) return;

  // ---- Sticky header height (sections scroll to just below it) -------------
  const setHeaderHeight = () => {
    if (header) root.style.setProperty("--header-h", `${header.offsetHeight}px`);
  };
  setHeaderHeight();
  if (header && "ResizeObserver" in window) new ResizeObserver(setHeaderHeight).observe(header);

  // ---- Current section, progress bar, floating button ----------------------
  let current = -1;
  function currentIndex() {
    const line = (header ? header.offsetHeight : 0) + window.innerHeight * 0.3;
    let idx = 0;
    sections.forEach((sec, i) => { if (sec.getBoundingClientRect().top <= line) idx = i; });
    // at the very bottom, the last section is current even if it is short
    if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) idx = sections.length - 1;
    return idx;
  }

  function update() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (progress) progress.style.width = `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;

    const idx = currentIndex();
    if (idx === current) return;
    current = idx;
    const id = sections[idx].id;
    navLinks.forEach(a => {
      const on = a.dataset.sec === id;
      a.classList.toggle("active", on);
      if (on) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
    });
    document.body.classList.toggle("on-hero", sections[idx].classList.contains("hero"));

    if (fab) {
      const last = idx === sections.length - 1;
      const next = sections[idx + 1];
      fab.dataset.target = last ? sections[0].id : next.id;
      if (fabLabel) fabLabel.textContent = last ? "Back to top" : `Next: ${next.dataset.label}`;
      fab.setAttribute("aria-label", last ? "Back to top" : `Next section: ${next.dataset.label}`);
      if (fabArrow) fabArrow.classList.toggle("up", last);
    }
  }

  let ticking = false;
  const onScroll = () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { ticking = false; update(); });
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();

  if (fab) {
    fab.addEventListener("click", () => {
      const t = document.getElementById(fab.dataset.target || sections[1].id);
      if (t) t.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  // ---- Mobile section menu -------------------------------------------------
  if (menuBtn && menu) {
    const setMenu = open => {
      menu.classList.toggle("open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
    };
    menuBtn.addEventListener("click", () => setMenu(!menu.classList.contains("open")));
    menu.addEventListener("click", e => { if (e.target.closest("a")) setMenu(false); });
    document.addEventListener("click", e => {
      if (menu.classList.contains("open") && !menu.contains(e.target) && e.target !== menuBtn) setMenu(false);
    });
  }

  // ---- Filter panel and active-filter chips --------------------------------
  const btnFilters = document.getElementById("btn-filters");
  const panel = document.getElementById("filter-panel");
  const chips = document.getElementById("filter-chips");
  const count = document.getElementById("filter-count");
  const FILTERS = [
    { id: "filter-year-min", def: "2016", fmt: () => null },  // shown together with the max year
    { id: "filter-year-max", def: "2026", fmt: () => null },
    { id: "filter-type", def: "all", fmt: t => t },
    { id: "filter-quartile", def: "all", fmt: t => t },
    { id: "filter-field", def: "all", fmt: t => `Field: ${t}` },
    { id: "filter-if", def: "0", fmt: t => `Journal ${t}` },
    { id: "filter-q1-papers", def: "0", fmt: t => `Scientists: ${t}` },
  ];

  if (btnFilters && panel) {
    btnFilters.addEventListener("click", () => {
      const open = panel.hidden;
      panel.hidden = !open;
      btnFilters.setAttribute("aria-expanded", String(open));
    });
  }

  function renderChips() {
    if (!chips) return;
    const sel = id => document.getElementById(id);
    const active = [];
    const yMin = sel("filter-year-min"), yMax = sel("filter-year-max");
    if (yMin && yMax && (yMin.value !== "2016" || yMax.value !== "2026")) {
      active.push({ label: `Years ${yMin.value}–${yMax.value}`, reset: () => { yMin.value = "2016"; yMax.value = "2026"; return yMin; } });
    }
    FILTERS.forEach(f => {
      const el = sel(f.id);
      if (!el || el.value === f.def) return;
      const label = f.fmt(el.options[el.selectedIndex].textContent.trim());
      if (label) active.push({ label, reset: () => { el.value = f.def; return el; } });
    });

    if (count) { count.hidden = active.length === 0; count.textContent = String(active.length); }
    if (!active.length) {
      chips.innerHTML = '<span class="chip chip-muted">No filters · all papers 2016–2026</span>';
      return;
    }
    chips.innerHTML = "";
    active.forEach(a => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.title = "Remove this filter";
      b.innerHTML = `<span></span><span class="x" aria-hidden="true">×</span>`;
      b.firstChild.textContent = a.label;
      b.setAttribute("aria-label", `Remove filter ${a.label}`);
      b.addEventListener("click", () => {
        const el = a.reset();
        el.dispatchEvent(new Event("change"));  // app.js recomputes everything on change
      });
      chips.appendChild(b);
    });
  }

  FILTERS.forEach(f => {
    const el = document.getElementById(f.id);
    if (el) el.addEventListener("change", renderChips);
  });
  const btnReset = document.getElementById("btn-reset-filters");
  if (btnReset) btnReset.addEventListener("click", () => setTimeout(renderChips, 0));
  renderChips();
});
