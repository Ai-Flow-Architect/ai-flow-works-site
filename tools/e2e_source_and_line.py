# 集客の庭②④の実ブラウザ検査（受け口は横取りして本番へ1件も送らない）
#  ② 3つのフォームの本文末尾に「流入：…」1行が付くか／最初の入口を2回目の訪問で上書きしないか
#  ④ 診断結果の「LINEで受け取る」が公式LINE(@087nomob)の下書きURLになり、要約が入っているか
# 使い方: python3 tools/e2e_source_and_line.py http://127.0.0.1:8765
import sys
import urllib.parse
from playwright.sync_api import sync_playwright

base = sys.argv[1]
GAS = "script.google.com/macros"
fails = []


def check(cond, label):
    print(("OK  " if cond else "NG  ") + label)
    if not cond:
        fails.append(label)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    bodies = []

    def fake_gas(route):
        bodies.append(route.request.post_data or "")
        route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')

    ctx.route("**/" + "macros/**", fake_gas)
    ctx.route("**/googletagmanager.com/**", lambda r: r.abort())
    pg = ctx.new_page()

    # 1回目の訪問＝検索から来た（utm つき）
    pg.goto(base + "/diagnose.html?utm_source=google&utm_medium=cpc&utm_campaign=t1", wait_until="load")
    pg.click(".btn-start")
    for _ in range(30):
        if pg.is_visible("#screen-result"):
            break
        opt = pg.locator("#screen-q .opt").first
        opt.click()
        pg.click("#btn-next")
    check(pg.is_visible("#screen-result"), "診断が結果画面まで進む")

    href = pg.get_attribute("#res-line", "href") or ""
    check(href.startswith("https://line.me/R/oaMessage/%40087nomob/?"), "LINEボタンが公式LINEの下書きURL")
    text = urllib.parse.unquote(href.split("/?", 1)[-1])
    check("【診断結果を受け取りたい】" in text and "判定：Lv" in text and "年間削減の目安：" in text, "下書きに判定と削減額の要約")
    check("流入：広告・google" in text and "utm：google/cpc/t1" in text, "下書きに流入元の1行")
    check(len(href) < 2000, f"URLの長さ {len(href)} < 2000")

    pg.select_option("#lf-biz", index=1)
    pg.fill("#lf-name", "【テスト】甲野")
    pg.fill("#lf-email", "test@example.invalid")
    pg.click("#lf-submit")
    pg.wait_for_timeout(1500)
    check(len(bodies) == 1 and "流入：広告・google" in bodies[-1] and "送信：diagnose" in bodies[-1], "診断フォームの本文に流入の1行")
    check(pg.is_visible("#lead-success"), "診断フォームが成功表示")

    # 2回目の訪問＝直接（参照元なし）→ 最初の入口（google）のまま
    pg.goto(base + "/index.html", wait_until="load")
    pg.fill("#form [name=name]", "【テスト】乙野")
    pg.fill("#form [name=email]", "test@example.invalid")
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(1500)
    check(len(bodies) == 2 and "流入：広告・google" in bodies[-1] and "入口：/diagnose.html" in bodies[-1], "白フォームは最初の入口を保つ")

    # 黒ページのフォーム
    pg.goto(base + "/premium.html", wait_until="load")
    f = "#contact-form"
    pg.fill(f + " [name=name]", "【テスト】丙野")
    pg.fill(f + " [name=email]", "test@example.invalid")
    pg.fill(f + " [name=message]", "テスト")
    bt = pg.locator(f + " [name=bizType]")
    if bt.count():
        bt.select_option(index=1)
    pg.click("#iform-submit-btn")
    pg.wait_for_timeout(1500)
    check(len(bodies) == 3 and "送信：premium_contact" in bodies[-1], "黒フォームの本文に流入の1行")

    # 保存が使えない環境でも壊れない（新しい文脈・localStorage を投げる）
    ctx2 = b.new_context()
    ctx2.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('blocked')}})")
    pg2 = ctx2.new_page()
    errs = []
    pg2.on("pageerror", lambda e: errs.append(str(e)))
    pg2.goto(base + "/index.html", wait_until="load")
    v = pg2.evaluate("window.AFW_SRC ? AFW_SRC('x') : ''")
    check(v.startswith("流入：直接") and not errs, "保存不可でも流入行が作れる（直接）")
    b.close()

print("FAIL" if fails else "ALL PASS", len(fails))
sys.exit(1 if fails else 0)
