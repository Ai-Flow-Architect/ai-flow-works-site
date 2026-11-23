# 集客の庭②④の実ブラウザ検査（受け口は横取りして本番へ1件も送らない）
#  ② 3つのフォームの本文末尾に「流入：…」1行が付くか／最初の入口を2回目の訪問で上書きしないか
#  ④ 診断結果の「LINEで受け取る」が公式LINE(@087nomob)の下書きURLになり、要約が入っているか
#  広告の判定（設計書 §6-2 配線1）＝クリック番号・utm_medium・fbclid・id の行・直近広告
#  GA4（配線8）＝診断の「始めた」「最後まで行った」の2イベント
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


def events(page):
    """gtag('event', 名前, …) で積まれた診断のイベント名（タグ本体は止めているので dataLayer を読む）。"""
    return page.evaluate(
        "(window.dataLayer||[]).filter(a=>a[0]==='event'&&/^diagnose_/.test(a[1])).map(a=>a[1])"
    )


def kind_of(line):
    """取込み側 inbound_lead_ingest.parse_source と同じ読み方＝「流入：」の後の最初の | まで。"""
    return line.split("|", 1)[0].replace("流入：", "").strip()


def src_line(browser, query, referer=None):
    """新しい訪問者として index を開き、AFW_SRC の1行を返す。"""
    c = browser.new_context()
    c.route("**/googletagmanager.com/**", lambda r: r.abort())
    g = c.new_page()
    g.goto(base + "/index.html" + query, wait_until="domcontentloaded", referer=referer)
    v = g.evaluate("AFW_SRC('x')")
    c.close()
    return v


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
    check(events(pg) == [], "診断を始める前はイベントなし")
    pg.click(".btn-start")
    check(events(pg) == ["diagnose_start"], "GA4 diagnose_start が開始ボタンで1回")
    for _ in range(30):
        if pg.is_visible("#screen-result"):
            break
        opt = pg.locator("#screen-q .opt").first
        opt.click()
        pg.click("#btn-next")
    check(pg.is_visible("#screen-result"), "診断が結果画面まで進む")
    check(events(pg) == ["diagnose_start", "diagnose_complete"], "GA4 diagnose_complete が結果表示で1回")

    href = pg.get_attribute("#res-line", "href") or ""
    check(href.startswith("https://line.me/R/oaMessage/%40087nomob/?"), "LINEボタンが公式LINEの下書きURL")
    text = urllib.parse.unquote(href.split("/?", 1)[-1])
    check("【診断結果を受け取りたい】" in text and "判定：Lv" in text and "年間削減の目安：" in text, "下書きに判定と削減額の要約")
    check("流入：広告・google" in text and "utm：google/cpc/t1" in text, "下書きに流入元の1行")
    check(len(href) < 2000, f"URLの長さ {len(href)} < 2000")

    pg.select_option("#lf-biz", index=1)
    pg.select_option("#lf-rev", index=2)     # 入口の関門（2026-11-23）。中身の検査は e2e_gate_fields.py
    pg.select_option("#lf-staff", index=2)
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
    for nm in ("revenue", "staff", "firstBudget"):
        pg.select_option(f"#form [name={nm}]", index=2)
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
    for nm in ("revenue", "staff", "budget"):
        pg.select_option(f + f" [name={nm}]", index=2)
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

    # ── 広告の判定（配線1）──
    v = src_line(b, "?gclid=Abc-123_x")
    check(kind_of(v) == "広告・google", "gclid だけで「広告・google」")
    check(" | id：Abc-123_x | id種類：gclid | " in v, "id の行にクリック番号と種類")
    check(v.startswith("流入：") and v.endswith(" | 送信：x") and "直近広告：" not in v, "行の形（流入が先頭・送信が末尾・最初の入口が広告なら直近広告は重ねない）")
    check(kind_of(src_line(b, "?gbraid=GB1")) == "広告・google" and kind_of(src_line(b, "?wbraid=WB1")) == "広告・google", "gbraid・wbraid だけでも広告")
    check(kind_of(src_line(b, "?utm_source=yahoo&utm_medium=cpc")) == "広告・yahoo", "utm_medium=cpc で広告（媒体は utm_source）")
    check(kind_of(src_line(b, "?utm_medium=cpc")) == "広告・不明", "有料の印だけ（媒体も番号も無い）は「広告・不明」＝Google に混ぜない")
    v = src_line(b, "?fbclid=FB_9&utm_medium=paid")
    check(kind_of(v) == "広告・facebook" and "id種類：fbclid" in v, "fbclid＋utm_medium=paid（媒体なし）は「広告・facebook」")
    check(kind_of(src_line(b, "?gclid=G1&utm_medium=cpc")) == "広告・google", "gclid＋有料の印（媒体なし）は google")
    v = src_line(b, "?gclid=G1&utm_campaign=camp1")
    check(" | utm：camp1 | キャンペーン：camp1 | " in v, "キャンペーン名は utm の並びと別に個別の項目で載る")
    check(
        all(kind_of(src_line(b, "?utm_source=facebook&utm_medium=" + m)) == "広告・facebook" for m in ("ppc", "paid", "paid_social", "CPC")),
        "utm_medium=ppc/paid/paid_social も広告",
    )
    v = src_line(b, "?fbclid=FB_9")
    check(kind_of(v) == "直接" and "id：FB_9 | id種類：fbclid" in v, "fbclid だけは広告でない（番号は残る）")
    check(kind_of(src_line(b, "?utm_source=facebook&utm_medium=social&fbclid=FB_9")) == "SNS", "無料の投稿（fbclid つき）は SNS")
    check(kind_of(src_line(b, "", referer="https://www.google.com/")) == "検索", "参照元が google だけなら検索")
    v = src_line(b, "?gclid=G1&utm_source=google&utm_medium=cpc&utm_campaign=a%7Cb&utm_term=%E8%87%AA%E5%8B%95%E5%8C%96%0A%E5%A4%96%E6%B3%A8")
    check(len(v.split(" | ")) == 8 and "キャンペーン：a b" in v and "\n" not in v and "語：自動化 外注" in v, "値の中の | と改行は行を壊さない／検索語が載る")

    # 直近の広告＝最初の入口（直接）を守ったまま、後から来た広告を別に覚える
    ctx3 = b.new_context()
    ctx3.route("**/googletagmanager.com/**", lambda r: r.abort())
    ctx3.route("**/" + "macros/**", fake_gas)
    pg3 = ctx3.new_page()
    pg3.goto(base + "/index.html", wait_until="load")
    check("直近広告" not in pg3.evaluate("AFW_SRC('x')"), "広告で来ていなければ直近広告なし")
    pg3.goto(base + "/diagnose.html?gclid=G2&utm_source=google&utm_medium=cpc&utm_campaign=c2", wait_until="load")
    pg3.goto(base + "/index.html", wait_until="load")
    v = pg3.evaluate("AFW_SRC('x')")
    check(kind_of(v) == "直接" and " | 直近広告：広告・google gclid=G2 utm=google/cpc/c2 キャンペーン=c2 日=" in v and " | id：" not in v, "最初の入口は直接のまま、直近広告を別に覚える")
    pg3.goto(base + "/index.html?gclid=G3", wait_until="load")
    check("直近広告：広告・google gclid=G3 日=" in pg3.evaluate("AFW_SRC('x')"), "直近広告は新しい広告で上書き")
    old = "Date.now()-31*24*3600*1000"
    pg3.evaluate("(()=>{for(const k of ['afw_first_touch','afw_last_ad']){const v=JSON.parse(localStorage.getItem(k));v.t=%s;localStorage.setItem(k,JSON.stringify(v));}})()" % old)
    pg3.goto(base + "/index.html", wait_until="load")
    v = pg3.evaluate("AFW_SRC('x')")
    check(kind_of(v) == "直接" and "直近広告" not in v, "30日を過ぎた最初の入口と直近広告は使わない")

    # 設計書 §6-4 試験1＝広告のURLで診断→送信した本文に「広告・google」とクリック番号
    n0 = len(bodies)
    pg3.evaluate("localStorage.clear()")
    pg3.goto(base + "/diagnose.html?gclid=E2E_gclid-1&utm_term=kw", wait_until="load")
    pg3.evaluate("window.gtag = undefined")
    errs3 = []
    pg3.on("pageerror", lambda e: errs3.append(str(e)))
    pg3.click(".btn-start")
    for _ in range(30):
        if pg3.is_visible("#screen-result"):
            break
        pg3.locator("#screen-q .opt").first.click()
        pg3.click("#btn-next")
    check(pg3.is_visible("#screen-result") and not errs3 and events(pg3) == [], "gtag が無くても診断は最後まで進み、何も送らない")
    pg3.select_option("#lf-biz", index=1)
    pg3.select_option("#lf-rev", index=2)
    pg3.select_option("#lf-staff", index=2)
    pg3.fill("#lf-name", "【テスト】丁野")
    pg3.fill("#lf-email", "test@example.invalid")
    pg3.click("#lf-submit")
    pg3.wait_for_timeout(1500)
    sent = bodies[-1] if len(bodies) == n0 + 1 else ""
    check("流入：広告・google | 入口：/diagnose.html | 語：kw | id：E2E_gclid-1 | id種類：gclid | 送信：diagnose" in sent, "広告のURLから送信した本文に「広告・google」と id")
    b.close()

print("FAIL" if fails else "ALL PASS", len(fails))
sys.exit(1 if fails else 0)
