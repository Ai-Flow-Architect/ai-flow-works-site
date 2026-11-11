# 各ページを実ブラウザで開き、JSエラーとコンソールのerrorを数える（ローカルの http.server に対して実行）
import sys
from playwright.sync_api import sync_playwright

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
pages = ["index.html", "premium.html", "business.html", "diagnose.html", "roi-calculator.html", "privacy.html", "404.html"]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name in pages:
        pg = b.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
        pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
        pg.goto(f"{base}/{name}", wait_until="load", timeout=30000)
        pg.wait_for_timeout(1500)
        print(name, len(errs))
        for e in errs[:5]:
            print("   ", e[:200])
        pg.close()
    b.close()
