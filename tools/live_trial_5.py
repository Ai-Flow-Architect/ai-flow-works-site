# 問4の本番試し送信5回（2026-11-23・取締役OK）。全部お名前に【テスト】。
# 組み合わせ＝診断1（広告の目印つきURL）＋黒3（○1〜10億×6〜50人／×10億超／×1億未満〜5人・予算は3つを1回ずつ）＋白1
# 使い方: python3 tools/live_trial_5.py <受け取るメール> [開始番号 1〜5] [送信の間隔（秒）・既定200]
# 🔴 受け口（GAS）は同じ宛先の短い間隔（12秒おき）の送信を、200を返しても記録しない（11/23 実測）＝間隔は既定で200秒あける
import sys
from playwright.sync_api import sync_playwright

TO = sys.argv[1]
START = int(sys.argv[2]) if len(sys.argv) > 2 else 1
BASE = "https://ai-flow-works.com"
AD = "?gclid=TEST-q4-20261123&utm_source=google&utm_medium=cpc&utm_campaign=q4test"


def open_page(b, path):
    ctx = b.new_context()
    pg = ctx.new_page()
    sent = []
    pg.on("request", lambda r: sent.append(r.post_data or "") if "script.google.com/macros" in r.url and r.method == "POST" else None)
    pg.on("response", lambda r: print("   受け口の返事", r.status, r.url[:60], flush=True) if "script.google" in r.url or "googleusercontent" in r.url else None)
    # フォームに関係ない外部（グラフ・フォント・計測）は止める＝ミニPCのChromiumで読み込みが終わらず時間切れになったため（11/23 実測）
    pg.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in ("cdn.jsdelivr.net", "fonts.g", "googletagmanager")) else r.continue_())
    pg.goto(BASE + path, wait_until="commit", timeout=60000)
    pg.wait_for_load_state("domcontentloaded", timeout=90000)
    return ctx, pg, sent


def report(label, sent):
    body = (sent[-1] if sent else "").replace("\\n", "\n")
    keep = [l for l in body.split("\n") if any(k in l for k in ("流入", "年商", "従業員", "予算"))]
    print(label, "送信", len(sent), "|", " / ".join(keep)[:300], flush=True)


def diagnose(b):
    ctx, pg, sent = open_page(b, "/diagnose.html" + AD)
    pg.click(".btn-start")
    for _ in range(30):
        if pg.is_visible("#screen-result"):
            break
        title = pg.inner_text("#screen-q") if pg.is_visible("#screen-q") else ""
        pg.locator("#screen-q .opt").nth(1 if "初回の予算" in title else 0).click()
        pg.click("#btn-next")
    pg.select_option("#lf-biz", index=1)
    pg.fill("#lf-name", "【テスト】問4 試し送信1 診断（広告）")
    pg.fill("#lf-email", TO)
    pg.select_option("#lf-rev", "1〜10億")
    pg.select_option("#lf-staff", "6〜50人")
    pg.click("#lf-submit")
    pg.wait_for_timeout(25000)
    report("1 診断・広告", sent)
    ctx.close()


def premium(b, i, rev, staff, bidx):
    ctx, pg, sent = open_page(b, "/premium.html")
    f = "#contact-form"
    pg.select_option(f + " [name=bizType]", index=1)
    pg.fill(f + " [name=name]", f"【テスト】問4 試し送信{i} 黒")
    pg.fill(f + " [name=email]", TO)
    pg.fill(f + " [name=message]", "問4の本番試し送信です。返信不要です。")
    pg.select_option(f + " [name=revenue]", rev)
    pg.select_option(f + " [name=staff]", staff)
    opts = pg.eval_on_selector_all(f + " [name=budget] option", "os=>os.map(o=>o.value).filter(Boolean)")
    if not opts:
        raise SystemExit("黒の予算の選択肢が0件＝フォームが変わった。送らずに止める")
    pg.select_option(f + " [name=budget]", opts[bidx % len(opts)])
    pg.click("#iform-submit-btn")
    pg.wait_for_timeout(25000)
    report(f"{i} 黒 {rev}×{staff}", sent)
    ctx.close()


def white(b):
    ctx, pg, sent = open_page(b, "/index.html")
    pg.fill("#form [name=name]", "【テスト】問4 試し送信5 白")
    pg.fill("#form [name=email]", TO)
    pg.fill("#form [name=message]", "問4の本番試し送信です。返信不要です。")
    pg.select_option("#form [name=revenue]", "1〜10億")
    pg.select_option("#form [name=staff]", "6〜50人")
    fb = pg.eval_on_selector_all("#form [name=firstBudget] option", "os=>os.map(o=>o.value).filter(Boolean)")
    pg.select_option("#form [name=firstBudget]", fb[0])
    pg.click("#form button[type=submit]")
    pg.wait_for_timeout(25000)
    report("5 白", sent)
    ctx.close()


with sync_playwright() as p:
    b = p.chromium.launch()
    combos = {2: ("1〜10億", "6〜50人", 0), 3: ("10億超", "6〜50人", 1), 4: ("1億未満", "〜5人", 2)}
    GAP = int(sys.argv[3]) if len(sys.argv) > 3 else 200   # 送信の間隔（秒）。0にすると受け口が記録しない（11/23 実測）
    import time
    for n in range(START, 6):
        if n > START and GAP:
            time.sleep(GAP)
        if n == 1:
            diagnose(b)
        elif n in combos:
            premium(b, n, *combos[n])
        else:
            white(b)
    b.close()
