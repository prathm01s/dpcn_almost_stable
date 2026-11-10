"""Browser verification script using Chrome DevTools Protocol.
Tests Group 24 Dashboard across all views, tabs, filters, and offline capabilities.
Captures screenshots and checks for any JavaScript errors.
"""

import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import websocket


class ChromeDevToolsClient:
    def __init__(self, port=9333, width=1600, height=1000):
        self.port = port
        self.width = width
        self.height = height
        self.tmp_dir = tempfile.mkdtemp()
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.console_errors = []
        self.console_logs = []

    def start(self, initial_url):
        self.proc = subprocess.Popen([
            "google-chrome",
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            f"--user-data-dir={self.tmp_dir}",
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            f"--window-size={self.width},{self.height}",
            initial_url
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(2.0)
        # Find page target
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list").read().decode())
        page_targets = [t for t in targets if t.get("type") == "page" and "dashboard" in t.get("url", "")]
        if not page_targets:
            page_targets = [t for t in targets if t.get("type") == "page"]
        
        target = page_targets[0]
        ws_url = target["webSocketDebuggerUrl"]
        self.ws = websocket.create_connection(ws_url)

        # Enable domains
        self.send("Runtime.enable")
        self.send("Page.enable")
        self.send("Console.enable")

    def stop(self):
        if self.ws:
            self.ws.close()
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def send(self, method, params=None):
        self.msg_id += 1
        curr_id = self.msg_id
        payload = {"id": curr_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        
        start_time = time.time()
        while time.time() - start_time < 10:
            raw = self.ws.recv()
            msg = json.loads(raw)
            if "method" in msg:
                # Log events
                if msg["method"] == "Runtime.consoleAPICalled":
                    t = msg["params"].get("type")
                    args = [str(a.get("value", a.get("description", ""))) for a in msg["params"].get("args", [])]
                    txt = " ".join(args)
                    self.console_logs.append(f"[{t}] {txt}")
                    if t in ("error", "assert"):
                        self.console_errors.append(txt)
                elif msg["method"] == "Runtime.exceptionThrown":
                    exc = msg["params"].get("exceptionDetails", {})
                    self.console_errors.append(f"[Exception] {exc.get('text', '')}: {exc.get('exception', {}).get('description', '')}")
            elif msg.get("id") == curr_id:
                return msg.get("result", {})
        raise TimeoutError(f"Timeout waiting for response to {method}")

    def evaluate(self, expression):
        res = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        if "exceptionDetails" in res:
            err = res["exceptionDetails"]["exception"]["description"]
            raise RuntimeError(f"JS Error: {err}")
        return res.get("result", {}).get("value")

    def capture_screenshot(self, filepath):
        res = self.send("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])
        with open(filepath, "wb") as f:
            f.write(data)


def net_val(network, metric):
    """A value from stats/tables/network_summary.csv (the dashboard must show the same numbers)."""
    import csv
    with open("stats/tables/network_summary.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["network"] == network and r["metric"] == metric:
                return float(r["value"])
    raise KeyError((network, metric))


def run_tests():
    print("=== STARTING BROWSER VERIFICATION SUITE ===")

    # Test 1: Served over HTTP
    import functools
    import http.server
    import threading

    httpd = None
    try:
        httpd = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 8080),
            functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
        )
        srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        srv_thread.start()
        print("Started temporary HTTP server on port 8080")
    except OSError:
        pass  # Port already in use, reuse existing server

    client = ChromeDevToolsClient(port=9333)
    try:
        url = "http://127.0.0.1:8080/dashboard/index.html"
        print(f"Loading {url}...")
        client.start(url)
        time.sleep(1.5)

        title = client.evaluate("document.title")
        print(f"✓ Page Title: {title}")
        assert "Group 24" in title

        # Verify Initial KPIs (wait for the 7 MB data file to load and the first draw)
        for _ in range(60):
            if client.evaluate("document.getElementById('kpi-total-papers').textContent") != "-":
                break
            time.sleep(0.25)

        # Theme: light by default (D-36); the header toggle switches to dark and back, redrawing the charts
        client.evaluate("try { localStorage.removeItem('g24-theme'); } catch (e) {}")
        assert client.evaluate("document.documentElement.dataset.theme") == "light", "Light theme should be the default"
        client.evaluate("document.querySelector('.theme-toggle').click()")
        time.sleep(1.0)
        dark = client.evaluate("document.documentElement.dataset.theme")
        trend_ok = client.evaluate("!!echarts.getInstanceByDom(document.getElementById('chart-trend'))")
        client.evaluate("document.querySelector('.theme-toggle').click()")
        time.sleep(1.0)
        light = client.evaluate("document.documentElement.dataset.theme")
        print(f"✓ Theme toggle: light -> {dark} -> {light}, charts redrawn: {trend_ok}")
        assert dark == "dark" and light == "light" and trend_ok

        total_papers = client.evaluate("document.getElementById('kpi-total-papers').textContent")
        journal_papers = client.evaluate("document.getElementById('kpi-journal-papers').textContent")
        q1_share = client.evaluate("document.getElementById('kpi-q1-share').textContent")
        active_faculty = client.evaluate("document.getElementById('kpi-active-faculty').textContent")
        median_h = client.evaluate("document.getElementById('kpi-median-h').textContent")
        
        print(f"✓ Initial KPIs: Total Papers={total_papers}, Journals={journal_papers}, Q1={q1_share}, Faculty={active_faculty}, Median-h={median_h}")
        assert total_papers != "-" and int(total_papers.replace(",", "")) > 10000
        # Expected values come from the stats tables the dashboard is built from
        import csv
        with open("stats/tables/h_index_summary.csv", encoding="utf-8") as f:
            hsum = {r["institution"]: r for r in csv.DictReader(f)}
        assert int(active_faculty.replace(",", "")) == int(hsum["Group 24 Combined"]["active_faculty_count"])
        assert float(median_h) == float(hsum["Group 24 Combined"]["median_h_index"])

        # Screenshot Tab 1 (Overview)
        client.capture_screenshot("dashboard/screenshots/01_overview_all.png")
        print("✓ Captured: 01_overview_all.png")

        expected_inst_faculty = {
            "iict": int(hsum["CSIR-IICT"]["active_faculty_count"]),
            "ncl": int(hsum["CSIR-NCL"]["active_faculty_count"]),
            "cecri": int(hsum["CSIR-CECRI"]["active_faculty_count"]),
            "compare": int(hsum["Group 24 Combined"]["active_faculty_count"]),
        }

        # Test Institute Buttons
        for inst in ["iict", "ncl", "cecri", "compare"]:
            client.evaluate(f"document.querySelector('.inst-btn[data-inst=\"{inst}\"]').click()")
            time.sleep(0.3)
            p_count = client.evaluate("document.getElementById('kpi-total-papers').textContent")
            fac_count = client.evaluate("document.getElementById('kpi-active-faculty').textContent")
            print(f"✓ Institute {inst.upper()}: Papers={p_count}, Faculty={fac_count}")
            assert p_count != "-"
            assert int(fac_count.replace(",", "")) == expected_inst_faculty[inst]
            client.capture_screenshot(f"dashboard/screenshots/02_inst_{inst}.png")

        # Switch back to All
        client.evaluate("document.querySelector('.inst-btn[data-inst=\"all\"]').click()")
        time.sleep(0.3)

        # Scroll to each section of the single-page layout and check its content
        section_of = {"faculty": "faculty", "venues": "journals", "areas": "areas", "citation-net": "citations",
                      "authorship-net": "coauthorship", "connectivity": "india", "insights": "findings", "docs": "data",
                      "institutions": "institutions"}
        client.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
        tabs = [
            ("faculty", "03_tab_faculty.png"),
            ("venues", "04_tab_venues.png"),
            ("areas", "05_tab_areas.png"),
            ("citation-net", "06_tab_citation_net.png"),
            ("authorship-net", "07_tab_authorship_net.png"),
            ("institutions", "07c_institutions_time.png"),
            ("connectivity", "07b_tab_connectivity.png"),
            ("insights", "insights.png"),
            ("docs", "08_tab_docs.png"),
        ]

        for tab_id, ss_name in tabs:
            sec = section_of[tab_id]
            client.evaluate(f"document.getElementById('{sec}').scrollIntoView({{block: 'start'}})")
            time.sleep(1.5)  # network sections draw when they first come into view
            # The top navigation highlights the section in view
            active = client.evaluate("document.querySelector('.nav-link.active')?.dataset.sec || ''")
            assert active == sec, f"Section {sec} not highlighted in the navigation (got '{active}')"

            # Check specific elements
            if tab_id == "faculty":
                # Check faculty table rows
                rows = client.evaluate("document.querySelectorAll('#table-faculty .tabulator-row').length")
                print(f"✓ Faculty: {rows} rows visible in Tabulator table")
                assert rows > 0
                # Check department chart canvas
                dept_canvas = client.evaluate("document.querySelectorAll('#chart-departments canvas, #chart-departments svg').length")
                print(f"✓ Department chart rendered elements: {dept_canvas}")
                assert dept_canvas > 0
                # Scientist profiles: featured strip, hover card, profile panel
                featured = client.evaluate("document.querySelectorAll('#featured-scientists .prof-card[data-fid]').length")
                linked_rows = client.evaluate("document.querySelectorAll('#table-faculty .tabulator-row[data-fid]').length")
                client.evaluate("""(() => { const c = document.querySelector('#table-faculty .tabulator-row[data-fid] .tabulator-cell');
                    const b = c.getBoundingClientRect();
                    c.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, clientX: b.x + 10, clientY: b.y + 10})); })()""")
                time.sleep(0.3)
                hover = client.evaluate("!!document.querySelector('.prof-hover.show')")
                client.evaluate("document.querySelector('#table-faculty .tabulator-row[data-fid] .tabulator-cell').click()")
                time.sleep(1.0)
                title = client.evaluate("document.querySelector('.prof-overlay.open #prof-title')?.textContent || ''")
                net = client.evaluate("document.querySelectorAll('#prof-net canvas').length")
                print(f"✓ Profiles: Featured={featured}, Linked rows={linked_rows}, Hover={hover}, Opened='{title}', Network canvas={net}")
                assert featured > 0 and linked_rows > 0 and hover and title and net > 0
                client.capture_screenshot("dashboard/screenshots/03b_faculty_profile.png")
                client.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
                time.sleep(0.3)
                assert not client.evaluate("!!document.querySelector('.prof-overlay.open')")
            elif tab_id == "venues":
                top_rows = client.evaluate("document.querySelectorAll('#table-top-papers .tabulator-row').length")
                print(f"✓ Journals: {top_rows} top papers visible")
                assert top_rows >= 10
            elif tab_id == "citation-net":
                # faculty view is the default: one node per roster scientist (D-33)
                fac_canvas = client.evaluate("document.querySelectorAll('#chart-fac-cite-network canvas').length")
                fac_rows = client.evaluate("document.querySelectorAll('#tbody-fac-top-cited tr').length")
                fac_nodes = client.evaluate("document.getElementById('fac-cite-kpi-nodes').textContent")
                fac_edges = client.evaluate("document.getElementById('fac-cite-kpi-edges').textContent")
                print(f"✓ Faculty citation net: Canvas={fac_canvas}, Top rows={fac_rows}, Scientists={fac_nodes}, Links={fac_edges}")
                assert fac_canvas > 0 and fac_rows == 10
                assert fac_nodes == f"{int(net_val('faculty_citation', 'nodes (roster scientists with >= 1 paper)')):,}"
                assert fac_edges == f"{int(net_val('faculty_citation', 'directed edges (scientist A cites scientist B)')):,}"
                client.evaluate("document.querySelector('.net-view-btn[data-net=cite][data-view=papers]').click()")
                time.sleep(1.5)
                c_canvas = client.evaluate("document.querySelectorAll('#chart-citation-network canvas, #chart-citation-network svg').length")
                pr_rows = client.evaluate("document.querySelectorAll('#tbody-net-pagerank tr').length")
                flow_rows = client.evaluate("document.querySelectorAll('#tbody-net-cite-matrix tr').length")
                cite_edges = client.evaluate("document.getElementById('net-cite-kpi-edges').textContent")
                cite_nodes = client.evaluate("document.getElementById('net-cite-kpi-nodes').textContent")
                print(f"✓ Paper citation net: Canvas={c_canvas}, Top PR Rows={pr_rows}, Flow Matrix Rows={flow_rows}, Papers={cite_nodes}, Links={cite_edges}")
                assert c_canvas > 0 and pr_rows == 10 and flow_rows == 3
                assert cite_edges == f"{int(net_val('citation', 'distinct citing-cited paper pairs')):,}"
                assert cite_nodes == f"{int(net_val('citation', 'nodes (papers with >= 1 in-corpus link)')):,}"
                client.evaluate("document.querySelector('.net-view-btn[data-net=cite][data-view=faculty]').click()")
                time.sleep(0.5)
            elif tab_id == "authorship-net":
                fac_canvas = client.evaluate("document.querySelectorAll('#chart-fac-auth-network canvas').length")
                fac_rows = client.evaluate("document.querySelectorAll('#tbody-fac-bridges tr').length")
                fac_nodes = client.evaluate("document.getElementById('fac-auth-kpi-nodes').textContent")
                fac_pairs = client.evaluate("document.getElementById('fac-auth-kpi-edges').textContent")
                print(f"✓ Faculty co-authorship net: Canvas={fac_canvas}, Top rows={fac_rows}, Scientists={fac_nodes}, Pairs={fac_pairs}")
                assert fac_canvas > 0 and fac_rows == 10
                assert fac_nodes == f"{int(net_val('faculty_coauthorship', 'nodes (roster scientists with >= 1 paper)')):,}"
                assert fac_pairs == f"{int(net_val('faculty_coauthorship', 'co-author pairs (unique edges)')):,}"
                client.evaluate("document.querySelector('.net-view-btn[data-net=auth][data-view=papers]').click()")
                time.sleep(1.5)
                a_canvas = client.evaluate("document.querySelectorAll('#chart-authorship-network canvas, #chart-authorship-network svg').length")
                bridge_rows = client.evaluate("document.querySelectorAll('#tbody-net-bridges tr').length")
                collab_rows = client.evaluate("document.querySelectorAll('#tbody-net-auth-matrix tr').length")
                auth_nodes = client.evaluate("document.getElementById('net-auth-kpi-nodes').textContent")
                print(f"✓ All-author net: Canvas={a_canvas}, Bridge Rows={bridge_rows}, Collab Matrix Rows={collab_rows}, Authors={auth_nodes}")
                assert a_canvas > 0 and bridge_rows == 10 and collab_rows == 3
                assert auth_nodes == f"{int(net_val('authorship', 'authors (nodes)')):,}"
                client.evaluate("document.querySelector('.net-view-btn[data-net=auth][data-view=faculty]').click()")
                time.sleep(0.5)
            elif tab_id == "connectivity":
                cit_rows = client.evaluate("Tabulator.findTable('#table-p2-citing')[0].getDataCount()")
                findings = client.evaluate("document.getElementById('p2-citing-findings').textContent")
                print(f"✓ Who cites the labs: diagnostic rows={cit_rows}")
                assert cit_rows == 29 and "Largest non-governmental citers:" in findings and "Saveetha" in findings
                flow_canvas = client.evaluate("document.querySelectorAll('#chart-conn-flow canvas').length")
                sector_canvas = client.evaluate("document.querySelectorAll('#chart-conn-sectors canvas').length")
                citing_rows = client.evaluate("document.querySelectorAll('#tbody-conn-citing tr').length")
                hub_rows = client.evaluate("document.querySelectorAll('#tbody-conn-hubs tr').length")
                jac_rows = client.evaluate("document.querySelectorAll('#tbody-conn-jaccard tr').length")
                cites_kpi = client.evaluate("document.getElementById('conn-kpi-cites').textContent")
                ratio_kpi = client.evaluate("document.getElementById('conn-kpi-ratio').textContent")
                print(f"✓ Connectivity: Charts={flow_canvas}/{sector_canvas}, Citing Rows={citing_rows}, Hub Rows={hub_rows}, Jaccard Rows={jac_rows}, Cites={cites_kpi}, Ratio={ratio_kpi}")
                assert flow_canvas > 0 and sector_canvas > 0
                assert citing_rows == 10 and hub_rows == 25 and jac_rows == 3
                assert cites_kpi not in ("—%", "0%", "0.0%")
                assert ratio_kpi != "—"
                for inst in ["iict", "ncl", "cecri", "compare", "all"]:
                    client.evaluate(f"document.querySelector('.inst-btn[data-inst=\"{inst}\"]').click()")
                    time.sleep(0.3)
                    rows = client.evaluate("document.querySelectorAll('#tbody-conn-citing tr').length")
                    print(f"  ✓ Connectivity {inst.upper()}: {rows} citing-institute rows")
                    assert rows == 10
            elif tab_id == "insights":
                card_count = client.evaluate("document.querySelectorAll('#insights-grid .insight-card').length")
                stats = client.evaluate("document.querySelectorAll('#insights-grid .ic-stat').length")
                print(f"✓ Key Findings: {card_count} finding boxes, {stats} with a headline number")
                assert card_count == 8 and stats == 8
                # Each box opens a modal with its chart
                for i in range(card_count):
                    client.evaluate(f"document.querySelectorAll('#insights-grid .insight-card')[{i}].click()")
                    time.sleep(0.6)
                    shown = client.evaluate("!document.getElementById('ins-overlay').hidden")
                    canv = client.evaluate("document.querySelectorAll('#ins-body canvas, #ins-body svg').length")
                    assert shown and canv > 0, f"Finding {i + 1}: modal shown={shown}, chart elements={canv}"
                print(f"  ✓ All {card_count} finding modals open with a chart")
                # Insight 11 is a featured card on the home screen linking to its own page (D-38)
                # The two lead studies are large cards on the home screen, filled from the data (D-39)
                lead = client.evaluate("[document.querySelectorAll('#lead-i11-spark polyline').length, document.getElementById('lead-i11-check').textContent, "
                                       "document.querySelector('#lead-i11').getAttribute('href'), document.querySelectorAll('#lead-global-bars .lead-bar').length, "
                                       "document.querySelector('#lead-global').getAttribute('href'), document.querySelectorAll('.lead-stat').length]")
                print(f"  ✓ Lead-study cards: {lead}")
                assert lead[0] == 2 and "claims verified" in lead[1] and lead[2] == "insights11.html"
                assert lead[3] == 5 and lead[4] == "global.html" and lead[5] == 6
                client.evaluate("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
                time.sleep(0.3)
                assert client.evaluate("document.getElementById('ins-overlay').hidden"), "Escape should close the finding modal"

            elif tab_id == "institutions":
                # Phase II (D-34): institutional network and temporal analysis
                inst_canvas = client.evaluate("document.querySelectorAll('#chart-p2-inst-network canvas').length")
                temp_rows = client.evaluate("document.querySelectorAll('#p2-temporal-table tbody tr').length")
                inst_rows = client.evaluate("document.querySelectorAll('#p2-inst-table tbody tr').length")
                print(f"✓ Institutions & time: network canvas={inst_canvas}, partner rows={inst_rows}, periods={temp_rows}")
                assert inst_canvas > 0 and inst_rows == 15 and temp_rows == 4
            elif tab_id == "docs":
                download_links = client.evaluate("document.querySelectorAll('#data a[download]').length")
                print(f"✓ Data & Methods: {download_links} downloadable deliverable links")
                assert download_links >= 7

            client.capture_screenshot(f"dashboard/screenshots/{ss_name}")
            print(f"✓ Captured: {ss_name}")

        # Back to the trends section and test filters
        client.evaluate("document.getElementById('trends').scrollIntoView({block: 'start'})")
        time.sleep(0.8)
        # IR > 5 / IR > 10 card (D-33): numbers must match stats/tables/impact_ratio_summary.csv
        import csv
        with open("stats/tables/impact_ratio_summary.csv", encoding="utf-8") as f:
            irs = {r["institution"]: r for r in csv.DictReader(f)}
        kpi_txt = client.evaluate("document.getElementById('ir-hi-kpis').textContent")
        n5 = int(irs["Group 24 Combined"]["ir_q1_gt_5"]); n10 = int(irs["Group 24 Combined"]["ir_q1_gt_10"])
        rows5 = client.evaluate("Tabulator.findTable('#table-ir-high')[0].getDataCount()")
        client.evaluate("document.querySelector('#ir-hi-tabs button[data-t=\"10\"]').click()")
        time.sleep(0.4)
        rows10 = client.evaluate("Tabulator.findTable('#table-ir-high')[0].getDataCount()")
        print(f"✓ IR card: IR>5 rows={rows5} (table {n5}), IR>10 rows={rows10} (table {n10})")
        assert f"{n5:,}" in kpi_txt and rows5 == n5 and rows10 == n10
        client.evaluate("document.querySelector('#ir-hi-tabs button[data-t=\"5\"]').click()")
        # Phase II panels (D-34): numbers equal stats/tables/phase2_*.csv
        with open("stats/tables/phase2_overview.csv", encoding="utf-8") as f:
            p2o = {r["institution"]: r for r in csv.DictReader(f)}
        ov_txt = client.evaluate("document.getElementById('p2-overview-table').textContent")
        ov_rows = client.evaluate("document.querySelectorAll('#p2-overview-table tbody tr').length")
        allr = p2o["Group 24 Combined"]
        print(f"✓ Phase II overview: rows={ov_rows}, Q1&IF>10 all three={allr['q1_if_gt10']}")
        assert ov_rows == 4 and f"{int(allr['q1_if_gt10']):,}" in ov_txt and f"{int(allr['papers_ge10_authors']):,}" in ov_txt
        fac_rows = client.evaluate("Tabulator.findTable('#table-p2-faculty')[0].getDataCount()")
        top30 = client.evaluate("Tabulator.findTable('#table-p2-top30')[0].getDataCount()")
        print(f"✓ Phase II faculty comparison rows={fac_rows}, top-30 by IF rows={top30}")
        assert fac_rows == int(p2o["Group 24 Combined"]["active_faculty"]) and top30 == 30
        time.sleep(0.3)

        # Filter Year: 2020 - 2024
        client.evaluate("document.getElementById('filter-year-min').value = '2020'")
        client.evaluate("document.getElementById('filter-year-max').value = '2024'")
        client.evaluate("document.getElementById('filter-year-min').dispatchEvent(new Event('change'))")
        time.sleep(0.3)
        filtered_papers = client.evaluate("document.getElementById('kpi-total-papers').textContent")
        filtered_int = int(filtered_papers.replace(",", ""))
        print(f"✓ Filtered 2020-2024: Papers={filtered_papers}")
        assert 5000 < filtered_int < 14000
        client.capture_screenshot("dashboard/screenshots/09_filter_2020_2024.png")

        # Reset filters
        client.evaluate("document.getElementById('btn-reset-filters').click()")
        time.sleep(0.3)
        reset_papers = client.evaluate("document.getElementById('kpi-total-papers').textContent")
        print(f"✓ After Reset: Papers={reset_papers}")
        assert reset_papers == total_papers

        # Journal IF filter (SCImago 2-yr cites/doc): KPI = distinct papers whose journal IF >= 5
        expected_if5 = client.evaluate(
            "new Set(window.G24_DATA.papers_compact.filter(p => p.jif != null && p.jif >= 5).map(p => p.id)).size")
        client.evaluate("document.getElementById('filter-if').value = '5'")
        client.evaluate("document.getElementById('filter-if').dispatchEvent(new Event('change'))")
        time.sleep(0.3)
        if5_papers = int(client.evaluate("document.getElementById('kpi-total-papers').textContent").replace(",", ""))
        print(f"✓ IF ≥ 5: Papers={if5_papers:,} (expected {expected_if5:,})")
        assert if5_papers == expected_if5 and 0 < if5_papers < int(total_papers.replace(",", ""))
        client.evaluate("document.getElementById('btn-reset-filters').click()")
        time.sleep(0.3)

        # Faculty section: h-index chart is stacked by campus for All; Q1-papers filter narrows the scientists
        client.evaluate("document.getElementById('faculty').scrollIntoView({block: 'start'})")
        time.sleep(0.5)
        h_series = client.evaluate(
            "JSON.stringify(echarts.getInstanceByDom(document.getElementById('chart-h-index')).getOption().series"
            ".map(s => [s.name, s.data.reduce((a, b) => a + b, 0)]))")
        h_series = json.loads(h_series)
        print(f"✓ h-index by campus (All): {h_series}")
        assert [s[0] for s in h_series] == ["CSIR-IICT", "CSIR-NCL", "CSIR-CECRI"]
        assert sum(s[1] for s in h_series) == int(client.evaluate("document.getElementById('kpi-active-faculty').textContent").replace(",", ""))
        for minq1 in ("5", "10"):
            expected = client.evaluate(
                f"window.G24_DATA.by_institute.all.faculty.filter(f => f.q1_papers > {minq1} && f.papers > 0).length")
            client.evaluate(f"document.getElementById('filter-q1-papers').value = '{minq1}'")
            client.evaluate("document.getElementById('filter-q1-papers').dispatchEvent(new Event('change'))")
            time.sleep(0.4)
            active = int(client.evaluate("document.getElementById('kpi-active-faculty').textContent").replace(",", ""))
            rows = client.evaluate("Tabulator.findTable('#table-faculty')[0].getDataCount()")
            print(f"✓ > {minq1} Q1 papers: {active} active scientists, {rows} directory rows")
            assert active == expected and rows >= active
        client.capture_screenshot("dashboard/screenshots/03c_faculty_q1_filter.png")
        client.evaluate("document.getElementById('btn-reset-filters').click()")
        time.sleep(0.3)

        print("\n--- Console Output Summary ---")
        for l in client.console_logs:
            print("  ", l)
        
        print("\n--- Console Errors Check ---")
        if client.console_errors:
            print(f"❌ {len(client.console_errors)} Console errors found:")
            for err in client.console_errors:
                print("  ERROR:", err)
            raise AssertionError("Console errors detected during run")
        else:
            print("✓ ZERO Console errors detected! Clean execution.")

    finally:
        client.stop()

    # Test 2: Offline file:// protocol verification
    print("\n=== TESTING OFFLINE file:// PROTOCOL ===")
    client_file = ChromeDevToolsClient(port=9334)
    try:
        abs_path = os.path.abspath("dashboard/index.html")
        file_url = f"file://{abs_path}"
        print(f"Loading {file_url}...")
        client_file.start(file_url)
        time.sleep(1.5)

        title = client_file.evaluate("document.title")
        papers = client_file.evaluate("document.getElementById('kpi-total-papers').textContent")
        print(f"✓ file:// Loaded: Title='{title}', Total Papers={papers}")
        assert "Group 24" in title
        assert papers != "-" and int(papers.replace(",", "")) > 10000

        if client_file.console_errors:
            print(f"❌ Console errors on file://:")
            for err in client_file.console_errors:
                print("  ERROR:", err)
            raise AssertionError("Console errors on file://")
        else:
            print("✓ ZERO Console errors on file:// protocol! 100% offline-ready.")
    finally:
        client_file.stop()

    # Test 3: Insight 11 page (D-38), offline over file://
    print("\n=== TESTING OFFLINE file:// PROTOCOL FOR INSIGHTS11.HTML ===")
    client_i11 = ChromeDevToolsClient(port=9335)
    try:
        client_i11.start(f"file://{os.path.abspath('dashboard/insights11.html')}")
        for _ in range(40):
            if client_i11.evaluate("document.querySelectorAll('#i-kpis .kpi-card').length") > 0:
                break
            time.sleep(0.25)
        title_i11 = client_i11.evaluate("document.title")
        assert "Insight 11" in title_i11, title_i11
        for cid in ["ch-faculty", "ch-threshold", "ch-field", "ch-overlay", "ch-meanfield", "ch-origin"]:
            assert client_i11.evaluate(f"document.querySelectorAll('#{cid} canvas').length") > 0, f"{cid} not rendered"
        assert client_i11.evaluate("document.querySelectorAll('#i-toc a').length") == 8
        assert client_i11.evaluate("document.querySelectorAll('.g-answer').length") == 7
        claims = client_i11.evaluate("[document.querySelectorAll('#tbl-claims tbody tr').length, document.querySelectorAll('#tbl-claims .i-fail').length]")
        print(f"✓ insights11.html: 6 charts; claims table {claims[0]} rows, {claims[1]} failed")
        assert claims[0] >= 10 and claims[1] == 0
        # every switch redraws
        client_i11.evaluate("document.querySelectorAll('.g-seg button').forEach(b => b.click())")
        time.sleep(1.0)
        for _ in range(40):
            if client_i11.evaluate("document.querySelectorAll('mjx-container svg').length") > 10:
                break
            time.sleep(0.25)
        mathjax_svgs = client_i11.evaluate("document.querySelectorAll('mjx-container svg').length")
        print(f"✓ MathJax formulas rendered on insights11.html: {mathjax_svgs}")
        assert mathjax_svgs > 10, "Formulas did not render"
        if client_i11.console_errors:
            for err in client_i11.console_errors:
                print("  ERROR:", err)
            raise AssertionError("Console errors on insights11.html")
        print("✓ ZERO Console errors on insights11.html")
    finally:
        client_i11.stop()

    # Withdrawn studies (D-33): kept in the repo with a banner, not linked from the dashboard
    withdrawn_pages = ["insight_smart_spec.html", "insight_frugal_rd.html",
                       "insight_patents_papers.html", "insight_leiden_benchmarks.html"]
    index_html = open("dashboard/index.html", encoding="utf-8").read()
    for page_name in withdrawn_pages:
        assert page_name not in index_html, f"Withdrawn page {page_name} is still linked from index.html"
        assert "Withdrawn from the Group 24 dashboard" in open(f"dashboard/{page_name}", encoding="utf-8").read()
    print(f"\n✓ Withdrawn pages unlinked and bannered: {len(withdrawn_pages)}")

    # The Academic Bridge (Study 1.1) is now part of the Global Benchmark (D-39); its old address redirects
    bridge = open("dashboard/insight_academic_bridge.html", encoding="utf-8").read()
    assert 'url=global.html#g-india' in bridge and "insight_academic_bridge.html" not in index_html
    print("✓ Academic Bridge page redirects to global.html#g-india")

    # Global Benchmark page (D-35): linked from the home screen, renders offline without errors
    print("\n=== TESTING GLOBAL BENCHMARK PAGE (file://) ===")
    index_html = open("dashboard/index.html", encoding="utf-8").read()
    assert 'href="global.html" class="lead-card lead-global"' in index_html, "Home screen lacks the Global Benchmark card"
    client_g = ChromeDevToolsClient(port=9337)
    try:
        client_g.start(f"file://{os.path.abspath('dashboard/global.html')}")
        for _ in range(40):
            if client_g.evaluate("document.querySelectorAll('#g-kpis .kpi-card').length") > 0:
                break
            time.sleep(0.25)
        assert "Global Benchmark" in client_g.evaluate("document.title")
        for cid in ["ch-countries", "ch-index", "ch-cagr", "ch-world", "ch-impact", "ch-profiles", "ch-collab", "ch-flows", "ch-india"]:
            n = client_g.evaluate(f"document.querySelectorAll('#{cid} canvas').length")
            assert n > 0, f"Chart {cid} not rendered on global.html"
        # contents cards carry an answer for every section
        assert client_g.evaluate("document.querySelectorAll('#g-toc a').length") == 8
        assert client_g.evaluate("[...document.querySelectorAll('.g-answer')].every(e => e.textContent.trim().length > 40)")
        # tables sit in collapsed sections and are built when opened
        client_g.evaluate("document.querySelectorAll('details.g-more').forEach(d => d.open = true)")
        time.sleep(1.0)
        assert client_g.evaluate("document.querySelectorAll('#tbl-india tbody tr').length") == 60
        for tid in ["tbl-countries", "tbl-sim", "tbl-summary", "tbl-links"]:
            rows = client_g.evaluate(f"document.querySelectorAll('#{tid} .tabulator-row').length")
            assert rows > 0, f"Table {tid} empty on global.html"
        assert client_g.evaluate("document.querySelectorAll('#g-rules li').length") >= 6, "Peer rules missing"
        assert client_g.evaluate("document.querySelectorAll('#peer-cards .g-peer').length") >= 10, "Peer cards missing"
        # every switch redraws without errors
        client_g.evaluate("document.querySelectorAll('#seg-index button, #seg-impact button, #seg-flows button').forEach(b => b.click())")
        time.sleep(0.5)
        title_now = client_g.evaluate("document.getElementById('impact-title').textContent")
        assert "international" in title_now.lower() or "country" in title_now.lower(), title_now
        if client_g.console_errors:
            for err in client_g.console_errors:
                print("  ERROR:", err)
            raise AssertionError("Console errors on global.html")
        print("✓ global.html: 9 charts, contents with answers, 5 tables, rules and peers rendered; zero console errors")
    finally:
        client_g.stop()

    print("\n=== ALL BROWSER VERIFICATION TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_tests()
