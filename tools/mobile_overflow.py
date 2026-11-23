# スマホ幅（375px）で横はみ出しが無いか（ページ全体の幅＞画面幅なら NG）。黒・白・診断の3枚。
# 使い方: python3 tools/mobile_overflow.py http://127.0.0.1:8765 [--shot <保存先フォルダ>]
import os
import sys
from playwright.sync_api import sync_playwright

base = sys.argv[1]
shot = sys.argv[sys.argv.index("--shot") + 1] if "--shot" in sys.argv else None
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2, is_mobile=True)
    ctx.route("**/googletagmanager.com/**", lambda r: r.abort())
    ctx.route("**/g/collect**", lambda r: r.abort())
    for page in ("premium.html", "index.html", "diagnose.html"):
        pg = ctx.new_page()
        pg.goto(f"{base}/{page}", wait_until="domcontentloaded")
        pg.wait_for_timeout(1200)
        w = pg.evaluate("document.documentElement.scrollWidth")
        ok = w <= 375
        bad += not ok
        print(("OK  " if ok else "NG  ") + f"{page} 横幅 {w}px（画面375px）")
        if shot:
            os.makedirs(shot, exist_ok=True)
            pg.screenshot(path=os.path.join(shot, page.replace(".html", "_375.png")), full_page=True)
        pg.close()
    b.close()
sys.exit(1 if bad else 0)
