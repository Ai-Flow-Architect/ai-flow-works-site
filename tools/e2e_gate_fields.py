# 入口の関門（2026-11-23 取締役OK＝問2）の実ブラウザ検査（受け口は横取りして本番へ1件も送らない）
#  3つのフォーム（白・黒・診断）が本文に【年商】【従業員数】【初回の予算】の3行を書くか
#  その3行を取込み側（~/.claude/scripts/inbound_lead_ingest.py）が1文字も違わず読めるか＝サイトと取込みの「合わせ」
#  選ばないと送れないか／受け口の予算の列へは今までの4つの値（lite/standard/full/undecided）しか送らないか
# 使い方: python3 tools/e2e_gate_fields.py http://127.0.0.1:8765
import json
import re
import os
import sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.expanduser("~/.claude/scripts"))
import inbound_lead_ingest as ing  # noqa: E402

base = sys.argv[1]
fails = []
GAS_VALUES = {"lite", "standard", "full", "undecided", ""}


def check(cond, label):
    print(("OK  " if cond else "NG  ") + label)
    if not cond:
        fails.append(label)


def gate_of(body):
    return ing.parse_gate(json.loads(body)["message"])


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    bodies = []

    def fake_gas(route):
        bodies.append(route.request.post_data or "")
        route.fulfill(status=200, content_type="application/json", body='{"status":"ok"}')

    ctx.route("**/macros/**", fake_gas)
    ctx.route("**/googletagmanager.com/**", lambda r: r.abort())
    ctx.route("**/g/collect**", lambda r: r.abort())
    ctx.route(re.compile(r".*\.(mp4|webm)(\?.*)?$"), lambda r: r.abort())   # 動画が接続を握ると次の画面が開かない（同一ホスト6本の上限）
    pg = ctx.new_page()

    # 選択肢の文字が取込み側と同じか（ページの <option value> を全部読む）
    for page, sel in (("/index.html", "#form"), ("/premium.html", "#contact-form"), ("/diagnose.html", "#lead-form")):
        pg.goto(base + page, wait_until="domcontentloaded")
        for nm, key in (("revenue", "年商"), ("staff", "従業員数")):
            vals = pg.eval_on_selector_all(f"{sel} [name={nm}] option", "os=>os.map(o=>o.value).filter(Boolean)")
            check(tuple(vals) == ing.GATE_FIELDS[key], f"{page} {key}の選択肢＝取込みと同じ {vals}")
    pg.goto(base + "/index.html", wait_until="domcontentloaded")
    vals = pg.eval_on_selector_all("#form [name=firstBudget] option", "os=>os.map(o=>o.value).filter(Boolean)")
    check(tuple(vals) == ing.GATE_FIELDS["初回の予算"], f"白 初回の予算の選択肢＝取込みと同じ {vals}")
    pg.goto(base + "/premium.html", wait_until="domcontentloaded")
    vals = pg.eval_on_selector_all("#contact-form [name=budget] option", "os=>os.map(o=>o.value).filter(Boolean)")
    check(tuple(vals) == ing.GATE_FIELDS["初回の予算"], f"黒 初回の予算の選択肢＝取込みと同じ {vals}")

    # ── 白：選ばないと送れない → 選ぶと3行 ──
    pg.goto(base + "/index.html", wait_until="domcontentloaded")
    pg.fill("#form [name=name]", "【テスト】甲野")
    pg.fill("#form [name=email]", "test@example.invalid")
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(600)
    check(len(bodies) == 0 and pg.is_visible("#inv"), "白：3択が空のままでは送れない（案内が出る）")
    pg.select_option("#form [name=revenue]", "1〜10億")
    pg.select_option("#form [name=staff]", "6〜50人")
    pg.select_option("#form [name=firstBudget]", "10万未満")
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(1200)
    check(len(bodies) == 1, "白：3択を選ぶと送れる")
    g = gate_of(bodies[-1]) if bodies else {}
    check(g == {"年商": "1〜10億", "従業員数": "6〜50人", "初回の予算": "10万未満"}, f"白：取込みが3行を読める {g}")
    check(ing.target_mark(g) == ("○", True), "白：1〜10億×6〜50人＝○（予算10万未満でも○）")
    check(json.loads(bodies[-1])["budget"] == "" if bodies else False, "白：予算の列は今までどおり空")

    # ── 黒：外れの組み合わせ＝× ──
    pg.goto(base + "/premium.html", wait_until="domcontentloaded")
    f = "#contact-form"
    pg.select_option(f + " [name=bizType]", index=1)
    pg.fill(f + " [name=name]", "【テスト】乙野")
    pg.fill(f + " [name=email]", "test@example.invalid")
    pg.fill(f + " [name=message]", "テスト")
    pg.click("#iform-submit-btn")
    pg.wait_for_timeout(600)
    check(len(bodies) == 1, "黒：3択が空のままでは送れない（ブラウザの必須）")
    pg.select_option(f + " [name=revenue]", "10億超")
    pg.select_option(f + " [name=staff]", "6〜50人")
    pg.select_option(f + " [name=budget]", "30万超")
    pg.click("#iform-submit-btn")
    pg.wait_for_timeout(1200)
    check(len(bodies) == 2, "黒：3択を選ぶと送れる")
    g = gate_of(bodies[-1]) if len(bodies) == 2 else {}
    check(g == {"年商": "10億超", "従業員数": "6〜50人", "初回の予算": "30万超"}, f"黒：取込みが3行を読める {g}")
    check(ing.target_mark(g) == ("×", True), "黒：10億超＝×（人数が狙いでも外れ）")
    sent = json.loads(bodies[-1]) if len(bodies) == 2 else {}
    check(sent.get("budget") == "full" and sent.get("budget") in GAS_VALUES, "黒：受け口の予算の列は今までの値（30万超→full）")
    check("【お客様の区分】法人" in sent.get("message", ""), "黒：お客様の区分の行は残る")

    # ── 診断：予算は質問で、年商・人数はフォームで ──
    pg.close()
    pg = ctx.new_page()   # 黒ページの後は新しいタブで開く（同じタブで移ると開かないことがある＝試験の道具側の詰まり）
    pg.goto(base + "/diagnose.html", wait_until="domcontentloaded")
    pg.wait_for_selector(".btn-start")
    pg.click(".btn-start")
    for _ in range(30):
        if pg.is_visible("#screen-result"):
            break
        title = pg.inner_text("#screen-q") if pg.is_visible("#screen-q") else ""
        if "初回の予算" in title:
            labels = pg.locator("#screen-q .opt").all_inner_texts()
            check(len(labels) == 3, f"診断：予算の質問は3択 {len(labels)}")
            pg.locator("#screen-q .opt").nth(1).click()   # 10万〜30万円
        else:
            pg.locator("#screen-q .opt").first.click()
        pg.click("#btn-next")
    check(pg.is_visible("#screen-result"), "診断：結果画面まで進む")
    pg.select_option("#lf-biz", index=1)
    pg.fill("#lf-name", "【テスト】丙野")
    pg.fill("#lf-email", "test@example.invalid")
    pg.click("#lf-submit")
    pg.wait_for_timeout(600)
    check(len(bodies) == 2 and "年商" in pg.inner_text("#lf-err"), "診断：年商が空なら送れない（案内が出る）")
    pg.select_option("#lf-rev", "1〜10億")
    pg.click("#lf-submit")
    pg.wait_for_timeout(600)
    check(len(bodies) == 2 and "従業員数" in pg.inner_text("#lf-err"), "診断：従業員数が空なら送れない")
    pg.select_option("#lf-staff", "〜5人")
    pg.click("#lf-submit")
    pg.wait_for_timeout(1200)
    check(len(bodies) == 3, "診断：選ぶと送れる")
    g = gate_of(bodies[-1]) if len(bodies) == 3 else {}
    check(g == {"年商": "1〜10億", "従業員数": "〜5人", "初回の予算": "10〜30万"}, f"診断：取込みが3行を読める {g}")
    check(ing.target_mark(g) == ("×", True), "診断：〜5人＝×")
    sent = json.loads(bodies[-1]) if len(bodies) == 3 else {}
    check(sent.get("budget") == "standard", "診断：受け口の予算の列は今までの値（10〜30万→standard）")
    check("【AI診断リード】" in sent.get("message", ""), "診断：診断結果の本文は残る")

    # 送った本文をまるごと取込みへ通す（広告の行として）＝下見で🟡が出ない
    rows = []
    for i, raw in enumerate(bodies):
        d = json.loads(raw)
        msg = d["message"].rsplit("\n流入：", 1)[0] + "\n流入：広告・google | 入口：/ | id：G-E2E | id種類：gclid | 送信：x"
        rows.append([f"2026-12-01 10:0{i}:00", "お問い合わせ", "己野", "", f"g{i}@kino.invalid.jp", "", msg])
    marks = [ing.ad_info(ing.pad(r))["target"] for r in rows]
    check(marks == ["○", "×", "×"], f"取込み：3件の狙い＝○×× {marks}")
    b.close()

print("FAIL" if fails else "ALL PASS", len(fails))
sys.exit(1 if fails else 0)
