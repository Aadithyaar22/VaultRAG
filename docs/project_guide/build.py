"""Builds docs/PROJECT_GUIDE.pdf from the HTML parts + SVG diagrams (needs Google Chrome for printing)."""
import pathlib, subprocess, sys
here = pathlib.Path(__file__).parent
svg = lambda n: (here / "svg" / f"{n}.svg").read_text()
body = "\n".join((here / p).read_text() for p in ("p0_cover.html", "p1_plain.html", "p2_build.html", "p3_run.html", "p4_proof.html", "p5_ref.html"))
for key, name in (("{{FLOW}}", "flow"), ("{{ARCH}}", "arch"), ("{{DATA}}", "data"), ("{{INGEST}}", "ingest"), ("{{RSEG}}", "rseg")):
    body = body.replace(key, svg(name))
import re
def fix_tables(m):
    t = m.group(0)
    rows = re.findall(r"<tr.*?</tr>", t, flags=re.S)
    if rows and "<th" in rows[0]:
        t = t.replace(rows[0], "<thead>" + rows[0] + "</thead>", 1)
    if len(rows) <= 8:                     # short tables stay on one page; long ones split but repeat the header
        t = t.replace("<table", '<table style="break-inside:avoid"', 1) if "break-inside" not in t[:80] else t
    return t
body = re.sub(r"<table.*?</table>", fix_tables, body, flags=re.S)
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>VaultRAG — Project Guide</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,500;1,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
<style>{(here / "style.css").read_text()}</style></head><body>{body}</body></html>"""
out = here / "guide.html"; out.write_text(html)
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
pdf = here.parent / "PROJECT_GUIDE.pdf"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                f"--print-to-pdf={pdf}", f"file://{out}"], check=True, stderr=subprocess.DEVNULL)
print("wrote", pdf, pdf.stat().st_size // 1024, "KB")
