# スマホ幅（375px）で12px未満の文字を数える（問5①・黒ページ）。
#  数え方＝文字を直接持つ要素のうち、画面に出ている（幅・高さ>0・非表示でない）物の計算後の文字サイズ<12px。
#  使い方: python3 tools/small_text_scan.py http://127.0.0.1:8765/premium.html [--max 0]
#  --max N を付けると N か所を超えた時に exit 1（公開前の検査に使う）
import sys
from collections import Counter
from playwright.sync_api import sync_playwright

url = sys.argv[1]
limit = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else None

JS = """() => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (['SCRIPT','STYLE','NOSCRIPT','SVG','PATH','TEXT'].includes(el.tagName.toUpperCase())) continue;
    if (el.closest('svg')) continue;
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (!own) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const px = parseFloat(cs.fontSize);
    if (px < 12) out.push({px, tag: el.tagName.toLowerCase(), cls: (el.className && el.className.baseVal === undefined ? el.className : '').toString().split(' ')[0], text: own.slice(0, 24)});
  }
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2, is_mobile=True)
    ctx.route("**/googletagmanager.com/**", lambda r: r.abort())
    ctx.route("**/g/collect**", lambda r: r.abort())
    pg = ctx.new_page()
    pg.goto(url, wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)
    rows = pg.evaluate(JS)
    b.close()

print(f"12px未満の文字: {len(rows)}か所（375px）")
for (px, key), n in Counter((r["px"], r["tag"] + "." + r["cls"]) for r in rows).most_common(40):
    ex = next(r["text"] for r in rows if r["px"] == px and r["tag"] + "." + r["cls"] == key)
    print(f"  {px:5.2f}px ×{n:3d}  {key:32s} 例「{ex}」")
if limit is not None and len(rows) > limit:
    sys.exit(1)
