# HTML内のインラインscriptを1本ずつ node --check にかけ、構文エラーの位置を出す
import re, subprocess, sys, tempfile, pathlib

html = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
for m in re.finditer(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", html, re.S):
    attrs, code = m.group(1), m.group(2)
    if "json" in attrs or "module" in attrs:
        continue
    line = html.count("\n", 0, m.start()) + 1
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(code)
    r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
    if r.returncode:
        print("NG script starting at html line", line, "length", len(code))
        print(r.stderr[:600])
