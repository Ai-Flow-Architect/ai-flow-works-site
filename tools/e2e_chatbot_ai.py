# 問5②（2026-11-23）黒ページのAI相談ボットが質問をAIへ渡すか（AIの窓口 Worker は横取り＝本物のAIは呼ばない）
#  ① 普通の可否の質問（「Excelと連携できますか？」）がAIへ届く・FAQの答えが参考として添えられる
#  ② AIの答えに言い切り（「対応可能です」）があれば、確約でない旨の1行がコードで足される
#  ③ お金・契約・期日の約束（返金等）はAIへ渡さず、今までどおり定型の案内
#  ④ AIが落ちた時はFAQの答えで受け止める
# 使い方: python3 tools/e2e_chatbot_ai.py http://127.0.0.1:8765
import json
import sys
from playwright.sync_api import sync_playwright

base = sys.argv[1]
fails = []


def check(cond, label):
    print(("OK  " if cond else "NG  ") + label)
    if not cond:
        fails.append(label)


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context()
    calls = []
    mode = {"fail": False, "reply": "はい、Excelとの連携は対応可能です。詳しくはお問い合わせフォーム（無料）へ。"}

    def fake_worker(route):
        calls.append(json.loads(route.request.post_data or "{}"))
        if mode["fail"]:
            route.fulfill(status=500, body="x")
        else:
            route.fulfill(status=200, content_type="application/json",
                          body=json.dumps({"choices": [{"message": {"content": mode["reply"]}}]}))

    ctx.route("**/ai-flow-openai-proxy.*/**", fake_worker)
    ctx.route("**/googletagmanager.com/**", lambda r: r.abort())
    ctx.route("**/g/collect**", lambda r: r.abort())
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/premium.html", wait_until="domcontentloaded")
    pg.click("#chat-btn")
    pg.wait_for_timeout(1500)
    pg.locator("#cp-opts button", has_text="自由に質問する").first.click()
    pg.wait_for_timeout(500)

    def ask(text, wait=2500):
        if not pg.is_visible("#cp-inp"):   # 答えた後は選択肢へ戻る＝もう一度「自由に質問する」を押す
            pg.locator("#cp-opts button", has_text="自由に").first.click()
            pg.wait_for_timeout(400)
        n = pg.locator("#cp-msgs > *").count()
        pg.fill("#cp-inp", text)
        pg.press("#cp-inp", "Enter")
        pg.wait_for_timeout(wait)
        return " ".join(pg.locator("#cp-msgs > *").all_inner_texts()[n:])

    out = ask("Excelと連携できますか？")
    check(len(calls) == 1, f"① 可否の質問がAIへ届く（呼び出し {len(calls)} 回）")
    msgs = calls[0]["messages"] if calls else []
    check(any(m["role"] == "user" and "Excelと連携できますか" in m["content"] for m in msgs), "① 質問の文がそのまま渡る")
    check(any(m["role"] == "system" and "よくある質問の答え" in m["content"] and "¥100,000" in m["content"] for m in msgs),
          "① FAQの答え（料金を含む）が参考として添えられる")
    check("対応可能です" in out and "確実にできるかはご状況を伺ったうえで" in out, "② 言い切りには確約でない旨の1行が付く")

    mode["reply"] = "はい、スプレッドシートとの連携もできます"   # 句点なしの言い切り（2026-11-23 検査役の指摘）
    out = ask("スプレッドシートも使えますか？")
    check(len(calls) == 2 and "確実にできるかはご状況を伺ったうえで" in out, "② 句点なしの言い切りにも1行が付く")

    mode["reply"] = "業務の流れを伺えれば、最適な方法をご提案いたします。"
    out = ask("どんな業務が向いていますか？")
    check(len(calls) == 3 and "確実にできるか" not in out, "② 言い切りの無い答えには何も足さない")

    out = ask("返金はできますか？")
    check(len(calls) == 3, "③ 返金の質問はAIへ渡さない")
    check("伺ったうえで" in out or "返金" in out, "③ 定型の案内が出る")

    mode["fail"] = True
    out = ask("Excelの集計は？", wait=3500)
    check(len(calls) == 4, "④ AIへは渡そうとする")
    check("スプレッドシート" in out or "Excel" in out, "④ AIが落ちたらFAQの答えで受け止める")
    check(not errs, f"画面のエラーなし {errs[:2]}")
    b.close()

print("FAIL" if fails else "ALL PASS", len(fails))
sys.exit(1 if fails else 0)
