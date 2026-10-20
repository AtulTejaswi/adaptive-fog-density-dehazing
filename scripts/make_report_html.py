"""Convert the Markdown report to a print-ready HTML file."""
from __future__ import annotations

from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "report.md"
OUT = ROOT / "report" / "FogSense_report.html"

md_text = SRC.read_text(encoding="utf-8")
body = markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "toc", "sane_lists", "nl2br"],
    output_format="html5",
)

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FogSense report</title>
<style>
  @page {{ size: A4; margin: 16mm 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", "Calibri", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1B2733;
    margin: 0;
  }}
  h1 {{ font-size: 20pt; color: #0B1F33; border-bottom: 2px solid #0E7C86; padding-bottom: 4px; page-break-before: always; }}
  h1:first-of-type {{ page-break-before: auto; }}
  h2 {{ font-size: 15pt; color: #0B1F33; margin-top: 14pt; page-break-after: avoid; }}
  h3 {{ font-size: 12.5pt; color: #0E7C86; margin-top: 10pt; page-break-after: avoid; }}
  p, li {{ orphans: 3; widows: 3; }}
  code {{ font-family: Consolas, monospace; font-size: 9pt; background: #F1F4F8; padding: 1px 3px; border-radius: 3px; }}
  pre {{ background: #F1F4F8; padding: 8px; border-radius: 4px; overflow-x: auto; page-break-inside: avoid; }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8pt 0; page-break-inside: avoid; font-size: 9pt; }}
  th, td {{ border: 1px solid #C9D2DB; padding: 4px 6px; vertical-align: top; }}
  th {{ background: #0B1F33; color: white; font-weight: 600; }}
  tr:nth-child(even) td {{ background: #F7F9FB; }}
  img {{ max-width: 100%; height: auto; page-break-inside: avoid; margin: 6pt 0; border: 1px solid #E3E8EE; }}
  blockquote {{ border-left: 3px solid #0E7C86; margin: 8pt 0; padding: 4pt 10pt; color: #445566; background: #F7F9FB; }}
  hr {{ border: none; border-top: 1px solid #C9D2DB; margin: 10pt 0; }}
  ul, ol {{ margin: 4pt 0 8pt 18pt; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
OUT.write_text(html, encoding="utf-8")
print("wrote", OUT)
