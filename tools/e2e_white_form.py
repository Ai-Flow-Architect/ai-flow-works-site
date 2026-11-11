# 白ページの事前登録フォームを実ブラウザで送り、受け口の応答で成功表示が出るかを見る（テストと明示した1件）
import sys
from playwright.sync_api import sync_playwright

base = sys.argv[1]
to = sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    events = []
    pg.on("request", lambda r: events.append(r.url) if "google-analytics.com/g/collect" in r.url and "generate_lead" in r.url else None)
    pg.goto(base + "/index.html", wait_until="load")
    pg.fill("#form [name=name]", "【テスト】白フォーム送信確認 11/11")
    pg.fill("#form [name=company]", "テスト（削除してよい）")
    pg.fill("#form [name=email]", to)
    pg.fill("#form [name=message]", "集客の庭① 送信経路の確認。返信不要です。")
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(12000)
    print("ok表示", pg.is_visible("#ok"), "ng表示", pg.is_visible("#ng"))
    print("generate_lead 送信", len(events))
    b.close()
