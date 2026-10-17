"""Builds ../01_pitch_deck.pdf from deck_template.html + the guide's SVG diagrams (needs Google Chrome)."""
import pathlib, subprocess
here = pathlib.Path(__file__).parent; out = here.parent; svg = here.parent.parent / "docs" / "project_guide" / "svg"
t = (here / "deck_template.html").read_text()
for k, n in (("{{FLOW}}", "flow"), ("{{ARCH}}", "arch"), ("{{RSEG}}", "rseg")):
    t = t.replace(k, (svg / f"{n}.svg").read_text())
(here / "deck.html").write_text(t)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                "--virtual-time-budget=15000", f"--print-to-pdf={out / '01_pitch_deck.pdf'}", f"file://{here / 'deck.html'}"], check=True, stderr=subprocess.DEVNULL)
(here / "deck.html").unlink()
print("wrote deck:", (out / "01_pitch_deck.pdf").stat().st_size // 1024, "KB")
