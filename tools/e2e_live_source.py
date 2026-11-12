# 本番の白フォームから【テスト】1件を送り、受け口の応答と流入行を確かめる（集客の庭② 公開確認）
# 使い方: python3 tools/e2e_live_source.py <自分のメール>
import sys
from playwright.sync_api import sync_playwright

to = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    sent = []
    pg.on("request", lambda r: sent.append(r.post_data or "") if "script.google.com/macros" in r.url and r.method == "POST" else None)
    pg.goto("https://ai-flow-works.com/?utm_source=e2etest&utm_medium=check&utm_campaign=garden2", wait_until="load")
    pg.fill("#form [name=name]", "【テスト】集客の庭② 公開確認 11/12")
    pg.fill("#form [name=company]", "テスト（削除してよい）")
    pg.fill("#form [name=email]", to)
    pg.fill("#form [name=message]", "流入元つき登録の公開確認。返信不要です。")
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(15000)
    print("成功表示", pg.is_visible("#ok"), "失敗表示", pg.is_visible("#ng"))
    print("送った本文の流入行:", [ln for ln in (sent[-1] if sent else "").split("\\n") if "流入" in ln])
    b.close()
