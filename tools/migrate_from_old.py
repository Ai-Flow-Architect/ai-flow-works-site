"""旧サイト（ai-flow-architect.github.io = ~/projects/new-project）から
新サイト（ai-flow-works.com）を1回だけ組み立てる移行スクリプト。

白（見本カタログ）= index.html（入口・通常）
黒（旧トップ）     = premium.html（プレミアム・高価格帯）
両方の最上部に「通常 / プレミアム」の切替タブを入れ、表記を AI Flow Works にそろえる。

実行: python3 tools/migrate_from_old.py   （何度実行しても同じ結果になる）
"""
import os
import re
import shutil
import sys

SRC = os.path.expanduser("~/projects/new-project")
DST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = "https://ai-flow-architect.github.io"
NEW = "https://ai-flow-works.com"
BRAND_OLD = "AI Flow Architect"
BRAND_NEW = "AI Flow Works"

# 客様の声（引用）の中の表記は書き換えない＝引用を改変しない
KEEP_QUOTE = "「AI Flow Architectに頼むと魔法みたいに終わる」"

COPY_FILES = ["diagnose.html", "diagnose-engine.js", "roi-calculator.html",
              "business.html", "privacy.html", "og.png"]
COPY_DIRS = [("assets", "assets"), ("catalog/thumbs", "thumbs"), ("catalog/videos", "videos")]


def tabs(active, dark):
    """通常 / プレミアム の切替タブ（ページ最上部・高さ44px）"""
    if dark:
        bg, fg, on_bg, on_fg, line = "#0c0c0c", "#9a9a9a", "#f5f5f5", "#0c0c0c", "#262626"
    else:
        bg, fg, on_bg, on_fg, line = "#f7f7f5", "#4d4d4d", "#191919", "#ffffff", "#e6e6e3"
    # 黒ページは元のメニューが画面上端に固定（top:0・高さ60px）＝タブも固定にしてメニューを44px下げる
    extra = (".afw-tabs{position:fixed;top:0;left:0;right:0;height:44px;align-items:center}"
             "body>nav{top:44px!important}body{padding-top:44px}") if dark else ""
    a_std = ' aria-current="page"' if active == "std" else ""
    a_pre = ' aria-current="page"' if active == "pre" else ""
    return f'''<div class="afw-tabs" role="navigation" aria-label="プランの切替">
<style>
.afw-tabs{{background:{bg};border-bottom:1px solid {line};display:flex;justify-content:center;padding:6px 16px;position:relative;z-index:1000}}
.afw-tabs a{{font:700 13px/1 'Noto Sans JP',-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;color:{fg};text-decoration:none;padding:9px 18px;border-radius:999px;letter-spacing:.04em}}
.afw-tabs a[aria-current="page"]{{background:{on_bg};color:{on_fg}}}
.afw-tabs a:focus-visible{{outline:3px solid #9cc6f5;outline-offset:2px}}
{extra}
</style>
<a href="./"{a_std}>通常プラン</a><a href="premium.html"{a_pre}>プレミアム</a>
</div>
'''


def rebrand(s):
    s = s.replace(KEEP_QUOTE, "\x00KEEP\x00")
    s = s.replace(BRAND_OLD, BRAND_NEW)
    s = s.replace("AI Flow<span> Architect</span>", "AI Flow<span> Works</span>")
    s = s.replace("なぜ「AIフローアーキテクト」が選ばれるのか？", "なぜ「AI Flow Works」が選ばれるのか？")
    return s.replace("\x00KEEP\x00", KEEP_QUOTE)


def insert_after_body(s, html):
    m = re.search(r"<body[^>]*>", s)
    if not m:
        sys.exit("body タグが見つからない")
    return s[:m.end()] + "\n" + html + s[m.end():]


def build_white():
    s = open(os.path.join(SRC, "catalog", "index.html"), encoding="utf-8").read()
    s = s.replace(f"{OLD}/catalog/", f"{NEW}/")
    s = s.replace(f"{OLD}/og.png", f"{NEW}/og.png")
    s = s.replace('href="../#contact"', 'href="premium.html#contact"')
    s = s.replace('href="../privacy.html"', 'href="privacy.html"')
    s = s.replace('href="../"', 'href="./"')
    s = rebrand(s)
    s = s.replace("<title>できることカタログ — AI Flow Works</title>",
                  "<title>AI Flow Works — できることカタログ</title>")
    return insert_after_body(s, tabs("std", dark=False))


def build_black():
    s = open(os.path.join(SRC, "index" + ".html"), encoding="utf-8").read()
    s = s.replace(f'<link rel="canonical" href="{OLD}/">',
                  f'<link rel="canonical" href="{NEW}/premium.html">')
    s = s.replace(f'<meta property="og:url" content="{OLD}/">',
                  f'<meta property="og:url" content="{NEW}/premium.html">')
    s = s.replace(OLD, NEW)
    s = rebrand(s)
    return insert_after_body(s, tabs("pre", dark=True))


def build_sub(name):
    s = open(os.path.join(SRC, name), encoding="utf-8").read()
    s = s.replace(OLD, NEW)
    s = rebrand(s)
    if name == "business.html":
        before = "<th>事業者名</th><td>AIフローアーキテクト（個人事業）</td>"
        if before not in s:
            sys.exit("business.html の事業者名の行が見つからない")
        s = s.replace(before, "<th>事業者名</th><td>AI Flow Works（屋号：AIフローアーキテクト・個人事業）</td>")
    return s


def icon_link():
    """黒ページ（旧トップ）のファビコン行を取り出して全ページで使う"""
    s = open(os.path.join(SRC, "index" + ".html"), encoding="utf-8").read()
    m = re.search(r'<link rel="icon"[^>]*>', s)
    if not m:
        sys.exit("旧トップにファビコンが見つからない")
    return m.group(0)


def ensure_icon(s, link):
    if 'rel="icon"' in s:
        return s
    return s.replace("</head>", link + "\n</head>", 1)


PAGE_404 = """<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light only"><meta name="robots" content="noindex">
<title>ページが見つかりません — AI Flow Works</title>
<style>body{margin:0;font-family:'Noto Sans JP',-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;background:#fff;color:#191919;display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center;padding:0 16px}
h1{font-size:28px;margin:0 0 12px}p{color:#4d4d4d;margin:0 0 28px}
a{display:inline-block;background:#2383e2;color:#fff;text-decoration:none;font-weight:700;padding:14px 26px;border-radius:999px;margin:4px}
a.s{background:#e3efff;color:#1a6fc4}</style>
</head><body><main><h1>ページが見つかりません</h1>
<p>URLが変わったか、ページが移動した可能性があります。</p>
<a href="/">トップへ戻る</a><a class="s" href="/premium.html">プレミアム</a></main></body></html>
"""


def main():
    os.makedirs(DST, exist_ok=True)
    link = icon_link()
    w = lambda n, t: open(os.path.join(DST, n), "w", encoding="utf-8").write(ensure_icon(t, link) if n.endswith(".html") else t)
    w("index.html", build_white())
    w("premium.html", build_black())
    w("404.html", PAGE_404)
    for n in COPY_FILES:
        if n.endswith(".html"):
            w(n, build_sub(n))
        else:
            shutil.copy2(os.path.join(SRC, n), os.path.join(DST, n))
    shutil.copy2(os.path.join(SRC, "catalog", "assets.json"), os.path.join(DST, "assets.json"))
    for src, dst in COPY_DIRS:
        d = os.path.join(DST, dst)
        if os.path.isdir(d):
            shutil.rmtree(d)
        shutil.copytree(os.path.join(SRC, src), d)
    w("CNAME", "ai-flow-works.com\n")
    w(".nojekyll", "")
    w("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {NEW}/sitemap.xml\n")
    pages = ["", "premium.html", "diagnose.html", "roi-calculator.html", "business.html", "privacy.html"]
    urls = "".join(f"  <url><loc>{NEW}/{p}</loc></url>\n" for p in pages)
    w("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    print("built:", DST)


if __name__ == "__main__":
    main()
