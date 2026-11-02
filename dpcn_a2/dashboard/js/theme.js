/**
 * Light / dark theme for every dashboard page. Dark is the default.
 * Load in <head> (before the stylesheets apply) so the page never flashes the wrong theme.
 *
 * - Sets <html data-theme="dark|light">; the CSS defines both colour sets.
 * - Remembers the viewer's choice in localStorage when the browser allows it.
 * - Makes every ECharts chart use a matching theme (echarts.init is wrapped).
 * - Adds a toggle button: into [data-theme-slot] if the page has one, else floating.
 * - Pages that redraw their own charts set window.G24Theme.handlesCharts = true and listen
 *   for the "g24:theme" event; other pages reload so their charts pick up the new colours.
 */
(function () {
  const KEY = "g24-theme";
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked: use the default */ }
  let theme = saved === "light" || saved === "dark" ? saved : "dark";
  root.setAttribute("data-theme", theme);

  const ink = {
    dark: { text: "#e2e8f0", text2: "#cbd5e1", muted: "#94a3b8", axis: "#475569", split: "#243049", surface: "#151e30", tooltip: "#1b2539", tooltipBorder: "#3a4a68" },
    light: { text: "#1e293b", text2: "#475569", muted: "#64748b", axis: "#cbd5e1", split: "#e2e8f0", surface: "#ffffff", tooltip: "#ffffff", tooltipBorder: "#cbd5e1" },
  };

  const api = {
    get: () => theme,
    isDark: () => theme === "dark",
    ink: () => ink[theme],
    handlesCharts: false,
    set(t) {
      if (t !== "light" && t !== "dark" || t === theme) return;
      theme = t;
      root.setAttribute("data-theme", t);
      let stored = false;
      try { localStorage.setItem(KEY, t); stored = localStorage.getItem(KEY) === t; } catch (e) { stored = false; }
      updateButtons();
      if (api.handlesCharts) {
        document.dispatchEvent(new CustomEvent("g24:theme", { detail: { theme: t } }));
      } else if (stored && document.querySelector("[_echarts_instance_]")) {
        location.reload();  // simple pages: redraw charts with the new colours
      }
    },
    toggle() { api.set(theme === "dark" ? "light" : "dark"); },
  };
  window.G24Theme = api;

  function axisTheme(c) {
    return {
      axisLine: { lineStyle: { color: c.axis } },
      axisTick: { lineStyle: { color: c.axis } },
      axisLabel: { color: c.text2 },
      splitLine: { lineStyle: { color: [c.split] } },
      splitArea: { areaStyle: { color: ["rgba(255,255,255,0.02)", "rgba(0,0,0,0)"] } },
      nameTextStyle: { color: c.muted },
    };
  }

  // Light-theme neutral -> dark-theme neutral
  const DARK_SWAP = {
    "#0f172a": "#e2e8f0", "#1e293b": "#e2e8f0", "#334155": "#e2e8f0",
    "#475569": "#cbd5e1", "#64748b": "#94a3b8",
    "#cbd5e1": "#475569", "#e2e8f0": "#2a3650", "#f1f5f9": "#243049", "#f8fafc": "#243049",
  };
  const WHITE = { "#fff": 1, "#ffffff": 1, "white": 1 };
  function darken(v, key) {
    if (key === "tooltip") return v;
    if (typeof v === "string") {
      const k = v.toLowerCase();
      if (DARK_SWAP[k]) return DARK_SWAP[k];
      if (WHITE[k] && (key === "backgroundColor" || key === "borderColor")) return ink.dark.surface;
      return v;
    }
    if (Array.isArray(v)) return v.map(x => darken(x, key));
    if (v && typeof v === "object" && Object.getPrototypeOf(v) === Object.prototype) {
      const out = {};
      for (const k in v) out[k] = darken(v[k], k);
      return out;
    }
    return v;
  }

  function registerChartThemes() {
    if (!window.echarts || window.echarts.__g24Themed) return;
    const c = ink.dark;
    window.echarts.registerTheme("g24dark", {
      backgroundColor: "transparent",
      textStyle: { color: c.text2 },
      title: { textStyle: { color: c.text }, subtextStyle: { color: c.muted } },
      legend: { textStyle: { color: c.text2 }, pageTextStyle: { color: c.text2 }, pageIconColor: c.text2, pageIconInactiveColor: "#475569" },
      tooltip: { backgroundColor: c.tooltip, borderColor: c.tooltipBorder, textStyle: { color: c.text } },
      categoryAxis: axisTheme(c), valueAxis: axisTheme(c), logAxis: axisTheme(c), timeAxis: axisTheme(c),
      toolbox: { iconStyle: { borderColor: c.muted } },
      dataZoom: { textStyle: { color: c.text2 } },
      visualMap: { textStyle: { color: c.text2 } },
      pie: { label: { color: c.text2 }, labelLine: { lineStyle: { color: c.axis } } },
      graph: { label: { color: c.text } },
      sankey: { label: { color: c.text } },
      radar: { axisName: { color: c.text2 }, splitLine: { lineStyle: { color: c.split } }, axisLine: { lineStyle: { color: c.axis } } },
    });
    const init = window.echarts.init;
    window.echarts.init = function (dom, chartTheme, opts) {
      const inst = init.call(this, dom, chartTheme || (theme === "dark" ? "g24dark" : null), opts);
      // Pages written for a light background hard-code light greys in their chart options;
      // in the dark theme swap those for their dark equivalents (tooltips stay light).
      const setOption = inst.setOption;
      inst.setOption = function (option, ...rest) {
        if (theme === "dark" && !api.handlesCharts) option = darken(option, "");
        return setOption.call(this, option, ...rest);
      };
      return inst;
    };
    window.echarts.__g24Themed = true;
  }

  function buttonHTML() {
    return theme === "dark"
      ? '<span class="ti" aria-hidden="true">☀</span><span class="tl">Light</span>'
      : '<span class="ti" aria-hidden="true">☾</span><span class="tl">Dark</span>';
  }
  function updateButtons() {
    document.querySelectorAll(".theme-toggle").forEach(b => {
      b.innerHTML = buttonHTML();
      b.setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
      b.title = b.getAttribute("aria-label");
    });
  }
  function addButton() {
    if (document.querySelector(".theme-toggle")) return;
    const b = document.createElement("button");
    b.type = "button";
    b.className = "theme-toggle";
    b.addEventListener("click", api.toggle);
    const slot = document.querySelector("[data-theme-slot]");
    if (slot) slot.appendChild(b);
    else { b.classList.add("theme-toggle-floating"); document.body.appendChild(b); }
    updateButtons();
  }

  // Floating-button styles for pages without the main stylesheet
  const css = document.createElement("style");
  css.textContent = ".theme-toggle-floating{position:fixed;left:16px;bottom:16px;z-index:2000;display:inline-flex;align-items:center;gap:.4rem;" +
    "font:inherit;font-size:.82rem;font-weight:700;padding:.45rem .85rem;border-radius:999px;cursor:pointer;" +
    "border:1px solid rgba(148,163,184,.5);background:#151e30;color:#e2e8f0;box-shadow:0 6px 16px rgba(0,0,0,.3)}" +
    "[data-theme=light] .theme-toggle-floating{background:#fff;color:#1e293b}";
  document.head.appendChild(css);

  // If ECharts is already loaded (pages that load it in <head> before this file), theme it now;
  // otherwise on DOMContentLoaded, which runs before the page scripts' own handlers.
  registerChartThemes();
  document.addEventListener("DOMContentLoaded", () => { registerChartThemes(); addButton(); });
})();
