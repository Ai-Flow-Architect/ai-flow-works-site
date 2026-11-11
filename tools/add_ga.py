# 全ページに GA4 タグを入れる（既に入っているページは触らない・冪等）
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
GA_ID = "G-EDE4GD3W09"
SNIPPET = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
"""

for p in sorted(ROOT.glob("*.html")):
    s = p.read_text(encoding="utf-8")
    if GA_ID in s:
        print("skip", p.name)
        continue
    if s.count("</head>") != 1:
        print("NG head count", p.name)
        continue
    p.write_text(s.replace("</head>", SNIPPET + "</head>"), encoding="utf-8")
    print("added", p.name)
