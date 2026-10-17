"""Renders docs/images/architecture.png (+ .svg copy) from svg/arch.svg."""
import pathlib, shutil, subprocess
g = pathlib.Path(__file__).parent; sub = g.parent / "images"
svg = (g / "svg" / "arch.svg").read_text().replace("<svg ", '<svg style="width:1460px;height:auto" ', 1)
html = ('<!doctype html><html><body style="margin:0;background:#fff"><div style="width:1520px;padding:30px 30px 20px;background:#fff">'
        '<div style="font:italic 700 34px Georgia,serif;margin:0 0 6px">VaultRAG — system architecture</div>'
        '<div style="font:15px Helvetica,Arial,sans-serif;color:#4a463c;margin-bottom:14px">Every question: check the badge → search only allowed pages → '
        'AI writes → <b>final re-check</b> → show or block → write the diary. Team Hacktivists · IBM Z Datathon 2026</div>' + svg + '</div></body></html>')
page = g / "arch_png.html"; page.write_text(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=2", "--window-size=1520,1010", f"--screenshot={sub / 'architecture.png'}", f"file://{page}"],
               check=True, stderr=subprocess.DEVNULL)
shutil.copy(g / "svg" / "arch.svg", sub / "architecture.svg"); page.unlink()
print("wrote", sub / "architecture.png")
