# 黒ページの途中で切れた initBeam の写し（構文エラーで一度も実行されていない）を取り除く。
# 直後の完全な写しの先頭と一致する時だけ消す（一致しなければ何もしない）。
import pathlib, re

p = pathlib.Path(__file__).resolve().parent.parent / "premium.html"
s = p.read_text(encoding="utf-8")
blocks = [m for m in re.finditer(r"<script>\n\(function\(\)\{\n  function initBeam\(\)\{.*?</script>\n", s, re.S)]
print("initBeam scripts:", len(blocks))
if len(blocks) >= 2:
    a, b = blocks[0], blocks[1]
    body_a = a.group(0)[: -len("</script>\n")]
    body_b = b.group(0)
    if body_b.startswith(body_a.rstrip()):
        s2 = s[: a.start()] + s[a.end():].lstrip("\n")
        p.write_text(s2, encoding="utf-8")
        print("removed truncated copy, chars", len(a.group(0)))
    else:
        print("not a prefix -> untouched")
