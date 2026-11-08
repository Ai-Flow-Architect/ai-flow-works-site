"""公開前の機械検査（何度でも実行可）。1つでも🔴があれば exit 1。
- 旧アドレス(github.io)の残り
- 旧表記(AI Flow Architect)の残り（客様の声の引用1か所は許可）
- 相対リンク・画像の参照先が実在するか
- 切替タブが両ページにあるか
- 鍵らしき文字列（OpenAI/Gemini/GitHub/Slack 等）が無いか
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
red = []
pages = [f for f in os.listdir(ROOT) if f.endswith(".html")]
KEY = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|xox[bp]-[A-Za-z0-9-]{20,})")
for f in pages:
    s = open(os.path.join(ROOT, f), encoding="utf-8").read()
    body = re.sub(r"data:[^\"')]{100,}", "", s)
    n_old = len(re.findall(r"ai-flow-architect\.github\.io", body))
    if n_old:
        red.append(f"{f}: 旧アドレスが {n_old} か所")
    n_brand = len(re.findall(r"AI Flow Architect", body)) - body.count("「AI Flow Architectに頼むと魔法みたいに終わる」")
    if n_brand:
        red.append(f"{f}: 旧表記が {n_brand} か所")
    if KEY.search(body):
        red.append(f"{f}: 鍵らしき文字列あり")
    for ref in re.findall(r'(?:src|href)\s*=\s*"([^"#?]+)', body):
        if ref.startswith(("http", "//", "mailto:", "tel:", "javascript:", "data:")):
            continue
        if "'" in ref or "+" in ref or "${" in ref:  # JS で組み立てる参照（旧サイトと同じ動き）は対象外
            continue
        p = ref[1:] if ref.startswith("/") else ref
        target = os.path.join(ROOT, p)
        if p in ("", "./") or p.endswith("/"):
            target = os.path.join(ROOT, p, "index.html")
        if not os.path.exists(target):
            red.append(f"{f}: 参照先が無い {ref}")
for f in ("index.html", "premium.html"):
    s = open(os.path.join(ROOT, f), encoding="utf-8").read()
    if 'class="afw-tabs"' not in s or 'aria-current="page"' not in s:
        red.append(f"{f}: 切替タブが無い")
# assets.json が参照する thumbs/videos の実在
import json
data = json.load(open(os.path.join(ROOT, "assets.json"), encoding="utf-8"))
items = data if isinstance(data, list) else data.get("items", data.get("assets", []))
miss = 0
for it in items:
    for k in ("thumb", "video", "image"):
        v = it.get(k) if isinstance(it, dict) else None
        if v and not v.startswith("http") and not os.path.exists(os.path.join(ROOT, v)) \
                and not os.path.exists(os.path.join(ROOT, "thumbs", v)) and not os.path.exists(os.path.join(ROOT, "videos", v)):
            miss += 1
print(f"pages={len(pages)} assets.json件数={len(items)} 参照切れ(assets.json)={miss}")
if miss:
    red.append(f"assets.json の参照切れ {miss} 件")
for r in red:
    print("🔴", r)
print("🔴0件" if not red else f"🔴{len(red)}件")
sys.exit(1 if red else 0)
