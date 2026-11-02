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

        # Verify Initial KPIs
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

        # Test Tab Switching & Content
        tabs = [
            ("faculty", "03_tab_faculty.png"),
            ("venues", "04_tab_venues.png"),
            ("areas", "05_tab_areas.png"),
            ("citation-net", "06_tab_citation_net.png"),
            ("authorship-net", "07_tab_authorship_net.png"),
            ("connectivity", "07b_tab_connectivity.png"),
            ("insights", "insights.png"),
            ("docs", "08_tab_docs.png"),
        ]

        for tab_id, ss_name in tabs:
            client.evaluate(f"document.querySelector('.tab-btn[data-tab=\"{tab_id}\"]').click()")
            time.sleep(0.5)
            # Check container active
            is_active = client.evaluate(f"document.getElementById('tab-{tab_id}').classList.contains('active')")
            assert is_active, f"Tab {tab_id} did not become active"

            # Check specific elements
            if tab_id == "faculty":
                # Check faculty table rows
                rows = client.evaluate("document.querySelectorAll('#table-faculty .tabulator-row').length")
                print(f"✓ Faculty Tab: {rows} rows visible in Tabulator table")
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
                print(f"✓ Venues Tab: {top_rows} top papers visible")
                assert top_rows >= 10
            elif tab_id == "citation-net":
                c_canvas = client.evaluate("document.querySelectorAll('#chart-citation-network canvas, #chart-citation-network svg').length")
                pr_rows = client.evaluate("document.querySelectorAll('#tbody-net-pagerank tr').length")
                flow_rows = client.evaluate("document.querySelectorAll('#tbody-net-cite-matrix tr').length")
                cite_edges = client.evaluate("document.getElementById('net-cite-kpi-edges').textContent")
                print(f"✓ Citation Net Tab: Canvas={c_canvas}, Top PR Rows={pr_rows}, Flow Matrix Rows={flow_rows}, Edges={cite_edges}")
                assert c_canvas > 0
                assert pr_rows == 10
                assert flow_rows == 3
                assert cite_edges == "27,754"
            elif tab_id == "authorship-net":
                a_canvas = client.evaluate("document.querySelectorAll('#chart-authorship-network canvas, #chart-authorship-network svg').length")
                bridge_rows = client.evaluate("document.querySelectorAll('#tbody-net-bridges tr').length")
                collab_rows = client.evaluate("document.querySelectorAll('#tbody-net-auth-matrix tr').length")
                auth_edges = client.evaluate("document.getElementById('net-auth-kpi-edges').textContent")
                print(f"✓ Authorship Net Tab: Canvas={a_canvas}, Bridge Rows={bridge_rows}, Collab Matrix Rows={collab_rows}, Edges={auth_edges}")
                assert a_canvas > 0
                assert bridge_rows == 10
                assert collab_rows == 3
                assert auth_edges == "65,058"
            elif tab_id == "connectivity":
                flow_canvas = client.evaluate("document.querySelectorAll('#chart-conn-flow canvas').length")
                sector_canvas = client.evaluate("document.querySelectorAll('#chart-conn-sectors canvas').length")
                citing_rows = client.evaluate("document.querySelectorAll('#tbody-conn-citing tr').length")
                hub_rows = client.evaluate("document.querySelectorAll('#tbody-conn-hubs tr').length")
                jac_rows = client.evaluate("document.querySelectorAll('#tbody-conn-jaccard tr').length")
                cites_kpi = client.evaluate("document.getElementById('conn-kpi-cites').textContent")
                ratio_kpi = client.evaluate("document.getElementById('conn-kpi-ratio').textContent")
                print(f"✓ Connectivity Tab: Charts={flow_canvas}/{sector_canvas}, Citing Rows={citing_rows}, Hub Rows={hub_rows}, Jaccard Rows={jac_rows}, Cites={cites_kpi}, Ratio={ratio_kpi}")
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
                card_count = client.evaluate("document.querySelectorAll('#insights-grid .card').length")
                chart_canvas = client.evaluate("document.querySelectorAll('#insights-grid canvas, #insights-grid svg').length")
                print(f"✓ Insights Tab: {card_count} finding cards, {chart_canvas} ECharts canvas elements rendered")
                assert card_count == 11
                assert chart_canvas >= 11
                # Test Card 11 interactive buttons
                diff_table_rows = client.evaluate("document.querySelectorAll('#tbody-diff-spreaders tr').length")
                assert diff_table_rows > 0, "Card 11 table rows should be populated"
                # Switch to Materials and Condition A first
                client.evaluate("document.querySelector('#diff-field-selector button[data-field=\"Materials\"]').click()")
                time.sleep(0.3)
                client.evaluate("document.querySelector('#diff-cond-selector button[data-cond=\"condition_a\"]').click()")
                time.sleep(0.3)
                client.evaluate("document.getElementById('card-insight-11').scrollIntoView()")
                time.sleep(0.5)
                client.capture_screenshot("dashboard/screenshots/11_card11_diffusion_cond_a_materials.png")
                print("  ✓ Captured: 11_card11_diffusion_cond_a_materials.png")

                # Switch to Condition B
                client.evaluate("document.querySelector('#diff-cond-selector button[data-cond=\"condition_b\"]').click()")
                time.sleep(0.3)
                mat_rows = client.evaluate("document.querySelectorAll('#tbody-diff-spreaders tr').length")
                print(f"  ✓ Card 11 interactive toggle: Materials (Condition B) rendered {mat_rows} spreader rows")
                assert mat_rows > 0
                client.capture_screenshot("dashboard/screenshots/11_card11_diffusion.png")
                print("  ✓ Captured: 11_card11_diffusion.png")

            elif tab_id == "docs":
                download_links = client.evaluate("document.querySelectorAll('#tab-docs a[download]').length")
                print(f"✓ Docs Tab: {download_links} downloadable deliverable links")
                assert download_links >= 7

            client.capture_screenshot(f"dashboard/screenshots/{ss_name}")
            print(f"✓ Captured: {ss_name}")

        # Switch back to Overview and test filters
        client.evaluate("document.querySelector('.tab-btn[data-tab=\"overview\"]').click()")
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

        # Faculty tab: h-index chart is stacked by campus for All; Q1-papers filter narrows the scientists
        client.evaluate("document.querySelector('.tab-btn[data-tab=\"faculty\"]').click()")
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

    # Test 3: Offline file:// test for insights11.html
    print("\n=== TESTING OFFLINE file:// PROTOCOL FOR INSIGHTS11.HTML ===")
    client_i11 = ChromeDevToolsClient(port=9335)
    try:
        abs_path_i11 = os.path.abspath("dashboard/insights11.html")
        file_url_i11 = f"file://{abs_path_i11}"
        print(f"Loading {file_url_i11}...")
        client_i11.start(file_url_i11)
        time.sleep(1.5)

        title_i11 = client_i11.evaluate("document.title")
        nodes_txt = client_i11.evaluate("document.getElementById('net-stat-nodes').textContent")
        print(f"✓ insights11.html Loaded: Title='{title_i11}', Connected Faculty Nodes={nodes_txt}")
        assert "Cadre Faculty Networks" in title_i11
        assert nodes_txt == "235"

        # Switch to Cleaning section
        client_i11.evaluate("document.querySelector(\".nav-btn[data-section='cleaning']\").click()")
        time.sleep(0.5)
        raw_val = client_i11.evaluate("document.getElementById('clean-stat-raw').textContent")
        print(f"✓ Cleaning section rendered: Raw Scraped={raw_val}")
        assert raw_val == "505"

        # Switch to Diffusion section
        client_i11.evaluate("document.querySelector(\".nav-btn[data-section='diffusion']\").click()")
        time.sleep(0.5)
        kpi_nimfa = client_i11.evaluate("document.getElementById('diff-kpi-nimfa-t50').textContent")
        print(f"✓ Diffusion section rendered: NIMFA T50={kpi_nimfa}")
        assert "steps" in kpi_nimfa

        # Verify MathJax SVG rendering
        mathjax_svgs = client_i11.evaluate("document.querySelectorAll('mjx-container svg').length")
        print(f"✓ MathJax SVG Math Elements rendered on insights11.html: {mathjax_svgs}")
        assert mathjax_svgs > 0, "No MathJax SVG elements rendered on insights11.html"

        client_i11.capture_screenshot("dashboard/screenshots/11_cadre_networks_suite.png")

        if client_i11.console_errors:
            print(f"❌ Console errors on insights11.html file://:")
            for err in client_i11.console_errors:
                print("  ERROR:", err)
            raise AssertionError("Console errors on insights11.html")
        else:
            print("✓ ZERO Console errors on insights11.html! Standalone suite is 100% offline-ready.")
    finally:
        client_i11.stop()

    macro_pages = [
        ("insight_smart_spec.html", "Smart Specialization", "chart-radar"),
        ("insight_academic_bridge.html", "Academic-Industrial Bridge", "chart-ker"),
        ("insight_frugal_rd.html", "Frugal Innovation", "chart-cost-q1"),
        ("insight_patents_papers.html", "Patent-to-Paper Decoupling", "chart-quadrant"),
        ("insight_leiden_benchmarks.html", "Global Leiden Crown Indicators", "chart-leiden-comp")
    ]

    for page_name, expected_title, chart_id in macro_pages:
        print(f"\n=== TESTING OFFLINE file:// PROTOCOL FOR {page_name.upper()} ===")
        abs_path = os.path.abspath(f"dashboard/{page_name}")
        file_url = f"file://{abs_path}"
        client_macro = ChromeDevToolsClient(port=9336)
        try:
            client_macro.start(file_url)
            time.sleep(1.0)
            page_title = client_macro.evaluate("document.title")
            print(f"✓ {page_name} Loaded: Title='{page_title}'")
            assert expected_title in page_title, f"Unexpected title {page_title} in {page_name}"
            chart_elems = client_macro.evaluate(f"document.querySelectorAll('#{chart_id} canvas, #{chart_id} svg').length")
            print(f"✓ {page_name} Chart '{chart_id}' rendered elements: {chart_elems}")
            assert chart_elems > 0, f"Chart {chart_id} not rendered in {page_name}"
            
            # Verify MathJax SVG rendering on macro pages
            mathjax_svgs = client_macro.evaluate("document.querySelectorAll('mjx-container svg').length")
            print(f"✓ MathJax SVG Math Elements rendered on {page_name}: {mathjax_svgs}")
            assert mathjax_svgs > 0, f"No MathJax SVG elements rendered on {page_name}"
            
            if client_macro.console_errors:
                print(f"❌ Console errors on {page_name}:")
                for err in client_macro.console_errors:
                    print("  ERROR:", err)
                raise AssertionError(f"Console errors on {page_name}")
            else:
                print(f"✓ ZERO Console errors on {page_name}! 100% offline-ready.")
        finally:
            client_macro.stop()

    print("\n=== ALL BROWSER VERIFICATION TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_tests()
